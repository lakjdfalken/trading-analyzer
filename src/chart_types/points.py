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
import re

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
    if td.empty:
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
        total_by_market = td.groupby("Market")["Points"].sum().to_dict()
        stats = {
            "total_points": float(td["Points"].sum()),
            "num_markets": int(len(total_by_market)),
            "total_by_market": total_by_market,
        }
        result.update({"df": pivot, "raw": mm, "stats": stats, "td": td})
        return result

    return {"ok": False, "reason": "invalid mode"}


def create_points_view(df, mode='daily', top_n=10):
    """Create unified points figure with stats on top and chart below."""
    dfc = base.get_filtered_trading_df(df)
    if dfc is None or dfc.empty:
        return setup_base_figure()

    agg = aggregate_points(dfc, mode=mode)
    # base empty figure if no data
    if not agg.get("ok"):
        fig = setup_base_figure()
        fig = apply_standard_layout(fig, "Points")
        return fig

    stats = agg["stats"]
    # build a 2-row layout: larger table area on top and chart below
    # increase top row height so the stats table is larger and move it upward relative to the chart
    fig = make_subplots(
        rows=2,
        cols=1,
        row_heights=[0.32, 0.68],
        specs=[[{"type": "table"}], [{"type": "xy"}]]
    )

    # Stats table (simple key/value)
    stat_keys = []
    stat_vals = []
    # flatten stats for table readability
    for k, v in stats.items():
        if isinstance(v, dict):
            stat_keys.append(k)
            stat_vals.append("; ".join(f"{mk}:{mv:.2f}" if isinstance(mv, (float, int)) else f"{mk}:{mv}" for mk, mv in v.items()))
        else:
            stat_keys.append(k)
            stat_vals.append(str(v))

    # Compute table heights so the full table is visible (no internal scroll).
    # Increase header/row heights to make the table area visually larger.
    header_height = 36
    row_height = 30

    # Ensure a reasonable minimum chart area height and overall figure height
    min_chart_area_px = 360
    padding_px = 60  # margins, legend, etc.
    total_height = int(header_height + row_height * max(1, len(stat_keys))) + min_chart_area_px + padding_px

    # Add table with explicit row heights so Plotly doesn't add an internal scrollbar.
    fig.add_trace(
        go.Table(
            header=dict(values=["Metric", "Value"], fill_color="lightgrey", align="left", height=header_height),
            cells=dict(values=[stat_keys, stat_vals], align="left", height=row_height),
        ),
        row=1,
        col=1,
    )
    # set preliminary figure height to accommodate the table + chart area; final resize applied later
    fig.update_layout(height=total_height)

    # Chart area
    if mode == "daily":
        dfc: pd.DataFrame = agg["df"]
        if not dfc.empty:
            fig.add_trace(go.Bar(x=dfc["Date"], y=dfc["Points"], name="Daily Points",
                                 marker=dict(color=dfc["Points"].apply(lambda x: COLORS.get("profit", "green") if x > 0 else COLORS.get("loss", "red")))),
                          row=2, col=1)
            fig.add_trace(go.Scatter(x=dfc["Date"], y=dfc["Cumulative"], name="Cumulative", line=dict(color=COLORS.get("profit", "green"))),
                          row=2, col=1)

    elif mode == "monthly":
        dfc: pd.DataFrame = agg["df"]
        if not dfc.empty:
            fig.add_trace(go.Bar(x=dfc["Month"], y=dfc["Points"], name="Monthly Points",
                                 marker=dict(color=dfc["Points"].apply(lambda x: COLORS.get("profit", "green") if x > 0 else COLORS.get("loss", "red")))),
                          row=2, col=1)
            fig.add_trace(go.Scatter(x=dfc["Month"], y=dfc["Cumulative"], name="Cumulative", line=dict(color=COLORS.get("profit", "green"))),
                          row=2, col=1)

    elif mode == "per_market":
        pivot: pd.DataFrame = agg["df"]
        if not pivot.empty:
            # stacked/grouped bars per month per market
            markets = pivot.columns.tolist()
            for i, m in enumerate(markets):
                fig.add_trace(go.Bar(x=pivot.index, y=pivot[m], name=m,
                                     marker=dict(color=COLORS.get("trading", [None])[i % len(COLORS.get("trading", [None]))])),
                              row=2, col=1)
            # optionally add total line
            total_series = pivot.sum(axis=1)
            fig.add_trace(go.Scatter(x=pivot.index, y=total_series, name="Total", line=dict(color=COLORS.get("profit", "green"))),
                          row=2, col=1)

    # Apply standard styling (mutates fig in-place)
    apply_standard_layout(fig, f"Points - {mode.replace('_', ' ').title()}")

    # Final layout: use computed height and place legend between table and chart.
    final_height = max(total_height, 700)
    fig.update_layout(
        height=final_height,
        showlegend=True,
        # move the table further up by reducing top margin
        margin=dict(t=40, b=60, l=60, r=60),
        legend=dict(
            orientation='h',
            yanchor='bottom',
            # with row_heights=[0.32,0.68] the chart top is at ~0.68 in paper coords;
            # place legend so its bottom aligns just above the chart area
            y=0.68,
            x=0.5,
            xanchor='center'
        )
    )
    fig.update_xaxes(tickangle=45)
    return fig


def some_entry(df, account_id=None, start_date=None, end_date=None, *args, **kwargs):
    """
    Compatibility stub (safe import-time behavior).
    Replace with real implementation if needed.
    """
    try:
        dfc = base.get_filtered_trading_df(df, account_id=account_id, start_date=start_date, end_date=end_date)
    except Exception:
        dfc = None
    if dfc is None:
        dfc = pd.DataFrame()
    if dfc.empty:
        return setup_base_figure()
    # Default behavior: render the daily points view for the filtered data
    return create_points_view(dfc, mode="daily")