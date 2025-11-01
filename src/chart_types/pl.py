# Consolidated P/L visualizations (daily, vs trades, relative, market)
import logging
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

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
    # get canonical filtered/normalized data
    trading_df = base.get_filtered_trading_df(df, account_id=account_id)
    if trading_df is None or trading_df.empty:
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
    fig.add_trace(go.Bar(x=daily[date_col], y=daily['_pl_in_base'],
                         marker_color=['green' if v >= 0 else 'red' for v in daily['_pl_in_base']],
                         text=[base.format_currency(v, base_currency) for v in daily['_pl_in_base']]))
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

    trading_df = base.normalize_trading_df(df)
    if trading_df is None:
        trading_df = pd.DataFrame()
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
            line=dict(color=color, width=2),
            marker=dict(size=6, color=color)
        ), row=i+1, col=1, secondary_y=True)

        fig.update_yaxes(title_text="P/L (%)", row=i+1, col=1, secondary_y=False, showgrid=True, gridwidth=1, gridcolor='LightGray')
        fig.update_yaxes(title_text="Number of Trades", row=i+1, col=1, secondary_y=True, showgrid=False)
        fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='LightGray', row=i+1, col=1)

    apply_standard_layout(fig, "Daily P/L vs Trades")
    fig.update_layout(showlegend=True, margin=dict(t=80, b=50), height=400 * len(currencies))
    return fig


def create_relative_balance_history(df):
    fig = setup_base_figure()
    trading_data = base.normalize_trading_df(df)
    if trading_data is None:
        trading_data = pd.DataFrame()
    if trading_data.empty:
        return fig

    trading_data = trading_data.sort_values('Transaction Date')
    total_pl = trading_data.get('P/L', pd.Series(dtype=float)).sum()
    days_traded = len(trading_data['Transaction Date'].dt.date.unique())
    daily_average = total_pl / days_traded if days_traded > 0 else 0

    trading_data['Cumulative P/L'] = trading_data.get('P/L', pd.Series(dtype=float)).cumsum()
    fig.add_trace(go.Scatter(
        x=trading_data['Transaction Date'],
        y=trading_data['Cumulative P/L'],
        mode='lines+markers',
        name='Cumulative P/L',
        hovertemplate='Date: %{x}<br>Cumulative P/L: %{y:.2f}<extra></extra>'
    ))

    apply_standard_layout(fig, "Relative P/L Over Time")
    fig.update_layout(
        annotations=[
            dict(
                text=(f'Total P/L: {total_pl:.2f}<br>Daily Average: {daily_average:.2f}'),
                xref='paper', yref='paper', x=0.92, y=0.08, showarrow=False,
                bgcolor='white', bordercolor='black', borderwidth=1
            )
        ]
    )
    return fig


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
    # 1) normalize + filter (chart caller should already pass filtered DF; we still normalize to be safe)
    dfc = base.get_filtered_trading_df(df)
    if dfc.empty:
        return setup_base_figure()

    # 2) remove funding/charges / non-market rows (use your existing logic)
    market_df = get_market_data(dfc)   # keep get_market_data but have it call base.get_filtered_trading_df internally
    if market_df.empty:
        return setup_base_figure()

    # 3) unify to base currency if requested
    if exchange_rates is None:
        exchange_rates = getattr(_settings, 'DEFAULT_EXCHANGE_RATES', {})
    if base_currency is None:
        base_currency = getattr(_settings, 'DEFAULT_BASE_CURRENCY', 'USD')
    unified = base.to_unified_currency(market_df, exchange_rates, base_currency, pl_col='_pl_numeric')

    # 4) pick label column, aggregate, and plot
    label_col = base.pick_label_col(unified)
    agg = unified.groupby(label_col)['_pl_in_base'].sum().reset_index().sort_values('_pl_in_base', ascending=False).head(top_n)

    fig = setup_base_figure()
    if agg.empty:
        return fig
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