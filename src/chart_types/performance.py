from .base import format_currency, setup_base_figure, apply_common_styling
import matplotlib.pyplot as plt
import pandas as pd
from settings import FIGURE_SIZES, COLORS

def create_daily_pl_vs_trades(df):
    # Create clean copy and ensure datetime type
    df_copy = df.copy()
    df_copy['Transaction Date'] = pd.to_datetime(df_copy['Transaction Date'])
    
    trading_mask = ~df_copy['Action'].str.startswith('Fund ')
    initial_balance = df_copy[trading_mask]['Balance'].iloc[0]
    
    # Now we can safely use .dt accessor for grouping
    daily_pl = df_copy[trading_mask].groupby(df_copy['Transaction Date'].dt.date)['P/L'].sum()
    daily_pl_pct = (daily_pl / abs(initial_balance)) * 100
    
    trade_df = df_copy[df_copy['Action'].str.contains('Trade', case=False)]
    daily_trades = trade_df.groupby(trade_df['Transaction Date'].dt.date).size()
    
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=FIGURE_SIZES['wide'], 
                                  gridspec_kw={'height_ratios': [3, 1]})

    # Get dates for x-axis
    dates = [d.strftime('%m-%d') for d in daily_pl.index]  # Short date format MM-DD
    
    correlation = daily_pl_pct.corr(daily_trades)
    
    # Create bars with value labels
    bars = ax1.bar(range(len(daily_pl_pct)), daily_pl_pct,
            color=[COLORS['profit'] if x >= 0 else COLORS['loss'] for x in daily_pl_pct])
            
    # Add value labels on P/L bars
    for idx, bar in enumerate(bars):
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.1f}%',
                ha='center',
                va='bottom' if height >= 0 else 'top')
    
    # Create trade count line with value labels
    line = ax2.plot(range(len(daily_trades)), daily_trades, 
                    color=COLORS['trading'][1], 
                    marker='o')[0]
    
    # Add value labels for trade counts
    for x, y in enumerate(daily_trades):
        ax2.text(x, y, str(int(y)),
                ha='center',
                va='bottom')
    
    # Set x-axis labels with dates
    ax1.set_xticks(range(len(dates)))
    ax1.set_xticklabels(dates, rotation=45, ha='right')
    ax2.set_xticks(range(len(dates)))
    ax2.set_xticklabels(dates, rotation=45, ha='right')
    
    apply_common_styling(ax1, 'Daily P/L vs Trade Count',
                        ylabel='Daily P/L (%)')
    apply_common_styling(ax2, '', xlabel='Date',
                        ylabel='Trade Count')
    
    ax1.text(0.95, 0.95, f'Correlation: {correlation:.2f}',
             transform=ax1.transAxes,
             horizontalalignment='right')
             
    fig.tight_layout()  # Adjust layout to prevent label overlap
    return fig

def create_daily_pl(df):
    # Create clean copy and prepare data
    df_copy = df.copy()
    df_copy['Transaction Date'] = pd.to_datetime(df_copy['Transaction Date'])
    
    # Filter trading transactions and get initial balance
    trading_mask = ~df_copy['Action'].str.startswith('Fund')  # Changed from Fund ' to Fund
    trading_df = df_copy[trading_mask]
    initial_balance = trading_df['Balance'].iloc[0]
    
    # Calculate daily P/L for long and short positions separately
    # Use .gt(0) and .lt(0) instead of direct comparison
    long_pl = trading_df[trading_df['Amount'].gt(0)].groupby(
        trading_df['Transaction Date'].dt.date)['P/L'].sum()
    short_pl = trading_df[trading_df['Amount'].lt(0)].groupby(
        trading_df['Transaction Date'].dt.date)['P/L'].sum()
    
    # Convert to percentage of initial balance
    long_pl_pct = (long_pl / abs(initial_balance)) * 100
    short_pl_pct = (short_pl / abs(initial_balance)) * 100
    
    # Create figure
    fig, ax = plt.subplots(figsize=FIGURE_SIZES['wide'])
    
    # Get all unique dates
    all_dates = sorted(set(long_pl_pct.index) | set(short_pl_pct.index))
    x = range(len(all_dates))
    
    # Create stacked bars
    long_values = [long_pl_pct.get(date, 0) for date in all_dates]
    short_values = [short_pl_pct.get(date, 0) for date in all_dates]
    
    # Plot bars
    long_bars = ax.bar(x, long_values, color=COLORS['profit'], label='Long P/L')
    short_bars = ax.bar(x, short_values, color=COLORS['loss'], label='Short P/L')
    
    # Add value labels on bars
    for idx, (long_v, short_v) in enumerate(zip(long_values, short_values)):
        if long_v != 0:
            ax.text(idx, long_v, f'{long_v:.1f}%',
                   ha='center', va='bottom' if long_v >= 0 else 'top')
        if short_v != 0:
            ax.text(idx, short_v, f'{short_v:.1f}%',
                   ha='center', va='bottom' if short_v >= 0 else 'top')
    
    # Set x-axis labels with dates
    ax.set_xticks(x)
    ax.set_xticklabels([d.strftime('%Y-%m-%d') for d in all_dates],
                       rotation=45, ha='right')
    
    # Add total return text for both long and short
    total_long = sum(long_values)
    total_short = sum(short_values)
    total_return = total_long + total_short
    
    summary_text = (f'Total Return: {total_return:.1f}%\n'
                   f'Long: {total_long:.1f}%\n'
                   f'Short: {total_short:.1f}%')
    
    ax.text(0.02, 0.95, summary_text,
            transform=ax.transAxes,
            color=COLORS['trading'][0],
            fontweight='bold',
            bbox=dict(facecolor='white', alpha=0.8, edgecolor='none'))
    
    # Add horizontal line at 0%
    ax.axhline(y=0, color='gray', linestyle='--', alpha=0.5)
    
    # Add legend
    ax.legend()
    
    apply_common_styling(ax, 'Daily P/L Performance - Long vs Short',
                        xlabel='Date',
                        ylabel='Daily P/L (%)')
    
    fig.tight_layout()
    return fig

