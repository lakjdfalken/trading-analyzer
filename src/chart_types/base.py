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
    """Create a basic Plotly figure with standard layout"""
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
    """Apply standard layout settings to a Plotly figure"""
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

def ensure_currency_column(df, default_currency='USD'):
    """
    Ensures DataFrame has a currency column, adds default if missing
    """
    df_copy = df.copy()
    if 'currency' not in df_copy.columns:
        df_copy['currency'] = default_currency
    return df_copy

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

def get_broker_currency_groups(df):
    """
    Returns grouped data by broker and currency combinations
    """
    df_copy = prepare_dataframe(df)
    
    # Ensure currency column exists, default to USD if missing
    if 'currency' not in df_copy.columns:
        df_copy['currency'] = 'USD'
    
    # Group by broker and currency
    groups = df_copy.groupby(['broker_name', 'currency'])
    
    return groups

def get_trading_data_by_currency(df, broker=None, currency=None):
    """
    Returns trading data filtered by broker and/or currency
    """
    trading_data = get_trading_data(df)
    
    if broker:
        trading_data = trading_data[trading_data['broker_name'] == broker]
    
    if currency:
        # Ensure currency column exists
        if 'currency' not in trading_data.columns:
            trading_data['currency'] = 'USD'
        trading_data = trading_data[trading_data['currency'] == currency]
    
    return trading_data

def calculate_currency_metrics(df, broker, currency):
    """
    Calculate P/L metrics for a specific broker-currency combination
    """
    broker_currency_data = df[
        (df['broker_name'] == broker) & 
        (df['currency'] == currency)
    ].copy()
    
    total_pl = broker_currency_data['P/L'].sum()
    days_traded = len(broker_currency_data['Transaction Date'].dt.date.unique())
    daily_average = total_pl / days_traded if days_traded > 0 else 0
    
    # Calculate funding charges
    charges_mask = broker_currency_data['Action'].str.contains('Funding charge', case=False, na=False)
    total_charges = broker_currency_data[charges_mask]['P/L'].sum()
    
    # Calculate deposits and withdrawals
    deposits = broker_currency_data[broker_currency_data['Action'] == 'Fund rece received']['P/L'].sum()
    withdrawals = broker_currency_data[broker_currency_data['Action'] == 'Fund payable']['P/L'].sum()
    
    return {
        'total_pl': total_pl,
        'daily_average': daily_average,
        'total_charges': total_charges,
        'deposits': deposits,
        'withdrawals': withdrawals,
        'currency': currency
    }

def convert_to_base_currency(amount, from_currency, exchange_rates, base_currency='SEK'):
    """
    Convert amount from one currency to base currency
    """
    if from_currency == base_currency:
        return amount
    
    if from_currency in exchange_rates:
        # Direct conversion using the exchange rate
        return amount * exchange_rates[from_currency]
    else:
        logger.warning(f"Exchange rate not found for {from_currency}, using original amount")
        return amount

def format_currency_with_conversion(value, currency, exchange_rates, base_currency='SEK', show_converted=True):
    """
    Format currency value with optional conversion display
    """
    symbol = CURRENCY_SYMBOLS.get(currency, '')
    formatted = f'{symbol}{value:,.2f}'
    
    if show_converted and currency != base_currency:
        converted_value = convert_to_base_currency(value, currency, exchange_rates, base_currency)
        base_symbol = CURRENCY_SYMBOLS.get(base_currency, '')
        formatted += f' ({base_symbol}{converted_value:,.2f})'
    
    return formatted

def get_unified_currency_data(df, exchange_rates, target_currency='SEK'):
    """
    Convert all monetary values to a single currency for unified analysis
    """
    df_copy = df.copy()
    
    # Ensure currency column exists - use target_currency as default
    if 'currency' not in df_copy.columns:
        df_copy['currency'] = target_currency
    
    # Convert monetary columns
    monetary_columns = ['Amount', 'P/L', 'Balance', 'Fund_Balance', 'Opening', 'Closing']
    
    for col in monetary_columns:
        if col in df_copy.columns:
            df_copy[f'{col}_Original'] = df_copy[col].copy()  # Keep original values
            
            # Convert each row based on its currency
            for idx, row in df_copy.iterrows():
                original_currency = row['currency']
                if pd.notna(row[col]) and original_currency != target_currency:
                    converted_value = convert_to_base_currency(
                        row[col], original_currency, exchange_rates, target_currency
                    )
                    df_copy.at[idx, col] = converted_value
            
            # Update currency column to reflect conversion
            df_copy['currency'] = target_currency
    
    return df_copy
