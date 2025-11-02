# Consolidated P/L visualizations (daily, vs trades, relative, market)
import logging
import pandas as pd
import matplotlib.pyplot as plt

from .base import (
    ensure_market_column,
    find_date_col,
    setup_base_figure,
    apply_standard_layout,
)

import settings as _settings
import chart_types.base as base
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Defensive defaults for settings that may not exist in every environment.
COLORS = getattr(_settings, "COLORS", {"profit": "green", "loss": "red", "trading": ["#1f77b4"]})
DEFAULT_BASE_CURRENCY = getattr(_settings, "DEFAULT_BASE_CURRENCY", "USD")
DEFAULT_EXCHANGE_RATES = getattr(_settings, "DEFAULT_EXCHANGE_RATES", {})
AVAILABLE_CURRENCIES = getattr(_settings, "AVAILABLE_CURRENCIES", ["USD"])
CURRENCY_SYMBOLS = getattr(_settings, "CURRENCY_SYMBOLS", {"USD": "$"})

logger = logging.getLogger(__name__)


def _currency_color_map():
    base_colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f']
    return {c: base_colors[i % len(base_colors)] for i, c in enumerate(AVAILABLE_CURRENCIES)}


def create_daily_pl(df, exchange_rates=None, base_currency=None, account_id=None):
    """Daily P/L using canonical helpers."""
    logger.debug("create_daily_pl called; incoming df type=%s shape=%s", type(df), getattr(df, "shape", None))
    # Prefer incoming DataFrame when it already looks normalized (has date and P/L)
    trading_df = None
    try:
        if isinstance(df, pd.DataFrame):
            if ('Transaction Date' in df.columns) and (('_pl_numeric' in df.columns) or ('P/L' in df.columns)):
                trading_df = df.copy()
                logger.debug("create_daily_pl: using incoming DataFrame directly (has date and P/L)")
    except Exception:
        logger.exception("create_daily_pl: error inspecting incoming df; will try normalized helper")

    # fallback to canonical helper
    if trading_df is None:
        try:
            trading_df = base.get_filtered_trading_df(df, account_id=account_id)
        except Exception:
            logger.exception("create_daily_pl: get_filtered_trading_df failed; falling back to original df")
            trading_df = df.copy() if isinstance(df, pd.DataFrame) else pd.DataFrame()

    if not isinstance(trading_df, pd.DataFrame):
        trading_df = pd.DataFrame()
    if trading_df.empty:
        logger.warning("create_daily_pl: no trading data after normalization/filtering")
        return setup_base_figure()

    # convert to base currency if requested
    if exchange_rates is None:
        exchange_rates = getattr(_settings, "DEFAULT_EXCHANGE_RATES", {})
    if base_currency is None:
        base_currency = getattr(_settings, "DEFAULT_BASE_CURRENCY", None)
    unified = base.to_unified_currency(trading_df, exchange_rates, base_currency)

    # aggregate by day
    date_col = find_date_col(unified) or 'Transaction Date'
    unified[date_col] = pd.to_datetime(unified[date_col], errors='coerce')
    daily = unified.set_index(date_col).resample('D')['_pl_in_base'].sum().reset_index()

    fig = setup_base_figure()
    if daily.empty:
        return fig
    # use COLORS from settings.py directly
    marker_colors = [COLORS['profit'] if v >= 0 else COLORS['loss'] for v in daily['_pl_in_base']]
    logger.debug("create_daily_pl: marker colors=%s", marker_colors)

    fig.add_trace(go.Bar(
        x=daily[date_col],
        y=daily['_pl_in_base'],
        marker_color=marker_colors,
        text=[base.format_currency(v, base_currency) for v in daily['_pl_in_base']]
    ))
    apply_standard_layout(fig, "Daily P/L")
    return fig


