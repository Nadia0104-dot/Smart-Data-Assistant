@bp.route("/formula/generate", methods=["POST"])
def route_formula_generate():
    data = request.get_json() or {}
    q = data.get("query", "")
    ql = q.strip().lower()
    tokens = ql.split()
    if not tokens:
        return jsonify({"error": "Empty query"}), 400
    func = tokens[0]
    col = " ".join(tokens[1:])
    
    df = STORE["working_df"] if STORE["working_df"] is not None else STORE["original_df"]
    if df is None:
        return jsonify({"error": "No dataset"}), 400
    
    col_idx = -1
    for i, c in enumerate(df.columns):
        if c.lower() == col.lower():
            col_idx = i; break
    if col_idx == -1:
        for i, c in enumerate(df.columns):
            if col.lower() in c.lower() or c.lower() in col.lower():
                col_idx = i; break
    if col_idx == -1:
        return jsonify({"error": f'Column "{col}" not found'}), 400
        
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


@bp.route("/upload/ai-insights", methods=["POST"])
def route_ai_insights():
    df = STORE["working_df"] if STORE["working_df"] is not None else STORE["original_df"]
    if df is None:
        return jsonify({"error": "No dataset"}), 400
    summary = df_summary(df)
    return jsonify({"summary": summary})