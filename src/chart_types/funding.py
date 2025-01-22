import matplotlib.pyplot as plt
import pandas as pd
from .base import format_currency, setup_base_figure, apply_common_styling
from settings import FIGURE_SIZES, COLORS

def create_funding_distribution(df):
    fig = plt.Figure(figsize=FIGURE_SIZES['wide'])
    currencies = df['Currency'].unique()
    
    # Filter funding data
    funding_df = df[df['Action'].str.startswith('Fund ')].copy()
    
    for i, currency in enumerate(currencies, 1):
        ax = fig.add_subplot(len(currencies), 1, i)
        currency_funding = funding_df[funding_df['Currency'] == currency]
        
        if not currency_funding.empty:
            # Calculate totals
            total_in = currency_funding[currency_funding['P/L'] > 0]['P/L'].sum()
            total_out = currency_funding[currency_funding['P/L'] < 0]['P/L'].sum()
            net_total = total_in + total_out
            
            # Create bars with explicit labels for legend
            bars = ax.bar(range(len(currency_funding)), 
                         currency_funding['P/L'],
                         color=[COLORS['profit'] if x > 0 else COLORS['loss'] 
                               for x in currency_funding['P/L']],
                         label=['Funding In' if x > 0 else 'Funding Out' 
                               for x in currency_funding['P/L']])
            
            # Add value labels on bars
            for idx, bar in enumerate(bars):
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height,
                       format_currency(height, currency),
                       ha='center', va='bottom' if height >= 0 else 'top')
            
            # Add totals text box
            totals_text = (f"Total In: {format_currency(total_in, currency)}\n"
                          f"Total Out: {format_currency(total_out, currency)}\n"
                          f"Net Total: {format_currency(net_total, currency)}")
            
            ax.text(0.02, 0.95, totals_text,
                   transform=ax.transAxes,
                   bbox=dict(facecolor='white', alpha=0.8, edgecolor='none'),
                   verticalalignment='top')
            
            # Set x-axis labels with dates
            dates = currency_funding['Transaction Date'].dt.strftime('%Y-%m-%d')
            ax.set_xticks(range(len(currency_funding)))
            ax.set_xticklabels(dates, rotation=45, ha='right')
            
            # Add proper legend with unique entries
            handles = [plt.Rectangle((0,0),1,1, color=COLORS['profit']),
                      plt.Rectangle((0,0),1,1, color=COLORS['loss'])]
            labels = ['Funding In', 'Funding Out']
            ax.legend(handles, labels, loc='upper right')
        
        apply_common_styling(ax, f'Funding Flow Distribution ({currency})')
    
    fig.tight_layout()
    return fig

def create_funding_charges(df):
    # Funding charges implementation
    fig = plt.Figure(figsize=FIGURE_SIZES['wide'])
    currencies = df['Currency'].unique()
    
    # Create a clean copy and prepare data
    df = df.copy()
    df['Transaction Date'] = pd.to_datetime(df['Transaction Date'])
    
    # Filter for funding charges - checking both Description and Action fields
    funding_c_df = df[
        (df['Action'].str.contains('Funding charge', case=False, na=False)) ].copy()
    funding_charges_in = funding_c_df[funding_c_df['P/L'] > 0]  # Receivable funding
    funding_charges_out = funding_c_df[funding_c_df['P/L'] < 0]  # Outgoing funding  

    for i, currency in enumerate(currencies, 1):
        ax = fig.add_subplot(len(currencies), 1, i)
        currency_charges = funding_c_df[funding_c_df['Currency'] == currency]
        
        if not currency_charges.empty:
            # Create bars with consistent coloring for charges
            bars = ax.bar(range(len(currency_charges)), 
                         currency_charges['P/L'],
                         color=[COLORS['profit'] if x > 0 else COLORS['loss'] 
                               for x in currency_charges['P/L']]) 

            # Add value labels on bars
            for idx, bar in enumerate(bars):
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height,
                       format_currency(height, currency),
                       ha='center', va='bottom' if height >= 0 else 'top')
            
            # Set x-axis labels with dates
            dates = currency_charges['Transaction Date'].dt.strftime('%Y-%m-%d')
            ax.set_xticks(range(len(currency_charges)))
            ax.set_xticklabels(dates, rotation=45, ha='right')
        
        apply_common_styling(ax, f'Funding Charges ({currency})')

        # Only add legend if we have data
        if not currency_charges.empty:
            ax.legend(['Funding Charge In', 'Funding Charge Out'])
        
        # Format y-axis with currency
        ax.yaxis.set_major_formatter(plt.FuncFormatter(
            lambda x, p: format_currency(x, currency)))
    
    fig.tight_layout()
    return fig
