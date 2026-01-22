import pandas as pd
from .data_manager import data_manager

def infer_asset_type(symbol: str) -> str:
    s = str(symbol).strip().upper()
    if s.startswith("SH") or s.startswith("SZ"):
        return "stock"
    if s.endswith(".SH") or s.endswith(".SZ"):
        return "stock"
    if s.isdigit() and len(s) == 6:
        return "stock"
    return "futures"

def fetch_futures_data(symbol='LH0', period='5', start_date=None, end_date=None):
    return data_manager.get_data_with_fallback(symbol, period, start_date, end_date, asset_type="futures")

def fetch_stock_data(symbol, period='daily', start_date=None, end_date=None):
    code = str(symbol).upper().strip()
    if code.startswith("SH") or code.startswith("SZ"):
        code = code[2:]
    if code.endswith(".SH") or code.endswith(".SZ"):
        code = code[:-3]
    return data_manager.get_data_with_fallback(code, period, start_date, end_date, asset_type="stock")

def fetch_lh_data(period='5', adjust='0'):
    return fetch_futures_data(symbol='LH0', period=period)

if __name__ == "__main__":
    # 测试获取数据
    df = fetch_lh_data(period='5')
    if df is not None:
        print(df.head())
        print(df.tail())
