import matplotlib.pyplot as plt
import pandas as pd
# Base utilities used across all chart types
from settings import CURRENCY_SYMBOLS
import logging
import os
import base64
logger = logging.getLogger(__name__)
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import sqlite3

def format_currency(value, currency):
    symbol = CURRENCY_SYMBOLS.get(currency, '')
    return f'{symbol}{value:,.2f}'  # Now preserves negative signs

def setup_base_figure():
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

def apply_standard_layout(fig, title):
    fig.update_layout(
        title=title,
        plot_bgcolor='white',
        paper_bgcolor='white',
        showlegend=True,
        legend=dict(
            x=0.0,
            y=1.0,
            xanchor='left',
            yanchor='top'
        ),
        margin=dict(
            l=150,    # Left margin for legend
            r=50,     # Right margin
            t=100,    # Top margin
            b=50,     # Bottom margin
            pad=4     # Padding
        ),
        autosize=True
    )
    
    # Add consistent grid styling
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='LightGray')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='LightGray')
    
    return fig
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
    trading_mask = df_copy['Action'].str.contains('Trade', case=False, na=False)
    trading_data = df_copy[trading_mask].copy()
    trading_data['Transaction Date'] = pd.to_datetime(trading_data['Transaction Date'])
    logger.debug(f"Trading data Actions:\n{trading_data['Action'].unique()}")
    logger.debug(f"Trading data Descriptions:\n{trading_data['Description'].unique()}")
    return trading_data
def get_trade_counts(df):
    """
    Returns daily trade counts
    """
    df_copy = prepare_dataframe(df)
    trade_df = df_copy[df_copy['Action'].str.contains('Trade', case=False)]
    return trade_df.groupby(trade_df['Transaction Date'].dt.date).size()

def get_trading_pl_without_funding(df):
    """
    Returns trading data with correct balance progression and pure trading P/L
    """
    df_copy = prepare_dataframe(df).copy()
    df_copy = df_copy.sort_values('Transaction Date')
    
    # Identify funding entries and trading entries
    funding_mask = df_copy['Action'].str.contains('Fund', case=False, na=False)
    trading_mask = df_copy['Action'].str.contains('Trade', case=False, na=False)
    
    # Create a new column for adjusted balance
    df_copy['Adjusted_Balance'] = df_copy['Balance'].copy()
    
    # Process each funding entry
    for idx in df_copy[funding_mask].index:
        funding_pl = df_copy.loc[idx, 'P/L']
        # Only adjust balances after this specific funding entry
        df_copy.loc[idx:, 'Adjusted_Balance'] -= funding_pl
    
    # Replace original Balance with adjusted balance
    df_copy['Balance'] = df_copy['Adjusted_Balance']
    df_copy.drop('Adjusted_Balance', axis=1, inplace=True)
    
    logger.debug(f"Trading data after funding adjustment:\n{df_copy[trading_mask][['Transaction Date', 'Action', 'Description', 'Balance', 'P/L']]}")
    
    return df_copy[trading_mask].copy()


def get_all_data():
    try:
        conn = sqlite3.connect('trading_data.db')
        query = """
            SELECT * FROM transactions 
            ORDER BY "Transaction Date" ASC
        """
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        # Convert date column to datetime
        df['Transaction Date'] = pd.to_datetime(df['Transaction Date'])
        return df
        
    except Exception as e:
        logger.error(f"Error fetching data from database: {str(e)}")
        raise
