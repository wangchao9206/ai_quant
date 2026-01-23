import sys
import os
import traceback
import logging
from core.config import DISABLE_PROXIES

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("main")

# FORCE DISABLE PROXY GLOBALLY if configured
# The user reports persistent ProxyError issues.
# We explicitly set NO_PROXY to '*' to bypass any system/registry proxies.
# We also clear HTTP_PROXY/HTTPS_PROXY to ensure no env var interference.
if DISABLE_PROXIES:
    os.environ["NO_PROXY"] = "*"
    os.environ["no_proxy"] = "*"
    if "HTTP_PROXY" in os.environ: del os.environ["HTTP_PROXY"]
    if "HTTPS_PROXY" in os.environ: del os.environ["HTTPS_PROXY"]
    if "http_proxy" in os.environ: del os.environ["http_proxy"]
    if "https_proxy" in os.environ: del os.environ["https_proxy"]
    if "ALL_PROXY" in os.environ: del os.environ["ALL_PROXY"]
    if "all_proxy" in os.environ: del os.environ["all_proxy"]

print(f"Loading main.py... name={__name__}")

try:
    # print("Importing dependencies...")
    from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Request
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import StreamingResponse
    from apscheduler.schedulers.background import BackgroundScheduler
    from pydantic import BaseModel
    from typing import Optional, Dict, Any, List
    import asyncio
    import time
    import uvicorn
    import json
    import io
    import pandas as pd
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter, landscape
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    # print("Standard dependencies imported.")
except Exception as e:
    print(f"CRITICAL: Failed to import dependencies: {e}")
    traceback.print_exc()
    sys.exit(1)

# 确保 core 模块可以被导入
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    print("Importing core modules...")
    # import akshare as ak # Removed to avoid startup blocking
    import datetime
    from core.constants import get_multiplier
    from core.config import DATA_SYNC_CRON_HOUR, DATA_SYNC_CRON_MINUTE
    from core.database import BacktestStore, init_mongo, get_backtest_store
    from core.data_manager import data_manager
    from core.tasks import daily_data_update, startup_sync_check
    from core.engine import BacktestEngine
    from core.optimizer import StrategyOptimizer
    from core.analysis import generate_strategy_summary
    print("Core modules imported successfully.")
except Exception as e:
    print(f"CRITICAL: Failed to import core modules: {e}")
    traceback.print_exc()
    sys.exit(1)

try:
    print("Initializing MongoDB...")
    init_mongo()
    print("MongoDB initialized.")
except Exception as e:
    print(f"CRITICAL: Failed to initialize MongoDB: {e}")
    traceback.print_exc()
    sys.exit(1)

app = FastAPI(debug=True)

from routers import market, analysis, stock, fund, derivatives, commodities, yidao
app.include_router(market.router, prefix="/api/market", tags=["Market"])
app.include_router(analysis.router, prefix="/api/analysis", tags=["Analysis"])
app.include_router(stock.router, prefix="/api/stock", tags=["Stock"])
app.include_router(fund.router, prefix="/api/fund", tags=["Fund"])
app.include_router(derivatives.router, prefix="/api/derivatives", tags=["Derivatives"])
app.include_router(commodities.router, prefix="/api/commodities", tags=["Commodities"])
app.include_router(yidao.router, prefix="/api/yidao", tags=["YiDao"])

# 数据库依赖
def get_db():
    yield get_backtest_store()

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"], # 明确允许的方法
    allow_headers=["*"],
)

class BacktestRequest(BaseModel):
    symbol: str
    period: str
    strategy_params: Dict[str, Any]
    auto_optimize: bool = True # 是否开启自动优化
    start_date: Optional[str] = None # 开始时间 (YYYY-MM-DD)
    end_date: Optional[str] = None   # 结束时间 (YYYY-MM-DD)
    initial_cash: float = 1000000.0 # 初始本金
    strategy_code: Optional[str] = None # 自定义策略代码
    asset_type: Optional[str] = None

HEALTH_STATUS = {
    "startup": {"ok": None, "ts": 0.0, "detail": None},
    "mongo": {"ok": None, "ts": 0.0, "detail": None},
    "akshare": {"ok": None, "ts": 0.0, "detail": None},
}

def _update_health(name: str, ok: bool, detail: Optional[str] = None) -> None:
    HEALTH_STATUS[name] = {"ok": ok, "ts": time.time(), "detail": detail}

