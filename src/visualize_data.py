import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import logging
from settings import (
    FIGURE_SIZES,
    COLORS,
    MARKET_SPREADS,
    CURRENCY_SYMBOLS,
    VALID_GRAPH_TYPES
)
logging.getLogger('matplotlib').setLevel(logging.WARNING)
logging.getLogger('matplotlib.pyplot').setLevel(logging.WARNING)
logging.getLogger('matplotlib.font_manager').setLevel(logging.WARNING)
logging.getLogger('PIL.PngImagePlugin').setLevel(logging.WARNING)

# Utility functions
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

# Main visualization function
def create_visualization_figure(df, graph_type):
    if df.empty:
        raise ValueError("DataFrame is empty")
    
    if graph_type not in VALID_GRAPH_TYPES:
        raise ValueError(f"Invalid graph type: {graph_type}")
    
    if graph_type == 'Balance History':
        return create_balance_history(df)
    elif graph_type == 'Distribution Days':
        return create_distribution_days(df)
    elif graph_type == 'Funding':
        return create_funding_distribution(df)
    elif graph_type == 'Funding Charges':
        return create_funding_charges(df)
    elif graph_type == 'Long vs Short Positions':
        return create_position_distribution(df)
    elif graph_type == 'Market Actions':
        return create_market_actions(df)
    elif graph_type == 'Market P/L':
        return create_market_pl(df)
    elif graph_type == 'Daily P/L':
        return create_daily_pl(df)

# Individual visualization functions
def create_balance_history(df):
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # Create clean copy and filter out Fund entries
    trading_df = df[~df['Action'].str.startswith('Fund')].copy()
    
    # Calculate single percentage change for the entire period
    first_value = trading_df['P/L'].iloc[0]
    latest_value = trading_df['P/L'].sum()
    total_return = ((latest_value - first_value) / abs(first_value)) * 100
    
    # Plot balance lines
    for currency in trading_df['Currency'].unique():
        currency_df = trading_df[trading_df['Currency'] == currency]
        if not currency_df.empty:
            # Sort and calculate cumulative balance
            currency_df = currency_df.sort_values('Transaction Date')
            currency_df['Trading_Balance'] = currency_df['P/L'].cumsum()
            
            # Plot trading balance
            sns.lineplot(data=currency_df, x='Transaction Date', y='Trading_Balance', 
                        linewidth=3, ax=ax, 
                        label=f'Trading Balance ({currency})',
                        color=COLORS['trading'][0])
    
    # Add single return text
    ax.text(0.02, 0.98,
           f'Total Return: {total_return:.1f}%',
           transform=ax.transAxes,
           color=COLORS['trading'][0],
           fontweight='bold',
           bbox=dict(facecolor='white', alpha=0.8, edgecolor='none'))
    
    # Style the plot
    ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    ax.set_title('Relative Trading Balance History')
    ax.yaxis.set_major_formatter(plt.FuncFormatter(
        lambda x, p: format_currency(x, df['Currency'].iloc[0])))
    ax.grid(True, alpha=0.3)
    ax.tick_params(axis='x', rotation=45)
    
    fig.tight_layout()
    return fig

def create_distribution_days(df):
    fig, ax = setup_base_figure('square')
    
    # Ensure Transaction Date is datetime
    df['Transaction Date'] = pd.to_datetime(df['Transaction Date'])
    
    # Exclude all Fund entries
    trading_mask = ~df['Action'].str.startswith('Fund ')
    trading_only_df = df[trading_mask].copy()
    
    # Calculate daily P/L from pure trading activity
    daily_pl = trading_only_df.groupby(trading_only_df['Transaction Date'].dt.date)['P/L'].sum()
    
    data = [
        len(daily_pl[daily_pl > 0]),
        len(daily_pl[daily_pl < 0]),
        len(daily_pl[daily_pl == 0])
    ]
    
    ax.pie(data, 
           labels=['Winning Days', 'Losing Days', 'Breakeven Days'],
           colors=[COLORS['profit'], COLORS['loss'], COLORS['neutral']],
           autopct='%1.1f%%')
    
    apply_common_styling(ax, 'Trading Day Performance Distribution')
    return fig


def create_position_distribution(df):
    fig, ax = setup_base_figure('square')
    position_data = []
    labels = []
    colors = []
    
    for currency in df['Currency'].unique():
        currency_df = df[df['Currency'] == currency]
        long_pos = currency_df[currency_df['Amount'] > 0]['Amount'].sum()
        short_pos = abs(currency_df[currency_df['Amount'] < 0]['Amount'].sum())
        
        if long_pos > 0:
            position_data.append(long_pos)
            labels.append(f'Long ({currency})')
            colors.append(COLORS['profit'])
        if short_pos > 0:
            position_data.append(short_pos)
            labels.append(f'Short ({currency})')
            colors.append(COLORS['loss'])
    
    ax.pie(position_data, labels=labels, autopct='%1.1f%%', colors=colors)
    apply_common_styling(ax, 'Long vs Short Positions')
    return fig

