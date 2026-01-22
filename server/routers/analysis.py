
from fastapi import APIRouter
from typing import List, Dict, Any
from pydantic import BaseModel
import asyncio
import threading
import time

router = APIRouter()


_cache_lock = threading.Lock()
_sentiment_overview_cache = {"data": None, "ts": 0.0, "refreshing": False, "next": 0.0}
_hot_topics_cache = {"data": None, "ts": 0.0, "refreshing": False, "next": 0.0}
_news_cache = {"data": None, "ts": 0.0, "refreshing": False, "next": 0.0}
_risk_metrics_cache = {"data": None, "ts": 0.0, "refreshing": False, "next": 0.0}
_risk_corr_cache = {"data": None, "ts": 0.0, "refreshing": False, "next": 0.0}


async def _get_or_refresh(cache, ttl_s: float, timeout_s: float, fail_delay_s: float, fetch_fn, fallback_fn):
    now = time.monotonic()
    with _cache_lock:
        cached = cache["data"]
        ts = cache["ts"]
        refreshing = cache["refreshing"]
        next_refresh = cache["next"]

    if cached is not None and now - ts < ttl_s:
        return cached

    if (not refreshing) and now >= next_refresh:
        with _cache_lock:
            if (not cache["refreshing"]) and time.monotonic() >= cache["next"]:
                cache["refreshing"] = True

                async def _refresh():
                    try:
                        try:
                            data = await asyncio.wait_for(asyncio.to_thread(fetch_fn), timeout=timeout_s)
                        except Exception:
                            with _cache_lock:
                                cache["next"] = time.monotonic() + fail_delay_s
                            return
                        if data is not None:
                            with _cache_lock:
                                cache["data"] = data
                                cache["ts"] = time.monotonic()
                    finally:
                        with _cache_lock:
                            cache["refreshing"] = False

                asyncio.create_task(_refresh())

    return cached if cached is not None else fallback_fn()

# --- Models ---

class SentimentData(BaseModel):
    score: int
    trend: List[int]
    status: str # 贪婪/恐惧等

class HotTopic(BaseModel):
    text: str
    weight: int
    sentiment: str # bullish, bearish, neutral

class NewsItem(BaseModel):
    id: int
    title: str
    source: str
    time: str
    impact: int
    sentiment: str
    analysis: str

class RiskMetrics(BaseModel):
    var95: float
    var99: float
    beta: float
    sharpe: float
    maxDrawdown: float
    curve: List[float] = []
    dates: List[str] = []

class StressTest(BaseModel):
    scenario: str
    impact: str
    probability: str

# --- Routes ---

@router.get("/sentiment/overview")
async def get_sentiment_overview():
    def _fetch():
        try:
            import akshare as ak

            df = ak.stock_zh_index_spot_em()
            if df is None or df.empty:
                return None
            row = df[df["指数名称"] == "上证指数"]
            if row.empty:
                return None
            r = row.iloc[0].to_dict()
            change_pct = float(r.get("涨跌幅") or r.get("f3") or 0)
            score = max(0, min(100, 50 + change_pct * 8))
            trend = []
            try:
                hist = ak.stock_zh_index_daily_em(symbol="sh000001")
                if hist is None or hist.empty:
                    hist = ak.stock_zh_index_daily_em(symbol="SH000001")
                if hist is not None and not hist.empty:
                    hist = hist.tail(8)
                    for _, h in hist.iterrows():
                        close_price = float(h.get("close") or h.get("收盘") or 0)
                        open_price = float(h.get("open") or h.get("开盘") or close_price)
                        pct = 0 if open_price == 0 else (close_price - open_price) / open_price * 100
                        trend.append(max(0, min(100, 50 + pct * 8)))
            except Exception:
                trend = []
            if not trend:
                trend = []
            status = "恐惧"
            if score > 80:
                status = "极度贪婪"
            elif score > 50:
                status = "贪婪"
            elif score < 20:
                status = "极度恐惧"
            return {"score": int(score), "trend": trend, "status": status}
        except Exception:
            return None

    cached = await _get_or_refresh(
        _sentiment_overview_cache,
        ttl_s=10.0,
        timeout_s=6.0,
        fail_delay_s=15.0,
        fetch_fn=_fetch,
        fallback_fn=lambda: None,
    )
    if cached:
        return cached
    # Return a safe default structure if data is missing, rather than 404 or None which might break frontend
    return {"score": 50, "trend": [], "status": "Neutral"}

