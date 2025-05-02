from .base import get_trading_data, setup_base_figure, apply_standard_layout
import plotly.graph_objects as go
from settings import COLORS, MARKETS
import logging
import pandas as pd
import re

logger = logging.getLogger(__name__)

def create_points_per_market(df):
    logger.debug("Starting monthly points per market analysis")
    trading_data = get_trading_data(df)
    
    # Calculate points for each trade
    trading_data['Points'] = trading_data.apply(lambda row: 
        calculate_points(row['Opening'], row['Closing'], row['Action']), axis=1)
    
    # Extract market information from Description
    trading_data['Market'] = trading_data['Description'].apply(extract_market)
    
    # Convert transaction date to datetime if it's not already
    trading_data['Transaction Date'] = pd.to_datetime(trading_data['Transaction Date'])
    
    # Extract month and year for grouping
    trading_data['Month'] = trading_data['Transaction Date'].dt.to_period('M')
    
    # Group by month and market, then sum points
    market_monthly_points = trading_data.groupby(['Month', 'Market'])['Points'].sum().reset_index()
    
    # Convert Period to datetime for plotting
    market_monthly_points['Month'] = market_monthly_points['Month'].dt.to_timestamp()
    
    # Create figure
    fig = setup_base_figure()
    
    # Get unique markets and months for organizing the data
    markets = market_monthly_points['Market'].unique()
    months = sorted(market_monthly_points['Month'].unique())
    
    # Create a color map for markets
    market_colors = {
        market: COLORS['trading'][i % len(COLORS['trading'])] 
        for i, market in enumerate(markets)
    }
    
    # Add traces for each market
    for market in markets:
        market_data = market_monthly_points[market_monthly_points['Market'] == market]
        
        # Calculate cumulative points for this market
        market_cumulative = market_data.sort_values('Month')['Points'].cumsum()
        total_market_points = market_cumulative.iloc[-1] if not market_cumulative.empty else 0
        
        # Add bar chart for this market
        fig.add_trace(go.Bar(
            x=market_data['Month'],
            y=market_data['Points'],
            name=f'{market} Monthly',
            marker=dict(
                color=market_data['Points'].apply(
                    lambda x: COLORS['profit'] if x > 0 else COLORS['loss']
                )
            ),
            hovertemplate='Month: %{x}<br>Points: %{y:.2f}<br>Market: ' + market + '<extra></extra>'
        ))
        
        # Also add line for cumulative points per market
        fig.add_trace(go.Scatter(
            x=market_data['Month'],
            y=market_cumulative,
            mode='lines+markers',
            name=f'{market} Cumulative',
            line=dict(color=market_colors.get(market, COLORS['neutral'])),
            hovertemplate='Month: %{x}<br>Cumulative Points: %{y:.2f}<br>Market: ' + market + '<extra></extra>'
        ))
    
    # Calculate overall points statistics
    total_points = trading_data['Points'].sum()
    total_points_by_market = trading_data.groupby('Market')['Points'].sum().to_dict()
    
    # Add annotation box with total points by market
    annotation_text = f'Total Points: {total_points:.2f}<br><br>By Market:<br>'
    for market, points in total_points_by_market.items():
        annotation_text += f'{market}: {points:.2f}<br>'
    
    fig.add_annotation(
        x=1,
        y=1,
        xref='paper',
        yref='paper',
        text=annotation_text,
        showarrow=False,
        font=dict(size=12),
        bgcolor='white',
        bordercolor='black',
        borderwidth=2,
        borderpad=4,
        align='left'
    )
    
    # Update layout with monthly formatting
    fig = apply_standard_layout(fig, "Monthly Points Won/Lost Per Market")
    
    # Format x-axis to show month and year
    fig.update_xaxes(
        tickformat="%b %Y",
        tickangle=45,
        title_text="Month"
    )
    
    # Update legend to be more compact
    fig.update_layout(
        legend=dict(
            orientation="v",
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=0.01,
            bgcolor='rgba(255,255,255,0.8)'
        ),
        barmode='group'  # Group bars by month
    )
    
    return fig

def calculate_points(open_price, close_price, action):
    try:
        open_price = float(str(open_price).replace(',', ''))
        close_price = float(str(close_price).replace(',', ''))
        
        if action == 'Trade Receivable':
            points = abs(close_price - open_price)
        elif action == 'Trade Payable':    
            points = -(open_price - close_price)  # Subtract points for Trade Payable
            
        logger.debug(f"Calculated points: {points} for {action} open: {open_price} close: {close_price}")
        return points
    except:
        return 0

def extract_market(description):
    """Extract market name from trade description"""
    # Common market patterns in the description
    market_patterns = {
        r'(?i)wall\s*street': 'Wall Street',
        r'(?i)nasdaq': 'NASDAQ',
        r'(?i)nasdaq\s*100': 'NASDAQ 100',
        r'(?i)us\s*tech': 'US Tech',
        r'(?i)ustec': 'US Tech',
        r'(?i)s\s*&\s*p': 'S&P 500',
        r'(?i)gold': 'Gold',
        r'(?i)oil': 'Oil',
        r'(?i)forex': 'Forex',
        r'(?i)eur\s*usd': 'EUR/USD',
        r'(?i)gbp\s*usd': 'GBP/USD',
        r'(?i)usd\s*jpy': 'USD/JPY'
    }
    
    # Check description against patterns
    for pattern, market_name in market_patterns.items():
        if re.search(pattern, str(description)):
            return market_name
    
    # Try to match known market IDs if they're in the description
    for market_name, market_id in MARKETS.items():
        if str(market_id) in str(description):
            return market_name
    
    # Default if no match found
    return 'Other'