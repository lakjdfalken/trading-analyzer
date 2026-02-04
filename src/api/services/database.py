"""
Database service for accessing trading data.

Provides methods to query the SQLite database and return data
in formats suitable for the API responses.
"""

import bisect
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from db_path import DATABASE_PATH


def format_start_date(dt: datetime) -> str:
    """Format a datetime for start of range SQL filtering.

    Returns date string at start of day (00:00:00) to ensure inclusive filtering.
    """
    return dt.strftime("%Y-%m-%d 00:00:00")


def format_end_date(dt: datetime) -> str:
    """Format a datetime for end of range SQL filtering.

    Returns date string at end of day (23:59:59) to ensure inclusive filtering
    when comparing against timestamps with time components.
    """
    return dt.strftime("%Y-%m-%d 23:59:59")


@contextmanager
def get_db_connection():
    """Context manager for database connections."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def get_dataframe(query: str, params: Optional[List[Any]] = None) -> pd.DataFrame:
    """Execute a query and return results as a DataFrame."""
    with get_db_connection() as conn:
        if params:
            return pd.read_sql_query(query, conn, params=params)
        return pd.read_sql_query(query, conn)


def execute_query(query: str, params: Optional[Tuple] = None) -> List[Dict[str, Any]]:
    """Execute a query and return results as a list of dictionaries."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        columns = [description[0] for description in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]


# Request-scoped cache for included account IDs
_included_account_ids_cache: Optional[List[int]] = None


def get_included_account_ids() -> List[int]:
    """Get list of account IDs that are included in statistics.

    Uses request-scoped caching via context variable from main.py.
    Falls back to direct query if context not available.
    """
    # Try to get from request-scoped cache
    try:
        from api.main import (
            get_cached_included_account_ids,
            set_cached_included_account_ids,
        )

        cached = get_cached_included_account_ids()
        if cached is not None:
            return cached

        # Query and cache
        query = """
            SELECT account_id
            FROM accounts
            WHERE COALESCE(include_in_stats, 1) = 1
        """
        results = execute_query(query)
        ids = [r["account_id"] for r in results]
        set_cached_included_account_ids(ids)
        return ids
    except ImportError:
        # Fallback if not running in FastAPI context
        query = """
            SELECT account_id
            FROM accounts
            WHERE COALESCE(include_in_stats, 1) = 1
        """
        results = execute_query(query)
        return [r["account_id"] for r in results]


def _build_included_accounts_filter(
    account_id: Optional[int],
    params: List,
    table_alias: str = "",
    column_name: str = "account_id",
) -> str:
    """Build SQL filter for included accounts.

    Args:
        account_id: Specific account ID to filter, or None for all included accounts
        params: List to append parameters to (modified in place)
        table_alias: Table alias prefix (e.g., "bt." or "")
        column_name: Column name for account_id

    Returns:
        SQL condition string
    """
    prefix = f"{table_alias}." if table_alias else ""

    if account_id:
        params.append(account_id)
        return f"{prefix}{column_name} = ?"
    else:
        included_ids = get_included_account_ids()
        if included_ids:
            placeholders = ",".join("?" * len(included_ids))
            params.extend(included_ids)
            return f"{prefix}{column_name} IN ({placeholders})"
        return "1=0"  # No accounts included


class BalanceTimeline:
    """Efficient balance lookup using binary search."""

    def __init__(self, timeline_data: List[Tuple[str, float]]):
        """Initialize with sorted list of (datetime_str, balance) tuples."""
        self._times = [t[0] for t in timeline_data]
        self._balances = [t[1] for t in timeline_data]

    def find_balance_at_time(self, open_time: Optional[str]) -> Optional[float]:
        """Find the account balance just before the given open time using binary search.

        Returns the balance from the last transaction at or before open_time.
        """
        if not self._times or not open_time:
            return None

        # Binary search for the rightmost position where time <= open_time
        idx = bisect.bisect_right(self._times, open_time)
        if idx == 0:
            return None
        return self._balances[idx - 1]


