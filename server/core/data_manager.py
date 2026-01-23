import os
import sqlite3
import pandas as pd
import datetime
import traceback
import logging
from contextlib import contextmanager
from typing import Optional, Iterable
from core.tdx_http_client import tdx_http_client
from core.data_processor import DataProcessor
from core.config import (
    DATA_SYNC_STOCK_SYMBOLS,
    DATA_SYNC_FUND_SYMBOLS,
    DATA_SYNC_FUTURES_SYMBOLS,
    DATA_SYNC_STOCK_LIMIT,
    DATA_SYNC_FUND_LIMIT,
    DATA_SYNC_FUTURES_LIMIT,
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "storage", "data")
DB_PATH = os.path.join(BASE_DIR, "storage", "market_data.db")

logger = logging.getLogger(__name__)


class DataManager:
    def __init__(self, data_dir: str = DATA_DIR, db_path: Optional[str] = None, cleaning_rules: Optional[dict] = None):
        self.data_dir = data_dir
        self.db_path = db_path or DB_PATH
        self.cleaning_rules = cleaning_rules
        os.makedirs(self.data_dir, exist_ok=True)
        self._ensure_db()

    def _infer_asset_type(self, symbol: str) -> str:
        s = str(symbol).strip().upper()
        if s.startswith("SH") or s.startswith("SZ"):
            return "stock"
        if s.endswith(".SH") or s.endswith(".SZ"):
            return "stock"
        if s.isdigit() and len(s) == 6:
            return "stock"
        return "futures"

    def _normalize_symbol(self, symbol: str, asset_type: str) -> str:
        s = str(symbol).strip().upper()
        if asset_type == "stock":
            if s.startswith("SH") or s.startswith("SZ"):
                s = s[2:]
            if s.endswith(".SH") or s.endswith(".SZ"):
                s = s[:-3]
        return s

    @contextmanager
    def _connect(self) -> Iterable[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _ensure_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS market_bars (
                    asset_type TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    period TEXT NOT NULL,
                    ts TEXT NOT NULL,
                    open_price REAL,
                    high_price REAL,
                    low_price REAL,
                    close_price REAL,
                    volume REAL,
                    open_interest REAL,
                    amount REAL,
                    update_time TEXT NOT NULL,
                    PRIMARY KEY (asset_type, symbol, period, ts)
                );
                CREATE INDEX IF NOT EXISTS idx_market_bars_ts ON market_bars(ts);
                CREATE TABLE IF NOT EXISTS sync_state (
                    asset_type TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    period TEXT NOT NULL,
                    last_ts TEXT,
                    last_sync TEXT,
                    PRIMARY KEY (asset_type, symbol, period)
                );
                CREATE TABLE IF NOT EXISTS sync_jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    asset_type TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    period TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT,
                    status TEXT NOT NULL,
                    rows_fetched INTEGER NOT NULL,
                    rows_written INTEGER NOT NULL,
                    error TEXT
                );
                """
            )

    def get_symbols_list(self):
        """
        获取品种列表，优先从本地缓存读取
        """
        cache_path = os.path.join(self.data_dir, "symbols_cache.json")
        if os.path.exists(cache_path):
            try:
                import json
                with open(cache_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data
            except Exception as e:
                print(f"Error loading symbols cache: {e}")
        return None

    def save_symbols_list(self, symbols_list):
        """
        保存品种列表到本地
        """
        cache_path = os.path.join(self.data_dir, "symbols_cache.json")
        try:
            import json
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(symbols_list, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving symbols cache: {e}")

    def _get_last_ts(self, asset_type: str, symbol: str, period: str) -> Optional[datetime.datetime]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT last_ts FROM sync_state WHERE asset_type=? AND symbol=? AND period=?",
                (asset_type, symbol, period),
            ).fetchone()
            if row and row[0]:
                return pd.to_datetime(row[0]).to_pydatetime()
        return None

    def _set_last_ts(self, asset_type: str, symbol: str, period: str, last_ts: datetime.datetime) -> None:
        ts_val = last_ts.isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO sync_state(asset_type, symbol, period, last_ts, last_sync)
                VALUES(?, ?, ?, ?, ?)
                ON CONFLICT(asset_type, symbol, period)
                DO UPDATE SET last_ts=excluded.last_ts, last_sync=excluded.last_sync
                """,
                (asset_type, symbol, period, ts_val, datetime.datetime.now(datetime.UTC).isoformat()),
            )

    def _record_job(
        self,
        asset_type: str,
        symbol: str,
        period: str,
        mode: str,
        start_time: datetime.datetime,
        end_time: datetime.datetime,
        status: str,
        rows_fetched: int,
        rows_written: int,
        error: Optional[str] = None,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO sync_jobs(
                    asset_type, symbol, period, mode, start_time, end_time, status,
                    rows_fetched, rows_written, error
                ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    asset_type,
                    symbol,
                    period,
                    mode,
                    start_time.isoformat(),
                    end_time.isoformat(),
                    status,
                    rows_fetched,
                    rows_written,
                    error,
                ),
            )

    def _next_start_date(self, last_ts: datetime.datetime, period: str) -> datetime.datetime:
        if period in {"daily", "weekly"}:
            return last_ts + datetime.timedelta(days=1)
        if str(period).isdigit():
            return last_ts + datetime.timedelta(minutes=int(period))
        return last_ts + datetime.timedelta(days=1)

    def load_data(self, symbol, period, start_date=None, end_date=None, asset_type="futures"):
        filters = ["asset_type=?", "symbol=?", "period=?"]
        params = [asset_type, symbol, period]

        if start_date:
            filters.append("ts>=?")
            params.append(pd.to_datetime(start_date).isoformat())
        if end_date:
            end_dt = pd.to_datetime(end_date) + pd.Timedelta(days=1)
            filters.append("ts<?")
            params.append(end_dt.isoformat())

        where_clause = " AND ".join(filters)
        sql = (
            "SELECT ts, open_price, high_price, low_price, close_price, volume, open_interest, amount "
            f"FROM market_bars WHERE {where_clause} ORDER BY ts ASC"
        )

        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()

        if not rows:
            return None

        df = pd.DataFrame(rows, columns=[
            "ts",
            "Open",
            "High",
            "Low",
            "Close",
            "Volume",
            "OpenInterest",
            "Amount",
        ])
        df["ts"] = pd.to_datetime(df["ts"])
        df.set_index("ts", inplace=True)
        df.index.name = "date" if period in {"daily", "weekly"} else "datetime"
        return df

    def _fetch_from_tdx(self, symbol, period_str):
        """
        Attempt to fetch kline from TDX (HTTP or Internal).
        Returns DataFrame with standard columns (Open, High, Low, Close, Volume) and DatetimeIndex,
        or None if failed.
        """
        
        tdx_period = "day"
        if period_str == "daily":
            tdx_period = "day"
        elif period_str == "weekly":
            tdx_period = "week"
        elif str(period_str).isdigit():
            tdx_period = f"{period_str}min"
        else:
            tdx_period = period_str

        data = []
        if tdx_http_client.is_available():
            try:
                data = tdx_http_client.get_kline(symbol, tdx_period)
            except:
                pass

        if not data:
            try:
                pass
            except:
                pass
                
        if not data:
            return None
            
        try:
            df = pd.DataFrame(data)
            if df.empty:
                return None
                
            rename_map = {
                'open': 'Open', 'close': 'Close', 'high': 'High', 'low': 'Low', 
                'vol': 'Volume', 'amount': 'Amount',
                'datetime': 'date' if period_str in ['daily', 'weekly'] else 'datetime'
            }
            
            if 'open' in df.columns:
                df.rename(columns=rename_map, inplace=True)
            
            idx_col = 'date' if 'date' in df.columns else 'datetime'
            if idx_col in df.columns:
                df[idx_col] = pd.to_datetime(df[idx_col])
                df.set_index(idx_col, inplace=True)
            else:
                return None
                
            return df
        except Exception as e:
            print(f"Error processing TDX data: {e}")
            return None

    def _format_date(self, value: Optional[datetime.datetime]) -> Optional[str]:
        if value is None:
            return None
        return pd.to_datetime(value).strftime("%Y%m%d")

    def _filter_after(self, df: pd.DataFrame, last_ts: Optional[datetime.datetime]) -> pd.DataFrame:
        if df is None or df.empty or last_ts is None:
            return df
        return df[df.index > last_ts]

    def _fetch_stock_data(self, symbol: str, period: str, start_date: Optional[datetime.datetime]) -> Optional[pd.DataFrame]:
        try:
            if period in {"daily", "weekly"}:
                df = self._fetch_from_tdx(symbol, period)
                if df is not None:
                    return df

                import akshare as ak
                start_arg = self._format_date(start_date)
                try:
                    if start_arg:
                        df = ak.stock_zh_a_hist(symbol=symbol, period="daily", adjust="qfq", start_date=start_arg)
                    else:
                        df = ak.stock_zh_a_hist(symbol=symbol, period="daily", adjust="qfq")
                except TypeError:
                    df = ak.stock_zh_a_hist(symbol=symbol, period="daily", adjust="qfq")

                if df is None or df.empty:
                    return None
                df.rename(columns={
                    "日期": "date",
                    "开盘": "Open",
                    "最高": "High",
                    "最低": "Low",
                    "收盘": "Close",
                    "成交量": "Volume",
                }, inplace=True)
                df["date"] = pd.to_datetime(df["date"])
                df.set_index("date", inplace=True)
                return df

            df = self._fetch_from_tdx(symbol, period)
            if df is not None:
                return df

            import akshare as ak
            try:
                df = ak.stock_zh_a_hist_min_em(symbol=symbol, period=period, adjust="qfq")
            except Exception:
                return None
            if df is None or df.empty:
                return None
            df.rename(columns={
                "时间": "datetime",
                "开盘": "Open",
                "最高": "High",
                "最低": "Low",
                "收盘": "Close",
                "成交量": "Volume",
            }, inplace=True)
            df["datetime"] = pd.to_datetime(df["datetime"])
            df.set_index("datetime", inplace=True)
            return df
        except Exception:
            return None

    def _fetch_futures_data(self, symbol: str, period: str, start_date: Optional[datetime.datetime]) -> Optional[pd.DataFrame]:
        try:
            import akshare as ak
            if period in {"daily", "weekly"}:
                df = ak.futures_zh_daily_sina(symbol=symbol)
                if df is None or df.empty:
                    return None
                df.rename(columns={
                    "date": "date",
                    "open": "Open",
                    "high": "High",
                    "low": "Low",
                    "close": "Close",
                    "volume": "Volume",
                    "hold": "OpenInterest",
                }, inplace=True)
                df["date"] = pd.to_datetime(df["date"])
                df.set_index("date", inplace=True)
                return df

            df = ak.futures_zh_minute_sina(symbol=symbol, period=period)
            if df is None or df.empty:
                return None
            df.rename(columns={
                "datetime": "datetime",
                "open": "Open",
                "high": "High",
                "low": "Low",
                "close": "Close",
                "volume": "Volume",
                "hold": "OpenInterest",
            }, inplace=True)
            df["datetime"] = pd.to_datetime(df["datetime"])
            df.set_index("datetime", inplace=True)
            return df
        except Exception:
            return None

    def _fetch_fund_data(self, symbol: str) -> Optional[pd.DataFrame]:
        try:
            import akshare as ak
            df = ak.fund_open_fund_info_em(fund=symbol, indicator="单位净值走势")
            if df is None or df.empty:
                return None
            date_col = "净值日期" if "净值日期" in df.columns else df.columns[0]
            value_col = "单位净值" if "单位净值" in df.columns else df.columns[1]
            df.rename(columns={date_col: "date", value_col: "Close"}, inplace=True)
            df["date"] = pd.to_datetime(df["date"])
            df.set_index("date", inplace=True)
            df["Open"] = df["Close"]
            df["High"] = df["Close"]
            df["Low"] = df["Close"]
            return df
        except Exception:
            return None

    def _fetch_data(self, symbol: str, period: str, asset_type: str, start_date: Optional[datetime.datetime]) -> Optional[pd.DataFrame]:
        if asset_type == "fund":
            return self._fetch_fund_data(symbol)
        if asset_type == "stock":
            return self._fetch_stock_data(symbol, period, start_date)
        return self._fetch_futures_data(symbol, period, start_date)

    def _write_market_data_mongo(self, df: pd.DataFrame, asset_type: str, symbol: str, period: str) -> int:
        if df is None or df.empty:
            return 0
        try:
            from core.database import get_market_collection
        except Exception:
            return 0

        try:
            col = get_market_collection()
        except Exception as e:
            logger.warning("Mongo market collection unavailable: %s", e)
            return 0

        try:
            try:
                from pymongo import UpdateOne
            except Exception:
                UpdateOne = None

            update_time = datetime.datetime.now(datetime.UTC).isoformat()
            if UpdateOne is not None:
                ops = []
                for ts, row in df.iterrows():
                    ts_val = pd.to_datetime(ts).isoformat()
                    doc = {
                        "asset_type": asset_type,
                        "symbol": symbol,
                        "period": period,
                        "ts": ts_val,
                        "open_price": row.get("Open"),
                        "high_price": row.get("High"),
                        "low_price": row.get("Low"),
                        "close_price": row.get("Close"),
                        "volume": row.get("Volume"),
                        "open_interest": row.get("OpenInterest"),
                        "amount": row.get("Amount"),
                        "update_time": update_time,
                    }
                    key = {
                        "asset_type": asset_type,
                        "symbol": symbol,
                        "period": period,
                        "ts": ts_val,
                    }
                    ops.append(UpdateOne(key, {"$set": doc}, upsert=True))
                if ops:
                    col.bulk_write(ops, ordered=False)
                return len(ops)

            written = 0
            for ts, row in df.iterrows():
                ts_val = pd.to_datetime(ts).isoformat()
                doc = {
                    "asset_type": asset_type,
                    "symbol": symbol,
                    "period": period,
                    "ts": ts_val,
                    "open_price": row.get("Open"),
                    "high_price": row.get("High"),
                    "low_price": row.get("Low"),
                    "close_price": row.get("Close"),
                    "volume": row.get("Volume"),
                    "open_interest": row.get("OpenInterest"),
                    "amount": row.get("Amount"),
                    "update_time": update_time,
                }
                key = {
                    "asset_type": asset_type,
                    "symbol": symbol,
                    "period": period,
                    "ts": ts_val,
                }
                col.update_one(key, {"$set": doc}, upsert=True)
                written += 1
            return written
        except Exception as e:
            logger.warning("Mongo market write failed: %s", e)
            return 0

    def _write_market_data(self, df: pd.DataFrame, asset_type: str, symbol: str, period: str) -> int:
        if df is None or df.empty:
            return 0
        update_time = datetime.datetime.now(datetime.UTC).isoformat()
        rows = []
        for ts, row in df.iterrows():
            rows.append(
                (
                    asset_type,
                    symbol,
                    period,
                    pd.to_datetime(ts).isoformat(),
                    row.get("Open"),
                    row.get("High"),
                    row.get("Low"),
                    row.get("Close"),
                    row.get("Volume"),
                    row.get("OpenInterest"),
                    row.get("Amount"),
                    update_time,
                )
            )

        with self._connect() as conn:
            conn.executemany(
                """
                INSERT INTO market_bars(
                    asset_type, symbol, period, ts, open_price, high_price, low_price, close_price,
                    volume, open_interest, amount, update_time
                ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(asset_type, symbol, period, ts)
                DO UPDATE SET
                    open_price=excluded.open_price,
                    high_price=excluded.high_price,
                    low_price=excluded.low_price,
                    close_price=excluded.close_price,
                    volume=excluded.volume,
                    open_interest=excluded.open_interest,
                    amount=excluded.amount,
                    update_time=excluded.update_time
                """,
                rows,
            )
        self._write_market_data_mongo(df, asset_type, symbol, period)
        return len(rows)

    def sync_symbol_data(self, symbol: str, period: str, asset_type: str, full: bool = False) -> bool:
        start_time = datetime.datetime.now(datetime.UTC)
        last_ts = None if full else self._get_last_ts(asset_type, symbol, period)
        mode = "full" if full or last_ts is None else "incremental"
        try:
            start_date = None if last_ts is None else self._next_start_date(last_ts, period)
            df = self._fetch_data(symbol, period, asset_type, start_date)
            rows_fetched = 0 if df is None else len(df)
            df = DataProcessor.clean_data(df, self.cleaning_rules)
            df = self._filter_after(df, last_ts)
            rows_written = self._write_market_data(df, asset_type, symbol, period)
            if df is not None and not df.empty:
                self._set_last_ts(asset_type, symbol, period, df.index.max().to_pydatetime())
            end_time = datetime.datetime.now(datetime.UTC)
            self._record_job(
                asset_type,
                symbol,
                period,
                mode,
                start_time,
                end_time,
                "success",
                rows_fetched,
                rows_written,
                None,
            )
            return True
        except Exception as e:
            end_time = datetime.datetime.now(datetime.UTC)
            self._record_job(
                asset_type,
                symbol,
                period,
                mode,
                start_time,
                end_time,
                "failed",
                0,
                0,
                str(e),
            )
            logger.error("Sync failed: %s %s %s", asset_type, symbol, period)
            logger.error("%s", traceback.format_exc())
            return False

    def fetch_and_update(
        self,
        symbol: str,
        period: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        asset_type: Optional[str] = None,
        full: bool = False,
    ) -> Optional[pd.DataFrame]:
        resolved_type = asset_type or self._infer_asset_type(symbol)
        normalized_symbol = self._normalize_symbol(symbol, resolved_type)
        df = self.load_data(normalized_symbol, period, start_date, end_date, asset_type=resolved_type)
        if df is not None and not df.empty:
            return df
        self.sync_symbol_data(normalized_symbol, period, resolved_type, full=full)
        return self.load_data(normalized_symbol, period, start_date, end_date, asset_type=resolved_type)

    def migrate_market_to_mongo(self, batch_size: int = 1000) -> dict:
        from core.database import migrate_market_sqlite_to_mongo
        return migrate_market_sqlite_to_mongo(self.db_path, batch_size=batch_size)

    def get_data_with_fallback(self, symbol, period, start_date=None, end_date=None, asset_type="futures"):
        df = self.load_data(symbol, period, start_date, end_date, asset_type=asset_type)
        if df is not None and not df.empty:
            return df
        return self.fetch_and_update(symbol, period, start_date, end_date, asset_type=asset_type)

    def _limit_list(self, values: Iterable[str], limit: int) -> list:
        values_list = list(values)
        if limit and limit > 0:
            return values_list[:limit]
        return values_list

    def _get_futures_symbols(self) -> list:
        if DATA_SYNC_FUTURES_SYMBOLS:
            return list(DATA_SYNC_FUTURES_SYMBOLS)
        cache = self.get_symbols_list()
        if isinstance(cache, dict) and cache.get("futures"):
            symbols = [s.get("code") for s in cache.get("futures") if s.get("code")]
            return self._limit_list(symbols, DATA_SYNC_FUTURES_LIMIT)
        try:
            import akshare as ak
            df = ak.futures_display_main_sina()
            if df is None or df.empty:
                return []
            return self._limit_list(df["symbol"].dropna().astype(str).tolist(), DATA_SYNC_FUTURES_LIMIT)
        except Exception:
            return []

    def _get_stock_symbols(self) -> list:
        if DATA_SYNC_STOCK_SYMBOLS:
            return list(DATA_SYNC_STOCK_SYMBOLS)
        cache = self.get_symbols_list()
        if isinstance(cache, dict) and cache.get("stocks"):
            symbols = [s.get("code") for s in cache.get("stocks") if s.get("code")]
            return self._limit_list(symbols, DATA_SYNC_STOCK_LIMIT)
        try:
            import akshare as ak
            df = ak.stock_zh_a_spot_em()
            if df is None or df.empty:
                return []
            symbols = df["代码"].dropna().astype(str).tolist()
            return self._limit_list(symbols, DATA_SYNC_STOCK_LIMIT)
        except Exception:
            return []

    def _get_fund_symbols(self) -> list:
        if DATA_SYNC_FUND_SYMBOLS:
            return list(DATA_SYNC_FUND_SYMBOLS)
        try:
            import akshare as ak
            df = ak.fund_open_fund_rank_em()
            if df is None or df.empty:
                return []
            if "基金代码" in df.columns:
                symbols = df["基金代码"].dropna().astype(str).tolist()
            else:
                symbols = df.iloc[:, 0].dropna().astype(str).tolist()
            return self._limit_list(symbols, DATA_SYNC_FUND_LIMIT)
        except Exception:
            return []

    def sync_asset(self, asset_type: str, period: str = "daily", full: bool = False) -> dict:
        if asset_type == "stock":
            symbols = self._get_stock_symbols()
        elif asset_type == "fund":
            symbols = self._get_fund_symbols()
        else:
            symbols = self._get_futures_symbols()

        results = {"asset_type": asset_type, "period": period, "total": len(symbols), "success": 0, "failed": 0}
        for symbol in symbols:
            if not symbol:
                continue
            ok = self.sync_symbol_data(symbol, period, asset_type, full=full)
            if ok:
                results["success"] += 1
            else:
                results["failed"] += 1
        return results

    def sync_all(self, asset_types: Optional[list] = None, period: str = "daily", full: bool = False) -> list:
        asset_types = asset_types or ["stock", "fund", "futures"]
        summaries = []
        for asset_type in asset_types:
            summaries.append(self.sync_asset(asset_type, period=period, full=full))
        return summaries

data_manager = DataManager()
