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


def get_position_data(df, currency):
    """Returns position data for a specific currency"""
    trading_df = get_trading_data(df)
    currency_df = trading_df[trading_df["Currency"] == currency]

    long_pos = currency_df[currency_df["Amount"] > 0]["Amount"].sum()
    short_pos = abs(currency_df[currency_df["Amount"] < 0]["Amount"].sum())
    long_pl = currency_df[currency_df["Amount"] > 0]["P/L"].sum()
    short_pl = currency_df[currency_df["Amount"] < 0]["P/L"].sum()

    return {
        "long_pos": long_pos,
        "short_pos": short_pos,
        "long_pl": long_pl,
        "short_pl": short_pl,
    }


def create_position_distribution(df):
    fig = setup_base_figure()
    position_data = []
    labels = []
    colors = []
    pl_text = []

    trading_df = get_trading_data(df)

    for currency in trading_df["Currency"].unique():
        pos_data = get_position_data(df, currency)

        if pos_data["long_pos"] > 0:
            position_data.append(pos_data["long_pos"])
            labels.append(f"Long ({currency})")
            colors.append(COLORS["profit"])
            pl_text.append(
                f"Long P/L: {format_currency(pos_data['long_pl'], currency)}"
            )

        if pos_data["short_pos"] > 0:
            position_data.append(pos_data["short_pos"])
            labels.append(f"Short ({currency})")
            colors.append(COLORS["loss"])
            pl_text.append(
                f"Short P/L: {format_currency(pos_data['short_pl'], currency)}"
            )

    # Create pie chart
    fig.add_trace(
        go.Pie(
            values=position_data,
            labels=labels,
            marker_colors=colors,
            textinfo="percent+label",
            hovertemplate="%{label}<br>Amount: %{value:.2f}<br>%{percent}<extra></extra>",
        )
    )

    # Add P/L summary
    total_pl = trading_df["P/L"].sum()
    pl_summary = "<br>".join(
        pl_text
        + [f"Total P/L: {format_currency(total_pl, trading_df['Currency'].iloc[0])}"]
    )

    fig.add_annotation(
        text=pl_summary,
        xref="paper",
        yref="paper",
        x=1.2,
        y=0,
        showarrow=False,
        bgcolor="white",
        bordercolor="gray",
        borderwidth=1,
    )

    # Update layout for better pie chart display
    fig.update_layout(
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(t=100, b=100, r=200),  # Increased right margin for P/L text
    )

    fig = apply_standard_layout(fig, "Long vs Short Positions")

    return fig
