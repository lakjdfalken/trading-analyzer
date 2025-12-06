import logging
import os
import sqlite3
import traceback
from datetime import datetime

import pandas as pd

from db_path import DATABASE_PATH
from file_handler import clean_csv_format, detect_file_format
from logger import setup_logger
from settings import COLUMN_MAPPINGS

# Initialize logger
logger = logging.getLogger(__name__)

# Canonical database column names - these MUST match the existing database schema
DB_COLUMN_NAMES = {
    "transaction_date": "Transaction Date",
    "open_period": "Open Period",
    "reference": "Ref. No.",
    "action": "Action",
    "description": "Description",
    "amount": "Amount",
    "pl": "P/L",
    "balance": "Balance",
    "opening": "Opening",
    "closing": "Closing",
    "status": "Status",
    "currency": "Currency",
}


def standardize_columns(df, mapping):
    """
    Standardize column names using the mapping configuration.

    Args:
        df: Original DataFrame with broker-specific column names
        mapping: Dictionary mapping standardized names to possible broker column names

    Returns:
        DataFrame with standardized column names
    """
    standardized_df = df.copy()

    # Create a mapping from actual column names to standardized names
    column_map = {}
    for std_name, possible_names in mapping.items():
        for possible_name in possible_names:
            if possible_name in df.columns:
                column_map[possible_name] = std_name
                break

    # Log any missing required columns
    for std_name, possible_names in mapping.items():
        if not any(name in df.columns for name in possible_names):
            logger.warning(
                f"No match found for required column '{std_name}'. Expected one of: {possible_names}"
            )

    # Rename the columns
    standardized_df = standardized_df.rename(columns=column_map)

    return standardized_df


def get_unique_transaction_id(row):
    """
    Create a unique identifier for a transaction row.
    Works with both standardized and original column names.
    Falls back to generating a deterministic ID if no reference column exists.
    """
    import hashlib

    # Find the appropriate date column
    date_col = None
    date_candidates = ["Transaction Date", "transaction_date", "Date", "date"]
    for candidate in date_candidates:
        if candidate in row:
            date_col = candidate
            break

    if date_col is None:
        available_cols = list(row.keys()) if hasattr(row, "keys") else list(row.index)
        logger.error(f"Cannot find date column. Available columns: {available_cols}")
        raise KeyError(f"Missing date column in transaction row")

    # Find the appropriate reference column - expanded list of candidates
    ref_col = None
    ref_candidates = [
        "Ref. No.",
        "Ref No",
        "Ref",
        "Reference",
        "reference",
        "Serial",
        "Serial No",
        "serial",
        "serial_no",
        "Transaction ID",
        "transaction_id",
        "ID",
        "id",
    ]
    for candidate in ref_candidates:
        if candidate in row:
            ref_col = candidate
            break

    # Find the appropriate action column
    action_col = None
    action_candidates = ["Action", "action", "Type", "type"]
    for candidate in action_candidates:
        if candidate in row:
            action_col = candidate
            break

    if action_col is None:
        available_cols = list(row.keys()) if hasattr(row, "keys") else list(row.index)
        logger.error(f"Cannot find action column. Available columns: {available_cols}")
        raise KeyError(f"Missing action column in transaction row")

    # Use string representation for date to avoid datetime comparison issues
    date_value = str(row[date_col])
    action_value = str(row[action_col])

    # If we have a reference column, use it
    if ref_col is not None:
        ref_value = str(row[ref_col])
        return f"{date_value}_{ref_value}_{action_value}"

    # Fallback: generate deterministic ID from multiple fields
    logger.debug("No reference column found, generating deterministic ID from row data")
    key_parts = [
        date_value,
        action_value,
        str(row.get("Amount", row.get("amount", ""))),
        str(row.get("Opening", row.get("opening", ""))),
        str(row.get("Closing", row.get("closing", ""))),
        str(row.get("Description", row.get("description", ""))),
        str(row.get("P/L", row.get("pl", row.get("pnl", "")))),
    ]
    key_str = "|".join(key_parts)
    generated_id = hashlib.sha1(key_str.encode("utf-8")).hexdigest()[:16]
    return f"{date_value}_{generated_id}_{action_value}"