class TradingDatabase:
    """Service class for trading database operations."""

    @staticmethod
    def get_all_trades(
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        instruments: Optional[List[str]] = None,
        account_id: Optional[int] = None,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Get trades with optional filters.

        Returns:
            Tuple of (trades list, total count)
        """
        # Build WHERE clause
        conditions = []
        params = []

        # Filter out non-trading actions (funding, charges, etc.)
        conditions.append(
            "\"Action\" NOT LIKE '%Fund%' AND \"Action\" NOT LIKE '%Charge%' "
            "AND \"Action\" NOT LIKE '%Deposit%' AND \"Action\" NOT LIKE '%Withdraw%'"
        )

        if start_date:
            conditions.append('"Transaction Date" >= ?')
            params.append(start_date.isoformat())

        if end_date:
            conditions.append('"Transaction Date" <= ?')
            params.append(format_end_date(end_date))

        if instruments:
            placeholders = ",".join("?" * len(instruments))
            conditions.append(f'"Description" IN ({placeholders})')
            params.extend(instruments)

        # Add account filter
        conditions.append(_build_included_accounts_filter(account_id, params))

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        # Get total count
        count_query = f"""
            SELECT COUNT(*) as total
            FROM broker_transactions
            WHERE {where_clause}
        """

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(count_query, tuple(params))
            total = cursor.fetchone()[0]

        # Get trades
        query = f"""
            SELECT
                "Ref. No." as id,
                "Description" as instrument,
                "Action" as action,
                "Opening" as entryPrice,
                "Closing" as exitPrice,
                "Open Period" as entryTime,
                "Transaction Date" as exitTime,
                "Amount" as quantity,
                COALESCE("P/L", 0) as pnl,
                CASE WHEN "Opening" > 0 THEN (COALESCE("P/L", 0) / "Opening") * 100 ELSE 0 END as pnlPercent,
                "Status" as status,
                broker_name,
                "Currency" as currency
            FROM broker_transactions
            WHERE {where_clause}
            ORDER BY "Transaction Date" DESC
        """

        if limit:
            query += f" LIMIT {limit} OFFSET {offset}"

        trades = execute_query(query, tuple(params))

        # Process trades to add direction and ensure all required fields
        for trade in trades:
            action = trade.get("action", "").lower()
            if "buy" in action or "long" in action:
                trade["direction"] = "long"
            elif "sell" in action or "short" in action:
                trade["direction"] = "short"
            else:
                # Infer from price movement
                entry = trade.get("entryPrice", 0) or 0
                exit_price = trade.get("exitPrice", 0) or 0
                pnl = trade.get("pnl", 0) or 0
                if entry > 0 and exit_price > 0:
                    if (exit_price > entry and pnl > 0) or (
                        exit_price < entry and pnl < 0
                    ):
                        trade["direction"] = "long"
                    else:
                        trade["direction"] = "short"
                else:
                    trade["direction"] = "long"  # Default

            trade["status"] = "closed"

            # Ensure all numeric fields have values (not None)
            trade["entryPrice"] = trade.get("entryPrice") or 0
            trade["exitPrice"] = trade.get("exitPrice") or 0
            trade["quantity"] = trade.get("quantity") or 1
            trade["pnl"] = trade.get("pnl") or 0
            trade["pnlPercent"] = trade.get("pnlPercent") or 0

        return trades, total

    @staticmethod
    def get_recent_trades(
        limit: int = 10,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        instruments: Optional[List[str]] = None,
        account_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Get most recent trades."""
        trades, _ = TradingDatabase.get_all_trades(
            start_date=start_date,
            end_date=end_date,
            instruments=instruments,
            account_id=account_id,
            limit=limit,
        )
        return trades

    @staticmethod
    def get_trade_by_id(trade_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific trade by ID."""
        query = """
            SELECT
                "Ref. No." as id,
                "Description" as instrument,
                "Action" as action,
                "Opening" as entryPrice,
                "Closing" as exitPrice,
                "Open Period" as entryTime,
                "Transaction Date" as exitTime,
                "Amount" as quantity,
                COALESCE("P/L", 0) as pnl
            FROM broker_transactions
            WHERE "Ref. No." = ?
        """
        results = execute_query(query, (trade_id,))
        return results[0] if results else None

    @staticmethod
    def get_balance_history(
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        account_id: Optional[int] = None,
        target_currency: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get balance history over time with currency conversion."""
        from api.services.currency import CurrencyService

        # Require explicit currency - no auto-detection per .rules
        if target_currency is None:
            raise ValueError("target_currency is required - no auto-detection allowed")

        conditions = ["1=1"]
        params: List[Any] = []

        if start_date:
            conditions.append('"Transaction Date" >= ?')
            params.append(start_date.isoformat())

        if end_date:
            conditions.append('"Transaction Date" <= ?')
            params.append(format_end_date(end_date))

        if account_id:
            conditions.append("bt.account_id = ?")
            params.append(account_id)

        where_clause = " AND ".join(conditions)

        # Get all accounts that should be included (have any transactions)
        if account_id:
            all_accounts_query = """
                SELECT a.account_id, a.currency
                FROM accounts a
                WHERE a.account_id = ?
            """
            all_accounts = execute_query(all_accounts_query, (account_id,))
        else:
            all_accounts_query = """
                SELECT a.account_id, a.currency
                FROM accounts a
                WHERE COALESCE(a.include_in_stats, 1) = 1
                AND EXISTS (
                    SELECT 1 FROM broker_transactions bt
                    WHERE bt.account_id = a.account_id
                )
            """
            all_accounts = execute_query(all_accounts_query, ())

        account_currencies: Dict[int, str] = {}
        for acc in all_accounts:
            account_currencies[acc["account_id"]] = acc["currency"]

        # Batch query: Get initial balances for ALL accounts in one query
        initial_balances: Dict[int, float] = {}
        if start_date and account_currencies:
            # Use window function to get last balance before start_date for each account
            account_ids = list(account_currencies.keys())
            placeholders = ",".join("?" * len(account_ids))
            init_query = f"""
                WITH ranked AS (
                    SELECT
                        account_id,
                        "Balance" as balance,
                        ROW_NUMBER() OVER (
                            PARTITION BY account_id
                            ORDER BY "Transaction Date" DESC, rowid DESC
                        ) as rn
                    FROM broker_transactions
                    WHERE account_id IN ({placeholders})
                    AND "Transaction Date" < ?
                )
                SELECT account_id, balance
                FROM ranked
                WHERE rn = 1
            """
            init_params = account_ids + [start_date.isoformat()]
            init_results = execute_query(init_query, tuple(init_params))
            for row in init_results:
                initial_balances[row["account_id"]] = row["balance"] or 0

            # For accounts without transactions before start_date, check initial_balance
            missing_accounts = [
                aid for aid in account_ids if aid not in initial_balances
            ]
            if missing_accounts:
                placeholders = ",".join("?" * len(missing_accounts))
                acc_query = f"""
                    SELECT account_id, initial_balance
                    FROM accounts
                    WHERE account_id IN ({placeholders})
                """
                acc_results = execute_query(acc_query, tuple(missing_accounts))
                for row in acc_results:
                    initial_balances[row["account_id"]] = row["initial_balance"] or 0

        # Get balance per date and account currency for conversion
        # Use subquery to get the last transaction (by transaction_id) for each day/account
        query = f"""
            SELECT
                DATE(bt."Transaction Date") as date,
                bt.account_id,
                bt."Balance" as balance,
                a.currency as account_currency
            FROM broker_transactions bt
            LEFT JOIN accounts a ON bt.account_id = a.account_id
            INNER JOIN (
                SELECT DATE("Transaction Date") as txn_date, account_id, MAX("Transaction Date") as last_txn_time
                FROM broker_transactions
                GROUP BY DATE("Transaction Date"), account_id
            ) last_txn ON bt."Transaction Date" = last_txn.last_txn_time AND bt.account_id = last_txn.account_id
            WHERE {where_clause}
            ORDER BY date ASC
        """

        raw_data = execute_query(query, tuple(params))

        # Build per-account balance history with carry-forward
        # First, collect all dates and per-account balances
        all_dates: set = set()
        account_date_balances: Dict[int, Dict[str, float]] = {}

        # Initialize all accounts with empty date maps
        for acct_id in account_currencies:
            account_date_balances[acct_id] = {}

        for row in raw_data:
            date_str = row["date"]
            acct_id = row["account_id"]
            balance = row["balance"] or 0

            all_dates.add(date_str)
            account_date_balances[acct_id][date_str] = balance

        # For each account, carry forward from initial balance through all dates
        sorted_dates = sorted(all_dates)
        for acct_id in account_currencies:
            # Start with the initial balance (from before start_date)
            last_balance = initial_balances.get(acct_id, 0)
            for date_str in sorted_dates:
                if date_str in account_date_balances[acct_id]:
                    last_balance = account_date_balances[acct_id][date_str]
                else:
                    # Carry forward the last known balance
                    account_date_balances[acct_id][date_str] = last_balance

        # Aggregate by date with currency conversion
        date_balances: Dict[str, float] = {}
        for date_str in sorted_dates:
            total = 0.0
            for acct_id in account_currencies:
                balance = account_date_balances[acct_id].get(date_str, 0)
                acct_currency = account_currencies.get(acct_id)

                # Convert to target currency if needed
                if (
                    target_currency
                    and acct_currency
                    and acct_currency != target_currency
                ):
                    rate = CurrencyService.get_exchange_rate(
                        acct_currency, target_currency
                    )
                    if rate:
                        balance *= rate

                total += balance
            date_balances[date_str] = total

        data = [
            {"date": date, "balance": balance}
            for date, balance in sorted(date_balances.items())
        ]

        return {
            "data": data,
            "currency": target_currency,
        }

    @staticmethod
    def get_balance_history_by_account(
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        target_currency: Optional[str] = None,
        account_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Get balance history per account for stacked area charting."""
        from api.services.currency import CurrencyService

        # Require explicit currency - no auto-detection per .rules
        if target_currency is None:
            raise ValueError("target_currency is required - no auto-detection allowed")

        conditions = ["1=1"]
        params: List[Any] = []

        if start_date:
            conditions.append('bt."Transaction Date" >= ?')
            params.append(start_date.isoformat())

        if end_date:
            conditions.append('bt."Transaction Date" <= ?')
            params.append(format_end_date(end_date))

        if account_id:
            conditions.append("bt.account_id = ?")
            params.append(account_id)

        where_clause = " AND ".join(conditions)

        # Get all included accounts
        if account_id:
            accounts_query = """
                SELECT a.account_id, a.account_name, a.currency
                FROM accounts a
                WHERE a.account_id = ?
            """
            accounts = execute_query(accounts_query, (account_id,))
        else:
            accounts_query = """
                SELECT a.account_id, a.account_name, a.currency
                FROM accounts a
                WHERE COALESCE(a.include_in_stats, 1) = 1
                AND EXISTS (
                    SELECT 1 FROM broker_transactions bt
                    WHERE bt.account_id = a.account_id
                )
            """
            accounts = execute_query(accounts_query)

        account_info: Dict[int, Dict[str, Any]] = {}
        for acc in accounts:
            account_info[acc["account_id"]] = {
                "name": acc["account_name"] or f"Account {acc['account_id']}",
                "currency": acc["currency"],
            }

        # Batch query for initial balances
        initial_balances: Dict[int, float] = {}
        if start_date and account_info:
            account_ids = list(account_info.keys())
            placeholders = ",".join("?" * len(account_ids))
            init_query = f"""
                WITH ranked AS (
                    SELECT
                        account_id,
                        "Balance" as balance,
                        ROW_NUMBER() OVER (
                            PARTITION BY account_id
                            ORDER BY "Transaction Date" DESC, rowid DESC
                        ) as rn
                    FROM broker_transactions
                    WHERE account_id IN ({placeholders})
                    AND "Transaction Date" < ?
                )
                SELECT account_id, balance
                FROM ranked
                WHERE rn = 1
            """
            init_results = execute_query(
                init_query, tuple(account_ids + [start_date.isoformat()])
            )
            for row in init_results:
                initial_balances[row["account_id"]] = row["balance"] or 0

        # Get last balance per day per account
        query = f"""
            WITH last_txn AS (
                SELECT
                    DATE("Transaction Date") as date,
                    account_id,
                    MAX("Transaction Date") as max_time
                FROM broker_transactions
                GROUP BY DATE("Transaction Date"), account_id
            )
            SELECT
                lt.date,
                lt.account_id,
                bt."Balance" as balance
            FROM last_txn lt
            JOIN broker_transactions bt
                ON bt."Transaction Date" = lt.max_time
                AND bt.account_id = lt.account_id
            WHERE {where_clause}
            ORDER BY lt.date ASC
        """

        raw_data = execute_query(query, tuple(params))

        # Collect all dates and per-account balances
        all_dates: set = set()
        account_date_balances: Dict[int, Dict[str, float]] = {
            aid: {} for aid in account_info
        }

        for row in raw_data:
            date_str = row["date"]
            acct_id = row["account_id"]
            if acct_id in account_info:
                all_dates.add(date_str)
                account_date_balances[acct_id][date_str] = row["balance"] or 0

        sorted_dates = sorted(all_dates)

        # Carry forward balances and convert currencies
        series: Dict[int, List[Dict[str, Any]]] = {aid: [] for aid in account_info}
        total_by_date: Dict[str, float] = {}

        for acct_id in account_info:
            last_balance = initial_balances.get(acct_id, 0)
            acct_currency = account_info[acct_id]["currency"]

            for date_str in sorted_dates:
                if date_str in account_date_balances[acct_id]:
                    last_balance = account_date_balances[acct_id][date_str]

                # Convert to target currency
                converted_balance = last_balance
                if acct_currency and acct_currency != target_currency:
                    rate = CurrencyService.get_exchange_rate(
                        acct_currency, target_currency
                    )
                    if rate:
                        converted_balance = last_balance * rate

                series[acct_id].append({"date": date_str, "balance": converted_balance})
                total_by_date[date_str] = (
                    total_by_date.get(date_str, 0) + converted_balance
                )

        # Build response
        result_series = []
        for acct_id, data_points in series.items():
            result_series.append(
                {
                    "accountId": acct_id,
                    "accountName": account_info[acct_id]["name"],
                    "data": data_points,
                }
            )

        total_data = [
            {"date": date, "balance": balance}
            for date, balance in sorted(total_by_date.items())
        ]

        return {
            "series": result_series,
            "total": total_data,
            "currency": target_currency,
        }

    @staticmethod
    def get_monthly_pnl_by_account(
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        target_currency: Optional[str] = None,
        instruments: Optional[List[str]] = None,
        account_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Get monthly P&L broken down by account for stacked bar charting."""
        from api.services.currency import CurrencyService

        # Require explicit currency - no auto-detection per .rules
        if target_currency is None:
            raise ValueError("target_currency is required - no auto-detection allowed")

        conditions = [
            "bt.\"Action\" NOT LIKE '%Fund%' AND bt.\"Action\" NOT LIKE '%Charge%' "
            "AND bt.\"Action\" NOT LIKE '%Deposit%' AND bt.\"Action\" NOT LIKE '%Withdraw%'"
        ]
        params: List[Any] = []

        if start_date:
            conditions.append('bt."Transaction Date" >= ?')
            params.append(start_date.isoformat())

        if end_date:
            conditions.append('bt."Transaction Date" <= ?')
            params.append(format_end_date(end_date))

        if instruments:
            placeholders = ",".join("?" * len(instruments))
            conditions.append(f'bt."Description" IN ({placeholders})')
            params.extend(instruments)

        # Add account filter
        conditions.append(
            _build_included_accounts_filter(account_id, params, table_alias="bt")
        )

        where_clause = " AND ".join(conditions)

        # Get account info
        if account_id:
            accounts_query = """
                SELECT a.account_id, a.account_name, a.currency
                FROM accounts a
                WHERE a.account_id = ?
            """
            accounts = execute_query(accounts_query, (account_id,))
        else:
            included_ids = get_included_account_ids()
            if included_ids:
                placeholders = ",".join("?" * len(included_ids))
                accounts_query = f"""
                    SELECT a.account_id, a.account_name, a.currency
                    FROM accounts a
                    WHERE a.account_id IN ({placeholders})
                """
                accounts = execute_query(accounts_query, tuple(included_ids))
            else:
                accounts = []

        account_info: Dict[int, Dict[str, Any]] = {}
        for acc in accounts:
            account_info[acc["account_id"]] = {
                "name": acc["account_name"] or f"Account {acc['account_id']}",
                "currency": acc["currency"],
            }

        # Get monthly P&L per account
        query = f"""
            SELECT
                strftime('%Y-%m', bt."Transaction Date") as month,
                bt.account_id,
                SUM(bt."P/L") as pnl,
                COUNT(*) as trades,
                SUM(CASE WHEN bt."P/L" >= 0 THEN 1 ELSE 0 END) as wins
            FROM broker_transactions bt
            WHERE {where_clause}
            GROUP BY strftime('%Y-%m', bt."Transaction Date"), bt.account_id
            ORDER BY month ASC
        """

        raw_data = execute_query(query, tuple(params))

        # Collect all months
        all_months: set = set()
        account_month_data: Dict[int, Dict[str, Dict[str, Any]]] = {
            aid: {} for aid in account_info
        }

        for row in raw_data:
            month = row["month"]
            acct_id = row["account_id"]
            if acct_id in account_info:
                all_months.add(month)
                acct_currency = account_info[acct_id]["currency"]
                pnl = row["pnl"] or 0

                # Convert to target currency
                if acct_currency and acct_currency != target_currency:
                    converted = CurrencyService.convert(
                        pnl, acct_currency, target_currency
                    )
                    if converted is not None:
                        pnl = converted

                account_month_data[acct_id][month] = {
                    "pnl": pnl,
                    "trades": row["trades"],
                    "wins": row["wins"],
                }

        sorted_months = sorted(all_months)

        # Build series and totals
        series = []
        total_by_month: Dict[str, Dict[str, Any]] = {}

        for acct_id, month_data in account_month_data.items():
            data_points = []
            for month in sorted_months:
                if month in month_data:
                    data_points.append(
                        {
                            "month": month,
                            "pnl": month_data[month]["pnl"],
                            "trades": month_data[month]["trades"],
                            "wins": month_data[month]["wins"],
                        }
                    )
                    # Aggregate totals
                    if month not in total_by_month:
                        total_by_month[month] = {"pnl": 0, "trades": 0, "wins": 0}
                    total_by_month[month]["pnl"] += month_data[month]["pnl"]
                    total_by_month[month]["trades"] += month_data[month]["trades"]
                    total_by_month[month]["wins"] += month_data[month]["wins"]
                else:
                    data_points.append(
                        {"month": month, "pnl": 0, "trades": 0, "wins": 0}
                    )

            series.append(
                {
                    "accountId": acct_id,
                    "accountName": account_info[acct_id]["name"],
                    "data": data_points,
                }
            )

        total_data = [
            {
                "month": month,
                "pnl": data["pnl"],
                "trades": data["trades"],
                "winRate": (data["wins"] / data["trades"] * 100)
                if data["trades"] > 0
                else 0,
            }
            for month, data in sorted(total_by_month.items())
        ]

        return {
            "series": series,
            "total": total_data,
            "currency": target_currency,
        }

    @staticmethod
    def get_monthly_pnl(
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        instruments: Optional[List[str]] = None,
        target_currency: Optional[str] = None,
        account_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Get monthly P&L aggregated with currency conversion."""
        from api.services.currency import CurrencyService

        # Require explicit currency - no auto-detection per .rules
        if target_currency is None:
            raise ValueError("target_currency is required - no auto-detection allowed")

        conditions = [
            "bt.\"Action\" NOT LIKE '%Fund%' AND bt.\"Action\" NOT LIKE '%Charge%' "
            "AND bt.\"Action\" NOT LIKE '%Deposit%' AND bt.\"Action\" NOT LIKE '%Withdraw%'"
        ]
        params: List[Any] = []

        if start_date:
            conditions.append('bt."Transaction Date" >= ?')
            params.append(start_date.isoformat())

        if end_date:
            conditions.append('bt."Transaction Date" <= ?')
            params.append(format_end_date(end_date))

        if instruments:
            placeholders = ",".join("?" * len(instruments))
            conditions.append(f'bt."Description" IN ({placeholders})')
            params.extend(instruments)

        # Add account filter
        conditions.append(
            _build_included_accounts_filter(account_id, params, table_alias="bt")
        )

        where_clause = " AND ".join(conditions)

        # Get monthly P&L grouped by currency for conversion
        query = f"""
            SELECT
                strftime('%Y-%m', bt."Transaction Date") as month,
                a.currency as currency,
                SUM(bt."P/L") as pnl,
                COUNT(*) as trades,
                SUM(CASE WHEN bt."P/L" >= 0 THEN 1 ELSE 0 END) as wins
            FROM broker_transactions bt
            JOIN accounts a ON bt.account_id = a.account_id
            WHERE {where_clause}
            GROUP BY strftime('%Y-%m', bt."Transaction Date"), a.currency
            ORDER BY month ASC
        """

        raw_data = execute_query(query, tuple(params))

        # Aggregate by month with currency conversion
        month_map: Dict[str, Dict[str, Any]] = {}
        for row in raw_data:
            month = row["month"]
            currency = row["currency"] or target_currency
            pnl = row["pnl"] or 0
            trades = row["trades"] or 0
            wins = row["wins"] or 0

            # Convert to target currency
            if currency != target_currency:
                converted = CurrencyService.convert(pnl, currency, target_currency)
                if converted is not None:
                    pnl = converted

            if month not in month_map:
                month_map[month] = {"month": month, "pnl": 0, "trades": 0, "wins": 0}

            month_map[month]["pnl"] += pnl
            month_map[month]["trades"] += trades
            month_map[month]["wins"] += wins

        # Calculate win rates and build final data
        data = []
        cumulative = 0
        for month in sorted(month_map.keys()):
            entry = month_map[month]
            cumulative += entry["pnl"]
            win_rate = (
                (entry["wins"] / entry["trades"] * 100) if entry["trades"] > 0 else 0
            )
            data.append(
                {
                    "month": entry["month"],
                    "pnl": entry["pnl"],
                    "cumulativePnl": cumulative,
                    "trades": entry["trades"],
                    "winRate": win_rate,
                }
            )

        return {
            "data": data,
            "currency": target_currency,
        }

    @staticmethod
    def get_win_rate_by_instrument(
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        account_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Get win rate statistics by instrument."""
        conditions = [
            "\"Action\" NOT LIKE '%Fund%' AND \"Action\" NOT LIKE '%Charge%' "
            "AND \"Action\" NOT LIKE '%Deposit%' AND \"Action\" NOT LIKE '%Withdraw%'"
        ]
        params: List[Any] = []

        if start_date:
            conditions.append('"Transaction Date" >= ?')
            params.append(start_date.isoformat())

        if end_date:
            conditions.append('"Transaction Date" <= ?')
            params.append(format_end_date(end_date))

        # Add account filter
        conditions.append(_build_included_accounts_filter(account_id, params))

        where_clause = " AND ".join(conditions)

        query = f"""
            SELECT
                "Description" as name,
                COUNT(*) as trades,
                SUM(CASE WHEN "P/L" >= 0 THEN 1 ELSE 0 END) as wins,
                SUM(CASE WHEN "P/L" < 0 THEN 1 ELSE 0 END) as losses
            FROM broker_transactions
            WHERE {where_clause}
            GROUP BY "Description"
            ORDER BY trades DESC
        """

        results = execute_query(query, tuple(params))

        for r in results:
            total = r["trades"] or 0
            wins = r["wins"] or 0
            r["winRate"] = (wins / total * 100) if total > 0 else 0

        return results

    @staticmethod
    def get_points_by_instrument(
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        target_currency: Optional[str] = None,
        account_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Get points (price movement) by instrument with P&L in target currency."""
        from api.services.currency import CurrencyService

        conditions = [
            "bt.\"Action\" NOT LIKE '%Fund%' AND bt.\"Action\" NOT LIKE '%Charge%' "
            "AND bt.\"Action\" NOT LIKE '%Deposit%' AND bt.\"Action\" NOT LIKE '%Withdraw%'"
        ]
        params: List[Any] = []

        if start_date:
            conditions.append('bt."Transaction Date" >= ?')
            params.append(start_date.isoformat())

        if end_date:
            conditions.append('bt."Transaction Date" <= ?')
            params.append(format_end_date(end_date))

        # Add account filter
        conditions.append(
            _build_included_accounts_filter(account_id, params, table_alias="bt")
        )

        where_clause = " AND ".join(conditions)

        # Query groups by instrument AND account currency for proper conversion
        query = f"""
            SELECT
                bt."Description" as instrument,
                a.currency as account_currency,
                SUM(CASE
                    WHEN bt."Closing" IS NOT NULL AND bt."Opening" IS NOT NULL AND bt."Opening" != 0
                    THEN bt."Closing" - bt."Opening"
                    ELSE 0
                END) as totalPoints,
                SUM(bt."P/L") as totalPnl,
                COUNT(*) as totalTrades
            FROM broker_transactions bt
            JOIN accounts a ON bt.account_id = a.account_id
            WHERE {where_clause}
            GROUP BY bt."Description", a.currency
            ORDER BY totalPnl DESC
        """

        raw_data = execute_query(query, tuple(params))

        # Aggregate by instrument with currency conversion
        instrument_map: Dict[str, Dict[str, Any]] = {}
        for row in raw_data:
            instrument = row["instrument"]
            currency = row["account_currency"] or target_currency
            points = row["totalPoints"] or 0
            pnl = row["totalPnl"] or 0
            trades = row["totalTrades"] or 0

            # Convert P&L to target currency if needed
            if target_currency and currency and currency != target_currency:
                converted = CurrencyService.convert(pnl, currency, target_currency)
                if converted is not None:
                    pnl = converted

            if instrument not in instrument_map:
                instrument_map[instrument] = {
                    "instrument": instrument,
                    "totalPoints": 0,
                    "totalPnl": 0,
                    "totalTrades": 0,
                }

            instrument_map[instrument]["totalPoints"] += points
            instrument_map[instrument]["totalPnl"] += pnl
            instrument_map[instrument]["totalTrades"] += trades

        results = list(instrument_map.values())
        results.sort(key=lambda x: x["totalPnl"], reverse=True)
        return results

    @staticmethod
    def _calculate_max_drawdown(
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        instruments: Optional[List[str]] = None,
        account_id: Optional[int] = None,
    ) -> float:
        """Calculate maximum drawdown as a percentage."""
        conditions = []
        params: List[Any] = []

        if start_date:
            conditions.append('"Transaction Date" >= ?')
            params.append(start_date.isoformat())

        if end_date:
            conditions.append('"Transaction Date" <= ?')
            params.append(format_end_date(end_date))

        if instruments:
            placeholders = ",".join("?" * len(instruments))
            conditions.append(f'"Description" IN ({placeholders})')
            params.extend(instruments)

        if account_id:
            conditions.append("account_id = ?")
            params.append(account_id)

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        # Get balance history sorted by date
        query = f"""
            SELECT "Balance" as balance
            FROM broker_transactions
            WHERE {where_clause}
            ORDER BY "Transaction Date" ASC
        """

        results = execute_query(query, tuple(params))

        if not results:
            return 0.0

        # Calculate max drawdown
        peak = 0.0
        max_drawdown = 0.0

        for row in results:
            balance = row["balance"] or 0
            if balance > peak:
                peak = balance
            if peak > 0:
                drawdown = (peak - balance) / peak * 100
                if drawdown > max_drawdown:
                    max_drawdown = drawdown

        return max_drawdown

    @staticmethod
    def get_kpi_metrics(
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        instruments: Optional[List[str]] = None,
        target_currency: Optional[str] = None,
        account_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Calculate KPI metrics with currency conversion."""
        from api.services.currency import CurrencyService

        conditions = [
            "bt.\"Action\" NOT LIKE '%Fund%' AND bt.\"Action\" NOT LIKE '%Charge%' "
            "AND bt.\"Action\" NOT LIKE '%Deposit%' AND bt.\"Action\" NOT LIKE '%Withdraw%'"
        ]
        params: List[Any] = []

        if start_date:
            conditions.append('bt."Transaction Date" >= ?')
            params.append(start_date.isoformat())

        if end_date:
            conditions.append('bt."Transaction Date" <= ?')
            params.append(format_end_date(end_date))

        if instruments:
            placeholders = ",".join("?" * len(instruments))
            conditions.append(f'bt."Description" IN ({placeholders})')
            params.extend(instruments)

        # Add account filter
        conditions.append(
            _build_included_accounts_filter(account_id, params, table_alias="bt")
        )

        where_clause = " AND ".join(conditions)

        # Require explicit currency - no auto-detection per .rules
        if target_currency is None:
            raise ValueError("target_currency is required - no auto-detection allowed")

        # Get P&L grouped by account currency for proper conversion
        # Use account currency (not transaction currency) for multi-account scenarios
        pnl_by_currency_query = f"""
            SELECT
                a.currency as currency,
                SUM(bt."P/L") as pnl,
                COUNT(*) as trades,
                SUM(CASE WHEN bt."P/L" >= 0 THEN 1 ELSE 0 END) as wins,
                SUM(CASE WHEN bt."P/L" < 0 THEN 1 ELSE 0 END) as losses,
                SUM(CASE WHEN bt."P/L" >= 0 THEN bt."P/L" ELSE 0 END) as total_wins,
                SUM(CASE WHEN bt."P/L" < 0 THEN bt."P/L" ELSE 0 END) as total_losses
            FROM broker_transactions bt
            JOIN accounts a ON bt.account_id = a.account_id
            WHERE {where_clause}
            GROUP BY a.currency
        """

        pnl_results = execute_query(pnl_by_currency_query, tuple(params))

        # Aggregate with currency conversion
        total_pnl = 0.0
        total_trades = 0
        winning_trades = 0
        losing_trades = 0
        total_wins_amount = 0.0
        total_losses_amount = 0.0

        for row in pnl_results:
            currency = row.get("currency") or target_currency
            pnl = row.get("pnl") or 0
            trades = row.get("trades") or 0
            wins = row.get("wins") or 0
            losses = row.get("losses") or 0
            wins_amt = row.get("total_wins") or 0
            losses_amt = abs(row.get("total_losses") or 0)

            # Convert to target currency
            if currency != target_currency:
                converted_pnl = CurrencyService.convert(pnl, currency, target_currency)
                converted_wins = CurrencyService.convert(
                    wins_amt, currency, target_currency
                )
                converted_losses = CurrencyService.convert(
                    losses_amt, currency, target_currency
                )
                if converted_pnl is not None:
                    pnl = converted_pnl
                if converted_wins is not None:
                    wins_amt = converted_wins
                if converted_losses is not None:
                    losses_amt = converted_losses

            total_pnl += pnl
            total_trades += trades
            winning_trades += wins
            losing_trades += losses
            total_wins_amount += wins_amt
            total_losses_amount += losses_amt

        # Calculate averages
        avg_win = total_wins_amount / winning_trades if winning_trades > 0 else 0
        avg_loss = total_losses_amount / losing_trades if losing_trades > 0 else 0

        # Get balance stats (with account join for proper filtering)
        balance_query = f"""
            SELECT
                COALESCE(MIN(bt."Balance"), 0) as min_balance,
                COALESCE(MAX(bt."Balance"), 0) as max_balance
            FROM broker_transactions bt
            JOIN accounts a ON bt.account_id = a.account_id
            WHERE {where_clause}
        """
        balance_results = execute_query(balance_query, tuple(params))
        balance_row = balance_results[0] if balance_results else {}
        max_balance = balance_row.get("max_balance", 0) or 0
        min_balance = balance_row.get("min_balance", 0) or 0

        # Calculate win rate
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0

        # Calculate profit factor
        profit_factor = (
            total_wins_amount / total_losses_amount if total_losses_amount > 0 else 0
        )

        # Calculate max drawdown (peak-to-trough)
        max_drawdown = TradingDatabase._calculate_max_drawdown(
            start_date, end_date, instruments, None
        )

        # Today's date for today's stats (UTC for consistency)
        today = datetime.now(timezone.utc).date().isoformat()

        # Get today's P&L with currency conversion (using account currency)
        today_pnl_query = f"""
            SELECT a.currency as currency, SUM(bt."P/L") as pnl, COUNT(*) as trades
            FROM broker_transactions bt
            JOIN accounts a ON bt.account_id = a.account_id
            WHERE DATE(bt."Transaction Date") = ? AND {where_clause}
            GROUP BY a.currency
        """
        today_params = [today] + list(params)
        today_pnl_results = execute_query(today_pnl_query, tuple(today_params))

        today_pnl = 0.0
        today_trades = 0
        for row in today_pnl_results:
            currency = row.get("currency") or target_currency
            pnl = row.get("pnl") or 0
            trades = row.get("trades") or 0

            if currency != target_currency:
                converted = CurrencyService.convert(pnl, currency, target_currency)
                if converted is not None:
                    pnl = converted

            today_pnl += pnl
            today_trades += trades

        # Get this week's stats (Monday to Sunday)
        today_dt = datetime.now(timezone.utc).date()
        week_start = today_dt - timedelta(days=today_dt.weekday())
        week_start_str = week_start.isoformat()

        week_pnl_query = f"""
            SELECT a.currency as currency, SUM(bt."P/L") as pnl, COUNT(*) as trades
            FROM broker_transactions bt
            JOIN accounts a ON bt.account_id = a.account_id
            WHERE DATE(bt."Transaction Date") >= ? AND {where_clause}
            GROUP BY a.currency
        """
        week_params = [week_start_str] + list(params)
        week_pnl_results = execute_query(week_pnl_query, tuple(week_params))

        week_pnl = 0.0
        week_trades = 0
        for row in week_pnl_results:
            currency = row.get("currency") or target_currency
            pnl = row.get("pnl") or 0
            trades = row.get("trades") or 0

            if currency != target_currency:
                converted = CurrencyService.convert(pnl, currency, target_currency)
                if converted is not None:
                    pnl = converted

            week_pnl += pnl
            week_trades += trades

        # Get this month's stats
        month_start = today_dt.replace(day=1).isoformat()

        month_pnl_query = f"""
            SELECT a.currency as currency, SUM(bt."P/L") as pnl, COUNT(*) as trades,
                   SUM(CASE WHEN bt."P/L" >= 0 THEN 1 ELSE 0 END) as wins
            FROM broker_transactions bt
            JOIN accounts a ON bt.account_id = a.account_id
            WHERE DATE(bt."Transaction Date") >= ? AND {where_clause}
            GROUP BY a.currency
        """
        month_params = [month_start] + list(params)
        month_pnl_results = execute_query(month_pnl_query, tuple(month_params))

        month_pnl = 0.0
        month_trades = 0
        month_wins = 0
        for row in month_pnl_results:
            currency = row.get("currency") or target_currency
            pnl = row.get("pnl") or 0
            trades = row.get("trades") or 0
            wins = row.get("wins") or 0

            if currency != target_currency:
                converted = CurrencyService.convert(pnl, currency, target_currency)
                if converted is not None:
                    pnl = converted

            month_pnl += pnl
            month_trades += trades
            month_wins += wins

        # Get this year's stats
        year_start = today_dt.replace(month=1, day=1).isoformat()

        year_pnl_query = f"""
            SELECT a.currency as currency, SUM(bt."P/L") as pnl, COUNT(*) as trades,
                   SUM(CASE WHEN bt."P/L" >= 0 THEN 1 ELSE 0 END) as wins
            FROM broker_transactions bt
            JOIN accounts a ON bt.account_id = a.account_id
            WHERE DATE(bt."Transaction Date") >= ? AND {where_clause}
            GROUP BY a.currency
        """
        year_params = [year_start] + list(params)
        year_pnl_results = execute_query(year_pnl_query, tuple(year_params))

        year_pnl = 0.0
        year_trades = 0
        year_wins = 0
        for row in year_pnl_results:
            currency = row.get("currency") or target_currency
            pnl = row.get("pnl") or 0
            trades = row.get("trades") or 0
            wins = row.get("wins") or 0

            if currency != target_currency:
                converted = CurrencyService.convert(pnl, currency, target_currency)
                if converted is not None:
                    pnl = converted

            year_pnl += pnl
            year_trades += trades
            year_wins += wins

        # Calculate average P&L per trade
        avg_pnl = total_pnl / total_trades if total_trades > 0 else 0

        # Calculate daily averages
        days_query = f"""
            SELECT COUNT(DISTINCT DATE(bt."Transaction Date")) as trading_days
            FROM broker_transactions bt
            WHERE {where_clause}
        """
        days_result = execute_query(days_query, tuple(params))
        trading_days = days_result[0]["trading_days"] if days_result else 1
        daily_avg = total_pnl / trading_days if trading_days > 0 else 0

        # Fetch point factors once for batch processing
        point_factors = CurrencyService.get_instrument_point_factors()

        # Get daily P&L and points breakdown for best/worst day and average calculations
        daily_trades_query = f"""
            SELECT
                DATE(bt."Transaction Date") as date,
                a.currency as currency,
                bt."P/L" as pnl,
                bt."Description" as instrument,
                COALESCE(bt."Opening", 0) as opening,
                COALESCE(bt."Closing", 0) as closing
            FROM broker_transactions bt
            JOIN accounts a ON bt.account_id = a.account_id
            WHERE {where_clause}
            ORDER BY date
        """
        daily_trades_results = execute_query(daily_trades_query, tuple(params))

        # Aggregate daily P&L and points by date with currency conversion
        daily_pnl_map: Dict[str, float] = {}
        daily_points_map: Dict[str, float] = {}
        daily_trades_map: Dict[str, int] = {}
        for row in daily_trades_results:
            date = row["date"]
            currency = row.get("currency") or target_currency
            pnl = row.get("pnl") or 0
            instrument = row.get("instrument") or ""
            opening = row.get("opening") or 0
            closing = row.get("closing") or 0

            # Calculate points for this trade
            points = CurrencyService.calculate_points(
                opening, closing, pnl, instrument, point_factors
            )

            if currency != target_currency:
                converted = CurrencyService.convert(pnl, currency, target_currency)
                if converted is not None:
                    pnl = converted

            daily_pnl_map[date] = daily_pnl_map.get(date, 0) + pnl
            daily_points_map[date] = daily_points_map.get(date, 0) + points
            daily_trades_map[date] = daily_trades_map.get(date, 0) + 1

        daily_pnl_values = list(daily_pnl_map.values())
        daily_points_values = list(daily_points_map.values())
        daily_trades_values = list(daily_trades_map.values())
        num_days = len(daily_pnl_values)

        avg_daily_pnl = sum(daily_pnl_values) / num_days if num_days > 0 else 0
        avg_daily_points = sum(daily_points_values) / num_days if num_days > 0 else 0
        avg_trades_per_day = sum(daily_trades_values) / num_days if num_days > 0 else 0
        best_day_pnl = max(daily_pnl_values) if daily_pnl_values else 0
        worst_day_pnl = min(daily_pnl_values) if daily_pnl_values else 0

        # Get monthly P&L and points breakdown for best/worst month and average calculations
        monthly_trades_query = f"""
            SELECT
                strftime('%Y-%m', bt."Transaction Date") as month,
                a.currency as currency,
                bt."P/L" as pnl,
                bt."Description" as instrument,
                COALESCE(bt."Opening", 0) as opening,
                COALESCE(bt."Closing", 0) as closing
            FROM broker_transactions bt
            JOIN accounts a ON bt.account_id = a.account_id
            WHERE {where_clause}
            ORDER BY month
        """
        monthly_trades_results = execute_query(monthly_trades_query, tuple(params))

        # Aggregate monthly P&L and points by month with currency conversion
        monthly_pnl_map: Dict[str, float] = {}
        monthly_points_map: Dict[str, float] = {}
        monthly_trades_map: Dict[str, int] = {}
        for row in monthly_trades_results:
            month = row["month"]
            currency = row.get("currency") or target_currency
            pnl = row.get("pnl") or 0
            instrument = row.get("instrument") or ""
            opening = row.get("opening") or 0
            closing = row.get("closing") or 0

            # Calculate points for this trade
            points = CurrencyService.calculate_points(
                opening, closing, pnl, instrument, point_factors
            )

            if currency != target_currency:
                converted = CurrencyService.convert(pnl, currency, target_currency)
                if converted is not None:
                    pnl = converted

            monthly_pnl_map[month] = monthly_pnl_map.get(month, 0) + pnl
            monthly_points_map[month] = monthly_points_map.get(month, 0) + points
            monthly_trades_map[month] = monthly_trades_map.get(month, 0) + 1

        monthly_pnl_values = list(monthly_pnl_map.values())
        monthly_points_values = list(monthly_points_map.values())
        monthly_trades_values = list(monthly_trades_map.values())
        num_months = len(monthly_pnl_values)

        avg_monthly_pnl = sum(monthly_pnl_values) / num_months if num_months > 0 else 0
        avg_monthly_points = (
            sum(monthly_points_values) / num_months if num_months > 0 else 0
        )
        avg_trades_per_month = (
            sum(monthly_trades_values) / num_months if num_months > 0 else 0
        )
        best_month_pnl = max(monthly_pnl_values) if monthly_pnl_values else 0
        worst_month_pnl = min(monthly_pnl_values) if monthly_pnl_values else 0

        # Get yearly P&L and points breakdown for average calculations
        yearly_trades_query = f"""
            SELECT
                strftime('%Y', bt."Transaction Date") as year,
                a.currency as currency,
                bt."P/L" as pnl,
                bt."Description" as instrument,
                COALESCE(bt."Opening", 0) as opening,
                COALESCE(bt."Closing", 0) as closing
            FROM broker_transactions bt
            JOIN accounts a ON bt.account_id = a.account_id
            WHERE {where_clause}
            ORDER BY year
        """
        yearly_trades_results = execute_query(yearly_trades_query, tuple(params))

        # Aggregate yearly P&L and points by year with currency conversion
        yearly_pnl_map: Dict[str, float] = {}
        yearly_points_map: Dict[str, float] = {}
        for row in yearly_trades_results:
            year = row["year"]
            currency = row.get("currency") or target_currency
            pnl = row.get("pnl") or 0
            instrument = row.get("instrument") or ""
            opening = row.get("opening") or 0
            closing = row.get("closing") or 0

            # Calculate points for this trade
            points = CurrencyService.calculate_points(
                opening, closing, pnl, instrument, point_factors
            )

            if currency != target_currency:
                converted = CurrencyService.convert(pnl, currency, target_currency)
                if converted is not None:
                    pnl = converted

            yearly_pnl_map[year] = yearly_pnl_map.get(year, 0) + pnl
            yearly_points_map[year] = yearly_points_map.get(year, 0) + points

        yearly_pnl_values = list(yearly_pnl_map.values())
        yearly_points_values = list(yearly_points_map.values())
        num_years = len(yearly_pnl_values)

        current_year_str = str(today_dt.year)
        current_year_pnl = yearly_pnl_map.get(current_year_str, 0)
        current_year_points = yearly_points_map.get(current_year_str, 0)
        avg_yearly_pnl = sum(yearly_pnl_values) / num_years if num_years > 0 else 0

        # Get best/worst trade
        best_trade_query = f"""
            SELECT a.currency, bt."P/L" as pnl
            FROM broker_transactions bt
            JOIN accounts a ON bt.account_id = a.account_id
            WHERE {where_clause}
            ORDER BY bt."P/L" DESC
            LIMIT 1
        """
        best_result = execute_query(best_trade_query, tuple(params))
        best_trade = 0.0
        if best_result:
            currency = best_result[0].get("currency") or target_currency
            pnl = best_result[0].get("pnl") or 0
            if currency != target_currency:
                converted = CurrencyService.convert(pnl, currency, target_currency)
                if converted is not None:
                    pnl = converted
            best_trade = pnl

        worst_trade_query = f"""
            SELECT a.currency, bt."P/L" as pnl
            FROM broker_transactions bt
            JOIN accounts a ON bt.account_id = a.account_id
            WHERE {where_clause}
            ORDER BY bt."P/L" ASC
            LIMIT 1
        """
        worst_result = execute_query(worst_trade_query, tuple(params))
        worst_trade = 0.0
        if worst_result:
            currency = worst_result[0].get("currency") or target_currency
            pnl = worst_result[0].get("pnl") or 0
            if currency != target_currency:
                converted = CurrencyService.convert(pnl, currency, target_currency)
                if converted is not None:
                    pnl = converted
            worst_trade = pnl

        return {
            "totalPnl": total_pnl,
            "totalTrades": total_trades,
            "winningTrades": winning_trades,
            "losingTrades": losing_trades,
            "winRate": win_rate,
            "avgWin": avg_win,
            "avgLoss": avg_loss,
            "profitFactor": profit_factor,
            "maxDrawdown": max_drawdown,
            "avgPnlPerTrade": avg_pnl,
            "dailyAvgPnl": daily_avg,
            "bestTrade": best_trade,
            "worstTrade": worst_trade,
            "maxBalance": max_balance,
            "minBalance": min_balance,
            "todayPnl": today_pnl,
            "todayTrades": today_trades,
            "weekPnl": week_pnl,
            "weekTrades": week_trades,
            "monthPnl": month_pnl,
            "monthTrades": month_trades,
            "monthWinRate": (month_wins / month_trades * 100)
            if month_trades > 0
            else 0,
            "yearPnl": year_pnl,
            "yearTrades": year_trades,
            "yearWinRate": (year_wins / year_trades * 100) if year_trades > 0 else 0,
            "tradingDays": trading_days,
            "currency": target_currency,
            # Daily averages (for frontend compatibility)
            "avgDailyPnl": avg_daily_pnl,
            "avgDailyPoints": avg_daily_points,
            "avgTradesPerDay": avg_trades_per_day,
            "bestDayPnl": best_day_pnl,
            "worstDayPnl": worst_day_pnl,
            # Monthly averages
            "avgMonthlyPnl": avg_monthly_pnl,
            "avgMonthlyPoints": avg_monthly_points,
            "avgTradesPerMonth": avg_trades_per_month,
            "bestMonthPnl": best_month_pnl,
            "worstMonthPnl": worst_month_pnl,
            # Yearly summary
            "currentYearPnl": current_year_pnl,
            "currentYearPoints": current_year_points,
            "avgYearlyPnl": avg_yearly_pnl,
            # Legacy fields for backward compatibility
            "openPositions": 0,
            "totalExposure": 0,
            "avgTradeDuration": 0,
        }

    @staticmethod
    def get_available_instruments(
        start_date: Optional[datetime] = None, end_date: Optional[datetime] = None
    ) -> List[str]:
        """Get list of all instruments traded."""
        conditions = []
        params: List[Any] = []

        if start_date:
            conditions.append('"Transaction Date" >= ?')
            params.append(start_date.isoformat())

        if end_date:
            conditions.append('"Transaction Date" <= ?')
            params.append(format_end_date(end_date))

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        query = f"""
            SELECT DISTINCT "Description" as instrument
            FROM broker_transactions
            WHERE {where_clause}
            ORDER BY instrument
        """

        results = execute_query(query, tuple(params))
        return [r["instrument"] for r in results if r["instrument"]]

    @staticmethod
    def get_accounts() -> List[Dict[str, Any]]:
        """Get list of all accounts."""
        query = """
            SELECT account_id, account_name, broker_name, currency, initial_balance, notes
            FROM accounts
            ORDER BY account_name
        """
        return execute_query(query)

    @staticmethod
    def get_equity_curve(
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        target_currency: Optional[str] = None,
        account_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Get equity curve data (cumulative P&L over time)."""
        from api.services.currency import CurrencyService

        # Require explicit currency - no auto-detection per .rules
        if target_currency is None:
            raise ValueError("target_currency is required - no auto-detection allowed")

        conditions = [
            "bt.\"Action\" NOT LIKE '%Fund%' AND bt.\"Action\" NOT LIKE '%Charge%' "
            "AND bt.\"Action\" NOT LIKE '%Deposit%' AND bt.\"Action\" NOT LIKE '%Withdraw%'"
        ]
        params: List[Any] = []

        if start_date:
            conditions.append('bt."Transaction Date" >= ?')
            params.append(start_date.isoformat())

        if end_date:
            conditions.append('bt."Transaction Date" <= ?')
            params.append(format_end_date(end_date))

        # Add account filter
        conditions.append(
            _build_included_accounts_filter(account_id, params, table_alias="bt")
        )

        where_clause = " AND ".join(conditions)

        query = f"""
            SELECT
                DATE(bt."Transaction Date") as date,
                a.currency as currency,
                SUM(bt."P/L") as daily_pnl
            FROM broker_transactions bt
            JOIN accounts a ON bt.account_id = a.account_id
            WHERE {where_clause}
            GROUP BY DATE(bt."Transaction Date"), a.currency
            ORDER BY date ASC
        """

        raw_data = execute_query(query, tuple(params))

        # Aggregate by date with currency conversion
        date_pnl: Dict[str, float] = {}
        for row in raw_data:
            date_str = row["date"]
            currency = row["currency"] or target_currency
            pnl = row["daily_pnl"] or 0

            if currency != target_currency:
                converted = CurrencyService.convert(pnl, currency, target_currency)
                if converted is not None:
                    pnl = converted

            date_pnl[date_str] = date_pnl.get(date_str, 0) + pnl

        # Build cumulative equity curve
        data = []
        cumulative = 0
        for date_str in sorted(date_pnl.keys()):
            cumulative += date_pnl[date_str]
            data.append({"date": date_str, "balance": cumulative})

        return {
            "data": data,
            "currency": target_currency,
        }

    @staticmethod
    def get_daily_pnl(
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        target_currency: Optional[str] = None,
        account_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Get daily P&L data with percentage based on balance at trade open time.

        The P&L percentage is calculated using the account balance at the moment
        each trade was opened (Open Period), not when it was closed.

        Converts all P&L values to the target currency before aggregating.
        Requires target_currency to be specified - no auto-detection.
        """
        from api.services.currency import CurrencyService

        # Require explicit currency - no auto-detection per .rules
        if target_currency is None:
            raise ValueError("target_currency is required - no auto-detection allowed")

        conditions = [
            "bt.\"Action\" NOT LIKE '%Fund%' AND bt.\"Action\" NOT LIKE '%Charge%' "
            "AND bt.\"Action\" NOT LIKE '%Deposit%' AND bt.\"Action\" NOT LIKE '%Withdraw%'"
        ]
        params: List[Any] = []

        if start_date:
            conditions.append('bt."Transaction Date" >= ?')
            params.append(start_date.isoformat())

        if end_date:
            conditions.append('bt."Transaction Date" <= ?')
            params.append(format_end_date(end_date))

        # Add account filter
        conditions.append(
            _build_included_accounts_filter(account_id, params, table_alias="bt")
        )

        where_clause = " AND ".join(conditions)

        # Build balance history conditions
        balance_history_params: List[Any] = []
        balance_account_filter = _build_included_accounts_filter(
            account_id, balance_history_params, table_alias="bt"
        )

        # Get all transactions ordered by time to build balance history
        balance_history_query = f"""
            SELECT
                bt."Transaction Date" as txn_date,
                bt.account_id,
                a.currency as currency,
                bt."Balance" as balance
            FROM broker_transactions bt
            JOIN accounts a ON bt.account_id = a.account_id
            WHERE {balance_account_filter}
            ORDER BY bt."Transaction Date" ASC
        """
        balance_history_data = execute_query(
            balance_history_query, tuple(balance_history_params)
        )

        # Build a sorted list of (datetime, balance) tuples for binary search
        # Convert balances to target currency as we build the timeline
        timeline_data: List[Tuple[str, float]] = []
        for row in balance_history_data:
            txn_date = row["txn_date"]
            currency = row["currency"] or target_currency
            balance = row["balance"] or 0

            # Convert balance to target currency
            if currency != target_currency:
                converted = CurrencyService.convert(balance, currency, target_currency)
                if converted is not None:
                    balance = converted

            timeline_data.append((txn_date, balance))

        # Create efficient balance lookup using binary search
        balance_timeline = BalanceTimeline(timeline_data)

        # Get individual trades with their open period for percentage calculation
        trades_query = f"""
            SELECT
                DATE(bt."Transaction Date") as close_date,
                bt."Open Period" as open_period,
                bt."P/L" as pnl,
                a.currency as currency
            FROM broker_transactions bt
            JOIN accounts a ON bt.account_id = a.account_id
            WHERE {where_clause}
            ORDER BY bt."Transaction Date" ASC
        """
        trades_data = execute_query(trades_query, tuple(params))

        # Aggregate by date, calculating weighted percentage based on balance at open
        date_map: Dict[str, Dict[str, Any]] = {}
        for row in trades_data:
            close_date = row["close_date"]
            open_period = row["open_period"]
            pnl = row["pnl"] or 0
            currency = row["currency"] or target_currency

            # Convert P&L to target currency
            if currency != target_currency:
                converted = CurrencyService.convert(pnl, currency, target_currency)
                if converted is not None:
                    pnl = converted

            if close_date not in date_map:
                date_map[close_date] = {
                    "date": close_date,
                    "pnl": 0,
                    "trades": 0,
                    "weighted_pnl_percent": 0,
                    "total_open_balance": 0,
                }

            date_map[close_date]["pnl"] += pnl
            date_map[close_date]["trades"] += 1

            # Find balance at the time trade was opened using binary search
            balance_at_open = balance_timeline.find_balance_at_time(open_period)
            if balance_at_open and balance_at_open > 0:
                # Calculate percentage for this trade based on balance when opened
                trade_percent = (pnl / balance_at_open) * 100
                date_map[close_date]["weighted_pnl_percent"] += trade_percent
                date_map[close_date]["total_open_balance"] += balance_at_open

        # Sort by date and calculate cumulative P&L
        daily_pnl = sorted(date_map.values(), key=lambda x: x["date"])
        cumulative = 0
        for entry in daily_pnl:
            cumulative += entry["pnl"]
            entry["cumulativePnl"] = cumulative
            entry["currency"] = target_currency

            # Calculate average percentage for the day
            # This is the sum of individual trade percentages
            if entry["trades"] > 0 and entry["total_open_balance"] > 0:
                # Use the weighted sum of percentages
                entry["pnlPercent"] = entry["weighted_pnl_percent"]
                # Store average balance at open for reference
                entry["previousBalance"] = entry["total_open_balance"] / entry["trades"]
            else:
                entry["pnlPercent"] = None
                entry["previousBalance"] = None

            # Clean up internal fields
            del entry["weighted_pnl_percent"]
            del entry["total_open_balance"]

        return daily_pnl

    @staticmethod
    def get_daily_pnl_by_account(
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        target_currency: Optional[str] = None,
        account_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Get daily P&L broken down by account for stacked area charting."""
        from api.services.currency import CurrencyService

        # Require explicit currency - no auto-detection per .rules
        if target_currency is None:
            raise ValueError("target_currency is required - no auto-detection allowed")

        conditions = [
            "bt.\"Action\" NOT LIKE '%Fund%' AND bt.\"Action\" NOT LIKE '%Charge%' "
            "AND bt.\"Action\" NOT LIKE '%Deposit%' AND bt.\"Action\" NOT LIKE '%Withdraw%'"
        ]
        params: List[Any] = []

        if start_date:
            conditions.append('bt."Transaction Date" >= ?')
            params.append(start_date.isoformat())

        if end_date:
            conditions.append('bt."Transaction Date" <= ?')
            params.append(format_end_date(end_date))

        # Add account filter
        conditions.append(
            _build_included_accounts_filter(account_id, params, table_alias="bt")
        )

        where_clause = " AND ".join(conditions)

        # Get account info
        if account_id:
            accounts_query = """
                SELECT a.account_id, a.account_name, a.currency
                FROM accounts a
                WHERE a.account_id = ?
            """
            accounts = execute_query(accounts_query, (account_id,))
        else:
            included_ids = get_included_account_ids()
            if included_ids:
                placeholders = ",".join("?" * len(included_ids))
                accounts_query = f"""
                    SELECT a.account_id, a.account_name, a.currency
                    FROM accounts a
                    WHERE a.account_id IN ({placeholders})
                """
                accounts = execute_query(accounts_query, tuple(included_ids))
            else:
                accounts = []

        account_info: Dict[int, Dict[str, Any]] = {}
        for acc in accounts:
            account_info[acc["account_id"]] = {
                "name": acc["account_name"] or f"Account {acc['account_id']}",
                "currency": acc["currency"],
            }

        # Get daily P&L per account
        query = f"""
            SELECT
                DATE(bt."Transaction Date") as date,
                bt.account_id,
                SUM(bt."P/L") as pnl,
                COUNT(*) as trades
            FROM broker_transactions bt
            WHERE {where_clause}
            GROUP BY DATE(bt."Transaction Date"), bt.account_id
            ORDER BY date ASC
        """

        raw_data = execute_query(query, tuple(params))

        # Collect all dates and per-account P&L
        all_dates: set = set()
        account_date_pnl: Dict[int, Dict[str, Dict[str, Any]]] = {
            aid: {} for aid in account_info
        }

        for row in raw_data:
            date_str = row["date"]
            acct_id = row["account_id"]
            if acct_id in account_info:
                all_dates.add(date_str)
                acct_currency = account_info[acct_id]["currency"]
                pnl = row["pnl"] or 0

                # Convert to target currency
                if acct_currency and acct_currency != target_currency:
                    converted = CurrencyService.convert(
                        pnl, acct_currency, target_currency
                    )
                    if converted is not None:
                        pnl = converted

                account_date_pnl[acct_id][date_str] = {
                    "pnl": pnl,
                    "trades": row["trades"],
                }

        sorted_dates = sorted(all_dates)

        # Build series with cumulative P&L per account
        series = []
        total_by_date: Dict[str, Dict[str, Any]] = {}

        for acct_id, date_data in account_date_pnl.items():
            data_points = []
            cumulative = 0

            for date_str in sorted_dates:
                if date_str in date_data:
                    pnl = date_data[date_str]["pnl"]
                    trades = date_data[date_str]["trades"]
                else:
                    pnl = 0
                    trades = 0

                cumulative += pnl
                data_points.append(
                    {
                        "date": date_str,
                        "pnl": pnl,
                        "cumulativePnl": cumulative,
                        "trades": trades,
                    }
                )

                # Aggregate totals
                if date_str not in total_by_date:
                    total_by_date[date_str] = {"pnl": 0, "trades": 0}
                total_by_date[date_str]["pnl"] += pnl
                total_by_date[date_str]["trades"] += trades

            series.append(
                {
                    "accountId": acct_id,
                    "accountName": account_info[acct_id]["name"],
                    "data": data_points,
                }
            )

        # Build total with cumulative
        total_cumulative = 0
        total_data = []
        for date_str in sorted_dates:
            if date_str in total_by_date:
                total_cumulative += total_by_date[date_str]["pnl"]
                total_data.append(
                    {
                        "date": date_str,
                        "pnl": total_by_date[date_str]["pnl"],
                        "cumulativePnl": total_cumulative,
                        "trades": total_by_date[date_str]["trades"],
                    }
                )

        return {
            "series": series,
            "total": total_data,
            "currency": target_currency,
        }


# Create singleton instance
db = TradingDatabase()
