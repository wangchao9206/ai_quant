
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
from core.tdx_client import tdx_client
from core.tdx_http_client import tdx_http_client

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
    # TODO: Implement stock list fetch via tdx-api or AkShare
    # For now, return empty to avoid blocking if tdx_client is removed
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



def _map_tdx_http_quote(data: Dict, code: str, display: str, exchange: Optional[str] = None):
    """Adapter for tdx-api (Go) JSON response."""
    try:
        # Handle potential wrapper
        items = []
        if "data" in data and isinstance(data["data"], list):
            items = data["data"]
        elif isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            # Maybe it's a single item or has data dict
            if "data" in data and isinstance(data["data"], dict):
                items = [data["data"]]
            else:
                items = [data]
        
        if not items:
            return None
            
        # Select best match if multiple
        target_item = items[0]
        if len(items) > 1 and exchange:
            # 0=SZ, 1=SH
            target_ex = 1 if exchange == "SH" else 0
            for item in items:
                if item.get("Exchange") == target_ex:
                    target_item = item
                    break
        
        item = target_item
        
        # Check for K dict (standard tdx-api format)
        # {"Exchange":0,"Code":"000001","K":{"Last":11070...}...}
        k_data = item.get("K", {})
        
        # Helper to get value from K or top level
        def get_val(keys, default=0):
            for k in keys:
                if k in k_data:
                    return k_data[k]
                if k in item:
                    return item[k]
            return default

        # Price scaling logic
        # tdx-api often returns raw integer values (e.g. 11070 for 11.07)
        # We assume factor of 1000 for stocks if looks like integer
        raw_price = float(get_val(["Last", "Price", "price", "current", "Close"], 0))
        
        if raw_price == 0:
            return None
            
        # Heuristic scaling
        # If price > 0 and looks like integer (no decimals in source, though float() adds .0)
        # We can't know for sure if it's integer in JSON without inspecting raw string, 
        # but tdx-api "Last": 11070 implies integer.
        # PingAn 11.07 -> 11070. Factor 1000.
        # Index 3300.00 -> 3300000? or 330000?
        # Let's assume factor 1000 for now as it's common in TDX raw.
        # Exception: if value is small?
        price = raw_price / 1000.0

        last_close = float(get_val(["LastClose", "last_close", "pre_close"], raw_price)) / 1000.0
        open_p = float(get_val(["Open", "open"], 0)) / 1000.0
        high = float(get_val(["High", "high"], 0)) / 1000.0
        low = float(get_val(["Low", "low"], 0)) / 1000.0
        
        # Volume usually in "TotalHand" (lots) or "Vol"
        # item["TotalHand"] = 496954 (lots?)
        # item["Amount"] = 549842752 (raw value?)
        vol = str(get_val(["TotalHand", "Vol", "vol", "volume"], 0))
        amt = str(get_val(["Amount", "amount"], 0))
        
        # Change
        # Rate: 0.09 (Percent?)
        change_pct = float(get_val(["Rate", "rate", "change_pct"], 0))
        
        # If rate is small (0.09), it might be 0.09% or 9%?
        # PingAn 11.05 -> 11.07 is +0.02. 0.02/11.05 = 0.18%.
        # If Rate is 0.09, maybe it's 0.09%?
        # Let's verify calculation
        if last_close > 0:
            calc_change = ((price - last_close) / last_close) * 100
            # If calculated change is close to Rate, trust Rate?
            # Or just use calculated.
            change_pct = calc_change
        
        change_amt = price - last_close

        name = item.get("Name") or item.get("name") or code
        # Name might need decoding if it's raw bytes? 
        # Requests .json() handles utf-8. tdx-api usually returns utf-8.
        
        return {
            "name": str(name),
            "code": display or code,
            "price": round(price, 2),
            "change": round(change_pct, 2),
            "changeAmt": round(change_amt, 2),
            "open": round(open_p, 2),
            "high": round(high, 2),
            "low": round(low, 2),
            "vol": vol,
            "amt": amt,
            "pe": 0.0,
            "pb": 0.0,
        }
    except Exception as e:
        print(f"Error mapping tdx-api quote: {e}")
        return None

