@bp.route("/upload", methods=["POST"])
def route_upload():
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