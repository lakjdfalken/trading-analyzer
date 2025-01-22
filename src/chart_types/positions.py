from .base import format_currency, setup_base_figure, apply_common_styling
from settings import COLORS

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

# def create_position_distribution(df):
#     fig, ax = setup_base_figure('square')
#     position_data = []
#     labels = []
#     colors = []
    
#     for currency in df['Currency'].unique():
#         currency_df = df[df['Currency'] == currency]
#         long_pos = currency_df[currency_df['Amount'] > 0]['Amount'].sum()
#         short_pos = abs(currency_df[currency_df['Amount'] < 0]['Amount'].sum())
        
#         if long_pos > 0:
#             position_data.append(long_pos)
#             labels.append(f'Long ({currency})')
#             colors.append(COLORS['profit'])
#         if short_pos > 0:
#             position_data.append(short_pos)
#             labels.append(f'Short ({currency})')
#             colors.append(COLORS['loss'])
    
#     ax.pie(position_data, labels=labels, autopct='%1.1f%%', colors=colors)
#     apply_common_styling(ax, 'Long vs Short Positions')
#     return fig