def _fetch_stock_quote_tdx(code: str, exchange: Optional[str] = None, display: Optional[str] = None):
    # 1. Try Local TDX HTTP API First (User Preference)
    # User requested integration of https://github.com/oficcejo/tdx-api
    if tdx_http_client.is_available():
        try:
            # tdx-api typically runs on localhost:8080
            data = tdx_http_client.get_quote(code)
            if data:
                mapped = _map_tdx_http_quote(data, code, display, exchange)
                if mapped:
                    return mapped
        except Exception as e:
            logger.error(f"TDX HTTP fallback error: {e}")
            pass

    # 2. Try Internal TDX Client (Fallback)
    # DISABLED BY USER REQUEST - REMOVING BLOCKING TDX CLIENT
    
    # 3. Final Fallback to AkShare (HTTP)
    return _fetch_stock_quote_akshare(code, exchange, display)

def _fetch_orderbook_tdx(code: str, exchange: Optional[str] = None):
    # 1. Try HTTP API (Prioritized)
    if tdx_http_client.is_available():
        try:
            # Construct code with prefix if possible
            target_code = code
            if exchange:
                target_code = f"{exchange}{code}"
                
            data = tdx_http_client.get_quote(target_code)
            if not data and target_code != code:
                # Retry without prefix
                data = tdx_http_client.get_quote(code)
                
            if data:
                # Handle wrapper
                item = None
                items = []
                if "data" in data and isinstance(data["data"], list):
                    items = data["data"]
                elif isinstance(data, list):
                    items = data
                elif isinstance(data, dict):
                    if "data" in data and isinstance(data["data"], dict):
                        items = [data["data"]]
                    else:
                        items = [data]
                
                if items:
                    item = items[0]
                    # Filter by exchange if needed
                    if len(items) > 1 and exchange:
                         target_ex = 1 if exchange == "SH" else 0
                         for it in items:
                             if it.get("Exchange") == target_ex:
                                 item = it
                                 break
                    
                    bids = []
                    asks = []
                    
                    # Parse BuyLevel / SellLevel (tdx-api format)
                    # "BuyLevel":[{"Buy":true,"Price":10990,"Number":2423}...]
                    # "SellLevel":[{"Buy":false,"Price":11000,"Number":4822}...]
                    
                    buy_levels = item.get("BuyLevel", [])
                    sell_levels = item.get("SellLevel", [])
                    
                    for level in buy_levels:
                        p = float(level.get("Price", 0)) / 1000.0
                        v = float(level.get("Number", 0)) # Volume
                        if p > 0:
                            bids.append({"p": p, "v": v})
                            
                    for level in sell_levels:
                        p = float(level.get("Price", 0)) / 1000.0
                        v = float(level.get("Number", 0))
                        if p > 0:
                            asks.append({"p": p, "v": v})
                            
                    # If empty, maybe fall back to Bid1...Bid5 check (legacy format?)
                    if not bids and not asks:
                         k_data = item.get("K", {})
                         def get_val(keys, default=0):
                             for k in keys:
                                 if k in k_data: return k_data[k]
                                 if k in item: return item[k]
                             return default

                         for i in range(1, 6):
                             bp = float(get_val([f"Bid{i}"])) / 1000.0
                             bv = float(get_val([f"BidVol{i}"]))
                             if bp > 0: bids.append({"p": bp, "v": bv})
                             
                             ap = float(get_val([f"Ask{i}"])) / 1000.0
                             av = float(get_val([f"AskVol{i}"]))
                             if ap > 0: asks.append({"p": ap, "v": av})
                    
                    # Ensure correct order
                    # Bids: Descending (Highest buy first) - usually already sorted
                    # Asks: Ascending (Lowest sell first)
                    
                    return {
                        "bids": bids,
                        "asks": asks
                    }
        except Exception as e:
            logger.error(f"TDX HTTP orderbook error: {e}")
            pass

    return None

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
                            if parsed["kind"] == "index":
                                data = await asyncio.wait_for(asyncio.to_thread(_fetch_index_quote_akshare, parsed["code"], parsed["exchange"], parsed["display"]), timeout=6.0)
                            else:
                                # Use prioritized fetch strategy: tdx-api -> internal tdx (disabled) -> AkShare
                                data = await asyncio.to_thread(_fetch_stock_quote_tdx, parsed["code"], parsed["exchange"], parsed["display"])
                                
                                if not data:
                                    logger.warning(f"TDX failed for {symbol}, trying AkShare fallback")
                                    # Double check fallback (though _fetch_stock_quote_tdx already does it)
                                    try:
                                        data = await asyncio.wait_for(asyncio.to_thread(_fetch_stock_quote_akshare, parsed["code"], parsed["exchange"], parsed["display"]), timeout=8.0)
                                    except Exception as e:
                                        logger.error(f"AkShare fallback timeout/error: {e}")
                                        data = None
                        except Exception as e:
                            logger.error(f"Fetch quote error for {symbol}: {e}")
                            # Final attempt with AkShare
                            try:
                                data = await asyncio.wait_for(asyncio.to_thread(_fetch_stock_quote_akshare, parsed["code"], parsed["exchange"], parsed["display"]), timeout=8.0)
                            except:
                                data = None
                            
                            if not data:
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

