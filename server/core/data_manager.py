import os
import pandas as pd
# import akshare as ak  # Moved to lazy import
import datetime
import traceback

# 定义数据存储路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "storage", "data")

class DataManager:
    def __init__(self):
        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR)

    def _get_file_path(self, symbol, period):
        symbol_dir = os.path.join(DATA_DIR, symbol)
        if not os.path.exists(symbol_dir):
            os.makedirs(symbol_dir)
        return os.path.join(symbol_dir, f"{period}.csv")

    def get_symbols_list(self):
        """
        获取品种列表，优先从本地缓存读取
        """
        cache_path = os.path.join(DATA_DIR, "symbols_cache.json")
        if os.path.exists(cache_path):
            try:
                # 检查文件修改时间，比如超过 24 小时才刷新
                # 但这里我们主要目的是持久化，所以只要有就用，更新交给 daily_update
                import json
                with open(cache_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data
            except Exception as e:
                print(f"Error loading symbols cache: {e}")
        return None

    def save_symbols_list(self, symbols_list):
        """
        保存品种列表到本地
        """
        cache_path = os.path.join(DATA_DIR, "symbols_cache.json")
        try:
            import json
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(symbols_list, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving symbols cache: {e}")

    def load_data(self, symbol, period, start_date=None, end_date=None):
        """
        从本地加载数据，如果本地没有或强制刷新，则不在此处理（由 update_data 处理）
        这里假设调用者会先尝试加载，如果返回 None 再尝试 fetch
        或者我们可以让 get_data 封装 fetch 逻辑
        """
        file_path = self._get_file_path(symbol, period)
        if not os.path.exists(file_path):
            return None
        
        try:
            # 读取 CSV
            df = pd.read_csv(file_path)
            
            # 恢复索引
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'])
                df.set_index('date', inplace=True)
            elif 'datetime' in df.columns:
                df['datetime'] = pd.to_datetime(df['datetime'])
                df.set_index('datetime', inplace=True)
            else:
                # 尝试猜测
                first_col = df.columns[0]
                df[first_col] = pd.to_datetime(df[first_col])
                df.set_index(first_col, inplace=True)

            # 过滤日期
            if start_date:
                df = df[df.index >= pd.to_datetime(start_date)]
            if end_date:
                end_dt = pd.to_datetime(end_date) + pd.Timedelta(days=1)
                df = df[df.index < end_dt]
            
            return df
        except Exception as e:
            print(f"Error loading local data for {symbol} {period}: {e}")
            return None

    def fetch_and_update(self, symbol, period, asset_type="futures"):
        """
        从 AkShare 获取数据并更新本地存储
        """
        print(f"Fetching data for {symbol} ({period})...")
        try:
            import akshare as ak
            new_df = None
            if period == 'weekly':
                df_daily = self.fetch_and_update(symbol, 'daily', asset_type=asset_type)
                if df_daily is None or df_daily.empty:
                    return None
                agg_dict = {
                    'Open': 'first',
                    'High': 'max',
                    'Low': 'min',
                    'Close': 'last',
                    'Volume': 'sum',
                    'OpenInterest': 'last'
                }
                agg_dict = {k: v for k, v in agg_dict.items() if k in df_daily.columns}
                new_df = df_daily.resample('W-FRI').agg(agg_dict)
                new_df.dropna(inplace=True)
            elif period == 'daily':
                if asset_type == "stock":
                    new_df = ak.stock_zh_a_hist(symbol=symbol, period="daily", adjust="qfq")
                    new_df.rename(columns={
                        '日期': 'date',
                        '开盘': 'Open',
                        '最高': 'High',
                        '最低': 'Low',
                        '收盘': 'Close',
                        '成交量': 'Volume'
                    }, inplace=True)
                    new_df['date'] = pd.to_datetime(new_df['date'])
                    new_df.set_index('date', inplace=True)
                else:
                    new_df = ak.futures_zh_daily_sina(symbol=symbol)
                    new_df.rename(columns={
                        'date': 'date', 'open': 'Open', 'high': 'High', 'low': 'Low',
                        'close': 'Close', 'volume': 'Volume', 'hold': 'OpenInterest'
                    }, inplace=True)
                    new_df['date'] = pd.to_datetime(new_df['date'])
                    new_df.set_index('date', inplace=True)
            else:
                if asset_type == "stock":
                    new_df = ak.stock_zh_a_hist_min_em(symbol=symbol, period=period, adjust="qfq")
                    new_df.rename(columns={
                        '时间': 'datetime',
                        '开盘': 'Open',
                        '最高': 'High',
                        '最低': 'Low',
                        '收盘': 'Close',
                        '成交量': 'Volume'
                    }, inplace=True)
                    new_df['datetime'] = pd.to_datetime(new_df['datetime'])
                    new_df.set_index('datetime', inplace=True)
                else:
                    new_df = ak.futures_zh_minute_sina(symbol=symbol, period=period)
                    new_df.rename(columns={
                        'datetime': 'datetime', 'open': 'Open', 'high': 'High', 'low': 'Low',
                        'close': 'Close', 'volume': 'Volume', 'hold': 'OpenInterest'
                    }, inplace=True)
                    new_df['datetime'] = pd.to_datetime(new_df['datetime'])
                    new_df.set_index('datetime', inplace=True)

            # 转换数值列
            cols = ['Open', 'High', 'Low', 'Close', 'Volume', 'OpenInterest']
            for col in cols:
                if col in new_df.columns:
                    new_df[col] = pd.to_numeric(new_df[col], errors='coerce')
            
            # 保存逻辑
            file_path = self._get_file_path(symbol, period)
            
            if os.path.exists(file_path):
                # 如果文件存在，合并
                old_df = self.load_data(symbol, period)
                if old_df is not None:
                    # 合并并去重
                    combined_df = pd.concat([old_df, new_df])
                    combined_df = combined_df[~combined_df.index.duplicated(keep='last')]
                    combined_df.sort_index(inplace=True)
                    final_df = combined_df
                else:
                    final_df = new_df
            else:
                final_df = new_df
            
            # 保存到 CSV
            final_df.to_csv(file_path)
            print(f"Updated {symbol} {period} data. Total rows: {len(final_df)}")
            return final_df
            
        except Exception as e:
            print(f"Failed to fetch/update data for {symbol} {period}: {e}")
            traceback.print_exc()
            return None

    def get_data_with_fallback(self, symbol, period, start_date=None, end_date=None, asset_type="futures"):
        """
        优先读取本地，如果本地没有或需要更新（简单的策略是：如果本地没有则下载），
        为了性能，我们假设如果有本地文件，就直接用。
        自动更新任务由后台调度器负责。
        """
        df = self.load_data(symbol, period, start_date, end_date)
        
        # 如果本地没有数据，强制下载
        if df is None or df.empty:
            print(f"No local data for {symbol} {period}, fetching...")
            full_df = self.fetch_and_update(symbol, period, asset_type=asset_type)
            if full_df is not None:
                # 重新应用日期过滤
                df = full_df
                if start_date:
                    df = df[df.index >= pd.to_datetime(start_date)]
                if end_date:
                    end_dt = pd.to_datetime(end_date) + pd.Timedelta(days=1)
                    df = df[df.index < end_dt]
        
        return df

data_manager = DataManager()
