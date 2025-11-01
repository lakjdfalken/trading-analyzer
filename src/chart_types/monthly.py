from .base import get_trading_data, setup_base_figure, apply_standard_layout
import plotly.graph_objects as go
from settings import COLORS
import re
import pandas as pd
import logging
from .base import (
    find_date_col,
    find_pl_col,
    coerce_date,
    coerce_pl_numeric,
    ensure_market_column,
    aggregate_pl_by_period,
    top_markets_by_pl,
)
import chart_types.base as base

logger = logging.getLogger(__name__)

def create_monthly_distribution(df):
    trading_data = get_trading_data(df)
    trading_data['Month'] = trading_data['Transaction Date'].dt.strftime('%Y-%m')
    
    # Calculate monthly metrics
    monthly_stats = {}
    total_pl = 0
    for month in sorted(trading_data['Month'].unique()):
        month_data = trading_data[trading_data['Month'] == month]
        wins = month_data[month_data['P/L'] > 0]
        losses = month_data[month_data['P/L'] < 0]
        
        win_pl = wins['P/L'].sum()
        loss_pl = losses['P/L'].sum()
        total_pl += win_pl + loss_pl
        
        monthly_stats[month] = {
            'win_count': len(wins),
            'loss_count': len(losses),
            'win_pl': win_pl,
            'loss_pl': loss_pl
        }
    
    months = sorted(monthly_stats.keys())
    
    fig = setup_base_figure()
    
    # Add bars for wins
    fig.add_trace(go.Bar(
        name='Wins',
        x=months,
        y=[monthly_stats[m]['win_count'] for m in months],
        marker_color=COLORS['profit'],
        text=[f"Trades: <br>{monthly_stats[m]['win_count']}<br>(+{monthly_stats[m]['win_pl']:.0f})" for m in months],
        textposition='inside',
        textfont=dict(color='white', size=12)
    ))
    
    # Add bars for losses
    fig.add_trace(go.Bar(
        name='Losses',
        x=months,
        y=[monthly_stats[m]['loss_count'] for m in months],
        marker_color=COLORS['loss'],
        text=[f"Trades: <br>{monthly_stats[m]['loss_count']}<br>({monthly_stats[m]['loss_pl']:.0f})" for m in months],
        textposition='inside',
        textfont=dict(color='white', size=12)
    ))
    
    # Add total annotation
    fig.add_annotation(
        text=f"Total P/L: {total_pl:,.0f}",
        xref='paper',
        yref='paper',
        x=1.02,
        y=0.95,
        showarrow=False,
        bgcolor='white',
        bordercolor='gray',
        borderwidth=1
    )
    
    fig.update_layout(barmode='group')
    fig = apply_standard_layout(fig, "Monthly Win/Loss trades")
    
    return fig

def create_monthly_summary(df, start_date=None, end_date=None):
    dfc = base.get_filtered_trading_df(df, start_date=start_date, end_date=end_date)
    if dfc is None:
        dfc = pd.DataFrame()
    if dfc.empty:
        return setup_base_figure()

    dfc['Month'] = dfc['Transaction Date'].dt.to_period('M').dt.to_timestamp()

    monthly_summary = dfc.groupby('Month').agg(
        total_trades=('P/L', 'size'),
        winning_trades=('P/L', lambda x: (x > 0).sum()),
        losing_trades=('P/L', lambda x: (x < 0).sum()),
        total_pl=('P/L', 'sum'),
        average_pl=('P/L', 'mean'),
        max_win=('P/L', lambda x: x[x > 0].max()),
        max_loss=('P/L', lambda x: x[x < 0].min()),
    ).reset_index()

    fig = setup_base_figure()

    fig.add_trace(go.Scatter(
        x=monthly_summary['Month'],
        y=monthly_summary['total_trades'],
        mode='lines+markers',
        name='Total Trades',
        line=dict(color=COLORS['default'], width=2),
        marker=dict(size=8)
    ))

    fig.add_trace(go.Scatter(
        x=monthly_summary['Month'],
        y=monthly_summary['winning_trades'],
        mode='lines+markers',
        name='Winning Trades',
        line=dict(color=COLORS['profit'], width=2),
        marker=dict(size=8)
    ))

    fig.add_trace(go.Scatter(
        x=monthly_summary['Month'],
        y=monthly_summary['losing_trades'],
        mode='lines+markers',
        name='Losing Trades',
        line=dict(color=COLORS['loss'], width=2),
        marker=dict(size=8)
    ))

    fig.add_trace(go.Scatter(
        x=monthly_summary['Month'],
        y=monthly_summary['total_pl'],
        mode='lines+markers',
        name='Total P/L',
        line=dict(color=COLORS['highlight'], width=2, dash='dash'),
        marker=dict(size=8)
    ))

    fig.update_layout(
        title='Monthly Trading Summary',
        xaxis_title='Month',
        yaxis_title='Count / P/L',
        legend_title='Metrics',
        xaxis=dict(tickformat='%Y-%m'),
        yaxis_tickprefix='',
        yaxis_ticksuffix='',
    )

    fig = apply_standard_layout(fig, "Monthly Trading Summary")

    return fig