from .base import prepare_dataframe, get_trading_data, format_currency, setup_base_figure, apply_common_styling
import plotly.graph_objects as go
from settings import COLORS

def get_funding_data(df):
    """Returns dataframe filtered for funding transactions"""
    df_copy = prepare_dataframe(df)
    return df_copy[df_copy['Action'].str.startswith('Fund')]

def create_funding_distribution(df):
    funding_df = get_funding_data(df)
    fig = setup_base_figure()
    
    for currency in funding_df['Currency'].unique():
        currency_funding = funding_df[funding_df['Currency'] == currency]
        
        if not currency_funding.empty:
            # Calculate totals
            total_in = currency_funding[currency_funding['P/L'] > 0]['P/L'].sum()
            total_out = currency_funding[currency_funding['P/L'] < 0]['P/L'].sum()
            net_total = total_in + total_out
            
            # Create pie chart
            values = [abs(total_in), abs(total_out)]
            labels = ['Funding In', 'Funding Out']
            
            fig.add_trace(go.Pie(
                values=values,
                labels=labels,
                name=currency,
                domain={'x': [0, 0.7]},  # Position pie chart on left side
                marker_colors=[COLORS['profit'], COLORS['loss']],
                textinfo='percent+value',
                hovertemplate="%{label}<br>Amount: %{value:,.2f}<br>Percentage: %{percent}<extra></extra>"
            ))
            
            # Add totals annotation
            totals_text = (
                f"Currency: {currency}<br>"
                f"Total In: {format_currency(total_in, currency)}<br>"
                f"Total Out: {format_currency(total_out, currency)}<br>"
                f"Net Total: {format_currency(net_total, currency)}"
            )
            
            fig.add_annotation(
                text=totals_text,
                xref='paper', yref='paper',
                x=0.85, y=0.5,
                showarrow=False,
                bgcolor='white',
                bordercolor='gray',
                borderwidth=1
            )
    
    fig.update_layout(
        title='Funding Distribution',
        showlegend=True,
        margin=dict(t=100, b=100, r=200)
    )
    
    return fig

def create_funding_charges(df):
    df_copy = prepare_dataframe(df)
    funding_c_df = df_copy[df_copy['Action'].str.contains('Funding charge', case=False, na=False)]
    
    fig = setup_base_figure()
    
    for currency in funding_c_df['Currency'].unique():
        currency_charges = funding_c_df[funding_c_df['Currency'] == currency]
        
        if not currency_charges.empty:
            # Sort by date for chronological display
            currency_charges = currency_charges.sort_values('Transaction Date')
            
            # Add bar chart
            fig.add_trace(go.Bar(
                x=currency_charges['Transaction Date'],
                y=currency_charges['P/L'],
                name=f'{currency} Charges',
                marker_color=[COLORS['profit'] if x > 0 else COLORS['loss'] for x in currency_charges['P/L']],
                text=[format_currency(x, currency) for x in currency_charges['P/L']],
                textposition='outside',
                hovertemplate="Date: %{x}<br>Amount: %{text}<extra></extra>"
            ))
            
            # Calculate and add summary statistics
            total_charges = currency_charges['P/L'].sum()
            avg_charge = currency_charges['P/L'].mean()
            
            summary_text = (
                f"{currency} Summary<br>"
                f"Total Charges: {format_currency(total_charges, currency)}<br>"
                f"Average Charge: {format_currency(avg_charge, currency)}"
            )
            
            fig.add_annotation(
                text=summary_text,
                xref='paper', yref='paper',
                x=1.02, y=0.95,
                showarrow=False,
                bgcolor='white',
                bordercolor='gray',
                borderwidth=1
            )
    
    fig.update_layout(
        title='Funding Charges History',
        xaxis_title='Date',
        yaxis_title='Charge Amount',
        showlegend=True,
        margin=dict(t=100, b=100, r=300),
        xaxis_tickangle=45
    )
    
    return fig
