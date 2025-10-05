from .base import get_trading_data, apply_standard_layout, setup_base_figure, format_currency, get_unified_currency_data
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from settings import (COLORS, DEFAULT_BASE_CURRENCY, DEFAULT_EXCHANGE_RATES, 
                     AVAILABLE_CURRENCIES, CURRENCY_SYMBOLS)
import logging
import pandas as pd
from logger import setup_logger

logger = logging.getLogger(__name__)

def create_daily_pl_vs_trades(df, exchange_rates=None, base_currency=None, account_id=None):
    """Create daily P/L vs trades chart with account filtering"""
    # Filter by account if specified
    if account_id and account_id != "all":
        df = df[df['account_id'] == account_id]
    """Create daily P/L vs trades chart with multi-currency support"""
    if exchange_rates is None:
        exchange_rates = DEFAULT_EXCHANGE_RATES

    if base_currency is None:
        base_currency = DEFAULT_BASE_CURRENCY

    trading_df = get_trading_data(df)
    
    if trading_df.empty:
        logger.warning("No trading data available")
        return setup_base_figure()

    # Convert all data to base currency
    unified_data = get_unified_currency_data(trading_df, exchange_rates, base_currency)

    # Add original currency info to unified data for labeling
    unified_data['original_currency'] = trading_df['Currency'].values

    # Get unique currencies from data, but only include those defined in settings
    data_currencies = set(unified_data['original_currency'].unique())
    available_currencies_set = set(AVAILABLE_CURRENCIES)
    currencies = sorted(data_currencies.intersection(available_currencies_set))
    
    if not currencies:
        logger.warning("No valid currencies found in data")
        return setup_base_figure()

    # Create subplots for each currency
    fig = make_subplots(
        rows=len(currencies),
        cols=1,
        subplot_titles=[f'Daily P/L vs Trades - {currency} ({CURRENCY_SYMBOLS.get(currency, currency)})' 
                       for currency in currencies],
        vertical_spacing=0.08,
        specs=[[{"secondary_y": True}] for _ in currencies]  # Enable secondary y-axis
    )

    # Create color mapping based on AVAILABLE_CURRENCIES order
    currency_colors = {}
    base_colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f']
    
    for i, currency in enumerate(AVAILABLE_CURRENCIES):
        currency_colors[currency] = base_colors[i % len(base_colors)]

    # Get initial balance for percentage calculations
    initial_balance = trading_df['Balance'].iloc[0] if not trading_df.empty else 1000

    for curr_idx, currency in enumerate(currencies):
        logger.debug(f"Processing currency {currency} (index {curr_idx})")

        # Filter unified data by original currency
        currency_data = unified_data[unified_data['original_currency'] == currency].copy()
        
        if currency_data.empty:
            logger.warning(f"No data for currency {currency}")
            continue

        # Calculate daily metrics
        daily_pl_original = currency_data.groupby(currency_data['Transaction Date'].dt.date)['P/L'].sum()

        # Convert to base currency if needed
        if currency != base_currency:
            conversion_rate = exchange_rates.get(currency, 1.0) / exchange_rates.get(base_currency, 1.0)
            daily_pl = daily_pl_original * conversion_rate
        else:
            daily_pl = daily_pl_original

        daily_pl_pct = (daily_pl / abs(initial_balance)) * 100
        daily_trades = currency_data.groupby(currency_data['Transaction Date'].dt.date).size()

        # Calculate summary statistics
        total_pl = daily_pl.sum()
        total_pl_pct = daily_pl_pct.sum()
        total_trades = daily_trades.sum()
        avg_pl_per_trade = total_pl / total_trades if total_trades > 0 else 0
        
        # Calculate correlation between P/L and trade count
        correlation = daily_pl_pct.corr(daily_trades) if len(daily_pl_pct) > 1 else 0

        # Get currency symbol for display
        currency_symbol = CURRENCY_SYMBOLS.get(currency, currency)
        base_currency_symbol = CURRENCY_SYMBOLS.get(base_currency, base_currency)

        # Prepare hover text with comprehensive information
        hover_text_pl = []
        hover_text_trades = []
        
        for date in daily_pl.index:
            pl_value_converted = daily_pl[date]  # Converted to base currency
            pl_value_original = daily_pl_original[date]  # Original currency
            pl_pct = daily_pl_pct[date]
            trade_count = daily_trades.get(date, 0)
            
            hover_text_pl.append(
                f'<b>Date</b>: {date}<br>'
                f'<b>P/L %</b>: {pl_pct:.2f}%<br>'
                f'<b>P/L Amount</b>: {base_currency_symbol}{pl_value_converted:.2f} ({base_currency})<br>'
                f'<b>Original P/L</b>: {currency_symbol}{pl_value_original:.2f} ({currency})<br>'
                f'<b>Trades</b>: {trade_count}'
            )
            
        for date in daily_trades.index:
            trade_count = daily_trades[date]
            pl_value_converted = daily_pl.get(date, 0)
            pl_value_original = daily_pl_original.get(date, 0)
            
            hover_text_trades.append(
                f'<b>Date</b>: {date}<br>'
                f'<b>Trade Count</b>: {trade_count}<br>'
                f'<b>P/L Amount</b>: {base_currency_symbol}{pl_value_converted:.2f} ({base_currency})<br>'
                f'<b>Original P/L</b>: {currency_symbol}{pl_value_original:.2f} ({currency})'
            )

        # Get currency color from our mapping
        color = currency_colors.get(currency, currency_colors.get(AVAILABLE_CURRENCIES[0], '#1f77b4'))

        # Add P/L bars (primary y-axis)
        fig.add_trace(
            go.Bar(
                x=daily_pl_pct.index,
                y=daily_pl_pct.values,
                name=f"Daily P/L % - {currency}",
                marker_color=[COLORS['profit'] if x >= 0 else COLORS['loss'] for x in daily_pl_pct],
                text=[f"{x:.1f}%" for x in daily_pl_pct],
                textposition='auto',
                cliponaxis=False,
                hovertext=hover_text_pl,
                hoverinfo='text',
                yaxis='y',
                offsetgroup=1
            ),
            row=curr_idx + 1, col=1
        )

        # Add trade count line (secondary y-axis)
        fig.add_trace(
            go.Scatter(
                x=daily_trades.index,
                y=daily_trades.values,
                mode='lines+markers',
                name=f"Trade Count - {currency}",
                line=dict(color=color, width=2),
                marker=dict(size=6, color=color),
                hovertext=hover_text_trades,
                hoverinfo='text',
                yaxis='y2'
            ),
            row=curr_idx + 1, col=1, secondary_y=True
        )

        # Update y-axes labels for this subplot
        fig.update_yaxes(
            title_text="P/L (%)", 
            row=curr_idx + 1, col=1, 
            secondary_y=False,
            showgrid=True, 
            gridwidth=1, 
            gridcolor='LightGray'
        )
        
        fig.update_yaxes(
            title_text="Number of Trades", 
            row=curr_idx + 1, col=1, 
            secondary_y=True,
            showgrid=False  # Don't show grid for secondary y-axis to avoid clutter
        )

        # Update x-axis
        fig.update_xaxes(
            showgrid=True, 
            gridwidth=1, 
            gridcolor='LightGray',
            row=curr_idx + 1, col=1
        )

    # Add comprehensive annotations with summary statistics
    annotations = []
    
    for curr_idx, currency in enumerate(currencies):
        currency_data = unified_data[unified_data['original_currency'] == currency]
        if currency_data.empty:
            continue
            
        daily_pl_original = currency_data.groupby(currency_data['Transaction Date'].dt.date)['P/L'].sum()
        daily_trades = currency_data.groupby(currency_data['Transaction Date'].dt.date).size()
        
        # Convert to base currency if needed
        if currency != base_currency:
            conversion_rate = exchange_rates.get(currency, 1.0) / exchange_rates.get(base_currency, 1.0)
            daily_pl = daily_pl_original * conversion_rate
        else:
            daily_pl = daily_pl_original
        
        total_pl = daily_pl.sum()
        total_pl_pct = (daily_pl.sum() / abs(initial_balance)) * 100
        total_trades = daily_trades.sum()
        avg_pl_per_trade = total_pl / total_trades if total_trades > 0 else 0
        correlation = daily_pl.corr(daily_trades) if len(daily_pl) > 1 else 0
        
        # Get currency symbols for display
        currency_symbol = CURRENCY_SYMBOLS.get(currency, currency)
        base_currency_symbol = CURRENCY_SYMBOLS.get(base_currency, base_currency)
        
        # Calculate y position for this currency's subplot
        y_pos = 1 - (curr_idx / len(currencies)) - 0.02
        
        # Summary statistics annotation
        annotations.append(
            dict(
                text=(
                    f'<b>{currency} ({currency_symbol}) Summary:</b><br>'
                    f'Total P/L: {total_pl_pct:.1f}% ({base_currency_symbol}{total_pl:.2f})<br>'
                    f'Total Trades: {total_trades}<br>'
                    f'Avg P/L per Trade: {base_currency_symbol}{avg_pl_per_trade:.2f}<br>'
                    f'P/L vs Trades Correlation: {correlation:.3f}'
                ),
                xref='paper',
                yref='paper',
                x=0.02,
                y=y_pos,
                showarrow=False,
                bgcolor='rgba(255,255,255,0.8)',
                bordercolor='gray',
                borderwidth=1,
                font=dict(size=10)
            )
        )

    # Update layout
    fig.update_layout(
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        margin=dict(t=80, b=50, l=80, r=80),
        bargap=0.15,
        autosize=True,
        plot_bgcolor='white',
        paper_bgcolor='white',
        annotations=annotations,
        height=400 * len(currencies)  # Adjust height based on number of currencies
    )

    return fig

