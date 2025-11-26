import logging
import re

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from settings import BROKERS, COLORS, OVERVIEW_SETTINGS

from .base import (
    aggregate_pl_by_period,
    coerce_date,
    coerce_pl_numeric,
    create_market_pl_chart,
    ensure_market_column,
    find_date_col,
    find_pl_col,
    format_currency,
    get_trading_data,
    normalize_trading_df,
    top_markets_by_pl,
)

logger = logging.getLogger(__name__)


def get_tax_overview_data(df, year=None, broker=None):
    # Normalize and coerce columns first
    if df is None or df.empty:
        return pd.DataFrame()

    df = df.copy()

    # detect and coerce date / pl columns
    date_col = find_date_col(df) or "Transaction Date"
    pl_col = find_pl_col(df) or "P/L"
    coerce_date(df, date_col)
    pl_alias = coerce_pl_numeric(df, pl_col)

    trading_df = normalize_trading_df(df)
    logger.debug(
        "get_tax_overview_data: normalize_trading_df returned type=%s shape=%s",
        type(trading_df),
        getattr(trading_df, "shape", None),
    )
    # Fallbacks if normalize_trading_df returned None or empty
    if trading_df is None or (hasattr(trading_df, "empty") and trading_df.empty):
        logger.debug(
            "get_tax_overview_data: normalize_trading_df returned None/empty, attempting fallbacks"
        )
        # try get_trading_data if available
        try:
            trading_df = get_trading_data(df)
            logger.debug(
                "get_tax_overview_data: get_trading_data returned type=%s shape=%s",
                type(trading_df),
                getattr(trading_df, "shape", None),
            )
        except Exception:
            logger.debug(
                "get_tax_overview_data: get_trading_data not available or failed; attempting to coerce to DataFrame"
            )
            try:
                trading_df = (
                    pd.DataFrame(df) if not isinstance(df, pd.DataFrame) else df.copy()
                )
                # ensure date/pl coercion on the fallback
                if date_col in trading_df.columns:
                    trading_df[date_col] = pd.to_datetime(
                        trading_df[date_col], errors="coerce"
                    )
                trading_df[pl_alias] = pd.to_numeric(
                    trading_df.get(pl_alias, trading_df.get(pl_col, 0)), errors="coerce"
                ).fillna(0.0)
                logger.debug(
                    "get_tax_overview_data: fallback DataFrame shape=%s",
                    getattr(trading_df, "shape", None),
                )
            except Exception:
                logger.exception("get_tax_overview_data: fallback coercion failed")
                return pd.DataFrame()
    # final check
    if trading_df is None or (hasattr(trading_df, "empty") and trading_df.empty):
        logger.debug("get_tax_overview_data: no trading data after fallbacks")
        return pd.DataFrame()
    logger.debug(
        "get_tax_overview_data: sample rows: %s", trading_df.head(3).to_dict("records")
    )
    # ensure Description exists
    if "Description" not in trading_df.columns:
        trading_df["Description"] = trading_df.get("Market", "").astype(str)
    df = trading_df

    # ensure Currency exist (fallbacks)
    if "Currency" not in df.columns:
        df["Currency"] = df.get("currency", "UNKNOWN")

    # Normalize broker display column
    if "broker_name" in df.columns:
        df["Broker_Key"] = df["broker_name"].astype(str)
        df["Broker_Display"] = df["Broker_Key"].apply(lambda k: BROKERS.get(k, k))
    else:
        # fall back to provided broker filter or unknown
        df["Broker_Display"] = BROKERS.get(broker, broker) if broker else "Unknown"
        df["Broker_Key"] = None

    # Filter by year if provided (handle strings like 'All Years' or empty)
    if (
        year
        and str(year).strip()
        and str(year) != OVERVIEW_SETTINGS.get("year_all_label", "All Years")
    ):
        try:
            year_int = int(year)
            df = df[df[date_col].dt.year == year_int]
        except Exception:
            return pd.DataFrame()

    # Filter by broker if provided and not "All"
    if broker and broker != OVERVIEW_SETTINGS.get("all_brokers_label", "All"):
        # broker may be a key or a display name
        # accept either: if matches a display name, map back to keys
        broker_keys = [k for k, v in BROKERS.items() if v == broker]
        if broker_keys:
            df = df[df.get("broker_name", df.get("Broker_Key")) == broker_keys[0]]
        else:
            # if broker looks like a key
            df = df[df.get("broker_name", df.get("Broker_Key")) == broker]

    if df.empty:
        return pd.DataFrame()

    # Add Year column for grouping
    # avoid SettingWithCopyWarning: work on an explicit copy and use .loc for assignment
    df = df.copy()
    df.loc[:, "Year"] = df[date_col].dt.year

    group_cols = ["Broker_Display", "Description", "Currency", "Year"]

    # Base aggregation
    grouped = (
        df.groupby(group_cols)
        .agg(
            Total_PL=(pl_alias, "sum"),
            Trade_Count=(pl_alias, "count"),
            First_Trade=(date_col, "min"),
            Last_Trade=(date_col, "max"),
        )
        .reset_index()
    )

    # Wins (positive PL) and Losses (absolute negative PL)
    wins = (
        df[df[pl_alias] > 0]
        .groupby(group_cols)[pl_alias]
        .sum()
        .rename("Wins")
        .reset_index()
    )
    losses = (
        df[df[pl_alias] < 0]
        .groupby(group_cols)[pl_alias]
        .sum()
        .abs()
        .rename("Losses")
        .reset_index()
    )

    # Merge wins/losses into grouped
    overview = grouped.merge(wins, on=group_cols, how="left").merge(
        losses, on=group_cols, how="left"
    )
    overview["Wins"] = overview["Wins"].fillna(0.0)
    overview["Losses"] = overview["Losses"].fillna(0.0)

    # Ensure columns expected by the UI
    # Rename Total_PL to Total_PL (already set), ensure types
    overview["Year"] = overview["Year"].astype(int)
    overview["Trade_Count"] = overview["Trade_Count"].astype(int)

    # Provide display-friendly Broker_Display values (already set)
    # Provide Description fallback if any missing
    overview["Description"] = overview["Description"].fillna("Unknown")

    # Order columns as expected by create_tax_overview_table
    expected_cols = [
        "Broker_Display",
        "Description",
        "Currency",
        "Year",
        "Total_PL",
        "Wins",
        "Losses",
        "Trade_Count",
        "First_Trade",
        "Last_Trade",
    ]
    for c in expected_cols:
        if c not in overview.columns:
            overview[c] = None

    overview = overview[expected_cols]

    return overview


