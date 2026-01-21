from fastapi import APIRouter
from typing import List
from pydantic import BaseModel
import asyncio
import random
import math
import threading
import time

router = APIRouter()


_futures_cache = {"data": None, "ts": 0.0, "refreshing": False, "next": 0.0}
_options_cache = {"data": None, "ts": 0.0, "refreshing": False, "next": 0.0}
_summary_cache = {"data": None, "ts": 0.0, "refreshing": False, "next": 0.0}
_cache_lock = threading.Lock()


def _to_float(value):
    if value in (None, ""):
        return None
    try:
        v = float(str(value).replace("%", "").strip())
    except Exception:
        return None
    return v if math.isfinite(v) else None

class FutureItem(BaseModel):
    key: str
    symbol: str
    name: str
    price: float
    change: float
    volume: str
    openInt: str
    basis: float

class OptionItem(BaseModel):
    key: str
    callPrice: float
    callVol: int
    strike: int
    putVol: int
    putPrice: float

@router.get("/futures", response_model=List[FutureItem])
async def get_futures():
    now = time.monotonic()
    with _cache_lock:
        cached = _futures_cache["data"]
        ts = _futures_cache["ts"]
        refreshing = _futures_cache["refreshing"]
        next_refresh = _futures_cache["next"]

    if cached is not None and now - ts < 15.0:
        return cached

    if not refreshing and now >= next_refresh:
        with _cache_lock:
            if not _futures_cache["refreshing"] and time.monotonic() >= _futures_cache["next"]:
                _futures_cache["refreshing"] = True

                async def _refresh():
                    try:
                        try:
                            data = await asyncio.wait_for(asyncio.to_thread(_fetch_futures_akshare), timeout=10.0)
                        except Exception:
                            with _cache_lock:
                                _futures_cache["next"] = time.monotonic() + 30.0
                            return
                        if data:
                            with _cache_lock:
                                _futures_cache["data"] = data
                                _futures_cache["ts"] = time.monotonic()
                    finally:
                        with _cache_lock:
                            _futures_cache["refreshing"] = False

                asyncio.create_task(_refresh())

    return cached if cached is not None else _mock_futures()

@router.get("/options", response_model=List[OptionItem])
async def get_options():
    now = time.monotonic()
    with _cache_lock:
        cached = _options_cache["data"]
        ts = _options_cache["ts"]
        refreshing = _options_cache["refreshing"]
        next_refresh = _options_cache["next"]

    if cached is not None and now - ts < 30.0:
        return cached

    if not refreshing and now >= next_refresh:
        with _cache_lock:
            if not _options_cache["refreshing"] and time.monotonic() >= _options_cache["next"]:
                _options_cache["refreshing"] = True

                async def _refresh():
                    try:
                        try:
                            data = await asyncio.wait_for(asyncio.to_thread(_fetch_options_akshare), timeout=10.0)
                        except Exception:
                            with _cache_lock:
                                _options_cache["next"] = time.monotonic() + 45.0
                            return
                        if data:
                            with _cache_lock:
                                _options_cache["data"] = data
                                _options_cache["ts"] = time.monotonic()
                    finally:
                        with _cache_lock:
                            _options_cache["refreshing"] = False

                asyncio.create_task(_refresh())

    return cached if cached is not None else _mock_options()

@router.get("/summary")
async def get_derivatives_summary():
    now = time.monotonic()
    with _cache_lock:
        cached = _summary_cache["data"]
        ts = _summary_cache["ts"]
        refreshing = _summary_cache["refreshing"]
        next_refresh = _summary_cache["next"]

    if cached is not None and now - ts < 60.0:
        return cached

    if not refreshing and now >= next_refresh:
        with _cache_lock:
            if not _summary_cache["refreshing"] and time.monotonic() >= _summary_cache["next"]:
                _summary_cache["refreshing"] = True

                async def _refresh():
                    try:
                        try:
                            data = await asyncio.wait_for(asyncio.to_thread(_fetch_summary_akshare), timeout=10.0)
                        except Exception:
                            with _cache_lock:
                                _summary_cache["next"] = time.monotonic() + 60.0
                            return
                        if data:
                            with _cache_lock:
                                _summary_cache["data"] = data
                                _summary_cache["ts"] = time.monotonic()
                    finally:
                        with _cache_lock:
                            _summary_cache["refreshing"] = False

                asyncio.create_task(_refresh())

    return cached if cached is not None else _mock_summary()


