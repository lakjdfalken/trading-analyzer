from .base import get_trading_data, setup_base_figure, apply_standard_layout
import plotly.graph_objects as go
from settings import COLORS

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
        text=[f"{monthly_stats[m]['win_count']}<br>(+{monthly_stats[m]['win_pl']:.0f})" for m in months],
        textposition='inside',
        textfont=dict(color='white', size=12)
    ))
    
    # Add bars for losses
    fig.add_trace(go.Bar(
        name='Losses',
        x=months,
        y=[monthly_stats[m]['loss_count'] for m in months],
        marker_color=COLORS['loss'],
        text=[f"{monthly_stats[m]['loss_count']}<br>({monthly_stats[m]['loss_pl']:.0f})" for m in months],
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
    fig = apply_standard_layout(fig, "Monthly Win/Loss Distribution")
    
    return fig