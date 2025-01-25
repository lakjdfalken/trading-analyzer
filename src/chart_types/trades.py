from .base import prepare_dataframe, format_currency, setup_base_figure, apply_common_styling
from settings import COLORS
import pandas as pd

def get_trade_distribution(df):
    """Returns trading day performance metrics"""
    trading_df = prepare_dataframe(df)
    trading_df = trading_df[~trading_df['Action'].str.startswith('Fund')]
    daily_pl = trading_df.groupby(trading_df['Transaction Date'].dt.date)['P/L'].sum()
    
    return {
        'winning_days': len(daily_pl[daily_pl > 0]),
        'losing_days': len(daily_pl[daily_pl < 0]),
        'breakeven_days': len(daily_pl[daily_pl == 0])
    }

def create_distribution_days(df):
    distribution = get_trade_distribution(df)
    fig, ax = setup_base_figure('square')
    
    data = [
        distribution['winning_days'],
        distribution['losing_days'],
        distribution['breakeven_days']
    ]
    
    ax.pie(data, 
           labels=['Winning Days', 'Losing Days', 'Breakeven Days'],
           colors=[COLORS['profit'], COLORS['loss'], COLORS['neutral']],
           autopct='%1.1f%%')
    
    apply_common_styling(ax, 'Trading Day Performance Distribution')
    return fig

def create_daily_trade_count(df):
    df_copy = prepare_dataframe(df)
    trade_df = df_copy[df_copy['Action'].str.contains('Trade', case=False)]
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