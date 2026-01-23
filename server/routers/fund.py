from fastapi import APIRouter
from typing import List
from pydantic import BaseModel
import asyncio
import math
import threading
import time

router = APIRouter()


_fund_list_cache = {"data": None, "ts": 0.0, "refreshing": False, "next": 0.0}
_fund_list_lock = threading.Lock()


def _to_float(value):
    if value in (None, ""):
        return None
    try:
        v = float(str(value).replace("%", "").strip())
    except Exception:
        return None
    return v if math.isfinite(v) else None

class FundItem(BaseModel):
    key: str
    code: str
    name: str
    manager: str
    type: str
    nav: str
    return1y: float
    sharpe: float
    maxdd: float

def _fallback_fund_list() -> List[dict]:
    return [
        {
            "key": "1",
            "code": "000001",
            "name": "示例基金A",
            "manager": "-",
            "type": "Stock",
            "nav": "0.0000",
            "return1y": 0.0,
            "sharpe": 0.0,
            "maxdd": 0.0,
        },
        {
            "key": "2",
            "code": "000002",
            "name": "示例基金B",
            "manager": "-",
            "type": "Hybrid",
            "nav": "0.0000",
            "return1y": 0.0,
            "sharpe": 0.0,
            "maxdd": 0.0,
        },
    ]

@router.get("/list", response_model=List[FundItem])
async def get_fund_list():
    """
    获取基金列表
    """
    now = time.monotonic()
    with _fund_list_lock:
        cached = _fund_list_cache["data"]
        ts = _fund_list_cache["ts"]
        refreshing = _fund_list_cache["refreshing"]
        next_refresh = _fund_list_cache["next"]

    if cached is not None and now - ts < 60.0:
        return cached

    if not refreshing and now >= next_refresh:
        with _fund_list_lock:
            if not _fund_list_cache["refreshing"] and time.monotonic() >= _fund_list_cache["next"]:
                _fund_list_cache["refreshing"] = True

                async def _refresh():
                    try:
                        try:
                            data = await asyncio.wait_for(asyncio.to_thread(_fetch_fund_list_akshare), timeout=12.0)
                        except Exception:
                            with _fund_list_lock:
                                _fund_list_cache["next"] = time.monotonic() + 60.0
                            return
                        if data:
                            with _fund_list_lock:
                                _fund_list_cache["data"] = data
                                _fund_list_cache["ts"] = time.monotonic()
                        else:
                            with _fund_list_lock:
                                _fund_list_cache["next"] = time.monotonic() + 60.0
                    finally:
                        with _fund_list_lock:
                            _fund_list_cache["refreshing"] = False

                asyncio.create_task(_refresh())

    return cached if cached is not None else _fallback_fund_list()


def _fetch_fund_list_akshare():
    import akshare as ak

    fetchers = [
        getattr(ak, "fund_open_fund_rank_em", None),
        getattr(ak, "fund_open_fund_daily_em", None),
        getattr(ak, "fund_open_fund_info_em", None),
    ]
    for fetcher in fetchers:
        if fetcher is None:
            continue
        try:
            df = fetcher()
        except Exception:
            continue
        if df is None or df.empty:
            continue
        records = df.to_dict(orient="records")
        result = []
        for i, r in enumerate(records[:20]):
            code = r.get("基金代码") or r.get("代码") or r.get("fund_code") or r.get("code") or ""
            name = r.get("基金简称") or r.get("基金名称") or r.get("name") or r.get("基金") or ""
            manager = r.get("基金经理") or r.get("manager") or r.get("基金经理人") or "-"
            ftype = r.get("基金类型") or r.get("类型") or r.get("fund_type") or r.get("基金分类") or "Stock"
            nav_val = r.get("单位净值") or r.get("净值") or r.get("nav") or r.get("最新净值") or r.get("净值")
            return1y_val = r.get("近1年") or r.get("近一年") or r.get("近1年收益") or r.get("年化收益") or r.get("1Y") or r.get("收益率")
            sharpe_val = r.get("夏普") or r.get("Sharpe") or r.get("sharpe")
            maxdd_val = r.get("最大回撤") or r.get("max_drawdown")
            nav = _to_float(nav_val)
            return1y = _to_float(return1y_val)
            sharpe = _to_float(sharpe_val)
            maxdd = _to_float(maxdd_val)
            result.append({
                "key": str(i + 1),
                "code": str(code),
                "name": str(name) if name else str(code),
                "manager": str(manager),
                "type": str(ftype),
                "nav": f"{nav:.4f}" if nav is not None else "0.0000",
                "return1y": round(return1y if return1y is not None else 0.0, 1),
                "sharpe": round(sharpe if sharpe is not None else 0.0, 1),
                "maxdd": round(maxdd if maxdd is not None else 0.0, 1),
            })
        # Sort by code to keep the list stable (prevent jumping)
        result.sort(key=lambda x: x['code'])
        if result:
            return result
    return []
