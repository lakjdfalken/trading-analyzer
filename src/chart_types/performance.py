from .base import get_trading_data, apply_common_styling, setup_base_figure, format_currency
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from settings import COLORS

def create_daily_pl_vs_trades(df):
    trading_df = get_trading_data(df)
    initial_balance = trading_df['Balance'].iloc[0]
    
    # Calculate daily metrics
    daily_pl = trading_df.groupby(trading_df['Transaction Date'].dt.date)['P/L'].sum()
    daily_pl_pct = (daily_pl / abs(initial_balance)) * 100
    daily_trades = trading_df.groupby(trading_df['Transaction Date'].dt.date).size()
    
    # Calculate correlation
    correlation = daily_pl_pct.corr(daily_trades)
    
    # Create figure with secondary y-axis
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    # Add P/L bars
    fig.add_trace(
        go.Bar(
            x=daily_pl_pct.index,
            y=daily_pl_pct.values,
            name="Daily P/L %",
            marker_color=[COLORS['profit'] if x >= 0 else COLORS['loss'] for x in daily_pl_pct],
            text=[f"{x:.1f}%" for x in daily_pl_pct],
            textposition='outside'
        ),
        secondary_y=False
    )
    
    # Add trade count line
    fig.add_trace(
        go.Scatter(
            x=daily_trades.index,
            y=daily_trades.values,
            name="Trade Count",
            line=dict(color=COLORS['trading'][1]),
            text=daily_trades.values,
            textposition='top center'
        ),
        secondary_y=True
    )
    
    # Add correlation annotation
    fig.add_annotation(
        text=f'Correlation: {correlation:.2f}',
        xref='paper', yref='paper',
        x=0.02, y=0.98,
        showarrow=False,
        bgcolor='white',
        bordercolor='gray',
        borderwidth=1
    )
    
    # Update layout
    fig.update_layout(
        title='Daily P/L vs Trade Count',
        xaxis_title='Date',
        margin=dict(t=100, b=100),
        barmode='group'
    )
    
    # Update y-axes labels
    fig.update_yaxes(title_text="Daily P/L (%)", secondary_y=False)
    fig.update_yaxes(title_text="Trade Count", secondary_y=True)
    
    return fig

def create_daily_pl(df):
    trading_df = get_trading_data(df)
    initial_balance = trading_df['Balance'].iloc[0]
    
    # Calculate daily P/L for long and short positions
    long_pl = trading_df[trading_df['Amount'] > 0].groupby(
        trading_df['Transaction Date'].dt.date)['P/L'].sum()
    short_pl = trading_df[trading_df['Amount'] < 0].groupby(
        trading_df['Transaction Date'].dt.date)['P/L'].sum()
    
    # Convert to percentage of initial balance
    long_pl_pct = (long_pl / abs(initial_balance)) * 100
    short_pl_pct = (short_pl / abs(initial_balance)) * 100
    
    # Get all unique dates
    all_dates = sorted(set(long_pl_pct.index) | set(short_pl_pct.index))
    
    # Create figure
    fig = setup_base_figure()
    
    # Add long position bars
    fig.add_trace(go.Bar(
        x=all_dates,
        y=[long_pl_pct.get(date, 0) for date in all_dates],
        name='Long P/L',
        marker_color=COLORS['profit'],
        text=[f"{long_pl_pct.get(date, 0):.1f}%" for date in all_dates],
        textposition='outside'
    ))
    
    # Add short position bars
    fig.add_trace(go.Bar(
        x=all_dates,
        y=[short_pl_pct.get(date, 0) for date in all_dates],
        name='Short P/L',
        marker_color=COLORS['loss'],
        text=[f"{short_pl_pct.get(date, 0):.1f}%" for date in all_dates],
        textposition='outside'
    ))
    
    # Calculate and add summary statistics
    total_long = sum(long_pl_pct)
    total_short = sum(short_pl_pct)
    total_return = total_long + total_short
    
    summary_text = (
        f'Total Return: {total_return:.1f}%<br>'
        f'Long: {total_long:.1f}%<br>'
        f'Short: {total_short:.1f}%'
    )
    
    fig.add_annotation(
        text=summary_text,
        xref='paper', yref='paper',
        x=0.02, y=0.98,
        showarrow=False,
        bgcolor='white',
        bordercolor='gray',
        borderwidth=1
    )
    
    # Update layout
    fig.update_layout(
        barmode='relative',
        title='Daily P/L Performance - Long vs Short',
        xaxis_title='Date',
        yaxis_title='Daily P/L (%)',
        margin=dict(t=100, b=100),
        xaxis_tickangle=45
    )
    
    return fig