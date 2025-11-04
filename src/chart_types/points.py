"""
Consolidated points visualizations (daily / monthly / per-market).
Provides:
 - create_points_view(df, mode='daily'|'monthly'|'per_market', top_n=10)
 - calculate_points_value(open, close, market, action)
 - aggregate_points(df, mode)

Design:
 - Uses get_trading_data() + ensure_market_column() from chart_types.base
 - Returns a Plotly Figure with a small stats table on top and the main chart below.
"""
from typing import Dict, Any
import logging

from plotly.subplots import make_subplots
import plotly.graph_objects as go
import pandas as pd

from .base import (
    get_trading_data,
    ensure_market_column,
    find_date_col,
    setup_base_figure,
    apply_standard_layout,
)
import settings as _settings
import chart_types.base as base

logger = logging.getLogger(__name__)

MARKET_POINT_MULTIPLIERS: Dict[str, float] = getattr(_settings, "MARKET_POINT_MULTIPLIERS", {})
DEFAULT_POINT_MULTIPLIER: float = getattr(_settings, "DEFAULT_POINT_MULTIPLIER", 1.0)
COLORS = getattr(_settings, "COLORS", {"profit": "green", "loss": "red", "trading": ["#1f77b4"]})


def _to_float(v):
    try:
        if v is None:
            return None
        return float(str(v).replace(",", ""))
    except Exception:
        return None


def calculate_points_value(open_price, close_price, market=None, action=None, multipliers=None):
    """Signed points for single trade. Positive for profit, negative for loss.
    Uses MARKET_POINT_MULTIPLIERS (fall back DEFAULT_POINT_MULTIPLIER).
    """
    if multipliers is None:
        multipliers = MARKET_POINT_MULTIPLIERS or {}

    op = _to_float(open_price)
    cp = _to_float(close_price)
    if op is None or cp is None or op == 0 or cp == 0:
        return 0.0

    try:
        mult = float(multipliers.get(market, DEFAULT_POINT_MULTIPLIER))
    except Exception:
        mult = DEFAULT_POINT_MULTIPLIER

    diff = cp - op
    pts = diff * mult

    # if explicit action semantics exist (older code used Trade Receivable/Payable)
    if isinstance(action, str):
        a = action.strip().lower()
        if "receivable" in a or "buy" in a:
            return round(pts, 1)
        if "payable" in a or "sell" in a:
            return round(-pts, 1)
    # default: preserve sign from price diff (positive = profit)
    return round(pts, 1)


