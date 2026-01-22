from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from typing import Optional
import pandas as pd
import math
import datetime

from api.deps import get_data_manager
from core.data_manager import DataManager
from core.data_processor import DataProcessor
from core.tasks import daily_data_update
from core.constants import get_multiplier

router = APIRouter()

# 缓存品种列表 (Module-level cache)
CACHED_SYMBOLS = []
LAST_CACHE_TIME = None

def clean_nan(x):
    return None if (isinstance(x, float) and math.isnan(x)) else x

@router.get("/quality")
async def get_data_quality(
    symbol: str,
    period: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    data_manager: DataManager = Depends(get_data_manager)
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

@router.get("/kline")
async def get_kline_data(
    symbol: str,
    period: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    data_manager: DataManager = Depends(get_data_manager)
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

@router.get("/symbols")
async def get_symbols(data_manager: DataManager = Depends(get_data_manager)):
    global CACHED_SYMBOLS, LAST_CACHE_TIME
    
    futures_list = []
    
    # 1. 内存缓存 (1小时失效)
    if CACHED_SYMBOLS and LAST_CACHE_TIME:
        if (datetime.datetime.now() - LAST_CACHE_TIME).total_seconds() < 3600:
            futures_list = CACHED_SYMBOLS
    
    # 2. 本地文件缓存 (持久化)
    if not futures_list:
        local_symbols = data_manager.get_symbols_list()
        if local_symbols:
            print("从本地缓存加载品种列表")
            futures_list = local_symbols
            CACHED_SYMBOLS = futures_list
            LAST_CACHE_TIME = datetime.datetime.now()
            
    # 3. 网络获取 (如果本地没有)
    if not futures_list:
        try:
            print("正在从 AkShare 获取最新期货品种列表...")
            import akshare as ak
            df = ak.futures_display_main_sina()
            
            for _, row in df.iterrows():
                symbol = row['symbol']
                name = row['name']
                multiplier = get_multiplier(symbol)
                
                futures_list.append({
                    "code": symbol,
                    "name": f"{name} ({symbol})",
                    "multiplier": multiplier
                })
                
            CACHED_SYMBOLS = futures_list
            LAST_CACHE_TIME = datetime.datetime.now()
            
            # 保存到本地
            data_manager.save_symbols_list(futures_list)
            
        except Exception as e:
            print(f"获取品种列表失败: {e}")
            # 如果失败，返回硬编码的列表作为降级方案
            futures_list = [
                {"code": "LH0", "name": "生猪主力 (LH0)", "multiplier": 16},
                {"code": "SH0", "name": "烧碱主力 (SH0)", "multiplier": 30},
                {"code": "RB0", "name": "螺纹钢主力 (RB0)", "multiplier": 10},
                {"code": "M0", "name": "豆粕主力 (M0)", "multiplier": 10},
                {"code": "IF0", "name": "沪深300 (IF0)", "multiplier": 300}
            ]

    # 4. Common Stocks / Indices
    # Provide common indices and stocks for backtest
    common_stocks = [
        {"code": "sh000001", "name": "上证指数 (000001)", "multiplier": 1},
        {"code": "sz399001", "name": "深证成指 (399001)", "multiplier": 1},
        {"code": "sh000300", "name": "沪深300 (000300)", "multiplier": 1},
        {"code": "sh000016", "name": "上证50 (000016)", "multiplier": 1},
        {"code": "sz399006", "name": "创业板指 (399006)", "multiplier": 1},
        {"code": "sh600519", "name": "贵州茅台 (600519)", "multiplier": 100},
        {"code": "sz300750", "name": "宁德时代 (300750)", "multiplier": 100},
        {"code": "sz002594", "name": "比亚迪 (002594)", "multiplier": 100},
    ]

    return {
        "futures": futures_list,
        "stocks": common_stocks
    }

@router.post("/update")
async def trigger_data_update(
    background_tasks: BackgroundTasks
):
    background_tasks.add_task(daily_data_update)
    return {"message": "Data update task triggered in background"}
