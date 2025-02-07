from .base import prepare_dataframe, get_trading_data, format_currency, setup_base_figure, apply_standard_layout
import plotly.graph_objects as go
from settings import COLORS
import pandas as pd
import logging
from logger import setup_logger

logger = logging.getLogger(__name__)

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
    logger.debug("Starting funding charges analysis")
    
    df_copy = prepare_dataframe(df).copy()
    df_copy['Transaction Date'] = pd.to_datetime(df_copy['Transaction Date'])
    # Sort by date and P/L in reverse order to stack largest values first
    #df_copy = df_copy.sort_values(['Transaction Date', 'P/L'], ascending=[True, False])
    
    funding_mask = df_copy['Action'].str.contains('Funding charge', case=False, na=False)
    funding_c_df = df_copy[funding_mask]

    #funding_c_df = funding_c_df.sort_values(['Transaction Date', 'P/L'], ascending=[True, True])
    # Sort by date first, then by absolute value of P/L in descending order
    
    logger.debug(f"Found {len(funding_c_df)} funding charge entries")
    
    fig = setup_base_figure()
    y_position = 0.95
    
    # Sort by exact timestamp and P/L to ensure consistent display
    #funding_c_df = funding_c_df.sort_values(['Transaction Date', 'P/L'], ascending=[True, False])
    
    # Calculate date range and adjust bar width accordingly
    date_range = (funding_c_df['Transaction Date'].max() - funding_c_df['Transaction Date'].min()).days
    bar_width = max(8*60*60*1000, date_range*24*60*60*1000/100)  # Minimum 8 hours, or 1% of total range

    for idx, row in funding_c_df.iterrows():
        fig.add_trace(go.Bar(
            x=[row['Transaction Date']],
            y=[row['P/L']],
            name=f"{row['Currency']} {row['Transaction Date'].strftime('%Y-%m-%d')}",
            marker=dict(
                color=COLORS['loss'],
                line=dict(color='white', width=1)
            ),
            text=[format_currency(row['P/L'], row['Currency'])],
            textposition='auto',
            width=bar_width,
            offset=-bar_width/2,
            showlegend=False
        ))
    
    # Add total annotations per currency
    for currency in funding_c_df['Currency'].unique():
        currency_total = funding_c_df[funding_c_df['Currency'] == currency]['P/L'].sum()
        fig.add_annotation(
            text=f"Total {currency} Charges: {format_currency(currency_total, currency)}",
            xref='paper', yref='paper',
            x=1.02, y=y_position,
            showarrow=False,
            bgcolor='white',
            bordercolor='gray',
            borderwidth=1
        )
        y_position -= 0.05
    
    # Calculate total range for y-axis
    total_min = funding_c_df['P/L'].sum()
    logger.debug(f"total_min: {total_min} funding charge entries")
    logger.debug(f"Total {currency} Charges: {format_currency(currency_total, currency)}")
    
    fig.update_layout(
        barmode='stack',
        bargap=0.3,
        showlegend=False,
        yaxis=dict(
            #range=[total_min * 1.1, 0],  # Set range from total sum to zero
            range=[total_min, 0],  # Set range from total sum to zero
            title="Cumulative Charges"
        )
    )
    
    fig = apply_standard_layout(fig, "Funding Charges History")
    return fig