def create_daily_pl_vs_trades(df, exchange_rates=None, base_currency=None, account_id=None):
    # Use explicit fallback inside function so there's no dependency on name at import-time
    if exchange_rates is None:
        exchange_rates = DEFAULT_EXCHANGE_RATES or {}
    if base_currency is None:
        base_currency = DEFAULT_BASE_CURRENCY

    if account_id and account_id != "all":
        try:
            df = df[df['account_id'] == account_id]
        except Exception:
            pass

    # Prefer incoming DataFrame if it already looks normalized (has date + P/L)
    trading_df = None
    try:
        if isinstance(df, pd.DataFrame):
            if ('Transaction Date' in df.columns) and (('_pl_numeric' in df.columns) or ('P/L' in df.columns)):
                trading_df = df.copy()
                logger.debug("create_daily_pl_vs_trades: using incoming DataFrame directly (has date and P/L)")
    except Exception:
        logger.exception("create_daily_pl_vs_trades: error inspecting incoming df; will try normalizer")

    # Fallback to normalizer if needed
    if trading_df is None:
        try:
            trading_df = base.normalize_trading_df(df)
        except Exception:
            logger.exception("create_daily_pl_vs_trades: normalize_trading_df failed; falling back to incoming df")
            trading_df = None

    # Ensure we have a DataFrame; attempt a quick salvage from original df if empty
    if not isinstance(trading_df, pd.DataFrame):
        trading_df = pd.DataFrame()
    if trading_df.empty:
        try:
            tmp = df.copy() if isinstance(df, pd.DataFrame) else pd.DataFrame()
            if not tmp.empty and 'P/L' in tmp.columns:
                tmp['_pl_numeric'] = pd.to_numeric(tmp['P/L'], errors='coerce').fillna(0.0)
                if 'Transaction Date' in tmp.columns:
                    tmp['Transaction Date'] = pd.to_datetime(tmp['Transaction Date'], errors='coerce')
                if not tmp.empty:
                    trading_df = tmp
                    logger.debug("create_daily_pl_vs_trades: salvaged trading_df from incoming df")
        except Exception:
            logger.exception("create_daily_pl_vs_trades: salvage attempt failed")

    if trading_df.empty:
        logger.warning("No trading data for daily PL vs trades")
        return setup_base_figure()

    unified_data = base.get_unified_currency_data(trading_df, exchange_rates, base_currency)
    unified_data['original_currency'] = trading_df.get('Currency', pd.Series([''] * len(trading_df))).values
    currencies = sorted(set(unified_data['original_currency'].unique()) & set(AVAILABLE_CURRENCIES))
    if not currencies:
        return setup_base_figure()

    fig = make_subplots(rows=len(currencies), cols=1,
                        subplot_titles=[f'Daily P/L vs Trades - {c} ({CURRENCY_SYMBOLS.get(c,c)})' for c in currencies],
                        vertical_spacing=0.08,
                        specs=[[{"secondary_y": True}] for _ in currencies])

    currency_colors = _currency_color_map()
    initial_balance = trading_df['Balance'].iloc[0] if not trading_df.empty else 1000

    for i, currency in enumerate(currencies):
        currency_data = unified_data[unified_data['original_currency'] == currency]
        if currency_data.empty:
            continue

        daily_pl_original = currency_data.groupby(currency_data['Transaction Date'].dt.date)['P/L'].sum()
        if currency != base_currency:
            conversion_rate = exchange_rates.get(currency, 1.0) / exchange_rates.get(base_currency, 1.0)
            daily_pl = daily_pl_original * conversion_rate
        else:
            daily_pl = daily_pl_original

        daily_pl_pct = (daily_pl / abs(initial_balance)) * 100
        daily_trades = currency_data.groupby(currency_data['Transaction Date'].dt.date).size()

        total_pl = daily_pl.sum()
        total_pl_pct = daily_pl_pct.sum()
        total_trades = daily_trades.sum()
        avg_pl_per_trade = total_pl / total_trades if total_trades > 0 else 0
        correlation = daily_pl_pct.corr(daily_trades) if len(daily_pl_pct) > 1 else 0

        color = currency_colors.get(currency, '#1f77b4')

        # add traces
        fig.add_trace(go.Bar(
            x=daily_pl_pct.index, y=daily_pl_pct.values,
            name=f"Daily P/L % - {currency}",
            marker_color=[COLORS['profit'] if x >= 0 else COLORS['loss'] for x in daily_pl_pct],
            text=[f"{x:.1f}%" for x in daily_pl_pct],
            textposition='auto',
            cliponaxis=False,
            hoverinfo='text'
        ), row=i+1, col=1)

        fig.add_trace(go.Scatter(
            x=daily_trades.index, y=daily_trades.values,
            mode='lines+markers',
            name=f"Trade Count - {currency}",
            line=dict(color=COLORS['trading'], width=2),
            marker=dict(size=6, color=color)
        ), row=i+1, col=1, secondary_y=True)

        fig.update_yaxes(title_text="P/L (%)", row=i+1, col=1, secondary_y=False, showgrid=True, gridwidth=1, gridcolor='LightGray')
        fig.update_yaxes(title_text="Number of Trades", row=i+1, col=1, secondary_y=True, showgrid=False)
        fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='LightGray', row=i+1, col=1)

    apply_standard_layout(fig, "Daily P/L vs Trades")
    fig.update_layout(showlegend=True, margin=dict(t=80, b=50), height=400 * len(currencies))
    return fig