def _needs_refresh(name: str, ttl: float) -> bool:
    ts = (HEALTH_STATUS.get(name, {}) or {}).get("ts") or 0.0
    return time.time() - ts > ttl

async def _check_mongo_health(force: bool = False) -> Optional[bool]:
    if not force and not _needs_refresh("mongo", 30.0):
        return HEALTH_STATUS["mongo"]["ok"]
    def _work():
        try:
            get_backtest_store()
            return True, None
        except Exception as e:
            return False, str(e)
    ok, detail = await asyncio.to_thread(_work)
    _update_health("mongo", ok, detail)
    return ok

async def _check_akshare_health(force: bool = False) -> Optional[bool]:
    if not force and not _needs_refresh("akshare", 60.0):
        return HEALTH_STATUS["akshare"]["ok"]
    def _work():
        try:
            import akshare as ak
            df = ak.stock_zh_index_spot_em()
            if df is None or df.empty:
                return False, "empty"
            return True, None
        except Exception as e:
            return False, str(e)
    try:
        ok, detail = await asyncio.wait_for(asyncio.to_thread(_work), timeout=4.0)
    except Exception as e:
        ok, detail = False, str(e)
    _update_health("akshare", ok, detail)
    return ok

def _health_snapshot() -> Dict[str, Any]:
    data = {k: dict(v) for k, v in HEALTH_STATUS.items()}
    return data

async def _run_startup_self_check() -> None:
    await asyncio.gather(
        _check_mongo_health(True),
        _check_akshare_health(True),
    )
    data = _health_snapshot()
    ok = all([
        data.get("mongo", {}).get("ok"),
        data.get("akshare", {}).get("ok"),
    ])
    _update_health("startup", ok)

@app.get("/api/health")
async def get_health():
    await asyncio.gather(
        _check_mongo_health(),
        _check_akshare_health(),
    )
    data = _health_snapshot()
    ok = all([
        data.get("mongo", {}).get("ok"),
        data.get("akshare", {}).get("ok"),
    ])
    _update_health("startup", ok)
    return _health_snapshot()

