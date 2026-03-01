"""
Shared query helpers for database service methods.

Eliminates repeated boilerplate patterns:
- Building WHERE conditions with date/account filtering
- Currency conversion loops over query results
- Aggregating P&L by currency then converting to target
"""

from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

from api.services.database import (
    _build_included_accounts_filter,
    execute_query,
    format_end_date,
)


def build_trade_conditions(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    instruments: Optional[List[str]] = None,
    account_id: Optional[int] = None,
    table_alias: str = "bt",
    exclude_funding: bool = True,
) -> Tuple[str, List[Any]]:
    """Build standard WHERE conditions and params for trade queries.

    Args:
        start_date: Optional start date filter.
        end_date: Optional end date filter.
        instruments: Optional instrument name filter.
        account_id: Optional specific account filter, or None for all included.
        table_alias: SQL table alias for broker_transactions (default "bt").
        exclude_funding: Whether to exclude funding/charge/deposit rows.

    Returns:
        Tuple of (where_clause_string, params_list).
    """
    conditions: List[str] = []
    params: List[Any] = []
    prefix = f"{table_alias}." if table_alias else ""

    if exclude_funding:
        conditions.append(
            f"{prefix}\"Action\" NOT LIKE '%Fund%' AND {prefix}\"Action\" NOT LIKE '%Charge%' "
            f"AND {prefix}\"Action\" NOT LIKE '%Deposit%' AND {prefix}\"Action\" NOT LIKE '%Withdraw%'"
        )

    if start_date:
        conditions.append(f'{prefix}"Transaction Date" >= ?')
        params.append(start_date.isoformat())

    if end_date:
        conditions.append(f'{prefix}"Transaction Date" <= ?')
        params.append(format_end_date(end_date))

    if instruments:
        placeholders = ",".join("?" * len(instruments))
        conditions.append(f'{prefix}"Description" IN ({placeholders})')
        params.extend(instruments)

    conditions.append(
        _build_included_accounts_filter(account_id, params, table_alias=table_alias)
    )

    where_clause = " AND ".join(conditions) if conditions else "1=1"
    return where_clause, params


def convert_amount(
    amount: float,
    from_currency: Optional[str],
    target_currency: Optional[str],
) -> float:
    """Convert a single amount between currencies.

    Returns the original amount if currencies match or conversion fails.
    """
    if not target_currency or not from_currency or from_currency == target_currency:
        return amount

    from api.services.currency import CurrencyService

    converted = CurrencyService.convert(amount, from_currency, target_currency)
    return converted if converted is not None else amount


def aggregate_pnl_by_currency(
    rows: List[Dict[str, Any]],
    target_currency: str,
    currency_key: str = "currency",
    value_keys: Optional[List[str]] = None,
    count_keys: Optional[List[str]] = None,
) -> Dict[str, float]:
    """Aggregate monetary values across rows with different currencies.

    This replaces the repeated pattern of looping over currency-grouped query
    results, converting each to target_currency, and summing.

    Args:
        rows: Query result rows, each containing a currency and numeric values.
        target_currency: Currency to convert all values into.
        currency_key: Column name for the source currency.
        value_keys: Column names for monetary values to convert and sum.
            Defaults to ["pnl"].
        count_keys: Column names for integer counts to sum (no conversion).
            Defaults to ["trades"].

    Returns:
        Dict with summed totals for each value_key and count_key.
    """
    if value_keys is None:
        value_keys = ["pnl"]
    if count_keys is None:
        count_keys = ["trades"]

    totals: Dict[str, float] = {}
    for key in value_keys + count_keys:
        totals[key] = 0.0

    for row in rows:
        currency = row.get(currency_key) or target_currency

        for key in value_keys:
            value = row.get(key) or 0
            totals[key] += convert_amount(value, currency, target_currency)

        for key in count_keys:
            totals[key] += row.get(key) or 0

    return totals


def query_grouped_by_currency(
    select_clause: str,
    where_clause: str,
    params: List[Any],
    target_currency: str,
    group_by: str = "a.currency",
    value_keys: Optional[List[str]] = None,
    count_keys: Optional[List[str]] = None,
    extra_params: Optional[List[Any]] = None,
) -> Dict[str, float]:
    """Execute a query grouped by currency and aggregate with conversion.

    Combines the common pattern of:
    1. SELECT ... GROUP BY currency
    2. Loop over results converting each currency
    3. Sum into totals

    Args:
        select_clause: Full SELECT query with {where_clause} placeholder
            or complete query string.
        where_clause: The WHERE clause to use.
        params: Base query parameters.
        target_currency: Currency to convert all values into.
        group_by: GROUP BY expression (default "a.currency").
        value_keys: Monetary columns to convert and sum.
        count_keys: Integer columns to sum without conversion.
        extra_params: Additional params to prepend (e.g., date for today filter).

    Returns:
        Dict with summed totals.
    """
    all_params = list(extra_params or []) + list(params)
    rows = execute_query(select_clause, tuple(all_params))
    return aggregate_pnl_by_currency(
        rows,
        target_currency,
        value_keys=value_keys,
        count_keys=count_keys,
    )


def query_per_period(
    period_expr: str,
    where_clause: str,
    params: List[Any],
    target_currency: str,
    table_alias: str = "bt",
) -> Tuple[Dict[str, float], Dict[str, float], Dict[str, int]]:
    """Query per-trade data and aggregate P&L and points by time period.

    Replaces the repeated pattern of querying individual trades, calculating
    points, converting currency, and grouping by date/month/year.

    Args:
        period_expr: SQL expression for the period key
            (e.g., "DATE(bt.\"Transaction Date\")" or "strftime('%Y-%m', ...)").
        where_clause: WHERE clause string.
        params: Query parameters.
        target_currency: Target currency for conversion.
        table_alias: Table alias for broker_transactions.

    Returns:
        Tuple of (pnl_by_period, points_by_period, trades_by_period).
    """
    from api.services.currency import CurrencyService

    prefix = f"{table_alias}." if table_alias else ""

    query = f"""
        SELECT
            {period_expr} as period,
            a.currency as currency,
            {prefix}"P/L" as pnl,
            {prefix}"Description" as instrument,
            COALESCE({prefix}"Opening", 0) as opening,
            COALESCE({prefix}"Closing", 0) as closing
        FROM broker_transactions {table_alias}
        JOIN accounts a ON {table_alias}.account_id = a.account_id
        WHERE {where_clause}
        ORDER BY period
    """

    rows = execute_query(query, tuple(params))

    point_factors = CurrencyService.get_instrument_point_factors()

    pnl_map: Dict[str, float] = {}
    points_map: Dict[str, float] = {}
    trades_map: Dict[str, int] = {}

    for row in rows:
        period = row["period"]
        currency = row.get("currency") or target_currency
        pnl = row.get("pnl") or 0
        instrument = row.get("instrument") or ""
        opening = row.get("opening") or 0
        closing = row.get("closing") or 0

        points = CurrencyService.calculate_points(
            opening, closing, pnl, instrument, point_factors
        )

        pnl = convert_amount(pnl, currency, target_currency)

        pnl_map[period] = pnl_map.get(period, 0) + pnl
        points_map[period] = points_map.get(period, 0) + points
        trades_map[period] = trades_map.get(period, 0) + 1

    return pnl_map, points_map, trades_map
