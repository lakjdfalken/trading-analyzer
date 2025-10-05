from .base import get_trading_data, apply_standard_layout, setup_base_figure, format_currency, get_unified_currency_data
import plotly.graph_objects as go
from settings import (COLORS, DEFAULT_BASE_CURRENCY, DEFAULT_EXCHANGE_RATES, 
                     AVAILABLE_CURRENCIES, CURRENCY_SYMBOLS)
import logging
import pandas as pd
from logger import setup_logger

logger = logging.getLogger(__name__)

def create_daily_pl(df, exchange_rates=None, base_currency=None, account_id=None):
    """Create daily P/L chart with improved multi-currency support"""
    if exchange_rates is None:
        exchange_rates = DEFAULT_EXCHANGE_RATES

    if base_currency is None:
        base_currency = DEFAULT_BASE_CURRENCY
    
    if account_id and account_id != "all":
        df = df[df['account_id'] == account_id]

    info_text = (
        "Daily P/L Calculation:<br><br>"
        "- Long positions: Sum of profits/losses from buy trades<br>"
        "- Short positions: Sum of profits/losses from sell trades<br>"
        "- Percentages calculated against daily starting balance<br>"
        "- All amounts converted to base currency for comparison"
    )

    fig = setup_base_figure()

    trading_df = get_trading_data(df)
    
    if trading_df.empty:
        logger.warning("No trading data available")
        return fig

    trading_df = trading_df.sort_values('Transaction Date')

    # Convert all data to base currency
    unified_data = get_unified_currency_data(trading_df, exchange_rates, base_currency)

    # Add original currency info to unified data for labeling
    unified_data['original_currency'] = trading_df['Currency'].values

    # Get unique currencies from data, but only include those defined in settings
    data_currencies = set(unified_data['original_currency'].unique())
    available_currencies_set = set(AVAILABLE_CURRENCIES)
    currencies = sorted(data_currencies.intersection(available_currencies_set))

    # Create color mapping based on AVAILABLE_CURRENCIES order
    currency_colors = {}
    base_colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']
    
    for i, currency in enumerate(AVAILABLE_CURRENCIES):
        currency_colors[currency] = base_colors[i % len(base_colors)]

    # Get initial balance for percentage calculations
    initial_balance = trading_df['Balance'].iloc[0] if not trading_df.empty else 1000

    # Track overall statistics
    all_long_pct = 0
    all_short_pct = 0
    all_trading_days = set()

    for curr_idx, currency in enumerate(currencies):
        logger.debug(f"Processing currency {currency} (index {curr_idx})")

        # Filter unified data by original currency
        currency_data = unified_data[unified_data['original_currency'] == currency].copy()
        
        if currency_data.empty:
            continue

        # Calculate daily balances for this currency
        daily_balances = {}
        for date in sorted(currency_data['Transaction Date'].dt.date.unique()):
            day_data = currency_data[currency_data['Transaction Date'].dt.date == date]
            day_first_balance = day_data['Balance'].iloc[0]
            day_first_pl = day_data['P/L'].iloc[0]
            day_initial_balance = day_first_balance - day_first_pl
            daily_balances[date] = day_initial_balance

        # Calculate daily P/L for long and short positions
        long_pl_original = currency_data[currency_data['Amount'] > 0].groupby(
            currency_data['Transaction Date'].dt.date)['P/L'].sum()
        short_pl_original = currency_data[currency_data['Amount'] < 0].groupby(
            currency_data['Transaction Date'].dt.date)['P/L'].sum()

        # Convert to base currency if needed
        if currency != base_currency:
            conversion_rate = exchange_rates.get(currency, 1.0) / exchange_rates.get(base_currency, 1.0)
            long_pl = long_pl_original * conversion_rate
            short_pl = short_pl_original * conversion_rate
        else:
            long_pl = long_pl_original
            short_pl = short_pl_original

        # Calculate percentages using correct daily balances
        long_pl_pct = pd.Series({date: (pl / daily_balances.get(date, initial_balance)) * 100
                                for date, pl in long_pl.items()})
        short_pl_pct = pd.Series({date: (pl / daily_balances.get(date, initial_balance)) * 100
                                 for date, pl in short_pl.items()})

        # Get all dates for this currency
        all_dates = sorted(set(long_pl_pct.index) | set(short_pl_pct.index))
        all_trading_days.update(all_dates)

        # Accumulate totals
        all_long_pct += long_pl_pct.sum()
        all_short_pct += short_pl_pct.sum()

        # Get currency colors
        base_color = currency_colors.get(currency, currency_colors.get(AVAILABLE_CURRENCIES[0], '#1f77b4'))
        
        # Create slightly different colors for long/short
        long_color = base_color
        # Make short color slightly darker by converting hex to rgb and darkening
        short_color = base_color
        if base_color.startswith('#') and len(base_color) == 7:
            # Convert hex to RGB, darken, and convert back
            r = int(base_color[1:3], 16)
            g = int(base_color[3:5], 16)
            b = int(base_color[5:7], 16)
            # Darken by 20%
            r = max(0, int(r * 0.8))
            g = max(0, int(g * 0.8))
            b = max(0, int(b * 0.8))
            short_color = f'#{r:02x}{g:02x}{b:02x}'

        # Get currency symbol for display
        currency_symbol = CURRENCY_SYMBOLS.get(currency, currency)
        base_currency_symbol = CURRENCY_SYMBOLS.get(base_currency, base_currency)

        # Prepare hover text for long and short positions
        long_hover_text = []
        short_hover_text = []
        
        for date in all_dates:
            long_pl_val = long_pl.get(date, 0)
            short_pl_val = short_pl.get(date, 0)
            long_pl_original_val = long_pl_original.get(date, 0)
            short_pl_original_val = short_pl_original.get(date, 0)
            long_pct = long_pl_pct.get(date, 0)
            short_pct = short_pl_pct.get(date, 0)
            
            long_hover_text.append(
                f'<b>Date</b>: {date}<br>'
                f'<b>Long P/L %</b>: {long_pct:.2f}%<br>'
                f'<b>Long P/L Amount</b>: {base_currency_symbol}{long_pl_val:.2f} ({base_currency})<br>'
                f'<b>Original Long P/L</b>: {currency_symbol}{long_pl_original_val:.2f} ({currency})'
            )
            
            short_hover_text.append(
                f'<b>Date</b>: {date}<br>'
                f'<b>Short P/L %</b>: {short_pct:.2f}%<br>'
                f'<b>Short P/L Amount</b>: {base_currency_symbol}{short_pl_val:.2f} ({base_currency})<br>'
                f'<b>Original Short P/L</b>: {currency_symbol}{short_pl_original_val:.2f} ({currency})'
            )

        # Add long position bars with hover text
        fig.add_trace(go.Bar(
            x=all_dates,
            y=[long_pl_pct.get(date, 0) for date in all_dates],
            name=f'Long P/L - {currency}',
            marker_color=long_color,
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
            name=f'Short P/L - {currency}',
            marker_color=short_color,
            text=[f"{short_pl_pct.get(date, 0):.1f}%" for date in all_dates],
            textposition='auto',
            cliponaxis=False,
            hovertext=short_hover_text,
            hoverinfo='text'
        ))

    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='LightGray')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='LightGray')

    # Calculate final totals
    total_pl_pct = all_long_pct + all_short_pct
    avg_daily_pct = total_pl_pct / len(all_trading_days) if all_trading_days else 0
    trading_days = len(all_trading_days)

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
            text=(
                "Daily P/L Calculation:<br><br>"
                "- Long positions: Sum of profits/losses from buy trades<br>"
                "- Short positions: Sum of profits/losses from sell trades<br>"
                "- Percentages calculated against daily starting balance<br>"
                "- All amounts converted to base currency for comparison"
            ),
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
            text=(f'Total Long: {all_long_pct:.1f}% <br>'
                  f'Total Short: {all_short_pct:.1f}% <br>'
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