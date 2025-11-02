import os
import sqlite3
from typing import Optional, Dict, List
import pandas as pd
import settings as _settings
from chart_types.base import find_pl_col, coerce_pl_numeric  # centralized helpers
import logging
import re

logger = logging.getLogger(__name__)

# Import transaction import helper (try absolute then relative). If not present, set to None.
try:
    from import_data import import_transaction_data as import_transaction_data_from_module
except Exception:
    try:
        from .import_data import import_transaction_data as import_transaction_data_from_module
    except Exception:
        import_transaction_data_from_module = None
        logger.debug("import_transaction_data module not available; import functionality will be disabled until this is provided.")
# Import from settings instead
from settings import BROKERS, MARKET_MAPPINGS, MARKET_POINT_MULTIPLIERS  # safe defaults in settings

class DataManager:
    def __init__(self):
        self.df = None
        self.accounts_df = None
        self.db_connection = None
            
    def load_existing_data(self):
        """Load existing data from database with account information"""
        try:
            from create_database import create_db_schema
            create_db_schema()

            self.db_connection = sqlite3.connect('trading.db')
            # Always load transactions with account info
            self.df = pd.read_sql_query("""
                SELECT t.*, a.account_name, a.broker_name as account_broker
                FROM broker_transactions t
                LEFT JOIN accounts a ON t.account_id = a.account_id
            """, self.db_connection)
            self.accounts_df = pd.read_sql_query("SELECT * FROM accounts", self.db_connection)

            self.db_connection.close()
            self.db_connection = None

            # Normalize columns and canonicalize types/values immediately
            if self.df is not None and not self.df.empty:
                self.df = self._normalize_df_columns(self.df)
                # Ensure Transaction Date is datetime
                if 'Transaction Date' in self.df.columns:
                    self.df['Transaction Date'] = pd.to_datetime(self.df['Transaction Date'], errors='coerce')
                # Ensure P/L numeric
                if 'P/L' in self.df.columns:
                    self.df['P/L'] = pd.to_numeric(self.df['P/L'], errors='coerce').fillna(0.0)
                # Canonical Currency column and lowercase values
                if 'Currency' in self.df.columns:
                    self.df['Currency'] = self.df['Currency'].astype(str).str.strip()
                # Keep broker/account columns consistent
                if 'account_broker' in self.df.columns and 'broker_name' not in self.df.columns:
                    self.df = self.df.rename(columns={'account_broker': 'broker_name'})

                logger.info(f"Loaded {len(self.df)} existing records")
                if self.accounts_df is not None and not self.accounts_df.empty:
                    logger.info(f"Loaded {len(self.accounts_df)} accounts")
            else:
                logger.info("No existing data found")

        except Exception as e:
            logger.warning(f"No existing data loaded: {e}")
            if self.db_connection:
                self.db_connection.close()
                self.db_connection = None

    def import_data(self, file_path, broker_key, account_id=None):
        try:
            # Check if file exists
            if not os.path.exists(file_path):
                logger.error(f"File not found: {file_path}")
                return False

            # Ensure account_id is integer
            if account_id is not None:
                account_id = int(account_id)
            else:
                logger.error("Account ID is required for importing data")
                return False
                
            logger.info(f"Importing data from {file_path} for broker: {broker_key}, account: {account_id}")
            
            # Use the import_transaction_data function from import_data.py
            try:
                if import_transaction_data_from_module is None:
                    raise RuntimeError("import_transaction_data function not found; ensure import_data.py exists and exports import_transaction_data")
                result_df = import_transaction_data_from_module(file_path, broker_key, account_id)
                logger.info(f"Successfully imported data with {len(result_df)} records")
                
                # Update the current dataframe by reloading from the database
                self.load_existing_data()
                return True
            except Exception as e:
                logger.error(f"Error in import_transaction_data: {e}")
                logger.error(traceback.format_exc())
                raise
                
        except Exception as e:
            logger.error(f"Failed to import data: {e}")
            return False

    def _normalize_df_columns(self, df):
        """
        Normalize common DB/import column variants to canonical names used by the UI code.
        Returns a new DataFrame (does not mutate input).
        """
        if df is None or df.empty:
            return df

        # mapping keys are normalized forms (lowercase, no spaces/underscores/dashes)
        norm_to_canonical = {
            'transactiondate': 'Transaction Date',
            'transaction_date': 'Transaction Date',
            'transaction-date': 'Transaction Date',
            'date': 'Transaction Date',

            'pl': 'P/L',
            'p/l': 'P/L',
            'profitloss': 'P/L',
            'plamount': 'P/L',
            'profit': 'P/L',

            'description': 'Description',
            'desc': 'Description',

            'market': 'Market',

            'balance': 'Balance',

            'currency': 'Currency',
            'curr': 'Currency',

            'broker_name': 'broker_name',
            'brokername': 'broker_name',
            'broker': 'broker_name',

            'account_id': 'account_id',
            'accountid': 'account_id',
        }

        col_map = {}
        for c in df.columns:
            key = re.sub(r'[\s\-_]', '', c.strip().lower())
            # try direct match, then fallback to stripped key
            if key in norm_to_canonical:
                col_map[c] = norm_to_canonical[key]

        normalized = df.rename(columns=col_map).copy() if col_map else df.copy()
        # Ensure canonical date column (best-effort)
        for date_cand in ('Transaction Date', 'transactiondate', 'date', 'Date'):
            if date_cand in normalized.columns:
                try:
                    normalized[date_cand] = pd.to_datetime(normalized[date_cand], errors='coerce')
                    normalized.rename(columns={date_cand: 'Transaction Date'}, inplace=True)
                    break
                except Exception:
                    continue

        # Ensure numeric P/L alias exists
        pl_col = find_pl_col(normalized) or 'P/L'
        coerce_pl_numeric(normalized, pl_col, alias='_pl_numeric')

        # Canonicalize common text columns
        if 'Action' in normalized.columns:
            normalized['Action'] = normalized['Action'].astype(str)
        if 'Description' in normalized.columns:
            normalized['Description'] = normalized['Description'].astype(str)

        # Classify transactions now so further logic can rely on transaction_type
        try:
            normalized = self._classify_transactions(normalized)
        except Exception:
            logger.exception("Failed to classify transactions during normalization")

        return normalized

    # Keep only your filter methods and data access methods below
    def get_data_by_year(self, year=None):
        """Get data filtered by year"""
        if not self.has_data():
            return None

        filtered_df = self.df.copy()

        if year and year != "All Years":
            filtered_df['Transaction Date'] = pd.to_datetime(filtered_df['Transaction Date'])
            filtered_df = filtered_df[filtered_df['Transaction Date'].dt.year == int(year)]

        return filtered_df

    def get_data_by_month(self, year, month=None):
        """Get data filtered by year and month"""
        if not self.has_data():
            return None

        filtered_df = self.get_data_by_year(year)

        if month and month != "All Months":
            filtered_df['Transaction Date'] = pd.to_datetime(filtered_df['Transaction Date'])
            filtered_df = filtered_df[filtered_df['Transaction Date'].dt.month == int(month)]

        return filtered_df

    def get_data_by_day(self, year, month, day=None):
        """Get data filtered by year, month, and day"""
        if not self.has_data():
            return None

        filtered_df = self.get_data_by_month(year, month)

        if day and day != "All Days":
            filtered_df['Transaction Date'] = pd.to_datetime(filtered_df['Transaction Date'])
            filtered_df = filtered_df[filtered_df['Transaction Date'].dt.day == int(day)]

        return filtered_df

    def calculate_pl_per_trade(self, df):
        """Calculate P/L per trade for each market"""
        if 'Market' not in df.columns or 'P/L' not in df.columns:
            return None
            
        # Group by market and calculate P/L per trade
        market_stats = df.groupby('Market').agg({
            'P/L': 'sum',
            'Transaction Date': 'count'
        }).rename(columns={'Transaction Date': 'Trades'})

        # Calculate P/L per trade
        market_stats['P/L per Trade'] = market_stats['P/L'] / market_stats['Trades']

        return market_stats.sort_values('P/L per Trade', ascending=False)

    def convert_to_base_currency(self, amount, currency, base_currency, exchange_rates):
        """Convert amount to base currency using exchange rates"""
        # Strict conversion that relies on settings.SUPPORTED_CURRENCIES and the canonical
        # DEFAULT_EXCHANGE_RATES_PER_BASE mapping. Do not attempt to guess arbitrary formats.
        if amount == 0 or currency == base_currency:
            return amount

        supported = getattr(_settings, 'SUPPORTED_CURRENCIES', None)
        if supported and (currency not in supported or base_currency not in supported):
            logger.error("Unsupported currency pair: %s -> %s. Supported: %s", currency, base_currency, supported)
            raise ValueError(f"Unsupported currency: {currency} or {base_currency}")

        # Prefer a provided per-base exchange_rates mapping (expected shape: { base_currency: { CUR: rate } })
        rates_per_base = None
        if isinstance(exchange_rates, dict) and exchange_rates:
            # If it's already per-base (has base_currency as top-level key)
            if base_currency in exchange_rates and isinstance(exchange_rates[base_currency], dict):
                rates_per_base = exchange_rates
            else:
                # If it's a flat mapping assumed to be rates relative to base_currency
                # validate keys are supported currencies
                keys = set(exchange_rates.keys())
                if supported is None or keys.issubset(set(supported)):
                    rates_per_base = {base_currency: exchange_rates}

        # Fall back to canonical DEFAULT_EXCHANGE_RATES_PER_BASE from settings
        if rates_per_base is None:
            rates_per_base = getattr(_settings, 'DEFAULT_EXCHANGE_RATES_PER_BASE', {})

        per_base = rates_per_base.get(base_currency) or {}
        if not per_base:
            logger.error("No exchange rates available for base currency %s", base_currency)
            raise ValueError(f"No exchange rates available for base currency {base_currency}")

        # Expect per_base to map currency -> value_in_base (e.g. 'EUR': 11.32 meaning 1 EUR = 11.32 SEK)
        if currency not in per_base:
            logger.error("Missing rate for %s -> %s in configured rates", currency, base_currency)
            raise ValueError(f"Missing exchange rate for {currency} to {base_currency}")

        try:
            rate = float(per_base[currency])
            return amount * rate
        except Exception as e:
            logger.exception("Failed to apply exchange rate for %s -> %s: %s", currency, base_currency, e)
            raise

    def calculate_total_balance(self, df, base_currency, exchange_rates):
        """Calculate total balance in base currency"""
        # Use canonical 'Balance' and 'Currency' names
        if df is None or df.empty:
            return 0.0
        if 'Balance' not in df.columns or 'Currency' not in df.columns:
            return 0.0

        total_balance = 0.0
        for _, row in df.iterrows():
            # guard and coerce
            try:
                amount = float(row['Balance'])
            except Exception:
                amount = 0.0
            currency = row['Currency']

            # Convert to base currency
            converted_amount = self.convert_to_base_currency(amount, currency, base_currency, exchange_rates)
            total_balance += converted_amount

        return total_balance

    def calculate_points(self, df: Optional[pd.DataFrame], market_point_multipliers: Optional[Dict[str, float]] = None) -> int:
        """
        Centralized points calculation. Accepts a (normalized) DataFrame and returns total points.
        DataManager normalization should ensure common column names, but this helper is tolerant.
        """
        if market_point_multipliers is None:
            market_point_multipliers = MARKET_POINT_MULTIPLIERS or {}

        if df is None or df.empty:
            return 0

        # Operate on trading rows only (use explicit classification if available)
        trading_df = df.copy()
        if 'transaction_type' in trading_df.columns:
            trading_df = trading_df[trading_df['transaction_type'] == 'trading'].copy()
        else:
            trading_df = self.get_trading_df(df)

        if trading_df is None or trading_df.empty:
            return 0

        # Restrict to trades that have valid opening and closing prices
        valid_trades = self.filter_valid_open_close_trades(trading_df)
        if valid_trades is None or valid_trades.empty:
            # no valid open/close trades -> no points
            return 0

        # Determine P/L numeric column (prefer normalized alias)
        pl_col = None
        for c in valid_trades.columns:
            key = re.sub(r'[\s\-_]', '', str(c).strip().lower())
            if key in ('p/l', 'pl', 'plamount', 'profitloss', 'profit'):
                pl_col = c
                break
        if pl_col is None:
            for alias in ('_pl_numeric', 'pl_numeric', '_pl'):
                if alias in valid_trades.columns:
                    pl_col = alias
                    break
        if pl_col is None:
            return 0

        # Ensure Market column exists (infer from Description if necessary)
        if 'Market' not in valid_trades.columns and 'Description' in valid_trades.columns:
            def infer(desc):
                if not isinstance(desc, str):
                    return 'Unknown'
                for source_map in (MARKET_MAPPINGS or {}).values():
                    for market_name, patterns in source_map.items():
                        for pat in patterns:
                            try:
                                if re.search(pat, desc, flags=re.IGNORECASE):
                                    return market_name
                            except re.error:
                                continue
                return 'Unknown'
            valid_trades = valid_trades.copy()
            valid_trades['Market'] = valid_trades['Description'].apply(infer)

        if 'Market' not in valid_trades.columns:
            return 0

        # Signed P/L numeric values
        pl_values = pd.to_numeric(valid_trades[pl_col], errors='coerce').fillna(0.0)

        # Compute points per trade: apply multiplier to magnitude and preserve sign
        def compute_points_pair(pl_val, market):
            try:
                mult = float(market_point_multipliers.get(market, 1.0))
            except Exception:
                mult = 1.0
            pts = abs(pl_val) * mult
            return pts if pl_val >= 0 else -pts

        points_list = [compute_points_pair(p, m) for p, m in zip(pl_values, valid_trades['Market'])]
        points_series = pd.Series(points_list, index=valid_trades.index)

        # Sum points per market then total, preserve sign and round to nearest int
        market_points = points_series.groupby(valid_trades['Market']).sum()
        total_points = int(round(market_points.sum())) if not market_points.empty else 0
        return total_points

    def filter_valid_open_close_trades(self, df: Optional[pd.DataFrame]) -> pd.DataFrame:
        """
        Return rows that have valid opening and closing prices (non-null and non-zero).
        Detection of opening/closing columns is tolerant to common variants:
        'Opening', 'Open', 'opening', 'Closing', 'Close', 'closing', but excludes 'Open Period' etc.
        This is intended to be a conservative filter used for point calculations where both prices are required.
        """
        if df is None or df.empty:
            return pd.DataFrame()

        dfc = df.copy()

        # find candidate opening/closing columns
        opening_col = None
        closing_col = None
        for c in dfc.columns:
            lc = c.lower().strip()
            # skip misleading columns
            if 'period' in lc:
                continue
            if (('open' == lc) or ('opening' in lc) or (lc.startswith('open') and not 'openperiod' in lc)) and opening_col is None:
                opening_col = c
            if (('close' == lc) or ('closing' in lc) or (lc.startswith('close'))) and closing_col is None:
                closing_col = c

        # If not found, try looser search (contains)
        if opening_col is None:
            for c in dfc.columns:
                if 'open' in c.lower() and 'period' not in c.lower():
                    opening_col = c
                    break
        if closing_col is None:
            for c in dfc.columns:
                if 'close' in c.lower():
                    closing_col = c
                    break

        # If either not found, return empty frame (we cannot be sure)
        if not opening_col or not closing_col:
            logger.debug("filter_valid_open_close_trades: could not find opening/closing columns (opening=%s closing=%s)", opening_col, closing_col)
            return pd.DataFrame(columns=dfc.columns)

        # coerce to numeric and require non-zero values
        try:
            open_vals = pd.to_numeric(dfc[opening_col], errors='coerce').fillna(0.0).abs()
            close_vals = pd.to_numeric(dfc[closing_col], errors='coerce').fillna(0.0).abs()
        except Exception:
            logger.exception("filter_valid_open_close_trades: error coercing open/close columns to numeric")
            return pd.DataFrame(columns=dfc.columns)

        mask = (open_vals != 0.0) & (close_vals != 0.0)
        # also ensure both are not NaT (for datetime columns that might be misdetected)
        mask = mask & (~pd.isna(dfc[opening_col])) & (~pd.isna(dfc[closing_col]))

        result = dfc[mask].copy()
        logger.debug("filter_valid_open_close_trades: found %d valid rows out of %d", len(result), len(dfc))
        return result

    def get_top_markets(self, df: Optional[pd.DataFrame], top_n: int = 5) -> pd.DataFrame:
        """
        Return top_n markets by P/L per trade. Returns a DataFrame with columns:
        ['Market', 'Total P/L', 'Avg P/L per Trade', 'Total Trades']
        """
        if df is None or df.empty:
            return pd.DataFrame(columns=['Market', 'Total P/L', 'Avg P/L per Trade', 'Total Trades'])

        df = df.copy()
        # operate only on trading rows
        if 'transaction_type' in df.columns:
            df = df[df['transaction_type'] == 'trading'].copy()

        # find P/L column or alias
        pl_col = None
        for c in df.columns:
            key = re.sub(r'[\s\-_]', '', str(c).strip().lower())
            if key in ('p/l', 'pl', 'plamount', 'profitloss', 'profit'):
                pl_col = c
                break
        if pl_col is None:
            for alias in ('_pl_numeric', 'pl_numeric', '_pl'):
                if alias in df.columns:
                    pl_col = alias
                    break
        if pl_col is None:
            return pd.DataFrame(columns=['Market', 'Total P/L', 'Avg P/L per Trade', 'Total Trades'])

        # ensure market column
        if 'Market' not in df.columns and 'Description' in df.columns:
            def infer(desc):
                if not isinstance(desc, str):
                    return 'Unknown'
                for source_map in (MARKET_MAPPINGS or {}).values():
                    for market_name, patterns in source_map.items():
                        for pat in patterns:
                            try:
                                if re.search(pat, desc, flags=re.IGNORECASE):
                                    return market_name
                            except re.error:
                                continue
                return 'Unknown'
            df['Market'] = df['Description'].apply(infer)

        # numeric PL
        df['___pl'] = pd.to_numeric(df[pl_col], errors='coerce').fillna(0)

        grouped = df.groupby('Market').agg(
            Total_PL=('___pl', 'sum'),
            Avg_PL=('___pl', 'mean'),
            Total_Trades=('___pl', 'count')
        ).reset_index()

        grouped['P/L per Trade'] = grouped.apply(lambda r: (r['Total_PL'] / r['Total_Trades']) if r['Total_Trades'] else 0.0, axis=1)
        result = grouped.rename(columns={'Avg_PL': 'Avg P/L per Trade', 'Total_PL': 'Total P/L'}).sort_values('P/L per Trade', ascending=False).head(top_n)
        return result[['Market', 'Total P/L', 'Avg P/L per Trade', 'Total_Trades']].rename(columns={'Total_Trades': 'Total Trades'})

    def get_data(self):
        """Get the current dataframe (returned copy is normalized and safe to mutate)"""
        if self.df is None:
            return None
        # Return a copy to avoid callers mutating the master df
        return self.df.copy()

    def has_data(self):
        """Check if data is available"""
        return self.df is not None and not self.df.empty

    def get_filtered_data(self, broker_filter=None, account_id=None, start_date=None, end_date=None):
        """Get filtered data based on criteria"""
        if not self.has_data():
                return None

        filtered_df = self.df.copy()

        if broker_filter and broker_filter != 'All':
            filtered_df = filtered_df[filtered_df['broker_name'] == broker_filter]

        if account_id and account_id != 'all':
            try:
                filtered_df = filtered_df[filtered_df['account_id'] == int(account_id)]
            except ValueError:
                logger.error(f"Invalid account_id for filtering: {account_id}")
                return None

        if start_date and end_date:
            try:
                filtered_df['Transaction Date'] = pd.to_datetime(filtered_df['Transaction Date'])
                filtered_df = filtered_df[
                    (filtered_df['Transaction Date'].dt.date >= pd.to_datetime(start_date).date()) &
                    (filtered_df['Transaction Date'].dt.date <= pd.to_datetime(end_date).date())
                ]
            except ValueError as e:
                logger.error(f"Date filtering error: {e}")
                return None
                
        return filtered_df

    def cleanup(self):
        """Clean up database connections"""
        try:
            if self.db_connection:
                self.db_connection.close()
                self.db_connection = None
        except Exception as e:
            logger.error(f"Error cleaning up database connections: {e}")

    def get_trading_df(self, df: Optional[pd.DataFrame]) -> pd.DataFrame:
        """
        Return a DataFrame containing only trading transactions (exclude funding/deposits/withdrawals/charges).
        Ensures a numeric P/L alias '_pl_numeric' exists on the returned frame.
        """
        if df is None or df.empty:
            return pd.DataFrame()

        dfc = df.copy()

        # If transaction_type exists, use it (fast path)
        if 'transaction_type' in dfc.columns:
            return dfc[dfc['transaction_type'] == 'trading'].copy()

        # Otherwise attempt to classify and then filter
        try:
            dfc = self._classify_transactions(dfc)
            return dfc[dfc['transaction_type'] == 'trading'].copy()
        except Exception:
            # fallback: treat non-zero _pl_numeric rows as trading
            pl_series = pd.to_numeric(dfc.get('_pl_numeric', pd.Series(dtype=float)), errors='coerce').fillna(0.0)
            trading_df = dfc[pl_series != 0.0].copy()
            return trading_df

    def get_trading_pl_total(self, df: Optional[pd.DataFrame]) -> float:
        """Return total (sum) of trading P/L using the normalized numeric alias."""
        if df is None:
            return 0.0

        if 'transaction_type' in df.columns:
            trading_df = df[df['transaction_type'] == 'trading']
        else:
            trading_df = self.get_trading_df(df)

        if trading_df is None or trading_df.empty:
            return 0.0

        return float(trading_df.get('_pl_numeric', pd.Series(dtype=float)).sum())

    def get_available_years(self) -> List[int]:
        """
        Return available years (ints) present in the stored trading data.

        Strategy (simple, sqlite-first):
        - If self.conn (sqlite3.Connection) and a table name exists, run a DISTINCT year query.
        - Else if self.db_path / self.database is set, open sqlite and run the query.
        - Else fall back to loading a DataFrame via get_all_data()/get_filtered_data() and derive years.
        """
        try:
            # prefer explicit table name attributes
            table = getattr(self, "table_name", None) or getattr(self, "table", None) or getattr(self, "transactions_table", None)
            date_col = getattr(self, "date_col", "Transaction Date")

            # 1) sqlite connection on the manager
            conn = getattr(self, "conn", None) or getattr(self, "connection", None) or getattr(self, "db_connection", None)
            if isinstance(conn, sqlite3.Connection) and table:
                try:
                    cur = conn.cursor()
                    q = f'SELECT DISTINCT strftime(\'%Y\', "{date_col}") FROM "{table}" WHERE "{date_col}" IS NOT NULL'
                    cur.execute(q)
                    rows = [int(r[0]) for r in cur.fetchall() if r and r[0] is not None]
                    years = sorted(set(rows), reverse=True)
                    return years
                except Exception:
                    pass

            # 2) sqlite file path
            db_path = getattr(self, "db_path", None) or getattr(self, "database", None)
            if db_path and table:
                try:
                    with sqlite3.connect(db_path) as c:
                        cur = c.cursor()
                        q = f'SELECT DISTINCT strftime(\'%Y\', "{date_col}") FROM "{table}" WHERE "{date_col}" IS NOT NULL'
                        cur.execute(q)
                        rows = [int(r[0]) for r in cur.fetchall() if r and r[0] is not None]
                        years = sorted(set(rows), reverse=True)
                        return years
                except Exception:
                    pass

            # 3) Fallback: load dataframe and derive years
            df = None
            if hasattr(self, "get_all_data") and callable(getattr(self, "get_all_data")):
                try:
                    df = self.get_all_data()
                except Exception:
                    df = None
            if (df is None or not isinstance(df, pd.DataFrame) or df.empty) and hasattr(self, "get_filtered_data") and callable(getattr(self, "get_filtered_data")):
                try:
                    df = self.get_filtered_data()
                except Exception:
                    df = None

            if df is None or not isinstance(df, pd.DataFrame) or df.empty:
                return []

            # choose Transaction Date (or find a date column)
            if date_col not in df.columns:
                date_col = next((c for c in df.columns if "date" in c.lower()), date_col)
            df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
            years = sorted(df[date_col].dt.year.dropna().unique().astype(int).tolist(), reverse=True)
            return years
        except Exception:
            return []

    def _classify_transactions(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Annotate df with a 'transaction_type' column using patterns from settings.
        Expected mapping in settings: TRANSACTION_TYPE_PATTERNS = {
            'funding': [r'fund', r'deposit', ...],
            'charge': [r'charge', r'fee', ...],
            'withdrawal': [r'withdraw', ...],
            'trading': [r'buy', r'sell', r'open', r'close', r'trade', ...],
        }
        This function is tolerant: it uses Action and Description columns and falls back to _pl_numeric sign.
        """
        if df is None or df.empty:
            return df

        dfc = df.copy()

        # Ensure working columns exist
        if 'Action' not in dfc.columns:
            dfc['Action'] = dfc.get('Action', '').astype(str)
        if 'Description' not in dfc.columns:
            dfc['Description'] = dfc.get('Description', '').astype(str)
        if '_pl_numeric' not in dfc.columns:
            pl_col = find_pl_col(dfc) or 'P/L'
            coerce_pl_numeric(dfc, pl_col, alias='_pl_numeric')

        patterns = getattr(_settings, 'TRANSACTION_TYPE_PATTERNS', None)
        if patterns is None:
            # sensible defaults
            patterns = {
                'funding': [r'fund', r'deposit', r'receivable', r'payable'],
                'charge': [r'charge', r'fee', r'commission'],
                'withdrawal': [r'withdraw', r'withdrawal', r'payable'],
                'trading': [r'\bbuy\b', r'\bsell\b', r'\bopen\b', r'\bclose\b', r'\btrade\b', r'executed|execution|filled'],
            }

        # initialize as other
        dfc['transaction_type'] = 'other'

        # Apply patterns in order; allow settings to define priority by insertion order
        for ttype, pats in patterns.items():
            if not isinstance(pats, (list, tuple)):
                pats = [pats]
            combined = "|".join(f"(?:{p})" for p in pats)
            try:
                mask_action = dfc['Action'].astype(str).str.contains(combined, case=False, na=False, regex=True)
            except Exception:
                mask_action = pd.Series(False, index=dfc.index)
            try:
                mask_desc = dfc['Description'].astype(str).str.contains(combined, case=False, na=False, regex=True)
            except Exception:
                mask_desc = pd.Series(False, index=dfc.index)
            mask = mask_action | mask_desc
            # set type where still other
            dfc.loc[(dfc['transaction_type'] == 'other') & mask, 'transaction_type'] = ttype

        # If still classified as 'other', use _pl_numeric nonzero as trading
        nontrading_mask = dfc['transaction_type'] == 'other'
        try:
            pl_nonzero = pd.to_numeric(dfc.get('_pl_numeric', pd.Series(dtype=float)), errors='coerce').fillna(0.0) != 0.0
            dfc.loc[nontrading_mask & pl_nonzero, 'transaction_type'] = 'trading'
        except Exception:
            logger.exception("Error when falling back to _pl_numeric for transaction classification")

        # final cleanup: cast to category
        try:
            dfc['transaction_type'] = dfc['transaction_type'].astype('category')
        except Exception:
            pass

        return dfc
