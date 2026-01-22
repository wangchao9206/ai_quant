
from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Optional
from pydantic import BaseModel
import asyncio
import datetime
import math
import re
import threading
import time
from core.tdx_client import tdx_client

router = APIRouter()


_cache_lock = threading.Lock()
_quote_cache = {}
_orderbook_cache = {}
_intraday_cache = {}
_stock_list_cache = {"data": None, "ts": 0.0, "refreshing": False, "next": 0.0}

_INDEX_CODES = {
    "000001", "000300", "000905", "399001", "399006", "399005", "000016", "000688"
}

def _to_float(value):
    if value in (None, ""):
        return None
    try:
        v = float(str(value).replace("%", "").strip())
    except Exception:
        return None
    return v if math.isfinite(v) else None

def _get_cache(bucket, key):
    cache = bucket.get(key)
    if cache is None:
        cache = {"data": None, "ts": 0.0, "refreshing": False, "next": 0.0}
        bucket[key] = cache
    return cache

def _trim_cache(bucket, max_size=100):
    if len(bucket) > max_size:
        keys = list(bucket.keys())
        to_remove = max(1, int(len(keys) * 0.2))
        for k in keys[:to_remove]:
            bucket.pop(k, None)

def _parse_symbol(symbol: str):
    s = symbol.upper().strip()
    exchange = None
    code = s
    
    # Remove common prefixes/suffixes
    if s.startswith("SH") or s.startswith("SZ"):
        exchange = s[:2]
        code = s[2:]
    elif s.endswith(".SH") or s.endswith(".SZ"):
        exchange = s[-2:]
        code = s[:-3]
    
    # Infer exchange if not explicit
    if not exchange:
        if code.startswith("6"):
            exchange = "SH"
        elif code.startswith("0") or code.startswith("3"):
            exchange = "SZ"
        elif code.startswith("4") or code.startswith("8"):
            exchange = "BJ"
            
    kind = "stock"
    # Basic heuristic for index vs stock
    # SH index: 000xxx, SZ index: 399xxx
    if code in _INDEX_CODES:
        kind = "index"
    elif exchange == "SH" and code.startswith("000"):
        kind = "index"
    elif exchange == "SZ" and code.startswith("399"):
        kind = "index"
        
    return {
        "kind": kind,
        "exchange": exchange,
        "code": code,
        "display": symbol
    }

class StockQuote(BaseModel):
    name: str
    code: str
    price: float
    change: float
    changeAmt: float
    open: float
    high: float
    low: float
    vol: str
    amt: str
    pe: float
    pb: float

class OrderBook(BaseModel):
    asks: List[Dict[str, float]]
    bids: List[Dict[str, float]]

class IntradayData(BaseModel):
    times: List[str]
    values: List[List[float]]

# Helper to fetch stock list from TDX
def _fetch_stock_list_tdx():
    stocks = []
    try:
        # Fetch SH (1) and SZ (0)
        # Fetch first 3 batches (3000 stocks) from each market should cover most
        for market in [0, 1]:
            for start in [0, 1000, 2000, 3000, 4000]: # Up to 5000 stocks per market
                try:
                    data = tdx_client.get_security_list(market, start)
                    if not data:
                        break
                    for d in data:
                        code = d.get('code')
                        name = d.get('name')
                        if code and name:
                            stocks.append({"code": str(code), "name": str(name)})
                    if len(data) < 1000:
                        break
                except Exception:
                    break
        # Ensure deterministic order
        stocks.sort(key=lambda x: x['code'])
        return stocks
    except Exception as e:
        print(f"TDX stock list fetch error: {e}")
        return []

# --- Routes ---