@router.get("/sentiment/topics", response_model=List[HotTopic])
async def get_hot_topics():
    def _fetch():
        try:
            import akshare as ak

            fetcher = getattr(ak, "stock_sector_spot", None) or getattr(ak, "stock_sector_spot_em", None)
            if not fetcher:
                return None
            data = fetcher()
            if data is None or data.empty:
                return None
            records = data.to_dict(orient="records")
            result = []
            for r in records[:12]:
                name = r.get("板块名称") or r.get("name") or "概念"
                change = r.get("涨跌幅") or r.get("rate") or r.get("change") or 0
                try:
                    change = float(change)
                except Exception:
                    change = 0.0
                sentiment = "neutral"
                if change > 0.5:
                    sentiment = "bullish"
                elif change < -0.5:
                    sentiment = "bearish"
                result.append({"text": name, "weight": int(abs(change) * 5 + 5), "sentiment": sentiment})
            return result or None
        except Exception:
            return None

    cached = await _get_or_refresh(
        _hot_topics_cache,
        ttl_s=30.0,
        timeout_s=6.0,
        fail_delay_s=30.0,
        fetch_fn=_fetch,
        fallback_fn=lambda: [],
    )
    return cached or []

@router.get("/sentiment/news", response_model=List[NewsItem])
async def get_news_stream():
    def _fetch():
        try:
            import akshare as ak

            df = ak.stock_news_em()
            if df is None or df.empty:
                return None
            records = df.to_dict(orient="records")
            result = []
            for i, r in enumerate(records[:20]):
                title = r.get("新闻标题") or r.get("title") or ""
                source = r.get("新闻来源") or r.get("source") or ""
                time_val = r.get("发布时间") or r.get("time") or ""
                sentiment = "neutral"
                if any(k in str(title) for k in ["大涨", "新高", "利好", "增长"]):
                    sentiment = "bullish"
                if any(k in str(title) for k in ["大跌", "新低", "利空", "下滑"]):
                    sentiment = "bearish"
                
                # Deterministic impact based on sentiment
                impact = 75
                if sentiment == "bullish" or sentiment == "bearish":
                    impact = 90
                
                result.append(
                    {
                        "id": i + 1,
                        "title": str(title),
                        "source": str(source) if source else "",
                        "time": str(time_val),
                        "impact": impact,
                        "sentiment": sentiment,
                        "analysis": "",
                    }
                )
            return result or None
        except Exception:
            return None

    return await _get_or_refresh(
        _news_cache,
        ttl_s=20.0,
        timeout_s=6.0,
        fail_delay_s=30.0,
        fetch_fn=_fetch,
        fallback_fn=lambda: [],
    )

@router.get("/risk/metrics", response_model=RiskMetrics)
async def get_risk_metrics():
    def _fetch():
        try:
            import akshare as ak
            import pandas as pd

            df = ak.stock_zh_index_daily_em(symbol="sh000001")
            if df is None or df.empty:
                df = ak.stock_zh_index_daily_em(symbol="SH000001")
            if df is None or df.empty:
                return None
            df = df.tail(120)
            close_series = pd.to_numeric(df["close"] if "close" in df.columns else df["收盘"], errors="coerce").dropna()
            returns = close_series.pct_change().dropna()
            if returns.empty:
                return None
            portfolio_value = 1_000_000
            var95 = abs(returns.quantile(0.05) * portfolio_value)
            var99 = abs(returns.quantile(0.01) * portfolio_value)
            sharpe = (returns.mean() / returns.std()) * (252 ** 0.5) if returns.std() != 0 else 0
            cumulative = (1 + returns).cumprod()
            rolling_max = cumulative.cummax()
            drawdown = (cumulative / rolling_max - 1).min()
            
            # Prepare chart data (last 30 points for display)
            chart_data = cumulative.tail(30)
            dates = [d.strftime("%Y-%m-%d") for d in chart_data.index]
            curve = [round(float(v) * portfolio_value, 2) for v in chart_data.values]
            
            return {
                "var95": round(float(var95), 2),
                "var99": round(float(var99), 2),
                "beta": 1.0,
                "sharpe": round(float(sharpe), 2),
                "maxDrawdown": round(float(drawdown) * 100, 2),
                "curve": curve,
                "dates": dates
            }
        except Exception:
            return None

    return await _get_or_refresh(
        _risk_metrics_cache,
        ttl_s=300.0,
        timeout_s=8.0,
        fail_delay_s=120.0,
        fetch_fn=_fetch,
        fallback_fn=lambda: None,
    )

