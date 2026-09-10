
# # backend/visualizer_analyzer.py level 1
# import pandas as pd
# import numpy as np
# import math

# def _to_py(x):
#     try:
#         if pd.isna(x):
#             return None
#     except Exception:
#         pass
#     try:
#         if hasattr(x, "item"):
#             return x.item()
#     except Exception:
#         pass
#     return x

# class VisualizerAnalyzer:
#     def __init__(self, df: pd.DataFrame):
#         self.df = df.copy()

#     def preview(self, rows: int = 100):
#         dfp = self.df.head(rows)
#         preview_records = dfp.fillna("").to_dict(orient="records")
#         types = {c: str(self.df[c].dtype) for c in self.df.columns}
#         return {"rows": int(self.df.shape[0]), "columns": int(self.df.shape[1]), "types": types, "preview": preview_records}

#     def basic_summary(self):
#         missing_counts = self.df.isna().sum().to_dict()
#         duplicates = int(self.df.duplicated().sum())
#         numeric_cols = self.df.select_dtypes(include=["number"]).columns.tolist()
#         cat_cols = [c for c in self.df.columns if c not in numeric_cols]
#         return {"rows": int(self.df.shape[0]), "columns": int(self.df.shape[1]), "duplicates": duplicates, "missing_per_column": {k: int(v) for k, v in missing_counts.items()}, "numeric_columns": numeric_cols, "categorical_columns": cat_cols}

#     def numeric_stats(self):
#         num = self.df.select_dtypes(include=["number"])
#         if num.empty:
#             return {}
#         desc = num.describe().to_dict()
#         out = {}
#         for col, stats in desc.items():
#             out[col] = {k: _to_py(v) for k, v in stats.items()}
#             # add skewness/kurtosis
#             try:
#                 out[col]["skew"] = float(np.round(num[col].skew(), 4))
#                 out[col]["kurtosis"] = float(np.round(num[col].kurtosis(), 4))
#             except Exception:
#                 pass
#         return out

#     def correlation(self):
#         num = self.df.select_dtypes(include=["number"])
#         if num.empty:
#             return {}
#         corr = num.corr().round(4).to_dict()
#         out = {}
#         for k, v in corr.items():
#             out[k] = {kk: float(vv) if (vv is not None and not isinstance(vv, str)) else vv for kk, vv in v.items()}
#         return out

#     def top_values(self, col: str, n: int = 5):
#         if col not in self.df.columns:
#             return []
#         ser = self.df[col].value_counts().head(n)
#         return [{"value": _to_py(k), "count": int(v)} for k, v in ser.items()]

#     def anomaly_zscore(self, col: str, threshold: float = 3.0):
#         """Simple z-score anomaly detection for a numeric column."""
#         if col not in self.df.columns:
#             return []
#         ser = self.df[col].dropna()
#         if ser.empty:
#             return []
#         mean = ser.mean(); std = ser.std(ddof=0)
#         if std == 0 or math.isnan(std):
#             return []
#         z = (ser - mean) / std
#         anomalies = ser.loc[abs(z) > threshold]
#         return [{"index": int(idx), "value": float(v), "z": float(z.loc[idx])} for idx, v in anomalies.items()]

#     def recommend_chart(self, x: str = None, y: str = None):
#         """
#         Suggest chart type based on types of columns.
#         """
#         if x and y:
#             if pd.api.types.is_numeric_dtype(self.df[x]) and pd.api.types.is_numeric_dtype(self.df[y]):
#                 return "scatter"
#             if pd.api.types.is_numeric_dtype(self.df[y]) and not pd.api.types.is_numeric_dtype(self.df[x]):
#                 return "bar"
#             return "bar"
#         if x:
#             if pd.api.types.is_numeric_dtype(self.df[x]):
#                 return "histogram"
#             return "bar"
#         return "heatmap"

#     def insights(self, sample_top_n: int = 5):
#         b = self.basic_summary()
#         nstats = self.numeric_stats()
#         corr = self.correlation()
#         top_vals = {c: self.top_values(c, n=sample_top_n) for c in list(self.df.columns)[:6]}
#         return {"basic": b, "numeric_stats": nstats, "correlation": corr, "top_values_sample": top_vals}
    
import pandas as pd
import numpy as np
import math


def _to_py(x):
    try:
        if pd.isna(x):
            return None
    except Exception:
        pass
    try:
        if hasattr(x, "item"):
            return x.item()
    except Exception:
        pass
    return x


class VisualizerAnalyzer:
    def __init__(self, df: pd.DataFrame):
        if df is None or len(df) == 0:
            raise ValueError("Analyzer requires valid dataframe")
        self.df = df.copy()

    def preview(self, rows: int = 100):
        dfp = self.df.head(rows)
        return {
            "rows": len(self.df),
            "columns": len(self.df.columns),
            "types": {c: str(self.df[c].dtype) for c in self.df.columns},
            "preview": dfp.fillna("").to_dict("records")
        }

    def basic_summary(self):
        missing = self.df.isna().sum().to_dict()
        numeric_cols = self.df.select_dtypes(include=["number"]).columns.tolist()
        cat_cols = [c for c in self.df.columns if c not in numeric_cols]

        return {
            "rows": len(self.df),
            "columns": len(self.df.columns),
            "duplicates": int(self.df.duplicated().sum()),
            "missing": {k: int(v) for k, v in missing.items()},
            "numeric_columns": numeric_cols,
            "categorical_columns": cat_cols
        }

    def numeric_stats(self):
        num = self.df.select_dtypes(include=["number"])
        if num.empty:
            return {}

        desc = num.describe().to_dict()
        return {
            col: {k: _to_py(v) for k, v in stats.items()}
            for col, stats in desc.items()
        }

    def correlation(self):
        num = self.df.select_dtypes(include=["number"])
        if len(num.columns) < 2:
            return {}
        return num.corr().round(4).to_dict()

    def top_values(self, col: str, n: int = 5):
        if col not in self.df.columns:
            return []
        vc = self.df[col].value_counts().head(n)
        return [{"value": k, "count": int(v)} for k, v in vc.items()]

    def insights(self):
        return {
            "basic": self.basic_summary(),
            "numeric_stats": self.numeric_stats(),
            "correlation": self.correlation(),
            "top_values_sample": {
                c: self.top_values(c)
                for c in self.df.columns[:5]
            }
        }