"""
Database service for accessing trading data.

Provides methods to query the SQLite database and return data
in formats suitable for the API responses.
"""

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from db_path import DATABASE_PATH
from settings import DEFAULT_POINT_MULTIPLIER, MARKET_POINT_MULTIPLIERS


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
            WHERE {where_clause}
            ORDER BY "Transaction Date" DESC
        """

        if limit:
            query += f" LIMIT {limit} OFFSET {offset}"

        trades = execute_query(query, tuple(params))

        # Process trades to add direction
        for trade in trades:
            action = trade.get("action", "").lower()
            if "buy" in action or "long" in action:
                trade["direction"] = "long"
            elif "sell" in action or "short" in action:
                trade["direction"] = "short"
            else:
                # Infer from price movement
                entry = trade.get("entry_price", 0) or 0
                exit_price = trade.get("exit_price", 0) or 0
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

        return trades, total

    @staticmethod
    def get_recent_trades(
        limit: int = 10,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        instruments: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Get most recent trades."""
        trades, _ = TradingDatabase.get_all_trades(
            start_date=start_date,
            end_date=end_date,
            instruments=instruments,
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
    ) -> Dict[str, Any]:
        """Get balance history over time with currency info."""
        conditions = ["1=1"]
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

        # Get the primary currency used (most common)
        currency_query = f"""
            SELECT "Currency", COUNT(*) as cnt
            FROM broker_transactions
            WHERE {where_clause} AND "Currency" IS NOT NULL
            GROUP BY "Currency"
            ORDER BY cnt DESC
            LIMIT 1
        """
        currency_results = execute_query(currency_query, tuple(params))
        currency = currency_results[0].get("Currency") if currency_results else None

        query = f"""
            SELECT
                DATE("Transaction Date") as date,
                MAX("Balance") as balance
            FROM broker_transactions
            WHERE {where_clause}
            GROUP BY DATE("Transaction Date")
            ORDER BY date ASC
        """

        data = execute_query(query, tuple(params))
        return {
            "data": data,
            "currency": currency,
        }

    @staticmethod
    def get_balance_history_by_account(
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Get balance history per account for multi-account charting."""
        conditions = ["1=1"]
        params = []

        if start_date:
            conditions.append('"Transaction Date" >= ?')
            params.append(start_date.isoformat())

        if end_date:
            conditions.append('"Transaction Date" <= ?')
            params.append(end_date.isoformat())

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

        # Get balance history per account
        series = []
        for account in accounts:
            acc_id = account["account_id"]
            acc_name = account["account_name"] or f"Account {acc_id}"
            acc_currency = account["currency"]

            query = f"""
                SELECT
                    DATE("Transaction Date") as date,
                    MAX("Balance") as balance
                FROM broker_transactions
                WHERE {where_clause} AND account_id = ?
                GROUP BY DATE("Transaction Date")
                ORDER BY date ASC
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

        # Get total balance (sum across all accounts, requires same currency or conversion)
        total_query = f"""
            SELECT
                DATE("Transaction Date") as date,
                SUM(daily_balance) as balance
            FROM (
                SELECT
                    DATE("Transaction Date") as date,
                    account_id,
                    MAX("Balance") as daily_balance
                FROM broker_transactions
                WHERE {where_clause}
                GROUP BY DATE("Transaction Date"), account_id
            )
            GROUP BY date
            ORDER BY date ASC
        """
        total_data = execute_query(total_query, tuple(params))

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
    ) -> Dict[str, Any]:
        """Get monthly P&L per account for multi-account charting."""
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
                    strftime('%Y-%m', "Transaction Date") as month_key,
                    CASE CAST(strftime('%m', "Transaction Date") AS INTEGER)
                        WHEN 1 THEN 'Jan' WHEN 2 THEN 'Feb' WHEN 3 THEN 'Mar'
                        WHEN 4 THEN 'Apr' WHEN 5 THEN 'May' WHEN 6 THEN 'Jun'
                        WHEN 7 THEN 'Jul' WHEN 8 THEN 'Aug' WHEN 9 THEN 'Sep'
                        WHEN 10 THEN 'Oct' WHEN 11 THEN 'Nov' WHEN 12 THEN 'Dec'
                    END || ' ' || strftime('%Y', "Transaction Date") as month,
                    SUM("P/L") as pnl,
                    COUNT(*) as trades,
                    ROUND(
                        CAST(SUM(CASE WHEN "P/L" >= 0 THEN 1 ELSE 0 END) AS FLOAT) /
                        CAST(COUNT(*) AS FLOAT) * 100,
                        1
                    ) as winRate
                FROM broker_transactions
                WHERE {where_clause} AND account_id = ?
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

        # Get total monthly P&L across all accounts
        total_query = f"""
            SELECT
                strftime('%Y-%m', "Transaction Date") as month_key,
                CASE CAST(strftime('%m', "Transaction Date") AS INTEGER)
                    WHEN 1 THEN 'Jan' WHEN 2 THEN 'Feb' WHEN 3 THEN 'Mar'
                    WHEN 4 THEN 'Apr' WHEN 5 THEN 'May' WHEN 6 THEN 'Jun'
                    WHEN 7 THEN 'Jul' WHEN 8 THEN 'Aug' WHEN 9 THEN 'Sep'
                    WHEN 10 THEN 'Oct' WHEN 11 THEN 'Nov' WHEN 12 THEN 'Dec'
                END || ' ' || strftime('%Y', "Transaction Date") as month,
                SUM("P/L") as pnl,
                COUNT(*) as trades,
                ROUND(
                    CAST(SUM(CASE WHEN "P/L" >= 0 THEN 1 ELSE 0 END) AS FLOAT) /
                    CAST(COUNT(*) AS FLOAT) * 100,
                    1
                ) as winRate
            FROM broker_transactions
            WHERE {where_clause}
            GROUP BY month_key
            ORDER BY month_key ASC
        """
        total_data = execute_query(total_query, tuple(params))

        return {
            "series": series,
            "total": {
                "accountName": "Total",
                "data": total_data,
            },
        }

    @staticmethod
    def get_monthly_pnl(
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        instruments: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Get P&L aggregated by month with currency info."""
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

        where_clause = " AND ".join(conditions)

        # Get the primary currency used (most common)
        currency_query = f"""
            SELECT "Currency", COUNT(*) as cnt
            FROM broker_transactions
            WHERE {where_clause} AND "Currency" IS NOT NULL
            GROUP BY "Currency"
            ORDER BY cnt DESC
            LIMIT 1
        """
        currency_results = execute_query(currency_query, tuple(params))
        currency = currency_results[0].get("Currency") if currency_results else None

        query = f"""
            SELECT
                strftime('%Y-%m', "Transaction Date") as month_key,
                CASE CAST(strftime('%m', "Transaction Date") AS INTEGER)
                    WHEN 1 THEN 'Jan' WHEN 2 THEN 'Feb' WHEN 3 THEN 'Mar'
                    WHEN 4 THEN 'Apr' WHEN 5 THEN 'May' WHEN 6 THEN 'Jun'
                    WHEN 7 THEN 'Jul' WHEN 8 THEN 'Aug' WHEN 9 THEN 'Sep'
                    WHEN 10 THEN 'Oct' WHEN 11 THEN 'Nov' WHEN 12 THEN 'Dec'
                END || ' ' || strftime('%Y', "Transaction Date") as month,
                SUM("P/L") as pnl,
                COUNT(*) as trades,
                ROUND(
                    CAST(SUM(CASE WHEN "P/L" >= 0 THEN 1 ELSE 0 END) AS FLOAT) /
                    CAST(COUNT(*) AS FLOAT) * 100,
                    1
                ) as winRate
            FROM broker_transactions
            WHERE {where_clause}
            GROUP BY month_key
            ORDER BY month_key ASC
        """

        data = execute_query(query, tuple(params))
        return {
            "data": data,
            "currency": currency,
        }

    @staticmethod
    def get_win_rate_by_instrument(
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
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
    ) -> List[Dict[str, Any]]:
        """
        Get points/pips statistics per instrument.

        Points are calculated based on price movement:
        - Gold: 0.1 price movement = 1 point (multiplier 10)
        - Indexes: 1.0 price movement = 1 point (multiplier 1)
        - Forex: pip-based calculation (e.g., 0.0001 = 1 pip for EUR/USD)
        """
        conditions = [
            "\"Action\" NOT LIKE '%Fund%' AND \"Action\" NOT LIKE '%Charge%' "
            "AND \"Action\" NOT LIKE '%Deposit%' AND \"Action\" NOT LIKE '%Withdraw%'",
            '"Opening" IS NOT NULL AND "Opening" > 0',
            '"Closing" IS NOT NULL AND "Closing" > 0',
        ]
        params = []

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
            action = (trade["action"] or "").lower()
            amount = abs(trade["amount"] or 1)

            if entry == 0 or exit_price == 0:
                continue

            # Determine multiplier based on instrument name
            multiplier = DEFAULT_POINT_MULTIPLIER
            for market_key, mult in MARKET_POINT_MULTIPLIERS.items():
                if market_key.lower() in name.lower():
                    multiplier = mult
                    break

            # Calculate raw price difference
            price_diff = exit_price - entry

            # Determine direction from action or P/L
            is_long = "buy" in action or "long" in action
            if not is_long and not ("sell" in action or "short" in action):
                # Infer from P/L and price movement
                is_long = (price_diff > 0 and pnl > 0) or (price_diff < 0 and pnl < 0)

            # Calculate points (positive if profitable direction)
            if is_long:
                points = price_diff * multiplier
            else:
                points = -price_diff * multiplier

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
                    "multiplier": multiplier,
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

        Returns the largest percentage drop from a peak to a subsequent trough
        in the balance history.
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

        # Get balance history ordered by date
        query = f"""
            SELECT "Balance"
            FROM broker_transactions
            WHERE {where_clause}
            ORDER BY "Transaction Date" ASC, "Transaction ID" ASC
        """

        results = execute_query(query, tuple(params))

        if not results:
            return 0.0

        balances = [row.get("Balance", 0) or 0 for row in results]

        if not balances:
            return 0.0

        # Calculate max drawdown using peak-to-trough method
        peak = balances[0]
        max_drawdown = 0.0

        for balance in balances:
            if balance > peak:
                peak = balance
            elif peak > 0:
                drawdown = (peak - balance) / peak * 100
                if drawdown > max_drawdown:
                    max_drawdown = drawdown

        return max_drawdown

    @staticmethod
    def get_kpi_metrics(
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        instruments: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Calculate KPI metrics with currency info."""
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

        where_clause = " AND ".join(conditions)

        # Get the primary currency used (most common)
        currency_query = f"""
            SELECT "Currency", COUNT(*) as cnt
            FROM broker_transactions
            WHERE {where_clause} AND "Currency" IS NOT NULL
            GROUP BY "Currency"
            ORDER BY cnt DESC
            LIMIT 1
        """
        currency_results = execute_query(currency_query, tuple(params))
        currency = currency_results[0].get("Currency") if currency_results else None

        query = f"""
            SELECT
                COALESCE(SUM("P/L"), 0) as total_pnl,
                COUNT(*) as total_trades,
                SUM(CASE WHEN "P/L" >= 0 THEN 1 ELSE 0 END) as winning_trades,
                SUM(CASE WHEN "P/L" < 0 THEN 1 ELSE 0 END) as losing_trades,
                COALESCE(AVG(CASE WHEN "P/L" >= 0 THEN "P/L" END), 0) as avg_win,
                COALESCE(ABS(AVG(CASE WHEN "P/L" < 0 THEN "P/L" END)), 0) as avg_loss,
                COALESCE(MIN("Balance"), 0) as min_balance,
                COALESCE(MAX("Balance"), 0) as max_balance
            FROM broker_transactions
            WHERE {where_clause}
        """

        results = execute_query(query, tuple(params))
        row = results[0] if results else {}

        total_trades = row.get("total_trades", 0) or 0
        winning_trades = row.get("winning_trades", 0) or 0
        losing_trades = row.get("losing_trades", 0) or 0
        avg_win = row.get("avg_win", 0) or 0
        avg_loss = row.get("avg_loss", 0) or 0
        total_pnl = row.get("total_pnl", 0) or 0
        max_balance = row.get("max_balance", 0) or 0
        min_balance = row.get("min_balance", 0) or 0

        # Calculate win rate
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0

        # Calculate profit factor
        total_wins = winning_trades * avg_win if winning_trades > 0 else 0
        total_losses = losing_trades * avg_loss if losing_trades > 0 else 1
        profit_factor = total_wins / total_losses if total_losses > 0 else 0

        # Calculate max drawdown (peak-to-trough)
        max_drawdown = TradingDatabase._calculate_max_drawdown(
            start_date, end_date, instruments, None
        )

        # Get today's stats
        today = datetime.now().date().isoformat()
        today_query = f"""
            SELECT
                COALESCE(SUM("P/L"), 0) as today_pnl,
                COUNT(*) as today_trades
            FROM broker_transactions
            WHERE DATE("Transaction Date") = ? AND {where_clause}
        """
        today_params = [today] + list(params)
        today_results = execute_query(today_query, tuple(today_params))
        today_row = today_results[0] if today_results else {}

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
            "todayPnl": round(today_row.get("today_pnl", 0) or 0, 2),
            "todayTrades": today_row.get("today_trades", 0) or 0,
            "openPositions": 0,  # Would need real-time data
            "totalExposure": 0,  # Would need real-time data
            "avgTradeDuration": 120,  # Default 2 hours, would need calculation
            "currency": currency,
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
    ) -> Dict[str, Any]:
        """
        Get equity curve based on cumulative P/L excluding funding.

        This provides a true trading performance curve without deposits/withdrawals
        affecting the drawdown calculations.
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

        where_clause = " AND ".join(conditions)

        # Get the primary currency used (most common)
        currency_query = f"""
            SELECT "Currency", COUNT(*) as cnt
            FROM broker_transactions
            WHERE {where_clause} AND "Currency" IS NOT NULL
            GROUP BY "Currency"
            ORDER BY cnt DESC
            LIMIT 1
        """
        currency_results = execute_query(currency_query, tuple(params))
        currency = currency_results[0].get("Currency") if currency_results else None

        query = f"""
            SELECT
                DATE("Transaction Date") as date,
                SUM("P/L") as daily_pnl,
                SUM(SUM("P/L")) OVER (ORDER BY DATE("Transaction Date")) as cumulative_pnl
            FROM broker_transactions
            WHERE {where_clause}
            GROUP BY DATE("Transaction Date")
            ORDER BY date ASC
        """

        data = execute_query(query, tuple(params))

        # Transform to equity curve format (starting from 0)
        equity_data = []
        for point in data:
            equity_data.append(
                {
                    "date": point["date"],
                    "balance": point["cumulative_pnl"] or 0,
                    "dailyPnl": point["daily_pnl"] or 0,
                }
            )

        return {
            "data": equity_data,
            "currency": currency,
        }

    @staticmethod
    def get_daily_pnl(
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """Get daily P&L data."""
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

        query = f"""
            SELECT
                DATE("Transaction Date") as date,
                SUM("P/L") as pnl,
                COUNT(*) as trades,
                SUM(SUM("P/L")) OVER (ORDER BY DATE("Transaction Date")) as cumulativePnl
            FROM broker_transactions
            WHERE {where_clause}
            GROUP BY DATE("Transaction Date")
            ORDER BY date ASC
        """

        return execute_query(query, tuple(params))


# Create singleton instance
db = TradingDatabase()