#def create_daily_pl_vs_trades(df):
# fig, ax1 = plt.subplots(figsize=FIGURE_SIZES['wide'])
    
#     # Create second y-axis for trade count
#     ax2 = ax1.twinx()
    
#     # Prepare P/L data
#     df_copy = df.copy()
#     df_copy['Transaction Date'] = pd.to_datetime(df_copy['Transaction Date'])
#     trading_mask = ~df_copy['Action'].str.startswith('Fund ')
#     initial_balance = df_copy[trading_mask]['Balance'].iloc[0]
    
#     # Calculate daily P/L percentage
#     daily_pl = df_copy[trading_mask].groupby(df_copy['Transaction Date'].dt.date)['P/L'].sum()
#     daily_pl_pct = (daily_pl / abs(initial_balance)) * 100
    
#     # Prepare trade count data
#     trade_df = df[df['Action'].str.contains('Trade', case=False)]
#     daily_trades = trade_df.groupby(trade_df['Transaction Date'].dt.date).size()
    
#     # Align dates for both metrics
#     all_dates = sorted(set(daily_pl_pct.index) | set(daily_trades.index))
    
#     # Plot P/L bars
#     bars = ax1.bar(range(len(all_dates)), 
#                    [daily_pl_pct.get(date, 0) for date in all_dates],
#                    alpha=0.6,
#                    color=[COLORS['profit'] if x >= 0 else COLORS['loss'] 
#                          for x in [daily_pl_pct.get(date, 0) for date in all_dates]],
#                    label='Daily P/L %')
    
#     # Plot trade count line
#     line = ax2.plot(range(len(all_dates)), 
#                     [daily_trades.get(date, 0) for date in all_dates],
#                     color=COLORS['trading'][1],
#                     linewidth=2,
#                     marker='o',
#                     label='Number of Trades')
    
#     # Add value labels
#     for idx, v in enumerate(daily_pl_pct):
#         ax1.text(idx, v, f'{v:.1f}%',
#                 ha='center', 
#                 va='bottom' if v >= 0 else 'top')
    
#     # Styling
#     ax1.set_xlabel('Date')
#     ax1.set_ylabel('Daily P/L (%)')
#     ax2.set_ylabel('Number of Trades')
    
#     # Set x-axis labels
#     ax1.set_xticks(range(len(all_dates)))
#     ax1.set_xticklabels([d.strftime('%Y-%m-%d') for d in all_dates],
#                         rotation=45, ha='right')
    
#     # Add horizontal line at 0% for P/L
#     ax1.axhline(y=0, color='gray', linestyle='--', alpha=0.5)
    
#     # Add legends for both axes
#     lines1, labels1 = ax1.get_legend_handles_labels()
#     lines2, labels2 = ax2.get_legend_handles_labels()
#     ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left')
    
#     # Calculate and display correlation
#     correlation = pd.Series([daily_pl_pct.get(date, 0) for date in all_dates]).corr(
#         pd.Series([daily_trades.get(date, 0) for date in all_dates]))
    
#     ax1.text(0.95, 0.95,
#              f'Correlation: {correlation:.2f}',
#              transform=ax1.transAxes,
#              horizontalalignment='right',
#              verticalalignment='top',
#              bbox=dict(facecolor='white', alpha=0.8, edgecolor='none'))
    
#     fig.tight_layout()
#     return fig