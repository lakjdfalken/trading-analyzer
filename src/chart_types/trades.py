from .base import prepare_dataframe, get_trading_data, format_currency, setup_base_figure, apply_common_styling
import plotly.graph_objects as go
from settings import COLORS

def get_trade_distribution(df):
    """Returns trading day performance metrics"""
    trading_df = get_trading_data(df)
    daily_pl = trading_df.groupby(trading_df['Transaction Date'].dt.date)['P/L'].sum()
    
    return {
        'winning_days': len(daily_pl[daily_pl > 0]),
        'losing_days': len(daily_pl[daily_pl < 0]),
        'breakeven_days': len(daily_pl[daily_pl == 0])
    }

def create_distribution_days(df):
    distribution = get_trade_distribution(df)
    fig = setup_base_figure()
    
    data = [
        distribution['winning_days'],
        distribution['losing_days'],
        distribution['breakeven_days']
    ]
    labels = ['Winning Days', 'Losing Days', 'Breakeven Days']
    colors = [COLORS['profit'], COLORS['loss'], COLORS['neutral']]
    
    fig.add_trace(go.Pie(
        values=data,
        labels=labels,
        marker_colors=colors,
        textinfo='percent+label',
        hovertemplate='%{label}<br>Count: %{value}<br>%{percent}<extra></extra>'
    ))
    
    # Add summary annotation
    total_days = sum(data)
    win_rate = (distribution['winning_days'] / total_days * 100) if total_days > 0 else 0
    
    summary_text = (
        f'Total Trading Days: {total_days}<br>'
        f'Win Rate: {win_rate:.1f}%'
    )
    
    fig.add_annotation(
        text=summary_text,
        xref='paper', yref='paper',
        x=1.2, y=0,
        showarrow=False,
        bgcolor='white',
        bordercolor='gray',
        borderwidth=1
    )
    
    fig.update_layout(
        showlegend=True,
        margin=dict(t=100, b=100, r=200)
    )
    
    apply_common_styling(fig, title='Trading Day Performance Distribution')
    return fig

def create_daily_trade_count(df):
    trading_df = get_trading_data(df)
    daily_trades = trading_df.groupby(trading_df['Transaction Date'].dt.date).size()
    avg_trades = daily_trades.mean()
    
    fig = setup_base_figure()
    
    # Add bar chart for daily trades
    fig.add_trace(go.Bar(
        x=list(daily_trades.index),
        y=daily_trades.values,
        name='Daily Trades',
        marker_color=COLORS['trading'][0],
        opacity=0.6
    ))
    
    # Add average line
    fig.add_trace(go.Scatter(
        x=list(daily_trades.index),
        y=[avg_trades] * len(daily_trades),
        name=f'Average ({avg_trades:.1f} trades/day)',
        line=dict(color=COLORS['trading'][1], dash='dash')
    ))
    
    # Add summary annotation
    summary_text = (
        f'Total Trades: {daily_trades.sum()}<br>'
        f'Average: {avg_trades:.1f} trades/day<br>'
        f'Max: {daily_trades.max()} trades/day'
    )
    
    fig.add_annotation(
        text=summary_text,
        xref='paper', yref='paper',
        x=1.02, y=1,
        showarrow=False,
        bgcolor='white',
        bordercolor='gray',
        borderwidth=1
    )
    
    fig.update_layout(
        barmode='overlay',
        margin=dict(r=200),
        xaxis_tickangle=45
    )
    
    apply_common_styling(
        fig,
        title='Daily Trading Volume',
        xlabel='Date',
        ylabel='Number of Trades'
    )
    
    return fig
