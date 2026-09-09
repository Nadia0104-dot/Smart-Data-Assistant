# cleaner_analyzer.py
# Utilities to perform dataframe cleaning operations used by cleaner.py
# Dependencies: pandas, numpy

import io
import re
from typing import Dict, Any, Tuple, List

import pandas as pd
import numpy as np

from sklearn.impute import KNNImputer
from sklearn.preprocessing import RobustScaler

# Helper: keep a working copy in memory in caller (cleaner.py)
# Functions operate on and return DataFrames (in-memory).

def df_summary(df: pd.DataFrame) -> Dict[str, Any]:
    """Return basic summary stats used by frontend."""
    rows, cols = df.shape
    duplicates = int(df.duplicated().sum())
    missing_total = int(df.isna().sum().sum())
    # simple outlier estimation (IQR) — count rows with any column flagged as outlier
    outlier_mask = pd.DataFrame(False, index=df.index, columns=df.columns)
    outlier_count = 0
    try:
        numeric = df.select_dtypes(include=[np.number])
        for c in numeric.columns:
            col = numeric[c].dropna()
            if col.empty:
                continue
            q1 = col.quantile(0.25)
            q3 = col.quantile(0.75)
            iqr = q3 - q1
            if iqr == 0:
                continue
            low = q1 - 1.5 * iqr
            high = q3 + 1.5 * iqr
            mask = (df[c] < low) | (df[c] > high)
            outlier_mask.loc[mask.index, c] = mask.fillna(False)
        outlier_rows = outlier_mask.any(axis=1)
        outlier_count = int(outlier_rows.sum())
    except Exception:
        outlier_count = 0

    # skew detection (> |1|)
    skewed = 0
    try:
        numeric = df.select_dtypes(include=[np.number]).dropna(axis=1, how='all')
        if not numeric.empty:
            skew_vals = numeric.skew().abs()
            skewed = int((skew_vals > 1).sum())
    except Exception:
        skewed = 0

    return {
        "rows": rows,
        "columns": cols,
        "duplicates": duplicates,
        "missing": missing_total,
        "outliers": outlier_count,
        "skewed": skewed
    }

def get_column_types(df: pd.DataFrame) -> Dict[str, str]:
    """Return a mapping of column → dtype name (string)."""
    dtypes = {}
    for col in df.columns:
        dtype = str(df[col].dtype)
        dtypes[col] = dtype
    return dtypes

def df_preview_html(df: pd.DataFrame, max_rows: int = 100) -> str:
    """Return HTML table for preview. Uses classes cell-missing and row-duplicate."""
    if df is None or df.empty:
        return "<div class='muted'>No data</div>"
    preview = df.head(max_rows).copy()
    # prepare header
    html = ["<div class='table-container'><table class='preview'>"]
    html.append("<thead><tr>")
    for col in preview.columns:
        html.append(f"<th>{escape_html(str(col))}</th>")
    html.append("</tr></thead><tbody>")
    dup_mask = df.duplicated(keep=False)
    # we show duplicates for rows present in preview by index
    for idx, row in preview.iterrows():
        row_class = "row-duplicate" if bool(dup_mask.loc[idx]) else ""
        html.append(f"<tr class='{row_class}'>")
        for col in preview.columns:
            val = row[col]
            cell_class = "cell-missing" if pd.isna(val) else ""
            display = "" if pd.isna(val) else escape_html(truncate_str(val))
            html.append(f"<td class='{cell_class}' title='{escape_html(str(val))}'>{display}</td>")
        html.append("</tr>")
    html.append("</tbody></table></div>")
    return "".join(html)

def escape_html(s: Any) -> str:
    s = "" if s is None else str(s)
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;").replace("'", "&#39;"))

def truncate_str(v: Any, length: int = 120) -> str:
    s = "" if v is None else str(v)
    if len(s) > length:
        return s[:length-3] + "..."
    return s

# --- Cleaning operations ---