@router.get("/search")
async def search_stock(q: str = Query(..., min_length=1)):
    """
    Search for stocks by code or name
    """
    now = time.monotonic()
    with _cache_lock:
        cached = _stock_list_cache["data"]
        ts = _stock_list_cache["ts"]
        refreshing = _stock_list_cache["refreshing"]
        next_refresh = _stock_list_cache["next"]

    # Cache for 1 hour
    if cached is None or (now - ts > 3600):
        if not refreshing and now >= next_refresh:
            with _cache_lock:
                if not _stock_list_cache["refreshing"]:
                    _stock_list_cache["refreshing"] = True
                    
                    async def _refresh():
                        try:
                            # Use TDX instead of AkShare
                            data = await asyncio.to_thread(_fetch_stock_list_tdx)
                            if data:
                                with _cache_lock:
                                    _stock_list_cache["data"] = data
                                    _stock_list_cache["ts"] = time.monotonic()
                        except Exception as e:
                            print(f"Failed to fetch stock list: {e}")
                            with _cache_lock:
                                _stock_list_cache["next"] = time.monotonic() + 60.0
                        finally:
                            with _cache_lock:
                                _stock_list_cache["refreshing"] = False
                    
                    asyncio.create_task(_refresh())
    
    # Use cached data if available, even if stale
    data = cached or []

    q_str = q.lower().strip()
    results = []
    for item in data:
        if q_str in item["code"] or q_str in item["name"]:
            results.append(item)
        if len(results) >= 10:
            break
            
    return results


def _fetch_stock_quote_tdx(code: str, exchange: Optional[str] = None, display: Optional[str] = None):
    try:
        quotes = tdx_client.get_quotes([code])
        if not quotes:
            return None
        q = quotes[0]
        
        # Try to find name from cache if missing or just code
        name = q.get('name')
        if name == code:
             with _cache_lock:
                cached_list = _stock_list_cache.get("data")
                if cached_list:
                    for s in cached_list:
                        if s['code'] == code:
                            name = s['name']
                            break

        return {
            "name": name,
            "code": display or code,
            "price": q.get('price', 0),
            "change": q.get('change_pct', 0),
            "changeAmt": q.get('change', 0),
            "open": q.get('open', 0),
            "high": q.get('high', 0),
            "low": q.get('low', 0),
            "vol": str(q.get('vol', 0)),
            "amt": str(q.get('amount', 0)),
            "pe": 0.0, # TDX quote doesn't have PE/PB usually
            "pb": 0.0,
        }
    except Exception as e:
        print(f"TDX quote error for {code}: {e}")
        return None

@router.get("/quote", response_model=StockQuote)
async def get_stock_quote(symbol: str):
    parsed = _parse_symbol(symbol)
    cache_key = f"{parsed['kind']}:{parsed['exchange'] or ''}:{parsed['code']}"
    now = time.monotonic()
    with _cache_lock:
        cache = _get_cache(_quote_cache, cache_key)
        cached = cache["data"]
        ts = cache["ts"]
        refreshing = cache["refreshing"]
        next_refresh = cache["next"]

    if cached is not None and now - ts < 3.0:
        return cached

    if not refreshing and now >= next_refresh:
        with _cache_lock:
            cache = _get_cache(_quote_cache, cache_key)
            if not cache["refreshing"] and time.monotonic() >= cache["next"]:
                cache["refreshing"] = True
                _trim_cache(_quote_cache)

                async def _refresh():
                    try:
                        try:
                            if parsed["kind"] == "index":
                                data = await asyncio.wait_for(asyncio.to_thread(_fetch_index_quote_akshare, parsed["code"], parsed["exchange"], parsed["display"]), timeout=6.0)
                            else:
                                # Use TDX for stocks
                                data = await asyncio.to_thread(_fetch_stock_quote_tdx, parsed["code"], parsed["exchange"], parsed["display"])
                        except Exception:
                            with _cache_lock:
                                cache["next"] = time.monotonic() + 5.0
                            return
                        if data:
                            with _cache_lock:
                                cache["data"] = data
                                cache["ts"] = time.monotonic()
                    finally:
                        with _cache_lock:
                            cache["refreshing"] = False

                # If cache is empty, await the result (first load)
                if cached is None:
                    await _refresh()
                    # Re-read cache
                    with _cache_lock:
                        cache = _get_cache(_quote_cache, cache_key)
                        cached = cache["data"]
                else:
                    asyncio.create_task(_refresh())

    if cached is not None:
        return cached
    
    # Return 404 if data not found
    raise HTTPException(status_code=404, detail="Stock quote not found")

def _fetch_orderbook_tdx(code: str):
    try:
        quotes = tdx_client.get_quotes([code])
        if not quotes:
            return None
        q = quotes[0]
        return {"asks": q.get('asks', []), "bids": q.get('bids', [])}
    except Exception:
        return None

