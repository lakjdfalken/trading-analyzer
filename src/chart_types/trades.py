from .base import format_currency, setup_base_figure, apply_common_styling
from settings import COLORS
import pandas as pd

def create_distribution_days(df):
    # Convert Transaction Date to datetime explicitly
    df['Transaction Date'] = pd.to_datetime(df['Transaction Date'])
    
    # Now we can safely use .dt accessor
    trading_days = df['Transaction Date'].dt.date.unique()
    
    # Rest of your distribution days calculation
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
    # Create clean copy and ensure datetime type
    df_copy = df.copy()
    df_copy['Transaction Date'] = pd.to_datetime(df_copy['Transaction Date'])
    
    # Filter for trade transactions
    trade_df = df_copy[df_copy['Action'].str.contains('Trade', case=False)]
    
    # Group by date and count trades
    daily_trades = trade_df.groupby(trade_df['Transaction Date'].dt.date).size()
    
    fig, ax = setup_base_figure('wide')
    avg_trades = daily_trades.mean()
    
    bars = ax.bar(range(len(daily_trades)), daily_trades, 
                 color=COLORS['trading'][0], alpha=0.6,
                 label='Daily Trades')
    
    ax.axhline(y=avg_trades, color=COLORS['trading'][1], 
               linestyle='--', label=f'Average ({avg_trades:.1f} trades/day)')
    
    ax.set_xticks(range(len(daily_trades)))
    ax.set_xticklabels([d.strftime('%Y-%m-%d') for d in daily_trades.index],
                       rotation=45, ha='right')
    
    apply_common_styling(ax, 'Daily Trading Volume',
                        xlabel='Date',
                        ylabel='Number of Trades')
    ax.legend()
    return fig