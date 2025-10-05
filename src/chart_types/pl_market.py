import numpy as np
import pandas as pd
from .base import (prepare_dataframe, format_currency, setup_base_figure, 
                   apply_standard_layout, get_trading_data, get_trading_pl_without_funding)
from settings import COLORS
import plotly.graph_objects as go
from plotly.subplots import make_subplots

def get_market_data(df):
    """Returns dataframe filtered for market transactions with funding impacts removed"""
    # Use get_trading_pl_without_funding which already removes funding impacts
    trading_df = get_trading_pl_without_funding(df)
    
    # Further exclude any non-market transactions that might still be in the data
    excluded_patterns = [
        'Fee',
        'Payable',
        'Interest',
        'Online Transfer'
    ]
    pattern = '|'.join(excluded_patterns)
    market_df = trading_df[~trading_df['Description'].str.contains(pattern, case=False, na=False)]
    
    return market_df

def create_market_actions(df, account_id=None):
    """Create market actions chart with account filtering"""
    # Filter by account if specified
    if account_id and account_id != "all":
        df = df[df['account_id'] == account_id]
    # Use get_trading_pl_without_funding for consistent data handling
    trading_df = get_trading_pl_without_funding(df)
    
    # Convert to datetime if needed
    if not pd.api.types.is_datetime64_any_dtype(trading_df['Transaction Date']):
        trading_df['Transaction Date'] = pd.to_datetime(trading_df['Transaction Date'])
    
    # Get base figure with fluid layout
    fig = setup_base_figure()
    
    # Process and add data
    daily_actions = trading_df.groupby([trading_df['Transaction Date'].dt.date, 'Action']).size().unstack(fill_value=0)
    averages = daily_actions.mean()
    
    for action in daily_actions.columns:
        fig.add_trace(go.Bar(
            name=action,
            x=daily_actions.index,
            y=daily_actions[action],
            text=daily_actions[action],
            textposition='auto',
        ))
        
    # Apply common styling
    fig = apply_standard_layout(fig, "Market Actions")
    
    return fig

def create_market_pl(df):
    # Use the improved get_market_data function which uses get_trading_pl_without_funding
    market_df = get_market_data(df)
    
    # Group by Description and Currency, maintaining sign for P/L values
    market_pl = market_df.groupby(['Description', 'Currency'])['P/L'].sum().reset_index()
    market_pl = market_pl.sort_values('P/L')
    
    # Calculate total P/L per currency
    total_pl = market_df.groupby('Currency')['P/L'].sum()
    
    # Create modern bar chart
    fig = go.Figure(data=[
        go.Bar(
            x=market_pl['Description'],
            y=market_pl['P/L'],
            text=[format_currency(v, c) for v, c in zip(market_pl['P/L'], market_pl['Currency'])],
            textposition='auto',
            marker_color=[COLORS['loss'] if x < 0 else COLORS['profit'] for x in market_pl['P/L']],
            hovertemplate='<b>%{x}</b><br>P/L: %{text}<extra></extra>'
        )
    ])
    
    # Add win/loss statistics
    win_loss_stats = calculate_win_loss_stats(market_df)
    stats_text = "<br>".join([f"{k}: {v}" for k, v in win_loss_stats.items()])
    
    fig.add_annotation(
        text=f"Win/Loss Stats<br>{stats_text}",
        xref="paper", yref="paper",
        x=0.02, y=0.78,  # Positioned below total P/L
        showarrow=False,
        bgcolor="white",
        bordercolor="black",
        borderwidth=1
    )
    
    # Add total P/L annotation
    totals_text = "<br>".join([f"{curr}: {format_currency(pl, curr)}" 
                              for curr, pl in total_pl.items()])
    
    fig.add_annotation(
        text=f"Total P/L<br>{totals_text}",
        xref="paper", yref="paper",
        x=0.02, y=0.98,
        showarrow=False,
        bgcolor="white",
        bordercolor="black",
        borderwidth=1
    )
    
    fig.update_layout(
        title='Market Profit/Loss Analysis',
        xaxis_title='Markets',
        yaxis_title='Total P/L',
        template='plotly_white',
        showlegend=False
    )
    
    return fig

