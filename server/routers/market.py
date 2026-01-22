
from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Optional
from pydantic import BaseModel
import asyncio
import datetime
import threading
import time
import pandas as pd
from core.tdx_client import tdx_client

router = APIRouter()


_indices_cache = {"data": None, "ts": 0.0, "refreshing": False, "next": 0.0}
_sectors_cache = {"data": None, "ts": 0.0, "refreshing": False, "next": 0.0}
_macro_calendar_cache = {"data": None, "ts": 0.0, "refreshing": False, "next": 0.0}
_replay_cache = {}
_cache_lock = threading.Lock()


def _get_cache(bucket, key):
    cache = bucket.get(key)
    if cache is None:
        cache = {"data": None, "ts": 0.0, "refreshing": False, "next": 0.0}
        bucket[key] = cache
    return cache

# --- Models ---

class MacroEvent(BaseModel):
    id: int
    time: str
    country: str
    currency: str
    event: str
    importance: str  # high, medium, low
    actual: str
    forecast: str
    previous: str
    impact: str

class MarketReplayData(BaseModel):
    time: str
    values: List[float] # [Open, Close, Low, High]
    vol: int

class KeyFrame(BaseModel):
    label: str
    index: int
    value: str
    type: str # min_price, max_price, max_vol

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
    asks: List[Dict[str, float]] # [{"p": 10.0, "v": 100}]
    bids: List[Dict[str, float]]

class SectorInfo(BaseModel):
    name: str
    change: float

class MarketIndex(BaseModel):
    name: str
    value: float
    change: float
    volume: str

class IntradayData(BaseModel):
    times: List[str]
    values: List[List[float]] # [[Open, Close, Low, High], ...]

# --- Routes ---

@router.get("/indices", response_model=List[MarketIndex])
async def get_market_indices():
    now = time.monotonic()
    with _cache_lock:
        cached = _indices_cache["data"]
        ts = _indices_cache["ts"]
        refreshing = _indices_cache["refreshing"]
        next_refresh = _indices_cache["next"]

    if cached is not None and now - ts < 10.0:
        return cached

    if not refreshing and now >= next_refresh:
        with _cache_lock:
            if not _indices_cache["refreshing"] and time.monotonic() >= _indices_cache["next"]:
                _indices_cache["refreshing"] = True

                async def _refresh():
                    try:
                        try:
                            # Use TDX for indices (Real-time)
                            data = await asyncio.to_thread(tdx_client.get_index_quotes)
                        except Exception as e:
                            print(f"TDX indices failed: {e}")
                            with _cache_lock:
                                _indices_cache["next"] = time.monotonic() + 5.0
                            return
                        if data:
                            with _cache_lock:
                                _indices_cache["data"] = data
                                _indices_cache["ts"] = time.monotonic()
                    finally:
                        with _cache_lock:
                            _indices_cache["refreshing"] = False

                asyncio.create_task(_refresh())

    return cached if cached is not None else []

@router.get("/sectors", response_model=List[SectorInfo])
async def get_market_sectors():
    now = time.monotonic()
    with _cache_lock:
        cached = _sectors_cache["data"]
        ts = _sectors_cache["ts"]
        refreshing = _sectors_cache["refreshing"]
        next_refresh = _sectors_cache["next"]

    if cached is not None and now - ts < 20.0:
        return cached

    if not refreshing and now >= next_refresh:
        with _cache_lock:
            if not _sectors_cache["refreshing"] and time.monotonic() >= _sectors_cache["next"]:
                _sectors_cache["refreshing"] = True

                async def _refresh():
                    try:
                        try:
                            data = await asyncio.wait_for(asyncio.to_thread(_fetch_market_sectors), timeout=10.0)
                        except Exception as e:
                            print(f"Sector fetch failed: {e}")
                            with _cache_lock:
                                _sectors_cache["next"] = time.monotonic() + 10.0
                            return
                        if data:
                            with _cache_lock:
                                _sectors_cache["data"] = data
                                _sectors_cache["ts"] = time.monotonic()
                    finally:
                        with _cache_lock:
                            _sectors_cache["refreshing"] = False

                asyncio.create_task(_refresh())

    return cached if cached is not None else []


def _fetch_market_sectors():
    import akshare as ak
    try:
        # 东方财富行业板块
        df = ak.stock_board_industry_name_em()
        if df is None or df.empty:
            return []
        
        result = []
        for _, row in df.iterrows():
            name = row.get("板块名称")
            change = row.get("涨跌幅")
            try:
                change = float(change)
            except:
                change = 0.0
            
            result.append({"name": name, "change": change})
            
        # Sort by name to keep the list stable
        result.sort(key=lambda x: x['name'])
        
        # Return all sectors (sorted by name) to ensure list stability
        # Users prefer a stable list over a jumping "hot" list
        return result

    except Exception as e:
        print(f"Error fetching sectors: {e}")
        return []

