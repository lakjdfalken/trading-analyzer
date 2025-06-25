import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from .base import get_trading_pl_without_funding, format_currency
from settings import COLORS, BROKERS
import logging

logger = logging.getLogger(__name__)

def get_tax_overview_data(df, selected_year=None, selected_broker=None):
    """
    Get trading data organized for tax declaration purposes
    Returns data grouped by broker, market, and year with P/L summaries
    """
    # Get clean trading data without funding
    trading_df = get_trading_pl_without_funding(df)
    
    # Convert to datetime if needed
    if not pd.api.types.is_datetime64_any_dtype(trading_df['Transaction Date']):
        trading_df['Transaction Date'] = pd.to_datetime(trading_df['Transaction Date'])
    
    # Add year column
    trading_df['Year'] = trading_df['Transaction Date'].dt.year
    
    # Filter by selected year if provided
    if selected_year:
        trading_df = trading_df[trading_df['Year'] == selected_year]
    
    # Filter by selected broker if provided
    if selected_broker and selected_broker != 'All':
        trading_df = trading_df[trading_df['broker_name'] == selected_broker]
    
    # Group by broker, market, currency, and year
    tax_summary = trading_df.groupby([
        'broker_name', 'Description', 'Currency', 'Year'
    ]).agg({
        'P/L': ['sum', 'count'],
        'Transaction Date': ['min', 'max']
    }).round(2)
    
    # Flatten column names
    tax_summary.columns = ['Total_PL', 'Trade_Count', 'First_Trade', 'Last_Trade']
    tax_summary = tax_summary.reset_index()
    
    # Separate wins and losses
    tax_summary['Wins'] = tax_summary['Total_PL'].apply(lambda x: x if x > 0 else 0)
    tax_summary['Losses'] = tax_summary['Total_PL'].apply(lambda x: abs(x) if x < 0 else 0)
    
    # Add broker display name
    tax_summary['Broker_Display'] = tax_summary['broker_name'].map(BROKERS)
    
    return tax_summary

