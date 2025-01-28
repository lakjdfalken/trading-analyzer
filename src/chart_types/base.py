import matplotlib.pyplot as plt
import pandas as pd
# Base utilities used across all chart types
from settings import CURRENCY_SYMBOLS
import logging
logger = logging.getLogger(__name__)
import plotly.graph_objects as go
from plotly.subplots import make_subplots

def format_currency(value, currency):
    symbol = CURRENCY_SYMBOLS.get(currency, '')
    return f'{symbol}{value:,.2f}'  # Now preserves negative signs

def setup_base_figure(figsize='default'):
    fig = go.Figure()
    fig.update_layout(
        template='plotly_white',
        autosize=True,
        margin=dict(l=50, r=50, t=50, b=50),
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    return fig

def apply_common_styling(fig, title, xlabel=None, ylabel=None):
    fig.update_layout(
        title=title,
        xaxis_title=xlabel,
        yaxis_title=ylabel,
        font=dict(size=12),
        # Ensure fluid sizing is maintained
        autosize=True
    )

def prepare_dataframe(df):
    """
    Prepares dataframe with proper datetime handling and returns a clean copy
    """
    df_copy = df.copy()
    df_copy['Transaction Date'] = pd.to_datetime(df_copy['Transaction Date'])
    df_copy['Open Period'] = pd.to_datetime(df_copy['Open Period'])
    return df_copy

def get_trading_data(df):
    df_copy = prepare_dataframe(df)
    df_filtered = df_copy[~df_copy['Action'].str.startswith('Fund')]
    # Debug data before plotting
    logger.debug(f"Data shape in base.py: {df_filtered.shape}")
    logger.debug(f"Unique Fund in base.py: {df_filtered['Action'].str.contains('Fund', case=False).unique()}") 
    return df_filtered
def get_trade_counts(df):
    """
    Returns daily trade counts
    """
    df_copy = prepare_dataframe(df)
    trade_df = df_copy[df_copy['Action'].str.contains('Trade', case=False)]
    return trade_df.groupby(trade_df['Transaction Date'].dt.date).size()
