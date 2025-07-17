from .base import prepare_dataframe, get_trading_data, format_currency, setup_base_figure, apply_standard_layout
import plotly.graph_objects as go
from settings import COLORS
import pandas as pd
import logging

logger = logging.getLogger(__name__)

def get_funding_data(df):
    """Returns dataframe filtered for funding transactions"""
    logger.debug("get_funding_data called")  # Add this debug line
    df_copy = prepare_dataframe(df)
    
    # Try case-insensitive matching for funding transactions
    funding_mask = df_copy['Action'].str.contains('fund', case=False, na=False)
    funding_df = df_copy[funding_mask]
    
    logger.debug(f"Found {len(funding_df)} funding transactions")  # Add this debug line
    
    return funding_df

def create_funding_distribution(df):
    logger.debug("create_funding_distribution called")  # Add this debug line
    funding_df = get_funding_data(df)
    
    # Debug: Check what Action values we actually have
    logger.debug(f"Unique Action values in funding data: {funding_df['Action'].unique()}")
    
    # Convert dates and sort all data at once
    funding_df['Transaction Date'] = pd.to_datetime(funding_df['Transaction Date'])
    funding_df = funding_df.sort_values('Transaction Date', ascending=True)
    
    # Calculate totals - check for different possible charge action names
    total_deposits = funding_df[funding_df['Action'] == 'Fund receivable']['P/L'].sum()
    total_withdrawals = funding_df[funding_df['Action'] == 'Fund payable']['P/L'].sum()
    
    # Try different possible names for charges
    charges_mask = (
        (funding_df['Action'] == 'Funding Charges') |
        (funding_df['Action'] == 'Funding charge') |
        (funding_df['Action'].str.contains('Funding charge', case=False, na=False))
    )
    total_charges = funding_df[charges_mask]['P/L'].sum()
    net_total = total_deposits + total_withdrawals + total_charges

    logger.debug(f"Calculated totals - Deposits: {total_deposits}, Withdrawals: {total_withdrawals}, Charges: {total_charges}")

    fig = setup_base_figure()
    
    for currency in funding_df['Currency'].unique():
        currency_funding = funding_df[funding_df['Currency'] == currency]
        
        # Updated funding_types with blue color for charges and better matching
        funding_types = {
            'Fund receivable': {'name': 'Deposits', 'color': COLORS['profit']},
            'Fund payable': {'name': 'Withdrawals', 'color': COLORS['loss']}
        }
        
        # Add charges with flexible matching
        charges_data = currency_funding[
            (currency_funding['Action'] == 'Funding Charges') |
            (currency_funding['Action'] == 'Funding charge') |
            (currency_funding['Action'].str.contains('Funding charge', case=False, na=False))
        ]
        
        # Process standard funding types
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
                    ),
                    legendgroup=f"{props['name']}_{currency}",
                    showlegend=True
                ))
        
        # Process charges separately with blue color
        if not charges_data.empty:
            x_dates = charges_data['Transaction Date'].dt.strftime('%Y-%m-%d')
            
            fig.add_trace(go.Bar(
                name=f"Charges ({currency})",
                x=x_dates,
                y=abs(charges_data['P/L']),
                marker_color='#0066CC',  # Blue color
                text=[f"{val:.0f}" for val in charges_data['P/L']],
                textposition='inside',
                textfont=dict(
                    color='white',
                    size=12
                ),
                legendgroup=f"Charges_{currency}",
                showlegend=True
            ))
    
    # Set explicit x-axis range
    min_date = funding_df['Transaction Date'].min()
    max_date = funding_df['Transaction Date'].max()
    
    fig.update_layout(
        title='Funding Transactions Over Time',
        xaxis=dict(
            title='Date',
            type='date',
            tickformat='%Y-%m-%d'
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
            yanchor='top',
            bgcolor='rgba(255,255,255,0.8)',
            bordercolor='black',
            borderwidth=1
        ),
        autosize=True
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
    df_copy['Transaction Date'] = pd.to_datetime(df_copy['Transaction Date'], format='%Y-%m-%d')
    
    funding_mask = df_copy['Action'].str.contains('Funding charge', case=False, na=False)
    funding_c_df = df_copy[funding_mask]

    # Reset index after filtering to ensure proper sorting
    funding_c_df = funding_c_df.reset_index(drop=True)
    funding_c_df = funding_c_df.sort_values(by='Transaction Date', ascending=True)
    
    logger.debug(f"Found {len(funding_c_df)} funding charge entries")
    logger.debug(f"Date range: {funding_c_df['Transaction Date'].min()} to {funding_c_df['Transaction Date'].max()}")
    
    fig = setup_base_figure()
    y_position = 0.95
    
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
            range=[total_min, 0],  # Set range from total sum to zero
            title="Cumulative Charges"
        ),
        xaxis=dict(
            title='Date',
            type='date',
            tickformat='%Y-%m-%d',
        )
    )
    
    fig = apply_standard_layout(fig, "Funding Charges History")
    return fig