def fix_future_dates(df, date_columns=["transaction_date", "open_period"]):
    """
    Fix dates that appear to be in the future

    This function checks if dates are unreasonably far in the future and
    corrects them by swapping day and month if they appear to be in MM/DD format
    instead of DD/MM format.
    """
    current_year = datetime.now().year

    for col in date_columns:
        if col in df.columns:
            # Convert to datetime if not already
            if not pd.api.types.is_datetime64_any_dtype(df[col]):
                df[col] = pd.to_datetime(df[col], errors="coerce")

            # Check for future dates
            future_mask = df[col] > datetime.now()
            future_count = future_mask.sum()

            if future_count > 0:
                logger.warning(
                    f"Found {future_count} dates in the future in column '{col}'"
                )

                # Sample of future dates for debugging
                sample = df.loc[future_mask, col].head(5).tolist()
                logger.debug(f"Sample future dates: {sample}")

                # Try to fix future dates by swapping day/month
                future_dates = df.loc[future_mask, col].copy()
                fixed_dates = future_dates.copy()

                for i, date in enumerate(future_dates):
                    if date.year > current_year:
                        # Try to swap day and month
                        try:
                            # Create a new date with swapped day/month
                            if date.day <= 12:  # Only swap if day can be a valid month
                                fixed_date = date.replace(
                                    year=date.year - 1, month=date.day, day=date.month
                                )
                                fixed_dates.iloc[i] = fixed_date
                                logger.debug(
                                    f"Fixed future date: {date} -> {fixed_date}"
                                )
                        except Exception as e:
                            logger.error(f"Failed to fix future date {date}: {str(e)}")

                # Apply fixed dates
                df.loc[future_mask, col] = fixed_dates

                # Check if we still have future dates
                still_future = (df[col] > datetime.now()).sum()
                if still_future > 0:
                    logger.warning(
                        f"Still have {still_future} future dates after fixing"
                    )
                else:
                    logger.info(
                        f"Successfully fixed all future dates in column '{col}'"
                    )

    return df


def parse_dates_with_multiple_formats(df, columns):
    """
    Try to parse date columns with multiple formats.
    Prioritizes EU format (DD/MM/YYYY) which is common in broker exports.
    """
    date_formats = [
        "%d/%m/%Y %H:%M:%S",  # EU format with seconds (most common for brokers)
        "%d/%m/%Y %H:%M",  # EU format without seconds
        "%Y-%m-%d %H:%M:%S",  # ISO format with seconds
        "%Y-%m-%d %H:%M",  # ISO format without seconds
        "%Y-%m-%d",  # ISO format date only
        "%m/%d/%Y %H:%M:%S",  # US format with seconds
        "%m/%d/%Y %H:%M",  # US format without seconds
    ]

    for col in columns:
        if col not in df.columns:
            logger.error(f"Missing column {col} for date parsing")
            continue

        # Skip if already datetime
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            logger.debug(f"Column {col} is already datetime type")
            continue

        parsed = False
        original_values = df[col].copy()

        # Try each format
        for date_format in date_formats:
            try:
                logger.debug(f"Trying to parse {col} with format {date_format}")
                parsed_dates = pd.to_datetime(
                    df[col], format=date_format, errors="raise"
                )
                df[col] = parsed_dates
                logger.info(f"Successfully parsed {col} with format {date_format}")
                parsed = True
                break
            except (ValueError, TypeError) as e:
                logger.debug(f"Format {date_format} failed for {col}: {e}")
                continue

        if not parsed:
            # If none of the formats work, try the pandas default parser with dayfirst=True
            logger.warning(
                f"Could not parse {col} with specified formats, trying pandas default with dayfirst=True"
            )
            try:
                df[col] = pd.to_datetime(
                    original_values, dayfirst=True, errors="coerce"
                )
            except Exception as e:
                logger.error(f"Failed to parse {col} with pandas default: {e}")
                df[col] = pd.to_datetime(original_values, errors="coerce")

            # Check for NaT values
            nat_count = df[col].isna().sum()
            if nat_count > 0:
                logger.warning(f"Found {nat_count} unparseable dates in column {col}")

    return df


