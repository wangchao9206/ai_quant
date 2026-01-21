
from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Optional
from pydantic import BaseModel
import asyncio
import random
import datetime
import threading
import time
import pandas as pd

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
                            data = await asyncio.wait_for(asyncio.to_thread(_fetch_market_indices_akshare), timeout=6.0)
                        except Exception:
                            with _cache_lock:
                                _indices_cache["next"] = time.monotonic() + 15.0
                            return
                        if data:
                            with _cache_lock:
                                _indices_cache["data"] = data
                                _indices_cache["ts"] = time.monotonic()
                    finally:
                        with _cache_lock:
                            _indices_cache["refreshing"] = False

                asyncio.create_task(_refresh())

    return cached if cached is not None else _mock_market_indices()

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
                            data = await asyncio.wait_for(asyncio.to_thread(_fetch_market_sectors_akshare), timeout=6.0)
                        except Exception:
                            with _cache_lock:
                                _sectors_cache["next"] = time.monotonic() + 20.0
                            return
                        if data:
                            with _cache_lock:
                                _sectors_cache["data"] = data
                                _sectors_cache["ts"] = time.monotonic()
                    finally:
                        with _cache_lock:
                            _sectors_cache["refreshing"] = False

                asyncio.create_task(_refresh())

    return cached if cached is not None else _mock_market_sectors()


def _mock_market_indices():
    return [
        {"name": "上证指数", "value": 3200.50 + random.uniform(-10, 10), "change": 1.25 + random.uniform(-0.2, 0.2), "volume": "4500亿"},
        {"name": "深证成指", "value": 10502.20 + random.uniform(-30, 30), "change": -0.50 + random.uniform(-0.2, 0.2), "volume": "5800亿"},
        {"name": "创业板指", "value": 2200.15 + random.uniform(-10, 10), "change": 0.80 + random.uniform(-0.2, 0.2), "volume": "2100亿"},
        {"name": "科创50", "value": 980.45 + random.uniform(-5, 5), "change": 2.10 + random.uniform(-0.2, 0.2), "volume": "800亿"},
    ]


def _fetch_market_indices_akshare():
    import akshare as ak

    df = ak.stock_zh_index_spot_em()
    if df is None or df.empty:
        return []

    records = df.to_dict(orient="records")
    wanted = {"上证指数", "深证成指", "创业板指", "科创50"}
    result = []
    for r in records:
        name = r.get("指数名称") or r.get("name") or r.get("f14")
        if name in wanted:
            value = r.get("最新价") or r.get("close") or r.get("price") or r.get("f2")
            change = r.get("涨跌幅") or r.get("rate") or r.get("change") or r.get("f3")
            volume = r.get("成交量") or r.get("volume") or r.get("f5")
            try:
                value = float(value)
            except Exception:
                value = None
            try:
                change = float(change)
            except Exception:
                change = None
            volume_str = str(volume) if volume is not None else ""
            result.append({"name": name, "value": value, "change": change, "volume": volume_str})
    return result


def _mock_market_sectors():
    sectors = ["白酒", "新能源车", "半导体", "银行", "房地产", "医药", "人工智能", "光伏", "券商", "中字头"]
    return [{"name": name, "change": round(random.uniform(-3.0, 3.0), 2)} for name in sectors]


def _fetch_market_sectors_akshare():
    import akshare as ak

    fetcher = getattr(ak, "stock_sector_spot", None) or getattr(ak, "stock_sector_spot_em", None)
    if not fetcher:
        return []

    data = fetcher()
    if data is None or data.empty:
        return []

    records = data.to_dict(orient="records")
    result = []
    for r in records[:20]:
        name = r.get("板块名称") or r.get("name")
        change = r.get("涨跌幅") or r.get("rate") or r.get("change")
        try:
            change = float(change)
        except Exception:
            change = round(random.uniform(-3.0, 3.0), 2)
        result.append({"name": name or "板块", "change": change})
    return result

@router.get("/macro/calendar", response_model=List[MacroEvent])
async def get_macro_calendar(
    date: Optional[str] = None,
    countries: Optional[str] = None # comma separated
):
    def _mock_events():
        return [
            {
                "id": 1,
                "time": "20:30",
                "country": "US",
                "currency": "USD",
                "event": "美国12月季调后非农就业人口(万人)",
                "importance": "high",
                "actual": "21.6",
                "forecast": "17.0",
                "previous": "17.3",
                "impact": "利空金银",
            },
            {
                "id": 2,
                "time": "20:30",
                "country": "US",
                "currency": "USD",
                "event": "美国12月失业率",
                "importance": "high",
                "actual": "3.7%",
                "forecast": "3.8%",
                "previous": "3.7%",
                "impact": "中性",
            },
            {
                "id": 3,
                "time": "22:00",
                "country": "US",
                "currency": "USD",
                "event": "美国12月ISM非制造业PMI",
                "importance": "medium",
                "actual": "50.6",
                "forecast": "52.6",
                "previous": "52.7",
                "impact": "利多金银",
            },
            {
                "id": 4,
                "time": "18:00",
                "country": "EU",
                "currency": "EUR",
                "event": "欧元区12月CPI年率初值",
                "importance": "high",
                "actual": "2.9%",
                "forecast": "3.0%",
                "previous": "2.4%",
                "impact": "利多欧元",
            },
            {
                "id": 5,
                "time": "09:30",
                "country": "CN",
                "currency": "CNY",
                "event": "中国12月CPI年率",
                "importance": "medium",
                "actual": "-0.3%",
                "forecast": "-0.4%",
                "previous": "-0.5%",
                "impact": "温和复苏",
            },
        ]

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
                events.append(
                    {
                        "id": i + 1,
                        "time": str(event_time)[-5:] if event_time else "",
                        "country": "CN",
                        "currency": "CNY",
                        "event": str(event_name) if event_name else "经济事件",
                        "importance": "medium",
                        "actual": "",
                        "forecast": "",
                        "previous": "",
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
        cached = _mock_events()

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
    if date:
        random.seed(date)
        for e in result:
            actual = str(e.get("actual") or "").strip()
            if not actual:
                continue
            has_pct = "%" in actual
            try:
                v = float(actual.replace("%", ""))
            except Exception:
                continue
            v = v + random.uniform(-0.5, 0.5)
            e["actual"] = f"{v:.1f}{'%' if has_pct else ''}"
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
    def _mock():
        base_price = 3000.0
        data = []
        start_time = datetime.datetime.now().replace(hour=9, minute=30, second=0, microsecond=0)
        step = 5
        try:
            step = int(period)
        except Exception:
            step = 5
        for i in range(count):
            change = (random.random() - 0.5) * 10
            open_price = base_price + (random.random() - 0.5) * 5
            close_price = open_price + change
            low_price = min(open_price, close_price) - random.random() * 2
            high_price = max(open_price, close_price) + random.random() * 2
            base_price = close_price
            current_time = start_time + datetime.timedelta(minutes=i * step)
            data.append(
                {
                    "time": current_time.strftime("%H:%M"),
                    "values": [
                        round(open_price, 2),
                        round(close_price, 2),
                        round(low_price, 2),
                        round(high_price, 2),
                    ],
                    "vol": int(random.random() * 10000),
                }
            )
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

    if cached is not None and now - ts < 60.0:
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

    return cached if cached is not None else _mock()
