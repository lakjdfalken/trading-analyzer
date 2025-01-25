from .base import format_currency, setup_base_figure, apply_common_styling
from settings import COLORS

def create_position_distribution(df):
    fig, ax = setup_base_figure('square')
    position_data = []
    labels = []
    colors = []
    pl_text = []
    
    # Filter out Fund transactions
    trading_df = df[~df['Action'].str.startswith('Fund')]
    
    for currency in trading_df['Currency'].unique():
        currency_df = trading_df[trading_df['Currency'] == currency]
        
        # Position calculations
        long_pos = currency_df[currency_df['Amount'] > 0]['Amount'].sum()
        short_pos = abs(currency_df[currency_df['Amount'] < 0]['Amount'].sum())
        
        # P/L calculations
        long_pl = currency_df[currency_df['Amount'] > 0]['P/L'].sum()
        short_pl = currency_df[currency_df['Amount'] < 0]['P/L'].sum()
        
        if long_pos > 0:
            position_data.append(long_pos)
            labels.append(f'Long ({currency})\nP/L: {format_currency(long_pl, currency)}')
            colors.append(COLORS['profit'])
            pl_text.append(f'Long P/L: {format_currency(long_pl, currency)}')
            
        if short_pos > 0:
            position_data.append(short_pos)
            labels.append(f'Short ({currency})\nP/L: {format_currency(short_pl, currency)}')
            colors.append(COLORS['loss'])
            pl_text.append(f'Short P/L: {format_currency(short_pl, currency)}')
    
    # Create pie chart
    wedges, texts, autotexts = ax.pie(position_data, labels=labels, 
                                     autopct='%1.1f%%', colors=colors)
    
    # Add combined P/L text box
    total_pl = trading_df['P/L'].sum()
    pl_summary = f'Total P/L: {format_currency(total_pl, trading_df["Currency"].iloc[0])}'
    ax.text(1.2, -1.1, pl_summary, 
            bbox=dict(facecolor='white', edgecolor='gray', alpha=0.8),
            ha='center')
    
    apply_common_styling(ax, 'Long vs Short Positions')
    return fig