def create_market_actions(df):
    fig, ax = setup_base_figure('wide')
    
    # Define color mapping for trade actions
    action_colors = {
        'Trade Receivable': COLORS['profit'],  # Green for receivables
        'Trade Payable': COLORS['loss'],       # Red for payables
        'Fund Receivable': '#3498db',          # Keep other actions with distinct colors
        'Fund Payable': '#9b59b6',
        'Funding charge': '#f1c40f'
    }
    
    market_actions = df.groupby(['Description', 'Action']).size().unstack()
    market_actions.plot(kind='bar', stacked=True, ax=ax, 
                       color=[action_colors.get(col, '#e74c3c') for col in market_actions.columns])
    
    apply_common_styling(ax, 'Trading Actions by Market',
                        xlabel='Markets',
                        ylabel='Number of Trades')
    
    ax.legend(title='Action Types', bbox_to_anchor=(1.05, 1))
    fig.tight_layout()
    return fig

def create_market_pl(df):
    fig, ax = setup_base_figure('wide')
    
    # Filter out Online Transfer Cash entries and create market P/L summary
    market_df = df[~df['Description'].str.contains('Online Transfer Cash', case=False, na=False)]
    market_pl = market_df.groupby(['Description', 'Currency'])['P/L'].sum().reset_index()
    market_pl = market_pl.sort_values('P/L')
    
    # Calculate total P/L per currency
    total_pl = market_df.groupby('Currency')['P/L'].sum()
    
    colors = [COLORS['loss'] if x < 0 else COLORS['profit'] for x in market_pl['P/L']]
    bars = ax.bar(range(len(market_pl)), market_pl['P/L'], color=colors)
    
    # Set x-axis labels
    ax.set_xticks(range(len(market_pl)))
    ax.set_xticklabels([f"{desc}\n({curr})" for desc, curr in 
                        zip(market_pl['Description'], market_pl['Currency'])],
                       rotation=45, ha='right')
    
    # Add value labels on bars
    for i, (v, curr) in enumerate(zip(market_pl['P/L'], market_pl['Currency'])):
        ax.text(i, v, format_currency(v, curr),
                ha='center', va='bottom' if v >= 0 else 'top')
    
    # Add total P/L text in the top right corner
    totals_text = "Total P/L:\n" + "\n".join(
        [f"{curr}: {format_currency(pl, curr)}" for curr, pl in total_pl.items()]
    )
    ax.text(0.95, 0.95, totals_text,
            transform=ax.transAxes,
            ha='right', va='top',
            bbox=dict(facecolor='white', alpha=0.8, edgecolor='none'))
    
    apply_common_styling(ax, 'Profit/Loss by Market',
                        xlabel='Markets',
                        ylabel='Total P/L')
    
    fig.tight_layout()
    return fig

def create_funding_distribution(df):
    fig = plt.Figure(figsize=FIGURE_SIZES['wide'])
    currencies = df['Currency'].unique()
    
    # Create a clean copy of the DataFrame and convert dates
    df = df.copy()
    df['Transaction Date'] = pd.to_datetime(df['Transaction Date'])
    
    # Filter funding data from the prepared DataFrame
    funding_df = df[df['Action'].str.startswith('Fund ')].copy()
    
    for i, currency in enumerate(currencies, 1):
        ax = fig.add_subplot(len(currencies), 1, i)
        currency_funding = funding_df[funding_df['Currency'] == currency]
        
        if not currency_funding.empty:
            # Calculate totals
            total_in = currency_funding[currency_funding['P/L'] > 0]['P/L'].sum()
            total_out = currency_funding[currency_funding['P/L'] < 0]['P/L'].sum()
            net_total = total_in + total_out
            
            # Create bars and color them based on P/L value
            bars = ax.bar(range(len(currency_funding)), 
                         currency_funding['P/L'],
                         color=[COLORS['profit'] if x > 0 else COLORS['loss'] 
                               for x in currency_funding['P/L']])
            
            # Add value labels on bars
            for idx, bar in enumerate(bars):
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height,
                       format_currency(height, currency),
                       ha='center', va='bottom' if height >= 0 else 'top')
            
            # Add totals text box
            totals_text = (f"Total In: {format_currency(total_in, currency)}\n"
                          f"Total Out: {format_currency(total_out, currency)}\n"
                          f"Net Total: {format_currency(net_total, currency)}")
            
            ax.text(0.02, 0.95, totals_text,
                   transform=ax.transAxes,
                   bbox=dict(facecolor='white', alpha=0.8, edgecolor='none'),
                   verticalalignment='top')
            
            # Set x-axis labels with dates
            dates = currency_funding['Transaction Date'].dt.strftime('%Y-%m-%d')
            ax.set_xticks(range(len(currency_funding)))
            ax.set_xticklabels(dates, rotation=45, ha='right')
        
        apply_common_styling(ax, f'Funding Flow Distribution ({currency})')
        
        if not currency_funding.empty:
            ax.legend(['Funding In', 'Funding Out'])
        
        ax.yaxis.set_major_formatter(plt.FuncFormatter(
            lambda x, p: format_currency(x, currency)))
    
    fig.tight_layout()
    return fig

