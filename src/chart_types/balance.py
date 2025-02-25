import plotly.graph_objects as go
from .base import prepare_dataframe, setup_base_figure, apply_standard_layout
import logging

logger = logging.getLogger(__name__)

def create_balance_history(df):
    fig = setup_base_figure()
    trading_data = prepare_dataframe(df).copy()  # Create explicit copy
    
    # Sort by date and group by broker
    trading_data = trading_data.sort_values('Transaction Date')
    brokers = trading_data['broker_name'].unique()
    
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
        # Add trace for each broker
        fig.add_trace(go.Scatter(
            x=broker_data['Transaction Date'],
            y=broker_data['Cumulative P/L'],
            mode='lines+markers',
            name=f'{broker} Cumulative P/L',
            hovertemplate=f'Broker: {broker}<br>Date: %{{x}}<br>Cumulative P/L: %{{y:.2f}}<extra></extra>'
        ))
        
        # Add annotations for broker metrics
        fig.add_annotation(
            text=f'{broker}<br>Total P/L: {total_pl:.2f}<br>Daily Avg: {daily_average:.2f}',
            xref='paper', yref='paper',
            x=0.92, y=0.08 + (list(brokers).index(broker) * 0.1),  # Stack annotations
            showarrow=False,
            bgcolor='white',
            bordercolor='black',
            borderwidth=1
        )
    
    fig = apply_standard_layout(fig, "Combined Broker P/L Over Time")
    
    return fig