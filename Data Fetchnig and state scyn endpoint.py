# Generic POST helper for actions that don't require extra params
def _apply_and_store(df_new):
    STORE["working_df"] = df_new.copy().reset_index(drop=True)
    preview = df_preview_html(STORE["working_df"])
    summary = df_summary(STORE["working_df"])
    return jsonify({"preview_html": preview, "summary": summary})


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