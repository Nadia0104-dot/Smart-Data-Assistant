# # backend/ai_chart_builder.py level 1
# """
# Lightweight local "AI" chart builder.
# Parses a user prompt and returns a suggested Plotly chart configuration.
# This is rule-based and intended as an offline-first assistant — replaceable with a real LLM later.
# """

# from typing import Dict, Any
# import re
# import pandas as pd
# import numpy as np
# from collections import Counter


# def _is_time_series_col(s: pd.Series) -> bool:
#     # heuristics: datetime dtype or name contains year/month/date/time
#     name = s.name.lower()
#     if pd.api.types.is_datetime64_any_dtype(s):
#         return True
#     if any(k in name for k in ("date", "time", "year", "month", "day")):
#         return True
#     # values appear to be years?
#     try:
#         vals = s.dropna().astype(str).head(20).tolist()
#         if all(re.match(r'^\d{4}$', v) for v in vals):
#             return True
#     except Exception:
#         pass
#     return False


# def _num_unique_ratio(s: pd.Series):
#     try:
#         return s.nunique() / max(1, len(s))
#     except Exception:
#         return 1.0


# def suggest_from_prompt(df: pd.DataFrame, prompt: str) -> Dict[str, Any]:
#     """
#     Analyze dataframe and the user's prompt and return:
#     {
#       "chart_type": "line"/"bar"/"scatter"/"histogram"/"heatmap"/"pie"/"area",
#       "x_column": "colname" or None,
#       "y_column": "colname" or None,
#       "color": "colname" or None,
#       "filters": {...}
#     }
#     """
#     prompt_l = prompt.lower().strip()
#     tokens = re.findall(r"[a-zA-Z0-9_]+", prompt_l)

#     numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
#     cat_cols = df.select_dtypes(exclude=["number", "datetime"]).columns.tolist()
#     dt_cols = [c for c in df.columns if _is_time_series_col(df[c])]
#     # prioritize datetime for x if present
#     x_col = None
#     y_col = None
#     color = None
#     chart_type = None
#     filters = {}

#     # detect explicit "by <col>" or "by <col1> and <col2>"
#     m_by = re.search(r"by ([a-z0-9_ ]+)", prompt_l)
#     if m_by:
#         cand = m_by.group(1).strip()
#         # pick first matching column name by containment
#         for col in df.columns:
#             if col.lower() in cand or cand in col.lower():
#                 x_col = col
#                 break

#     # detect operations: "trend", "trendline", "compare", "compare with", "compare to"
#     if "trend" in prompt_l or "trendline" in prompt_l or "monthly" in prompt_l or "weekly" in prompt_l:
#         chart_type = "line"
#         # choose time col for x if available
#         if dt_cols:
#             x_col = dt_cols[0]
#         # pick top numeric as y
#         if numeric_cols:
#             y_col = numeric_cols[0]
#     if "compare" in prompt_l or "vs" in prompt_l or "compare with" in prompt_l:
#         # choose scatter when two numeric columns mentioned
#         chart_type = "scatter"
#         # if user mentions two columns explicitly, use them
#         col_matches = [c for c in df.columns if c.lower() in prompt_l]
#         if len(col_matches) >= 2:
#             x_col, y_col = col_matches[0], col_matches[1]
#         else:
#             # otherwise first two numerics
#             if len(numeric_cols) >= 2:
#                 x_col, y_col = numeric_cols[0], numeric_cols[1]
#     if "distribution" in prompt_l or "histogram" in prompt_l or "distribution of" in prompt_l:
#         chart_type = "histogram"
#         # find mentioned col or top numeric
#         col_match = next((c for c in df.columns if c.lower() in prompt_l), None)
#         if col_match:
#             y_col = col_match
#         elif numeric_cols:
#             y_col = numeric_cols[0]
#     if "heatmap" in prompt_l or "correlation" in prompt_l:
#         chart_type = "heatmap"
#     if "bar" in prompt_l or "count of" in prompt_l or "top" in prompt_l:
#         chart_type = "bar"
#         # choose categorical for x
#         if cat_cols:
#             x_col = cat_cols[0]
#         elif df.columns.any():
#             x_col = df.columns[0]
#         if numeric_cols:
#             y_col = numeric_cols[0]
#     if "pie" in prompt_l or "donut" in prompt_l:
#         chart_type = "pie"
#         if cat_cols:
#             x_col = cat_cols[0]

