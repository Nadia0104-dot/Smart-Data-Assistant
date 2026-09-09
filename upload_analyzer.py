# backend/upload_analyzer.py
import pandas as pd
import os

class UploadAnalyzer:
    def __init__(self, filepath):
        self.filepath = filepath
        self.df = self._load_file(filepath)

    def _load_file(self, path):
        path = str(path)
        if path.lower().endswith(".tsv"):
            return pd.read_csv(path, sep="\t", engine="python")
        if path.lower().endswith(".csv"):
            encodings = ("utf-8", "utf-8-sig", "latin1", "iso-8859-1")
            for enc in encodings:
                try:
                    return pd.read_csv(path, encoding=enc, engine="python")
                except Exception:
                    continue
            return pd.read_csv(path, engine="python")
        if path.lower().endswith((".xls", ".xlsx")):
            return pd.read_excel(path)
        raise ValueError(f"Unsupported file type: {path}")

    def file_metadata(self):
        df = self.df.copy()
        if df.empty:
            return {"rows":0,"columns":0,"missing_percent":{},"duplicates":0,"preview":[]}

        # Replace empty strings with NaN for proper missing detection
        df = df.replace(r'^\s*$', pd.NA, regex=True)

        rows = len(df)
        cols = len(df.columns)

        # Missing percentage per column
        missing_percent = (df.isna().sum() / max(1, rows) * 100).round(2).to_dict()

        # Duplicates: add a boolean column to mark duplicate rows
        df["_is_duplicate"] = df.duplicated()

        duplicates = int(df["_is_duplicate"].sum())

        # Preview (first 5 rows)
        preview = df.head(5).fillna("").to_dict(orient="records")

        return {
            "rows": rows,
            "columns": cols,
            "missing_percent": missing_percent,
            "duplicates": duplicates,
            "preview": preview
        }