@app.get("/api/strategies/recommended")
async def get_recommended_strategies(db: BacktestStore = Depends(get_db)):
    """
    获取推荐策略：
    1. 从历史回测中筛选表现最好的 (Top 3 by Return Rate)
    2. 如果历史记录不足，补充预设的经典策略
    """
    recommendations = []
    
    # 1. 查询历史最佳
    top_records = db.top_records(min_return=10, min_trades=5, limit=3)
    
    for record in top_records:
        recommendations.append({
            "id": f"hist_{record.get('id')}",
            "name": f"历史优选: {record.get('symbol')} {record.get('period')}策略",
            "description": f"基于历史回测数据筛选的高收益策略，收益率 {float(record.get('return_rate') or 0):.2f}%",
            "tags": ["高收益", "历史验证"],
            "metrics": {
                "return_rate": record.get("return_rate"),
                "win_rate": record.get("win_rate"),
                "max_drawdown": record.get("max_drawdown"),
                "sharpe_ratio": record.get("sharpe_ratio")
            },
            "config": {
                "symbol": record.get("symbol"),
                "period": record.get("period"),
                "strategy_params": record.get("strategy_params")
            },
            "source": "history",
            "usage_guide": "此策略基于历史数据挖掘，建议在相似的市场环境（波动率、趋势性）下使用。请先进行模拟交易验证。",
            "risk_warning": "历史回测表现不代表未来收益。注意过拟合风险，当市场风格切换时策略可能会失效。"
        })
        
    # 2. 预设经典策略 (如果推荐不足 5 个)
    presets = [
        {
            "id": "preset_trend_conservative",
            "name": "稳健趋势跟踪",
            "description": "使用较长周期的均线组合 (20/60)，配合较宽的 ATR 止损 (3.0)，适合捕捉大趋势，交易频率较低。",
            "tags": ["稳健", "长线", "低频"],
            "metrics": {
                "return_rate": 25.5, # 模拟数据
                "win_rate": 45.0,
                "max_drawdown": 12.0,
                "sharpe_ratio": 1.5
            },
            "config": {
                "symbol": "SH0", # 默认
                "period": "daily",
                "strategy_params": {
                    "fast_period": 20,
                    "slow_period": 60,
                    "atr_period": 14,
                    "atr_multiplier": 3.0,
                    "risk_per_trade": 0.01
                }
            },
            "source": "preset",
            "usage_guide": "该策略适合在日线级别的大趋势行情中使用。建议在市场明确出现单边上涨或下跌趋势时开启。适合资金量较大、追求稳健收益的投资者。",
            "risk_warning": "由于是趋势跟踪策略，在长期震荡市中可能会出现连续小幅磨损。请耐心持有，避免频繁干预。"
        },
        {
            "id": "preset_trend_aggressive",
            "name": "激进波段策略",
            "description": "使用灵敏的均线组合 (5/20) 和较紧的止损 (1.5)，旨在捕捉短期快速波动，交易活跃，适合波动率高的品种。",
            "tags": ["激进", "短线", "高频"],
            "metrics": {
                "return_rate": 40.2, # 模拟数据
                "win_rate": 38.0,
                "max_drawdown": 25.0,
                "sharpe_ratio": 1.2
            },
            "config": {
                "symbol": "SH0",
                "period": "30", # 30分钟
                "strategy_params": {
                    "fast_period": 5,
                    "slow_period": 20,
                    "atr_period": 14,
                    "atr_multiplier": 1.5,
                    "risk_per_trade": 0.03
                }
            },
            "source": "preset",
            "usage_guide": "适合波动率较高的品种（如股指期货、黑色系）。建议在开盘后波动剧烈时段运行。适合风险偏好较高、追求高收益的投资者。",
            "risk_warning": "策略交易频率高，滑点和手续费对收益影响较大。回撤风险较高，请严格遵守止损，不建议隔夜重仓。"
        },
        {
            "id": "preset_intraday",
            "name": "日内超短线",
            "description": "基于 5 分钟 K 线的极速策略，利用 3/10 均线交叉，严格止损，不留隔夜仓。",
            "tags": ["超短线", "日内", "高风险"],
            "metrics": {
                "return_rate": 0,
                "win_rate": 0,
                "max_drawdown": 0,
                "sharpe_ratio": 0
            },
            "config": {
                "symbol": "SH000001",
                "period": "5",
                "strategy_params": {
                    "fast_period": 3,
                    "slow_period": 10,
                    "atr_period": 14,
                    "atr_multiplier": 1.0,
                    "risk_per_trade": 0.01
                }
            },
            "source": "preset",
            "usage_guide": "严格的日内交易策略。建议仅在主力合约活跃时段交易。每日收盘前 15 分钟请强制平仓。",
            "risk_warning": "对网络延迟和滑点极度敏感。请确保交易环境稳定。若连续亏损超过 3 次，建议当日停止交易。"
        }
    ]
    
    # 合并，去重 (简单按ID)
    existing_ids = set(r['id'] for r in recommendations)
    for p in presets:
        if p['id'] not in existing_ids:
            recommendations.append(p)
            
    return recommendations

