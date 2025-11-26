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
    get_trading_data,
    setup_base_figure,
    top_markets_by_pl,
)

logger = logging.getLogger(__name__)


def get_trade_distribution(df):
    trading_data = get_trading_data(df)
    wins = trading_data[trading_data["P/L"] > 0]
    losses = trading_data[trading_data["P/L"] < 0]

    win_count = len(wins)
    loss_count = len(losses)
    total_trades = win_count + loss_count

    win_rate = (win_count / total_trades * 100) if total_trades > 0 else 0
    avg_win = wins["P/L"].mean() if not wins.empty else 0
    avg_loss = losses["P/L"].mean() if not losses.empty else 0
    total_win = wins["P/L"].sum() if not wins.empty else 0
    total_loss = losses["P/L"].sum() if not losses.empty else 0

    return win_count, loss_count, win_rate, avg_win, avg_loss, total_win, total_loss


def create_distribution_days(df):
    (
        wins,
        losses,
        win_rate,
        avg_win,
        avg_loss,
        total_win,
        total_loss,
    ) = get_trade_distribution(df)

    fig = setup_base_figure()

    fig.add_trace(
        go.Bar(
            x=["Wins", "Losses"],
            y=[wins, losses],
            marker_color=[COLORS["profit"], COLORS["loss"]],
            text=[
                f"Trades: <br>{wins}<br>(P/L: {total_win:.0f})",
                f"{losses}<br>(P/L: {total_loss:.0f})",
            ],
            textposition="inside",
            textfont=dict(color="white", size=12),
        )
    )

    fig.add_annotation(
        text=(
            f"Win Rate: {win_rate:.1f}%<br>"
            f"Avg Win: {avg_win:.2f}<br>"
            f"Avg Loss: {avg_loss:.2f}"
        ),
        xref="paper",
        yref="paper",
        x=0.92,
        y=0.95,
        showarrow=False,
        bgcolor="white",
        bordercolor="black",
        borderwidth=1,
    )

    fig = apply_standard_layout(fig, "Trades Win/Loss")

    return fig