@router.get("/orderbook", response_model=OrderBook)
async def get_orderbook(symbol: str):
    parsed = _parse_symbol(symbol)
    cache_key = f"{parsed['kind']}:{parsed['exchange'] or ''}:{parsed['code']}"
    now = time.monotonic()
    with _cache_lock:
        cache = _get_cache(_orderbook_cache, cache_key)
        cached = cache["data"]
        ts = cache["ts"]
        refreshing = cache["refreshing"]
        next_refresh = cache["next"]

    if cached is not None and now - ts < 1.0:
        return cached

    if not refreshing and now >= next_refresh:
        with _cache_lock:
            cache = _get_cache(_orderbook_cache, cache_key)
            if not cache["refreshing"] and time.monotonic() >= cache["next"]:
                cache["refreshing"] = True
                _trim_cache(_orderbook_cache)

                async def _refresh():
                    try:
                        try:
                            if parsed["kind"] == "index":
                                data = None
                            else:
                                # Use TDX
                                data = await asyncio.to_thread(_fetch_orderbook_tdx, parsed["code"])
                        except Exception:
                            with _cache_lock:
                                cache["next"] = time.monotonic() + 10.0
                            return
                        if data:
                            with _cache_lock:
                                cache["data"] = data
                                cache["ts"] = time.monotonic()
                    finally:
                        with _cache_lock:
                            cache["refreshing"] = False

                asyncio.create_task(_refresh())

    if cached is not None:
        return cached
    return {"asks": [], "bids": []}


@router.get("/intraday", response_model=IntradayData)
async def get_intraday(symbol: str):
    parsed = _parse_symbol(symbol)
    cache_key = f"{parsed['kind']}:{parsed['exchange'] or ''}:{parsed['code']}"
    now = time.monotonic()
    with _cache_lock:
        cache = _get_cache(_intraday_cache, cache_key)
        cached = cache["data"]
        ts = cache["ts"]
        refreshing = cache["refreshing"]
        next_refresh = cache["next"]

    if cached is not None and now - ts < 30.0:
        return cached

    if not refreshing and now >= next_refresh:
        with _cache_lock:
            cache = _get_cache(_intraday_cache, cache_key)
            if not cache["refreshing"] and time.monotonic() >= cache["next"]:
                cache["refreshing"] = True
                _trim_cache(_intraday_cache, max_size=50)

                async def _refresh():
                    try:
                        try:
                            if parsed["kind"] == "index":
                                data = await asyncio.wait_for(
                                    asyncio.to_thread(_fetch_index_kline_akshare, parsed["code"], parsed["exchange"]),
                                    timeout=8.0,
                                )
                            else:
                                data = await asyncio.wait_for(asyncio.to_thread(_fetch_intraday_akshare, parsed["code"]), timeout=10.0)
                        except Exception:
                            with _cache_lock:
                                cache["next"] = time.monotonic() + 30.0
                            return
                        if data:
                            with _cache_lock:
                                cache["data"] = data
                                cache["ts"] = time.monotonic()
                    finally:
                        with _cache_lock:
                            cache["refreshing"] = False

                asyncio.create_task(_refresh())

    if cached is not None:
        return cached
    return {"times": [], "values": []}


def _fetch_index_quote_akshare(code: str, exchange: Optional[str], display: str):
    try:
        import akshare as ak

        df = ak.stock_zh_index_spot_em()
        if df is None or df.empty:
            return None
        records = df.to_dict(orient="records")
        rec = None
        for r in records:
            c = r.get("代码") or r.get("指数代码") or r.get("f12") or r.get("index_code") or ""
            c = str(c).strip()
            if c.isdigit() and c.zfill(6) == code:
                rec = r
                break
        if not rec:
            return None
        name = rec.get("指数名称") or rec.get("名称") or rec.get("name") or rec.get("f14") or display
        price = _to_float(rec.get("最新价") or rec.get("price") or rec.get("f2"))
        change_pct = _to_float(rec.get("涨跌幅") or rec.get("change") or rec.get("f3")) or 0.0
        change_amt = _to_float(rec.get("涨跌额") or rec.get("change_amt") or rec.get("f4")) or 0.0
        open_price = _to_float(rec.get("今开") or rec.get("open") or rec.get("f5") or price) or (price or 0.0)
        high_price = _to_float(rec.get("最高") or rec.get("high") or rec.get("f6") or price) or (price or 0.0)
        low_price = _to_float(rec.get("最低") or rec.get("low") or rec.get("f7") or price) or (price or 0.0)
        vol = rec.get("成交量") or rec.get("volume") or rec.get("f5") or ""
        amt = rec.get("成交额") or rec.get("amount") or rec.get("f6") or ""
        if price is None:
            return None
        return {
            "name": str(name),
            "code": display,
            "price": round(price, 2),
            "change": round(change_pct, 2),
            "changeAmt": round(change_amt, 2),
            "open": round(open_price, 2),
            "high": round(high_price, 2),
            "low": round(low_price, 2),
            "vol": str(vol),
            "amt": str(amt),
            "pe": 0.0,
            "pb": 0.0,
        }
    except Exception:
        return None


