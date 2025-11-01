import matplotlib.pyplot as plt
import pandas as pd
import settings as _settings
from typing import Optional

# Base utilities used across all chart types
from settings import CURRENCY_SYMBOLS
import logging
import re
from typing import Optional
from settings import MARKET_MAPPINGS
logger = logging.getLogger(__name__)
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import sqlite3

def setup_base_figure():
    """Create a basic Plotly figure with standard layout"""
    fig = go.Figure()
    
    fig.update_layout(
        template='plotly_white',
        autosize=True,
        margin=dict(l=50, r=50, t=50, b=50),
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    return fig

def apply_standard_layout(fig, title):
    """Apply standard layout settings to a Plotly figure"""
    fig.update_layout(
        title=title,
        plot_bgcolor='white',
        paper_bgcolor='white',
        showlegend=True,
        legend=dict(
            x=0.0,
            y=1.0,
            xanchor='left',
            yanchor='top'
        ),
        margin=dict(
            l=150,    # Left margin for legend
            r=50,     # Right margin
            t=100,    # Top margin
            b=50,     # Bottom margin
            pad=4     # Padding
        ),
        autosize=True
    )
    
    # Add consistent grid styling
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='LightGray')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='LightGray')
    
    return fig

def ensure_currency_column(df, default_currency='USD'):
    """
    Ensures DataFrame has a currency column, adds default if missing
    """
    df_copy = df.copy()
    if 'currency' not in df_copy.columns:
        df_copy['currency'] = default_currency
    return df_copy

def prepare_dataframe(df):
    """
    Prepares dataframe with proper datetime handling and returns a clean copy
    """
    df_copy = df.copy()
    df_copy['Transaction Date'] = pd.to_datetime(df_copy['Transaction Date'])
    df_copy['Open Period'] = pd.to_datetime(df_copy['Open Period'])
    return df_copy

def get_trading_data(df):
    df_copy = prepare_dataframe(df)
    trading_mask = df_copy['Action'].str.contains('Trade', case=False, na=False)
    trading_data = df_copy[trading_mask].copy()
    trading_data['Transaction Date'] = pd.to_datetime(trading_data['Transaction Date'])
    logger.debug(f"Trading data Actions:\n{trading_data['Action'].unique()}")
    logger.debug(f"Trading data Descriptions:\n{trading_data['Description'].unique()}")
    return trading_data

def get_trade_counts(df):
    """
    Returns daily trade counts
    """
    df_copy = prepare_dataframe(df)
    trade_df = df_copy[df_copy['Action'].str.contains('Trade', case=False)]
    return trade_df.groupby(trade_df['Transaction Date'].dt.date).size()

def create_market_pl_chart(df):
    """
    Returns trading data with correct balance progression and pure trading P/L
    """
    df_copy = prepare_dataframe(df).copy()
    df_copy = df_copy.sort_values('Transaction Date')
    
    # Identify funding entries and trading entries
    funding_mask = df_copy['Action'].str.contains('Fund', case=False, na=False)
    trading_mask = df_copy['Action'].str.contains('Trade', case=False, na=False)
    
    # Create a new column for adjusted balance
    df_copy['Adjusted_Balance'] = df_copy['Balance'].copy()
    
    # Process each funding entry
    for idx in df_copy[funding_mask].index:
        funding_pl = df_copy.loc[idx, 'P/L']
        # Only adjust balances after this specific funding entry
        df_copy.loc[idx:, 'Adjusted_Balance'] -= funding_pl
    
    # Replace original Balance with adjusted balance
    df_copy['Balance'] = df_copy['Adjusted_Balance']
    df_copy.drop('Adjusted_Balance', axis=1, inplace=True)
    
    logger.debug(f"Trading data after funding adjustment:\n{df_copy[trading_mask][['Transaction Date', 'Action', 'Description', 'Balance', 'P/L']]}")
    
    return df_copy[trading_mask].copy()

def get_all_data():
    try:
        conn = sqlite3.connect('trading_data.db')
        query = """
            SELECT * FROM transactions 
            ORDER BY "Transaction Date" ASC
        """
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        # Convert date column to datetime
        df['Transaction Date'] = pd.to_datetime(df['Transaction Date'])
        return df
        
    except Exception as e:
        logger.error(f"Error fetching data from database: {str(e)}")
        raise

def get_broker_currency_groups(df):
    """
    Returns grouped data by broker and currency combinations
    """
    df_copy = prepare_dataframe(df)
    
    # Ensure currency column exists, default to USD if missing
    if 'currency' not in df_copy.columns:
        df_copy['currency'] = 'USD'
    
    # Group by broker and currency
    groups = df_copy.groupby(['broker_name', 'currency'])
    
    return groups