def remove_duplicates(df: pd.DataFrame, keep: str = "first") -> pd.DataFrame:
    before = len(df)
    out = df.drop_duplicates(keep=keep)

    # debug trace (optional but VERY useful)
    print(f"[REMOVE DUPLICATES] {before} → {len(out)} rows removed: {before - len(out)}")

    return out.reset_index(drop=True)

def drop_missing_rows(df: pd.DataFrame, how: str = "any", thresh: int = None) -> pd.DataFrame:
    # how: 'any' or 'all'. thresh: integer minimum non-null values required.
    if thresh is not None:
        return df.dropna(axis=0, thresh=thresh).reset_index(drop=True)
    return df.dropna(axis=0, how=how).reset_index(drop=True)

def remove_outliers_iqr(df: pd.DataFrame, cols: List[str] = None) -> pd.DataFrame:
    if cols is None:
        numeric = df.select_dtypes(include=[np.number]).columns.tolist()
    else:
        numeric = [c for c in cols if c in df.columns]
    out_df = df.copy()
    for c in numeric:
        col = out_df[c]
        nonnull = col.dropna()
        if nonnull.empty:
            continue
        q1 = nonnull.quantile(0.25)
        q3 = nonnull.quantile(0.75)
        iqr = q3 - q1
        if iqr == 0:
            continue
        low = q1 - 1.5 * iqr
        high = q3 + 1.5 * iqr
        out_df = out_df[(out_df[c].isna()) | ((out_df[c] >= low) & (out_df[c] <= high))]
    return out_df.reset_index(drop=True)

# def normalize_df(df: pd.DataFrame, cols: List[str] = None) -> pd.DataFrame:
    out = df.copy()
    if cols is None:
        cols = out.select_dtypes(include=[np.number]).columns.tolist()
    for c in cols:
        try:
            col = out[c].astype(float)
            minv = col.min()
            maxv = col.max()
            if pd.isna(minv) or pd.isna(maxv) or maxv == minv:
                continue
            out[c] = (col - minv) / (maxv - minv)
        except Exception:
            continue
    return out

def normalize_df(df: pd.DataFrame, cols: List[str] = None) -> pd.DataFrame:
    out = df.copy()

    if cols is None:
        cols = out.select_dtypes(include=[np.number]).columns.tolist()

    for c in cols:
        if c not in out.columns:
            continue

        col = pd.to_numeric(out[c], errors="coerce")
        minv = col.min()
        maxv = col.max()

        if pd.isna(minv) or pd.isna(maxv) or maxv == minv:
            continue

        out[c] = (col - minv) / (maxv - minv)

    return out

# def standardize_df(df: pd.DataFrame, cols: List[str] = None) -> pd.DataFrame:
    out = df.copy()
    if cols is None:
        cols = out.select_dtypes(include=[np.number]).columns.tolist()
    for c in cols:
        try:
            col = out[c].astype(float)
            mean = col.mean()
            std = col.std(ddof=0)
            if pd.isna(std) or std == 0:
                continue
            out[c] = (col - mean) / std
        except Exception:
            continue
    return out

def standardize_df(df: pd.DataFrame, cols: List[str] = None) -> pd.DataFrame:
    out = df.copy()

    if cols is None:
        cols = out.select_dtypes(include=[np.number]).columns.tolist()

    for c in cols:
        if c not in out.columns:
            continue

        col = pd.to_numeric(out[c], errors="coerce")
        mean = col.mean()
        std = col.std(ddof=0)

        if pd.isna(std) or std == 0:
            continue

        out[c] = (col - mean) / std

    return out

def trim_spaces_df(df: pd.DataFrame, cols: List[str] = None) -> pd.DataFrame:
    out = df.copy()
    if cols is None:
        cols = out.select_dtypes(include=['object', 'string']).columns.tolist()
    for c in cols:
        try:
            out[c] = out[c].astype(str).where(~out[c].isna(), other=np.nan).str.strip()
        except Exception:
            continue
    return out

def to_lowercase_df(df: pd.DataFrame, cols: List[str] = None) -> pd.DataFrame:
    out = df.copy()
    if cols is None:
        cols = out.select_dtypes(include=['object', 'string']).columns.tolist()
    for c in cols:
        try:
            out[c] = out[c].astype(str).where(~out[c].isna(), other=np.nan).str.lower()
        except Exception:
            continue
    return out

