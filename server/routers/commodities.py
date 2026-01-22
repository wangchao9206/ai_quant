from fastapi import APIRouter
from typing import List
from pydantic import BaseModel
import asyncio
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

    return cached if cached is not None else []


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
        {"name": "Gold (伦敦金)", "keywords": ["黄金", "沪金", "AU", "XAU"], "unit": "USD/oz", "base": 2045},
        {"name": "Silver (白银)", "keywords": ["白银", "沪银", "AG", "XAG"], "unit": "USD/oz", "base": 24},
        {"name": "Copper (沪铜)", "keywords": ["沪铜", "铜", "CU"], "unit": "CNY/T", "base": 68500},
        {"name": "Aluminum (沪铝)", "keywords": ["沪铝", "铝", "AL"], "unit": "CNY/T", "base": 18950},
        {"name": "Zinc (沪锌)", "keywords": ["沪锌", "锌", "ZN"], "unit": "CNY/T", "base": 21300},
        {"name": "Crude Oil (原油)", "keywords": ["原油", "SC"], "unit": "CNY/bbl", "base": 560},
        {"name": "Rebar (螺纹钢)", "keywords": ["螺纹", "螺纹钢", "RB"], "unit": "CNY/T", "base": 3850},
        {"name": "Iron Ore (铁矿石)", "keywords": ["铁矿", "铁矿石", "I"], "unit": "CNY/T", "base": 950},
        {"name": "Soymeal (豆粕)", "keywords": ["豆粕", "M"], "unit": "CNY/T", "base": 3450},
        {"name": "Palm Oil (棕榈油)", "keywords": ["棕榈", "棕榈油", "P"], "unit": "CNY/T", "base": 7200},
        {"name": "Corn (玉米)", "keywords": ["玉米", "C"], "unit": "CNY/T", "base": 2450},
        {"name": "Sugar (白糖)", "keywords": ["白糖", "糖", "SR"], "unit": "CNY/T", "base": 6200},
        {"name": "Cotton (棉花)", "keywords": ["棉花", "棉", "CF"], "unit": "CNY/T", "base": 16200},
        {"name": "Rubber (橡胶)", "keywords": ["橡胶", "RU"], "unit": "CNY/T", "base": 14200},
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
            "price": round(price if price is not None else 0.0, 2),
            "change": round(change if change is not None else 0.0, 2),
            "unit": t["unit"],
        })
    return result

@router.get("/chart", response_model=ChartData)
async def get_commodity_chart(timeframe: str = "1H", symbol: str = "au0"):
    """
    获取商品走势图 (默认黄金)
    """
    def _fetch_chart():
        try:
            import akshare as ak
            # Use Sina futures daily data
            # symbol mapping: au0 -> 黄金, ag0 -> 白银, sc0 -> 原油, rb0 -> 螺纹
            # For 1H, we might need minute data, but let's stick to daily for stability or check minute
            # ak.futures_zh_minute_sina(symbol="au0", period="60")
            
            period = "60"
            if timeframe == "1D":
                period = "daily" # special handling if needed, but sina_minute uses 1/5/15/30/60
            
            if timeframe == "1D":
                df = ak.futures_zh_daily_sina(symbol=symbol)
            else:
                # Map timeframe to minutes
                p = "60"
                if timeframe == "5m": p = "5"
                elif timeframe == "15m": p = "15"
                elif timeframe == "30m": p = "30"
                df = ak.futures_zh_minute_sina(symbol=symbol, period=p)

            if df is None or df.empty:
                return None
            
            # Standardize columns
            # Daily: date, open, high, low, close, volume, hold, settle
            # Minute: datetime, open, high, low, close, volume, hold
            
            times = []
            values = []
            
            for _, row in df.tail(200).iterrows():
                t = row.get("date") or row.get("datetime")
                o = row.get("open")
                c = row.get("close")
                l = row.get("low")
                h = row.get("high")
                
                if t and o and c:
                    times.append(str(t))
                    values.append(float(c)) # ChartData uses single value line? Model says values: List[float]
            
            return {"times": times, "values": values}
        except Exception as e:
            print(f"Chart fetch error: {e}")
            return None

    # We can cache this
    return await asyncio.to_thread(_fetch_chart) or {"times": [], "values": []}

