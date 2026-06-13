from flask import (
    Blueprint, current_app, jsonify, request, send_file, make_response
)
import io
import pandas as pd
from datetime import datetime

# Import analyzer functions
from cleaner_analyzer import (
    df_preview_html, df_summary, remove_duplicates, drop_missing_rows,
    remove_outliers_iqr, normalize_df, standardize_df, trim_spaces_df,
    to_lowercase_df, to_uppercase_df, remove_special_chars_df, regex_replace_df,
    extract_substring_df, format_date_df, drop_column_df, convert_dtype_df,
    fill_missing_df, df_to_csv_bytes, auto_clean_pipeline,

    # NEW
    remove_empty_columns_df,
    smart_fill_missing_df,
    knn_fill_missing_df,
    remove_highly_correlated_df,
    robust_scale_df,
    auto_fix_dtypes,
    remove_constant_columns_df,
    clean_column_names_df,
    remove_html_tags_df,
    remove_extra_whitespace_df,
    advanced_auto_clean_pipeline
)

# Blueprint setup
bp = Blueprint("cleaner", __name__)

# === Simple in-memory storage (single-user)
STORE = {
    "original_df": None,  # Original dataframe as uploaded
    "working_df": None,   # Cleaned dataframe during active operations
    "filename": None,
    "uploaded_at": None
}

# Helper to load a saved CSV (if you have one)
def load_uploaded_df_from_file(path: str):
    df = pd.read_csv(path)
    STORE["original_df"] = df
    STORE["working_df"] = df.copy()
    STORE["filename"] = path
    STORE["uploaded_at"] = datetime.utcnow()