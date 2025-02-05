from .base import prepare_dataframe, get_trading_data, format_currency, setup_base_figure, apply_standard_layout
import plotly.graph_objects as go
from settings import COLORS
import pandas as pd

def get_funding_data(df):
    """Returns dataframe filtered for funding transactions"""
    df_copy = prepare_dataframe(df)
#    print("Unique Action values:", df_copy['Action'].unique())
    
    # Try case-insensitive matching for funding transactions
    funding_mask = df_copy['Action'].str.contains('fund', case=False, na=False)
    funding_df = df_copy[funding_mask]
    
#    print("Number of funding transactions found:", len(funding_df))
#    if not funding_df.empty:
#        print("Sample of funding data:\n", funding_df[['Transaction Date', 'Action', 'P/L']].head())
    
    return funding_df

def create_funding_distribution(df):
    funding_df = get_funding_data(df)
    
    # Convert dates and sort all data at once
    funding_df['Transaction Date'] = pd.to_datetime(funding_df['Transaction Date'])
    funding_df = funding_df.sort_values('Transaction Date', ascending=True)
    
    # Calculate totals
    total_deposits = funding_df[funding_df['Action'] == 'Fund receivable']['P/L'].sum()
    total_withdrawals = funding_df[funding_df['Action'] == 'Fund payable']['P/L'].sum()
    total_charges = funding_df[funding_df['Action'] == 'Funding Charges']['P/L'].sum()
    net_total = total_deposits + total_withdrawals + total_charges

    fig = setup_base_figure()
    
    for currency in funding_df['Currency'].unique():
        currency_funding = funding_df[funding_df['Currency'] == currency]
        
        funding_types = {
            'Fund receivable': {'name': 'Deposits', 'color': COLORS['profit']},
            'Fund payable': {'name': 'Withdrawals', 'color': COLORS['loss']}
        }
        
        for action, props in funding_types.items():
            action_data = currency_funding[currency_funding['Action'] == action]
            if not action_data.empty:
                # Convert datetime to string format for Plotly
                x_dates = action_data['Transaction Date'].dt.strftime('%Y-%m-%d')
                
                fig.add_trace(go.Bar(
                    name=f"{props['name']} ({currency})",
                    x=x_dates,
                    y=abs(action_data['P/L']),
                    marker_color=props['color'],
                    text=[f"{val:.0f}" for val in action_data['P/L']],
                    textposition='inside',
                    textfont=dict(
                        color='white',
                        size=12
                    )
                ))    
    # Set explicit x-axis range
    min_date = funding_df['Transaction Date'].min()
    max_date = funding_df['Transaction Date'].max()
    
    fig.update_layout(
        title='Funding Transactions Over Time',
        xaxis=dict(
            title='Date',
            type='category',
        ),
        yaxis_title='Amount (Absolute Value)',
        barmode='group',
        bargap=0.15,
        bargroupgap=0.1,
        showlegend=True,
        legend=dict(
            x=0.0,
            y=1.0,
            xanchor='left',
            yanchor='top'
        ),
        autosize=True
#        height=600
    )
    
    fig.add_annotation(
        text=(f"Total Deposits: {total_deposits:,.0f}<br>"
              f"Total Withdrawals: {abs(total_withdrawals):,.0f}<br>"
              f"Total Charges: {abs(total_charges):,.0f}<br>"
              f"Net Total: {net_total:,.0f}"),
        xref='paper',
        yref='paper',
        x=0.85,
        y=0.90,
        showarrow=False,
        font=dict(size=12),
        bgcolor='white',
        bordercolor='black',
        borderwidth=1,
        xanchor='left',
        yanchor='bottom'
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
    fig = apply_standard_layout(fig, "Funding Charges History") 

    return fig
