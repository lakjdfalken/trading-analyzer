from .base import format_currency, setup_base_figure, apply_common_styling
from settings import COLORS

def create_distribution_days(df):
    fig, ax = setup_base_figure('square')
    trading_mask = ~df['Action'].str.startswith('Fund ')
    trading_only_df = df[trading_mask].copy()
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

def create_daily_trade_count(df):
    fig, ax = setup_base_figure('wide')
    trade_df = df[df['Action'].str.contains('Trade', case=False)].copy()
    daily_counts = trade_df.groupby(trade_df['Transaction Date'].dt.date).size()
    avg_trades = daily_counts.mean()
    
    bars = ax.bar(range(len(daily_counts)), daily_counts, 
                 color=COLORS['trading'][0], alpha=0.6,
                 label='Daily Trades')
    
    ax.axhline(y=avg_trades, color=COLORS['trading'][1], 
               linestyle='--', label=f'Average ({avg_trades:.1f} trades/day)')
    
    ax.set_xticks(range(len(daily_counts)))
    ax.set_xticklabels([d.strftime('%Y-%m-%d') for d in daily_counts.index],
                       rotation=45, ha='right')
    
    apply_common_styling(ax, 'Daily Trading Volume',
                        xlabel='Date',
                        ylabel='Number of Trades')
    ax.legend()
    return fig


# def create_distribution_days(df):
#     fig, ax = setup_base_figure('square')
    
#     # Ensure Transaction Date is datetime
#     df['Transaction Date'] = pd.to_datetime(df['Transaction Date'])
    
#     # Exclude all Fund entries
#     trading_mask = ~df['Action'].str.startswith('Fund ')
#     trading_only_df = df[trading_mask].copy()
    
#     # Calculate daily P/L from pure trading activity
#     daily_pl = trading_only_df.groupby(trading_only_df['Transaction Date'].dt.date)['P/L'].sum()
    
#     data = [
#         len(daily_pl[daily_pl > 0]),
#         len(daily_pl[daily_pl < 0]),
#         len(daily_pl[daily_pl == 0])
#     ]
    
#     ax.pie(data, 
#            labels=['Winning Days', 'Losing Days', 'Breakeven Days'],
#            colors=[COLORS['profit'], COLORS['loss'], COLORS['neutral']],
#            autopct='%1.1f%%')
    
#     apply_common_styling(ax, 'Trading Day Performance Distribution')
#     return fig

# def create_daily_trade_count(df):
#     fig, ax = setup_base_figure('wide')
    
#     # Filter out non-trade entries and group by date
#     trade_df = df[df['Action'].str.contains('Trade', case=False)].copy()
#     trade_df['Transaction Date'] = pd.to_datetime(trade_df['Transaction Date'])
#     daily_counts = trade_df.groupby(trade_df['Transaction Date'].dt.date).size()
    
#     # Calculate average trades per day
#     avg_trades = daily_counts.mean()
    
#     # Create bars
#     bars = ax.bar(range(len(daily_counts)), daily_counts, 
#                  color=COLORS['trading'][0], alpha=0.6,
#                  label='Daily Trades')
    
#     # Add average line
#     ax.axhline(y=avg_trades, color=COLORS['trading'][1], 
#                linestyle='--', label=f'Average ({avg_trades:.1f} trades/day)')
    
#     # Set x-axis labels with dates
#     ax.set_xticks(range(len(daily_counts)))
#     ax.set_xticklabels([d.strftime('%Y-%m-%d') for d in daily_counts.index],
#                        rotation=45, ha='right')
    
#     # Add value labels on bars
#     for idx, v in enumerate(daily_counts):
#         ax.text(idx, v, str(v), ha='center', va='bottom')
    
#     apply_common_styling(ax, 'Daily Trading Volume',
#                         xlabel='Date',
#                         ylabel='Number of Trades')
    
#     ax.legend()
#     fig.tight_layout()
#     return fig