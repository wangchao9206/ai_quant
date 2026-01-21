
from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Optional
from pydantic import BaseModel
import asyncio
import random
import datetime
import math
import threading
import time

router = APIRouter()


_cache_lock = threading.Lock()
_quote_cache = {}
_orderbook_cache = {}
_intraday_cache = {}


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


def _trim_cache(bucket, max_size=200):
    if len(bucket) <= max_size:
        return
    items = sorted(bucket.items(), key=lambda kv: kv[1].get("ts", 0.0))
    for k, _ in items[: max(0, len(bucket) - max_size)]:
        bucket.pop(k, None)

# --- Models ---
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

class IntradayData(BaseModel):
    times: List[str]
    values: List[List[float]] # [[Open, Close, Low, High], ...]

# --- Routes ---

@router.get("/quote", response_model=StockQuote)
async def get_stock_quote(symbol: str):
    code = symbol.replace("SH", "").replace("SZ", "")
    now = time.monotonic()
    with _cache_lock:
        cache = _get_cache(_quote_cache, code)
        cached = cache["data"]
        ts = cache["ts"]
        refreshing = cache["refreshing"]
        next_refresh = cache["next"]

    if cached is not None and now - ts < 3.0:
        return cached

    if not refreshing and now >= next_refresh:
        with _cache_lock:
            cache = _get_cache(_quote_cache, code)
            if not cache["refreshing"] and time.monotonic() >= cache["next"]:
                cache["refreshing"] = True
                _trim_cache(_quote_cache)

                async def _refresh():
                    try:
                        try:
                            data = await asyncio.wait_for(asyncio.to_thread(_fetch_stock_quote_akshare, code), timeout=6.0)
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

    return cached if cached is not None else _mock_stock_quote(code)

@router.get("/orderbook", response_model=OrderBook)
async def get_orderbook(symbol: str):
    code = symbol.replace("SH", "").replace("SZ", "")
    now = time.monotonic()
    with _cache_lock:
        cache = _get_cache(_orderbook_cache, code)
        cached = cache["data"]
        ts = cache["ts"]
        refreshing = cache["refreshing"]
        next_refresh = cache["next"]

    if cached is not None and now - ts < 1.0:
        return cached

    if not refreshing and now >= next_refresh:
        with _cache_lock:
            cache = _get_cache(_orderbook_cache, code)
            if not cache["refreshing"] and time.monotonic() >= cache["next"]:
                cache["refreshing"] = True
                _trim_cache(_orderbook_cache)

                async def _refresh():
                    try:
                        try:
                            data = await asyncio.wait_for(asyncio.to_thread(_fetch_orderbook_akshare, code), timeout=6.0)
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

    return cached if cached is not None else _mock_orderbook(code)

@router.get("/intraday", response_model=IntradayData)
async def get_intraday(symbol: str):
    code = symbol.replace("SH", "").replace("SZ", "")
    now = time.monotonic()
    with _cache_lock:
        cache = _get_cache(_intraday_cache, code)
        cached = cache["data"]
        ts = cache["ts"]
        refreshing = cache["refreshing"]
        next_refresh = cache["next"]

    if cached is not None and now - ts < 30.0:
        return cached

    if not refreshing and now >= next_refresh:
        with _cache_lock:
            cache = _get_cache(_intraday_cache, code)
            if not cache["refreshing"] and time.monotonic() >= cache["next"]:
                cache["refreshing"] = True
                _trim_cache(_intraday_cache, max_size=50)

                async def _refresh():
                    try:
                        try:
                            data = await asyncio.wait_for(asyncio.to_thread(_fetch_intraday_akshare, code), timeout=10.0)
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

    return cached if cached is not None else _mock_intraday(code)


def _mock_stock_quote(code: str):
    base_price = 1850.00
    if code.startswith("00") or code.startswith("30"):
        base_price = 20.0
    current_price = base_price + random.uniform(-2, 2)
    last_close = base_price
    change_amt = current_price - last_close
    change_pct = (change_amt / last_close) * 100
    return {
        "name": "贵州茅台" if code == "600519" else f"模拟股票{code}",
        "code": code,
        "price": round(current_price, 2),
        "change": round(change_pct, 2),
        "changeAmt": round(change_amt, 2),
        "open": round(last_close * (1 + random.uniform(-0.01, 0.01)), 2),
        "high": round(current_price * 1.01, 2),
        "low": round(current_price * 0.99, 2),
        "vol": f"{random.randint(1, 100)}万",
        "amt": f"{random.randint(1, 100)}亿",
        "pe": round(random.uniform(10, 50), 2),
        "pb": round(random.uniform(1, 10), 2),
    }


def _fetch_stock_quote_akshare(code: str):
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
                "code": code,
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


def _mock_orderbook(code: str):
    price = 1850.00
    asks = [{"p": round(price + (i + 1) * 0.01, 2), "v": random.randint(1, 100)} for i in range(5)]
    bids = [{"p": round(price - i * 0.01, 2), "v": random.randint(1, 100)} for i in range(5)]
    return {"asks": asks[::-1], "bids": bids}


def _fetch_orderbook_akshare(code: str):
    import akshare as ak

    bid_ask_fetcher = getattr(ak, "stock_bid_ask_em", None)
    if not bid_ask_fetcher:
        return None

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
    if not rec:
        return None

    asks = []
    bids = []
    for i in range(5, 0, -1):
        ask_price = rec.get(f"卖{i}价") or rec.get(f"卖{i}")
        ask_vol = rec.get(f"卖{i}量") or rec.get(f"卖{i}量(手)")
        bid_price = rec.get(f"买{i}价") or rec.get(f"买{i}")
        bid_vol = rec.get(f"买{i}量") or rec.get(f"买{i}量(手)")
        ap = _to_float(ask_price)
        bp = _to_float(bid_price)
        av = int(_to_float(ask_vol) or 0)
        bv = int(_to_float(bid_vol) or 0)
        if ap is not None:
            asks.append({"p": round(ap, 2), "v": av})
        if bp is not None:
            bids.append({"p": round(bp, 2), "v": bv})

    if asks and bids:
        return {"asks": asks, "bids": bids}
    return None


def _mock_intraday(code: str):
    times = []
    values = []
    price = 100.0
    start_time = datetime.datetime.now().replace(hour=9, minute=30)
    for i in range(240):
        t = start_time + datetime.timedelta(minutes=i)
        times.append(t.strftime("%H:%M"))
        o = price
        c = price * (1 + random.uniform(-0.002, 0.002))
        l = min(o, c) * (1 - random.uniform(0, 0.001))
        h = max(o, c) * (1 + random.uniform(0, 0.001))
        values.append([round(o, 2), round(c, 2), round(l, 2), round(h, 2)])
        price = c
    return {"times": times, "values": values}


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
