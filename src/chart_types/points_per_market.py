from .base import get_trading_data, setup_base_figure, apply_standard_layout
import plotly.graph_objects as go
from settings import COLORS, MARKETS, MARKET_ID_MAPPING, MARKET_MAPPINGS
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
    
    # Extract market information with broker context if available
    if 'broker_name' in trading_data.columns:
        trading_data['Market'] = trading_data.apply(
            lambda row: extract_market(row['Description'], row['broker_name']), axis=1)
    else:
        trading_data['Market'] = trading_data['Description'].apply(extract_market)
    
    # Count unidentified markets
    other_count = (trading_data['Market'] == 'Other').sum()
    if other_count > 0:
        logger.info(f"Found {other_count} trades categorized as 'Other' market")
        
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
    
    # Add traces for each market - bar charts only (no cumulative lines)
    for market in markets:
        market_data = market_monthly_points[market_monthly_points['Market'] == market]
        
        # Calculate total points for this market (for annotation)
        total_market_points = market_data['Points'].sum()
        
        # Add bar chart for this market
        fig.add_trace(go.Bar(
            x=market_data['Month'],
            y=market_data['Points'],
            name=f'{market}',  # Simplified name without "Monthly"
            marker=dict(
                color=market_data['Points'].apply(
                    lambda x: COLORS['profit'] if x > 0 else COLORS['loss']
                )
            ),
            hovertemplate='Month: %{x}<br>Points: %{y:.2f}<br>Market: ' + market + '<extra></extra>'
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

def extract_market(description, broker_name='standard'):
    """
    Extract market name from trade description with broker-specific customization
    
    Args:
        description: The trade description text
        broker_name: The broker name for broker-specific mappings
    
    Returns:
        Standardized market name
    """
    # Convert description to string to handle non-string inputs
    description = str(description)
    
    # First, check for market IDs in the description
    for market_id, standard_name in MARKET_ID_MAPPING.items():
        if str(market_id) in description:
            logger.debug(f"Matched market ID {market_id} to {standard_name}")
            return standard_name
    
    # Then try broker-specific patterns if available
    if broker_name in MARKET_MAPPINGS:
        for market_name, patterns in MARKET_MAPPINGS[broker_name].items():
            for pattern in patterns:
                if re.search(pattern, description):
                    logger.debug(f"Matched broker-specific pattern '{pattern}' to {market_name}")
                    return market_name
    
    # Fall back to standard patterns
    for market_name, patterns in MARKET_MAPPINGS['standard'].items():
        for pattern in patterns:
            if re.search(pattern, description):
                logger.debug(f"Matched standard pattern '{pattern}' to {market_name}")
                return market_name
    
    # Log unmatched descriptions to help improve the patterns
    logger.warning(f"No market match found for: '{description}', categorizing as 'Other'")
    return 'Other'

def analyze_unmatched_markets(df):
    """
    Helper function to identify descriptions that don't match any market
    """
    trading_data = get_trading_data(df)
    
    # Apply market extraction
    if 'broker_name' in trading_data.columns:
        trading_data['Market'] = trading_data.apply(
            lambda row: extract_market(row['Description'], row['broker_name']), axis=1)
    else:
        trading_data['Market'] = trading_data['Description'].apply(extract_market)
    
    # Find unmatched entries
    unmatched = trading_data[trading_data['Market'] == 'Other']
    
    # Group by unique description to see what's missing
    if not unmatched.empty:
        descriptions = unmatched['Description'].value_counts()
        logger.info("Unmatched market descriptions:")
        for desc, count in descriptions.items():
            logger.info(f"  {count} trades: {desc}")
    
    return unmatched
