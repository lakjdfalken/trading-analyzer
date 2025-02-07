from .base import get_trading_data, setup_base_figure, apply_standard_layout
import plotly.graph_objects as go
from settings import COLORS
import logging
import pandas as pd

logger = logging.getLogger(__name__)

def create_points_analysis(df):
    logger.debug("Starting points analysis")
    trading_data = get_trading_data(df)
    
    # Calculate points for each trade
    trading_data['Points'] = trading_data.apply(lambda row: 
        calculate_points(row['Opening'], row['Closing'], row['Action']), axis=1)
    
    # Group by day and sum points
    trading_data['Date'] = pd.to_datetime(trading_data['Transaction Date']).dt.date
    daily_points = trading_data.groupby('Date')['Points'].sum().reset_index()
    
    # Calculate cumulative points
    daily_cumulative = daily_points['Points'].cumsum()
    total_points = daily_cumulative.iloc[-1]  # Get final cumulative value
    
    fig = setup_base_figure()
    
    # Add daily point bars
    fig.add_trace(go.Bar(
        x=daily_points['Date'],
        y=daily_points['Points'],
        name='Daily Points',
        marker=dict(
            color=daily_points['Points'].apply(
                lambda x: COLORS['profit'] if x > 0 else COLORS['loss']
            )
        )
    ))
    
    # Add cumulative line
    fig.add_trace(go.Scatter(
        x=daily_points['Date'],
        y=daily_cumulative,
        name='Cumulative Points',
        line=dict(color=COLORS['profit'])
    ))
    
    # Add total points annotation box
    fig.add_annotation(
        x=1,
        y=1,
        xref='paper',
        yref='paper',
        text=f'Total Points: {total_points:.2f}',
        showarrow=False,
        font=dict(size=16),
        bgcolor='white',
        bordercolor='black',
        borderwidth=2,
        borderpad=4
    )
    
    fig = apply_standard_layout(fig, "Daily Points Won/Lost Analysis")
    return fig

def calculate_points(open_price, close_price, action):
#    print(f"Calculating points for: Open={open_price}, Close={close_price}, Action={action}")
    try:
        open_price = float(str(open_price).replace(',', ''))
        close_price = float(str(close_price).replace(',', ''))
        
        if action == 'Trade Receivable':
            points = close_price - open_price
        elif action == 'Trade Payable':    
            points = -(open_price - close_price)
            
#        print(f"Calculated points: {points}")
        return points
    except:
        return 0 