def _prepare_trading_df(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize and return trading-only DataFrame with Market and Transaction Date normalized."""
    td = get_trading_data(df)
    if td is None or not isinstance(td, pd.DataFrame) or td.empty:
        return pd.DataFrame()
    td = ensure_market_column(td)
    date_col = find_date_col(td)
    if date_col:
        td[date_col] = pd.to_datetime(td[date_col], errors="coerce")
        td = td.rename(columns={date_col: "Transaction Date"})
    else:
        td["Transaction Date"] = pd.to_datetime(td.get("Transaction Date"), errors="coerce")
    return td


def aggregate_points(df: pd.DataFrame, mode: str = "daily") -> Dict[str, Any]:
    """Aggregate points for requested mode. Returns dict with aggregation frames and stats."""
    td = _prepare_trading_df(df)
    logger.debug("aggregate_points: mode=%s incoming df type=%s shape=%s prepared td.shape=%s",
                 mode, type(df), getattr(df, "shape", None), getattr(td, "shape", None))
    if td.empty:
        # no prepared trading-only rows — return explicit reason so callers can log / fallback
        logger.debug("aggregate_points: prepared trading df is empty")
        return {"ok": False, "reason": "no data"}

    # Compute points per trade (conservative: uses opening/closing if present; otherwise 0)
    def _row_points(r):
        open_price = r.get("Opening") or r.get("Open")
        close_price = r.get("Closing") or r.get("Close")
        market = r.get("Market")
        action = r.get("Action")
        return calculate_points_value(open_price, close_price, market, action)

    td = td.copy()
    td["Points"] = td.apply(lambda r: _row_points(r), axis=1)
    logger.debug("aggregate_points: sample points rows: %s", td.head(5).to_dict("records"))
    logger.debug("aggregate_points: points summary sum=%s mean=%s count=%s zeros=%s",
                 td["Points"].sum(), td["Points"].mean() if not td["Points"].empty else None,
                 len(td), int((td["Points"] == 0).sum()))

    result: Dict[str, Any] = {"ok": True}
    if mode == "daily":
        td["Date"] = pd.to_datetime(td["Transaction Date"]).dt.date
        daily = td.groupby("Date")["Points"].sum().reset_index().sort_values("Date")
        daily["Cumulative"] = daily["Points"].cumsum()
        stats = {
            "total_points": float(daily["Points"].sum()),
            "avg_per_day": float(daily["Points"].mean()) if not daily.empty else 0.0,
            "num_days": int(len(daily)),
        }
        result.update({"df": daily, "stats": stats, "td": td})
        return result

    if mode == "monthly":
        td["Month"] = pd.to_datetime(td["Transaction Date"]).dt.to_period("M").dt.to_timestamp()
        monthly = td.groupby("Month")["Points"].sum().reset_index().sort_values("Month")
        monthly["Cumulative"] = monthly["Points"].cumsum()
        stats = {
            "total_points": float(monthly["Points"].sum()),
            "avg_per_month": float(monthly["Points"].mean()) if not monthly.empty else 0.0,
            "num_months": int(len(monthly)),
        }
        result.update({"df": monthly, "stats": stats, "td": td})
        return result

    if mode == "per_market":
        # month x market aggregation to support grouped bars
        td["Month"] = pd.to_datetime(td["Transaction Date"]).dt.to_period("M").dt.to_timestamp()
        mm = td.groupby(["Month", "Market"])["Points"].sum().reset_index()
        # pivot for plotting
        pivot = mm.pivot(index="Month", columns="Market", values="Points").fillna(0).sort_index()
        # Round per-market points to one decimal for plotting
        pivot = pivot.round(1)
        # also round totals shown in stats to one decimal
        total_by_market = td.groupby("Market")["Points"].sum().round(1).to_dict()
        stats = {
            "total_points": float(td["Points"].sum()),
            "num_markets": int(len(total_by_market)),
            "total_by_market": total_by_market,
        }
        result.update({"df": pivot, "raw": mm, "stats": stats, "td": td})
        return result

    return {"ok": False, "reason": "invalid mode"}


def create_points_view(df, mode='daily', top_n=10):
    """Create unified points figure with stats on top and chart below.
    Layout adjusted to match the style used in trades.create_daily_trade_count:
    - compact top table (fixed header/row heights)
    - autosize=True so the figure follows the container
    - reduced top margin and horizontal legend
    """
    logger.debug("create_points_view: incoming df type=%s shape=%s mode=%s", type(df), getattr(df, "shape", None), mode)
    # Prefer caller-provided DataFrame if it already contains trading rows (Opening/Closing or Transaction Date)
    dfc = None
    try:
        dfc = base.get_filtered_trading_df(df)
    except Exception:
        logger.exception("create_points_view: base.get_filtered_trading_df failed")

    if not isinstance(dfc, pd.DataFrame) or dfc.empty:
        # fallback to incoming df when normalizer returned no rows
        if isinstance(df, pd.DataFrame) and getattr(df, "shape", (0, 0))[0] > 0:
            # heuristic: require either Opening/Closing or Transaction Date present
            has_prices = any(c in df.columns for c in ("Opening", "Closing", "Open", "Close"))
            has_date = "Transaction Date" in df.columns or any("date" in c.lower() for c in df.columns)
            if has_prices and has_date:
                dfc = df.copy()
                logger.debug("create_points_view: using incoming DataFrame as fallback (has prices & date)")
            else:
                logger.debug("create_points_view: incoming DataFrame lacks required columns (prices/date); will return empty figure")
                return setup_base_figure()
        else:
            logger.debug("create_points_view: base.get_filtered_trading_df returned empty and no suitable fallback")
            return setup_base_figure()

    agg = aggregate_points(dfc, mode=mode)
    # base empty figure if no data
    if not agg.get("ok"):
        logger.debug("create_points_view: aggregate_points returned not ok: %s", agg.get("reason"))
        fig = setup_base_figure()
        fig = apply_standard_layout(fig, "Points")
        return fig

    stats = agg["stats"]

    # Use a simple base figure (no top table). Show metrics as a trades.py-style annotation.
    fig = setup_base_figure()
    # Build a compact summary text (rounded to 1 decimal) depending on mode
    try:
        if mode == "daily":
            total = float(stats.get("total_points", 0.0))
            avg = float(stats.get("avg_per_day", 0.0))
            num = int(stats.get("num_days", 0))
            summary_text = (
                f"Total Points: {total:.1f}<br>"
                f"Average (per day): {avg:.1f}<br>"
                f"Days: {num}"
            )
        elif mode == "monthly":
            total = float(stats.get("total_points", 0.0))
            avg = float(stats.get("avg_per_month", 0.0))
            num = int(stats.get("num_months", 0))
            summary_text = (
                f"Total Points: {total:.1f}<br>"
                f"Average (per month): {avg:.1f}<br>"
                f"Months: {num}"
            )
        elif mode == "per_market":
            total = float(stats.get("total_points", 0.0))
            nmarkets = int(stats.get("num_markets", 0))
            tbm = stats.get("total_by_market", {}) or {}
            parts = []
            for m, v in tbm.items():
                try:
                    parts.append(f"{m}: {float(v):.1f}")
                except Exception:
                    parts.append(f"{m}: {v}")
            markets_str = "; ".join(parts)
            summary_text = (
                f"Total Points: {total:.1f}<br>"
                f"Markets: {nmarkets}<br>"
                f"{markets_str}"
            )
        else:
            summary_text = "; ".join(f"{k}: {v}" for k, v in stats.items())
    except Exception:
        logger.exception("Failed to build summary_text for points view")
        summary_text = ""
    # place annotation similarly to trades.py
    fig.add_annotation(
        text=summary_text,
        xref='paper', yref='paper',
        x=1.02, y=1,
        showarrow=False,
        bgcolor='white',
        bordercolor='gray',
        borderwidth=1
    )

    # Chart area (mode-specific)
    if mode == "daily":
        dfc: pd.DataFrame = agg["df"]
        if not dfc.empty:
            fig.add_trace(
                go.Bar(
                    x=dfc["Date"],
                    y=dfc["Points"],
                    name="Daily Points",
                    marker=dict(color=dfc["Points"].apply(lambda x: COLORS.get("profit", "green") if x > 0 else COLORS.get("loss", "red")))
                )
            )
            fig.add_trace(
                go.Scatter(
                    x=dfc["Date"],
                    y=dfc["Cumulative"],
                    name="Cumulative",
                    line=dict(color=COLORS.get("trading", "blue"))
                )
            )

    elif mode == "monthly":
        dfc: pd.DataFrame = agg["df"]
        if not dfc.empty:
            fig.add_trace(
                go.Bar(
                    x=dfc["Month"],
                    y=dfc["Points"],
                    name="Monthly Points",
                    marker=dict(color=dfc["Points"].apply(lambda x: COLORS.get("profit", "green") if x > 0 else COLORS.get("loss", "red")))
                )
            )
            fig.add_trace(
                go.Scatter(
                    x=dfc["Month"],
                    y=dfc["Cumulative"],
                    name="Cumulative",
                    line=dict(color=COLORS.get("trading", "blue"))
                )
            )

    elif mode == "per_market":
        pivot: pd.DataFrame = agg["df"]
        if not pivot.empty:
            markets = pivot.columns.tolist()
            for i, m in enumerate(markets):
                fig.add_trace(
                    go.Bar(
                        x=pivot.index,
                        y=pivot[m],
                        name=m,
                        marker=dict(color=COLORS.get("trading", "blue"))
                    )
                )

    # Apply styling and make responsive/autosize like trades.py
    apply_standard_layout(fig, f"Points - {mode.replace('_', ' ').title()}")
    fig.update_layout(
        autosize=True,
        showlegend=True,
        margin=dict(t=36, b=60, l=60, r=60),
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=0.02,
            x=0.5,
            xanchor='center'
        )
    )
    fig.update_xaxes(tickangle=45)

    return fig