def get_trading_data_by_currency(df, broker=None, currency=None):
    """
    Returns trading data filtered by broker and/or currency
    """
    trading_data = get_trading_data(df)
    
    if broker:
        trading_data = trading_data[trading_data['broker_name'] == broker]
    
    if currency:
        # Ensure currency column exists
        if 'currency' not in trading_data.columns:
            trading_data['currency'] = 'USD'
        trading_data = trading_data[trading_data['currency'] == currency]
    
    return trading_data

def calculate_currency_metrics(df, broker, currency):
    """
    Calculate P/L metrics for a specific broker-currency combination
    """
    broker_currency_data = df[
        (df['broker_name'] == broker) & 
        (df['currency'] == currency)
    ].copy()
    
    total_pl = broker_currency_data['P/L'].sum()
    days_traded = len(broker_currency_data['Transaction Date'].dt.date.unique())
    daily_average = total_pl / days_traded if days_traded > 0 else 0
    
    # Calculate funding charges
    charges_mask = broker_currency_data['Action'].str.contains('Funding charge', case=False, na=False)
    total_charges = broker_currency_data[charges_mask]['P/L'].sum()
    
    # Calculate deposits and withdrawals
    deposits = broker_currency_data[broker_currency_data['Action'] == 'Fund rece received']['P/L'].sum()
    withdrawals = broker_currency_data[broker_currency_data['Action'] == 'Fund payable']['P/L'].sum()
    
    return {
        'total_pl': total_pl,
        'daily_average': daily_average,
        'total_charges': total_charges,
        'deposits': deposits,
        'withdrawals': withdrawals,
        'currency': currency
    }

def convert_to_base_currency(amount, from_currency, exchange_rates, base_currency='SEK'):
    """
    Convert amount from one currency to base currency
    """
    if from_currency == base_currency:
        return amount
    
    if from_currency in exchange_rates:
        # Direct conversion using the exchange rate
        return amount * exchange_rates[from_currency]
    else:
        logger.warning(f"Exchange rate not found for {from_currency}, using original amount")
        return amount

def format_currency_with_conversion(value, currency, exchange_rates, base_currency='SEK', show_converted=True):
    """
    Format currency value with optional conversion display
    """
    symbol = CURRENCY_SYMBOLS.get(currency, '')
    formatted = f'{symbol}{value:,.2f}'
    
    if show_converted and currency != base_currency:
        converted_value = convert_to_base_currency(value, currency, exchange_rates, base_currency)
        base_symbol = CURRENCY_SYMBOLS.get(base_currency, '')
        formatted += f' ({base_symbol}{converted_value:,.2f})'
    
    return formatted

def get_unified_currency_data(df, exchange_rates, target_currency='SEK'):
    """
    Convert all monetary values to a single currency for unified analysis
    """
    df_copy = df.copy()
    
    # Ensure currency column exists - use target_currency as default
    if 'currency' not in df_copy.columns:
        df_copy['currency'] = target_currency
    
    # Convert monetary columns
    monetary_columns = ['Amount', 'P/L', 'Balance', 'Fund_Balance', 'Opening', 'Closing']
    
    for col in monetary_columns:
        if col in df_copy.columns:
            df_copy[f'{col}_Original'] = df_copy[col].copy()  # Keep original values
            
            # Convert each row based on its currency
            for idx, row in df_copy.iterrows():
                original_currency = row['currency']
                if pd.notna(row[col]) and original_currency != target_currency:
                    converted_value = convert_to_base_currency(
                        row[col], original_currency, exchange_rates, target_currency
                    )
                    df_copy.at[idx, col] = converted_value
            
            # Update currency column to reflect conversion
            df_copy['currency'] = target_currency
    
    return df_copy

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

# --- Column / date / P/L helpers (public API) --------------------------------
def find_column(df, candidates):
    """Return first column in df whose normalized name matches candidates set."""
    return _find_column(df, candidates)

def find_date_col(df):
    return _find_date_col(df)

def find_pl_col(df):
    return _find_pl_col(df)

def coerce_date(df, col):
    return _coerce_date(df, col)

def coerce_pl_numeric(df, col, alias='_pl_numeric'):
    return _coerce_pl_numeric(df, col, alias)

def _infer_market_from_description(desc: str) -> str:
    """Try to infer a market name using settings.MARKET_MAPPINGS patterns."""
    if not isinstance(desc, str) or not desc:
        return 'Unknown'
    for source_map in (MARKET_MAPPINGS or {}).values():
        for market_name, patterns in source_map.items():
            if not isinstance(patterns, (list, tuple)):
                patterns = [patterns]
            for pat in patterns:
                try:
                    if re.search(pat, desc, flags=re.IGNORECASE):
                        return market_name
                except re.error:
                    continue
    return 'Unknown'

