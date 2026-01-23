
from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Optional
from pydantic import BaseModel
import asyncio
import datetime
import threading
import time
import logging
from core.database import get_market_collection

router = APIRouter()
logger = logging.getLogger(__name__)



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

def _fallback_indices() -> List[Dict]:
    return [
        {"name": "上证指数", "value": 0.0, "change": 0.0, "volume": "0"},
        {"name": "深证成指", "value": 0.0, "change": 0.0, "volume": "0"},
        {"name": "创业板指", "value": 0.0, "change": 0.0, "volume": "0"},
        {"name": "科创50", "value": 0.0, "change": 0.0, "volume": "0"},
    ]

def _fallback_sectors() -> List[Dict]:
    return [
        {"name": "金融", "change": 0.0},
        {"name": "科技", "change": 0.0},
        {"name": "消费", "change": 0.0},
        {"name": "医药", "change": 0.0},
        {"name": "能源", "change": 0.0},
    ]

# --- Routes ---

@router.get("/indices", response_model=List[MarketIndex])
async def get_market_indices():
    logger.info("API Request: /indices")
    now = time.monotonic()
    with _cache_lock:
        cached = _indices_cache["data"]
        ts = _indices_cache["ts"]
        refreshing = _indices_cache["refreshing"]
        next_refresh = _indices_cache["next"]

    if cached is not None and now - ts < 10.0:
        logger.debug("Cache hit for /indices")
        return cached

    if not refreshing and now >= next_refresh:
        with _cache_lock:
            if not _indices_cache["refreshing"] and time.monotonic() >= _indices_cache["next"]:
                _indices_cache["refreshing"] = True
                
                async def _refresh():
                    try:
                        logger.info("Refreshing indices")
                        data = await asyncio.wait_for(asyncio.to_thread(_fetch_indices), timeout=10.0)
                        if data:
                            with _cache_lock:
                                _indices_cache["data"] = data
                                _indices_cache["ts"] = time.monotonic()
                            logger.info("Indices refreshed successfully")
                        else:
                            with _cache_lock:
                                _indices_cache["next"] = time.monotonic() + 10.0
                    except Exception as e:
                        logger.error(f"Failed to fetch indices: {e}")
                        with _cache_lock:
                            _indices_cache["next"] = time.monotonic() + 10.0
                    finally:
                        with _cache_lock:
                            _indices_cache["refreshing"] = False
                            
                asyncio.create_task(_refresh())

    return cached if cached is not None else _fallback_indices()

def _fetch_indices() -> List[Dict]:
    targets = [
        ("000001", "上证指数"),
        ("399001", "深证成指"),
        ("399006", "创业板指"),
        ("000688", "科创50"),
    ]
    try:
        col = get_market_collection()
    except Exception as e:
        logger.warning("Mongo market collection unavailable: %s", e)
        return []

    results = []
    for code, name in targets:
        try:
            docs = list(
                col.find(
                    {"asset_type": "stock", "symbol": code, "period": "daily"},
                    {"_id": 0, "ts": 1, "close_price": 1, "open_price": 1, "amount": 1, "volume": 1},
                )
                .sort("ts", -1)
                .limit(2)
            )
        except Exception:
            docs = []
        if not docs:
            continue
        latest = docs[0]
        prev = docs[1] if len(docs) > 1 else docs[0]
        price = latest.get("close_price") or latest.get("open_price") or 0
        last_close = prev.get("close_price") or price or 0
        try:
            price = float(price)
        except Exception:
            price = 0.0
        try:
            last_close = float(last_close)
        except Exception:
            last_close = price
        change_pct = ((price - last_close) / last_close * 100) if last_close else 0.0
        amount = latest.get("amount") or latest.get("volume") or 0
        try:
            amount = float(amount)
        except Exception:
            amount = 0.0
        vol_str = f"{amount/100000000:.2f}亿" if amount > 100000000 else f"{amount:.0f}"
        results.append({
            "name": name,
            "value": round(price, 2),
            "change": round(change_pct, 2),
            "volume": vol_str,
        })
    return results

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
                        else:
                            with _cache_lock:
                                _sectors_cache["next"] = time.monotonic() + 20.0
                    finally:
                        with _cache_lock:
                            _sectors_cache["refreshing"] = False

                asyncio.create_task(_refresh())

    return cached if cached is not None else _fallback_sectors()


def _fetch_market_sectors():
    return []

@router.get("/macro/calendar", response_model=List[MacroEvent])
async def get_macro_calendar(
    date: Optional[str] = None,
    countries: Optional[str] = None # comma separated
):
    logger.info(f"API Request: /macro/calendar date={date} countries={countries}")
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

    return cached if cached is not None else None
