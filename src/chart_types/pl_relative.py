import plotly.graph_objects as go
import chart_types.base as base
from .base import (
    get_trading_data,
    setup_base_figure,
    apply_standard_layout,
    find_date_col,
    find_pl_col,
    coerce_date,
    coerce_pl_numeric,
    ensure_market_column,
    aggregate_pl_by_period,
    top_markets_by_pl,
)
import logging
import pandas as pd

logger = logging.getLogger(__name__)

def create_relative_pl(df):
    dfc = base.get_filtered_trading_df(df)
    if dfc is None:
        dfc = pd.DataFrame()
    if dfc.empty:
        return setup_base_figure()

    info_text = (
        "Relative P/L Calculation:<br><br>"
        "Sum of profits/losses from all trades during the<br>"
        "period selected. Only actual positions are calculated.<br>"
        "Only trades that have been closed are included in the<br>"
        "calculation. The P/L is calculated as the difference<br>"
        "between the close price and the open price of the trade."
    )

    fig = setup_base_figure()
    trading_data = get_trading_data(dfc)
    
    trading_data = trading_data.sort_values('Transaction Date')
    
    # Calculate metrics
    total_pl = trading_data['P/L'].sum()
    days_traded = len(trading_data['Transaction Date'].dt.date.unique())
    daily_average = total_pl / days_traded if days_traded > 0 else 0
    
    # Calculate cumulative P/L
    trading_data['Cumulative P/L'] = trading_data['P/L'].cumsum()
    
    # Add metrics to plot
    fig.add_trace(go.Scatter(
        x=trading_data['Transaction Date'],
        y=trading_data['Cumulative P/L'],
        mode='lines+markers',
        name='Cumulative P/L',
        hovertemplate='Date: %{x}<br>Cumulative P/L: %{y:.2f}<extra></extra>'
    ))
    
    # DO NOT add the first annotation here - we'll do it in update_layout
    
    fig = apply_standard_layout(fig, "Relative P/L Over Time")

    # Add all annotations in the update_layout call
    fig.update_layout(
        updatemenus=[dict(
            type="buttons",
            direction="left",
            active=-1,
            buttons=[dict(
                args=[{"annotations[0].visible": True}],
                args2=[{"annotations[0].visible": False}],
                label="ⓘ",
                method="relayout"  # Either update or relayout should work
            )],
            x=0.98,
            y=1.05,
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
                xref='paper', yref='paper',
                x=0.5, y=0.5,
                showarrow=False,
                bgcolor='white',
                bordercolor='black',
                borderwidth=1,
                visible=False  # Start as invisible
            ),
            dict(
                text=f'Total P/L: {total_pl:.2f}<br>Daily Average: {daily_average:.2f}',
                xref='paper', yref='paper',
                x=0.92, y=0.08,
                showarrow=False,
                bgcolor='white',
                bordercolor='black',
                borderwidth=1
            )
        ]
    )
    
    return fig