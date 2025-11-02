from .base import prepare_dataframe, get_trading_data, format_currency, setup_base_figure, apply_standard_layout
import plotly.graph_objects as go
from settings import COLORS
import re
import pandas as pd
import logging
from .base import (
    find_date_col,
    find_pl_col,
    coerce_date,
    coerce_pl_numeric,
    ensure_market_column,
    aggregate_pl_by_period,
    top_markets_by_pl,
)
import chart_types.base as base
logger = logging.getLogger(__name__)


def create_daily_trade_count(df):
    trading_df = get_trading_data(df)
    daily_trades = trading_df.groupby(trading_df['Transaction Date'].dt.date).size()
    avg_trades = daily_trades.mean()
    
    fig = setup_base_figure()
    
    # Add bar chart for daily trades
    fig.add_trace(go.Bar(
        x=list(daily_trades.index),
        y=daily_trades.values,
        name='Daily Trades',
        marker_color=COLORS['trading'],
        opacity=0.6
    ))
    
    # Add average line
    fig.add_trace(go.Scatter(
        x=list(daily_trades.index),
        y=[avg_trades] * len(daily_trades),
        name=f'Average ({avg_trades:.1f} trades/day)',
        line=dict(color=COLORS['trading'], dash='dash')
    ))
    
    # Add summary annotation
    summary_text = (
        f'Total Trades: {daily_trades.sum()}<br>'
        f'Average: {avg_trades:.1f} trades/day<br>'
        f'Max: {daily_trades.max()} trades/day'
    )
    
    fig.add_annotation(
        text=summary_text,
        xref='paper', yref='paper',
        x=1.02, y=1,
        showarrow=False,
        bgcolor='white',
        bordercolor='gray',
        borderwidth=1
    )
    
    fig.update_layout(
        barmode='overlay',
        margin=dict(r=200),
        xaxis_tickangle=45
    )
    
    fig = apply_standard_layout(fig, "Daily Trading Volume")
    
    return fig

def _find_column(df, candidates):
    if df is None:
        return None
    for c in df.columns:
        key = re.sub(r'[\s\-_]', '', c.strip().lower())
        if key in candidates:
            return c
    return None

def _find_date_col(df):
    return _find_column(df, {'transactiondate', 'transaction_date', 'transaction-date', 'date'})

def _find_pl_col(df):
    return _find_column(df, {'p/l', 'pl', 'plamount', 'profitloss', 'profit'})

def _coerce_date(df, col):
    if col and col in df.columns:
        df[col] = pd.to_datetime(df[col], errors='coerce')
    return col

def _coerce_pl_numeric(df, col, alias='_pl_numeric'):
    if col and col in df.columns:
        df[alias] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
    else:
        df[alias] = 0.0
    return alias

def some_entry(df, *args, **kwargs):
    """
    Placeholder cleaned up from an invalid example signature.
    Returns an empty figure so the module can be imported safely.
    Replace with real implementation as needed.
    """
    try:
        from .base import setup_base_figure
    except Exception:
        import plotly.graph_objects as go
        fig = go.Figure()
        fig.update_layout(title="Not implemented")
        return fig

    return setup_base_figure()
