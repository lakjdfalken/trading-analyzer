import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import logging
from chart_types import (
    balance,
    funding,
    pl_daily_vs_trades,
    pl_market,
    pl_relative,
    trades,
    positions,
    winrate,
    monthly,
    points_daily,
    points_monthly,
    points_per_market,
)
from settings import (
    FIGURE_SIZES,
    CURRENCY_SYMBOLS,
    VALID_GRAPH_TYPES
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
def create_visualization_figure(df, graph_type):
    try:
        if df.empty:
            logger.error("Attempted to create visualization with empty DataFrame")
            raise ValueError("No data available for visualization")
        
        if graph_type not in VALID_GRAPH_TYPES:
            logger.error(f"Invalid graph type requested: {graph_type}")
            raise ValueError(f"Unsupported graph type: {graph_type}")
        
        # Map each graph type to its implementation
        GRAPH_IMPLEMENTATIONS = {
            # Balance charts
            'Balance History': balance.create_balance_history,
            'P/L History': pl_relative.create_relative_balance_history,
        
            # Trade analysis charts
            'Win Rate': winrate.create_distribution_days,
            'Daily Trades': trades.create_daily_trade_count,
        
            # Position analysis
            'Long vs Short Positions': positions.create_position_distribution,
        
            # Market analysis
            'Market Actions': pl_market.create_market_actions,
            'Market P/L': pl_market.create_market_pl,
        
            # Funding analysis
            'Funding': funding.create_funding_distribution,
            'Funding Charges': funding.create_funding_charges,
        
            # Performance analysis
            'Daily P/L': pl_daily_vs_trades.create_daily_pl,
            'Daily P/L vs Trades': pl_daily_vs_trades.create_daily_pl_vs_trades,

            'Monthly P/L': monthly.create_monthly_distribution,
            'Points Daily': points_daily.create_points_daily,
            'Points Monthly': points_monthly.create_points_monthly,
            'Points per Market': points_per_market.create_points_per_market,
        }
        return GRAPH_IMPLEMENTATIONS[graph_type](df)
            
    except Exception as e:
        logger.error(f"Error creating {graph_type} visualization: {str(e)}")
        raise




