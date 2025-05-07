from .base import get_trading_data, setup_base_figure, apply_standard_layout
import plotly.graph_objects as go
from settings import COLORS
import logging
import pandas as pd

logger = logging.getLogger(__name__)

def create_points_daily(df):
    logger.debug("Starting points analysis")
    trading_data = get_trading_data(df)
    
    # Calculate points for each trade
    trading_data['Points'] = trading_data.apply(lambda row: 
        calculate_points(row['Opening'], row['Closing'], row['Action']), axis=1)
    
    # Group by day and sum points
    trading_data['Date'] = pd.to_datetime(trading_data['Transaction Date']).dt.date
    daily_points = trading_data.groupby('Date')['Points'].sum().reset_index()
    
    # Initialize default values in case the dataframe is empty
    total_points = 0
    avg_points_per_day = 0
    
    # Calculate metrics only if we have data
    if not daily_points.empty:
        # Calculate cumulative points
        daily_cumulative = daily_points['Points'].cumsum()
        total_points = daily_cumulative.iloc[-1] if len(daily_cumulative) > 0 else 0
        
        # Calculate average points per day
        num_days = len(daily_points)
        avg_points_per_day = total_points / num_days if num_days > 0 else 0
    else:
        # Create empty series for plotting if no data
        daily_cumulative = pd.Series()
    
    fig = setup_base_figure()
    
    # Add daily point bars if we have data
    if not daily_points.empty:
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
    
    # Add total points and average points per day annotation box
    fig.add_annotation(
        x=1,
        y=1,
        xref='paper',
        yref='paper',
        text=f'Total Points: {total_points:.2f}<br>Avg Points/Day: {avg_points_per_day:.2f}',
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
    try:
        open_price = float(str(open_price).replace(',', ''))
        close_price = float(str(close_price).replace(',', ''))
        
        if action == 'Trade Receivable':
            # For winning trades, points won is absolute difference between prices
            points = abs(close_price - open_price)
        elif action == 'Trade Payable':    
            # For losing trades, points lost is also absolute difference (but negative)
            points = -abs(close_price - open_price)
            
        logger.debug(f"Calculated points: {points} for {action} open: {open_price} close: {close_price}")
        return points
    except Exception as e:
        logger.error(f"Error calculating points: {e}, open: {open_price}, close: {close_price}")
        return 0