@router.get("/macro/calendar", response_model=List[MacroEvent])
async def get_macro_calendar(
    date: Optional[str] = None,
    countries: Optional[str] = None # comma separated
):
    def _fetch_events_akshare():
        try:
            import akshare as ak

            fetcher = getattr(ak, "news_economic_baidu", None)
            if not fetcher:
                return None
            df = fetcher()
            if df is None or df.empty:
                return None
            records = df.to_dict(orient="records")
            events = []
            for i, r in enumerate(records[:100]):
                event_name = r.get("title") or r.get("name") or r.get("event")
                event_time = r.get("time") or r.get("date") or r.get("datetime") or ""
                area = r.get("area") or r.get("country") or "CN"
                
                # Map area to code if possible, or just keep it
                country_code = "CN"
                if "美国" in area: country_code = "US"
                elif "欧元区" in area: country_code = "EU"
                elif "日本" in area: country_code = "JP"
                elif "英国" in area: country_code = "UK"
                elif "中国" in area: country_code = "CN"
                
                events.append(
                    {
                        "id": i + 1,
                        "time": str(event_time)[-5:] if event_time else "",
                        "country": country_code,
                        "currency": "",
                        "event": str(event_name) if event_name else "经济事件",
                        "importance": "medium",
                        "actual": str(r.get("actual") or ""),
                        "forecast": str(r.get("forecast") or ""),
                        "previous": str(r.get("previous") or ""),
                        "impact": "",
                    }
                )
            return events or None
        except Exception:
            return None

    now = time.monotonic()
    with _cache_lock:
        cached = _macro_calendar_cache["data"]
        ts = _macro_calendar_cache["ts"]
        refreshing = _macro_calendar_cache["refreshing"]
        next_refresh = _macro_calendar_cache["next"]

    if cached is None:
        cached = []

    if (cached is not None) and (now - ts < 300.0):
        events = cached
    else:
        events = cached
        if (not refreshing) and now >= next_refresh:
            with _cache_lock:
                if (not _macro_calendar_cache["refreshing"]) and time.monotonic() >= _macro_calendar_cache["next"]:
                    _macro_calendar_cache["refreshing"] = True

                    async def _refresh():
                        try:
                            try:
                                data = await asyncio.wait_for(asyncio.to_thread(_fetch_events_akshare), timeout=6.0)
                            except Exception:
                                with _cache_lock:
                                    _macro_calendar_cache["next"] = time.monotonic() + 60.0
                                return
                            if data:
                                with _cache_lock:
                                    _macro_calendar_cache["data"] = data
                                    _macro_calendar_cache["ts"] = time.monotonic()
                        finally:
                            with _cache_lock:
                                _macro_calendar_cache["refreshing"] = False

                    asyncio.create_task(_refresh())

    result = [dict(e) for e in (events or [])]
    if countries:
        country_list = [c.strip() for c in countries.split(",") if c.strip()]
        if country_list:
            result = [e for e in result if e.get("country") in country_list]
    return result

@router.get("/replay/kline")
async def get_replay_kline(
    symbol: str = "SH000001",
    period: str = "5", # 5 mins
    count: int = 240
):
    def _fetch_akshare():
        try:
            import akshare as ak

            df = ak.stock_zh_index_daily_em(symbol=symbol)
            if df is None or df.empty:
                return None
            df = df.tail(count)
            data = []
            for _, row in df.iterrows():
                time_label = row.get("date") or row.get("日期") or row.get("datetime")
                open_price = row.get("open") or row.get("开盘") or row.get("open_price")
                close_price = row.get("close") or row.get("收盘") or row.get("close_price")
                low_price = row.get("low") or row.get("最低") or row.get("low_price")
                high_price = row.get("high") or row.get("最高") or row.get("high_price")
                vol = row.get("volume") or row.get("成交量") or 0
                try:
                    o = float(open_price)
                    c = float(close_price)
                    l = float(low_price)
                    h = float(high_price)
                except Exception:
                    continue
                try:
                    v = int(float(vol)) if vol is not None else 0
                except Exception:
                    v = 0
                data.append({"time": str(time_label), "values": [round(o, 2), round(c, 2), round(l, 2), round(h, 2)], "vol": v})
            if not data:
                return None
            closes = [d["values"][1] for d in data]
            vols = [d["vol"] for d in data]
            max_price = max(closes)
            min_price = min(closes)
            max_vol = max(vols)
            key_frames = [
                {"label": "至暗时刻 (Lowest Price)", "index": closes.index(min_price), "value": str(min_price), "type": "min_price"},
                {"label": "高光时刻 (Highest Price)", "index": closes.index(max_price), "value": str(max_price), "type": "max_price"},
                {"label": "最大波动 (Max Vol)", "index": vols.index(max_vol), "value": str(max_vol), "type": "max_vol"},
            ]
            return {"data": data, "key_frames": key_frames}
        except Exception:
            return None

    cache_key = f"{symbol}|{period}|{count}"
    now = time.monotonic()
    with _cache_lock:
        cache = _get_cache(_replay_cache, cache_key)
        cached = cache["data"]
        ts = cache["ts"]
        refreshing = cache["refreshing"]
        next_refresh = cache["next"]

    if cached is not None:
        return cached

    if (not refreshing) and now >= next_refresh:
        with _cache_lock:
            cache = _get_cache(_replay_cache, cache_key)
            if (not cache["refreshing"]) and time.monotonic() >= cache["next"]:
                cache["refreshing"] = True

                async def _refresh():
                    try:
                        try:
                            data = await asyncio.wait_for(asyncio.to_thread(_fetch_akshare), timeout=8.0)
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

    return cached if cached is not None else None
