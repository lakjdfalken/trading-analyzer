from .base import get_trading_data, apply_standard_layout, setup_base_figure, format_currency
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from settings import COLORS
import logging
import pandas as pd
from logger import setup_logger

logger = logging.getLogger(__name__)

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
        plot_bgcolor='white',    # Set plot background to white
        paper_bgcolor='white',
        annotations=annotations
    )
    
    fig.update_yaxes(title_text="P/L (%)", row=1, col=1, automargin=True, showgrid=True, gridwidth=1, gridcolor='LightGray')
    fig.update_yaxes(title_text="Number of Trades", row=2, col=1, automargin=True, showgrid=True, gridwidth=1, gridcolor='LightGray')
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='LightGray')
    
    return fig
def create_daily_pl(df):
    info_text = (
        "Daily P/L Calculation:<br><br>"
        "- Long positions: Sum of profits/losses from buy trades<br>"
        "- Short positions: Sum of profits/losses from sell trades<br>"
        "- Percentages calculated against daily starting balance"
    )
    
    fig = setup_base_figure()

    trading_df = get_trading_data(df)
    trading_df = trading_df.sort_values('Transaction Date')
    
    logger.debug(f"\nFull trading data sample:\n{trading_df[['Transaction Date', 'Action', 'Description', 'Amount', 'Balance', 'P/L']].head()}")
    daily_pl = trading_df.groupby(trading_df['Transaction Date'].dt.date)['P/L'].sum() 
    daily_balances = {}
    
    for date in sorted(trading_df['Transaction Date'].dt.date.unique()):
        day_data = trading_df[trading_df['Transaction Date'].dt.date == date]
        
        logger.debug(f"\nDetailed day data for {date}:")
        logger.debug(f"All transactions:\n{day_data[['Transaction Date', 'Action', 'Description', 'Amount', 'Balance', 'P/L']]}")
        
        day_first_balance = day_data['Balance'].iloc[0]
        day_first_pl = day_data['P/L'].iloc[0]
        day_initial_balance = day_first_balance - day_first_pl
        
        daily_balances[date] = day_initial_balance
        
        logger.debug(f"Day's first balance: {day_first_balance}")
        logger.debug(f"Day's first P/L: {day_first_pl}")
        logger.debug(f"Day's initial balance: {day_initial_balance}")
        
        day_total_pl = day_data['P/L'].sum()
        ending_balance = day_initial_balance + day_total_pl
        logger.debug(f"Day's total P/L: {day_total_pl}")
        logger.debug(f"Day's ending balance: {ending_balance}")
    
    logger.debug(f"\nFinal daily balances:\n{daily_balances}")
    
    # Calculate daily P/L for long and short positions
    long_pl = trading_df[trading_df['Amount'] > 0].groupby(
        trading_df['Transaction Date'].dt.date)['P/L'].sum()
    short_pl = trading_df[trading_df['Amount'] < 0].groupby(
        trading_df['Transaction Date'].dt.date)['P/L'].sum()
    
    logger.debug(f"\nRaw long P/L:\n{long_pl}")
    logger.debug(f"Raw short P/L:\n{short_pl}")
    
    # Calculate percentages using correct daily balances
    long_pl_pct = pd.Series({date: (pl / daily_balances[date]) * 100 
                            for date, pl in long_pl.items()})
    short_pl_pct = pd.Series({date: (pl / daily_balances[date]) * 100 
                             for date, pl in short_pl.items()})
    
    logger.debug(f"\nDaily long P/L percentages:\n{long_pl_pct}")
    logger.debug(f"Daily short P/L percentages:\n{short_pl_pct}")
    
    total_long_pct = long_pl_pct.sum()
    total_short_pct = short_pl_pct.sum()
    total_pl_pct = total_long_pct + total_short_pct
    
    logger.debug(f"\nTotal long percentage: {total_long_pct}%")
    logger.debug(f"Total short percentage: {total_short_pct}%")
    logger.debug(f"Total P/L percentage: {total_pl_pct}%")
    all_dates = sorted(set(long_pl_pct.index) | set(short_pl_pct.index))
    avg_daily_pct = (total_pl_pct / len(all_dates))
    trading_days = len(all_dates)
    
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

    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='LightGray')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='LightGray')

    # Final layout update with toggleable info button
    fig.update_layout(
        barmode='group',
        bargap=0.15,
        bargroupgap=0.05,
        showlegend=True,
        xaxis=dict(showgrid=False, zeroline=False),
        margin=dict(t=50, b=50),
        plot_bgcolor='white',
        paper_bgcolor='white',
        updatemenus=[dict(
            type="buttons",
            direction="left",
            active=-1,
            buttons=[dict(
                args=[{"annotations[0].visible": True}],
                args2=[{"annotations[0].visible": False}],
                label="ⓘ",
                method="relayout"
            )],
            x=0.98,
            y=0.98,
            xanchor="right",
            yanchor="top",
            bgcolor="white",
            bordercolor="black",
            borderwidth=1,
            showactive=False
        )],
        annotations=[
          dict(
            text=info_text,
            x=0.5,
            y=0.5,
            xref="paper",
            yref="paper",
            showarrow=False,
            bgcolor="white",
            bordercolor="black",
            borderwidth=1,
            visible=False
          ),
          dict(
            text=(f'Total Long: {total_long_pct:.1f}%<br>'
              f'Total Short: {total_short_pct:.1f}%<br>'
              f'Total P/L: {total_pl_pct:.1f}%<br>'
              f'Avg Daily P/L: {avg_daily_pct:.1f}%<br>'
              f'Trading Days: {trading_days}'),
            xref='paper', 
            yref='paper',
            x=0.02, 
            y=0.98,
            showarrow=False,
            bgcolor='white',
            bordercolor='gray',
            borderwidth=1
          ),
        ]
    )
    return fig