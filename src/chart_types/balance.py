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
        
        # Calculate metrics per broker
        total_pl = broker_data['P/L'].sum()
        days_traded = len(broker_data['Transaction Date'].dt.date.unique())
        daily_average = total_pl / days_traded if days_traded > 0 else 0
        
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
        
        # Add annotations for broker metrics
        fig.add_annotation(
            text=(f'{broker}<br>'
                  f'Total P/L (with funding): {total_pl:.2f}<br>'
                  f'Daily Avg (with funding): {daily_average:.2f}<br>'
                  f'Total P/L (excl. funding): {total_pl_no_funding:.2f}<br>'
                  f'Daily Avg (excl. funding): {daily_average_no_funding:.2f}'),
            xref='paper', yref='paper',
            x=0.92, y=0.08 + (list(brokers).index(broker) * 0.15),  # Stack annotations with more space
            showarrow=False,
            bgcolor='white',
            bordercolor='black',
            borderwidth=1
        )
    
    fig = apply_standard_layout(fig, "Balance History (With and Without Funding)")
    
    # Add a note explaining the lines
    fig.add_annotation(
        text="Blue solid line: Actual balance including funding<br>Green dashed line: Balance excluding funding",
        xref='paper', yref='paper',
        x=0.5, y=1.05,
        showarrow=False,
        font=dict(size=10),
        bgcolor='rgba(255,255,255,0.8)',
        bordercolor='black',
        borderwidth=1
    )
    
    return fig