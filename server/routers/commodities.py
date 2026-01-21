from fastapi import APIRouter
from typing import List
from pydantic import BaseModel
import asyncio
import random
import math
import threading
import time

router = APIRouter()


_commodities_cache = {"data": None, "ts": 0.0, "refreshing": False, "next": 0.0}
_commodities_lock = threading.Lock()


def _to_float(value):
    if value in (None, ""):
        return None
    try:
        v = float(str(value).replace("%", "").strip())
    except Exception:
        return None
    return v if math.isfinite(v) else None

class CommodityItem(BaseModel):
    name: str
    price: float
    change: float
    unit: str

class ChartData(BaseModel):
    times: List[str]
    values: List[float]

class MacroItem(BaseModel):
    name: str
    value: str
    change: str
    percent: int
    status: str # low, high, stable

class AlertItem(BaseModel):
    id: int
    message: str
    level: str

class InventoryItem(BaseModel):
    name: str
    value: str
    status: str

@router.get("/list", response_model=List[CommodityItem])
async def get_commodities():
    """
    获取商品行情列表
    """
    now = time.monotonic()
    with _commodities_lock:
        cached = _commodities_cache["data"]
        ts = _commodities_cache["ts"]
        refreshing = _commodities_cache["refreshing"]
        next_refresh = _commodities_cache["next"]

    if cached is not None and now - ts < 15.0:
        return cached

    if not refreshing and now >= next_refresh:
        with _commodities_lock:
            if not _commodities_cache["refreshing"] and time.monotonic() >= _commodities_cache["next"]:
                _commodities_cache["refreshing"] = True

                async def _refresh():
                    try:
                        try:
                            data = await asyncio.wait_for(asyncio.to_thread(_fetch_commodities_akshare), timeout=8.0)
                        except Exception:
                            with _commodities_lock:
                                _commodities_cache["next"] = time.monotonic() + 30.0
                            return
                        if data:
                            with _commodities_lock:
                                _commodities_cache["data"] = data
                                _commodities_cache["ts"] = time.monotonic()
                    finally:
                        with _commodities_lock:
                            _commodities_cache["refreshing"] = False

                asyncio.create_task(_refresh())

    return cached if cached is not None else _mock_commodities()


def _mock_commodities():
    items = [
        {"name": "Gold (伦敦金)", "base": 2045, "unit": "USD/oz"},
        {"name": "Silver (白银)", "base": 24, "unit": "USD/oz"},
        {"name": "Copper (沪铜)", "base": 68500, "unit": "CNY/T"},
    ]
    result = []
    for item in items:
        result.append({
            "name": item["name"],
            "price": round(item["base"] * (1 + random.uniform(-0.01, 0.01)), 2),
            "change": round(random.uniform(-1.5, 1.5), 2),
            "unit": item["unit"],
        })
    return result


def _fetch_commodities_akshare():
    import akshare as ak

    fetcher = getattr(ak, "futures_zh_spot", None)
    if not fetcher:
        return []

    df = fetcher()
    if df is None or df.empty:
        return []

    records = df.to_dict(orient="records")
    targets = [
        {"name": "Gold (伦敦金)", "keywords": ["黄金", "金", "AU"], "unit": "USD/oz", "base": 2045},
        {"name": "Silver (白银)", "keywords": ["白银", "银", "AG"], "unit": "USD/oz", "base": 24},
        {"name": "Copper (沪铜)", "keywords": ["铜", "CU"], "unit": "CNY/T", "base": 68500},
    ]
    result = []
    for t in targets:
        matched = None
        for r in records:
            name = str(r.get("品种") or r.get("名称") or r.get("合约") or r.get("symbol") or "")
            if any(k in name for k in t["keywords"]):
                matched = r
                break
        price_val = None
        change_val = None
        if matched:
            price_val = matched.get("最新价") or matched.get("最新") or matched.get("price") or matched.get("现价")
            change_val = matched.get("涨跌幅") or matched.get("涨跌") or matched.get("change")
        price = _to_float(price_val)
        change = _to_float(change_val)
        result.append({
            "name": t["name"],
            "price": round(price if price is not None else t["base"] * (1 + random.uniform(-0.01, 0.01)), 2),
            "change": round(change if change is not None else random.uniform(-1.5, 1.5), 2),
            "unit": t["unit"],
        })
    return result

@router.get("/chart", response_model=ChartData)
async def get_commodity_chart(timeframe: str = "1H"):
    """
    获取商品走势图
    """
    timeframe_map = {
        "1H": ['09:00', '10:00', '11:00', '13:00', '14:00', '15:00'],
        "4H": ['09:00', '11:00', '13:00', '15:00'],
        "1D": ['09:00', '10:30', '13:00', '14:30', '15:00']
    }
    times = timeframe_map.get(timeframe, timeframe_map["1H"])
    values = []
    base = 2040
    for _ in range(len(times)):
        base += random.uniform(-5, 5)
        values.append(round(base, 2))
    return {"times": times, "values": values}

@router.get("/macro", response_model=List[MacroItem])
async def get_macro_drivers():
    """
    获取宏观驱动因子
    """
    return [
        {
            "name": "美元指数 (DXY)", 
            "value": "103.5", 
            "change": "-0.2%", 
            "percent": 70, 
            "status": "low"
        },
        {
            "name": "美债收益率 (10Y)", 
            "value": "4.12%", 
            "change": "+1.2%", 
            "percent": 85, 
            "status": "high"
        },
        {
            "name": "通胀预期 (Breakeven)", 
            "value": "2.3%", 
            "change": "Stable", 
            "percent": 45, 
            "status": "stable"
        }
    ]

@router.get("/alerts", response_model=List[AlertItem])
async def get_commodity_alerts():
    alerts = [
        {
            "id": 1,
            "message": "监测到黄金/白银比价偏离历史均值 2.0 个标准差",
            "level": "warning"
        },
        {
            "id": 2,
            "message": "铜库存下降触发供给收缩信号",
            "level": "info"
        }
    ]
    return alerts

@router.get("/inventory", response_model=List[InventoryItem])
async def get_inventory_monitor():
    return [
        {"name": "LME 铜库存", "value": "18.5万吨", "status": "low"},
        {"name": "COMEX 黄金库存", "value": "2,100万盎司", "status": "stable"}
    ]
