import pandas as pd
import numpy as np

class DataProcessor:
    """
    数据预处理与质量评估模块
    负责数据清洗、转换、标准化和质量监控
    """
    
    @staticmethod
    def clean_data(df: pd.DataFrame) -> pd.DataFrame:
        """
        自动化数据清洗流程
        1. 处理缺失值 (插值)
        2. 去除重复索引
        3. 处理异常值 (简单的 winsorization 或 裁剪)
        """
        if df is None or df.empty:
            return df
            
        df_clean = df.copy()
        
        # 1. 去除重复索引
        df_clean = df_clean[~df_clean.index.duplicated(keep='last')]
        
        # 2. 处理缺失值 (线性插值，对于金融时间序列比较合理)
        df_clean.interpolate(method='linear', inplace=True)
        # 如果开头结尾有NaN，使用bfill/ffill
        df_clean.fillna(method='bfill', inplace=True)
        df_clean.fillna(method='ffill', inplace=True)
        
        # 3. 简单的异常值处理 (针对价格，不做过度处理以免失真，主要针对 volume < 0 等逻辑错误)
        if 'Volume' in df_clean.columns:
            df_clean.loc[df_clean['Volume'] < 0, 'Volume'] = 0
            
        # 针对 OHLC 的逻辑检查: High 必须 >= Low
        if 'High' in df_clean.columns and 'Low' in df_clean.columns:
             # 修复 High < Low 的情况 (交换)
             mask = df_clean['High'] < df_clean['Low']
             if mask.any():
                 df_clean.loc[mask, ['High', 'Low']] = df_clean.loc[mask, ['Low', 'High']].values
        
        return df_clean

    @staticmethod
    def detect_outliers(series: pd.Series, method='zscore', threshold=3):
        """
        检测异常值
        """
        if method == 'zscore':
            z_scores = np.abs((series - series.mean()) / series.std())
            return z_scores > threshold
        elif method == 'iqr':
            Q1 = series.quantile(0.25)
            Q3 = series.quantile(0.75)
            IQR = Q3 - Q1
            return (series < (Q1 - 1.5 * IQR)) | (series > (Q3 + 1.5 * IQR))
        return pd.Series([False] * len(series), index=series.index)

    @staticmethod
    def assess_quality(df: pd.DataFrame) -> dict:
        """
        建立数据质量评估指标
        """
        if df is None or df.empty:
            return {"score": 0, "issues": ["No data"]}
            
        issues = []
        score = 100
        
        # 1. 缺失值检查
        missing_count = df.isnull().sum().sum()
        if missing_count > 0:
            score -= min(20, missing_count / len(df) * 100)
            issues.append(f"Found {missing_count} missing values")
            
        # 2. 重复值检查 (索引)
        if df.index.duplicated().any():
            dup_count = df.index.duplicated().sum()
            score -= 10
            issues.append(f"Found {dup_count} duplicated timestamps")
            
        # 3. 连续性检查 (简单的gap检测)
        # 假设大部分间隔是一样的，检测异常间隔
        if len(df) > 10:
            diffs = df.index.to_series().diff().dropna()
            mode_diff = diffs.mode()[0]
            # 如果有超过 3 倍 mode_diff 的间隔 (排除周末/休市可能比较复杂，这里简化)
            # 这里简单统计异常间隔比例
            gaps = diffs[diffs > mode_diff * 5] # 5倍间隔视为断点
            if len(gaps) > 0:
                score -= min(10, len(gaps))
                issues.append(f"Found {len(gaps)} potential data gaps")
                
        # 4. 价格逻辑检查
        if 'High' in df.columns and 'Low' in df.columns:
            invalid_hl = (df['High'] < df['Low']).sum()
            if invalid_hl > 0:
                score -= 20
                issues.append(f"Found {invalid_hl} rows where High < Low")
                
        if 'Close' in df.columns:
            zeros = (df['Close'] == 0).sum()
            if zeros > 0:
                score -= 30
                issues.append(f"Found {zeros} rows with 0 price")

        return {
            "score": max(0, round(score, 1)),
            "issues": issues,
            "total_rows": len(df),
            "start_date": df.index[0].strftime('%Y-%m-%d') if not df.empty else None,
            "end_date": df.index[-1].strftime('%Y-%m-%d') if not df.empty else None
        }

    @staticmethod
    def normalize_data(df: pd.DataFrame, columns=None, method='minmax'):
        """
        数据标准化/归一化
        """
        if df is None or df.empty:
            return df
            
        df_norm = df.copy()
        cols_to_norm = columns if columns else [c for c in df.columns if np.issubdtype(df[c].dtype, np.number)]
        
        for col in cols_to_norm:
            if method == 'minmax':
                min_val = df[col].min()
                max_val = df[col].max()
                if max_val - min_val != 0:
                    df_norm[col] = (df[col] - min_val) / (max_val - min_val)
            elif method == 'zscore':
                mean_val = df[col].mean()
                std_val = df[col].std()
                if std_val != 0:
                    df_norm[col] = (df[col] - mean_val) / std_val
                    
        return df_norm
