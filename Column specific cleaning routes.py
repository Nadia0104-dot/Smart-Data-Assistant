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