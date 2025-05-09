from .base import get_trading_data, setup_base_figure, apply_standard_layout
import plotly.graph_objects as go
from settings import COLORS
import logging
import pandas as pd

logger = logging.getLogger(__name__)

def create_points_monthly(df):
    logger.debug("Starting monthly points analysis")
    trading_data = get_trading_data(df)
    
    # Calculate points for each trade
    trading_data['Points'] = trading_data.apply(lambda row: 
        calculate_points(row['Opening'], row['Closing'], row['Action']), axis=1)
    
    # Convert transaction date to datetime if it's not already
    trading_data['Transaction Date'] = pd.to_datetime(trading_data['Transaction Date'])
    
    # Extract month and year for grouping
    trading_data['Month'] = trading_data['Transaction Date'].dt.to_period('M')
    
    # Group by month and sum points
    monthly_points = trading_data.groupby('Month')['Points'].sum().reset_index()
    
    # Initialize default values
    total_points = 0
    avg_points_per_month = 0
    monthly_cumulative = pd.Series()
    
    # Calculate metrics only if we have data
    if not monthly_points.empty:
        # Convert Period to datetime for plotting
        monthly_points['Month'] = monthly_points['Month'].dt.to_timestamp()
        
        # Calculate cumulative points
        monthly_cumulative = monthly_points['Points'].cumsum()
        total_points = monthly_cumulative.iloc[-1] if not monthly_cumulative.empty else 0
        
        # Calculate average points per month
        num_months = len(monthly_points)
        avg_points_per_month = total_points / num_months if num_months > 0 else 0
    
    fig = setup_base_figure()
    
    # Add visualizations only if we have data
    if not monthly_points.empty:
        # Add monthly point bars
        fig.add_trace(go.Bar(
            x=monthly_points['Month'],
            y=monthly_points['Points'],
            name='Monthly Points',
            marker=dict(
                color=monthly_points['Points'].apply(
                    lambda x: COLORS['profit'] if x > 0 else COLORS['loss']
                )
            )
        ))
        
        # Add cumulative line
        fig.add_trace(go.Scatter(
            x=monthly_points['Month'],
            y=monthly_cumulative,
            name='Cumulative Points',
            line=dict(color=COLORS['profit'])
        ))
    
    # Add total points and average points per month annotation box
    fig.add_annotation(
        x=1,
        y=1,
        xref='paper',
        yref='paper',
        text=f'Total Points: {total_points:.2f}<br>Avg Points/Month: {avg_points_per_month:.2f}',
        showarrow=False,
        font=dict(size=16),
        bgcolor='white',
        bordercolor='black',
        borderwidth=2,
        borderpad=4
    )
    
    # Update layout with monthly formatting
    fig = apply_standard_layout(fig, "Monthly Points Won/Lost Analysis")
    
    # Format x-axis to show month and year
    fig.update_xaxes(
        tickformat="%b %Y",
        tickangle=45,
        title_text="Month"
    )
    
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