def _mock_futures():
    items = [
        {"symbol": "IF2312", "name": "沪深300主力", "base_price": 3520},
        {"symbol": "IC2312", "name": "中证500主力", "base_price": 5430},
        {"symbol": "IM2312", "name": "中证1000主力", "base_price": 6100},
        {"symbol": "RB2401", "name": "螺纹钢2401", "base_price": 3850},
    ]
    result = []
    for i, item in enumerate(items):
        price = item["base_price"] + random.uniform(-50, 50)
        result.append({
            "key": str(i + 1),
            "symbol": item["symbol"],
            "name": item["name"],
            "price": round(price, 1),
            "change": round(random.uniform(-2, 2), 1),
            "volume": f"{random.randint(5, 150)}W",
            "openInt": f"{random.randint(1, 200)}W",
            "basis": round(random.uniform(-20, 20), 1),
        })
    return result


def _fetch_futures_akshare():
    import akshare as ak

    df = ak.futures_zh_spot()
    if df is None or df.empty:
        return []
    records = df.to_dict(orient="records")
    result = []
    for i, r in enumerate(records[:20]):
        symbol = r.get("合约") or r.get("symbol") or r.get("合约代码") or ""
        name = r.get("品种") or r.get("name") or r.get("品种名称") or ""
        price = r.get("最新价") or r.get("最新") or r.get("price") or 0
        change = r.get("涨跌幅") or r.get("涨跌") or r.get("change") or 0
        volume = r.get("成交量") or r.get("volume") or ""
        open_int = r.get("持仓量") or r.get("open_interest") or ""
        basis = r.get("基差") or r.get("basis") or 0
        price_f = _to_float(price)
        change_f = _to_float(change)
        basis_f = _to_float(basis)
        result.append({
            "key": str(i + 1),
            "symbol": str(symbol),
            "name": str(name),
            "price": round(price_f, 1) if price_f is not None else 0,
            "change": round(change_f, 1) if change_f is not None else 0,
            "volume": str(volume),
            "openInt": str(open_int),
            "basis": round(basis_f, 1) if basis_f is not None else 0,
        })
    return result


def _mock_options():
    strikes = [3500, 3550, 3600, 3650]
    result = []
    for i, k in enumerate(strikes):
        result.append({
            "key": str(i + 1),
            "strike": k,
            "callPrice": round(random.uniform(10, 200), 1),
            "callVol": random.randint(1000, 10000),
            "putPrice": round(random.uniform(10, 200), 1),
            "putVol": random.randint(1000, 10000),
        })
    return result


def _fetch_options_akshare():
    import akshare as ak

    df = ak.option_current_em()
    if df is None or df.empty:
        return []

    records = df.to_dict(orient="records")
    result = []
    for r in records[:20]:
        strike = r.get("行权价") or r.get("strike") or r.get("行权价(元)") or 0
        option_type = r.get("期权类型") or r.get("type") or ""
        price = r.get("最新价") or r.get("price") or 0
        vol = r.get("成交量") or r.get("volume") or 0
        strike_i = int(float(strike)) if _to_float(strike) is not None else 0
        price_f = _to_float(price)
        vol_i = int(_to_float(vol) or 0)
        if option_type in ["认购", "CALL", "C"]:
            result.append({
                "key": str(len(result) + 1),
                "strike": strike_i,
                "callPrice": round(price_f, 1) if price_f is not None else 0,
                "callVol": vol_i,
                "putPrice": 0,
                "putVol": 0,
            })
        elif option_type in ["认沽", "PUT", "P"]:
            result.append({
                "key": str(len(result) + 1),
                "strike": strike_i,
                "callPrice": 0,
                "callVol": 0,
                "putPrice": round(price_f, 1) if price_f is not None else 0,
                "putVol": vol_i,
            })
    return result[:12]


def _mock_summary():
    return {
        "basis": round(random.uniform(-5, 20), 2),
        "vix": round(random.uniform(15, 35), 1),
        "signal": "Gamma Scalping (Long Vol)",
    }


def _fetch_summary_akshare():
    result = _mock_summary()
    try:
        import akshare as ak

        df = ak.index_option_300index_qvix()
        if df is not None and not df.empty:
            latest = df.tail(1)
            val = latest.iloc[0].to_dict().get("close") or latest.iloc[0].to_dict().get("收盘")
            val_f = _to_float(val)
            if val_f is not None:
                result["vix"] = round(val_f, 1)
    except Exception:
        pass
    return result
