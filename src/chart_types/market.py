import numpy as np
import pandas as pd
from .base import prepare_dataframe, format_currency, setup_base_figure, apply_common_styling
from settings import COLORS
import plotly.graph_objects as go
from plotly.subplots import make_subplots

def get_market_data(df):
    """Returns dataframe filtered for market transactions"""
    df_copy = prepare_dataframe(df)
    return df_copy[~df_copy['Description'].str.contains('Online Transfer Cash', case=False, na=False)]

def create_market_actions(df):
    # Get base figure with fluid layout
    fig = setup_base_figure()
    
    # Process and add data
    daily_actions = df.groupby([df['Transaction Date'].dt.date, 'Action']).size().unstack(fill_value=0)
    averages = daily_actions.mean()
    
    for action in daily_actions.columns:
        fig.add_trace(go.Bar(
            name=action,
            x=daily_actions.index,
            y=daily_actions[action],
            text=daily_actions[action],
            textposition='auto',
        ))
        
        fig.add_trace(go.Scatter(
            name=f'Avg {action}',
            x=daily_actions.index,
            y=[averages[action]] * len(daily_actions),
            mode='lines',
            line=dict(dash='dash'),
            opacity=0.7
        ))
    
    # Apply common styling
    apply_common_styling(
        fig, 
        title='Daily Market Actions with Averages',
        xlabel='Date',
        ylabel='Number of Actions'
    )
    
    return fig

def create_market_pl(df):
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
