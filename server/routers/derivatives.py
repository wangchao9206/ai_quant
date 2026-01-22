from fastapi import APIRouter
from typing import List
from pydantic import BaseModel
import asyncio
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

    if cached is not None:
        return cached
    return []

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

    if cached is not None:
        return cached
    return []

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

    return cached if cached is not None else {"basis": 0.0, "vix": 0.0, "signal": "Neutral"}


def _fetch_futures_akshare():
    import akshare as ak

    df = ak.futures_zh_spot()
    if df is None or df.empty:
        return []
    records = df.to_dict(orient="records")

    rows = []
    for r in records:
        symbol = r.get("合约") or r.get("symbol") or r.get("合约代码") or ""
        symbol = str(symbol).strip()
        if not symbol:
            continue

        name = r.get("品种") or r.get("name") or r.get("品种名称") or ""
        price = r.get("最新价") or r.get("最新") or r.get("price") or 0
        change = r.get("涨跌幅") or r.get("涨跌") or r.get("change") or 0
        volume = r.get("成交量") or r.get("volume") or ""
        open_int = r.get("持仓量") or r.get("open_interest") or ""
        basis = r.get("基差") or r.get("basis") or 0

        price_f = _to_float(price)
        change_f = _to_float(change)
        basis_f = _to_float(basis)
        vol_score = _to_float(volume) or 0.0

        rows.append({
            "symbol": symbol,
            "name": str(name),
            "price": round(price_f, 1) if price_f is not None else 0,
            "change": round(change_f, 1) if change_f is not None else 0,
            "volume": str(volume),
            "openInt": str(open_int),
            "basis": round(basis_f, 1) if basis_f is not None else 0,
            "_vol": vol_score,
        })

    # Sort by symbol for stability
    rows.sort(key=lambda x: x["symbol"])

    result = []
    # Return all (or up to 100) to ensure stability. 
    # Users prefer a stable list.
    for i, r in enumerate(rows):
        r.pop("_vol", None)
        r["key"] = str(i + 1)
        result.append(r)
    return result


def _fetch_options_akshare():
    import akshare as ak

    df = ak.option_current_em()
    if df is None or df.empty:
        return []

    records = df.to_dict(orient="records")
    by_strike = {}
    for r in records:
        strike = r.get("行权价") or r.get("strike") or r.get("行权价(元)") or 0
        strike_f = _to_float(strike)
        if strike_f is None:
            continue
        strike_i = int(strike_f)

        option_type = str(r.get("期权类型") or r.get("type") or "").upper()
        price = r.get("最新价") or r.get("price") or 0
        vol = r.get("成交量") or r.get("volume") or 0

        price_f = _to_float(price) or 0.0
        vol_i = int(_to_float(vol) or 0)

        row = by_strike.get(strike_i)
        if row is None:
            row = {"strike": strike_i, "callPrice": 0.0, "callVol": 0, "putPrice": 0.0, "putVol": 0, "_score": 0}
            by_strike[strike_i] = row

        if option_type in ["认购", "CALL", "C"]:
            row["callPrice"] = round(price_f, 1)
            row["callVol"] = vol_i
        elif option_type in ["认沽", "PUT", "P"]:
            row["putPrice"] = round(price_f, 1)
            row["putVol"] = vol_i

        row["_score"] = row.get("callVol", 0) + row.get("putVol", 0)

    rows = list(by_strike.values())
    
    # Sort by strike to ensure stability
    # Users prefer a stable list over a jumping "hot" list
    rows.sort(key=lambda x: x.get("strike", 0))

    result = []
    # Return all options (or a large enough subset if too many)
    # Typically there are 20-50 strikes, which is manageable.
    for i, r in enumerate(rows):
        r.pop("_score", None)
        r["key"] = str(i + 1)
        result.append(r)
        
    return result


def _fetch_summary_akshare():
    result = {
        "basis": 0.0,
        "vix": 0.0,
        "signal": "Neutral",
    }
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