#     # fallback heuristics if not set
#     if not chart_type:
#         # if prompt mentions time series words, use line
#         if any(k in prompt_l for k in ("month", "year", "trend", "daily", "weekly")) and dt_cols:
#             chart_type = "line"
#             x_col = x_col or dt_cols[0]
#             y_col = y_col or (numeric_cols[0] if numeric_cols else None)
#         elif len(numeric_cols) >= 2:
#             chart_type = "scatter"
#             x_col = x_col or numeric_cols[0]
#             y_col = y_col or numeric_cols[1]
#         elif numeric_cols and cat_cols:
#             chart_type = "bar"
#             x_col = x_col or cat_cols[0]
#             y_col = y_col or numeric_cols[0]
#         elif numeric_cols:
#             chart_type = "histogram"
#             y_col = numeric_cols[0]
#         else:
#             chart_type = "heatmap"

#     # color detection: "by <col>" often used as grouping
#     if not color:
#         m = re.search(r"by ([a-z0-9_ ]+)", prompt_l)
#         if m:
#             cand = m.group(1).strip()
#             for col in df.columns:
#                 if col.lower() in cand or cand in col.lower():
#                     color = col
#                     break
#     # simple filter detection: "where <col> = value" or "in <col> <value>"
#     m_where = re.search(r"where ([a-z0-9_]+) (?:is |= )?([a-z0-9_\-]+)", prompt_l)
#     if m_where:
#         col = m_where.group(1)
#         val = m_where.group(2)
#         # find actual column name matching
#         matched = next((c for c in df.columns if c.lower() == col.lower() or col.lower() in c.lower()), None)
#         if matched:
#             filters[matched] = val

#     # return sanitized config
#     return {
#         "chart_type": chart_type,
#         "x_column": x_col,
#         "y_column": y_col,
#         "color": color,
#         "filters": filters,
#         "explain": f"Suggested chart {chart_type}, x={x_col}, y={y_col}, color={color}"
#     }

import re
import pandas as pd
from typing import Dict, Any


def suggest_from_prompt(df: pd.DataFrame, prompt: str) -> Dict[str, Any]:

    prompt_l = prompt.lower().strip()

    numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
    cat_cols = df.select_dtypes(exclude=["number"]).columns.tolist()

    x_col = None
    y_col = None
    color = None
    chart_type = None
    filters = {}

    # ---------------- TIME SERIES ----------------
    if any(k in prompt_l for k in ["trend", "monthly", "year", "daily"]):
        chart_type = "line"
        x_col = df.columns[0]
        y_col = numeric_cols[0] if numeric_cols else None

    # ---------------- COMPARE ----------------
    elif "compare" in prompt_l or "vs" in prompt_l:
        chart_type = "scatter"
        if len(numeric_cols) >= 2:
            x_col, y_col = numeric_cols[:2]

    # ---------------- HISTOGRAM ----------------
    elif "distribution" in prompt_l:
        chart_type = "histogram"
        y_col = numeric_cols[0] if numeric_cols else None

    # ---------------- BAR ----------------
    elif "bar" in prompt_l or "top" in prompt_l:
        chart_type = "bar"
        x_col = cat_cols[0] if cat_cols else df.columns[0]

    # ---------------- PIE ----------------
    elif "pie" in prompt_l or "donut" in prompt_l:
        chart_type = "pie"
        x_col = cat_cols[0] if cat_cols else df.columns[0]

    # ---------------- HEATMAP ----------------
    elif "heatmap" in prompt_l or "correlation" in prompt_l:
        chart_type = "heatmap"

    # ---------------- DEFAULT ----------------
    if not chart_type:
        if len(numeric_cols) >= 2:
            chart_type = "scatter"
            x_col, y_col = numeric_cols[:2]
        else:
            chart_type = "bar"
            x_col = df.columns[0]

    return {
        "chart_type": chart_type,
        "x_column": x_col,
        "y_column": y_col,
        "color": color,
        "filters": filters,
        "explain": f"{chart_type} using {x_col} vs {y_col}"
    }