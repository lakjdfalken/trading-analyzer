import matplotlib.pyplot as plt
import pandas as pd
# Base utilities used across all chart types
from settings import FIGURE_SIZES, COLORS, CURRENCY_SYMBOLS

def format_currency(value, currency):
    symbol = CURRENCY_SYMBOLS.get(currency, '')
    return f'{symbol}{abs(value):,.2f}'

def setup_base_figure(figsize='default'):
    plt.style.use('bmh')
    fig = plt.Figure(figsize=FIGURE_SIZES.get(figsize, FIGURE_SIZES['default']))
    ax = fig.add_subplot(111)
    return fig, ax

def apply_common_styling(ax, title, xlabel=None, ylabel=None):
    ax.set_title(title, fontsize=14, pad=15)
    if xlabel:
        ax.set_xlabel(xlabel, fontsize=12)
    if ylabel:
        ax.set_ylabel(ylabel, fontsize=12)
    ax.tick_params(axis='x', rotation=45)
    ax.grid(True, alpha=0.3)

def prepare_dataframe(df):
    """
    Prepares dataframe with proper datetime handling and returns a clean copy
    """
    df_copy = df.copy()
    df_copy['Transaction Date'] = pd.to_datetime(df_copy['Transaction Date'])
    df_copy['Open Period'] = pd.to_datetime(df_copy['Open Period'])
    return df_copy

def get_trading_data(df):
    """
    Returns dataframe filtered for trading transactions
    """
    df_copy = prepare_dataframe(df)
    trading_mask = ~df_copy['Action'].str.startswith('Fund')
    return df_copy[trading_mask]

def get_trade_counts(df):
    """
    Returns daily trade counts
    """
    df_copy = prepare_dataframe(df)
    trade_df = df_copy[df_copy['Action'].str.contains('Trade', case=False)]
    return trade_df.groupby(trade_df['Transaction Date'].dt.date).size()