def create_tax_overview_table(df, selected_year=None, selected_broker=None):
    """
    Create a comprehensive tax overview table
    """
    tax_data = get_tax_overview_data(df, selected_year, selected_broker)

    if tax_data.empty:
        # Create empty figure with message
        fig = go.Figure()
        broker_text = (
            f" for {BROKERS.get(selected_broker, selected_broker)}"
            if selected_broker and selected_broker != "All"
            else ""
        )
        year_text = f" for {selected_year}" if selected_year else ""
        fig.add_annotation(
            text=f"No trading data found{broker_text}{year_text}",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=16),
        )
        fig.update_layout(
            title=f"Tax Overview{broker_text} - {selected_year if selected_year else 'All Years'}",
            template="plotly_white",
        )
        return fig

    # Create table data
    table_data = []
    headers = [
        "Broker",
        "Market",
        "Currency",
        "Year",
        "Total P/L",
        "Wins",
        "Losses",
        "Trades",
        "Period",
    ]

    for _, row in tax_data.iterrows():
        period = f"{row['First_Trade'].strftime('%Y-%m-%d')} to {row['Last_Trade'].strftime('%Y-%m-%d')}"
        table_data.append(
            [
                row["Broker_Display"],
                row["Description"],
                row["Currency"],
                str(int(row["Year"])),
                format_currency(row["Total_PL"], row["Currency"]),
                format_currency(row["Wins"], row["Currency"]),
                format_currency(row["Losses"], row["Currency"]),
                str(int(row["Trade_Count"])),
                period,
            ]
        )

    # Create table
    fig = go.Figure(
        data=[
            go.Table(
                header=dict(
                    values=headers,
                    fill_color="lightblue",
                    align="center",
                    font=dict(size=12, color="black"),
                ),
                cells=dict(
                    values=list(zip(*table_data))
                    if table_data
                    else [[] for _ in headers],
                    fill_color=[["white", "lightgray"] * (len(table_data) // 2 + 1)],
                    align="center",
                    font=dict(size=11),
                ),
            )
        ]
    )

    # Add summary statistics
    total_pl_by_currency = tax_data.groupby("Currency")["Total_PL"].sum()
    total_wins_by_currency = tax_data.groupby("Currency")["Wins"].sum()
    total_losses_by_currency = tax_data.groupby("Currency")["Losses"].sum()

    summary_text = "Summary by Currency:<br>"
    for currency in total_pl_by_currency.index:
        summary_text += f"{currency}: Total P/L: {format_currency(total_pl_by_currency[currency], currency)}, "
        summary_text += (
            f"Wins: {format_currency(total_wins_by_currency[currency], currency)}, "
        )
        summary_text += f"Losses: {format_currency(total_losses_by_currency[currency], currency)}<br>"

    fig.add_annotation(
        text=summary_text,
        xref="paper",
        yref="paper",
        x=0.02,
        y=-0.1,
        showarrow=False,
        bgcolor="lightyellow",
        bordercolor="black",
        borderwidth=1,
        font=dict(size=10),
    )

    # Update title to reflect broker selection
    broker_text = (
        f" - {BROKERS.get(selected_broker, selected_broker)}"
        if selected_broker and selected_broker != "All"
        else ""
    )
    fig.update_layout(
        title=f"Tax Declaration Overview{broker_text} - {selected_year if selected_year else 'All Years'}",
        template="plotly_white",
        height=600,
        margin=dict(b=100),  # Extra bottom margin for summary
    )

    return fig


def create_yearly_summary_chart(df, selected_broker=None):
    """
    Create a yearly summary chart showing P/L by broker and currency
    """
    # pass broker via keyword 'broker'
    tax_data = get_tax_overview_data(df, broker=selected_broker)

    if tax_data.empty:
        fig = go.Figure()
        broker_text = (
            f" for {BROKERS.get(selected_broker, selected_broker)}"
            if selected_broker and selected_broker != "All"
            else ""
        )
        fig.add_annotation(
            text=f"No trading data available{broker_text}",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=16),
        )
        return fig

    # Group by year, broker, and currency
    yearly_summary = (
        tax_data.groupby(["Year", "Broker_Display", "Currency"])["Total_PL"]
        .sum()
        .reset_index()
    )

    # Create subplots for each currency
    currencies = yearly_summary["Currency"].unique()
    fig = make_subplots(
        rows=len(currencies),
        cols=1,
        subplot_titles=[f"P/L by Year - {currency}" for currency in currencies],
        vertical_spacing=0.1,
    )

    for i, currency in enumerate(currencies, 1):
        currency_data = yearly_summary[yearly_summary["Currency"] == currency]

        for broker in currency_data["Broker_Display"].unique():
            broker_data = currency_data[currency_data["Broker_Display"] == broker]

            fig.add_trace(
                go.Bar(
                    name=f"{broker} ({currency})",
                    x=broker_data["Year"],
                    y=broker_data["Total_PL"],
                    text=[
                        format_currency(v, currency) for v in broker_data["Total_PL"]
                    ],
                    textposition="auto",
                    marker_color=[
                        COLORS["profit"] if x >= 0 else COLORS["loss"]
                        for x in broker_data["Total_PL"]
                    ],
                    hovertemplate=f"<b>{broker}</b><br>Year: %{{x}}<br>P/L: %{{text}}<extra></extra>",
                    showlegend=(i == 1),  # Only show legend for first subplot
                ),
                row=i,
                col=1,
            )

    # Update title to reflect broker selection
    broker_text = (
        f" - {BROKERS.get(selected_broker, selected_broker)}"
        if selected_broker and selected_broker != "All"
        else ""
    )
    fig.update_layout(
        title=f"Yearly P/L Summary by Broker and Currency{broker_text}",
        template="plotly_white",
        height=300 * len(currencies),
        barmode="group",
    )

    return fig


def get_available_years(df_or_manager):
    """
    Get list of available years from the trading data.

    - If a DataManager (or manager-like) object is passed and it implements
      get_available_years(), prefer that method (fast / DB-backed).
    - Otherwise fall back to extracting years from a pandas.DataFrame.
    Returns list of strings with the configured "All Years" label first.
    """
    try:
        label = OVERVIEW_SETTINGS.get("year_all_label", "All Years")

        # If a manager-like object was provided, prefer its helper
        if not isinstance(df_or_manager, pd.DataFrame) and hasattr(
            df_or_manager, "get_available_years"
        ):
            try:
                years = df_or_manager.get_available_years()
                # normalize to list of ints/strings
                if not years:
                    return [label]
                # convert ints -> strings, keep strings as-is
                normalized = []
                for y in years:
                    try:
                        normalized.append(str(int(y)))
                    except Exception:
                        normalized.append(str(y))
                return [label] + normalized
            except Exception:
                logger.debug(
                    "get_available_years: manager.get_available_years failed; falling back to DataFrame path",
                    exc_info=True,
                )

        # Fallback: treat argument as DataFrame
        df = (
            df_or_manager if isinstance(df_or_manager, pd.DataFrame) else pd.DataFrame()
        )
        if df is None or df.empty:
            logger.debug("get_available_years: no trading data")
            return [label]

        date_col = find_date_col(df) or "Transaction Date"
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
        years = sorted(
            df[date_col].dt.year.dropna().unique().astype(int).tolist(), reverse=True
        )
        logger.debug("get_available_years: found years=%s", years)
        return [label] + [str(y) for y in years] if years else [label]
    except Exception as e:
        logger.exception("Error getting available years: %s", e)
        return [OVERVIEW_SETTINGS.get("year_all_label", "All Years")]