def create_funding_charges(df):
    fig = plt.Figure(figsize=FIGURE_SIZES['wide'])
    currencies = df['Currency'].unique()
    
    # Create a clean copy and prepare data
    df = df.copy()
    df['Transaction Date'] = pd.to_datetime(df['Transaction Date'])
    
    # Filter for funding charges - checking both Description and Action fields
    funding_c_df = df[
        (df['Action'].str.contains('Funding charge', case=False, na=False)) ].copy()
    funding_charges_in = funding_c_df[funding_c_df['P/L'] > 0]  # Receivable funding
    funding_charges_out = funding_c_df[funding_c_df['P/L'] < 0]  # Outgoing funding  

    for i, currency in enumerate(currencies, 1):
        ax = fig.add_subplot(len(currencies), 1, i)
        currency_charges = funding_c_df[funding_c_df['Currency'] == currency]
        
        if not currency_charges.empty:
            # Create bars with consistent coloring for charges
            bars = ax.bar(range(len(currency_charges)), 
                         currency_charges['P/L'],
                         color=[COLORS['profit'] if x > 0 else COLORS['loss'] 
                               for x in currency_charges['P/L']]) 

            # Add value labels on bars
            for idx, bar in enumerate(bars):
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height,
                       format_currency(height, currency),
                       ha='center', va='bottom' if height >= 0 else 'top')
            
            # Set x-axis labels with dates
            dates = currency_charges['Transaction Date'].dt.strftime('%Y-%m-%d')
            ax.set_xticks(range(len(currency_charges)))
            ax.set_xticklabels(dates, rotation=45, ha='right')
        
        apply_common_styling(ax, f'Funding Charges ({currency})')

        # Only add legend if we have data
        if not currency_charges.empty:
            ax.legend(['Funding Charge In', 'Funding Charge Out'])
        
        # Format y-axis with currency
        ax.yaxis.set_major_formatter(plt.FuncFormatter(
            lambda x, p: format_currency(x, currency)))
    
    fig.tight_layout()
    return fig
def create_daily_pl(df):
    print("\n=== Starting Daily P/L Performance Visualization ===")
    
    # Create clean copy and prepare data
    df_copy = df.copy()
    df_copy['Transaction Date'] = pd.to_datetime(df_copy['Transaction Date'])
    
    # Get initial balance from first non-Fund entry
    trading_mask = ~df_copy['Action'].str.startswith('Fund ')
    initial_balance = df_copy[trading_mask]['Balance'].iloc[0]
    print(f"Initial trading balance: {initial_balance}")
    
    # Calculate daily P/L excluding Fund entries
    daily_pl = df_copy[trading_mask].groupby(df_copy['Transaction Date'].dt.date)['P/L'].sum()
    daily_pl_pct = (daily_pl / abs(initial_balance)) * 100
    
    # Create figure
    fig, ax = plt.subplots(figsize=FIGURE_SIZES['wide'])
    
    # Create bars
    bars = ax.bar(range(len(daily_pl_pct)), 
                  daily_pl_pct,
                  color=[COLORS['profit'] if x >= 0 else COLORS['loss'] for x in daily_pl_pct])
    
    # Add value labels on bars
    for idx, v in enumerate(daily_pl_pct):
        ax.text(idx, v, f'{v:.1f}%',
                ha='center', 
                va='bottom' if v >= 0 else 'top')
    
    # Set x-axis labels with dates
    ax.set_xticks(range(len(daily_pl_pct)))
    ax.set_xticklabels([d.strftime('%Y-%m-%d') for d in daily_pl_pct.index],
                        rotation=45, ha='right')
    
    # Add total return text
    total_return = daily_pl_pct.sum()
    ax.text(0.02, 0.95,
            f'Total Return: {total_return:.1f}%',
            transform=ax.transAxes,
            color=COLORS['trading'][0],
            fontweight='bold',
            bbox=dict(facecolor='white', alpha=0.8, edgecolor='none'))
    
    # Add horizontal line at 0%
    ax.axhline(y=0, color='gray', linestyle='--', alpha=0.5)
    
    apply_common_styling(ax, 'Daily P/L Performance',
                        xlabel='Date',
                        ylabel='Daily P/L (%)')
    
    fig.tight_layout()
    print(f"Total return: {total_return:.2f}%")
    print("=== Visualization Complete ===")
    return fig

def get_market_spread(market_name, hour):
    """
    Get the spread for a market at a specific hour
    
    Args:
        market_name (str): Name of the market (e.g. 'USTEC', 'Wall Street')
        hour (int): Hour of the day (0-23)
        
    Returns:
        float: Spread value for the given market and hour
    """
    if market_name not in MARKET_SPREADS:
        return None
        
    market_data = MARKET_SPREADS[market_name]
    
    # Check which time period the hour falls into
    normal_start, normal_end, normal_spread = market_data['normal_hours']
    closing_start, closing_end, closing_spread = market_data['closing_hours']
    off_start, off_end, off_spread = market_data['off_hours']
    
    if normal_start <= hour < normal_end:
        return normal_spread
    elif closing_start <= hour < closing_end:
        return closing_spread
    else:
        return off_spread