def _ensure_pl_column(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure a numeric PL column named '_pl_numeric' exists."""
    if '_pl_numeric' in df.columns:
        df['_pl_numeric'] = pd.to_numeric(df['_pl_numeric'], errors='coerce').fillna(0.0)
        return df
    if 'P/L' in df.columns:
        df['_pl_numeric'] = pd.to_numeric(df['P/L'], errors='coerce').fillna(0.0)
        return df
    # no PL column found -> create zero column
    df['_pl_numeric'] = 0.0
    return df


def _empty_figure(title: str = "No data available"):
    fig = plt.Figure(figsize=(10, 4))
    ax = fig.add_subplot(111)
    ax.set_title(title)
    return fig


def create_relative_balance_history(df, exchange_rates=None, base_currency=None, account_id=None,
                                    start_date=None, end_date=None) -> go.Figure:
    """
    P/L history (cumulative) — consistent signature with other chart functions.
    Prefers the caller-provided (already filtered) DataFrame. If account_id or
    start/end are supplied they will be applied as additional filters.
    Always returns a plotly.graph_objects.Figure.
    """
    try:
        logger.debug("create_relative_balance_history called; incoming df type=%s shape=%s",
                     type(df), getattr(df, "shape", None))

        if df is None:
            return setup_base_figure()
        if not isinstance(df, pd.DataFrame):
            try:
                df = pd.DataFrame(df)
            except Exception:
                logger.exception("create_relative_balance_history: failed to coerce df to DataFrame")
                return setup_base_figure()
        if df.empty:
            return setup_base_figure()

        # Ensure there is a date column we can use
        if 'Transaction Date' in df.columns:
            df['Transaction Date'] = pd.to_datetime(df['Transaction Date'], errors='coerce')
        else:
            for c in df.columns:
                if 'date' in c.lower():
                    df['Transaction Date'] = pd.to_datetime(df[c], errors='coerce')
                    break
        df = df.dropna(subset=['Transaction Date'])
        if df.empty:
            return setup_base_figure()

        # Apply optional account/date filters (caller often already filtered by graph_tab)
        try:
            if account_id is not None and 'account_id' in df.columns:
                df = df[df['account_id'] == account_id]
            if start_date is not None:
                sd = pd.to_datetime(start_date, errors='coerce')
                if pd.notna(sd):
                    df = df[df['Transaction Date'] >= sd]
            if end_date is not None:
                ed = pd.to_datetime(end_date, errors='coerce')
                if pd.notna(ed):
                    df = df[df['Transaction Date'] <= ed]
        except Exception:
            logger.exception("create_relative_balance_history: optional filtering failed; continuing with available rows")
        if df.empty:
            return setup_base_figure()

        # Ensure PL numeric column exists and compute daily cumulative
        df = _ensure_pl_column(df)
        df = df.set_index('Transaction Date')
        daily = df['_pl_numeric'].resample('D').sum().reset_index()
        if daily.empty:
            return setup_base_figure()
        daily['cumulative'] = daily['_pl_numeric'].cumsum()

        # Build Plotly figure
        fig = setup_base_figure()
        fig.add_trace(go.Scatter(
            x=daily['Transaction Date'],
            y=daily['cumulative'],
            mode='lines+markers',
            line=dict(color=COLORS.get('profit', 'green'), width=2),
            marker=dict(size=6),
            name='Cumulative P/L',
            hovertemplate='%{x|%Y-%m-%d}: %{y:.2f}<extra></extra>'
        ))
        apply_standard_layout(fig, "P/L History (Cumulative)")
        fig.update_yaxes(title_text="Cumulative P/L")
        fig.update_xaxes(title_text="Date")
        return fig
    except Exception as exc:
        logger.exception("create_relative_balance_history failed: %s", exc)
        return setup_base_figure()


def get_market_data(df):
    # Remove funding/charges using normalized trading data then exclude obvious non-market descriptions
    trading_df = base.normalize_trading_df(df)
    if trading_df is None:
        trading_df = pd.DataFrame()
    if trading_df.empty:
        return pd.DataFrame()
    excluded_patterns = ['fee', 'payable', 'interest', 'online transfer', 'deposit', 'withdraw']
    pattern = '|'.join(excluded_patterns)
    # Use .get to be tolerant if Description is missing; coerce to string
    desc_series = trading_df.get('Description')
    if desc_series is None:
        # try other candidate columns
        for cand in ('Desc', 'Market', 'Instrument', 'Symbol'):
            if cand in trading_df.columns:
                desc_series = trading_df[cand].astype(str)
                break
    if desc_series is None:
        # fallback: create empty string series
        desc_series = pd.Series([''] * len(trading_df), index=trading_df.index)
    else:
        desc_series = desc_series.astype(str)
    mask = ~desc_series.str.contains(pattern, case=False, na=False)
    # Return a copy of rows considered market-related
    return trading_df[mask].copy()


def calculate_win_loss_stats(market_df):
    stats = {}
    if market_df is None or market_df.empty:
        return {"Win Rate": "N/A", "Total Wins": "0", "Total Losses": "0"}
    wins = market_df[market_df.get('P/L', 0) > 0]
    losses = market_df[market_df.get('P/L', 0) < 0]
    total_trades = len(market_df)
    win_count = len(wins)
    win_rate = (win_count / total_trades) * 100 if total_trades > 0 else 0.0
    stats["Win Rate"] = f"{win_rate:.2f}%"
    wins_by_currency = wins.groupby('Currency')['P/L'].sum()
    losses_by_currency = losses.groupby('Currency')['P/L'].sum()
    stats["Total Wins"] = ", ".join([f"{CURRENCY_SYMBOLS.get(c,c)}{v:.2f}" for c, v in wins_by_currency.items()]) or "0"
    stats["Total Losses"] = ", ".join([f"{CURRENCY_SYMBOLS.get(c,c)}{abs(v):.2f}" for c, v in losses_by_currency.items()]) or "0"
    avg_win = wins.groupby('Currency')['P/L'].mean()
    avg_loss = losses.groupby('Currency')['P/L'].mean()
    avg_win_text = ", ".join([f"{CURRENCY_SYMBOLS.get(c,c)}{v:.2f}" for c, v in avg_win.items()]) or "N/A"
    avg_loss_text = ", ".join([f"{CURRENCY_SYMBOLS.get(c,c)}{abs(v):.2f}" for c, v in avg_loss.items()]) or "N/A"
    stats["Avg Win"] = avg_win_text
    stats["Avg Loss"] = avg_loss_text
    if not avg_win.empty and not avg_loss.empty:
        ratios = []
        for c in set(avg_win.index).intersection(set(avg_loss.index)):
            if avg_loss[c] != 0:
                ratios.append(f"{c}: {abs(avg_win[c]/avg_loss[c]):.2f}")
        stats["Win/Loss Ratio"] = ", ".join(ratios) or "N/A"
    else:
        stats["Win/Loss Ratio"] = "N/A"
    return stats


def create_win_loss_analysis(df):
    market_df = get_market_data(df)
    if market_df is None or market_df.empty:
        return setup_base_figure()
    stats = calculate_win_loss_stats(market_df)

    # determine label_col (reuse same logic as create_market_pl_chart)
    label_col = None
    for c in ['Description', 'Desc', 'Market', 'Instrument', 'Symbol']:
        if c in market_df.columns:
            label_col = c
            break
    if label_col is None:
        market_df = base.ensure_market_column(market_df)
        label_col = 'Market' if 'Market' in market_df.columns else market_df.columns[0]
    market_df[label_col] = market_df[label_col].astype(str)

    wins = market_df[market_df.get('P/L', 0) > 0].groupby(market_df[label_col]).size()
    losses = market_df[market_df.get('P/L', 0) < 0].groupby(market_df[label_col]).size()
    all_markets = pd.Series(pd.concat([wins.index.to_series(), losses.index.to_series()]).unique())

    chart_df = pd.DataFrame({
        'Market': all_markets,
         'Wins': wins.reindex(all_markets).fillna(0).astype(int),
         'Losses': losses.reindex(all_markets).fillna(0).astype(int)
     })
    chart_df['Win Rate'] = (chart_df['Wins'] / (chart_df['Wins'] + chart_df['Losses']) * 100).round(2).fillna(0)
    fig = make_subplots(rows=2, cols=1, row_heights=[0.7, 0.3], subplot_titles=["Win/Loss Count by Market", "Win Rate by Market"])
    fig.add_trace(go.Bar(name="Wins", x=chart_df['Market'], y=chart_df['Wins'], marker_color=COLORS['profit']), row=1, col=1)
    fig.add_trace(go.Bar(name="Losses", x=chart_df['Market'], y=chart_df['Losses'], marker_color=COLORS['loss']), row=1, col=1)
    fig.add_trace(go.Scatter(name="Win Rate", x=chart_df['Market'], y=chart_df['Win Rate'], mode='lines+markers',
                             marker=dict(size=8, color='rgba(0,128,128,0.8)'), line=dict(width=2, color='rgba(0,128,128,0.8)')),
                  row=2, col=1)
    apply_standard_layout(fig, "Win/Loss Analysis by Market")
    fig.update_layout(title='Win/Loss Analysis by Market', barmode='group', template='plotly_white', height=800)
    fig.update_xaxes(title_text="Market")
    fig.update_yaxes(title_text="Count", row=1, col=1)
    fig.update_yaxes(title_text="Win Rate (%)", row=2, col=1)
    return fig


def create_market_pl_chart(df, top_n=10, exchange_rates=None, base_currency=None):
    logger.debug("create_market_pl_chart called; incoming df type=%s shape=%s", type(df), getattr(df, "shape", None))

    # Prefer the incoming DataFrame when it already contains expected columns/rows.
    dfc = None
    try:
        if isinstance(df, pd.DataFrame) and getattr(df, "shape", (0, 0))[0] > 0:
            # heuristic: must have a date-like column and a P/L column (P/L or _pl_numeric)
            has_date = 'Transaction Date' in df.columns or any('date' in c.lower() for c in df.columns)
            has_pl = ('_pl_numeric' in df.columns) or ('P/L' in df.columns)
            if has_date and has_pl:
                dfc = df.copy()
                logger.debug("create_market_pl_chart: using incoming DataFrame directly")
    except Exception:
        logger.exception("create_market_pl_chart: error inspecting incoming df; will try base helper")

    # Fallback: use base.get_filtered_trading_df to normalize/filter when incoming df isn't suitable
    if dfc is None:
        try:
            dfc = base.get_filtered_trading_df(df)
        except Exception:
            logger.exception("create_market_pl_chart: get_filtered_trading_df failed; coercing to DataFrame")
            dfc = df.copy() if isinstance(df, pd.DataFrame) else pd.DataFrame()

    logger.debug("create_market_pl_chart: dfc.shape=%s columns=%s", getattr(dfc, "shape", None), list(getattr(dfc, "columns", [])))
    if dfc is None or dfc.empty:
        logger.debug("create_market_pl_chart: dfc is empty after filtering")
        return setup_base_figure()

    # 2) remove funding/charges / non-market rows
    market_df = get_market_data(dfc)
    logger.debug("create_market_pl_chart: market_df.shape=%s", getattr(market_df, "shape", None))

    # If market filtering removed everything, try to salvage by using dfc directly
    if market_df is None or market_df.empty:
        logger.warning("create_market_pl_chart: market_df empty after filtering; falling back to dfc (no market filtering)")
        market_df = dfc.copy()
        if market_df.empty:
            return setup_base_figure()

    # 3) unify to base currency if requested
    if exchange_rates is None:
        exchange_rates = getattr(_settings, 'DEFAULT_EXCHANGE_RATES', {})
    if base_currency is None:
        base_currency = getattr(_settings, 'DEFAULT_BASE_CURRENCY', 'USD')

    try:
        unified = base.to_unified_currency(market_df, exchange_rates, base_currency, pl_col='_pl_numeric')
    except Exception:
        logger.exception("create_market_pl_chart: to_unified_currency failed; attempting to coerce _pl_numeric and continue")
        market_df = _ensure_pl_column(market_df)
        unified = market_df.copy()
        unified['_pl_in_base'] = pd.to_numeric(unified.get('_pl_numeric', 0), errors='coerce').fillna(0.0)

    logger.debug("create_market_pl_chart: unified.shape=%s columns=%s", getattr(unified, "shape", None), list(getattr(unified, "columns", [])))

    # 4) pick label column, aggregate, and plot
    label_col = base.pick_label_col(unified)
    if label_col is None or label_col not in unified.columns:
        # fallback to Description if present
        if 'Description' in unified.columns:
            label_col = 'Description'
        else:
            # last resort: use first non-numeric column
            for c in unified.columns:
                if unified[c].dtype == object:
                    label_col = c
                    break
    if label_col is None:
        logger.warning("create_market_pl_chart: could not determine label column; returning empty figure")
        return setup_base_figure()

    logger.debug("create_market_pl_chart: using label_col=%s", label_col)
    try:
        agg = unified.groupby(label_col)['_pl_in_base'].sum().reset_index().sort_values('_pl_in_base', ascending=False).head(top_n)
    except Exception:
        logger.exception("create_market_pl_chart: aggregation failed; returning empty figure")
        return setup_base_figure()

    logger.debug("create_market_pl_chart: agg.head()=%s", agg.head().to_dict('records') if not agg.empty else "EMPTY")
    fig = setup_base_figure()
    if agg.empty:
        logger.debug("create_market_pl_chart: agg is empty -> no data to plot")
        return fig

    # ensure label col is string for plotting
    agg[label_col] = agg[label_col].astype(str)
    fig.add_trace(go.Bar(x=agg[label_col], y=agg['_pl_in_base'], text=[base.format_currency(v, base_currency) for v in agg['_pl_in_base']]))
    apply_standard_layout(fig, "PL by Market")
    return fig

# Backwards-compatible wrapper for older code that called get_trading_pl_without_funding
def get_trading_pl_without_funding(df, top_n=10):
    """
    Compatibility shim: previously returned Market P/L excluding funding/charges.
    Delegates to create_market_pl_chart to preserve behavior.
    """
    return create_market_pl_chart(df, top_n=top_n)

def create_market_pl(*args, **kwargs):
    """Backward-compatible alias for create_market_pl_chart."""
    return create_market_pl_chart(*args, **kwargs)

def create_balance_history(df, exchange_rates=None, base_currency=None, account_id=None, start_date=None, end_date=None):
    """
    Create a Balance History (line) Plotly figure.
    - df: DataFrame (expected to have 'Transaction Date', 'Balance', and optionally 'Currency')
    - exchange_rates/base_currency: optional conversion to a unified currency
    - account_id/start_date/end_date: optional filters (caller often pre-filters)
    Returns a plotly.graph_objects.Figure (never None).
    """
    try:
        logger.debug("create_balance_history called; incoming df type=%s shape=%s", type(df), getattr(df, "shape", None))
        logger.debug("create_balance_history params: account_id=%r start_date=%r end_date=%r (types: %s,%s,%s)",
                     account_id, start_date, end_date,
                     type(account_id), type(start_date), type(end_date))

        # Coerce to DataFrame
        if df is None:
            return setup_base_figure()
        if not isinstance(df, pd.DataFrame):
            try:
                df = pd.DataFrame(df)
            except Exception:
                logger.exception("create_balance_history: failed to coerce df to DataFrame")
                return setup_base_figure()
        if df.empty:
            return setup_base_figure()

        # Ensure transaction date column
        if 'Transaction Date' in df.columns:
            df['Transaction Date'] = pd.to_datetime(df['Transaction Date'], errors='coerce')
        else:
            for c in df.columns:
                if 'date' in c.lower():
                    df['Transaction Date'] = pd.to_datetime(df[c], errors='coerce')
                    break

        # Log date range BEFORE dropna
        try:
            logger.debug("create_balance_history: incoming Transaction Date min=%s max=%s",
                         df['Transaction Date'].min(), df['Transaction Date'].max())
        except Exception:
            logger.debug("create_balance_history: couldn't read min/max Transaction Date")
        df = df.dropna(subset=['Transaction Date'])
        if df.empty:
            return setup_base_figure()

        # Optional filtering by account_id
        try:
            if account_id is not None and 'account_id' in df.columns:
                logger.debug("create_balance_history: applying account_id filter: %r", account_id)
                df = df[df['account_id'] == account_id]
                logger.debug("create_balance_history: after account filter shape=%s", getattr(df, "shape", None))
        except Exception:
            logger.debug("create_balance_history: account filtering failed; continuing with available rows")

        # Optional date-range filtering
        try:
            logger.debug("create_balance_history: applying date filters (raw): start_date=%r end_date=%r", start_date, end_date)
            if start_date is not None:
                sd = pd.to_datetime(start_date, errors='coerce')
                logger.debug("create_balance_history: parsed start_date -> %s (na? %s)", sd, pd.isna(sd))
                if pd.notna(sd):
                    df = df[df['Transaction Date'] >= sd]
                    logger.debug("create_balance_history: after start_date filter shape=%s", getattr(df, "shape", None))
            if end_date is not None:
                ed = pd.to_datetime(end_date, errors='coerce')
                logger.debug("create_balance_history: parsed end_date -> %s (na? %s)", ed, pd.isna(ed))
                if pd.notna(ed):
                    df = df[df['Transaction Date'] <= ed]
                    logger.debug("create_balance_history: after end_date filter shape=%s", getattr(df, "shape", None))
        except Exception:
            logger.debug("create_balance_history: date filtering failed; continuing with available rows")

        # Log date range AFTER filters
        try:
            logger.debug("create_balance_history: post-filter Transaction Date min=%s max=%s (rows=%s)",
                         df['Transaction Date'].min() if not df.empty else None,
                         df['Transaction Date'].max() if not df.empty else None,
                         len(df))
        except Exception:
            logger.debug("create_balance_history: couldn't read post-filter min/max Transaction Date")
        if df.empty:
            return setup_base_figure()

        # Ensure Balance numeric
        df['Balance'] = pd.to_numeric(df.get('Balance', 0), errors='coerce').fillna(0.0)

        # Convert balances to base currency if requested and Currency column exists
        if exchange_rates is None:
            exchange_rates = DEFAULT_EXCHANGE_RATES or {}
        if base_currency is None:
            base_currency = DEFAULT_BASE_CURRENCY

        if 'Currency' in df.columns and exchange_rates and base_currency:
            def conv_factor(curr):
                try:
                    base_rate = exchange_rates.get(base_currency, 1.0) or 1.0
                    return (exchange_rates.get(curr, 1.0) or 1.0) / base_rate
                except Exception:
                    return 1.0
            df['_conv'] = df['Currency'].apply(conv_factor)
            df['_balance_in_base'] = df['Balance'] * df['_conv']
            y_col = '_balance_in_base'
            y_label_currency = base_currency
        else:
            y_col = 'Balance'
            y_label_currency = None
            df['_balance_in_base'] = df['Balance']

        # Resample to daily last-known balance and forward-fill
        df = df.set_index('Transaction Date').sort_index()
        daily = df['_balance_in_base'].resample('D').last().ffill().reset_index()
        if daily.empty:
            return setup_base_figure()

        # Build Plotly figure (use COLORS from settings.py)
        fig = setup_base_figure()
        line_color = COLORS.get('trading', 'blue')
        fig.add_trace(go.Scatter(
            x=daily['Transaction Date'],
            y=daily['_balance_in_base'],
            mode='lines+markers',
            line=dict(color=line_color, width=2),
            marker=dict(size=6),
            name=f"Balance{f' ({y_label_currency})' if y_label_currency else ''}",
            hovertemplate='%{x|%Y-%m-%d}: %{y:,.2f}<extra></extra>'
        ))
        apply_standard_layout(fig, "Balance History")
        fig.update_yaxes(title_text=f"Balance{f' ({y_label_currency})' if y_label_currency else ''}")
        fig.update_xaxes(title_text="Date")
        return fig

    except Exception as exc:
        logger.exception("create_balance_history failed: %s", exc)
        return setup_base_figure()

__all__ = [
    "create_daily_pl",
    "create_daily_pl_vs_trades",
    "create_relative_balance_history",
    "create_market_pl_chart",
    "create_win_loss_analysis",
    "get_trading_pl_without_funding",
    "create_market_pl",
    "create_balance_history",
]