def _fetch_index_kline_akshare(code: str, exchange: Optional[str]):
    try:
        import akshare as ak

        prefix = (exchange or "SH").lower()
        symbol = f"{prefix}{code}" if code.isdigit() else str(code)
        df = ak.stock_zh_index_daily_em(symbol=symbol)
        if df is None or df.empty:
            return None
        df = df.tail(240)
        times = []
        values = []
        for _, row in df.iterrows():
            t = row.get("date") or row.get("日期") or row.get("datetime")
            o = row.get("open") or row.get("开盘")
            c = row.get("close") or row.get("收盘")
            l = row.get("low") or row.get("最低")
            h = row.get("high") or row.get("最高")
            if t is None or o is None or c is None or l is None or h is None:
                continue
            try:
                times.append(str(t)[:10])
                values.append([round(float(o), 2), round(float(c), 2), round(float(l), 2), round(float(h), 2)])
            except Exception:
                continue
        return {"times": times, "values": values} if times and values else None
    except Exception:
        return None


def _fetch_stock_quote_akshare(code: str, exchange: Optional[str] = None, display: Optional[str] = None):
    import akshare as ak

    bid_ask_fetcher = getattr(ak, "stock_bid_ask_em", None)
    if bid_ask_fetcher:
        try:
            df = bid_ask_fetcher(symbol=code)
        except TypeError:
            df = bid_ask_fetcher(code)
        rec = None
        try:
            if hasattr(df, "to_dict") and hasattr(df, "iloc"):
                rec = df.iloc[0].to_dict()
        except Exception:
            rec = None
        if rec:
            name = rec.get("名称") or rec.get("name") or code
            price = _to_float(rec.get("最新价") or rec.get("最新") or rec.get("price") or rec.get("成交价"))
            change_pct = _to_float(rec.get("涨跌幅") or rec.get("change_pct") or rec.get("pct") or 0) or 0.0
            change_amt = _to_float(rec.get("涨跌额") or rec.get("change") or 0) or 0.0
            open_price = _to_float(rec.get("今开") or rec.get("open") or price) or (price or 0.0)
            high_price = _to_float(rec.get("最高") or rec.get("high") or price) or (price or 0.0)
            low_price = _to_float(rec.get("最低") or rec.get("low") or price) or (price or 0.0)
            vol = rec.get("成交量") or rec.get("volume") or ""
            amt = rec.get("成交额") or rec.get("amount") or ""
            pe = _to_float(rec.get("市盈率-动态") or rec.get("pe") or 0) or 0.0
            pb = _to_float(rec.get("市净率") or rec.get("pb") or 0) or 0.0
            if price is None:
                return None
            return {
                "name": str(name),
                "code": display or code,
                "price": round(price, 2),
                "change": round(change_pct, 2),
                "changeAmt": round(change_amt, 2),
                "open": round(open_price, 2),
                "high": round(high_price, 2),
                "low": round(low_price, 2),
                "vol": str(vol),
                "amt": str(amt),
                "pe": round(pe, 2),
                "pb": round(pb, 2),
            }
    return None





def _fetch_intraday_akshare(code: str):
    import akshare as ak

    df = ak.stock_zh_a_hist_min_em(symbol=code, period="1")
    if df is None or df.empty:
        return None

    times = []
    values = []
    for _, row in df.iterrows():
        t = row.get("时间") or row.get("datetime") or row.get("日期")
        o = row.get("开盘") or row.get("open")
        c = row.get("收盘") or row.get("close")
        l = row.get("最低") or row.get("low")
        h = row.get("最高") or row.get("high")
        if t is None or o is None or c is None or l is None or h is None:
            continue
        times.append(str(t)[-5:])
        values.append([round(float(o), 2), round(float(c), 2), round(float(l), 2), round(float(h), 2)])
    if times and values:
        return {"times": times, "values": values}
    return None
