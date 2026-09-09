
# cleaner.py
# Flask blueprint / routes to integrate with your frontend.
# Place in your Flask app and register blueprint or import functions.

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

bp = Blueprint("cleaner", __name__)

# === Simple in-memory storage (single-user)
# For multi-user, replace with session / per-user temp files / DB
STORE = {
    "original_df": None,  # df as uploaded
    "working_df": None,
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

# Example: if you want to auto-load a demo file on startup, uncomment & adapt:
# load_uploaded_df_from_file("data/demo.csv")


# --- Routes expected by frontend ---

@bp.route("/load_uploaded", methods=["GET"])
def route_load_uploaded():
    """Return preview_html and summary based on working_df (or original)."""
    df = STORE["working_df"] if STORE["working_df"] is not None else STORE["original_df"]
    if df is None:
        return jsonify({"error": "No uploaded dataset"}), 400
    preview_html = df_preview_html(df)
    summary = df_summary(df)
    return jsonify({"preview_html": preview_html, "summary": summary})


@bp.route("/clean/preview", methods=["GET"])
def route_clean_preview():
    df = STORE["working_df"] if STORE["working_df"] is not None else STORE["original_df"]
    if df is None:
        return jsonify({"html": "<div class='muted'>No data</div>", "health": {}, "types": {}})
    html = df_preview_html(df)
    health = df_summary(df)
    types = {}
    for c in df.columns:
        types[c] = str(df[c].dtype)
    return jsonify({"html": html, "health": health, "types": types})


@bp.route("/clean/data", methods=["GET"])
def route_clean_data():
    df = STORE["working_df"] if STORE["working_df"] is not None else STORE["original_df"]
    if df is None:
        return jsonify({"data": [], "rows": 0})
    # Return first 500 rows for client use
    records = df.head(500).to_dict(orient="records")
    return jsonify({"data": records, "rows": int(df.shape[0])})


# Generic POST helper for actions that don't require extra params
def _apply_and_store(df_new):
    STORE["working_df"] = df_new.copy().reset_index(drop=True)
    preview = df_preview_html(STORE["working_df"])
    summary = df_summary(STORE["working_df"])
    return jsonify({"preview_html": preview, "summary": summary})


# --- Basic cleaning endpoints ---


@bp.route("/clean/remove_duplicates", methods=["POST", "GET"])
def route_remove_duplicates():
    df = STORE["working_df"] if STORE["working_df"] is not None else STORE["original_df"]
    if df is None:
        return jsonify({"error": "No dataset"}), 400

    new = remove_duplicates(df)
    return _apply_and_store(new)

@bp.route("/clean/drop_missing", methods=["POST"])
def route_drop_missing():
    df = STORE["working_df"] if STORE["working_df"] is not None else STORE["original_df"]
    if df is None:
        return jsonify({"error": "No dataset"}), 400
    # drop any row with missing value (frontend requested)
    new = drop_missing_rows(df, how="any")
    return _apply_and_store(new)


@bp.route("/clean/remove_outliers", methods=["POST"])
def route_remove_outliers():
    df = STORE["working_df"] if STORE["working_df"] is not None else STORE["original_df"]
    if df is None:
        return jsonify({"error": "No dataset"}), 400
    new = remove_outliers_iqr(df)
    return _apply_and_store(new)


@bp.route("/clean/normalize", methods=["POST"])
def route_normalize():
    df = STORE["working_df"] if STORE["working_df"] is not None else STORE["original_df"]
    new = normalize_df(df)
    return _apply_and_store(new)


@bp.route("/clean/standardize", methods=["POST"])
def route_standardize():
    df = STORE["working_df"] if STORE["working_df"] is not None else STORE["original_df"]
    new = standardize_df(df)
    return _apply_and_store(new)


# Fill methods
@bp.route("/clean/fill_mean", methods=["POST"])
def route_fill_mean():
    df = STORE["working_df"] if STORE["working_df"] is not None else STORE["original_df"]
    new = fill_missing_df(df, method="mean")
    return _apply_and_store(new)

@bp.route("/clean/fill_median", methods=["POST"])
def route_fill_median():
    df = STORE["working_df"] if STORE["working_df"] is not None else STORE["original_df"]
    new = fill_missing_df(df, method="median")
    return _apply_and_store(new)

@bp.route("/clean/fill_mode", methods=["POST"])
def route_fill_mode():
    df = STORE["working_df"] if STORE["working_df"] is not None else STORE["original_df"]
    new = fill_missing_df(df, method="mode")
    return _apply_and_store(new)


# Trim / case / special chars
@bp.route("/clean/trim_spaces", methods=["POST"])
def route_trim_spaces():
    df = STORE["working_df"] if STORE["working_df"] is not None else STORE["original_df"]
    new = trim_spaces_df(df)
    return _apply_and_store(new)

@bp.route("/clean/to_lowercase", methods=["POST"])
def route_to_lowercase():
    df = STORE["working_df"] if STORE["working_df"] is not None else STORE["original_df"]
    new = to_lowercase_df(df)
    return _apply_and_store(new)

@bp.route("/clean/to_uppercase", methods=["POST"])
def route_to_uppercase():
    df = STORE["working_df"] if STORE["working_df"] is not None else STORE["original_df"]
    new = to_uppercase_df(df)
    return _apply_and_store(new)

@bp.route("/clean/remove_special_chars", methods=["POST"])
def route_remove_special_chars():
    df = STORE["working_df"] if STORE["working_df"] is not None else STORE["original_df"]
    new = remove_special_chars_df(df)
    return _apply_and_store(new)


# --- Column / dtype / regex operations (query params expected) ---
@bp.route("/clean/drop_column", methods=["POST", "GET"])
def route_drop_column():
    column = request.args.get("column") or request.form.get("column")
    if not column:
        return jsonify({"error": "Missing column parameter"}), 400
    df = STORE["working_df"] if STORE["working_df"] is not None else STORE["original_df"]
    new = drop_column_df(df, column)
    return _apply_and_store(new)


@bp.route("/clean/convert_dtype", methods=["POST", "GET"])
def route_convert_dtype():
    column = request.args.get("column") or request.form.get("column")
    dtype = request.args.get("dtype") or request.form.get("dtype")
    if not column or not dtype:
        return jsonify({"error": "Missing column or dtype parameter"}), 400
    df = STORE["working_df"] if STORE["working_df"] is not None else STORE["original_df"]
    new = convert_dtype_df(df, column, dtype)
    return _apply_and_store(new)


@bp.route("/clean/regex_replace", methods=["POST", "GET"])
def route_regex_replace():
    column = request.args.get("column") or request.form.get("column")
    pattern = request.args.get("pattern") or request.form.get("pattern")
    replacement = request.args.get("replacement") or request.form.get("replacement")
    if column is None or pattern is None or replacement is None:
        return jsonify({"error": "Missing params"}), 400
    df = STORE["working_df"] if STORE["working_df"] is not None else STORE["original_df"]
    new = regex_replace_df(df, column, pattern, replacement)
    return _apply_and_store(new)


@bp.route("/clean/extract_substring", methods=["POST", "GET"])
def route_extract_substring():
    column = request.args.get("column")
    start = request.args.get("start")
    end = request.args.get("end")
    if column is None or start is None:
        return jsonify({"error": "Missing params"}), 400
    df = STORE["working_df"] if STORE["working_df"] is not None else STORE["original_df"]
    new = extract_substring_df(df, column, start, end)
    return _apply_and_store(new)


@bp.route("/clean/format_date", methods=["POST", "GET"])
def route_format_date():
    column = request.args.get("column")
    fmt = request.args.get("format")
    if column is None or fmt is None:
        return jsonify({"error": "Missing params"}), 400
    df = STORE["working_df"] if STORE["working_df"] is not None else STORE["original_df"]
    new = format_date_df(df, column, fmt)
    return _apply_and_store(new)


# --- Reset / download / auto ---
@bp.route("/clean/reset", methods=["GET", "POST"])
def route_reset():
    if STORE["original_df"] is None:
        return jsonify({"error": "No original dataset stored"}), 400
    STORE["working_df"] = STORE["original_df"].copy()
    return jsonify({"ok": True})


@bp.route("/clean/download", methods=["GET"])
def route_download():
    df = STORE["working_df"] if STORE["working_df"] is not None else STORE["original_df"]
    if df is None:
        return jsonify({"error": "No dataset"}), 400
    csv_bytes = df_to_csv_bytes(df)
    return send_file(
        io.BytesIO(csv_bytes),
        mimetype="text/csv",
        as_attachment=True,
        download_name="cleaned_dataset.csv"
    )


@bp.route("/clean/auto", methods=["POST"])
def route_auto():
    df = STORE["working_df"] if STORE["working_df"] is not None else STORE["original_df"]
    if df is None:
        return jsonify({"error": "No dataset"}), 400
    new_df, summary = advanced_auto_clean_pipeline(df)
    STORE["working_df"] = new_df
    preview = df_preview_html(new_df)
    return jsonify({"preview_html": preview, "summary": summary})


# --- Formula generator (optional) ---
@bp.route("/formula/generate", methods=["POST"])
def route_formula_generate():
    data = request.get_json() or {}
    q = data.get("query", "")
    # simple server-side fallback (mirrors JS parsing)
    ql = q.strip().lower()
    # very simple parsing for sum/avg/min/max/count/trim
    tokens = ql.split()
    if not tokens:
        return jsonify({"error": "Empty query"}), 400
    func = tokens[0]
    col = " ".join(tokens[1:])
    # attempt to find column name in dataframe
    df = STORE["working_df"] if STORE["working_df"] is not None else STORE["original_df"]
    if df is None:
        return jsonify({"error": "No dataset"}), 400
    # find best matching column
    col_idx = -1
    for i, c in enumerate(df.columns):
        if c.lower() == col.lower():
            col_idx = i; break
    if col_idx == -1:
        # try contains
        for i, c in enumerate(df.columns):
            if col.lower() in c.lower() or c.lower() in col.lower():
                col_idx = i; break
    if col_idx == -1:
        return jsonify({"error": f'Column "{col}" not found'}), 400
    # compute excel style range
    def col_letter(n):
        s=""
        while n>=0:
            s = chr((n%26)+65) + s
            n = n//26 - 1
        return s
    start = 2
    end = max(2, df.shape[0]+1)
    rng = f"{col_letter(col_idx)}{start}:{col_letter(col_idx)}{end}"
    mapping = {
        "sum": f"=SUM({rng})",
        "avg": f"=AVERAGE({rng})",
        "average": f"=AVERAGE({rng})",
        "min": f"=MIN({rng})",
        "max": f"=MAX({rng})",
        "count": f"=COUNT({rng})",
        "trim": f"=ARRAYFORMULA(TRIM({rng}))"
    }
    out = mapping.get(func, None)
    if not out:
        return jsonify({"error": "Could not parse query"}), 400
    return jsonify({"formula": out})


# --- AI-insights placeholder (optional) ---
@bp.route("/upload/ai-insights", methods=["POST"])
def route_ai_insights():
    # placeholder: you can wire to an LLM or simple summary
    df = STORE["working_df"] if STORE["working_df"] is not None else STORE["original_df"]
    if df is None:
        return jsonify({"error": "No dataset"}), 400
    summary = df_summary(df)
    return jsonify({"summary": summary})


# --- Optional route to upload a CSV via POST (multipart/form-data) ---
@bp.route("/upload", methods=["POST"])
def route_upload():
    """
    Accepts file upload (form field 'file') and stores original_df and working_df.
    """
    f = request.files.get("file")
    if not f:
        return jsonify({"error": "No file uploaded"}), 400
    try:
        df = pd.read_csv(f)
    except Exception as e:
        return jsonify({"error": "Failed to parse CSV", "detail": str(e)}), 400
    STORE["original_df"] = df.copy()
    STORE["working_df"] = df.copy()
    STORE["filename"] = f.filename
    return jsonify({"ok": True, "rows": int(df.shape[0]), "cols": int(df.shape[1])})

@bp.route("/clean/auto_fix_types", methods=["POST"])
def route_auto_fix_types():
    df = STORE["working_df"] if STORE["working_df"] is not None else STORE["original_df"]

    if df is None:
        return jsonify({"error": "No dataset"}), 400

    new = auto_fix_dtypes(df)
    return _apply_and_store(new)



@bp.route("/clean/robust_scale", methods=["POST"])
def route_robust_scale():
    df = STORE["working_df"] if STORE["working_df"] is not None else STORE["original_df"]

    if df is None:
        return jsonify({"error": "No dataset"}), 400

    new = robust_scale_df(df)
    return _apply_and_store(new)