def to_uppercase_df(df: pd.DataFrame, cols: List[str] = None) -> pd.DataFrame:
    out = df.copy()
    if cols is None:
        cols = out.select_dtypes(include=['object', 'string']).columns.tolist()
    for c in cols:
        try:
            out[c] = out[c].astype(str).where(~out[c].isna(), other=np.nan).str.upper()
        except Exception:
            continue
    return out

def remove_special_chars_df(df: pd.DataFrame, cols: List[str] = None, pattern: str = r'[^0-9A-Za-z\s\-_.,]') -> pd.DataFrame:
    out = df.copy()
    if cols is None:
        cols = out.select_dtypes(include=['object', 'string']).columns.tolist()
    prog = re.compile(pattern)
    for c in cols:
        try:
            out[c] = out[c].astype(str).where(~out[c].isna(), other=np.nan).apply(lambda x: prog.sub('', x) if pd.notna(x) else x)
        except Exception:
            continue
    return out

def regex_replace_df(df: pd.DataFrame, column: str, pattern: str, replacement: str, flags=0) -> pd.DataFrame:
    out = df.copy()
    if column not in out.columns:
        return out
    try:
        out[column] = out[column].astype(str).where(~out[column].isna(), other=np.nan).str.replace(pattern, replacement, regex=True)
    except Exception:
        pass
    return out

def extract_substring_df(df: pd.DataFrame, column: str, start: int, end: int = None) -> pd.DataFrame:
    out = df.copy()
    if column not in out.columns:
        return out
    try:
        start = int(start)
        if end is None or end == "":
            out[column] = out[column].astype(str).where(~out[column].isna(), other=np.nan).str.slice(start)
        else:
            out[column] = out[column].astype(str).where(~out[column].isna(), other=np.nan).str.slice(start, int(end))
    except Exception:
        pass
    return out

def format_date_df(df: pd.DataFrame, column: str, fmt: str) -> pd.DataFrame:
    out = df.copy()
    if column not in out.columns:
        return out
    try:
        out[column] = pd.to_datetime(out[column], errors='coerce').dt.strftime(fmt)
    except Exception:
        pass
    return out

def drop_column_df(df: pd.DataFrame, column: str) -> pd.DataFrame:
    if column not in df.columns:
        return df
    return df.drop(columns=[column]).reset_index(drop=True)

def convert_dtype_df(df: pd.DataFrame, column: str, dtype: str) -> pd.DataFrame:
    out = df.copy()
    if column not in out.columns:
        return out
    try:
        if dtype in ('int', 'integer'):
            out[column] = pd.to_numeric(out[column], errors='coerce').astype('Int64')
        elif dtype in ('float',):
            out[column] = pd.to_numeric(out[column], errors='coerce').astype(float)
        elif dtype in ('str', 'string'):
            out[column] = out[column].astype(str).where(~out[column].isna(), other=np.nan)
        elif dtype in ('date', 'datetime'):
            out[column] = pd.to_datetime(out[column], errors='coerce')
    except Exception:
        pass
    return out

# def auto_fix_dtypes(df: pd.DataFrame) -> pd.DataFrame:
#     """
#     Production-grade dtype fixer:
#     - detects dates properly
#     - keeps numeric stable
#     - avoids corrupt conversions
#     """

#     out = df.copy()

#     for col in out.columns:

#         series = out[col]

#         # skip already numeric
#         if pd.api.types.is_numeric_dtype(series):
#             continue

#         # STEP 1: try strict datetime conversion
#         try:
#             parsed = pd.to_datetime(series, errors="coerce", infer_datetime_format=True)

#             # only accept if MOST values converted successfully
#             success_rate = parsed.notna().mean()

#             if success_rate > 0.7:   # threshold is IMPORTANT
#                 out[col] = parsed
#                 continue
#         except Exception:
#             pass

#         # STEP 2: try numeric
#         try:
#             numeric = pd.to_numeric(series, errors="coerce")
#             success_rate = numeric.notna().mean()

