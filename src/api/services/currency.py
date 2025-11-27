"""
Currency service for exchange rate management and currency conversion.

Provides methods to:
- Get and update exchange rates
- Convert amounts between currencies
- Store user currency preferences
"""

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from db_path import DATABASE_PATH

# Default exchange rates (to SEK as base)
DEFAULT_EXCHANGE_RATES = {
    "SEK": 1.0,
    "DKK": 1.52,
    "EUR": 11.32,
    "USD": 10.50,
    "GBP": 13.20,
    "NOK": 0.98,
    "CHF": 11.80,
    "JPY": 0.070,
    "AUD": 6.80,
    "CAD": 7.70,
    "NZD": 6.20,
}

# Currency symbols
CURRENCY_SYMBOLS = {
    "SEK": "kr",
    "DKK": "kr",
    "EUR": "€",
    "USD": "$",
    "GBP": "£",
    "NOK": "kr",
    "CHF": "CHF",
    "JPY": "¥",
    "AUD": "A$",
    "CAD": "C$",
    "NZD": "NZ$",
}

# Currency names
CURRENCY_NAMES = {
    "SEK": "Swedish Krona",
    "DKK": "Danish Krone",
    "EUR": "Euro",
    "USD": "US Dollar",
    "GBP": "British Pound",
    "NOK": "Norwegian Krone",
    "CHF": "Swiss Franc",
    "JPY": "Japanese Yen",
    "AUD": "Australian Dollar",
    "CAD": "Canadian Dollar",
    "NZD": "New Zealand Dollar",
}


