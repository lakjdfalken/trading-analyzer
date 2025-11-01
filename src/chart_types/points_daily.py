from .base import get_trading_data, setup_base_figure, apply_standard_layout
import plotly.graph_objects as go
from settings import COLORS
import logging
import re
import pandas as pd
from .base import (
    find_date_col,
    find_pl_col,
    coerce_date,
    coerce_pl_numeric,
    ensure_market_column,
    aggregate_pl_by_period,
    top_markets_by_pl,
)
try:
    from settings import COLORS, MARKET_POINT_MULTIPLIERS, DEFAULT_POINT_MULTIPLIER
except Exception:
    from settings import COLORS
    MARKET_POINT_MULTIPLIERS = {}
    DEFAULT_POINT_MULTIPLIER = 1.0

logger = logging.getLogger(__name__)

def create_points_daily(df):
    logger.debug("Starting points analysis")
    trading_data = get_trading_data(df)

    # basic guards
    if trading_data is None or not isinstance(trading_data, pd.DataFrame) or trading_data.empty:
        fig = setup_base_figure()
        fig = apply_standard_layout(fig, "Daily Points Won/Lost Analysis")
        return fig

    # Ensure Market column exists (always returns a DataFrame)
    trading_data = ensure_market_column(trading_data)

    # Normalize Transaction Date
    date_col = find_date_col(trading_data)
    if date_col:
        trading_data[date_col] = pd.to_datetime(trading_data[date_col], errors='coerce')
        trading_data = trading_data.rename(columns={date_col: 'Transaction Date'})
    else:
        trading_data['Transaction Date'] = pd.to_datetime(trading_data.get('Transaction Date'), errors='coerce')

    # Compute points per trade (calculate_points handles open/close checks)
    def calc_row_points(row):
        open_price = row.get('Opening') if 'Opening' in row.index else (row.get('Open') if 'Open' in row.index else None)
        close_price = row.get('Closing') if 'Closing' in row.index else (row.get('Close') if 'Close' in row.index else None)
        market = row.get('Market') if 'Market' in row.index else None
        action = row.get('Action') if 'Action' in row.index else None
        return calculate_points(open_price, close_price, market, action)

    trading_data = trading_data.copy()
    trading_data['Points'] = trading_data.apply(lambda r: calc_row_points(r), axis=1)

    # Group by day and sum points
    trading_data['Date'] = pd.to_datetime(trading_data['Transaction Date']).dt.date
    daily_points = trading_data.groupby('Date')['Points'].sum().reset_index()

    # Totals and averages
    total_points = float(daily_points['Points'].sum()) if not daily_points.empty else 0.0
    avg_points_per_day = float(daily_points['Points'].mean()) if not daily_points.empty else 0.0
    daily_cumulative = daily_points['Points'].cumsum() if not daily_points.empty else pd.Series(dtype=float)

    # Build figure
    fig = setup_base_figure()
    if not daily_points.empty:
        fig.add_trace(go.Bar(
            x=daily_points['Date'],
            y=daily_points['Points'],
            name='Daily Points',
            marker=dict(color=daily_points['Points'].apply(lambda x: COLORS.get('profit', 'green') if x > 0 else COLORS.get('loss', 'red')))
        ))
        fig.add_trace(go.Scatter(
            x=daily_points['Date'],
            y=daily_cumulative,
            name='Cumulative Points',
            line=dict(color=COLORS.get('profit', 'green'))
        ))

    fig.add_annotation(
        x=1,
        y=1,
        xref='paper',
        yref='paper',
        text=f'Total Points: {total_points:.2f}<br>Avg Points/Day: {avg_points_per_day:.2f}',
        showarrow=False,
        font=dict(size=16),
        bgcolor='white',
        bordercolor='black',
        borderwidth=2,
        borderpad=4
    )

    fig = apply_standard_layout(fig, "Daily Points Won/Lost Analysis")
    return fig

def calculate_points(open_price, close_price, market=None, action=None):
    """
    Calculate signed points for a single trade.
    - Uses market multipliers from settings.MARKET_POINT_MULTIPLIERS.
    - Requires both open_price and close_price to be present and non-zero.
    - Returns signed points (positive for profit, negative for loss).
    """
    try:
        if open_price is None or close_price is None:
            return 0.0

        # coerce floats (handle comma thousands)
        op = None
        cp = None
        try:
            op = float(str(open_price).replace(',', ''))
            cp = float(str(close_price).replace(',', ''))
        except Exception:
            logger.debug("calculate_points: could not coerce open/close to float: open=%s close=%s", open_price, close_price)
            return 0.0

        # require non-zero meaningful prices
        if op == 0.0 or cp == 0.0:
            return 0.0

        # get multiplier for market, fall back to default
        try:
            mult = float(MARKET_POINT_MULTIPLIERS.get(market, DEFAULT_POINT_MULTIPLIER))
        except Exception:
            mult = DEFAULT_POINT_MULTIPLIER

        # compute raw difference (signed)
        diff = cp - op
        points = diff * mult

        logger.debug("Calculated points: %s for market=%s open=%s close=%s mult=%s action=%s", points, market, op, cp, mult, action)
        return points
    except Exception as e:
        logger.error(f"Error calculating points: {e}, open: {open_price}, close: {close_price}, market: {market}")
        return 0.0

def _find_column(df, candidates):
    if df is None:
        return None
    for c in df.columns:
        key = re.sub(r'[\s\-_]', '', c.strip().lower())
        if key in candidates:
            return c
    return None

def _find_date_col(df):
    return _find_column(df, {'transactiondate', 'transaction_date', 'transaction-date', 'date'})

def _find_pl_col(df):
    return _find_column(df, {'p/l', 'pl', 'plamount', 'profitloss', 'profit'})

def _coerce_date(df, col):
    if col and col in df.columns:
        df[col] = pd.to_datetime(df[col], errors='coerce')
    return col

def _coerce_pl_numeric(df, col, alias='_pl_numeric'):
    if col and col in df.columns:
        df[alias] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
    else:
        df[alias] = 0.0
    return alias