#             if success_rate > 0.8:
#                 out[col] = numeric
#                 continue
#         except Exception:
#             pass

#         # STEP 3: keep string
#         out[col] = series.astype(str)

#     return out

def fill_missing_df(df: pd.DataFrame, method: str = "mean") -> pd.DataFrame:
    out = df.copy()
    if method == "mean":
        for c in out.select_dtypes(include=[np.number]).columns:
            try:
                out[c] = out[c].fillna(out[c].mean())
            except Exception:
                continue
    elif method == "median":
        for c in out.select_dtypes(include=[np.number]).columns:
            try:
                out[c] = out[c].fillna(out[c].median())
            except Exception:
                continue
    elif method == "mode":
        for c in out.columns:
            try:
                mode = out[c].mode(dropna=True)
                if not mode.empty:
                    out[c] = out[c].fillna(mode.iloc[0])
            except Exception:
                continue
    return out

# --- Auto-clean pipeline (combination of recommended actions) ---
def auto_clean_pipeline(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    d = df.copy()
    # remove exact duplicates
    d = remove_duplicates(d)
    # drop rows with any missing (as per UI spec)
    d = drop_missing_rows(d, how="any")
    # fill numeric missing (fallback) - but since we dropped any missing rows, it's mostly safe
    d = fill_missing_df(d, method="mean")
    # normalize then standardize numeric columns
    d = normalize_df(d)
    d = standardize_df(d)
    # remove outliers
    d = remove_outliers_iqr(d)
    summary = df_summary(d)
    return d.reset_index(drop=True), summary

# --- Utility: convert df to CSV bytes ---
def df_to_csv_bytes(df: pd.DataFrame) -> bytes:
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    return buf.getvalue().encode("utf-8")

# =========================================================
# ADVANCED CLEANING FUNCTIONS
# =========================================================

def remove_empty_columns_df(df: pd.DataFrame, threshold: float = 0.9) -> pd.DataFrame:
    """
    Remove columns having more than threshold missing values.
    """
    out = df.copy()

    remove_cols = []

    for col in out.columns:
        missing_ratio = out[col].isna().mean()

        if missing_ratio >= threshold:
            remove_cols.append(col)

    return out.drop(columns=remove_cols)


def smart_fill_missing_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Smart filling:
    Numeric -> median
    Text -> mode
    """
    out = df.copy()

    for col in out.columns:

        if out[col].dtype in ['int64', 'float64']:

            try:
                out[col] = out[col].fillna(out[col].median())
            except:
                pass

        else:

            try:
                mode = out[col].mode(dropna=True)

                if not mode.empty:
                    out[col] = out[col].fillna(mode.iloc[0])

            except:
                pass

    return out


def knn_fill_missing_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Advanced missing value imputation using KNN.
    """

    out = df.copy()

    numeric_cols = out.select_dtypes(include=[np.number]).columns

    if len(numeric_cols) == 0:
        return out

    try:
        imputer = KNNImputer(n_neighbors=5)

        out[numeric_cols] = imputer.fit_transform(out[numeric_cols])

    except:
        pass

    return out


def remove_highly_correlated_df(df: pd.DataFrame, threshold: float = 0.95) -> pd.DataFrame:
    """
    Remove highly correlated columns.
    """

    out = df.copy()

    numeric_df = out.select_dtypes(include=[np.number])

    if numeric_df.empty:
        return out

    corr_matrix = numeric_df.corr().abs()

    upper = corr_matrix.where(
        np.triu(np.ones(corr_matrix.shape), k=1).astype(bool)
    )

    drop_cols = [
        column for column in upper.columns
        if any(upper[column] > threshold)
    ]

    return out.drop(columns=drop_cols)


# def robust_scale_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Robust scaling less sensitive to outliers.
    """

    out = df.copy()

    numeric_cols = out.select_dtypes(include=[np.number]).columns

    if len(numeric_cols) == 0:
        return out

    try:
        scaler = RobustScaler()

        out[numeric_cols] = scaler.fit_transform(out[numeric_cols])

    except:
        pass

    return out
def robust_scale_df(df: pd.DataFrame, cols: List[str] = None) -> pd.DataFrame:
    """
    Uses median & IQR (best for real datasets)
    """
    out = df.copy()

    if cols is None:
        cols = out.select_dtypes(include=[np.number]).columns.tolist()

    for c in cols:
        col = pd.to_numeric(out[c], errors="coerce")

        median = col.median()
        q1 = col.quantile(0.25)
        q3 = col.quantile(0.75)
        iqr = q3 - q1

        if iqr == 0 or pd.isna(iqr):
            continue

        out[c] = (col - median) / iqr

    return out


def auto_fix_dtypes(df: pd.DataFrame) -> pd.DataFrame:
    """
    Smart dtype detection:
    - numeric stays numeric
    - date-like columns → datetime
    - rest → string
    """
    out = df.copy()

    for col in out.columns:
        if out[col].dtype in ["int64", "float64", "Int64"]:
            continue

        # try datetime first
        try:
            converted = pd.to_datetime(out[col], errors="raise", infer_datetime_format=True)
            out[col] = converted
            continue
        except Exception:
            pass

        # try numeric
        try:
            converted = pd.to_numeric(out[col], errors="raise")
            out[col] = converted
            continue
        except Exception:
            pass

        # fallback string
        out[col] = out[col].astype(str)

    return out

def remove_constant_columns_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Remove columns with only one unique value.
    """

    out = df.copy()

    constant_cols = []

    for col in out.columns:

        try:
            if out[col].nunique(dropna=False) <= 1:
                constant_cols.append(col)
        except:
            pass

    return out.drop(columns=constant_cols)


def clean_column_names_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean messy column names.
    """

    out = df.copy()

    cleaned = []

    for col in out.columns:

        col = str(col)

        col = col.strip().lower()

        col = re.sub(r'[^a-zA-Z0-9]+', '_', col)

        col = re.sub(r'_+', '_', col)

        col = col.strip('_')

        cleaned.append(col)

    out.columns = cleaned

    return out


def remove_html_tags_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Remove HTML tags from text columns.
    """

    out = df.copy()

    cols = out.select_dtypes(include=['object', 'string']).columns

    clean = re.compile('<.*?>')

    for col in cols:

        try:
            out[col] = out[col].astype(str).apply(
                lambda x: re.sub(clean, '', x) if pd.notna(x) else x
            )

        except:
            pass

    return out


def remove_extra_whitespace_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Remove extra spaces/tabs/newlines.
    """

    out = df.copy()

    cols = out.select_dtypes(include=['object', 'string']).columns

    for col in cols:

        try:
            out[col] = out[col].astype(str).apply(
                lambda x: re.sub(r'\s+', ' ', x).strip()
                if pd.notna(x) else x
            )

        except:
            pass

    return out


# =========================================================
# ULTRA AI AUTO CLEANER
# =========================================================

def advanced_auto_clean_pipeline(df: pd.DataFrame):

    original_rows = len(df)

    d = df.copy()

    # Column cleanup
    d = clean_column_names_df(d)

    # Trim spaces
    d = trim_spaces_df(d)

    # Remove extra whitespace
    d = remove_extra_whitespace_df(d)

    # Remove html
    d = remove_html_tags_df(d)

    # Fix datatypes

    d = auto_fix_dtypes(d)
    # Remove duplicates
    d = remove_duplicates(d)

    # Remove empty cols
    d = remove_empty_columns_df(d)

    # Remove constant cols
    d = remove_constant_columns_df(d)

    # Fill missing smartly
    d = smart_fill_missing_df(d)

    # KNN advanced imputation
    d = knn_fill_missing_df(d)

    # Remove outliers
    d = remove_outliers_iqr(d)

    # Remove high correlation
    d = remove_highly_correlated_df(d)

    # Robust scaling
    d = robust_scale_df(d)

    summary = df_summary(d)

    summary["cleaned_rows_removed"] = original_rows - len(d)

    return d.reset_index(drop=True), summary