def _fetch_orderbook_tdx(code: str):
    # 1. Try HTTP API (Prioritized)
    if tdx_http_client.is_available():
        try:
            logger.info(f"Fetching orderbook via TDX HTTP for {code}")
            data = tdx_http_client.get_quote(code)
            if data:
                # Handle wrapper
                item = None
                items = []
                if "data" in data and isinstance(data["data"], list):
                    items = data["data"]
                elif isinstance(data, list):
                    items = data
                elif isinstance(data, dict):
                    if "data" in data and isinstance(data["data"], dict):
                        items = [data["data"]]
                    else:
                        items = [data]
                
                if items:
                    item = items[0]
                    bids = []
                    asks = []
                    
                    k_data = item.get("K", {})
                    def get_val(keys, default=0):
                        for k in keys:
                            if k in k_data: return k_data[k]
                            if k in item: return item[k]
                        return default

                    for i in range(1, 6):
                        # Bid
                        bp = float(get_val([f"Bid{i}"])) / 1000.0
                        bv = float(get_val([f"BidVol{i}"]))
                        if bp > 0:
                            bids.append({"p": bp, "v": bv})
                        
                        # Ask
                        ap = float(get_val([f"Ask{i}"])) / 1000.0
                        av = float(get_val([f"AskVol{i}"]))
                        if ap > 0:
                            asks.append({"p": ap, "v": av})
                    
                    # Ensure correct order
                    # Bids: Descending (Highest buy first)
                    # Asks: Ascending (Lowest sell first)
                    # Usually API returns them in level order 1-5
                    
                    return {"asks": asks, "bids": bids}
        except Exception:
            pass

    # 2. Internal client (Disabled)
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
                            if parsed["kind"] == "index":
                                data = await asyncio.wait_for(
                                    asyncio.to_thread(_fetch_index_kline_akshare, parsed["code"], parsed["exchange"]),
                                    timeout=8.0,
                                )
                            else:
                                # Prioritize TDX HTTP
                                data = None
                                if tdx_http_client.is_available():
                                    try:
                                        m_data = await asyncio.to_thread(tdx_http_client.get_minute, parsed["code"])
                                        if m_data and m_data["values"]:
                                            data = m_data
                                    except Exception:
                                        pass

                                if not data:
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
