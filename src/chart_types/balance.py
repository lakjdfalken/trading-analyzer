import plotly.graph_objects as go
from .base import get_trading_data, setup_base_figure, apply_standard_layout
import logging

logger = logging.getLogger(__name__)

def create_balance_history(df):
    fig = setup_base_figure()
    trading_data = get_trading_data(df)
    
    trading_data = trading_data.sort_values('Transaction Date')
    
    # Calculate metrics
    total_pl = trading_data['P/L'].sum()
    days_traded = len(trading_data['Transaction Date'].dt.date.unique())
    daily_average = total_pl / days_traded if days_traded > 0 else 0
    
    # Calculate cumulative P/L
    trading_data['Cumulative P/L'] = trading_data['P/L'].cumsum()
    
    # Add metrics to plot
    fig.add_trace(go.Scatter(
        x=trading_data['Transaction Date'],
        y=trading_data['Cumulative P/L'],
        mode='lines+markers',
        name='Cumulative P/L',
        hovertemplate='Date: %{x}<br>Cumulative P/L: %{y:.2f}<extra></extra>'
    ))
    
    # Add annotations for metrics
    fig.add_annotation(
        text=f'Total P/L: {total_pl:.2f}<br>Daily Average: {daily_average:.2f}',
        xref='paper', yref='paper',
        x=0.92, y=0.08,
        showarrow=False,
        bgcolor='white',
        bordercolor='black',
        borderwidth=1
    )
    
    fig = apply_standard_layout(fig, "Relative P/L Over Time")
    
    return fig