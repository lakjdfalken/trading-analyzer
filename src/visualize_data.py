import matplotlib.pyplot as plt
import pandas as pd
import logging

from settings import (
    FIGURE_SIZES,
    CURRENCY_SYMBOLS,
    VALID_GRAPH_TYPES,
    DEFAULT_EXCHANGE_RATES,
    DEFAULT_BASE_CURRENCY
)

# Configure logging
logger = logging.getLogger(__name__)

logging.getLogger('matplotlib').setLevel(logging.WARNING)
logging.getLogger('matplotlib.pyplot').setLevel(logging.WARNING)
logging.getLogger('matplotlib.font_manager').setLevel(logging.WARNING)
logging.getLogger('PIL.PngImagePlugin').setLevel(logging.WARNING)

# Utility functions
def format_currency(value, currency):
    symbol = CURRENCY_SYMBOLS.get(currency, '')
    return f'{symbol}{abs(value):,.2f}'

def setup_base_figure(figsize='default'):
    plt.style.use('bmh')
    fig = plt.Figure(figsize=FIGURE_SIZES.get(figsize, FIGURE_SIZES['default']))
    ax = fig.add_subplot(111)
    return fig, ax

def apply_common_styling(ax, title, xlabel=None, ylabel=None):
    ax.set_title(title, fontsize=14, pad=15)
    if xlabel:
        ax.set_xlabel(xlabel, fontsize=12)
    if ylabel:
        ax.set_ylabel(ylabel, fontsize=12)
    ax.tick_params(axis='x', rotation=45)
    ax.grid(True, alpha=0.3)

# Main visualization function
def create_visualization_figure(df, graph_type, exchange_rates=None, base_currency=None):
    """
    Create visualization figure based on graph type
    """
    logger.debug("visualize_data: requested graph_type=%r", graph_type)
    
    if exchange_rates is None:
        exchange_rates = DEFAULT_EXCHANGE_RATES
    
    if base_currency is None:
        base_currency = DEFAULT_BASE_CURRENCY
    
    try:
        if df.empty:
            logger.error("Attempted to create visualization with empty DataFrame")
            raise ValueError("No data available for visualization")
        
        if graph_type not in VALID_GRAPH_TYPES:
            logger.error(f"Invalid graph type requested: {graph_type}")
            raise ValueError(f"Unsupported graph type: {graph_type}")
        
        # Handle Balance History separately since it needs exchange rates and base currency
        if graph_type == 'Balance History':
            from chart_types.balance import create_balance_history
            return create_balance_history(df, exchange_rates, base_currency)
        
        # For all other chart types, use the correct function names from the grep output
        elif graph_type == 'P/L History':
            from chart_types.pl import create_relative_balance_history
            return create_relative_balance_history(df)
            
        elif graph_type == 'Daily P/L':
            logger.debug("visualize_data: calling create_daily_pl with df.shape=%s", getattr(df, "shape", None))
            from chart_types.pl import create_daily_pl
            return create_daily_pl(df, exchange_rates, base_currency)
            
        elif graph_type == 'Monthly P/L':
            from chart_types.monthly import create_monthly_distribution
            return create_monthly_distribution(df)
            
        elif graph_type == 'Market P/L':
            from chart_types.pl import create_market_pl
            return create_market_pl(df)
            
        elif graph_type == 'Daily Trades':
            from chart_types.trades import create_daily_trade_count
            return create_daily_trade_count(df)
            
        elif graph_type == 'Daily P/L vs Trades':
            from chart_types.pl import create_daily_pl_vs_trades
            return create_daily_pl_vs_trades(df, exchange_rates=exchange_rates, base_currency=base_currency)
            
        elif graph_type == 'Points Daily':
            from chart_types.points import create_points_view
            return create_points_view(df, mode="daily", top_n=10)
            
        elif graph_type == 'Points Monthly':
            from chart_types.points import create_points_view
            return create_points_view(df, mode="monthly", top_n=10)
            
        elif graph_type == 'Points per Market':
            from chart_types.points import create_points_view
            return create_points_view(df, mode="per_market", top_n=10)
            
        elif graph_type == 'Win Rate':
            from chart_types.winrate import create_distribution_days
            return create_distribution_days(df)
            
        elif graph_type == 'Funding':
            from chart_types.funding import create_funding_distribution
            return create_funding_distribution(df)
            
        elif graph_type == 'Long vs Short Positions':
            from chart_types.positions import create_position_distribution
            return create_position_distribution(df)
            
        else:
            logger.error(f"Unknown graph type: {graph_type}")
            raise ValueError(f"Unknown graph type: {graph_type}")
                
    except Exception as e:
        logger.error(f"Error creating {graph_type} visualization: {str(e)}")
        raise