def calculate_win_loss_stats(market_df):
    """Calculate detailed win/loss statistics from market data"""
    # For individual trades, we need to look at each row, not grouped data
    # Each row should represent a single trade
    
    # Separate wins and losses
    wins = market_df[market_df['P/L'] > 0]
    losses = market_df[market_df['P/L'] < 0]
    
    # Create a dictionary to store all statistics
    stats = {}
    
    # 1. Win rate calculation
    total_trades = len(market_df)
    win_count = len(wins)
    loss_count = len(losses)
    
    if total_trades > 0:
        win_rate = (win_count / total_trades) * 100
        stats["Win Rate"] = f"{win_rate:.2f}%"
    else:
        stats["Win Rate"] = "N/A"
    
    # 2. Total wins vs total losses
    total_wins = wins['P/L'].sum()
    total_losses = losses['P/L'].sum()
    
    # Group by currency for proper formatting
    wins_by_currency = wins.groupby('Currency')['P/L'].sum()
    losses_by_currency = losses.groupby('Currency')['P/L'].sum()
    
    # Format the wins and losses by currency
    wins_text = ", ".join([f"{format_currency(v, c)}" for c, v in wins_by_currency.items()])
    losses_text = ", ".join([f"{format_currency(abs(v), c)}" for c, v in losses_by_currency.items()])
    
    stats["Total Wins"] = wins_text if not wins_by_currency.empty else "0"
    stats["Total Losses"] = losses_text if not losses_by_currency.empty else "0"
    
    # 3. Average win amount vs average loss amount
    avg_win_by_currency = {}
    avg_loss_by_currency = {}
    
    for currency in market_df['Currency'].unique():
        currency_wins = wins[wins['Currency'] == currency]
        currency_losses = losses[losses['Currency'] == currency]
        
        if not currency_wins.empty:
            avg_win = currency_wins['P/L'].mean()
            avg_win_by_currency[currency] = avg_win
        
        if not currency_losses.empty:
            avg_loss = currency_losses['P/L'].mean()
            avg_loss_by_currency[currency] = avg_loss
    
    avg_win_text = ", ".join([f"{format_currency(v, c)}" for c, v in avg_win_by_currency.items()])
    avg_loss_text = ", ".join([f"{format_currency(abs(v), c)}" for c, v in avg_loss_by_currency.items()])
    
    stats["Avg Win"] = avg_win_text if avg_win_text else "N/A"
    stats["Avg Loss"] = avg_loss_text if avg_loss_text else "N/A"
    
    # 4. Win/Loss ratio (Absolute ratio of average win to average loss)
    for currency in set(avg_win_by_currency.keys()).intersection(set(avg_loss_by_currency.keys())):
        if currency in avg_loss_by_currency and avg_loss_by_currency[currency] != 0:
            ratio = abs(avg_win_by_currency[currency] / avg_loss_by_currency[currency])
            if 'Win/Loss Ratio' not in stats:
                stats['Win/Loss Ratio'] = f"{currency}: {ratio:.2f}"
            else:
                stats['Win/Loss Ratio'] += f", {currency}: {ratio:.2f}"
    
    if 'Win/Loss Ratio' not in stats:
        stats['Win/Loss Ratio'] = "N/A"
    
    return stats

def create_win_loss_analysis(df):
    """Creates a detailed win/loss analysis chart with statistics"""
    # Get market data
    market_df = get_market_data(df)
    
    # Calculate win/loss statistics
    stats = calculate_win_loss_stats(market_df)
    
    # Count wins and losses by market
    market_wins = market_df[market_df['P/L'] > 0].groupby('Description').size()
    market_losses = market_df[market_df['P/L'] < 0].groupby('Description').size()
    
    # Get all unique markets
    all_markets = pd.Series(pd.concat([market_wins.index, market_losses.index]).unique())
    
    # Create a dataframe for the chart
    chart_df = pd.DataFrame({
        'Market': all_markets,
        'Wins': market_wins.reindex(all_markets).fillna(0).astype(int),
        'Losses': market_losses.reindex(all_markets).fillna(0).astype(int)
    })
    
    # Calculate win rate per market
    chart_df['Win Rate'] = (chart_df['Wins'] / (chart_df['Wins'] + chart_df['Losses']) * 100).round(2)
    chart_df = chart_df.sort_values('Win Rate', ascending=False)
    
    # Create figure with two subplots
    fig = make_subplots(
        rows=2, cols=1, 
        row_heights=[0.7, 0.3],
        subplot_titles=["Win/Loss Count by Market", "Win Rate by Market"]
    )
    
    # Add win/loss count bars
    fig.add_trace(
        go.Bar(
            name="Wins",
            x=chart_df['Market'],
            y=chart_df['Wins'],
            marker_color=COLORS['profit'],
            hovertemplate='<b>%{x}</b><br>Wins: %{y}<extra></extra>'
        ), 
        row=1, col=1
    )
    
    fig.add_trace(
        go.Bar(
            name="Losses",
            x=chart_df['Market'],
            y=chart_df['Losses'],
            marker_color=COLORS['loss'],
            hovertemplate='<b>%{x}</b><br>Losses: %{y}<extra></extra>'
        ), 
        row=1, col=1
    )
    
    # Add win rate line
    fig.add_trace(
        go.Scatter(
            name="Win Rate",
            x=chart_df['Market'],
            y=chart_df['Win Rate'],
            mode='lines+markers',
            marker=dict(size=10, color='rgba(0, 128, 128, 0.8)'),
            line=dict(width=3, color='rgba(0, 128, 128, 0.8)'),
            hovertemplate='<b>%{x}</b><br>Win Rate: %{y:.2f}%<extra></extra>'
        ),
        row=2, col=1
    )
    
    # Add win/loss statistics annotation
    stats_text = "<br>".join([f"{k}: {v}" for k, v in stats.items()])
    
    fig.add_annotation(
        text=f"Win/Loss Stats<br>{stats_text}",
        xref="paper", yref="paper",
        x=0.02, y=0.98,
        showarrow=False,
        bgcolor="white",
        bordercolor="black",
        borderwidth=1
    )
    
    # Update layout
    fig.update_layout(
        title='Win/Loss Analysis by Market',
        barmode='group',
        template='plotly_white',
        height=800,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    # Update axes
    fig.update_xaxes(title_text="Market", row=1, col=1)
    fig.update_yaxes(title_text="Count", row=1, col=1)
    fig.update_xaxes(title_text="Market", row=2, col=1)
    fig.update_yaxes(title_text="Win Rate (%)", row=2, col=1)
    
    return fig
