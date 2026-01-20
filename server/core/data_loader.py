import pandas as pd
from .data_manager import data_manager

def fetch_futures_data(symbol='LH0', period='5', start_date=None, end_date=None):
    """
    获取期货主力合约数据 (通用)
    :param symbol: 合约代码，如 'LH0' (生猪), 'SH0' (烧碱)
    :param period: 周期，'daily' (日线), '1', '5', '15', '30', '60' 分钟
    :param start_date: 开始日期 (YYYY-MM-DD)
    :param end_date: 结束日期 (YYYY-MM-DD)
    :return: Pandas DataFrame 格式的 OHLC 数据
    """
    return data_manager.get_data_with_fallback(symbol, period, start_date, end_date)

def fetch_lh_data(period='5', adjust='0'):
    return fetch_futures_data(symbol='LH0', period=period)

if __name__ == "__main__":
    # 测试获取数据
    df = fetch_lh_data(period='5')
    if df is not None:
        print(df.head())
        print(df.tail())
