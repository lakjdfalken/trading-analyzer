from .base import prepare_dataframe, format_currency, setup_base_figure, apply_common_styling
from settings import COLORS

def get_position_data(df, currency):
    """Returns position data for a specific currency"""
    df_copy = prepare_dataframe(df)
    trading_df = df_copy[~df_copy['Action'].str.startswith('Fund')]
    currency_df = trading_df[trading_df['Currency'] == currency]
    
    long_pos = currency_df[currency_df['Amount'] > 0]['Amount'].sum()
    short_pos = abs(currency_df[currency_df['Amount'] < 0]['Amount'].sum())
    long_pl = currency_df[currency_df['Amount'] > 0]['P/L'].sum()
    short_pl = currency_df[currency_df['Amount'] < 0]['P/L'].sum()
    
    return {
        'long_pos': long_pos,
        'short_pos': short_pos,
        'long_pl': long_pl,
        'short_pl': short_pl
    }

def create_position_distribution(df):
    fig, ax = setup_base_figure('square')
    position_data = []
    labels = []
    colors = []
    pl_text = []
    
    # Filter out Fund transactions and get trading data
    trading_df = prepare_dataframe(df)
    trading_df = trading_df[~trading_df['Action'].str.startswith('Fund')]
    
    for currency in trading_df['Currency'].unique():
        pos_data = get_position_data(df, currency)
        
        if pos_data['long_pos'] > 0:
            position_data.append(pos_data['long_pos'])
            labels.append(f'Long ({currency})\nP/L: {format_currency(pos_data["long_pl"], currency)}')
            colors.append(COLORS['profit'])
            pl_text.append(f'Long P/L: {format_currency(pos_data["long_pl"], currency)}')
            
        if pos_data['short_pos'] > 0:
            position_data.append(pos_data['short_pos'])
            labels.append(f'Short ({currency})\nP/L: {format_currency(pos_data["short_pl"], currency)}')
            colors.append(COLORS['loss'])
            pl_text.append(f'Short P/L: {format_currency(pos_data["short_pl"], currency)}')
    
    # Create pie chart with position distribution
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