def create_tax_overview_table(df, selected_year=None, selected_broker=None):
    """
    Create a comprehensive tax overview table
    """
    tax_data = get_tax_overview_data(df, selected_year, selected_broker)
    
    if tax_data.empty:
        # Create empty figure with message
        fig = go.Figure()
        broker_text = f" for {BROKERS.get(selected_broker, selected_broker)}" if selected_broker and selected_broker != 'All' else ""
        year_text = f" for {selected_year}" if selected_year else ""
        fig.add_annotation(
            text=f"No trading data found{broker_text}{year_text}",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(size=16)
        )
        fig.update_layout(
            title=f"Tax Overview{broker_text} - {selected_year if selected_year else 'All Years'}",
            template='plotly_white'
        )
        return fig
    
    # Create table data
    table_data = []
    headers = ['Broker', 'Market', 'Currency', 'Year', 'Total P/L', 'Wins', 'Losses', 'Trades', 'Period']
    
    for _, row in tax_data.iterrows():
        period = f"{row['First_Trade'].strftime('%Y-%m-%d')} to {row['Last_Trade'].strftime('%Y-%m-%d')}"
        table_data.append([
            row['Broker_Display'],
            row['Description'],
            row['Currency'],
            str(int(row['Year'])),
            format_currency(row['Total_PL'], row['Currency']),
            format_currency(row['Wins'], row['Currency']),
            format_currency(row['Losses'], row['Currency']),
            str(int(row['Trade_Count'])),
            period
        ])
    
    # Create table
    fig = go.Figure(data=[go.Table(
        header=dict(
            values=headers,
            fill_color='lightblue',
            align='center',
            font=dict(size=12, color='black')
        ),
        cells=dict(
            values=list(zip(*table_data)) if table_data else [[] for _ in headers],
            fill_color=[['white', 'lightgray'] * (len(table_data) // 2 + 1)],
            align='center',
            font=dict(size=11)
        )
    )])
    
    # Add summary statistics
    total_pl_by_currency = tax_data.groupby('Currency')['Total_PL'].sum()
    total_wins_by_currency = tax_data.groupby('Currency')['Wins'].sum()
    total_losses_by_currency = tax_data.groupby('Currency')['Losses'].sum()
    
    summary_text = "Summary by Currency:<br>"
    for currency in total_pl_by_currency.index:
        summary_text += f"{currency}: Total P/L: {format_currency(total_pl_by_currency[currency], currency)}, "
        summary_text += f"Wins: {format_currency(total_wins_by_currency[currency], currency)}, "
        summary_text += f"Losses: {format_currency(total_losses_by_currency[currency], currency)}<br>"
    
    fig.add_annotation(
        text=summary_text,
        xref="paper", yref="paper",
        x=0.02, y=-0.1,
        showarrow=False,
        bgcolor="lightyellow",
        bordercolor="black",
        borderwidth=1,
        font=dict(size=10)
    )
    
    # Update title to reflect broker selection
    broker_text = f" - {BROKERS.get(selected_broker, selected_broker)}" if selected_broker and selected_broker != 'All' else ""
    fig.update_layout(
        title=f"Tax Declaration Overview{broker_text} - {selected_year if selected_year else 'All Years'}",
        template='plotly_white',
        height=600,
        margin=dict(b=100)  # Extra bottom margin for summary
    )
    
    return fig

def create_yearly_summary_chart(df, selected_broker=None):
    """
    Create a yearly summary chart showing P/L by broker and currency
    """
    tax_data = get_tax_overview_data(df, selected_broker=selected_broker)
    
    if tax_data.empty:
        fig = go.Figure()
        broker_text = f" for {BROKERS.get(selected_broker, selected_broker)}" if selected_broker and selected_broker != 'All' else ""
        fig.add_annotation(
            text=f"No trading data available{broker_text}",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(size=16)
        )
        return fig
    
    # Group by year, broker, and currency
    yearly_summary = tax_data.groupby(['Year', 'Broker_Display', 'Currency'])['Total_PL'].sum().reset_index()
    
    # Create subplots for each currency
    currencies = yearly_summary['Currency'].unique()
    fig = make_subplots(
        rows=len(currencies), cols=1,
        subplot_titles=[f"P/L by Year - {currency}" for currency in currencies],
        vertical_spacing=0.1
    )
    
    for i, currency in enumerate(currencies, 1):
        currency_data = yearly_summary[yearly_summary['Currency'] == currency]
        
        for broker in currency_data['Broker_Display'].unique():
            broker_data = currency_data[currency_data['Broker_Display'] == broker]
            
            fig.add_trace(
                go.Bar(
                    name=f"{broker} ({currency})",
                    x=broker_data['Year'],
                    y=broker_data['Total_PL'],
                    text=[format_currency(v, currency) for v in broker_data['Total_PL']],
                    textposition='auto',
                    marker_color=[COLORS['profit'] if x >= 0 else COLORS['loss'] for x in broker_data['Total_PL']],
                    hovertemplate=f'<b>{broker}</b><br>Year: %{{x}}<br>P/L: %{{text}}<extra></extra>',
                    showlegend=(i == 1)  # Only show legend for first subplot
                ),
                row=i, col=1
            )
    
    # Update title to reflect broker selection
    broker_text = f" - {BROKERS.get(selected_broker, selected_broker)}" if selected_broker and selected_broker != 'All' else ""
    fig.update_layout(
        title=f"Yearly P/L Summary by Broker and Currency{broker_text}",
        template='plotly_white',
        height=300 * len(currencies),
        barmode='group'
    )
    
    return fig

def get_available_years(df):
    """
    Get list of available years from the trading data
    """
    try:
        trading_df = get_trading_pl_without_funding(df)
        if trading_df.empty:
            return []
        
        if not pd.api.types.is_datetime64_any_dtype(trading_df['Transaction Date']):
            trading_df['Transaction Date'] = pd.to_datetime(trading_df['Transaction Date'])
        
        years = sorted(trading_df['Transaction Date'].dt.year.unique(), reverse=True)
        return [int(year) for year in years]
    except Exception as e:
        logger.error(f"Error getting available years: {e}")
        return []