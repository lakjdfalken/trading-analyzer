import re
import pandas as pd
import logging
import settings as _settings
from .base import (
    normalize_trading_df,
    ensure_market_column,
)
import plotly.graph_objects as go

# pull config from settings with safe fallbacks
MARKET_POINT_MULTIPLIERS = getattr(_settings, 'MARKET_POINT_MULTIPLIERS', {})
MARKET_MAPPINGS = getattr(_settings, 'MARKET_MAPPINGS', {})
MARKET_ID_MAPPING = getattr(_settings, 'MARKET_ID_MAPPING', {})  # optional map id -> market name
DEFAULT_POINT_MULTIPLIER = getattr(_settings, 'DEFAULT_POINT_MULTIPLIER', 1)
COLORS = getattr(_settings, 'COLORS', {'profit': '#2ca02c', 'loss': '#d62728', 'trading': ['#1f77b4']})

logger = logging.getLogger(__name__)

def create_points_per_market(df):
    logger.debug("Starting monthly points per market analysis")
    trading_data = normalize_trading_df(df)
    if trading_data is None or trading_data.empty:
        return setup_base_figure()
    
    # Extract market information with broker context if available
    if 'broker_name' in trading_data.columns:
        trading_data['Market'] = trading_data.apply(
            lambda row: extract_market(row['Description'], row['broker_name']), axis=1)
    else:
        # ensure Description exists
        if 'Description' not in trading_data.columns:
            trading_data = ensure_market_column(trading_data)
            if 'Description' not in trading_data.columns:
                trading_data['Description'] = trading_data.get('Market', '').astype(str)
        trading_data['Market'] = trading_data['Description'].apply(extract_market)
    
    # Calculate points with market context
    trading_data['Points'] = trading_data.apply(lambda row: 
        calculate_points(row['Opening'], row['Closing'], row['Action'], row['Market']), axis=1)
    
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


def calculate_points(open_price, close_price, action, market=None):
    """
    Calculate points won or lost, adjusted for market-specific tick sizes
    
    Args:
        open_price: Opening price of the trade
        close_price: Closing price of the trade
        action: Trade action (Trade Receivable/Payable)
        market: The market name to apply specific multipliers
        
    Returns:
        Points won (positive) or lost (negative)
    """
    try:
        open_price = float(str(open_price).replace(',', ''))
        close_price = float(str(close_price).replace(',', ''))
        
        # Calculate raw price difference
        price_diff = abs(close_price - open_price)
        
        # Apply market-specific multiplier from settings
        points_multiplier = MARKET_POINT_MULTIPLIERS.get(market, DEFAULT_POINT_MULTIPLIER)
        price_diff *= points_multiplier
        
        # Assign positive or negative sign based on action
        if action == 'Trade Receivable':
            points = price_diff
        elif action == 'Trade Payable':    
            points = -price_diff
        else:
            points = 0
            
        logger.debug(f"Calculated points: {points} for {action} in {market}, open: {open_price} close: {close_price}, multiplier: {points_multiplier}")
        return points
    except Exception as e:
        logger.error(f"Error calculating points: {e}, open: {open_price}, close: {close_price}, market: {market}")
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

def calculate_points_per_market(df, market_point_multipliers=None):
    """Return total points per market using multipliers; robust to column name variants."""
    if df is None or df.empty:
        return {}

    df = df.copy()
    date_col = find_date_col(df) or 'Transaction Date'
    pl_col = find_pl_col(df) or 'P/L'
    coerce_date(df, date_col)
    pl_alias = coerce_pl_numeric(df, pl_col)

    # Ensure Market exists; try to infer from Description if missing
    if 'Market' not in df.columns and 'Description' in df.columns:
        import re as _re
        def _infer(desc):
            if not isinstance(desc, str):
                return 'Unknown'
            for source_map in MARKET_MAPPINGS.values():
                for market_name, pats in source_map.items():
                    for pat in pats:
                        try:
                            if _re.search(pat, desc):
                                return market_name
                        except re.error:
                            continue
            return 'Unknown'
        df['Market'] = df['Description'].apply(_infer)

    if market_point_multipliers is None:
        market_point_multipliers = MARKET_POINT_MULTIPLIERS

    # Use absolute PL values grouped by Market and apply multipliers
    df['_abs_pl'] = df[pl_alias].abs()
    # correct implementation: apply multiplier per market name
    market_points = {}
    for m, group in df.groupby('Market'):
        multiplier = market_point_multipliers.get(m, 1)
        total = (group['_abs_pl'] * multiplier).sum()
        market_points[m] = int(total)
    return market_points