@contextmanager
def get_db_connection():
    """Context manager for database connections."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def ensure_currency_tables():
    """Create currency-related tables if they don't exist."""
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Exchange rates table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS exchange_rates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_currency TEXT NOT NULL,
                to_currency TEXT NOT NULL,
                rate REAL NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                source TEXT DEFAULT 'manual',
                UNIQUE(from_currency, to_currency)
            )
        """)

        # User preferences table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_preferences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE NOT NULL,
                value TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()


def init_default_rates():
    """Initialize default exchange rates if not present."""
    ensure_currency_tables()

    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Check if rates exist
        cursor.execute("SELECT COUNT(*) FROM exchange_rates")
        count = cursor.fetchone()[0]

        if count == 0:
            # Insert default rates (all to SEK as base)
            base_currency = "SEK"
            for currency, rate in DEFAULT_EXCHANGE_RATES.items():
                if currency != base_currency:
                    # Rate from currency to SEK
                    cursor.execute(
                        """
                        INSERT OR REPLACE INTO exchange_rates (from_currency, to_currency, rate, source)
                        VALUES (?, ?, ?, 'default')
                    """,
                        (currency, base_currency, rate),
                    )

                    # Inverse rate from SEK to currency
                    cursor.execute(
                        """
                        INSERT OR REPLACE INTO exchange_rates (from_currency, to_currency, rate, source)
                        VALUES (?, ?, ?, 'default')
                    """,
                        (base_currency, currency, 1.0 / rate),
                    )

            conn.commit()


class CurrencyService:
    """Service class for currency operations."""

    def __init__(self):
        """Initialize the currency service."""
        init_default_rates()

    @staticmethod
    def get_supported_currencies() -> List[Dict[str, Any]]:
        """Get list of supported currencies."""
        currencies = []
        for code in CURRENCY_SYMBOLS.keys():
            currencies.append(
                {
                    "code": code,
                    "symbol": CURRENCY_SYMBOLS.get(code, code),
                    "name": CURRENCY_NAMES.get(code, code),
                }
            )
        return currencies

    @staticmethod
    def get_exchange_rate(from_currency: str, to_currency: str) -> Optional[float]:
        """Get exchange rate between two currencies."""
        if from_currency == to_currency:
            return 1.0

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT rate FROM exchange_rates
                WHERE from_currency = ? AND to_currency = ?
            """,
                (from_currency, to_currency),
            )
            result = cursor.fetchone()

            if result:
                return result[0]

            # Try to calculate via SEK as intermediate
            cursor.execute(
                """
                SELECT rate FROM exchange_rates
                WHERE from_currency = ? AND to_currency = 'SEK'
            """,
                (from_currency,),
            )
            from_to_sek = cursor.fetchone()

            cursor.execute(
                """
                SELECT rate FROM exchange_rates
                WHERE from_currency = 'SEK' AND to_currency = ?
            """,
                (to_currency,),
            )
            sek_to_target = cursor.fetchone()

            if from_to_sek and sek_to_target:
                return from_to_sek[0] * sek_to_target[0]

            # Fallback to default rates
            if (
                from_currency in DEFAULT_EXCHANGE_RATES
                and to_currency in DEFAULT_EXCHANGE_RATES
            ):
                from_rate = DEFAULT_EXCHANGE_RATES[from_currency]
                to_rate = DEFAULT_EXCHANGE_RATES[to_currency]
                return from_rate / to_rate

            return None

    @staticmethod
    def get_all_exchange_rates(base_currency: str = "SEK") -> Dict[str, float]:
        """Get all exchange rates relative to a base currency."""
        rates = {base_currency: 1.0}

        for currency in CURRENCY_SYMBOLS.keys():
            if currency != base_currency:
                rate = CurrencyService.get_exchange_rate(currency, base_currency)
                if rate:
                    rates[currency] = rate

        return rates

    @staticmethod
    def convert(amount: float, from_currency: str, to_currency: str) -> Optional[float]:
        """Convert an amount from one currency to another."""
        if from_currency == to_currency:
            return amount

        rate = CurrencyService.get_exchange_rate(from_currency, to_currency)
        if rate is None:
            return None

        return amount * rate

    @staticmethod
    def update_exchange_rate(
        from_currency: str, to_currency: str, rate: float, source: str = "manual"
    ) -> bool:
        """Update an exchange rate."""
        ensure_currency_tables()

        with get_db_connection() as conn:
            cursor = conn.cursor()
            try:
                # Update or insert the rate
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO exchange_rates
                    (from_currency, to_currency, rate, source, updated_at)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                    (from_currency, to_currency, rate, source),
                )

                # Also update the inverse rate
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO exchange_rates
                    (from_currency, to_currency, rate, source, updated_at)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                    (to_currency, from_currency, 1.0 / rate, source),
                )

                conn.commit()
                return True
            except Exception:
                return False

    @staticmethod
    def bulk_update_rates(
        rates: Dict[str, float], base_currency: str = "SEK", source: str = "manual"
    ) -> bool:
        """Bulk update exchange rates relative to a base currency."""
        ensure_currency_tables()

        with get_db_connection() as conn:
            cursor = conn.cursor()
            try:
                for currency, rate in rates.items():
                    if currency != base_currency:
                        # Rate from currency to base
                        cursor.execute(
                            """
                            INSERT OR REPLACE INTO exchange_rates
                            (from_currency, to_currency, rate, source, updated_at)
                            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                        """,
                            (currency, base_currency, rate, source),
                        )

                        # Inverse rate
                        cursor.execute(
                            """
                            INSERT OR REPLACE INTO exchange_rates
                            (from_currency, to_currency, rate, source, updated_at)
                            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                        """,
                            (base_currency, currency, 1.0 / rate, source),
                        )

                conn.commit()
                return True
            except Exception:
                return False

    @staticmethod
    def get_user_preference(key: str, default: Any = None) -> Any:
        """Get a user preference value."""
        ensure_currency_tables()

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT value FROM user_preferences WHERE key = ?
            """,
                (key,),
            )
            result = cursor.fetchone()

            if result:
                try:
                    return json.loads(result[0])
                except json.JSONDecodeError:
                    return result[0]

            return default

    @staticmethod
    def set_user_preference(key: str, value: Any) -> bool:
        """Set a user preference value."""
        ensure_currency_tables()

        with get_db_connection() as conn:
            cursor = conn.cursor()
            try:
                json_value = json.dumps(value) if not isinstance(value, str) else value
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO user_preferences (key, value, updated_at)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                """,
                    (key, json_value),
                )
                conn.commit()
                return True
            except Exception:
                return False

    @staticmethod
    def get_default_currency() -> str:
        """Get the user's default display currency."""
        return CurrencyService.get_user_preference("default_currency", "SEK")

    @staticmethod
    def set_default_currency(currency: str) -> bool:
        """Set the user's default display currency."""
        if currency not in CURRENCY_SYMBOLS:
            return False
        return CurrencyService.set_user_preference("default_currency", currency)

    @staticmethod
    def get_show_converted() -> bool:
        """Get whether to show converted currency values."""
        return CurrencyService.get_user_preference("show_converted_currency", True)

    @staticmethod
    def set_show_converted(show: bool) -> bool:
        """Set whether to show converted currency values."""
        return CurrencyService.set_user_preference("show_converted_currency", show)

    @staticmethod
    def format_currency(
        amount: float,
        currency: str,
        include_symbol: bool = True,
        decimal_places: int = 2,
    ) -> str:
        """Format an amount as a currency string."""
        symbol = CURRENCY_SYMBOLS.get(currency, "") if include_symbol else ""
        formatted = f"{amount:,.{decimal_places}f}"

        # Symbol placement varies by currency
        if currency in ["USD", "GBP", "AUD", "CAD", "NZD"]:
            return f"{symbol}{formatted}"
        else:
            return f"{formatted} {symbol}".strip()

    @staticmethod
    def format_with_conversion(
        amount: float,
        original_currency: str,
        target_currency: str,
        include_symbol: bool = True,
        decimal_places: int = 2,
    ) -> Dict[str, Any]:
        """Format amount with optional conversion to target currency."""
        result = {
            "original": {
                "amount": amount,
                "currency": original_currency,
                "formatted": CurrencyService.format_currency(
                    amount, original_currency, include_symbol, decimal_places
                ),
            },
            "converted": None,
        }

        if original_currency != target_currency:
            converted = CurrencyService.convert(
                amount, original_currency, target_currency
            )
            if converted is not None:
                result["converted"] = {
                    "amount": converted,
                    "currency": target_currency,
                    "formatted": CurrencyService.format_currency(
                        converted, target_currency, include_symbol, decimal_places
                    ),
                }

        return result

    @staticmethod
    def get_currencies_in_use() -> List[str]:
        """Get list of currencies actually used in trading data."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT Currency FROM broker_transactions
                WHERE Currency IS NOT NULL AND Currency != ''
                ORDER BY Currency
            """)
            return [row[0] for row in cursor.fetchall()]

    @staticmethod
    def get_brokers_with_currencies() -> List[Dict[str, Any]]:
        """Get list of brokers with their associated currencies."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT broker_name, Currency
                FROM broker_transactions
                WHERE broker_name IS NOT NULL AND Currency IS NOT NULL
                ORDER BY broker_name, Currency
            """)
            results = {}
            for row in cursor.fetchall():
                broker = row[0]
                currency = row[1]
                if broker not in results:
                    results[broker] = {
                        "broker": broker,
                        "currencies": [],
                    }
                if currency not in results[broker]["currencies"]:
                    results[broker]["currencies"].append(currency)

            return list(results.values())

    @staticmethod
    def get_account_currencies() -> List[Dict[str, Any]]:
        """Get currencies associated with each account."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT account_id, account_name, broker_name, currency
                FROM accounts
                ORDER BY broker_name, account_name
            """)
            return [
                {
                    "account_id": row[0],
                    "account_name": row[1],
                    "broker": row[2],
                    "currency": row[3],
                }
                for row in cursor.fetchall()
            ]
