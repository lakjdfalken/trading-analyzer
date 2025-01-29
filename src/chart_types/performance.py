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
    
    # Calculate totals
    total_pl_pct = daily_pl_pct.sum()
    total_trades = daily_trades.sum()
    correlation = daily_pl_pct.corr(daily_trades)
    
    fig = make_subplots(
        rows=2, 
        cols=1,
        subplot_titles=('Daily P/L %', 'Daily Trade Count'),
        vertical_spacing=0.12
    )
    
    # Add P/L bars with auto-adjusting text
    fig.add_trace(
        go.Bar(
            x=daily_pl_pct.index,
            y=daily_pl_pct.values,
            name="Daily P/L %",
            marker_color=[COLORS['profit'] if x >= 0 else COLORS['loss'] for x in daily_pl_pct],
            text=[f"{x:.1f}%" for x in daily_pl_pct],
            textposition='auto',
            cliponaxis=False
        ),
        row=1, col=1
    )
    
    # Add trade count bars
    fig.add_trace(
        go.Bar(
            x=daily_trades.index,
            y=daily_trades.values,
            name="Trade Count",
            marker_color=COLORS['trading'][1],
            text=daily_trades.values,
            textposition='auto',
            cliponaxis=False
        ),
        row=2, col=1
    )
    
    # Add annotations for totals and correlation
    annotations = [
        dict(
            text=f'Total P/L: {total_pl_pct:.1f}%',
            xref='paper', 
            yref='paper',
            x=0.02, 
            y=0.98,
            showarrow=False,
            bgcolor='white',
            bordercolor='gray',
            borderwidth=1
        ),
        dict(
            text=f'Correlation: {correlation:.2f}',
            xref='paper', 
            yref='paper',
            x=0.02, 
            y=0.90,
            showarrow=False,
            bgcolor='white',
            bordercolor='gray',
            borderwidth=1
        ),
        dict(
            text=f'Total Trades: {total_trades}',
            xref='paper', 
            yref='paper',
            x=0.02, 
            y=0.45,
            showarrow=False,
            bgcolor='white',
            bordercolor='gray',
            borderwidth=1
        )
    ]
    
    fig.update_layout(
        showlegend=False,
        margin=dict(t=50, b=50, l=50, r=50),
        bargap=0.15,
        autosize=True,
        annotations=annotations
    )
    
    fig.update_yaxes(title_text="P/L (%)", row=1, col=1, automargin=True)
    fig.update_yaxes(title_text="Number of Trades", row=2, col=1, automargin=True)
    
    return fig
def create_daily_pl(df):
    trading_df = get_trading_data(df)
    initial_balance = trading_df['Balance'].iloc[0]
    
    # Calculate daily P/L for long and short positions
    long_pl = trading_df[trading_df['Amount'] > 0].groupby(
        trading_df['Transaction Date'].dt.date)['P/L'].sum()
    short_pl = trading_df[trading_df['Amount'] < 0].groupby(
        trading_df['Transaction Date'].dt.date)['P/L'].sum()
    
    # Calculate total P/L first (actual profit/loss)
    total_pl = long_pl.sum() + short_pl.sum()
    total_pl_pct = (total_pl / abs(initial_balance)) * 100
    
    # Convert to percentage for display
    long_pl_pct = (long_pl / abs(initial_balance)) * 100
    short_pl_pct = abs((short_pl / abs(initial_balance)) * 100)
    total_long_pct = long_pl_pct.sum()
    total_short_pct = short_pl_pct.sum()
    
    all_dates = sorted(set(long_pl_pct.index) | set(short_pl_pct.index))
    
    fig = go.Figure()

    # Add long position bars
    fig.add_trace(go.Bar(
        x=all_dates,
        y=[long_pl_pct.get(date, 0) for date in all_dates],
        name='Long P/L',
        marker_color=COLORS['profit'],
        text=[f"{long_pl_pct.get(date, 0):.1f}%" for date in all_dates],
        textposition='auto',
        cliponaxis=False
    ))
    
    # Add short position bars
    fig.add_trace(go.Bar(
        x=all_dates,
        y=[short_pl_pct.get(date, 0) for date in all_dates],
        name='Short P/L',
        marker_color=COLORS['loss'],
        text=[f"{short_pl_pct.get(date, 0):.1f}%" for date in all_dates],
        textposition='auto',
        cliponaxis=False
    ))

    # Updated annotations to show true P/L
    annotations = [
        dict(
            text=f'Total Long: {total_long_pct:.1f}%',
            xref='paper', 
            yref='paper',
            x=0.02, 
            y=0.98,
            showarrow=False,
            bgcolor='white',
            bordercolor='gray',
            borderwidth=1
        ),
        dict(
            text=f'Total Short: {total_short_pct:.1f}%',
            xref='paper', 
            yref='paper',
            x=0.02, 
            y=0.90,
            showarrow=False,
            bgcolor='white',
            bordercolor='gray',
            borderwidth=1
        ),
        dict(
            text=f'Total P/L: {total_pl_pct:.1f}%',
            xref='paper', 
            yref='paper',
            x=0.02, 
            y=0.82,
            showarrow=False,
            bgcolor='white',
            bordercolor='gray',
            borderwidth=1,
            font=dict(size=13, weight='bold')
        )
    ]

    fig.update_layout(
        barmode='group',
        bargap=0.15,
        bargroupgap=0.05,
        showlegend=True,
        xaxis=dict(showgrid=False, zeroline=False),
        margin=dict(t=50, b=50),
        annotations=annotations
    )

    return fig