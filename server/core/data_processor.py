import pandas as pd
import numpy as np

class DataProcessor:
    DEFAULT_RULES = {
        "required_columns": ["Open", "High", "Low", "Close"],
        "numeric_columns": ["Open", "High", "Low", "Close", "Volume", "OpenInterest", "Amount"],
        "min_values": {
            "Open": 0,
            "High": 0,
            "Low": 0,
            "Close": 0,
            "Volume": 0,
            "OpenInterest": 0,
            "Amount": 0,
        },
        "interpolate": True,
        "fill_methods": ["bfill", "ffill"],
        "clip_ohlc": True,
    }

    @staticmethod
    def clean_data(df: pd.DataFrame, rules: dict | None = None) -> pd.DataFrame:
        if df is None or df.empty:
            return df

        rule_set = dict(DataProcessor.DEFAULT_RULES)
        if rules:
            rule_set.update(rules)

        df_clean = df.copy()

        if not isinstance(df_clean.index, pd.DatetimeIndex):
            try:
                df_clean.index = pd.to_datetime(df_clean.index)
            except Exception:
                return df_clean.iloc[0:0]

        required_columns = rule_set.get("required_columns") or []
        for col in required_columns:
            if col not in df_clean.columns:
                return df_clean.iloc[0:0]

        df_clean = df_clean[~df_clean.index.duplicated(keep="last")]

        numeric_columns = rule_set.get("numeric_columns") or []
        for col in numeric_columns:
            if col in df_clean.columns:
                df_clean[col] = pd.to_numeric(df_clean[col], errors="coerce")

        if rule_set.get("interpolate"):
            df_clean = df_clean.infer_objects(copy=False)
            df_clean = df_clean.interpolate(method="linear")

        for method in rule_set.get("fill_methods") or []:
            if method == "ffill":
                df_clean = df_clean.ffill()
            elif method == "bfill":
                df_clean = df_clean.bfill()
            else:
                df_clean = df_clean.fillna(method=method)

        min_values = rule_set.get("min_values") or {}
        for col, min_val in min_values.items():
            if col in df_clean.columns and min_val is not None:
                df_clean.loc[df_clean[col] < min_val, col] = min_val

        if "High" in df_clean.columns and "Low" in df_clean.columns:
            mask = df_clean["High"] < df_clean["Low"]
            if mask.any():
                df_clean.loc[mask, ["High", "Low"]] = df_clean.loc[mask, ["Low", "High"]].values

        if rule_set.get("clip_ohlc") and "High" in df_clean.columns and "Low" in df_clean.columns:
            for col in ("Open", "Close"):
                if col in df_clean.columns:
                    df_clean[col] = df_clean[col].clip(lower=df_clean["Low"], upper=df_clean["High"])

        if required_columns:
            df_clean = df_clean.dropna(subset=required_columns)

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
