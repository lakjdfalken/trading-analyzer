import logging
import pandas as pd
import settings as _settings
import plotly.graph_objects as go
from .base import (
    find_date_col,
    find_pl_col,
    coerce_date,
    coerce_pl_numeric,
    ensure_market_column,
    aggregate_pl_by_period,
    top_markets_by_pl,
    setup_base_figure,
    apply_standard_layout,
)
import chart_types.base as base

logger = logging.getLogger(__name__)

# Defensive defaults from settings
DEFAULT_BASE_CURRENCY = getattr(_settings, "DEFAULT_BASE_CURRENCY", "USD")
DEFAULT_EXCHANGE_RATES = getattr(_settings, "DEFAULT_EXCHANGE_RATES", {})

def create_balance_history(df, base_currency=None, account_id=None, start_date=None, end_date=None):
    """Create balance history chart with account filtering"""
    # Debug: Print initial DataFrame information
    logger.debug(f"Initial DataFrame info:")
    logger.debug(f"Shape: {df.shape}")
    logger.debug(f"Columns: {df.columns.tolist()}")
    logger.debug(f"Sample data: {df.head(1).to_dict('records')}")
   
    logger.debug(f"Account ID filter: {account_id}")

    # Add debug logging to print unique account IDs in the DataFrame
    logger.debug(f"Unique account IDs in DataFrame: {df['account_id'].unique().tolist()}")

    # Check if account_id exists in the DataFrame
    if account_id and account_id != "all":
        # Add debug logging to print the type of account_id
        logger.debug(f"Type of account_id: {type(account_id)}")

        # Convert account_id to integer if it's a string representation of a number
        if isinstance(account_id, str) and account_id.isdigit():
            account_id = int(account_id)
            logger.debug(f"Converted account_id to integer: {account_id}")

        if account_id not in df['account_id'].unique():
            logger.warning(f"Account ID {account_id} not found in DataFrame. Available account IDs: {df['account_id'].unique().tolist()}")
            account_id = None  # Reset account_id to None to avoid filtering

    # Filter by account if specified
    if account_id and account_id != "all":
        df = df[df['account_id'] == account_id]

    if base_currency is None:
        base_currency = DEFAULT_BASE_CURRENCY
    
    # Check if DataFrame is empty after filtering
    if df.empty:
        logger.error("DataFrame is empty after account filtering")
        # Return an empty figure or raise an exception
        fig = go.Figure()
        fig.update_layout(title="No data available")
        return fig

    # Ensure required columns exist
    required_columns = ['Transaction Date', 'broker_name', 'Balance']
    missing_columns = [col for col in required_columns if col not in df.columns]
    
    if missing_columns:
        logger.error(f"Missing required columns: {missing_columns}")
        logger.debug(f"Existing columns: {df.columns.tolist()}")
        raise ValueError(f"Missing required columns: {missing_columns}")

    # Ensure Transaction Date is datetime
    if not pd.api.types.is_datetime64_any_dtype(df['Transaction Date']):
        try:
            df['Transaction Date'] = pd.to_datetime(df['Transaction Date'])
        except Exception as e:
            logger.error(f"Error converting Transaction Date to datetime: {e}")
            raise

    # Add currency column if it doesn't exist
    if 'currency' not in df.columns:
        if 'Currency' in df.columns:
            # normalize to lowercase 'currency' expected by the chart code
            df['currency'] = df['Currency']
            logger.debug("Populated normalized 'currency' from 'Currency' column")
        else:
            # defensive fallback only if dataset truly lacks Currency
            logger.warning("No 'Currency' or normalized 'currency' column found; falling back to DEFAULT_BASE_CURRENCY")
            df['currency'] = DEFAULT_BASE_CURRENCY

    # Sort by date and group by broker
    df = df.sort_values('Transaction Date')
    brokers = df['broker_name'].unique()
    currencies = df['currency'].unique()

    logger.info(f"Processing {len(currencies)} currencies: {currencies}")
    logger.info(f"Processing {len(brokers)} brokers: {brokers}")

    # Create single figure for all currencies
    fig = setup_base_figure()

    # Color palette for different currencies and brokers
    currency_colors = ['blue', 'red', 'green', 'orange', 'purple', 'brown', 'pink', 'gray']
    broker_colors = ['solid', 'dash', 'dot', 'dashdot']
    
    # Process each original currency separately
    for curr_idx, currency in enumerate(currencies):
        logger.debug(f"Processing currency {currency} (index {curr_idx})")
        
        # Filter data by original currency
        currency_data = df[df['currency'] == currency].copy()
        
        logger.debug(f"Currency {currency} has {len(currency_data)} rows")
        
        # Process each broker for this currency
        for broker_idx, broker in enumerate(brokers):
            broker_data = currency_data[currency_data['broker_name'] == broker].copy()
            
            logger.debug(f"Broker {broker} for currency {currency} has {len(broker_data)} rows")
            
            if broker_data.empty:
                logger.debug(f"Skipping empty broker_data for {broker}-{currency}")
                continue
            
            # Create trace name
            trace_name = f'{broker} - {currency}' if len(brokers) > 1 else f'{currency}'
            color = currency_colors[curr_idx % len(currency_colors)]
            line_style = broker_colors[broker_idx % len(broker_colors)]
            
            logger.debug(f"Adding trace for {trace_name} with color {color}")
            
            # Add trace for balance
            fig.add_trace(go.Scatter(
                x=broker_data['Transaction Date'],
                y=broker_data['Balance'],
                mode='lines+markers',
                name=f'{trace_name} Balance',
                line=dict(color=color, dash=line_style, width=2),
                hovertemplate=f'Broker: {broker}<br>Currency: {currency}<br>Date: %{{x}}<br>Balance: %{{y:.2f}} {currency}<extra></extra>'
            ))

    # Update layout
    fig = apply_standard_layout(fig, "Balance History")
    
    # Update y-axis title
    fig.update_yaxes(title_text="Balance")
    
    logger.info(f"Final figure has {len(fig.data)} traces")
    
    return fig