@app.post("/api/backtest")
async def run_backtest(request: BacktestRequest, db: BacktestStore = Depends(get_db)):
    print(f"收到回测请求: {request.symbol}, {request.period}, {request.strategy_params}, 自动优化: {request.auto_optimize}, 时间段: {request.start_date} - {request.end_date}, 本金: {request.initial_cash}")
    
    strategy_class = None
    if request.strategy_code:
        try:
            print("Compiling custom strategy code...")
            local_scope = {}
            import backtrader as bt
            # Execute in a restricted scope but with bt available
            exec(request.strategy_code, {'bt': bt}, local_scope)
            if 'GeneratedStrategy' in local_scope:
                strategy_class = local_scope['GeneratedStrategy']
                print("Custom strategy 'GeneratedStrategy' loaded successfully.")
            else:
                raise ValueError("Generated code must define 'GeneratedStrategy' class")
        except Exception as e:
            print(f"Error compiling strategy: {e}")
            raise HTTPException(status_code=400, detail=f"Invalid strategy code: {str(e)}")

    engine = BacktestEngine()
    asset_type = request.asset_type or infer_asset_type(request.symbol)
    
    # 1. 运行初始回测
    result = engine.run(
        symbol=request.symbol, 
        period=request.period, 
        strategy_params=request.strategy_params,
        start_date=request.start_date,
        end_date=request.end_date,
        initial_cash=request.initial_cash,
        strategy_class=strategy_class,
        asset_type=asset_type
    )
    
    if "error" in result:
        print(f"Backtest execution returned error: {result['error']}")
        raise HTTPException(status_code=400, detail=result["error"])
        
    # 计算初始收益率
    initial_cash = result['metrics']['initial_cash']
    final_value = result['metrics']['final_value']
    net_profit = result['metrics']['net_profit']
    return_rate = (net_profit / initial_cash) * 100
    
    # 保存初始结果
    db.insert_record(
        {
            "symbol": request.symbol,
            "period": request.period,
            "strategy_params": request.strategy_params,
            "asset_type": asset_type,
            "initial_cash": initial_cash,
            "final_value": final_value,
            "net_profit": net_profit,
            "return_rate": return_rate,
            "sharpe_ratio": result["metrics"]["sharpe_ratio"],
            "max_drawdown": result["metrics"]["max_drawdown"],
            "total_trades": result["metrics"]["total_trades"],
            "win_rate": result["metrics"]["win_rate"],
            "is_optimized": 0,
            "equity_curve": result.get("equity_curve", []),
            "logs": result.get("logs", []),
        }
    )
    
    # 2. 检查是否需要自动优化
    optimized_result = None
    optimized_params = None
    
    if request.auto_optimize and return_rate < 20.0:
        optimizer = StrategyOptimizer()
        best_params, best_res = optimizer.optimize(
            symbol=request.symbol, 
            period=request.period, 
            initial_params=request.strategy_params,
            target_return=20.0,
            start_date=request.start_date,
            end_date=request.end_date,
            initial_cash=initial_cash,
            asset_type=asset_type
        )
        
        if best_res:
             # 计算优化后的收益率
            opt_final_value = best_res['metrics']['final_value']
            opt_net_profit = best_res['metrics']['net_profit']
            opt_return_rate = (opt_net_profit / initial_cash) * 100
            
            if opt_return_rate > return_rate:
                print(f"优化成功! 新收益率: {opt_return_rate:.2f}%")
                optimized_result = best_res
                optimized_params = best_params
                optimization_msg = f"原始收益率 {return_rate:.2f}% 未达标 (<20%)。已自动优化参数，新收益率 {opt_return_rate:.2f}%。"
                
                # 保存优化后的结果
                db.insert_record(
                    {
                        "symbol": request.symbol,
                        "period": request.period,
                        "strategy_params": best_params,
                        "asset_type": asset_type,
                        "initial_cash": initial_cash,
                        "final_value": opt_final_value,
                        "net_profit": opt_net_profit,
                        "return_rate": opt_return_rate,
                        "sharpe_ratio": best_res["metrics"]["sharpe_ratio"],
                        "max_drawdown": best_res["metrics"]["max_drawdown"],
                        "total_trades": best_res["metrics"]["total_trades"],
                        "win_rate": best_res["metrics"]["win_rate"],
                        "is_optimized": 1,
                        "equity_curve": best_res.get("equity_curve", []),
                        "logs": best_res.get("logs", []),
                    }
                )
            else:
                optimization_msg = "自动优化尝试未找到更好的参数组合。"
        else:
             optimization_msg = "自动优化失败，未产生有效结果。"
             
    # 构建最终响应
    response_data = result
    if optimized_result:
        response_data = optimized_result
        response_data['optimization_info'] = {
            'triggered': True,
            'message': optimization_msg,
            'original_return': return_rate,
            'optimized_return': (optimized_result['metrics']['net_profit'] / initial_cash) * 100,
            'optimized_params': optimized_params
        }
    else:
        response_data['optimization_info'] = {
            'triggered': False,
            'message': "收益率已达标或未开启自动优化" if return_rate >= 20 else "自动优化未找到更好结果"
        }

    return response_data

from core.data_processor import DataProcessor

# ... (Previous imports)

# Middleware for performance monitoring
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    
    # Log slow requests (> 1s)
    if process_time > 1.0:
        print(f"SLOW REQUEST: {request.url.path} took {process_time:.2f}s")
        
    return response

