import matplotlib.pyplot as plt
import seaborn as sns
from .base import format_currency, setup_base_figure, apply_common_styling
from settings import (
    COLORS,
)

def create_balance_history(df):
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # Create clean copy and filter out Fund entries
    trading_df = df[~df['Action'].str.startswith('Fund')].copy()
    
    # Calculate total P/L for each currency
    total_pl = trading_df.groupby('Currency')['P/L'].sum()
    
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
    
    # Add total P/L text in top left corner
    pl_text = "Total P/L:\n" + "\n".join(
        [f"{curr}: {format_currency(pl, curr)}" for curr, pl in total_pl.items()]
    )
    ax.text(0.02, 0.95,
            pl_text,
            transform=ax.transAxes,
            color=COLORS['trading'][0],
            fontweight='bold',
            bbox=dict(facecolor='white', alpha=0.8, edgecolor='none'))
    
    # Style the plot
    ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    ax.set_title('Trading Balance History')
    ax.yaxis.set_major_formatter(plt.FuncFormatter(
        lambda x, p: format_currency(x, df['Currency'].iloc[0])))
    ax.grid(True, alpha=0.3)
    ax.tick_params(axis='x', rotation=45)
    
    fig.tight_layout()
    return fig
