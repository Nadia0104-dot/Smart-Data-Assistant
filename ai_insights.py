# backend/ai_insights.py
import pandas as pd
import numpy as np
from typing import Dict, Any, List

def top_correlations(df: pd.DataFrame, top_n: int = 10):
    nums = df.select_dtypes(include=["number"]).dropna(axis=1, how="all")
    if nums.shape[1] < 2:
        return []
    corr = nums.corr().abs().stack().reset_index()
    corr.columns = ['x', 'y', 'corr']
    corr = corr[corr['x'] != corr['y']]
    corr = corr.sort_values('corr', ascending=False)
    # remove duplicates (x,y and y,x)
    seen = set()
    rows = []
    for _, r in corr.iterrows():
        pair = tuple(sorted([r['x'], r['y']]))
        if pair in seen: 
            continue
        seen.add(pair)
        rows.append({'x': r['x'], 'y': r['y'], 'corr': float(r['corr'])})
        if len(rows) >= top_n: break
    return rows

def detect_time_columns(df: pd.DataFrame) -> List[str]:
    cand = []
    for c in df.columns:
        s = df[c]
        try:
            if pd.api.types.is_datetime64_any_dtype(s):
                cand.append(c); continue
            name = c.lower()
            if any(k in name for k in ("date","time","year","month","day")):
                cand.append(c); continue
            sample = s.dropna().astype(str).head(40).tolist()
            if not sample: continue
            parse_ok = sum(1 for v in sample if is_parsable_date(v))
            if parse_ok >= max(3, len(sample)//3):
                cand.append(c)
        except Exception:
            pass
    return cand

def is_parsable_date(val: str) -> bool:
    try:
        pd.to_datetime(val)
        return True
    except Exception:
        return False

def distribution_summary(series: pd.Series) -> Dict[str, Any]:
    out = {}
    s = series.dropna()
    if s.empty:
        return out
    try:
        out['count'] = int(s.count())
        out['unique'] = int(s.nunique()) if hasattr(s, 'nunique') else None
        if pd.api.types.is_numeric_dtype(s):
            arr = s.astype(float)
            out.update({
                'min': float(arr.min()),
                'max': float(arr.max()),
                'median': float(arr.median()),
                'mean': float(arr.mean()),
                'std': float(arr.std(ddof=0)),
                'skew': float(arr.skew()),
            })
            # IQR outliers
            q1 = arr.quantile(0.25)
            q3 = arr.quantile(0.75)
            iqr = q3 - q1
            out['outlier_bounds'] = {'lower': float(q1 - 1.5*iqr), 'upper': float(q3 + 1.5*iqr)}
            out['outlier_count'] = int(((arr < (q1 - 1.5*iqr)) | (arr > (q3 + 1.5*iqr))).sum())
        else:
            top = s.astype(str).value_counts().head(10).to_dict()
            out['top'] = {str(k): int(v) for k, v in top.items()}
    except Exception:
        pass
    return out

def detect_anomalies(df: pd.DataFrame, numeric_cols=None, z_threshold: float = 3.5, max_rows:int=20):
    if numeric_cols is None:
        numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
    if not numeric_cols:
        return []
    numeric = df[numeric_cols].dropna(how='all')
    if numeric.empty:
        return []
    # compute z-score robustly with numpy
    arr = numeric.fillna(numeric.mean()).values.astype(float)
    mean = np.nanmean(arr, axis=0)
    std = np.nanstd(arr, axis=0)
    std[std == 0] = 1.0
    z = np.abs((arr - mean) / std)
    row_z = np.max(z, axis=1)
    idx = np.where(row_z > z_threshold)[0][:max_rows]
    return numeric.iloc[idx].head(max_rows).to_dict(orient='records')

def recommend_charts(df: pd.DataFrame, max_recs:int=5):
    recs = []
    nums = df.select_dtypes(include=["number"]).columns.tolist()
    cats = df.select_dtypes(exclude=["number","datetime"]).columns.tolist()
    times = detect_time_columns(df)
    if times and nums:
        recs.append({'type':'line', 'x': times[0], 'y': nums[0], 'reason':'Time-series detected; show trend.'})
    corr_pairs = top_correlations(df, top_n=5)
    if corr_pairs:
        top = corr_pairs[0]
        recs.append({'type':'scatter', 'x': top['x'], 'y': top['y'], 'reason':f"High correlation ({top['corr']:.2f})"})
    if nums:
        recs.append({'type':'histogram', 'y': nums[0], 'reason':'Distribution of numeric column.'})
    if cats:
        recs.append({'type':'bar', 'x': cats[0], 'reason':'Counts by category.'})
    if len(nums) >= 3:
        recs.append({'type':'heatmap', 'reason':'Correlation heatmap.'})
    return recs[:max_recs]

def full_insights(df: pd.DataFrame) -> Dict[str, Any]:
    out = {}
    out['summary'] = {
        'rows': int(df.shape[0]),
        'columns': int(df.shape[1]),
        'numeric_columns': df.select_dtypes(include=["number"]).columns.tolist(),
        'categorical_columns': df.select_dtypes(exclude=["number","datetime"]).columns.tolist()
    }
    col_summ = {}
    for c in list(df.columns)[:20]:
        try:
            col_summ[c] = distribution_summary(df[c])
        except Exception:
            col_summ[c] = {}
    out['column_summary'] = col_summ
    out['time_columns'] = detect_time_columns(df)
    out['top_correlations'] = top_correlations(df, top_n=10)
    out['recommendations'] = recommend_charts(df, max_recs=6)
    out['anomalies_sample'] = detect_anomalies(df)
    return out
