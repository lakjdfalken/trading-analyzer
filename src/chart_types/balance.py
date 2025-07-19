from plotly.subplots import make_subplots
import pandas as pd
import plotly.graph_objects as go
from .base import (prepare_dataframe, setup_base_figure, apply_standard_layout, 
                   get_trading_pl_without_funding, get_unified_currency_data)
from settings import CURRENCY_SYMBOLS, DEFAULT_BASE_CURRENCY
import logging

logger = logging.getLogger(__name__)

def create_balance_history(df, exchange_rates=None, base_currency=None):
    from settings import DEFAULT_EXCHANGE_RATES, DEFAULT_BASE_CURRENCY
    
    if exchange_rates is None:
        exchange_rates = DEFAULT_EXCHANGE_RATES
    
    if base_currency is None:
        base_currency = DEFAULT_BASE_CURRENCY
    
    # Debug: Check raw input data first
    logger.debug(f"Raw input DataFrame shape: {df.shape}")
    logger.debug(f"Raw input DataFrame columns: {df.columns.tolist()}")
    
    # Check for currency column with different cases
    currency_col = None
    for col in df.columns:
        if col.lower() == 'currency':
            currency_col = col
            break
    
    if currency_col:
        logger.debug(f"Found currency column: '{currency_col}'")
        logger.debug(f"Raw input currencies: {df[currency_col].unique()}")
        logger.debug(f"Raw input currency counts: {df[currency_col].value_counts()}")
        
        # Standardize the column name to lowercase before processing
        df_copy = df.copy()
        if currency_col != 'currency':
            df_copy['currency'] = df_copy[currency_col]
            logger.debug(f"Renamed '{currency_col}' to 'currency'")
    else:
        logger.debug("No currency column found in raw input data")
        df_copy = df.copy()
    
    trading_data = prepare_dataframe(df_copy).copy()

    # Add currency column if it doesn't exist - use SEK as default instead of USD
    if 'currency' not in trading_data.columns:
        logger.warning("No 'currency' column found after prepare_dataframe(), adding default currency")
        trading_data['currency'] = DEFAULT_BASE_CURRENCY

    # Debug: Log unique currencies found after preparation
    logger.debug(f"After prepare_dataframe() - Unique currencies: {trading_data['currency'].unique()}")
    logger.debug(f"After prepare_dataframe() - Currency value counts: {trading_data['currency'].value_counts()}")

    # Sort by date and group by broker
    trading_data = trading_data.sort_values('Transaction Date')
    brokers = trading_data['broker_name'].unique()
    currencies = trading_data['currency'].unique()

    logger.info(f"Processing {len(currencies)} currencies: {currencies}")
    logger.info(f"Processing {len(brokers)} brokers: {brokers}")

    # Create single figure for all currencies
    fig = setup_base_figure()

    # Color palette for different currencies and brokers
    currency_colors = ['blue', 'red', 'green', 'orange', 'purple', 'brown', 'pink', 'gray']
    broker_colors = ['solid', 'dash', 'dot', 'dashdot']
    
    # Also get data without funding for comparison - pass the corrected dataframe
    trading_data_without_funding = get_trading_pl_without_funding(df_copy)
    
    # Add currency column to no-funding data if missing
    if 'currency' not in trading_data_without_funding.columns:
        trading_data_without_funding['currency'] = DEFAULT_BASE_CURRENCY
    
    # Convert ALL data to base currency first for proper comparison
    unified_data = get_unified_currency_data(trading_data, exchange_rates, base_currency)
    unified_data_no_funding = get_unified_currency_data(trading_data_without_funding, exchange_rates, base_currency)
    
    # Add original currency info to unified data for labeling
    unified_data['original_currency'] = trading_data['currency'].values
    unified_data_no_funding['original_currency'] = trading_data_without_funding['currency'].values
    
    # Process each original currency separately - but plot converted values
    for curr_idx, currency in enumerate(currencies):
        logger.debug(f"Processing currency {currency} (index {curr_idx})")
        
        # Filter unified data by original currency
        currency_data = unified_data[unified_data['original_currency'] == currency].copy()
        currency_data_no_funding = unified_data_no_funding[
            unified_data_no_funding['original_currency'] == currency
        ].copy()
        
        logger.debug(f"Currency {currency} has {len(currency_data)} rows")
        
        # Process each broker for this currency
        for broker_idx, broker in enumerate(brokers):
            broker_data = currency_data[currency_data['broker_name'] == broker].copy()
            
            logger.debug(f"Broker {broker} for currency {currency} has {len(broker_data)} rows")
            
            if broker_data.empty:
                logger.debug(f"Skipping empty broker_data for {broker}-{currency}")
                continue
            
            # Calculate metrics per broker-currency combination (in base currency)
            total_pl = broker_data['P/L'].sum()
            days_traded = len(broker_data['Transaction Date'].dt.date.unique())
            daily_average = total_pl / days_traded if days_traded > 0 else 0
            
            # Calculate funding charges for this broker-currency
            charges_mask = broker_data['Action'].str.contains('Funding charge', case=False, na=False)
            total_charges = broker_data[charges_mask]['P/L'].sum()
            
            # Calculate deposits and withdrawals
            deposits = broker_data[broker_data['Action'] == 'Fund receivable']['P/L'].sum()
            withdrawals = broker_data[broker_data['Action'] == 'Fund payable']['P/L'].sum()
            
            # Create trace name
            trace_name = f'{broker} - {currency}' if len(brokers) > 1 else f'{currency}'
            color = currency_colors[curr_idx % len(currency_colors)]
            line_style = broker_colors[broker_idx % len(broker_colors)]
            
            logger.debug(f"Adding trace for {trace_name} with color {color}")
            
            # Add trace for actual balance (converted to base currency)
            fig.add_trace(go.Scatter(
                x=broker_data['Transaction Date'],
                y=broker_data['Balance'],
                mode='lines+markers',
                name=f'{trace_name} Balance',
                line=dict(color=color, dash=line_style, width=2),
                hovertemplate=f'Broker: {broker}<br>Original Currency: {currency}<br>Date: %{{x}}<br>Balance: %{{y:.2f}} {base_currency} (converted)<extra></extra>'
            ))
            
            # Filter no-funding data for this broker-currency
            broker_data_no_funding = currency_data_no_funding[
                currency_data_no_funding['broker_name'] == broker
            ].copy()
            
            if not broker_data_no_funding.empty:
                # Add trace for balance without funding (converted to base currency)
                fig.add_trace(go.Scatter(
                    x=broker_data_no_funding['Transaction Date'],
                    y=broker_data_no_funding['Balance'],
                    mode='lines',
                    name=f'{trace_name} (No Funding)',
                    line=dict(color=color, dash='dot', width=1),
                    opacity=0.7,
                    hovertemplate=f'Broker: {broker}<br>Original Currency: {currency}<br>Date: %{{x}}<br>Balance Without Funding: %{{y:.2f}} {base_currency} (converted)<extra></extra>'
                ))
                
                # Calculate metrics for balance without funding
                total_pl_no_funding = broker_data_no_funding['P/L'].sum()
                daily_average_no_funding = total_pl_no_funding / days_traded if days_traded > 0 else 0
            else:
                total_pl_no_funding = 0
                daily_average_no_funding = 0
            
            # Calculate trading P/L (excluding funding transactions)
            trading_only_mask = ~broker_data['Action'].str.contains('fund', case=False, na=False)
            trading_pl = broker_data[trading_only_mask]['P/L'].sum()
            
            # Format values with base currency symbols (since everything is converted)
            base_currency_symbol = CURRENCY_SYMBOLS.get(base_currency, '')
            
            # Add annotations for broker-currency metrics
            annotation_y_pos = 0.95 - (curr_idx * len(brokers) + broker_idx) * 0.12
            fig.add_annotation(
                text=(f'{broker} ({currency}→{base_currency})<br>'
                      f'Total P/L: {base_currency_symbol}{total_pl:.2f}<br>'
                      f'Daily Avg: {base_currency_symbol}{daily_average:.2f}<br>'
                      f'Funding: {base_currency_symbol}{total_charges:.2f}'),
                xref='paper', yref='paper',
                x=0.02, y=annotation_y_pos,
                xanchor='left', yanchor='top',
                showarrow=False,
                bgcolor='rgba(255,255,255,0.9)',
                bordercolor=color,
                borderwidth=1,
                font=dict(size=9)
            )
    
    # FIXED: Calculate proper cumulative total balance
    # Create a complete timeline and calculate running total balance at each point
    
    # Get all unique dates from all currencies/brokers
    all_dates = sorted(unified_data['Transaction Date'].unique())
    
    # For each date, calculate the total balance across all currencies
    total_balance_timeline = []
    total_balance_no_funding_timeline = []
    
    for date in all_dates:
        # Get the latest balance for each currency/broker combination up to this date
        date_total = 0
        date_total_no_funding = 0
        
        for currency in currencies:
            for broker in brokers:
                # Get latest balance for this currency/broker up to this date
                currency_broker_data = unified_data[
                    (unified_data['original_currency'] == currency) & 
                    (unified_data['broker_name'] == broker) &
                    (unified_data['Transaction Date'] <= date)
                ]
                
                if not currency_broker_data.empty:
                    latest_balance = currency_broker_data.iloc[-1]['Balance']
                    date_total += latest_balance
                
                # Same for no-funding data
                currency_broker_data_no_funding = unified_data_no_funding[
                    (unified_data_no_funding['original_currency'] == currency) & 
                    (unified_data_no_funding['broker_name'] == broker) &
                    (unified_data_no_funding['Transaction Date'] <= date)
                ]
                
                if not currency_broker_data_no_funding.empty:
                    latest_balance_no_funding = currency_broker_data_no_funding.iloc[-1]['Balance']
                    date_total_no_funding += latest_balance_no_funding
        
        total_balance_timeline.append({
            'date': date,
            'total_balance': date_total,
            'total_balance_no_funding': date_total_no_funding
        })
    
    # Convert to DataFrame for easier plotting
    total_timeline_df = pd.DataFrame(total_balance_timeline)
    
    logger.debug(f"Total timeline has {len(total_timeline_df)} points")
    
    # Add total balance line (thick black line)
    fig.add_trace(go.Scatter(
        x=total_timeline_df['date'],
        y=total_timeline_df['total_balance'],
        mode='lines+markers',
        name=f'TOTAL All Currencies ({base_currency})',
        line=dict(color='black', width=4),
        marker=dict(size=6),
        hovertemplate=f'Date: %{{x}}<br>Total Balance: %{{y:.2f}} {base_currency}<extra></extra>'
    ))
    
    # Add total balance without funding (thick gray line)
    fig.add_trace(go.Scatter(
        x=total_timeline_df['date'],
        y=total_timeline_df['total_balance_no_funding'],
        mode='lines',
        name=f'TOTAL No Funding ({base_currency})',
        line=dict(color='gray', width=3, dash='dash'),
        hovertemplate=f'Date: %{{x}}<br>Total Balance (No Funding): %{{y:.2f}} {base_currency}<extra></extra>'
    ))
    
    # Calculate total metrics
    total_pl_all = unified_data['P/L'].sum()
    total_days = len(all_dates)
    total_daily_avg = total_pl_all / total_days if total_days > 0 else 0
    
    # Add total metrics annotation
    base_currency_symbol = CURRENCY_SYMBOLS.get(base_currency, '')
    fig.add_annotation(
        text=(f'TOTAL ALL CURRENCIES<br>'
              f'(Converted to {base_currency})<br>'
              f'Total P/L: {base_currency_symbol}{total_pl_all:.2f}<br>'
              f'Daily Avg: {base_currency_symbol}{total_daily_avg:.2f}'),
        xref='paper', yref='paper',
        x=0.98, y=0.98,
        xanchor='right', yanchor='top',
        showarrow=False,
        bgcolor='rgba(0,0,0,0.1)',
        bordercolor='black',
        borderwidth=2,
        font=dict(size=12, color='black')
    )
    
    # Update layout
    fig = apply_standard_layout(fig, f"Balance History - All Currencies Converted to {base_currency}")
    
    # Update y-axis title
    fig.update_yaxes(title_text=f"Balance ({base_currency})")
    
    # Add a note explaining the lines
    currency_list = ', '.join(currencies)
    fig.add_annotation(
        text=(f"Individual currencies ({currency_list}) converted to {base_currency}<br>"
              f"Each color represents a different original currency<br>"
              f"Black thick line: Total of all currencies<br>"
              f"Gray dashed line: Total excluding funding<br>"
              f"Dotted lines: Individual balances excluding funding"),
        xref='paper', yref='paper',
        x=0.5, y=1.05,
        xanchor='center', yanchor='bottom',
        showarrow=False,
        font=dict(size=10),
        bgcolor='rgba(255,255,255,0.8)',
        bordercolor='black',
        borderwidth=1
    )
    
    logger.info(f"Final figure has {len(fig.data)} traces")
    
    return fig