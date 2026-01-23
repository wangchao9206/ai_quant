
from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Optional
from pydantic import BaseModel
import asyncio
import datetime
import math
import re
import threading
import time
import logging
from core.database import get_market_collection

router = APIRouter()
logger = logging.getLogger(__name__)



_cache_lock = threading.Lock()
_quote_cache = {}
_orderbook_cache = {}
_intraday_cache = {}
_stock_list_cache = {"data": None, "ts": 0.0, "refreshing": False, "next": 0.0}

_INDEX_CODES = {
    "000001", "000300", "000905", "399001", "399006", "399005", "000016", "000688"
}
_INDEX_NAME_MAP = {
    "000001": "上证指数",
    "000300": "沪深300",
    "000905": "中证500",
    "399001": "深证成指",
    "399006": "创业板指",
    "399005": "中小板指",
    "000016": "上证50",
    "000688": "科创50",
}

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

def _fetch_stock_list_mongo():
    try:
        col = get_market_collection()
    except Exception:
        return []
    try:
        symbols = col.distinct("symbol", {"asset_type": "stock", "period": "daily"})
    except Exception:
        return []
    results = []
    for s in symbols:
        if not s:
            continue
        code = str(s)
        name = _INDEX_NAME_MAP.get(code, code)
        results.append({"code": code, "name": name})
    return results

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
                            data = await asyncio.to_thread(_fetch_stock_list_mongo)
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
    q_digits = re.sub(r"\D", "", q_str)
    results = []
    for item in data:
        code = str(item.get("code") or "")
        name = str(item.get("name") or "")
        candidates = [code, name, f"sh{code}", f"sz{code}", f"bj{code}"]
        candidates = [c.lower() for c in candidates if c]
        matched = False
        if q_str and any(q_str in c for c in candidates):
            matched = True
        if not matched and q_digits and q_digits in code:
            matched = True
        if matched:
            results.append(item)
        if len(results) >= 10:
            break
            
    return results
def _fetch_latest_docs(asset_type: str, symbol: str, period: str, limit: int = 2):
    try:
        col = get_market_collection()
    except Exception:
        return []
    try:
        return list(
            col.find(
                {"asset_type": asset_type, "symbol": symbol, "period": period},
                {
                    "_id": 0,
                    "ts": 1,
                    "open_price": 1,
                    "high_price": 1,
                    "low_price": 1,
                    "close_price": 1,
                    "volume": 1,
                    "amount": 1,
                    "asks": 1,
                    "bids": 1,
                },
            )
            .sort("ts", -1)
            .limit(int(limit))
        )
    except Exception:
        return []


def _fetch_stock_quote_mongo(code: str, display: Optional[str] = None):
    docs = _fetch_latest_docs("stock", code, "daily", limit=2)
    if not docs:
        docs = _fetch_latest_docs("stock", code, "1", limit=2)
    if not docs:
        return None
    latest = docs[0]
    prev = docs[1] if len(docs) > 1 else latest
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
    change_amt = price - last_close
    open_p = latest.get("open_price") or price
    high = latest.get("high_price") or price
    low = latest.get("low_price") or price
    try:
        open_p = float(open_p)
    except Exception:
        open_p = price
    try:
        high = float(high)
    except Exception:
        high = price
    try:
        low = float(low)
    except Exception:
        low = price
    vol = latest.get("volume")
    amt = latest.get("amount")
    return {
        "name": str(display or code),
        "code": str(display or code),
        "price": round(price, 2),
        "change": round(change_pct, 2),
        "changeAmt": round(change_amt, 2),
        "open": round(open_p, 2),
        "high": round(high, 2),
        "low": round(low, 2),
        "vol": "" if vol is None else str(vol),
        "amt": "" if amt is None else str(amt),
        "pe": 0.0,
        "pb": 0.0,
    }


def _normalize_orderbook_side(raw):
    if not isinstance(raw, list):
        return []
    normalized = []
    for item in raw:
        if isinstance(item, dict):
            p = item.get("p") if "p" in item else item.get("price")
            v = item.get("v") if "v" in item else item.get("volume")
            try:
                p = float(p)
            except Exception:
                p = None
            try:
                v = float(v)
            except Exception:
                v = 0.0
            if p is None:
                continue
            normalized.append({"p": p, "v": v})
        elif isinstance(item, (list, tuple)) and len(item) >= 2:
            try:
                p = float(item[0])
            except Exception:
                p = None
            try:
                v = float(item[1])
            except Exception:
                v = 0.0
            if p is None:
                continue
            normalized.append({"p": p, "v": v})
    return normalized


def _fetch_orderbook_mongo(code: str):
    docs = _fetch_latest_docs("stock", code, "orderbook", limit=1)
    if not docs:
        return None
    latest = docs[0]
    asks = _normalize_orderbook_side(latest.get("asks"))
    bids = _normalize_orderbook_side(latest.get("bids"))
    if not asks and not bids:
        return None
    return {"asks": asks, "bids": bids}


def _fetch_intraday_mongo(code: str):
    docs = _fetch_latest_docs("stock", code, "1", limit=240)
    if not docs:
        return None
    docs.reverse()
    times = []
    values = []
    for doc in docs:
        ts = doc.get("ts")
        if ts is None:
            continue
        try:
            dt = datetime.datetime.fromisoformat(str(ts))
            t_str = dt.strftime("%H:%M")
        except Exception:
            t_str = str(ts)[-5:]
        o = doc.get("open_price")
        c = doc.get("close_price")
        l = doc.get("low_price")
        h = doc.get("high_price")
        if o is None or c is None or l is None or h is None:
            continue
        try:
            values.append([round(float(o), 2), round(float(c), 2), round(float(l), 2), round(float(h), 2)])
            times.append(t_str)
        except Exception:
            continue
    if not times or not values:
        return None
    return {"times": times, "values": values}

@router.get("/quote", response_model=StockQuote)
async def get_stock_quote(symbol: str):
    logger.info(f"API Request: /quote?symbol={symbol}")
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
        logger.debug(f"Cache hit for {symbol}")
        return cached

    if not refreshing and now >= next_refresh:
        with _cache_lock:
            cache = _get_cache(_quote_cache, cache_key)
            if not cache["refreshing"] and time.monotonic() >= cache["next"]:
                cache["refreshing"] = True
                _trim_cache(_quote_cache)

                async def _refresh():
                    try:
                        logger.info(f"Refreshing quote for {symbol} (kind={parsed['kind']})")
                        try:
                            data = await asyncio.to_thread(_fetch_stock_quote_mongo, parsed["code"], parsed["display"])
                        except Exception as e:
                            logger.error(f"Fetch quote error for {symbol}: {e}")
                            with _cache_lock:
                                cache["next"] = time.monotonic() + 5.0
                            return
                        if data:
                            with _cache_lock:
                                cache["data"] = data
                                cache["ts"] = time.monotonic()
                            logger.info(f"Quote refreshed for {symbol}")
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
    logger.warning(f"Stock quote not found for {symbol}")
    raise HTTPException(status_code=404, detail="Stock quote not found")

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
                                data = await asyncio.to_thread(_fetch_orderbook_mongo, parsed["code"])
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
    logger.info(f"API Request: /intraday?symbol={symbol}")
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
                            data = await asyncio.to_thread(_fetch_intraday_mongo, parsed["code"])
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
