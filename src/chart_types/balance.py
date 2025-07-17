import plotly.graph_objects as go
from .base import prepare_dataframe, setup_base_figure, apply_standard_layout, get_trading_pl_without_funding
import logging

logger = logging.getLogger(__name__)

def create_balance_history(df):
    fig = setup_base_figure()
    trading_data = prepare_dataframe(df).copy()  # Create explicit copy
    
    # Sort by date and group by broker
    trading_data = trading_data.sort_values('Transaction Date')
    brokers = trading_data['broker_name'].unique()
    
    # Also get data without funding for comparison
    trading_data_without_funding = get_trading_pl_without_funding(df)
    
    # Calculate and plot for each broker
    for broker in brokers:
        # Create explicit copy of filtered data
        broker_data = trading_data[trading_data['broker_name'] == broker].copy()
        
        # Calculate metrics per broker (including all transactions)
        total_pl = broker_data['P/L'].sum()
        days_traded = len(broker_data['Transaction Date'].dt.date.unique())
        daily_average = total_pl / days_traded if days_traded > 0 else 0
        
        # Calculate funding charges for this broker
        charges_mask = broker_data['Action'].str.contains('Funding charge', case=False, na=False)
        total_charges = broker_data[charges_mask]['P/L'].sum()
        
        # Calculate deposits and withdrawals
        deposits = broker_data[broker_data['Action'] == 'Fund receivable']['P/L'].sum()
        withdrawals = broker_data[broker_data['Action'] == 'Fund payable']['P/L'].sum()
        
        # Calculate cumulative P/L using loc
        broker_data.loc[:, 'Cumulative P/L'] = broker_data['P/L'].cumsum()        
        
        # Add trace for each broker with actual balance
        fig.add_trace(go.Scatter(
            x=broker_data['Transaction Date'],
            y=broker_data['Balance'],
            mode='lines+markers',
            name=f'{broker} Actual Balance',
            line=dict(color='blue'),
            hovertemplate=f'Broker: {broker}<br>Date: %{{x}}<br>Balance: %{{y:.2f}}<extra></extra>'
        ))
        
        # Filter no-funding data for this broker
        if 'broker_name' in trading_data_without_funding.columns:
            broker_data_no_funding = trading_data_without_funding[
                trading_data_without_funding['broker_name'] == broker].copy()
        else:
            # If broker_name column is missing, use all data (assuming single broker)
            broker_data_no_funding = trading_data_without_funding.copy()
        
        if not broker_data_no_funding.empty:
            # Add trace for each broker with balance without funding
            fig.add_trace(go.Scatter(
                x=broker_data_no_funding['Transaction Date'],
                y=broker_data_no_funding['Balance'],
                mode='lines+markers',
                name=f'{broker} Balance Without Funding',
                line=dict(color='green', dash='dash'),
                hovertemplate=f'Broker: {broker}<br>Date: %{{x}}<br>Balance Without Funding: %{{y:.2f}}<extra></extra>'
            ))
            
            # Calculate metrics for balance without funding
            total_pl_no_funding = broker_data_no_funding['P/L'].sum()
            daily_average_no_funding = total_pl_no_funding / days_traded if days_traded > 0 else 0
        else:
            total_pl_no_funding = 0
            daily_average_no_funding = 0
        
        # Calculate trading P/L (excluding funding transactions)
        trading_only_mask = ~broker_data['Action'].str.contains('fund', case=False, na=False)
        trading_pl = broker_data[trading_only_mask]['P/L'].sum()
        
        # Add annotations for broker metrics with charges breakdown
        fig.add_annotation(
            text=(f'{broker}<br>'
                  f'Total P/L (with funding): {total_pl:.2f}<br>'
                  f'Daily Avg (with funding): {daily_average:.2f}<br>'
                  f'Total P/L (excl. funding): {total_pl_no_funding:.2f}<br>'
                  f'Daily Avg (excl. funding): {daily_average_no_funding:.2f}<br>'
                  f'Trading P/L: {trading_pl:.2f}<br>'
                  f'Funding Charges: {total_charges:.2f}<br>'
                  f'Deposits: {deposits:.2f}<br>'
                  f'Withdrawals: {withdrawals:.2f}'),
            xref='paper', yref='paper',
            x=0.92, y=0.08 + (list(brokers).index(broker) * 0.20),  # More space for additional info
            showarrow=False,
            bgcolor='white',
            bordercolor='black',
            borderwidth=1,
            font=dict(size=10)
        )
    
    fig = apply_standard_layout(fig, "Balance History (With and Without Funding)")
    
    # Add a note explaining the lines and metrics
    fig.add_annotation(
        text=("Blue solid line: Actual balance including funding<br>"
              "Green dashed line: Balance excluding funding<br>"
              "Annotations show detailed breakdown including charges"),
        xref='paper', yref='paper',
        x=0.5, y=1.05,
        showarrow=False,
        font=dict(size=10),
        bgcolor='rgba(255,255,255,0.8)',
        bordercolor='black',
        borderwidth=1
    )
    
    return fig