@router.get("/risk/correlation")
async def get_risk_correlation():
    def _fetch():
        try:
            import akshare as ak
            import pandas as pd

            symbols = ["sh000001", "sz399001", "sz399006"]
            names = ["股票", "成指", "创业板"]
            series_list = []
            for s in symbols:
                df = ak.stock_zh_index_daily_em(symbol=s)
                if df is None or df.empty:
                    continue
                close_series = pd.to_numeric(df["close"] if "close" in df.columns else df["收盘"], errors="coerce").dropna().tail(120)
                r = close_series.pct_change().dropna()
                if not r.empty:
                    series_list.append(r)
            if len(series_list) < 2:
                return None
            aligned = pd.concat(series_list, axis=1).dropna()
            corr = aligned.corr().values.tolist()
            assets = names[: len(corr)]
            flat_data = []
            for i in range(len(corr)):
                for j in range(len(corr)):
                    flat_data.append([i, j, round(float(corr[i][j]), 2)])
            return {"assets": assets, "matrix": flat_data} if flat_data else None
        except Exception:
            return None

    cached = await _get_or_refresh(
        _risk_corr_cache,
        ttl_s=300.0,
        timeout_s=10.0,
        fail_delay_s=120.0,
        fetch_fn=_fetch,
        fallback_fn=lambda: None,
    )
    return cached or {"assets": [], "matrix": []}

@router.get("/risk/stress-test", response_model=List[StressTest])
async def get_stress_test():
    def _fetch():
        try:
            import akshare as ak
            import pandas as pd
            
            # Fetch long history for stress test
            df = ak.stock_zh_index_daily_em(symbol="sh000001")
            if df is None or df.empty:
                return None
            
            # Scenarios
            # 1. 2015 Crash (June 2015)
            # 2. 2018 Trade War
            # 3. 2020 Covid
            # 4. Recent Low
            
            df['date'] = pd.to_datetime(df['date'])
            df.set_index('date', inplace=True)
            close = pd.to_numeric(df['close'])
            
            scenarios = [
                {"name": "2015股灾", "start": "2015-06-12", "end": "2015-08-26"},
                {"name": "2018贸易战", "start": "2018-01-24", "end": "2018-12-28"},
                {"name": "2020疫情", "start": "2020-01-14", "end": "2020-03-19"},
                {"name": "近期回调", "start": "2023-05-09", "end": "2024-02-05"},
            ]
            
            result = []
            for s in scenarios:
                try:
                    start_price = close.asof(s["start"])
                    end_price = close.asof(s["end"])
                    if pd.isna(start_price) or pd.isna(end_price):
                        continue
                    drop = (end_price - start_price) / start_price
                    impact_str = f"{drop*100:.1f}%"
                    
                    # Probability (simplified estimation based on frequency of such drops)
                    prob = "Low"
                    if abs(drop) < 0.1: prob = "High"
                    elif abs(drop) < 0.2: prob = "Medium"
                    
                    result.append({
                        "scenario": s["name"],
                        "impact": impact_str,
                        "probability": prob
                    })
                except:
                    continue
            return result
        except Exception:
            return []
            
    return await asyncio.to_thread(_fetch) or []