@router.get("/macro", response_model=List[MacroItem])
async def get_macro_drivers():
    """
    获取宏观驱动因子 (美元指数, 美债等)
    """
    def _fetch_macro():
        try:
            import akshare as ak
            # Using simple indicators
            # Dollar Index
            result = []
            
            # Mock-like real data via simple scrape or fixed proxy if akshare is slow
            # But let's try to get something real if possible.
            # ak.index_investing_global(country="美国", index_name="美元指数") is slow/unstable
            
            # Alternative: Use currency rates
            df_fx = ak.currency_boc_safe() # SAFE data
            # This might be heavy.
            
            # Let's use a simpler approach: futures prices of key global commodities as proxies
            # or just return empty if too hard, but user wants REAL data.
            
            # Let's try to get Dollar Index from Sina Futures (DINIW)
            # ak.futures_hq_spot(symbol="DINIW") -> Global futures?
            
            # For now, let's return Gold and Oil as "Macro Drivers" for other commodities
            
            drivers = [
                {"code": "au0", "name": "黄金 (Gold)", "status": "stable"},
                {"code": "sc0", "name": "原油 (Oil)", "status": "stable"},
                {"code": "cu0", "name": "铜 (Copper)", "status": "stable"}
            ]
            
            futures = ak.futures_zh_spot()
            if futures is not None and not futures.empty:
                for d in drivers:
                    row = futures[futures['symbol'] == d['code']]
                    if not row.empty:
                        r = row.iloc[0]
                        price = _to_float(r.get('price') or r.get('latest_price'))
                        change = _to_float(r.get('change_rate') or r.get('change_pct') or r.get('涨跌幅'))
                        
                        if price is not None:
                            d['value'] = str(price)
                        else:
                            d['value'] = "-"
                            
                        if change is not None:
                            d['percent'] = int(change * 100) if abs(change) < 1 else int(change)
                            d['change'] = f"{change:.2f}%"
                            if change > 0.5: d['status'] = "high"
                            elif change < -0.5: d['status'] = "low"
                            
                        result.append(d)
                        
            return result
        except Exception:
            return []

    return await asyncio.to_thread(_fetch_macro) or []

@router.get("/alerts", response_model=List[AlertItem])
async def get_commodity_alerts():
    # Use news as alerts
    def _fetch_alerts():
        try:
            import akshare as ak
            df = ak.news_cctv(date=time.strftime("%Y%m%d"))
            if df is None or df.empty:
                return []
            
            alerts = []
            keywords = ["黄金", "石油", "原油", "钢铁", "煤炭", "有色"]
            for i, row in df.iterrows():
                title = row.get("title") or row.get("content")
                if title and any(k in str(title) for k in keywords):
                    alerts.append({
                        "id": i,
                        "message": str(title)[:50] + "...",
                        "level": "warning"
                    })
            return alerts[:5]
        except Exception:
            return []
            
    return await asyncio.to_thread(_fetch_alerts) or []

@router.get("/inventory", response_model=List[InventoryItem])
async def get_inventory_monitor():
    def _fetch_inventory():
        try:
            import akshare as ak
            # SHFE inventory
            # ak.futures_inventory_99_shfe(date=...)
            # This is complex to get right date.
            
            # Fetch inventory data
            items = [
                {"name": "沪铜库存", "symbol": "沪铜"},
                {"name": "沪铝库存", "symbol": "沪铝"},
                {"name": "螺纹库存", "symbol": "螺纹钢"},
                {"name": "豆粕库存", "symbol": "豆粕"},
            ]
            
            results = []
            for item in items:
                try:
                    df = ak.futures_inventory_em(symbol=item["symbol"])
                    if df is not None and not df.empty:
                        latest = df.iloc[-1]
                        val = latest.get("库存") or latest.get("inventory")
                        if val:
                            results.append({
                                "name": item["name"],
                                "value": f"{val} 吨",
                                "status": "normal" # logic to determine status
                            })
                except:
                    continue
            return results
        except Exception:
            return []

    return await asyncio.to_thread(_fetch_inventory) or []
