# # backend/visualizer.py level 1

import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
import io
import base64
from typing import Optional, Dict, Any, List

import plotly.express as px
import plotly.graph_objects as go

sns.set_style("whitegrid")


# =========================================================
#   MAIN VISUALIZER CLASS
# =========================================================
class DataVisualizer:
    def __init__(self, df: pd.DataFrame):
        if df is None:
            raise ValueError("DataVisualizer requires a dataframe")
        self.df = df.copy()

    # =====================================================
    #   VISUAL STYLE PRESETS (NEW)
    # =====================================================
    CHART_STYLES = {
        "modern_blue": {
            "bar": {"color": "#3b82f6"},
            "line": {"color": "#10b981"},
            "scatter": {"color": "#8b5cf6"},
            "histogram": {"color": "#f59e0b"}
        },
        "dark_mode": {
            "bar": {"color": "#60a5fa"},
            "line": {"color": "#34d399"},
            "scatter": {"color": "#f472b6"},
            "histogram": {"color": "#fbbf24"}
        },
        "neon": {
            "bar": {"color": "#22d3ee"},
            "line": {"color": "#a78bfa"},
            "scatter": {"color": "#fb7185"},
            "histogram": {"color": "#facc15"}
        }
    }
    # =====================================================
    #   COLUMN HELPERS
    # =====================================================
    def get_numeric_columns(self) -> List[str]:
        return self.df.select_dtypes(include=["number"]).columns.tolist()

    def get_categorical_columns(self) -> List[str]:
        return self.df.select_dtypes(exclude=["number"]).columns.tolist()
    def _get_style(self, chart_type: str, style: str = "modern_blue"):
        return self.CHART_STYLES.get(style, self.CHART_STYLES["modern_blue"]).get(
            chart_type, {"color": "#3b82f6"}
        )
    # =====================================================
    #   MATPLOTLIB FALLBACK (IMAGE RENDERING)
    # =====================================================
    def _fig_to_base64(self, fig):
        buf = io.BytesIO()
        fig.savefig(buf, format="png", bbox_inches="tight", dpi=120)
        plt.close(fig)
        buf.seek(0)
        return base64.b64encode(buf.getvalue()).decode("utf-8")

    # =====================================================
    #   BASIC MATPLOTLIB PLOTS
    # =====================================================

    def plot_histogram(self, column: str, bins: int = 30):
        fig, ax = plt.subplots(figsize=(8, 5))

        sns.histplot(
            self.df[column].dropna(),
            bins=bins,
            kde=True,
            ax=ax,
            color="#3b82f6",
            edgecolor="white",
            linewidth=0.5
        )

        ax.set_title(f"Distribution of {column}", fontsize=14, fontweight="bold")
        ax.set_facecolor("#f8fafc")
        fig.patch.set_facecolor("#f8fafc")

        return self._fig_to_base64(fig)


    def plot_bar(self, column: str, top_n: int = 20):
        fig, ax = plt.subplots(figsize=(9, 5))

        vc = self.df[column].value_counts().nlargest(top_n)

        sns.barplot(
            x=vc.values,
            y=vc.index,
            ax=ax,
            palette="viridis"
        )

        ax.set_title(f"Top {top_n} Categories in {column}", fontsize=14, fontweight="bold")

        return self._fig_to_base64(fig)
    def plot_boxplot(self, column: str):
        fig, ax = plt.subplots(figsize=(6, 5))
        sns.boxplot(y=self.df[column].dropna(), ax=ax)
        ax.set_title(f"Boxplot: {column}")
        return self._fig_to_base64(fig)


    def plot_scatter(self, x_column: str, y_column: str):
        if x_column not in self.df.columns or y_column not in self.df.columns:
            raise ValueError("Invalid columns for scatter plot")

        fig, ax = plt.subplots(figsize=(8, 5))

        sns.scatterplot(
            x=self.df[x_column],
            y=self.df[y_column],
            ax=ax,
            alpha=0.7,
            edgecolor=None,
            color="#8b5cf6"
        )

        sns.regplot(
            x=self.df[x_column],
            y=self.df[y_column],
            scatter=False,
            ax=ax,
            color="#ef4444"
        )

        ax.set_title(f"{x_column} vs {y_column}", fontsize=14, fontweight="bold")

        return self._fig_to_base64(fig)

    def plot_smart_line(self, x_column: str, y_column: str):
        if x_column not in self.df.columns or y_column not in self.df.columns:
            raise ValueError("Invalid columns for line plot")

        fig, ax = plt.subplots(figsize=(9, 5))

        df_sorted = self.df.sort_values(by=x_column)

        ax.plot(
            df_sorted[x_column],
            df_sorted[y_column],
            color="#10b981",
            linewidth=2,
            marker="o",
            markersize=3
        )

        ax.fill_between(
            df_sorted[x_column],
            df_sorted[y_column],
            alpha=0.2,
            color="#10b981"
        )

        ax.set_title(f"Trend: {y_column} over {x_column}", fontsize=14, fontweight="bold")

        return self._fig_to_base64(fig)

    def plot_heatmap(self):
        num = self.get_numeric_columns()
        if not num:
            raise ValueError("No numeric columns for heatmap")
        corr = self.df[num].corr()
        fig, ax = plt.subplots(figsize=(12, 9))
        sns.heatmap(corr, annot=True, fmt=".2f", cmap="coolwarm", ax=ax)
        ax.set_title("Correlation Heatmap")
        return self._fig_to_base64(fig)

    def plot_stacked_bar(self, x_column: str, y_column: str):
        fig, ax = plt.subplots(figsize=(9, 5))

        grouped = self.df.groupby(x_column)[y_column].sum().head(15)

        ax.bar(grouped.index, grouped.values, color="#3b82f6")

        ax.set_title(f"Stacked View: {y_column} by {x_column}", fontsize=14, fontweight="bold")
        ax.tick_params(axis='x', rotation=45)

        return self._fig_to_base64(fig)


    # =====================================================
    #   HIGH-LEVEL ROUTER FOR OLD CODE COMPATIBILITY
    # =====================================================
    def plot(self, chart_type: str, column: Optional[str] = None, y_column: Optional[str] = None, **kwargs):
        chart_type = (chart_type or "").lower()

        if chart_type == "histogram":
            return self.plot_histogram(column, bins=kwargs.get("bins", 30))
        if chart_type == "bar":
            return self.plot_bar(column, top_n=kwargs.get("top_n", 20))
        if chart_type == "boxplot":
            return self.plot_boxplot(column)
        if chart_type == "scatter":
            return self.plot_scatter(column, y_column)
        if chart_type == "line":
            return self.plot_smart_line(column, y_column)
        if chart_type == "heatmap":
            return self.plot_heatmap()
        if chart_type == "stacked_bar":
            return self.plot_stacked_bar(column, y_column)

        raise ValueError(f"Unsupported chart type: {chart_type}")

    # =====================================================
    #   SMART FILTER ENGINE
    # =====================================================
    def _apply_filters(self, df, filters: Dict[str, Any]):
        if not filters:
            return df

        for col, val in filters.items():
            if val is None or val == "":
                continue

            # RANGE FILTER
            if isinstance(val, list) and len(val) == 2:
                try:
                    df = df[df[col].between(val[0], val[1])]
                except Exception:
                    pass

            # STRING / CATEGORY FILTER
            else:
                df = df[df[col].astype(str).str.contains(str(val), case=False, na=False)]

        return df

    # =====================================================
    #   PLOTLY ADVANCED ENGINE (Level 2 updates)
    # =====================================================
    def plotly_trace(
        self,
        chart_type: str,
        x: Optional[str] = None,
        y: Optional[str] = None,
        color: Optional[str] = None,
        filters: Dict[str, Any] = None,
        chart_props: Dict[str, Any] = None,
        multi_y: List[str] = None,
        **kwargs
    ) -> Dict[str, Any]:

        df = self._apply_filters(self.df.copy(), filters or {})
        chart_type = (chart_type or "").lower()
        chart_props = chart_props or {}
        result = {"data": [], "layout": {}}

        # ---------------- HISTOGRAM ------------------------
        if chart_type == "histogram":
            trace = {
                "type": "histogram",
                "x": df[x].dropna().tolist(),
                "nbinsx": kwargs.get("bins", 30),
                "marker": {"color": chart_props.get("color", "#3b82f6")}
            }
            result["data"].append(trace)
            result["layout"] = {"title": chart_props.get("title", f"Histogram: {x}")}
            return self._apply_plotly_style(result)

        # ---------------- BAR CHART (MULTI-Y SUPPORT) -------------
        if chart_type == "bar":
            if multi_y:
                for col in multi_y:
                    trace = {
                        "type": "bar",
                        "x": df[x].tolist(),
                        "y": df[col].tolist(),
                        "name": col,
                        "marker": {"color": chart_props.get("color", None)}
                    }
                    result["data"].append(trace)
            else:
                vc = df[x].value_counts().head(50)
                trace = {
                    "type": "bar",
                    "x": vc.index.tolist(),
                    "y": vc.values.tolist(),
                    "marker": {"color": chart_props.get("color", "#fb7185")}
                }
                result["data"].append(trace)
            result["layout"] = {
                "title": chart_props.get("title", f"Bar: {x}"),
                "barmode": chart_props.get("barmode", "group")
            }
            return self._apply_plotly_style(result)

        # ---------------- SCATTER / LINE ---------------------
        if chart_type in ("scatter", "line", "area"):
            if not x or not y:
                raise ValueError(f"{chart_type} chart needs x and y")

            mode_type = "markers" if chart_type == "scatter" else "lines+markers"
            if chart_type == "area":
                fill = "tozeroy"
                mode_type = "lines"
            else:
                fill = None

            trace = {
                "type": "scatter",
                "x": df[x].tolist(),
                "y": df[y].tolist(),
                "mode": mode_type,
                "fill": fill,
                "line": {"color": chart_props.get("color", "#10b981")},
                "marker": {"size": chart_props.get("size", 7)}
            }
            if color and color in df.columns:
                trace["marker"]["color"] = df[color].astype(str).tolist()

            result["data"].append(trace)
            result["layout"] = {"title": chart_props.get("title", f"{chart_type.title()}: {x} vs {y}")}
            return self._apply_plotly_style(result)

        # ---------------- PIE / DONUT ------------------------
        if chart_type in ("pie", "donut"):
            vc = df[x].value_counts()
            trace = {
                "type": "pie",
                "labels": vc.index.tolist(),
                "values": vc.values.tolist(),
                "hole": 0.5 if chart_type == "donut" else 0
            }
            result["data"].append(trace)
            result["layout"] = {"title": chart_props.get("title", f"{chart_type.title()} Chart: {x}")}
            return self._apply_plotly_style(result)

        # ---------------- VIOLIN / BOX ------------------------
        if chart_type == "violin":
            fig = px.violin(
                df,
                y=y,
                x=x,
                color=color,
                box=True,
                points="all"
            )

            result = fig.to_dict()
            return self._apply_plotly_style(result)
        if chart_type == "box":
            fig = px.box(df, x=x, y=y, color=color)

            result = fig.to_dict()
            return self._apply_plotly_style(result)

        # ---------------- SCATTER MATRIX ----------------------
        if chart_type == "scatter-matrix":
            numcols = self.get_numeric_columns()[:5]

            fig = px.scatter_matrix(df[numcols])

            result = fig.to_dict()
            return self._apply_plotly_style(result)

        # ---------------- CORRELATION HEATMAP -----------------
        if chart_type == "heatmap":
            corr = df[self.get_numeric_columns()].corr()
            trace = {
                "type": "heatmap",
                "z": corr.values.tolist(),
                "x": corr.columns.tolist(),
                "y": corr.index.tolist(),
                "colorscale": chart_props.get("colorscale", "RdBu")
            }
            result["data"].append(trace)
            result["layout"] = {"title": chart_props.get("title", "Correlation Heatmap")}
            return self._apply_plotly_style(result)

        # ---------------- BUBBLE CHART -----------------
        if chart_type == "bubble":
            fig = px.scatter(
                df,
                x=x,
                y=y,
                size=y,
                color=color,
                hover_name=color
            )

            result = fig.to_dict()
            return self._apply_plotly_style(result)

        # ---------------- TREEMAP -----------------
        if chart_type == "treemap":
            fig = px.treemap(
                df,
                path=[x],
                values=y if y else None,
                color=y if y else None
            )

            result = fig.to_dict()
            return self._apply_plotly_style(result)

        # ---------------- SUNBURST -----------------
        if chart_type == "sunburst":
            fig = px.sunburst(
                df,
                path=[x, color] if color else [x],
                values=y if y else None
            )

            result = fig.to_dict()
            return self._apply_plotly_style(result)

        # ---------------- FUNNEL -----------------
        if chart_type == "funnel":
            fig = px.funnel(df, x=y, y=x)

            result = fig.to_dict()
            return self._apply_plotly_style(result)
        # fallback
        return {"data": [], "layout": {"title": "No data"}}
    # =====================================================
    #   PLOTLY STYLE ENHANCER (CLASS LEVEL - FIXED)
    # =====================================================
    def _apply_plotly_style(self, result: Dict[str, Any]):
        if "layout" not in result:
            result["layout"] = {}

        result["layout"]["template"] = "plotly_dark"
        result["layout"]["font"] = {
            "family": "Arial",
            "size": 12
        }
        result["layout"]["paper_bgcolor"] = "rgba(0,0,0,0)"
        result["layout"]["plot_bgcolor"] = "rgba(0,0,0,0)"

        return result
    
