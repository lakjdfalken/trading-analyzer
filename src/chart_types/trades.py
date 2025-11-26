import logging

import pandas as pd
import plotly.graph_objects as go

from settings import COLORS

from .base import (
    aggregate_pl_by_period,
    apply_standard_layout,
    coerce_date,
    coerce_pl_numeric,
    ensure_market_column,
    find_date_col,
    find_pl_col,
    format_currency,
    get_trading_data,
    prepare_dataframe,
    setup_base_figure,
    top_markets_by_pl,
)

logger = logging.getLogger(__name__)


def create_daily_trade_count(df):
    trading_df = get_trading_data(df)
    daily_trades = trading_df.groupby(trading_df["Transaction Date"].dt.date).size()
    avg_trades = daily_trades.mean()

    fig = setup_base_figure()

    # Add bar chart for daily trades
    fig.add_trace(
        go.Bar(
            x=list(daily_trades.index),
            y=daily_trades.values,
            name="Daily Trades",
            marker_color=COLORS["trading"],
            opacity=0.6,
        )
    )

    # Add average line
    fig.add_trace(
        go.Scatter(
            x=list(daily_trades.index),
            y=[avg_trades] * len(daily_trades),
            name=f"Average ({avg_trades:.1f} trades/day)",
            line=dict(color=COLORS["trading"], dash="dash"),
        )
    )

    # Add summary annotation
    summary_text = (
        f"Total Trades: {daily_trades.sum()}<br>"
        f"Average: {avg_trades:.1f} trades/day<br>"
        f"Max: {daily_trades.max()} trades/day"
    )

    fig.add_annotation(
        text=summary_text,
        xref="paper",
        yref="paper",
        x=1.02,
        y=1,
        showarrow=False,
        bgcolor="white",
        bordercolor="gray",
        borderwidth=1,
    )

    fig.update_layout(barmode="overlay", margin=dict(r=200), xaxis_tickangle=45)

    fig = apply_standard_layout(fig, "Daily Trading Volume")

    return fig