def create_daily_pl(df):
    info_text = (
        "Daily P/L Calculation:<br><br>"
        "- Long positions: Sum of profits/losses from buy trades<br>"
        "- Short positions: Sum of profits/losses from sell trades<br>"
        "- Percentages calculated against daily starting balance"
    )
    
    fig = setup_base_figure()

    trading_df = get_trading_data(df)
    trading_df = trading_df.sort_values('Transaction Date')
    
    # Try to extract currency from the dataframe
    currency = None
    if 'Currency' in trading_df.columns:
        # Use the most common currency in the dataframe
        currency = trading_df['Currency'].value_counts().index[0]
    elif 'Description' in trading_df.columns and not trading_df['Description'].empty:
        # Try to extract from description strings (common pattern in trading data)
        # This looks for currency symbols like $, €, £ etc. in the first description
        import re
        first_desc = trading_df['Description'].iloc[0]
        currency_match = re.search(r'[$€£¥]', first_desc)
        if currency_match:
            currency = currency_match.group(0)
    
    # If still no currency found, default to $
    if not currency:
        currency = '$'
    
    logger.debug(f"\nFull trading data sample:\n{trading_df[['Transaction Date', 'Action', 'Description', 'Amount', 'Balance', 'P/L']].head()}")
    daily_pl = trading_df.groupby(trading_df['Transaction Date'].dt.date)['P/L'].sum() 
    daily_balances = {}
    
    for date in sorted(trading_df['Transaction Date'].dt.date.unique()):
        day_data = trading_df[trading_df['Transaction Date'].dt.date == date]
        
        logger.debug(f"\nDetailed day data for {date}:")
        logger.debug(f"All transactions:\n{day_data[['Transaction Date', 'Action', 'Description', 'Amount', 'Balance', 'P/L']]}")
        
        day_first_balance = day_data['Balance'].iloc[0]
        day_first_pl = day_data['P/L'].iloc[0]
        day_initial_balance = day_first_balance - day_first_pl
        
        daily_balances[date] = day_initial_balance
        
        logger.debug(f"Day's first balance: {day_first_balance}")
        logger.debug(f"Day's first P/L: {day_first_pl}")
        logger.debug(f"Day's initial balance: {day_initial_balance}")
        
        day_total_pl = day_data['P/L'].sum()
        ending_balance = day_initial_balance + day_total_pl
        logger.debug(f"Day's total P/L: {day_total_pl}")
        logger.debug(f"Day's ending balance: {ending_balance}")
    
    logger.debug(f"\nFinal daily balances:\n{daily_balances}")
    
    # Calculate daily P/L for long and short positions
    long_pl = trading_df[trading_df['Amount'] > 0].groupby(
        trading_df['Transaction Date'].dt.date)['P/L'].sum()
    short_pl = trading_df[trading_df['Amount'] < 0].groupby(
        trading_df['Transaction Date'].dt.date)['P/L'].sum()
    
    logger.debug(f"\nRaw long P/L:\n{long_pl}")
    logger.debug(f"Raw short P/L:\n{short_pl}")
    
    # Calculate percentages using correct daily balances
    long_pl_pct = pd.Series({date: (pl / daily_balances[date]) * 100 
                            for date, pl in long_pl.items()})
    short_pl_pct = pd.Series({date: (pl / daily_balances[date]) * 100 
                             for date, pl in short_pl.items()})
    
    logger.debug(f"\nDaily long P/L percentages:\n{long_pl_pct}")
    logger.debug(f"Daily short P/L percentages:\n{short_pl_pct}")
    
    total_long_pct = long_pl_pct.sum()
    total_short_pct = short_pl_pct.sum()
    total_pl_pct = total_long_pct + total_short_pct
    
    logger.debug(f"\nTotal long percentage: {total_long_pct}%")
    logger.debug(f"Total short percentage: {total_short_pct}%")
    logger.debug(f"Total P/L percentage: {total_pl_pct}%")
    all_dates = sorted(set(long_pl_pct.index) | set(short_pl_pct.index))
    avg_daily_pct = (total_pl_pct / len(all_dates))
    trading_days = len(all_dates)
    
    fig = go.Figure()

    # Prepare hover text for long positions
    long_hover_text = []
    for date in all_dates:
        pl_pct = long_pl_pct.get(date, 0)
        pl_value = long_pl.get(date, 0)
        long_hover_text.append(f'<b>Date</b>: {date}<br><b>Long P/L %</b>: {pl_pct:.2f}%<br><b>Actual Long P/L</b>: {currency}{abs(pl_value):.2f}')
    
    # Prepare hover text for short positions
    short_hover_text = []
    for date in all_dates:
        pl_pct = short_pl_pct.get(date, 0)
        pl_value = short_pl.get(date, 0)
        short_hover_text.append(f'<b>Date</b>: {date}<br><b>Short P/L %</b>: {pl_pct:.2f}%<br><b>Actual Short P/L</b>: {currency}{abs(pl_value):.2f}')

    # Add long position bars with hover text
    fig.add_trace(go.Bar(
        x=all_dates,
        y=[long_pl_pct.get(date, 0) for date in all_dates],
        name='Long P/L',
        marker_color=COLORS['profit'],
        text=[f"{long_pl_pct.get(date, 0):.1f}%" for date in all_dates],
        textposition='auto',
        cliponaxis=False,
        hovertext=long_hover_text,
        hoverinfo='text'
    ))
    
    # Add short position bars with hover text
    fig.add_trace(go.Bar(
        x=all_dates,
        y=[short_pl_pct.get(date, 0) for date in all_dates],
        name='Short P/L',
        marker_color=COLORS['loss'],
        text=[f"{short_pl_pct.get(date, 0):.1f}%" for date in all_dates],
        textposition='auto',
        cliponaxis=False,
        hovertext=short_hover_text,
        hoverinfo='text'
    ))

    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='LightGray')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='LightGray')

    # Final layout update with toggleable info button
    fig.update_layout(
        barmode='group',
        bargap=0.15,
        bargroupgap=0.05,
        showlegend=True,
        xaxis=dict(showgrid=False, zeroline=False),
        margin=dict(t=50, b=50),
        plot_bgcolor='white',
        paper_bgcolor='white',
        updatemenus=[dict(
            type="buttons",
            direction="left",
            active=-1,
            buttons=[dict(
                args=[{"annotations[0].visible": True}],
                args2=[{"annotations[0].visible": False}],
                label="ⓘ",
                method="relayout"
            )],
            x=0.98,
            y=0.98,
            xanchor="right",
            yanchor="top",
            bgcolor="white",
            bordercolor="black",
            borderwidth=1,
            showactive=False
        )],
        annotations=[
          dict(
            text=info_text,
            x=0.5,
            y=0.5,
            xref="paper",
            yref="paper",
            showarrow=False,
            bgcolor="white",
            bordercolor="black",
            borderwidth=1,
            visible=False
          ),
          dict(
            text=(f'Total Long: {total_long_pct:.1f}% <br>'
              f'Total Short: {total_short_pct:.1f}% <br>'
              f'Total P/L: {total_pl_pct:.1f}% <br>'
              f'Avg Daily P/L: {avg_daily_pct:.1f}%<br>'
              f'Trading Days: {trading_days}'),
            xref='paper', 
            yref='paper',
            x=0.02, 
            y=0.98,
            showarrow=False,
            bgcolor='white',
            bordercolor='gray',
            borderwidth=1
          ),
        ]
    )
    return fig