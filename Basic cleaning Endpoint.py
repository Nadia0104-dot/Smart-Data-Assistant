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


# --- Fill Methods ---
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


# --- Text Transformations ---
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