def ensure_market_column(df: Optional[pd.DataFrame], column_name: str = 'Market') -> pd.DataFrame:
    """
    Ensure the returned DataFrame has a Market column.
    - If a Market-like column exists, normalize its name to 'Market'.
    - Otherwise infer Market from Description using MARKET_MAPPINGS.
    Always returns a DataFrame (possibly a copy) and never a string.
    """
    if df is None:
        return pd.DataFrame()

    if not isinstance(df, pd.DataFrame):
        # defensive: try to coerce if possible
        try:
            df = pd.DataFrame(df)
        except Exception:
            logger.error("ensure_market_column: unable to coerce input to DataFrame, returning empty DataFrame")
            return pd.DataFrame()

    dfc = df.copy()

    # Detect existing market-like column
    market_col = None
    for c in dfc.columns:
        key = re.sub(r'[\s\-_]', '', c.strip().lower())
        if key in ('market', 'symbol', 'instrument'):
            market_col = c
            break

    if market_col:
        # normalize name
        if market_col != column_name:
            dfc = dfc.rename(columns={market_col: column_name})
        return dfc

    # Try to infer from Description (or Description-like columns)
    desc_col = None
    for c in dfc.columns:
        key = re.sub(r'[\s\-_]', '', c.strip().lower())
        if key in ('description', 'desc'):
            desc_col = c
            break

    if desc_col:
        try:
            dfc[column_name] = dfc[desc_col].astype(str).apply(_infer_market_from_description)
            return dfc
        except Exception:
            logger.exception("ensure_market_column: failed to infer Market from Description; falling back to Unknown")
            dfc[column_name] = 'Unknown'
            return dfc

    # No description or market column found — add Market='Unknown'
    dfc[column_name] = 'Unknown'
    return dfc

def normalize_trading_df(df: Optional[pd.DataFrame]) -> pd.DataFrame:
    """
    Normalize a raw trading dataframe for charts:
    - ensure DataFrame type
    - ensure 'Market' column (via ensure_market_column)
    - normalize/rename date column to 'Transaction Date' (using find_date_col)
    - coerce P/L to numeric into column '_pl_numeric'
    - ensure transaction_type categorical if present
    Always returns a DataFrame.
    """
    if df is None:
        return pd.DataFrame()

    if not isinstance(df, pd.DataFrame):
        try:
            df = pd.DataFrame(df)
        except Exception:
            logger.error("normalize_trading_df: cannot coerce to DataFrame")
            return pd.DataFrame()

    dfc = df.copy()

    # ensure market column (will add 'Market' if missing)
    try:
        dfc = ensure_market_column(dfc)
    except Exception:
        logger.exception("normalize_trading_df: ensure_market_column failed; adding fallback Market='Unknown'")
        dfc['Market'] = dfc.get('Market', 'Unknown')

    # normalize date column
    date_col = None
    try:
        date_col = find_date_col(dfc)
    except Exception:
        logger.debug("normalize_trading_df: find_date_col failed")

    if date_col:
        dfc[date_col] = pd.to_datetime(dfc[date_col], errors='coerce')
        if date_col != 'Transaction Date':
            dfc = dfc.rename(columns={date_col: 'Transaction Date'})
    else:
        dfc['Transaction Date'] = pd.to_datetime(dfc.get('Transaction Date'), errors='coerce')

    # ensure a numeric P/L alias for safe grouping/plotting
    try:
        pl_col = find_pl_col(dfc) or 'P/L'
    except Exception:
        pl_col = 'P/L'
    try:
        dfc['_pl_numeric'] = coerce_pl_numeric(dfc, pl_col)
    except Exception:
        # fallback: try simple coercion
        try:
            dfc['_pl_numeric'] = pd.to_numeric(dfc.get(pl_col, pd.Series([0]*len(dfc))), errors='coerce').fillna(0.0)
        except Exception:
            dfc['_pl_numeric'] = 0.0
    # Ensure final dtype is numeric (float)
    try:
        dfc['_pl_numeric'] = pd.to_numeric(dfc['_pl_numeric'], errors='coerce').fillna(0.0).astype(float)
    except Exception:
        logger.debug("normalize_trading_df: failed to force _pl_numeric to float; leaving as-is")

    # Ensure a normalized currency column exists for consumers that expect 'currency'
    try:
        if 'currency' not in dfc.columns:
            if 'Currency' in dfc.columns:
                dfc['currency'] = dfc['Currency']
            else:
                dfc['currency'] = getattr(_settings, "DEFAULT_BASE_CURRENCY", "USD")
    except Exception:
        logger.debug("normalize_trading_df: failed to ensure 'currency' column")