def sanitize_dates_for_sqlite(df, columns):
    """
    Convert datetime columns to ISO format strings for SQLite compatibility.
    SQLite expects dates in 'YYYY-MM-DD HH:MM:SS' format.
    """
    for col in columns:
        if col not in df.columns:
            continue

        if pd.api.types.is_datetime64_any_dtype(df[col]):
            # Convert to ISO format string
            df[col] = df[col].dt.strftime("%Y-%m-%d %H:%M:%S")
            logger.debug(f"Converted {col} to ISO format for SQLite")
        else:
            # Try to parse and convert
            try:
                parsed = pd.to_datetime(df[col], dayfirst=True, errors="coerce")
                df[col] = parsed.dt.strftime("%Y-%m-%d %H:%M:%S")
                logger.debug(f"Parsed and converted {col} to ISO format")
            except Exception as e:
                logger.warning(f"Could not convert {col} to ISO format: {e}")

    return df


def import_transaction_data(file_path, broker_name="trade_nation", account_id=None):
    """
    Import transaction data from a CSV file into the database.

    Args:
        file_path: Path to the CSV file
        broker_name: Name of the broker (trade_nation or td365)
        account_id: Account ID for the transactions

    Returns:
        DataFrame with the imported data
    """
    logger.debug(
        f"Attempting to import data from {file_path} for broker: {broker_name}, with account_id: {account_id}"
    )

    # Check if account_id is provided
    if account_id is None:
        raise ValueError("Account ID must be provided for importing transactions")

    # Detect and handle file format
    # File is already converted to UTF-8 by the import endpoint
    try:
        file_format = detect_file_format(file_path)
        logger.debug(f"Detected file format: {file_format}")

        # Read new data with appropriate format handling
        if file_format == "windows":
            # Windows Excel format with ="value" encapsulation needs cleaning
            temp_file = clean_csv_format(file_path)
            new_df = pd.read_csv(temp_file, encoding="utf-8")
            logger.debug(f"Successfully read Windows format CSV, shape: {new_df.shape}")
        else:
            # Standard CSV format (already UTF-8 from import endpoint)
            new_df = pd.read_csv(file_path, encoding="utf-8")
            logger.debug(f"Successfully read standard CSV, shape: {new_df.shape}")
    except Exception as e:
        logger.error(f"Error reading CSV file: {str(e)}")
        logger.debug(traceback.format_exc())
        raise ValueError(f"Could not read CSV file: {str(e)}")

    logger.debug(f"Original columns: {new_df.columns.tolist()}")
    logger.debug(f"Sample data:\n{new_df.head(2)}")

    # Get the appropriate column mapping for this broker
    if broker_name not in COLUMN_MAPPINGS:
        raise ValueError(
            f"Unsupported broker: {broker_name}. Must be one of: {list(COLUMN_MAPPINGS.keys())}"
        )
    mapping = COLUMN_MAPPINGS[broker_name]

    # Standardize column names
    standardized_df = standardize_columns(new_df, mapping)
    logger.debug(f"Standardized columns: {standardized_df.columns.tolist()}")

    # Add broker_name and account_id columns
    standardized_df["broker_name"] = broker_name
    standardized_df["account_id"] = account_id

    # Process datetime columns
    datetime_columns = ["transaction_date", "open_period"]
    for col in datetime_columns:
        if col not in standardized_df.columns:
            logger.error(f"Missing required column: {col}")
            raise KeyError(
                f"Required column '{col}' not found in CSV file after standardization"
            )

    # Parse dates with multiple formats (prioritizes EU DD/MM/YYYY format)
    standardized_df = parse_dates_with_multiple_formats(
        standardized_df, datetime_columns
    )

    # Fix any dates that appear to be in the future (which might indicate a format issue)
    standardized_df = fix_future_dates(standardized_df, datetime_columns)

    # Sanitize dates to ISO format for SQLite compatibility
    standardized_df = sanitize_dates_for_sqlite(standardized_df, datetime_columns)

    # Convert numeric columns
    numeric_columns = ["amount", "pl", "balance", "opening", "closing"]
    for col in numeric_columns:
        if col in standardized_df.columns:
            standardized_df[col] = pd.to_numeric(standardized_df[col], errors="coerce")

    # Ensure text columns are strings
    text_columns = ["reference", "action", "description", "status", "currency"]
    for col in text_columns:
        if col in standardized_df.columns:
            standardized_df[col] = standardized_df[col].astype(str)

    # Initialize Fund_Balance, SL and TP columns with zeros as Decimal type
    standardized_df["Fund_Balance"] = pd.Series(
        0, index=standardized_df.index, dtype="float64"
    )
    standardized_df["sl"] = pd.Series(
        0.0, index=standardized_df.index, dtype="float64"
    )  # Stop Loss
    standardized_df["tp"] = pd.Series(
        0.0, index=standardized_df.index, dtype="float64"
    )  # Take Profit

    # Set Fund_Balance for fund receivable rows
    fund_receivable_mask = standardized_df["action"].str.contains(
        "Fund receivable", case=False, na=False
    )
    standardized_df.loc[fund_receivable_mask, "Fund_Balance"] = standardized_df.loc[
        fund_receivable_mask, "pl"
    ]

    # Map the standardized column names to the canonical database column names
    # This ensures consistency regardless of which broker mapping was used
    final_df = standardized_df.rename(columns=DB_COLUMN_NAMES)

    # Log the final columns for debugging
    logger.debug(f"Final columns after DB mapping: {final_df.columns.tolist()}")

    # Remove any columns that aren't in the database schema (except our added columns)
    expected_columns = list(DB_COLUMN_NAMES.values()) + [
        "broker_name",
        "account_id",
        "Fund_Balance",
        "sl",
        "tp",
    ]
    extra_columns = [col for col in final_df.columns if col not in expected_columns]
    if extra_columns:
        logger.debug(f"Dropping extra columns not in DB schema: {extra_columns}")
        final_df = final_df.drop(columns=extra_columns, errors="ignore")

    # Ensure account_id is present and is integer
    final_df["account_id"] = int(account_id)

    # Connect to database and check for existing records
    conn = sqlite3.connect(DATABASE_PATH)
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='broker_transactions'"
        )
        table_exists = cursor.fetchone() is not None

        if table_exists:
            cursor.execute("SELECT COUNT(*) FROM broker_transactions")
            existing_count = cursor.fetchone()[0]
            logger.info(f"Found {existing_count} existing records")

            if existing_count > 0:
                # Load existing data for comparison
                existing_df = pd.read_sql("SELECT * FROM broker_transactions", conn)

                # Create unique IDs for comparison with robust error handling
                try:
                    logger.debug("Creating unique IDs for existing records")
                    existing_df["unique_id"] = existing_df.apply(
                        lambda x: f"{x['broker_name']}_{get_unique_transaction_id(x)}",
                        axis=1,
                    )

                    logger.debug("Creating unique IDs for new records")
                    final_df["unique_id"] = final_df.apply(
                        lambda x: f"{x['broker_name']}_{get_unique_transaction_id(x)}",
                        axis=1,
                    )

                except Exception as e:
                    logger.error(f"Error creating unique IDs: {str(e)}")
                    logger.debug(f"Existing columns: {existing_df.columns.tolist()}")
                    logger.debug(f"Final columns: {final_df.columns.tolist()}")
                    logger.debug(traceback.format_exc())
                    raise

                # Find new records
                new_records = final_df[
                    ~final_df["unique_id"].isin(existing_df["unique_id"])
                ]
                logger.info(f"Found {len(new_records)} new records to import")

                if not new_records.empty:
                    new_records = new_records.drop("unique_id", axis=1)
                    new_records.to_sql(
                        "broker_transactions", conn, if_exists="append", index=False
                    )
                    logger.info(f"Successfully imported {len(new_records)} new records")
                else:
                    logger.info("No new records to import")
            else:
                # No existing records, create new table
                final_df.to_sql(
                    "broker_transactions", conn, if_exists="replace", index=False
                )
                logger.info(
                    f"Imported {len(final_df)} records as no existing data was found"
                )
        else:
            # Table doesn't exist, create it
            final_df.to_sql(
                "broker_transactions", conn, if_exists="replace", index=False
            )
            logger.info(f"Created new table and imported {len(final_df)} records")

    except Exception as e:
        logger.error(f"Error during database operation: {str(e)}")
        logger.debug(traceback.format_exc())
        raise
    finally:
        conn.close()

    # Verify the import by reading back from the database
    conn = sqlite3.connect(DATABASE_PATH)
    result_df = pd.read_sql("SELECT * FROM broker_transactions", conn)
    conn.close()

    logger.info("Import process completed successfully")
    return result_df
