import numpy as np
from .base import format_currency, setup_base_figure, apply_common_styling
from settings import COLORS

def create_market_actions(df):
    fig, ax = setup_base_figure('wide')
    
    # Define color mapping with consistent colors from settings
    action_colors = {
        'Trade Receivable': COLORS['profit'],
        'Trade Payable': COLORS['loss'],
        'Fund Receivable': COLORS['trading'][0],
        'Fund Payable': COLORS['trading'][1],
        'Funding charge': COLORS['trading'][2]
    }
    
    # Group and prepare data
    market_actions = df.groupby(['Description', 'Action']).size().unstack(fill_value=0)
    
    # Create stacked bars with better spacing
    market_actions.plot(kind='bar', stacked=True, ax=ax, 
                       width=0.8,  # Adjust bar width
                       color=[action_colors.get(col, COLORS['neutral']) for col in market_actions.columns])
    
    # Enhance x-axis readability
    ax.set_xticklabels(market_actions.index, rotation=45, ha='right')
    
    # Add value labels on bars
    for c in market_actions.columns:
        # Get the bottom position for each segment
        bottoms = np.zeros(len(market_actions))
        for other_c in market_actions.columns:
            if other_c == c:
                break
            bottoms += market_actions[other_c]
        
        # Add labels for non-zero values
        for i, (value, bottom) in enumerate(zip(market_actions[c], bottoms)):
            if value > 0:
                ax.text(i, bottom + value/2, int(value),
                       ha='center', va='center')
    
    apply_common_styling(ax, 'Trading Actions by Market',
                        xlabel='Markets',
                        ylabel='Number of Actions')
    
    # Improve legend positioning and style
    ax.legend(title='Action Types', 
             bbox_to_anchor=(1.05, 1),
             loc='upper left',
             borderaxespad=0)
    
    fig.tight_layout()
    return fig

def create_market_pl(df):
    fig, ax = setup_base_figure('wide')
    
    # Prepare market data
    market_df = df[~df['Description'].str.contains('Online Transfer Cash', case=False, na=False)]
    market_pl = market_df.groupby(['Description', 'Currency'])['P/L'].sum().reset_index()
    market_pl = market_pl.sort_values('P/L')  # Sort by P/L for better visualization
    
    # Calculate total P/L per currency
    total_pl = market_df.groupby('Currency')['P/L'].sum()
    
    # Create bars with colors based on profit/loss
    colors = [COLORS['loss'] if x < 0 else COLORS['profit'] for x in market_pl['P/L']]
    bars = ax.bar(range(len(market_pl)), market_pl['P/L'], color=colors)
    
    # Add market names on x-axis
    ax.set_xticks(range(len(market_pl)))
    ax.set_xticklabels([desc for desc in market_pl['Description']],
                       rotation=45, ha='right')
    
    # Add P/L values on top of bars
    for i, (v, curr) in enumerate(zip(market_pl['P/L'], market_pl['Currency'])):
        ax.text(i, v, format_currency(v, curr),
                ha='center', 
                va='bottom' if v >= 0 else 'top')
    
    # Add total P/L text box in top right corner
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