def aggregate_pl_by_period(df: pd.DataFrame, period: str = 'D', pl_col: str = '_pl_numeric', date_col: str = 'Transaction Date') -> pd.DataFrame:
    """
    Aggregate P/L by calendar period.
    period: pandas offset alias (e.g. 'D', 'W', 'M')
    Returns a DataFrame with two columns: ['Period', pl_col]
    """
    if df is None or df.empty:
        return pd.DataFrame(columns=['Period', pl_col])
    d = df.copy()
    if date_col not in d.columns:
        d[date_col] = pd.to_datetime(d.get(date_col))
    d[date_col] = pd.to_datetime(d[date_col], errors='coerce')
    d = d.dropna(subset=[date_col])
    d.set_index(date_col, inplace=True)
    agg = d[pl_col].resample(period).sum().reset_index().rename(columns={date_col: 'Period', pl_col: pl_col})
    return agg

def top_markets_by_pl(df: pd.DataFrame, pl_col: str = '_pl_numeric', label_col: str = 'Market', top_n: int = 10) -> pd.DataFrame:
    """
    Return top_n markets by summed P/L.
    """
    if df is None or df.empty:
        return pd.DataFrame(columns=[label_col, pl_col])
    d = df.copy()
    if label_col not in d.columns:
        d = ensure_market_column(d)
    d[label_col] = d[label_col].astype(str)
    agg = d.groupby(label_col)[pl_col].sum().reset_index().sort_values(pl_col, ascending=False).head(top_n)
    return agg

def get_filtered_trading_df(df: Optional[pd.DataFrame],
                            broker_key: Optional[str] = None,
                            account_id: Optional[int] = None,
                            start_date: Optional[str] = None,
                            end_date: Optional[str] = None) -> pd.DataFrame:
    """Normalize df and apply optional filters. Always returns a DataFrame."""
    dfc = normalize_trading_df(df)
    if dfc is None:
        dfc = pd.DataFrame()
    # broker filter
    if broker_key:
        try:
            dfc = dfc[dfc.get('broker_name', '') == broker_key]
        except Exception:
            pass
    # account filter
    if account_id and account_id != "all":
        try:
            dfc = dfc[dfc['account_id'] == account_id]
        except Exception:
            pass
    # date filters
    try:
        if start_date is not None:
            sd = pd.to_datetime(start_date, errors='coerce')
            if pd.notna(sd):
                dfc = dfc[dfc['Transaction Date'] >= sd]
        if end_date is not None:
            ed = pd.to_datetime(end_date, errors='coerce')
            if pd.notna(ed):
                dfc = dfc[dfc['Transaction Date'] <= ed]
    except Exception:
        logger.exception("get_filtered_trading_df: date filtering failed")
    return dfc.reset_index(drop=True)


def pick_label_col(df: pd.DataFrame, candidates=None) -> Optional[str]:
    """Pick best label column for grouping/axis."""
    if df is None or df.empty:
        return None
    if candidates is None:
        candidates = ['Description', 'Desc', 'Market', 'Instrument', 'Symbol']
    for c in candidates:
        if c in df.columns:
            return c
    # ensure Market exists
    df2 = ensure_market_column(df.copy())
    return 'Market' if 'Market' in df2.columns else (df2.columns[0] if len(df2.columns) else None)


def to_unified_currency(df: pd.DataFrame, exchange_rates: dict, base_currency: str,
                        pl_col: str = '_pl_numeric') -> pd.DataFrame:
    """Return copy with _pl_in_base and original_currency columns."""
    out = df.copy()
    out['original_currency'] = out.get('Currency', out.get('currency', pd.Series([None]*len(out))))
    # build conv factor (rate_for_currency -> base)
    def conv(curr):
        try:
            if not curr:
                return 1.0
            base_rate = exchange_rates.get(base_currency, 1.0) if base_currency else 1.0
            return (exchange_rates.get(curr, 1.0) / base_rate) if base_rate else 1.0
        except Exception:
            return 1.0
    out['_conv'] = out['original_currency'].apply(conv)
    out['_pl_in_base'] = pd.to_numeric(out.get(pl_col, out.get('P/L', 0)), errors='coerce').fillna(0.0) * out['_conv']
    return out


def format_currency(value, currency):
    """Format value using settings.CURRENCY_SYMBOLS fallback to currency text."""
    try:
        syms = getattr(_settings, "CURRENCY_SYMBOLS", {})
        symbol = syms.get(currency, currency if isinstance(currency, str) else "")
        return f"{symbol}{value:,.2f}"
    except Exception:
        return f"{value:.2f}"
