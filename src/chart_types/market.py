import numpy as np
from .base import prepare_dataframe, format_currency, setup_base_figure, apply_common_styling
from settings import COLORS

def get_market_data(df):
    """Returns dataframe filtered for market transactions"""
    df_copy = prepare_dataframe(df)
    return df_copy[~df_copy['Description'].str.contains('Online Transfer Cash', case=False, na=False)]

def create_market_actions(df):
    df_copy = prepare_dataframe(df)
    
    # Define color mapping with consistent colors from settings
    action_colors = {
        'Trade Receivable': COLORS['profit'],
        'Trade Payable': COLORS['loss'],
        'Fund Receivable': COLORS['trading'][0],
        'Fund Payable': COLORS['trading'][1],
        'Funding charge': COLORS['trading'][2]
    }
    
    # Group and prepare data
    market_actions = df_copy.groupby(['Description', 'Action']).size().unstack(fill_value=0)
    
    fig, ax = setup_base_figure('wide')
    
    # Create stacked bars with better spacing
    market_actions.plot(kind='bar', stacked=True, ax=ax, 
                       width=0.8,
                       color=[action_colors.get(col, COLORS['neutral']) 
                             for col in market_actions.columns])
    
    # Add value labels on bars
    for c in market_actions.columns:
        bottoms = np.zeros(len(market_actions))
        for other_c in market_actions.columns:
            if other_c == c:
                break
            bottoms += market_actions[other_c]
        
        for i, (value, bottom) in enumerate(zip(market_actions[c], bottoms)):
            if value > 0:
                ax.text(i, bottom + value/2, int(value),
                       ha='center', va='center')
    
    apply_common_styling(ax, 'Trading Actions by Market',
                        xlabel='Markets',
                        ylabel='Number of Actions')
    
    ax.legend(title='Action Types', 
             bbox_to_anchor=(1.05, 1),
             loc='upper left',
             borderaxespad=0)
    
    fig.tight_layout()
    return fig

def create_market_pl(df):
    market_df = get_market_data(df)
    market_pl = market_df.groupby(['Description', 'Currency'])['P/L'].sum().reset_index()
    market_pl = market_pl.sort_values('P/L')
    
    # Calculate total P/L per currency
    total_pl = market_df.groupby('Currency')['P/L'].sum()
    
    fig, ax = setup_base_figure('wide')
    
    # Create bars with colors based on profit/loss
    colors = [COLORS['loss'] if x < 0 else COLORS['profit'] for x in market_pl['P/L']]
    bars = ax.bar(range(len(market_pl)), market_pl['P/L'], color=colors)
    
    # Add market names and P/L values
    ax.set_xticks(range(len(market_pl)))
    ax.set_xticklabels([desc for desc in market_pl['Description']],
                       rotation=45, ha='right')
    
    for i, (v, curr) in enumerate(zip(market_pl['P/L'], market_pl['Currency'])):
        ax.text(i, v, format_currency(v, curr),
                ha='center', 
                va='bottom' if v >= 0 else 'top')
    
    # Add total P/L summary
    totals_text = "Total P/L:\n" + "\n".join(
        [f"{curr}: {format_currency(pl, curr)}" for curr, pl in total_pl.items()]
    )
    ax.text(0.02, 0.95, totals_text,
            transform=ax.transAxes,
            ha='left', va='top',
            bbox=dict(facecolor='white', alpha=0.8, edgecolor='none'))
    
    apply_common_styling(ax, 'Profit/Loss by Market',
                        xlabel='Markets',
                        ylabel='Total P/L')
    
    fig.tight_layout()
    return fig