@app.get("/api/data/quality")
async def get_data_quality(
    symbol: str,
    period: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """
    Get data quality assessment for a specific symbol/period
    """
    df = data_manager.load_data(symbol, period, start_date, end_date)
    if df is None or df.empty:
        # Try fetch if not exists
        df = data_manager.fetch_and_update(symbol, period)
        if df is not None:
             # Apply date filter again
             if start_date: df = df[df.index >= pd.to_datetime(start_date)]
             if end_date: 
                 end_dt = pd.to_datetime(end_date) + pd.Timedelta(days=1)
                 df = df[df.index < end_dt]
                 
    if df is None or df.empty:
         raise HTTPException(status_code=404, detail="No data available")
         
    return DataProcessor.assess_quality(df)

@app.get("/api/data/kline")
async def get_kline_data(
    symbol: str,
    period: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    print(f"Fetching kline data for {symbol} {period} {start_date}-{end_date}")
    
    # Use DataManager with fallback
    df = data_manager.get_data_with_fallback(symbol, period, start_date, end_date)
    
    if df is None or df.empty:
        print(f"No data found for {symbol} {period}")
        raise HTTPException(status_code=404, detail="No data found for the given symbol and parameters")

    try:
        # Apply Data Processor Cleaning
        df_clean = DataProcessor.clean_data(df)
        
        # Process data for ECharts
        df_chart = df_clean.copy()
        # Handle index
        if not isinstance(df_chart.index, pd.DatetimeIndex):
            if 'date' in df_chart.columns:
                df_chart['date'] = pd.to_datetime(df_chart['date'])
                df_chart.set_index('date', inplace=True)
            elif 'datetime' in df_chart.columns:
                df_chart['datetime'] = pd.to_datetime(df_chart['datetime'])
                df_chart.set_index('datetime', inplace=True)
            else:
                 # Try first column
                 df_chart.set_index(df_chart.columns[0], inplace=True)
                 df_chart.index = pd.to_datetime(df_chart.index)
        
        df_chart.sort_index(inplace=True)
        
        # Calculate MAs
        df_chart['MA5'] = df_chart['Close'].rolling(window=5).mean()
        df_chart['MA10'] = df_chart['Close'].rolling(window=10).mean()
        df_chart['MA20'] = df_chart['Close'].rolling(window=20).mean()
        df_chart['MA60'] = df_chart['Close'].rolling(window=60).mean()
        
        chart_data = {
            "dates": [d.strftime('%Y-%m-%d %H:%M') for d in df_chart.index],
            "ohlc": [[clean_nan(x) for x in row] for row in df_chart[['Open', 'Close', 'Low', 'High']].values],
            "ma5": [clean_nan(x) for x in df_chart['MA5']],
            "ma10": [clean_nan(x) for x in df_chart['MA10']],
            "ma20": [clean_nan(x) for x in df_chart['MA20']],
            "ma60": [clean_nan(x) for x in df_chart['MA60']],
            "volume": [clean_nan(x) for x in df_chart['Volume']] if 'Volume' in df_chart.columns else []
        }
        return chart_data
    except Exception as e:
        print(f"Error preparing chart data: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/backtest/history")
async def get_backtest_history(
    skip: int = 0, 
    limit: int = 20, 
    symbol: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    min_return: Optional[float] = None,
    sort_by: str = "timestamp",
    order: str = "desc",
    db: BacktestStore = Depends(get_db)
):
    return db.list_history(
        skip=skip,
        limit=limit,
        symbol=symbol,
        start_date=start_date,
        end_date=end_date,
        min_return=min_return,
        sort_by=sort_by,
        order=order,
        include_big_fields=False,
    )

@app.get("/api/backtest/history/{record_id}")
async def get_backtest_detail(record_id: int, db: BacktestStore = Depends(get_db)):
    record = db.get_record(record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Record not found")
    return record

@app.get("/api/strategy/correlation")
async def get_strategy_correlation(
    ids: Optional[str] = None,
    limit: int = 5,
    db: BacktestStore = Depends(get_db)
):
    selected_records = []
    if ids:
        try:
            id_list = [int(i) for i in ids.split(",")]
            selected_records = db.get_records_by_ids(id_list)
        except:
            pass
    else:
        # Default to top return strategies
        selected_records = db.list_history(skip=0, limit=limit, sort_by="return_rate", order="desc", include_big_fields=True).get("items", [])
        
    if not selected_records:
        return {"labels": [], "matrix": []}
        
    # Build DataFrame of Equity Curves
    data = {}
    for r in selected_records:
        # equity_curve is a list of dicts: [{'date': '2023-01-01', 'value': 100000, 'return': 0.0}, ...]
        curve = r.get("equity_curve")
        if not curve:
            continue
            
        # Parse equity curve
        dates = []
        returns = []
        # Ensure equity_curve is a list (it might be stored as JSON)
        if isinstance(curve, str):
            try:
                curve = json.loads(curve)
            except:
                curve = []
                
        for point in curve:
            if isinstance(point, dict) and 'date' in point and 'return' in point:
                dates.append(point['date'])
                returns.append(point['return'])
            
        if dates:
            # 确保 dates 里的元素都是 datetime 对象
            try:
                dt_index = pd.to_datetime(dates)
                s = pd.Series(returns, index=dt_index)
                # Label: ID - Symbol
                label = f"#{r.get('id')} {r.get('symbol')}"
                data[label] = s
            except Exception as e:
                print(f"Error parsing dates for record {r.get('id')}: {e}")
                continue

    if not data:
        return {"labels": [], "matrix": []}
        
    try:
        df = pd.DataFrame(data)
        # Fill NaN with 0 (assuming neutral/no return for missing days)
        df.fillna(0, inplace=True)
        
        if df.empty:
             return {"labels": [], "matrix": []}

        corr_matrix = df.corr()
        corr_matrix.fillna(0, inplace=True) # Fill NaN correlations if any
        
        # Format for frontend
        labels = corr_matrix.columns.tolist()
        # Round to 2 decimals, handle NaN/Inf just in case
        matrix = []
        for row in corr_matrix.values.tolist():
            new_row = []
            for x in row:
                try:
                    val = round(float(x), 2)
                    if val != val: # check for NaN
                        val = 0
                    new_row.append(val)
                except:
                    new_row.append(0)
            matrix.append(new_row)
        
        return {
            "labels": labels,
            "matrix": matrix
        }
    except Exception as e:
        print(f"Error calculating correlation: {e}")
        return {"labels": [], "matrix": []}

@app.get("/api/backtest/stats")
async def get_backtest_stats(db: BacktestStore = Depends(get_db)):
    return db.stats()

@app.get("/api/backtest/export")
async def export_backtest_history(
    symbol: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    min_return: Optional[float] = None,
    db: BacktestStore = Depends(get_db)
):
    records = db.export_records(symbol=symbol, start_date=start_date, end_date=end_date, min_return=min_return)
    
    data = []
    for r in records:
        data.append({
            "ID": r.get("id"),
            "Timestamp": r.get("timestamp"),
            "Symbol": r.get("symbol"),
            "Period": r.get("period"),
            "Initial Cash": r.get("initial_cash"),
            "Final Value": r.get("final_value"),
            "Net Profit": r.get("net_profit"),
            "Return Rate (%)": r.get("return_rate"),
            "Sharpe Ratio": r.get("sharpe_ratio"),
            "Max Drawdown (%)": r.get("max_drawdown"),
            "Total Trades": r.get("total_trades"),
            "Win Rate (%)": r.get("win_rate"),
            "Is Optimized": r.get("is_optimized")
        })
    
    df = pd.DataFrame(data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Backtest Records')
    output.seek(0)
    
    headers = {
        'Content-Disposition': 'attachment; filename="backtest_records.xlsx"'
    }
    return StreamingResponse(output, headers=headers, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

@app.get("/api/backtest/export/pdf")
async def export_backtest_history_pdf(
    symbol: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    min_return: Optional[float] = None,
    db: BacktestStore = Depends(get_db)
):
    records = db.export_records(symbol=symbol, start_date=start_date, end_date=end_date, min_return=min_return)
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(letter))
    elements = []
    
    styles = getSampleStyleSheet()
    elements.append(Paragraph("Backtest History Report", styles['Title']))
    elements.append(Spacer(1, 12))
    
    # Data for Table
    # Limit columns to fit on page
    data = [['ID', 'Date', 'Symbol', 'Return(%)', 'Sharpe', 'Drawdown(%)', 'Trades', 'WinRate(%)']]
    for r in records:
        ts = r.get("timestamp")
        if isinstance(ts, datetime.datetime):
            dt_str = ts.strftime('%Y-%m-%d')
        else:
            dt_str = str(ts)[:10] if ts else ""
        data.append([
            str(r.get("id")),
            dt_str,
            r.get("symbol"),
            f"{float(r.get('return_rate') or 0):.2f}",
            f"{float(r.get('sharpe_ratio') or 0):.2f}",
            f"{float(r.get('max_drawdown') or 0):.2f}",
            str(r.get("total_trades") or 0),
            f"{float(r.get('win_rate') or 0):.2f}"
        ])
    
    # Simple pagination if too many records? ReportLab handles page breaks automatically with SimpleDocTemplate
    
    t = Table(data)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    elements.append(t)
    
    try:
        doc.build(elements)
    except Exception as e:
        print(f"PDF generation error: {e}")
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")
        
    buffer.seek(0)
    
    headers = {
        'Content-Disposition': 'attachment; filename="backtest_report.pdf"'
    }
    return StreamingResponse(buffer, headers=headers, media_type='application/pdf')

@app.get("/api/backtest/{record_id}")
async def get_backtest_detail(record_id: int, db: BacktestStore = Depends(get_db)):
    record = db.get_record(record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Record not found")
    return record

@app.get("/api/strategy/summary/{record_id}")
async def get_summary_report(record_id: int, db: BacktestStore = Depends(get_db)):
    record = db.get_record(record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Record not found")
        
    summary = generate_strategy_summary(record)
    return {"summary": summary}

@app.delete("/api/backtest/{record_id}")
async def delete_backtest(record_id: int, db: BacktestStore = Depends(get_db)):
    ok = db.delete_record(record_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Record not found")
    return {"status": "success"}

class StrategyCodeRequest(BaseModel):
    code: str

@app.get("/api/strategy/code")
async def get_strategy_code():
    try:
        strategy_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "core", "strategy.py")
        with open(strategy_path, "r", encoding="utf-8") as f:
            code = f.read()
        return {"code": code}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/strategy/code")
async def save_strategy_code(request: StrategyCodeRequest):
    try:
        # 简单校验语法
        compile(request.code, "<string>", "exec")
        
        strategy_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "core", "strategy.py")
        with open(strategy_path, "w", encoding="utf-8") as f:
            f.write(request.code)
        return {"status": "success", "message": "Strategy code updated successfully"}
    except SyntaxError as e:
        raise HTTPException(status_code=400, detail=f"Syntax Error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

from core.strategy_generator import strategy_generator

class StrategyGenerationRequest(BaseModel):
    text: str

import importlib
import core.strategy_generator

@app.post("/api/strategies/generate")
async def generate_strategy(request: StrategyGenerationRequest):
    try:
        # Reload to ensure latest template is used
        importlib.reload(core.strategy_generator)
        from core.strategy_generator import strategy_generator as sg
        
        result = sg.parse(request.text)
        return result
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

# 缓存品种列表
CACHED_SYMBOLS = {"futures": [], "stocks": []}
LAST_CACHE_TIME = None
SYMBOLS_REFRESHING = False
SYMBOLS_NEXT_REFRESH = 0.0

from core.data_loader import fetch_futures_data, infer_asset_type
import math

# Helper to clean NaNs for JSON
def clean_nan(x):
    if isinstance(x, (float, int)) and math.isnan(x):
        return None
    return x


def refresh_symbols_cache():
    global CACHED_SYMBOLS, LAST_CACHE_TIME, SYMBOLS_REFRESHING, SYMBOLS_NEXT_REFRESH
    try:
        # 1. Fetch Futures
        futures_list = []
        try:
            import akshare as ak
            df = ak.futures_display_main_sina()
            for _, row in df.iterrows():
                symbol = row["symbol"]
                name = row["name"]
                multiplier = get_multiplier(symbol)
                futures_list.append({"code": symbol, "name": f"{name} ({symbol})", "multiplier": multiplier})
        except Exception as e:
            print(f"后台刷新期货列表失败: {e}")

        # 2. Fetch Stocks (using stock router's helper)
        stocks_list = []
        try:
            stock_data = stock._fetch_stock_list_mongo()
            for s in stock_data:
                # Add multiplier 1 for stocks
                stocks_list.append({
                    "code": s["code"],
                    "name": s["name"], 
                    "multiplier": 1
                })
        except Exception as e:
            print(f"后台刷新股票列表失败: {e}")

        if futures_list or stocks_list:
            CACHED_SYMBOLS = {
                "futures": futures_list or CACHED_SYMBOLS.get("futures", []),
                "stocks": stocks_list or CACHED_SYMBOLS.get("stocks", [])
            }
            LAST_CACHE_TIME = datetime.datetime.now()
            data_manager.save_symbols_list(CACHED_SYMBOLS)
            SYMBOLS_NEXT_REFRESH = time.monotonic() + 3600.0 # 1 hour refresh
    except Exception as e:
        print(f"后台刷新品种列表失败: {e}")
        SYMBOLS_NEXT_REFRESH = time.monotonic() + 60.0
    finally:
        SYMBOLS_REFRESHING = False

@app.get("/api/symbols")
async def get_symbols():
    logger.info("API Request: /api/symbols")
    global CACHED_SYMBOLS, LAST_CACHE_TIME, SYMBOLS_REFRESHING, SYMBOLS_NEXT_REFRESH
    
    # 1. 内存缓存 (1小时失效)
    if CACHED_SYMBOLS and CACHED_SYMBOLS.get("futures") and LAST_CACHE_TIME:
        if (datetime.datetime.now() - LAST_CACHE_TIME).total_seconds() < 3600:
            logger.info("Returning cached symbols (memory)")
            return CACHED_SYMBOLS
            
    # 2. 本地文件缓存 (持久化)
    logger.info("Checking local symbols cache...")
    local_symbols = None
    try:
        local_symbols = await asyncio.wait_for(
            asyncio.to_thread(data_manager.get_symbols_list),
            timeout=1.0, # Increased from 0.5s to 1.0s to be safe on Windows
        )
    except Exception as e:
        logger.warning(f"Local symbol cache read timeout/error: {e}")
        local_symbols = None
    
    if local_symbols and isinstance(local_symbols, dict) and (local_symbols.get("futures") or local_symbols.get("stocks")):
        logger.info("Loaded symbols from local cache")
        CACHED_SYMBOLS = local_symbols
        LAST_CACHE_TIME = datetime.datetime.now()
        return CACHED_SYMBOLS
        
    # 3. 网络获取 (如果本地没有)
    now = time.monotonic()
    if (not SYMBOLS_REFRESHING) and now >= SYMBOLS_NEXT_REFRESH:
        logger.info("Triggering background symbol refresh")
        SYMBOLS_REFRESHING = True
        async def _bg_refresh():
            try:
                await asyncio.wait_for(asyncio.to_thread(refresh_symbols_cache), timeout=10.0)
            except Exception as e:
                logger.error(f"Background symbol refresh failed: {e}")
        asyncio.create_task(_bg_refresh())

    logger.info("Returning fallback/default symbols")
    # Return default/fallback if cache empty
    return CACHED_SYMBOLS if (CACHED_SYMBOLS.get("futures") or CACHED_SYMBOLS.get("stocks")) else {
        "futures": [
            {"code": "LH0", "name": "生猪主力 (LH0)", "multiplier": 16},
            {"code": "SH0", "name": "烧碱主力 (SH0)", "multiplier": 30},
            {"code": "RB0", "name": "螺纹钢主力 (RB0)", "multiplier": 10},
            {"code": "M0", "name": "豆粕主力 (M0)", "multiplier": 10},
            {"code": "IF0", "name": "沪深300 (IF0)", "multiplier": 300},
        ],
        "stocks": []
    }

scheduler = BackgroundScheduler()

@app.post("/api/data/update")
async def trigger_data_update(background_tasks: BackgroundTasks):
    background_tasks.add_task(daily_data_update)
    return {"message": "Data update task triggered in background"}

@app.on_event("startup")
def start_scheduler():
    if not scheduler.running:
        scheduler.add_job(daily_data_update, 'cron', hour=DATA_SYNC_CRON_HOUR, minute=DATA_SYNC_CRON_MINUTE)
        scheduler.start()
        print("Scheduler started.")
    try:
        loop = asyncio.get_event_loop()
        loop.create_task(_run_startup_self_check())
        loop.create_task(asyncio.to_thread(startup_sync_check))
    except Exception as e:
        print(f"Startup self-check scheduling failed: {e}")

@app.on_event("shutdown")
def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown()
        print("Scheduler shut down.")

if __name__ == "__main__":
    try:
        print("Starting Uvicorn server on port 8001...")
        uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
    except Exception as e:
        print(f"CRITICAL: Server startup failed: {e}")
        traceback.print_exc()
