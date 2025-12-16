"""
Database service for accessing trading data.

Provides methods to query the SQLite database and return data
in formats suitable for the API responses.
"""

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from db_path import DATABASE_PATH


@contextmanager
def get_db_connection():
    """Context manager for database connections."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def get_dataframe(query: str, params: Optional[Tuple] = None) -> pd.DataFrame:
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
            params.append(end_date.isoformat())

        if instruments:
            placeholders = ",".join("?" * len(instruments))
            conditions.append(f'"Description" IN ({placeholders})')
            params.extend(instruments)

        if account_id:
            conditions.append("account_id = ?")
            params.append(account_id)

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
        """Get a single trade by ID."""
        query = """
            SELECT
                "Ref. No." as id,
                "Description" as instrument,
                "Action" as action,
                "Opening" as entry_price,
                "Closing" as exit_price,
                "Open Period" as entry_time,
                "Transaction Date" as exit_time,
                "Amount" as quantity,
                "P/L" as pnl,
                CASE WHEN "Opening" > 0 THEN ("P/L" / "Opening") * 100 ELSE 0 END as pnl_percent,
                "Status" as status,
                broker_name,
                "Currency" as currency
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
        params = []

        if start_date:
            conditions.append('"Transaction Date" >= ?')
            params.append(start_date.isoformat())

        if end_date:
            conditions.append('"Transaction Date" <= ?')
            params.append(end_date.isoformat())

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
                WHERE EXISTS (
                    SELECT 1 FROM broker_transactions bt
                    WHERE bt.account_id = a.account_id
                )
            """
            all_accounts = execute_query(all_accounts_query, ())

        account_currencies: Dict[int, str] = {}
        for acc in all_accounts:
            account_currencies[acc["account_id"]] = acc["currency"]

        # Get initial balance for each account BEFORE the start_date
        # This is the balance to carry forward from the beginning
        initial_balances: Dict[int, float] = {}
        for acct_id in account_currencies:
            if start_date:
                # Get the last balance before start_date
                init_query = """
                    SELECT "Balance" as balance
                    FROM broker_transactions
                    WHERE account_id = ? AND "Transaction Date" < ?
                    ORDER BY "Transaction Date" DESC, "Transaction ID" DESC
                    LIMIT 1
                """
                init_result = execute_query(
                    init_query, (acct_id, start_date.isoformat())
                )
                if init_result:
                    initial_balances[acct_id] = init_result[0]["balance"] or 0
                else:
                    # No transactions before start_date, check if there's an initial_balance in accounts
                    acc_query = (
                        "SELECT initial_balance FROM accounts WHERE account_id = ?"
                    )
                    acc_result = execute_query(acc_query, (acct_id,))
                    if acc_result and acc_result[0]["initial_balance"]:
                        initial_balances[acct_id] = acc_result[0]["initial_balance"]
                    else:
                        initial_balances[acct_id] = 0
            else:
                initial_balances[acct_id] = 0

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
        """Get balance history per account for multi-account charting."""
        from api.services.currency import CurrencyService

        # Require explicit currency - no auto-detection per .rules
        if target_currency is None:
            raise ValueError("target_currency is required - no auto-detection allowed")

        conditions = ["1=1"]
        params = []

        if start_date:
            conditions.append('"Transaction Date" >= ?')
            params.append(start_date.isoformat())

        if end_date:
            conditions.append('"Transaction Date" <= ?')
            params.append(end_date.isoformat())

        where_clause = " AND ".join(conditions)

        # Get all accounts with their info (or just the selected one)
        if account_id:
            accounts_query = """
                SELECT a.account_id, a.account_name, a.broker_name, a.currency, a.initial_balance
                FROM accounts a
                WHERE a.account_id = ?
            """
            accounts = execute_query(accounts_query, (account_id,))
        else:
            accounts_query = """
                SELECT a.account_id, a.account_name, a.broker_name, a.currency, a.initial_balance
                FROM accounts a
                WHERE EXISTS (
                    SELECT 1 FROM broker_transactions bt
                    WHERE bt.account_id = a.account_id
                )
            """
            accounts = execute_query(accounts_query, ())

        # Get initial balance for each account BEFORE the start_date
        initial_balances: Dict[int, float] = {}
        for account in accounts:
            acc_id = account["account_id"]
            if start_date:
                # Get the last balance before start_date
                init_query = """
                    SELECT "Balance" as balance
                    FROM broker_transactions
                    WHERE account_id = ? AND "Transaction Date" < ?
                    ORDER BY "Transaction Date" DESC, "Transaction ID" DESC
                    LIMIT 1
                """
                init_result = execute_query(
                    init_query, (acc_id, start_date.isoformat())
                )
                if init_result:
                    initial_balances[acc_id] = init_result[0]["balance"] or 0
                elif account["initial_balance"]:
                    initial_balances[acc_id] = account["initial_balance"]
                else:
                    initial_balances[acc_id] = 0
            else:
                initial_balances[acc_id] = 0

        # Collect all dates across all accounts first
        all_dates: set = set()
        account_raw_data: Dict[int, List[Dict]] = {}

        for account in accounts:
            acc_id = account["account_id"]

            query = f"""
                SELECT
                    DATE(bt."Transaction Date") as date,
                    bt."Balance" as balance
                FROM broker_transactions bt
                INNER JOIN (
                    SELECT DATE("Transaction Date") as txn_date, MAX("Transaction Date") as last_txn_time
                    FROM broker_transactions
                    WHERE account_id = ?
                    GROUP BY DATE("Transaction Date")
                ) last_txn ON bt."Transaction Date" = last_txn.last_txn_time
                WHERE {where_clause} AND bt.account_id = ?
                ORDER BY date ASC
            """
            acc_params = [acc_id] + list(params) + [acc_id]
            data = execute_query(query, tuple(acc_params))

            account_raw_data[acc_id] = data
            for row in data:
                all_dates.add(row["date"])

        sorted_dates = sorted(all_dates)

        # Build series with carry-forward logic
        series = []
        for account in accounts:
            acc_id = account["account_id"]
            acc_name = account["account_name"] or f"Account {acc_id}"
            acc_currency = account["currency"]

            # Build date->balance map from raw data
            date_balance_map: Dict[str, float] = {}
            for row in account_raw_data[acc_id]:
                date_balance_map[row["date"]] = row["balance"] or 0

            # Carry forward balances for all dates
            carried_data = []
            last_balance = initial_balances.get(acc_id, 0)
            for date_str in sorted_dates:
                if date_str in date_balance_map:
                    last_balance = date_balance_map[date_str]
                carried_data.append({"date": date_str, "balance": last_balance})

            # Convert balances if target currency specified and different from account currency
            if carried_data:
                if target_currency and acc_currency and acc_currency != target_currency:
                    rate = CurrencyService.get_exchange_rate(
                        acc_currency, target_currency
                    )
                    if rate:
                        carried_data = [
                            {"date": p["date"], "balance": p["balance"] * rate}
                            for p in carried_data
                        ]

                series.append(
                    {
                        "accountId": acc_id,
                        "accountName": acc_name,
                        "currency": target_currency or acc_currency,
                        "data": carried_data,
                    }
                )

        # Calculate total balance by summing converted series data
        # This ensures proper currency conversion for the total
        total_by_date: Dict[str, float] = {}
        for s in series:
            for point in s["data"]:
                date_str = point["date"]
                balance = point["balance"] or 0
                if date_str in total_by_date:
                    total_by_date[date_str] += balance
                else:
                    total_by_date[date_str] = balance

        total_data = [
            {"date": date, "balance": balance}
            for date, balance in sorted(total_by_date.items())
        ]

        return {
            "series": series,
            "total": {
                "accountName": "Total",
                "data": total_data,
            },
        }

    @staticmethod
    def get_monthly_pnl_by_account(
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        target_currency: str = None,
        account_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Get monthly P&L per account for multi-account charting.

        Converts all P&L values to target_currency before aggregating totals.
        Requires target_currency to be specified - no auto-detection per .rules.
        """
        from api.services.currency import CurrencyService

        # Require explicit currency - no auto-detection per .rules
        if target_currency is None:
            raise ValueError("target_currency is required - no auto-detection allowed")

        conditions = [
            "bt.\"Action\" NOT LIKE '%Fund%' AND bt.\"Action\" NOT LIKE '%Charge%' "
            "AND bt.\"Action\" NOT LIKE '%Deposit%' AND bt.\"Action\" NOT LIKE '%Withdraw%'"
        ]
        params = []

        if start_date:
            conditions.append('bt."Transaction Date" >= ?')
            params.append(start_date.isoformat())

        if end_date:
            conditions.append('bt."Transaction Date" <= ?')
            params.append(end_date.isoformat())

        if account_id:
            conditions.append("bt.account_id = ?")
            params.append(account_id)

        where_clause = " AND ".join(conditions)

        # Get all accounts with their info
        accounts_query = """
            SELECT a.account_id, a.account_name, a.broker_name, a.currency
            FROM accounts a
            WHERE EXISTS (
                SELECT 1 FROM broker_transactions bt
                WHERE bt.account_id = a.account_id
            )
        """
        accounts = execute_query(accounts_query, ())

        # Get monthly P&L per account
        series = []
        for account in accounts:
            acc_id = account["account_id"]
            acc_name = account["account_name"] or f"Account {acc_id}"
            acc_currency = account["currency"]

            query = f"""
                SELECT
                    strftime('%Y-%m', bt."Transaction Date") as month_key,
                    CASE CAST(strftime('%m', bt."Transaction Date") AS INTEGER)
                        WHEN 1 THEN 'Jan' WHEN 2 THEN 'Feb' WHEN 3 THEN 'Mar'
                        WHEN 4 THEN 'Apr' WHEN 5 THEN 'May' WHEN 6 THEN 'Jun'
                        WHEN 7 THEN 'Jul' WHEN 8 THEN 'Aug' WHEN 9 THEN 'Sep'
                        WHEN 10 THEN 'Oct' WHEN 11 THEN 'Nov' WHEN 12 THEN 'Dec'
                    END || ' ' || strftime('%Y', bt."Transaction Date") as month,
                    SUM(bt."P/L") as pnl,
                    COUNT(*) as trades,
                    ROUND(
                        CAST(SUM(CASE WHEN bt."P/L" >= 0 THEN 1 ELSE 0 END) AS FLOAT) /
                        CAST(COUNT(*) AS FLOAT) * 100,
                        1
                    ) as winRate
                FROM broker_transactions bt
                WHERE {where_clause} AND bt.account_id = ?
                GROUP BY month_key
                ORDER BY month_key ASC
            """
            acc_params = list(params) + [acc_id]
            data = execute_query(query, tuple(acc_params))

            if data:
                series.append(
                    {
                        "accountId": acc_id,
                        "accountName": acc_name,
                        "currency": acc_currency,
                        "data": data,
                    }
                )

        # Calculate total monthly P&L with proper currency conversion
        # Group by month and currency, then convert and aggregate
        total_query = f"""
            SELECT
                strftime('%Y-%m', bt."Transaction Date") as month_key,
                CASE CAST(strftime('%m', bt."Transaction Date") AS INTEGER)
                    WHEN 1 THEN 'Jan' WHEN 2 THEN 'Feb' WHEN 3 THEN 'Mar'
                    WHEN 4 THEN 'Apr' WHEN 5 THEN 'May' WHEN 6 THEN 'Jun'
                    WHEN 7 THEN 'Jul' WHEN 8 THEN 'Aug' WHEN 9 THEN 'Sep'
                    WHEN 10 THEN 'Oct' WHEN 11 THEN 'Nov' WHEN 12 THEN 'Dec'
                END || ' ' || strftime('%Y', bt."Transaction Date") as month,
                a.currency as account_currency,
                SUM(bt."P/L") as pnl,
                COUNT(*) as trades,
                SUM(CASE WHEN bt."P/L" >= 0 THEN 1 ELSE 0 END) as wins
            FROM broker_transactions bt
            JOIN accounts a ON bt.account_id = a.account_id
            WHERE {where_clause}
            GROUP BY month_key, a.currency
            ORDER BY month_key ASC
        """
        raw_total_data = execute_query(total_query, tuple(params))

        # Aggregate by month, converting currencies to target_currency
        month_totals: Dict[str, Dict[str, Any]] = {}
        for row in raw_total_data:
            month_key = row["month_key"]
            month = row["month"]
            currency = row["account_currency"] or target_currency
            pnl = row["pnl"] or 0
            trades = row["trades"] or 0
            wins = row["wins"] or 0

            # Convert P&L to target currency
            if currency != target_currency:
                converted = CurrencyService.convert(pnl, currency, target_currency)
                if converted is not None:
                    pnl = converted

            if month_key not in month_totals:
                month_totals[month_key] = {
                    "month_key": month_key,
                    "month": month,
                    "pnl": 0,
                    "trades": 0,
                    "wins": 0,
                }

            month_totals[month_key]["pnl"] += pnl
            month_totals[month_key]["trades"] += trades
            month_totals[month_key]["wins"] += wins

        # Build total data with win rates
        total_data = []
        for month_key in sorted(month_totals.keys()):
            entry = month_totals[month_key]
            win_rate = (
                round((entry["wins"] / entry["trades"]) * 100, 1)
                if entry["trades"] > 0
                else 0
            )
            total_data.append(
                {
                    "month_key": entry["month_key"],
                    "month": entry["month"],
                    "pnl": entry["pnl"],
                    "trades": entry["trades"],
                    "winRate": win_rate,
                }
            )

        return {
            "series": series,
            "total": {
                "accountName": "Total",
                "currency": target_currency,
                "data": total_data,
            },
        }

    @staticmethod
    def get_monthly_pnl(
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        instruments: Optional[List[str]] = None,
        target_currency: Optional[str] = None,
        account_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Get P&L aggregated by month with currency conversion.

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
        params = []

        if start_date:
            conditions.append('bt."Transaction Date" >= ?')
            params.append(start_date.isoformat())

        if end_date:
            conditions.append('bt."Transaction Date" <= ?')
            params.append(end_date.isoformat())

        if instruments:
            placeholders = ",".join("?" * len(instruments))
            conditions.append(f'bt."Description" IN ({placeholders})')
            params.extend(instruments)

        if account_id:
            conditions.append("bt.account_id = ?")
            params.append(account_id)

        where_clause = " AND ".join(conditions)

        # Get monthly P&L grouped by month AND account currency
        # Use account currency (not transaction currency) for proper multi-account conversion
        query = f"""
            SELECT
                strftime('%Y-%m', bt."Transaction Date") as month_key,
                CASE CAST(strftime('%m', bt."Transaction Date") AS INTEGER)
                    WHEN 1 THEN 'Jan' WHEN 2 THEN 'Feb' WHEN 3 THEN 'Mar'
                    WHEN 4 THEN 'Apr' WHEN 5 THEN 'May' WHEN 6 THEN 'Jun'
                    WHEN 7 THEN 'Jul' WHEN 8 THEN 'Aug' WHEN 9 THEN 'Sep'
                    WHEN 10 THEN 'Oct' WHEN 11 THEN 'Nov' WHEN 12 THEN 'Dec'
                END || ' ' || strftime('%Y', bt."Transaction Date") as month,
                a.currency as currency,
                SUM(bt."P/L") as pnl,
                COUNT(*) as trades,
                SUM(CASE WHEN bt."P/L" >= 0 THEN 1 ELSE 0 END) as wins
            FROM broker_transactions bt
            JOIN accounts a ON bt.account_id = a.account_id
            WHERE {where_clause}
            GROUP BY month_key, a.currency
            ORDER BY month_key ASC
        """

        raw_data = execute_query(query, tuple(params))

        # Aggregate by month, converting currencies
        month_map: Dict[str, Dict[str, Any]] = {}
        for row in raw_data:
            month_key = row["month_key"]
            month = row["month"]
            currency = row["currency"] or target_currency
            pnl = row["pnl"] or 0
            trades = row["trades"] or 0
            wins = row["wins"] or 0

            # Convert P&L to target currency
            if currency != target_currency:
                converted = CurrencyService.convert(pnl, currency, target_currency)
                if converted is not None:
                    pnl = converted

            if month_key not in month_map:
                month_map[month_key] = {
                    "month_key": month_key,
                    "month": month,
                    "pnl": 0,
                    "trades": 0,
                    "wins": 0,
                }

            month_map[month_key]["pnl"] += pnl
            month_map[month_key]["trades"] += trades
            month_map[month_key]["wins"] += wins

        # Calculate win rate and sort
        data = []
        for month_key in sorted(month_map.keys()):
            entry = month_map[month_key]
            win_rate = (
                round((entry["wins"] / entry["trades"]) * 100, 1)
                if entry["trades"] > 0
                else 0
            )
            data.append(
                {
                    "month_key": entry["month_key"],
                    "month": entry["month"],
                    "pnl": entry["pnl"],
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
        """Get win rate statistics per instrument."""
        conditions = [
            "\"Action\" NOT LIKE '%Fund%' AND \"Action\" NOT LIKE '%Charge%' "
            "AND \"Action\" NOT LIKE '%Deposit%' AND \"Action\" NOT LIKE '%Withdraw%'"
        ]
        params = []

        if start_date:
            conditions.append('"Transaction Date" >= ?')
            params.append(start_date.isoformat())

        if end_date:
            conditions.append('"Transaction Date" <= ?')
            params.append(end_date.isoformat())

        if account_id:
            conditions.append("account_id = ?")
            params.append(account_id)

        where_clause = " AND ".join(conditions)

        query = f"""
            SELECT
                "Description" as name,
                COUNT(*) as trades,
                SUM(CASE WHEN "P/L" >= 0 THEN 1 ELSE 0 END) as wins,
                SUM(CASE WHEN "P/L" < 0 THEN 1 ELSE 0 END) as losses,
                ROUND(
                    CAST(SUM(CASE WHEN "P/L" >= 0 THEN 1 ELSE 0 END) AS FLOAT) /
                    CAST(COUNT(*) AS FLOAT) * 100,
                    1
                ) as winRate,
                SUM("P/L") as totalPnl
            FROM broker_transactions
            WHERE {where_clause}
            GROUP BY "Description"
            HAVING trades >= 5
            ORDER BY trades DESC
            LIMIT 10
        """

        return execute_query(query, tuple(params))

    @staticmethod
    def get_points_by_instrument(
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        account_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get points/pips statistics per instrument.

        Points are calculated using CurrencyService.calculate_points(),
        which is the SINGLE SOURCE OF TRUTH for points calculation.
        Point factors are user-configurable via Settings.
        """
        from api.services.currency import CurrencyService

        # Fetch point factors ONCE before processing trades
        point_factors = CurrencyService.get_instrument_point_factors()

        conditions = [
            "\"Action\" NOT LIKE '%Fund%' AND \"Action\" NOT LIKE '%Charge%' "
            "AND \"Action\" NOT LIKE '%Deposit%' AND \"Action\" NOT LIKE '%Withdraw%'",
            '"Opening" IS NOT NULL AND "Opening" > 0',
            '"Closing" IS NOT NULL AND "Closing" > 0',
        ]
        params = []

        if account_id:
            conditions.append("account_id = ?")
            params.append(account_id)

        if start_date:
            conditions.append('"Transaction Date" >= ?')
            params.append(start_date.isoformat())

        if end_date:
            conditions.append('"Transaction Date" <= ?')
            params.append(end_date.isoformat())

        where_clause = " AND ".join(conditions)

        query = f"""
            SELECT
                "Description" as name,
                "Action" as action,
                "Opening" as entry_price,
                "Closing" as exit_price,
                "P/L" as pnl,
                "Amount" as amount
            FROM broker_transactions
            WHERE {where_clause}
        """

        trades = execute_query(query, tuple(params))

        # Group by instrument and calculate points
        instrument_stats: Dict[str, Dict[str, Any]] = {}

        for trade in trades:
            name = trade["name"]
            entry = trade["entry_price"] or 0
            exit_price = trade["exit_price"] or 0
            pnl = trade["pnl"] or 0

            if entry == 0 or exit_price == 0:
                continue

            # Calculate points using single source of truth (with pre-fetched factors)
            points = CurrencyService.calculate_points(
                entry, exit_price, pnl, name, point_factors
            )

            # Initialize instrument stats if needed
            if name not in instrument_stats:
                instrument_stats[name] = {
                    "name": name,
                    "totalPoints": 0,
                    "winPoints": 0,
                    "lossPoints": 0,
                    "trades": 0,
                    "wins": 0,
                    "losses": 0,
                    "avgPointsPerTrade": 0,
                    "avgWinPoints": 0,
                    "avgLossPoints": 0,
                }

            stats = instrument_stats[name]
            stats["totalPoints"] += points
            stats["trades"] += 1

            if pnl >= 0:
                stats["winPoints"] += points
                stats["wins"] += 1
            else:
                stats["lossPoints"] += points
                stats["losses"] += 1

        # Calculate averages
        results = []
        for name, stats in instrument_stats.items():
            if stats["trades"] >= 3:  # Minimum trades threshold
                stats["avgPointsPerTrade"] = round(
                    stats["totalPoints"] / stats["trades"], 2
                )
                stats["avgWinPoints"] = (
                    round(stats["winPoints"] / stats["wins"], 2)
                    if stats["wins"] > 0
                    else 0
                )
                stats["avgLossPoints"] = (
                    round(stats["lossPoints"] / stats["losses"], 2)
                    if stats["losses"] > 0
                    else 0
                )
                stats["totalPoints"] = round(stats["totalPoints"], 2)
                stats["winPoints"] = round(stats["winPoints"], 2)
                stats["lossPoints"] = round(stats["lossPoints"], 2)
                results.append(stats)

        # Sort by total trades descending
        results.sort(key=lambda x: x["trades"], reverse=True)

        return results[:10]  # Top 10 instruments

    @staticmethod
    def _calculate_max_drawdown(
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        instruments: Optional[List[str]] = None,
        account_id: Optional[int] = None,
    ) -> float:
        """
        Calculate maximum drawdown as peak-to-trough percentage decline.

        Uses cumulative P/L (equity curve) rather than account balance to avoid
        issues with deposits/withdrawals and negative balances.

        Returns the largest percentage drop from a peak to a subsequent trough.
        """
        conditions = [
            "\"Action\" NOT LIKE '%Fund%' AND \"Action\" NOT LIKE '%Charge%' "
            "AND \"Action\" NOT LIKE '%Deposit%' AND \"Action\" NOT LIKE '%Withdraw%'"
        ]
        params = []

        if start_date:
            conditions.append('"Transaction Date" >= ?')
            params.append(start_date.isoformat())

        if end_date:
            conditions.append('"Transaction Date" <= ?')
            params.append(end_date.isoformat())

        if instruments:
            placeholders = ",".join("?" * len(instruments))
            conditions.append(f'"Description" IN ({placeholders})')
            params.extend(instruments)

        if account_id:
            conditions.append("account_id = ?")
            params.append(account_id)

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        # Get P/L for each trade ordered by date to build equity curve
        query = f"""
            SELECT COALESCE("P/L", 0) as pnl
            FROM broker_transactions
            WHERE {where_clause}
            ORDER BY "Transaction Date" ASC
        """

        results = execute_query(query, tuple(params))

        if not results:
            return 0.0

        # Build cumulative P/L (equity curve)
        cumulative_pnl = 0.0
        equity_curve = []
        for row in results:
            pnl = row.get("pnl", 0) or 0
            cumulative_pnl += pnl
            equity_curve.append(cumulative_pnl)

        if not equity_curve:
            return 0.0

        # Calculate max drawdown using peak-to-trough method on equity curve
        peak = equity_curve[0]
        max_drawdown = 0.0

        for equity in equity_curve:
            if equity > peak:
                peak = equity
            elif peak > 0:
                # Only calculate drawdown when peak is positive
                drawdown = (peak - equity) / peak * 100
                if drawdown > max_drawdown:
                    max_drawdown = drawdown
            elif peak <= 0 and equity < peak:
                # Handle case where we start negative or at zero
                # Use absolute difference as a percentage of the absolute peak
                abs_peak = abs(peak) if peak != 0 else 1
                drawdown = abs(peak - equity) / abs_peak * 100
                if drawdown > max_drawdown:
                    max_drawdown = drawdown

        # Cap max drawdown at 100% for display purposes
        return min(max_drawdown, 100.0)

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

        # Fetch point factors ONCE before processing trades
        point_factors = CurrencyService.get_instrument_point_factors()

        conditions = [
            "bt.\"Action\" NOT LIKE '%Fund%' AND bt.\"Action\" NOT LIKE '%Charge%' "
            "AND bt.\"Action\" NOT LIKE '%Deposit%' AND bt.\"Action\" NOT LIKE '%Withdraw%'"
        ]
        params = []

        if start_date:
            conditions.append('bt."Transaction Date" >= ?')
            params.append(start_date.isoformat())

        if end_date:
            conditions.append('bt."Transaction Date" <= ?')
            params.append(end_date.isoformat())

        if instruments:
            placeholders = ",".join("?" * len(instruments))
            conditions.append(f'bt."Description" IN ({placeholders})')
            params.extend(instruments)

        if account_id:
            conditions.append("bt.account_id = ?")
            params.append(account_id)

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

        # Get daily stats for averages (P&L and points per day)
        # Fetch individual trades to apply instrument point factors
        daily_trades_query = f"""
            SELECT
                DATE(bt."Transaction Date") as date,
                a.currency as currency,
                bt."P/L" as pnl,
                bt."Description" as instrument,
                COALESCE(bt."Closing", 0) as closing,
                COALESCE(bt."Opening", 0) as opening
            FROM broker_transactions bt
            JOIN accounts a ON bt.account_id = a.account_id
            WHERE {where_clause}
            ORDER BY date
        """
        daily_trades_results = execute_query(daily_trades_query, tuple(params))

        # Aggregate daily stats by date with currency conversion and point factors
        daily_pnl_map: Dict[str, float] = {}
        daily_points_map: Dict[str, float] = {}
        daily_trades_map: Dict[str, int] = {}

        for row in daily_trades_results:
            date = row["date"]
            currency = row.get("currency") or target_currency
            pnl = row.get("pnl") or 0
            instrument = row.get("instrument") or ""
            closing = row.get("closing") or 0
            opening = row.get("opening") or 0

            # Calculate points using single source of truth (with pre-fetched factors)
            points = CurrencyService.calculate_points(
                opening, closing, pnl, instrument, point_factors
            )

            if currency != target_currency:
                converted = CurrencyService.convert(pnl, currency, target_currency)
                if converted is not None:
                    pnl = converted

            if date not in daily_pnl_map:
                daily_pnl_map[date] = 0.0
                daily_points_map[date] = 0.0
                daily_trades_map[date] = 0

            daily_pnl_map[date] += pnl
            daily_points_map[date] += points
            daily_trades_map[date] += 1

        # Calculate daily averages
        num_days = len(daily_pnl_map)
        daily_pnl_values = list(daily_pnl_map.values())
        daily_points_values = list(daily_points_map.values())
        daily_trades_values = list(daily_trades_map.values())

        avg_daily_pnl = sum(daily_pnl_values) / num_days if num_days > 0 else 0
        avg_daily_points = sum(daily_points_values) / num_days if num_days > 0 else 0
        avg_trades_per_day = sum(daily_trades_values) / num_days if num_days > 0 else 0
        best_day_pnl = max(daily_pnl_values) if daily_pnl_values else 0
        worst_day_pnl = min(daily_pnl_values) if daily_pnl_values else 0

        # Get monthly stats for averages
        # Fetch individual trades to apply instrument point factors
        monthly_trades_query = f"""
            SELECT
                strftime('%Y-%m', bt."Transaction Date") as month,
                a.currency as currency,
                bt."P/L" as pnl,
                bt."Description" as instrument,
                COALESCE(bt."Closing", 0) as closing,
                COALESCE(bt."Opening", 0) as opening
            FROM broker_transactions bt
            JOIN accounts a ON bt.account_id = a.account_id
            WHERE {where_clause}
            ORDER BY month
        """
        monthly_trades_results = execute_query(monthly_trades_query, tuple(params))

        # Aggregate monthly stats by month with currency conversion and point factors
        monthly_pnl_map: Dict[str, float] = {}
        monthly_points_map: Dict[str, float] = {}
        monthly_trades_map: Dict[str, int] = {}

        for row in monthly_trades_results:
            month = row["month"]
            currency = row.get("currency") or target_currency
            pnl = row.get("pnl") or 0
            instrument = row.get("instrument") or ""
            closing = row.get("closing") or 0
            opening = row.get("opening") or 0

            # Calculate points using single source of truth (with pre-fetched factors)
            points = CurrencyService.calculate_points(
                opening, closing, pnl, instrument, point_factors
            )

            if currency != target_currency:
                converted = CurrencyService.convert(pnl, currency, target_currency)
                if converted is not None:
                    pnl = converted

            if month not in monthly_pnl_map:
                monthly_pnl_map[month] = 0.0
                monthly_points_map[month] = 0.0
                monthly_trades_map[month] = 0

            monthly_pnl_map[month] += pnl
            monthly_points_map[month] += points
            monthly_trades_map[month] += 1

        # Calculate monthly averages
        num_months = len(monthly_pnl_map)
        monthly_pnl_values = list(monthly_pnl_map.values())
        monthly_points_values = list(monthly_points_map.values())
        monthly_trades_values = list(monthly_trades_map.values())

        avg_monthly_pnl = sum(monthly_pnl_values) / num_months if num_months > 0 else 0
        avg_monthly_points = (
            sum(monthly_points_values) / num_months if num_months > 0 else 0
        )
        avg_trades_per_month = (
            sum(monthly_trades_values) / num_months if num_months > 0 else 0
        )
        best_month_pnl = max(monthly_pnl_values) if monthly_pnl_values else 0
        worst_month_pnl = min(monthly_pnl_values) if monthly_pnl_values else 0

        # Get yearly stats - use separate where clause without date filter
        # so yearly KPIs always reflect full year data regardless of selected timeframe
        current_year = datetime.now(timezone.utc).year
        yearly_conditions = [
            "bt.\"Action\" NOT LIKE '%Fund%' AND bt.\"Action\" NOT LIKE '%Charge%' "
            "AND bt.\"Action\" NOT LIKE '%Deposit%' AND bt.\"Action\" NOT LIKE '%Withdraw%'"
        ]
        yearly_params = []

        if instruments:
            placeholders = ",".join("?" * len(instruments))
            yearly_conditions.append(f'bt."Description" IN ({placeholders})')
            yearly_params.extend(instruments)

        if account_id:
            yearly_conditions.append("bt.account_id = ?")
            yearly_params.append(account_id)

        yearly_where_clause = " AND ".join(yearly_conditions)

        # Fetch individual trades for yearly stats to apply instrument point factors
        yearly_trades_query = f"""
            SELECT
                strftime('%Y', bt."Transaction Date") as year,
                a.currency as currency,
                bt."P/L" as pnl,
                bt."Description" as instrument,
                COALESCE(bt."Closing", 0) as closing,
                COALESCE(bt."Opening", 0) as opening
            FROM broker_transactions bt
            JOIN accounts a ON bt.account_id = a.account_id
            WHERE {yearly_where_clause}
            ORDER BY year
        """
        yearly_trades_results = execute_query(yearly_trades_query, tuple(yearly_params))

        # Aggregate yearly stats by year with currency conversion and point factors
        yearly_pnl_map: Dict[str, float] = {}
        yearly_points_map: Dict[str, float] = {}

        for row in yearly_trades_results:
            year = row["year"]
            currency = row.get("currency") or target_currency
            pnl = row.get("pnl") or 0
            instrument = row.get("instrument") or ""
            closing = row.get("closing") or 0
            opening = row.get("opening") or 0

            # Calculate points using single source of truth (with pre-fetched factors)
            points = CurrencyService.calculate_points(
                opening, closing, pnl, instrument, point_factors
            )

            if currency != target_currency:
                converted = CurrencyService.convert(pnl, currency, target_currency)
                if converted is not None:
                    pnl = converted

            if year not in yearly_pnl_map:
                yearly_pnl_map[year] = 0.0
                yearly_points_map[year] = 0.0

            yearly_pnl_map[year] += pnl
            yearly_points_map[year] += points

        # Calculate yearly values
        current_year_str = str(current_year)
        current_year_pnl = yearly_pnl_map.get(current_year_str, 0)
        current_year_points = yearly_points_map.get(current_year_str, 0)

        num_years = len(yearly_pnl_map)
        yearly_pnl_values = list(yearly_pnl_map.values())
        avg_yearly_pnl = sum(yearly_pnl_values) / num_years if num_years > 0 else 0

        return {
            "totalPnl": round(total_pnl, 2),
            "winRate": round(win_rate, 1),
            "avgWin": round(avg_win, 2),
            "avgLoss": round(avg_loss, 2),
            "profitFactor": round(profit_factor, 2),
            "maxDrawdown": round(max_drawdown, 1),
            "totalTrades": total_trades,
            "winningTrades": winning_trades,
            "losingTrades": losing_trades,
            "todayPnl": round(today_pnl, 2),
            "todayTrades": today_trades,
            "openPositions": 0,  # Would need real-time data
            "totalExposure": 0,  # Would need real-time data
            "avgTradeDuration": 120,  # Default 2 hours, would need calculation
            "currency": target_currency,
            # Daily averages
            "avgDailyPnl": round(avg_daily_pnl, 2),
            "avgDailyPoints": round(avg_daily_points, 2),
            "avgTradesPerDay": round(avg_trades_per_day, 1),
            "bestDayPnl": round(best_day_pnl, 2),
            "worstDayPnl": round(worst_day_pnl, 2),
            # Monthly averages
            "avgMonthlyPnl": round(avg_monthly_pnl, 2),
            "avgMonthlyPoints": round(avg_monthly_points, 2),
            "avgTradesPerMonth": round(avg_trades_per_month, 1),
            "bestMonthPnl": round(best_month_pnl, 2),
            "worstMonthPnl": round(worst_month_pnl, 2),
            # Yearly summary
            "currentYearPnl": round(current_year_pnl, 2),
            "currentYearPoints": round(current_year_points, 2),
            "avgYearlyPnl": round(avg_yearly_pnl, 2),
        }

    @staticmethod
    def get_available_instruments() -> List[Dict[str, str]]:
        """Get list of available instruments from the database."""
        query = """
            SELECT DISTINCT "Description" as value, "Description" as label
            FROM broker_transactions
            WHERE "Action" NOT LIKE '%Fund%'
            AND "Action" NOT LIKE '%Charge%'
            AND "Action" NOT LIKE '%Deposit%'
            AND "Action" NOT LIKE '%Withdraw%'
            AND "Description" IS NOT NULL
            AND "Description" != ''
            ORDER BY "Description"
        """
        return execute_query(query)

    @staticmethod
    def get_accounts() -> List[Dict[str, Any]]:
        """Get all accounts."""
        query = """
            SELECT
                account_id as id,
                account_name as name,
                broker_name as broker,
                currency,
                initial_balance as initialBalance,
                notes
            FROM accounts
            ORDER BY account_name
        """
        return execute_query(query)

    @staticmethod
    def get_equity_curve(
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        account_id: Optional[int] = None,
        target_currency: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get equity curve based on cumulative P/L excluding funding.

        This provides a true trading performance curve without deposits/withdrawals
        affecting the drawdown calculations.

        Converts all P&L values to target_currency before aggregating.
        """
        from api.services.currency import CurrencyService

        # Require explicit currency - no auto-detection per .rules
        if target_currency is None:
            raise ValueError("target_currency is required - no auto-detection allowed")

        conditions = [
            "bt.\"Action\" NOT LIKE '%Fund%' AND bt.\"Action\" NOT LIKE '%Charge%' "
            "AND bt.\"Action\" NOT LIKE '%Deposit%' AND bt.\"Action\" NOT LIKE '%Withdraw%'"
        ]
        params = []

        if start_date:
            conditions.append('bt."Transaction Date" >= ?')
            params.append(start_date.isoformat())

        if end_date:
            conditions.append('bt."Transaction Date" <= ?')
            params.append(end_date.isoformat())

        if account_id:
            conditions.append("bt.account_id = ?")
            params.append(account_id)

        where_clause = " AND ".join(conditions)

        # Get daily P&L grouped by date AND account currency for proper conversion
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

        # Aggregate by date, converting currencies to target_currency
        date_map: Dict[str, float] = {}
        for row in raw_data:
            date = row["date"]
            currency = row["currency"] or target_currency
            pnl = row["daily_pnl"] or 0

            # Convert P&L to target currency
            if currency != target_currency:
                converted = CurrencyService.convert(pnl, currency, target_currency)
                if converted is not None:
                    pnl = converted
                # If conversion fails, we still add the unconverted value (not ideal but prevents data loss)

            if date not in date_map:
                date_map[date] = 0
            date_map[date] += pnl

        # Sort by date and calculate cumulative P&L
        sorted_dates = sorted(date_map.keys())
        equity_data = []
        cumulative_pnl = 0
        for date in sorted_dates:
            daily_pnl = date_map[date]
            cumulative_pnl += daily_pnl
            equity_data.append(
                {
                    "date": date,
                    "balance": cumulative_pnl,
                    "dailyPnl": daily_pnl,
                }
            )

        return {
            "data": equity_data,
            "currency": target_currency,
        }

    @staticmethod
    def get_daily_pnl(
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        target_currency: Optional[str] = None,
        account_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Get daily P&L data with previous day balance for percentage calculation.

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
        params = []

        if start_date:
            conditions.append('bt."Transaction Date" >= ?')
            params.append(start_date.isoformat())

        if end_date:
            conditions.append('bt."Transaction Date" <= ?')
            params.append(end_date.isoformat())

        if account_id:
            conditions.append("bt.account_id = ?")
            params.append(account_id)

        where_clause = " AND ".join(conditions)

        # Get daily P&L data grouped by date AND account currency
        query = f"""
            SELECT
                DATE(bt."Transaction Date") as date,
                a.currency as currency,
                SUM(bt."P/L") as pnl,
                COUNT(*) as trades
            FROM broker_transactions bt
            JOIN accounts a ON bt.account_id = a.account_id
            WHERE {where_clause}
            GROUP BY DATE(bt."Transaction Date"), a.currency
            ORDER BY date ASC
        """

        raw_data = execute_query(query, tuple(params))

        # Aggregate by date, converting currencies
        date_map: Dict[str, Dict[str, Any]] = {}
        for row in raw_data:
            date = row["date"]
            currency = row["currency"] or target_currency
            pnl = row["pnl"] or 0
            trades = row["trades"] or 0

            # Convert P&L to target currency
            if currency != target_currency:
                converted = CurrencyService.convert(pnl, currency, target_currency)
                if converted is not None:
                    pnl = converted
                # If conversion fails, we still add the unconverted value (not ideal but prevents data loss)

            if date not in date_map:
                date_map[date] = {"date": date, "pnl": 0, "trades": 0}

            date_map[date]["pnl"] += pnl
            date_map[date]["trades"] += trades

        # Sort by date and calculate cumulative P&L
        daily_pnl = sorted(date_map.values(), key=lambda x: x["date"])
        cumulative = 0
        for entry in daily_pnl:
            cumulative += entry["pnl"]
            entry["cumulativePnl"] = cumulative
            entry["currency"] = target_currency

        # Get daily balance history per account/currency for proper conversion
        balance_conditions = ["1=1"]
        balance_params = []
        if account_id:
            balance_conditions.append("bt.account_id = ?")
            balance_params.append(account_id)
        balance_where = " AND ".join(balance_conditions)

        balance_query = f"""
            SELECT
                DATE(bt."Transaction Date") as date,
                bt.account_id,
                a.currency as currency,
                bt."Balance" as balance
            FROM broker_transactions bt
            JOIN accounts a ON bt.account_id = a.account_id
            INNER JOIN (
                SELECT DATE("Transaction Date") as txn_date, account_id, MAX("Transaction Date") as last_txn_time
                FROM broker_transactions
                GROUP BY DATE("Transaction Date"), account_id
            ) last_txn ON bt."Transaction Date" = last_txn.last_txn_time AND bt.account_id = last_txn.account_id
            WHERE {balance_where}
            ORDER BY date ASC
        """

        balance_data = execute_query(balance_query, tuple(balance_params))

        # Aggregate balances by date, converting to target currency
        balance_map: Dict[str, float] = {}
        for row in balance_data:
            date = row["date"]
            currency = row["currency"] or target_currency
            balance = row["balance"] or 0

            # Convert balance to target currency
            if currency != target_currency:
                converted = CurrencyService.convert(balance, currency, target_currency)
                if converted is not None:
                    balance = converted

            if date not in balance_map:
                balance_map[date] = 0
            balance_map[date] += balance
        sorted_balance_dates = sorted(balance_map.keys())

        # Add previousBalance to each daily P&L entry
        for entry in daily_pnl:
            date = entry["date"]
            # Find the previous date's balance by looking for the latest balance date before this date
            prev_balance = None
            for i, balance_date in enumerate(sorted_balance_dates):
                if balance_date >= date:
                    # Found a date >= current, so use the previous one if exists
                    if i > 0:
                        prev_balance = balance_map.get(sorted_balance_dates[i - 1])
                    break
                # If we're at the last date and it's still < current date, use it
                if i == len(sorted_balance_dates) - 1:
                    prev_balance = balance_map.get(balance_date)

            entry["previousBalance"] = prev_balance

            # Calculate pnlPercent if we have previous balance
            if prev_balance and prev_balance != 0:
                entry["pnlPercent"] = (entry["pnl"] / prev_balance) * 100
            else:
                entry["pnlPercent"] = None

        return daily_pnl

    @staticmethod
    def get_daily_pnl_by_account(
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        target_currency: Optional[str] = None,
        account_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Get daily P&L data per account for multi-account charting.

        Converts all P&L values to target_currency before aggregating totals.
        """
        from api.services.currency import CurrencyService

        # Require explicit currency - no auto-detection per .rules
        if target_currency is None:
            raise ValueError("target_currency is required - no auto-detection allowed")

        conditions = [
            "\"Action\" NOT LIKE '%Fund%' AND \"Action\" NOT LIKE '%Charge%' "
            "AND \"Action\" NOT LIKE '%Deposit%' AND \"Action\" NOT LIKE '%Withdraw%'"
        ]
        params = []

        if start_date:
            conditions.append('"Transaction Date" >= ?')
            params.append(start_date.isoformat())

        if end_date:
            conditions.append('"Transaction Date" <= ?')
            params.append(end_date.isoformat())

        where_clause = " AND ".join(conditions)

        # Get accounts - either specific one or all with transactions
        if account_id:
            accounts_query = """
                SELECT a.account_id, a.account_name, a.broker_name, a.currency
                FROM accounts a
                WHERE a.account_id = ?
            """
            accounts = execute_query(accounts_query, (account_id,))
        else:
            accounts_query = """
                SELECT a.account_id, a.account_name, a.broker_name, a.currency
                FROM accounts a
                WHERE EXISTS (
                    SELECT 1 FROM broker_transactions bt
                    WHERE bt.account_id = a.account_id
                )
            """
            accounts = execute_query(accounts_query, ())

        # Get daily P&L per account
        series = []
        for account in accounts:
            acc_id = account["account_id"]
            acc_name = account["account_name"] or f"Account {acc_id}"
            acc_currency = account["currency"]

            query = f"""
                SELECT
                    DATE("Transaction Date") as date,
                    SUM("P/L") as pnl,
                    COUNT(*) as trades
                FROM broker_transactions
                WHERE {where_clause} AND account_id = ?
                GROUP BY DATE("Transaction Date")
                ORDER BY date ASC
            """
            acc_params = list(params) + [acc_id]
            raw_data = execute_query(query, tuple(acc_params))

            if raw_data:
                # Convert P&L to target currency if needed
                converted_data = []
                cumulative = 0
                rate = 1.0
                if acc_currency and acc_currency != target_currency:
                    rate = (
                        CurrencyService.get_exchange_rate(acc_currency, target_currency)
                        or 1.0
                    )

                for row in raw_data:
                    pnl = (row["pnl"] or 0) * rate
                    cumulative += pnl
                    converted_data.append(
                        {
                            "date": row["date"],
                            "pnl": pnl,
                            "trades": row["trades"],
                            "cumulativePnl": cumulative,
                        }
                    )

                series.append(
                    {
                        "accountId": acc_id,
                        "accountName": acc_name,
                        "currency": target_currency,
                        "data": converted_data,
                    }
                )

        # Calculate total by summing converted series data
        total_by_date: Dict[str, Dict[str, Any]] = {}
        for s in series:
            for point in s["data"]:
                date_str = point["date"]
                pnl = point["pnl"] or 0
                trades = point["trades"] or 0
                if date_str in total_by_date:
                    total_by_date[date_str]["pnl"] += pnl
                    total_by_date[date_str]["trades"] += trades
                else:
                    total_by_date[date_str] = {
                        "date": date_str,
                        "pnl": pnl,
                        "trades": trades,
                    }

        # Sort and calculate cumulative P&L for total
        total_data = sorted(total_by_date.values(), key=lambda x: x["date"])
        cumulative = 0
        for entry in total_data:
            cumulative += entry["pnl"]
            entry["cumulativePnl"] = cumulative

        return {
            "series": series,
            "total": {
                "accountName": "Total",
                "currency": target_currency,
                "data": total_data,
            },
        }


# Create singleton instance
db = TradingDatabase()
