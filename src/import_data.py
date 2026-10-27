import csv
import logging
import math
import os
import sqlite3
import traceback
from datetime import datetime, timezone

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

NUMERIC_COLUMNS = ["amount", "pl", "balance", "opening", "closing"]
TEXT_COLUMNS = ["reference", "action", "description", "status", "currency"]
DATETIME_COLUMNS = ["transaction_date", "open_period"]

# Cell values treated as missing (the same defaults the importer has always used)
NA_VALUES = {
    "",
    "#N/A",
    "#N/A N/A",
    "#NA",
    "-1.#IND",
    "-1.#QNAN",
    "-NaN",
    "-nan",
    "1.#IND",
    "1.#QNAN",
    "<NA>",
    "N/A",
    "NA",
    "NULL",
    "NaN",
    "None",
    "n/a",
    "nan",
    "null",
}

# SQLite column types used when the table has to be (re)created
COLUMN_TYPES = {
    "Amount": "REAL",
    "P/L": "REAL",
    "Balance": "REAL",
    "Opening": "REAL",
    "Closing": "REAL",
    "account_id": "INTEGER",
    "Fund_Balance": "REAL",
    "sl": "REAL",
    "tp": "REAL",
}


def detect_delimiter(file_path, encoding="utf-8-sig"):
    """
    Detect the delimiter used in a CSV file.

    Args:
        file_path: Path to the CSV file
        encoding: File encoding to use

    Returns:
        Detected delimiter character (comma, semicolon, or tab)
    """
    try:
        with open(file_path, "r", encoding=encoding) as f:
            # Read first few lines for detection
            sample = f.read(8192)

        # Use csv.Sniffer to detect delimiter
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
            logger.debug(f"Detected delimiter: {repr(dialect.delimiter)}")
            return dialect.delimiter
        except csv.Error:
            # Sniffer failed, try manual detection
            pass

        # Manual detection: count occurrences in first line
        first_line = sample.split("\n")[0] if "\n" in sample else sample

        delimiters = {
            ",": first_line.count(","),
            ";": first_line.count(";"),
            "\t": first_line.count("\t"),
            "|": first_line.count("|"),
        }

        # Pick the delimiter with most occurrences
        best_delimiter = max(delimiters, key=delimiters.get)

        # Only use if we found at least a few occurrences
        if delimiters[best_delimiter] >= 2:
            logger.debug(
                f"Manually detected delimiter: {repr(best_delimiter)} (count: {delimiters[best_delimiter]})"
            )
            return best_delimiter

        # Default to comma
        logger.debug("Could not detect delimiter, defaulting to comma")
        return ","

    except Exception as e:
        logger.warning(f"Error detecting delimiter: {e}, defaulting to comma")
        return ","


def read_csv_rows(file_path, delimiter):
    """
    Read a CSV file into a header list and a list of row dicts.

    Blank lines are skipped, missing cells become None, and duplicate header
    names are made unique by suffixing ".1", ".2", ...

    Returns:
        Tuple of (columns, rows)
    """
    with open(file_path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f, delimiter=delimiter)
        header = next(reader, None)
        if header is None:
            raise ValueError("CSV file is empty")

        columns = []
        seen = {}
        for name in header:
            if name in seen:
                seen[name] += 1
                name = f"{name}.{seen[name]}"
            seen.setdefault(name, 0)
            columns.append(name)

        rows = []
        for line_number, values in enumerate(reader, start=2):
            if not values or (len(values) == 1 and not values[0].strip()):
                continue
            if len(values) > len(columns):
                raise ValueError(
                    f"Line {line_number} has {len(values)} fields, expected {len(columns)}"
                )
            values = values + [""] * (len(columns) - len(values))
            rows.append(
                {
                    col: (None if value in NA_VALUES else value)
                    for col, value in zip(columns, values)
                }
            )

    return columns, rows


def standardize_columns(columns, mapping):
    """
    Standardize column names using the mapping configuration.

    Args:
        columns: Original broker-specific column names
        mapping: Dictionary mapping standardized names to possible broker column names

    Returns:
        Dictionary mapping each original column name to its standardized name
        (columns without a match keep their cleaned name)
    """
    # Clean column names: strip whitespace and remove invisible characters
    cleaned_columns = {}
    for col in columns:
        # Strip whitespace, BOM, and other invisible characters
        cleaned = col.strip().strip("﻿").strip("​").strip()
        cleaned_columns[col] = cleaned
        if col != cleaned:
            logger.debug(f"Cleaned column name: '{repr(col)}' -> '{cleaned}'")
    cleaned_names = list(cleaned_columns.values())

    logger.debug(f"Columns after cleaning: {cleaned_names}")

    # Build a lowercase lookup for case-insensitive matching
    column_lower_map = {col.lower(): col for col in cleaned_names}
    logger.debug(f"Lowercase column map: {column_lower_map}")

    # Create a mapping from actual column names to standardized names
    column_map = {}
    for std_name, possible_names in mapping.items():
        for possible_name in possible_names:
            # Try exact match first
            if possible_name in cleaned_names:
                column_map[possible_name] = std_name
                break
            # Try case-insensitive match
            possible_lower = possible_name.lower()
            if possible_lower in column_lower_map:
                actual_col = column_lower_map[possible_lower]
                column_map[actual_col] = std_name
                logger.debug(f"Case-insensitive match: '{actual_col}' -> '{std_name}'")
                break

    # Log any missing required columns
    for std_name, possible_names in mapping.items():
        found = False
        for possible_name in possible_names:
            if possible_name in cleaned_names:
                found = True
                break
            if possible_name.lower() in column_lower_map:
                found = True
                break
        if not found:
            logger.warning(
                f"No match found for required column '{std_name}'. Expected one of: {possible_names}. "
                f"Available columns: {cleaned_names}"
            )

    return {
        col: column_map.get(cleaned, cleaned) for col, cleaned in cleaned_columns.items()
    }


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
        logger.error(f"Cannot find date column. Available columns: {list(row.keys())}")
        raise KeyError(f"Missing date column in transaction row")

    # Find the appropriate reference column - expanded list of candidates
    ref_col = None
    ref_candidates = [
        "Serial / Ref. No.",
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
        logger.error(f"Cannot find action column. Available columns: {list(row.keys())}")
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


def fix_future_dates(rows, date_columns=DATETIME_COLUMNS):
    """
    Fix dates that appear to be in the future

    This function checks if dates are unreasonably far in the future and
    corrects them by swapping day and month if they appear to be in MM/DD format
    instead of DD/MM format.
    """
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    current_year = now.year

    for col in date_columns:
        future_rows = [row for row in rows if row.get(col) and row[col] > now]

        if future_rows:
            logger.warning(
                f"Found {len(future_rows)} dates in the future in column '{col}'"
            )

            # Sample of future dates for debugging
            sample = [row[col] for row in future_rows[:5]]
            logger.debug(f"Sample future dates: {sample}")

            # Try to fix future dates by swapping day/month
            for row in future_rows:
                date = row[col]
                if date.year > current_year:
                    # Try to swap day and month
                    try:
                        # Create a new date with swapped day/month
                        if date.day <= 12:  # Only swap if day can be a valid month
                            fixed_date = date.replace(
                                year=date.year - 1, month=date.day, day=date.month
                            )
                            row[col] = fixed_date
                            logger.debug(f"Fixed future date: {date} -> {fixed_date}")
                    except Exception as e:
                        logger.error(f"Failed to fix future date {date}: {str(e)}")

            # Check if we still have future dates
            still_future = sum(1 for row in future_rows if row[col] > now)
            if still_future > 0:
                logger.warning(f"Still have {still_future} future dates after fixing")
            else:
                logger.info(f"Successfully fixed all future dates in column '{col}'")

    return rows


def parse_dates_with_multiple_formats(rows, columns):
    """
    Try to parse date columns with multiple formats.
    Prioritizes EU format (DD/MM/YYYY) which is common in broker exports.

    A format is only used for a column if it parses every value in it.
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
    # Day-first formats tried per value when no single format fits a column
    fallback_formats = [
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y %H:%M",
        "%d/%m/%Y",
        "%d-%m-%Y %H:%M:%S",
        "%d-%m-%Y %H:%M",
        "%d-%m-%Y",
        "%d.%m.%Y %H:%M:%S",
        "%d.%m.%Y %H:%M",
        "%d.%m.%Y",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
        "%Y/%m/%d %H:%M:%S",
        "%Y/%m/%d",
        "%m/%d/%Y %H:%M:%S",
        "%m/%d/%Y %H:%M",
        "%m/%d/%Y",
    ]

    def parse_value(value, formats):
        for date_format in formats:
            try:
                return datetime.strptime(value.strip(), date_format)
            except ValueError:
                continue
        return None

    for col in columns:
        values = [row.get(col) for row in rows]

        parsed = False

        # Try each format
        for date_format in date_formats:
            logger.debug(f"Trying to parse {col} with format {date_format}")
            try:
                parsed_dates = [
                    datetime.strptime(v, date_format) if v is not None else None
                    for v in values
                ]
            except ValueError as e:
                logger.debug(f"Format {date_format} failed for {col}: {e}")
                continue
            for row, parsed_date in zip(rows, parsed_dates):
                row[col] = parsed_date
            logger.info(f"Successfully parsed {col} with format {date_format}")
            parsed = True
            break

        if not parsed:
            # If none of the formats work, parse each value on its own (day first)
            logger.warning(
                f"Could not parse {col} with specified formats, trying each value day-first"
            )
            for row, value in zip(rows, values):
                row[col] = parse_value(value, fallback_formats) if value else None

            # Check for unparseable values
            nat_count = sum(1 for row in rows if row[col] is None)
            if nat_count > 0:
                logger.warning(f"Found {nat_count} unparseable dates in column {col}")

    return rows


def sanitize_dates_for_sqlite(rows, columns):
    """
    Convert datetime columns to ISO format strings for SQLite compatibility.
    SQLite expects dates in 'YYYY-MM-DD HH:MM:SS' format.
    """
    for col in columns:
        for row in rows:
            value = row.get(col)
            row[col] = value.strftime("%Y-%m-%d %H:%M:%S") if value else None
        logger.debug(f"Converted {col} to ISO format for SQLite")

    return rows


def to_number(value):
    """Convert a cell to float, returning None for missing or non-numeric values."""
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(number) else number


def normalize_text_column(rows, col):
    """
    Convert a text column to strings, leaving missing values as None (NULL).

    Columns that hold only whole numbers (e.g. reference numbers) are
    normalized to their integer form, so "00123" and " 123" both become "123".
    """
    values = [row.get(col) for row in rows]
    present = [v for v in values if v is not None]

    def as_int(value):
        try:
            return str(int(value.strip()))
        except ValueError:
            return None

    if present and all(as_int(v) is not None for v in present):
        convert = as_int
    else:
        convert = str

    for row, value in zip(rows, values):
        row[col] = convert(value) if value is not None else None


def import_transaction_data(file_path, broker_name="trade_nation", account_id=None):
    """
    Import transaction data from a CSV file into the database.

    Args:
        file_path: Path to the CSV file
        broker_name: Name of the broker (trade_nation or td365)
        account_id: Account ID for the transactions

    Returns:
        Total number of rows in broker_transactions after the import
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
            delimiter = detect_delimiter(temp_file)
            columns, rows = read_csv_rows(temp_file, delimiter)
            logger.debug(
                f"Successfully read Windows format CSV with delimiter {repr(delimiter)}, rows: {len(rows)}"
            )
        else:
            # Standard CSV format (already UTF-8 from import endpoint)
            # Detect delimiter (could be comma, semicolon, or tab)
            delimiter = detect_delimiter(file_path)
            columns, rows = read_csv_rows(file_path, delimiter)
            logger.debug(
                f"Successfully read standard CSV with delimiter {repr(delimiter)}, rows: {len(rows)}"
            )
    except Exception as e:
        logger.error(f"Error reading CSV file: {str(e)}")
        logger.debug(traceback.format_exc())
        raise ValueError(f"Could not read CSV file: {str(e)}")

    logger.debug(f"Original columns: {columns}")
    logger.debug(f"Sample data: {rows[:2]}")

    # Get the appropriate column mapping for this broker
    if broker_name not in COLUMN_MAPPINGS:
        raise ValueError(
            f"Unsupported broker: {broker_name}. Must be one of: {list(COLUMN_MAPPINGS.keys())}"
        )
    mapping = COLUMN_MAPPINGS[broker_name]

    # Standardize column names, keeping only columns that exist in the DB schema
    column_map = standardize_columns(columns, mapping)
    std_columns = [
        std for std in dict.fromkeys(column_map.values()) if std in DB_COLUMN_NAMES
    ]
    logger.debug(f"Standardized columns: {list(column_map.values())}")
    rows = [
        {column_map[col]: value for col, value in row.items() if column_map[col] in DB_COLUMN_NAMES}
        for row in rows
    ]

    # Process datetime columns
    for col in DATETIME_COLUMNS:
        if col not in std_columns:
            logger.error(f"Missing required column: {col}")
            raise KeyError(
                f"Required column '{col}' not found in CSV file after standardization"
            )

    # Parse dates with multiple formats (prioritizes EU DD/MM/YYYY format)
    rows = parse_dates_with_multiple_formats(rows, DATETIME_COLUMNS)

    # Fix any dates that appear to be in the future (which might indicate a format issue)
    rows = fix_future_dates(rows, DATETIME_COLUMNS)

    # Sanitize dates to ISO format for SQLite compatibility
    rows = sanitize_dates_for_sqlite(rows, DATETIME_COLUMNS)

    # Convert numeric columns
    for col in NUMERIC_COLUMNS:
        if col in std_columns:
            for row in rows:
                row[col] = to_number(row[col])

    # Ensure text columns are strings
    for col in TEXT_COLUMNS:
        if col in std_columns:
            normalize_text_column(rows, col)

    # Map the standardized column names to the canonical database column names
    # This ensures consistency regardless of which broker mapping was used
    db_columns = [DB_COLUMN_NAMES[col] for col in std_columns] + [
        "broker_name",
        "account_id",
        "Fund_Balance",
        "sl",
        "tp",
    ]
    logger.debug(f"Final columns after DB mapping: {db_columns}")

    final_rows = []
    for row in rows:
        final_row = {DB_COLUMN_NAMES[col]: row[col] for col in std_columns}
        final_row["broker_name"] = broker_name
        final_row["account_id"] = int(account_id)
        # Initialize Fund_Balance, SL and TP with zeros; fund receivable rows
        # carry their P/L as the fund balance
        action = final_row.get("Action")
        if action and "fund receivable" in action.lower():
            final_row["Fund_Balance"] = final_row.get("P/L")
        else:
            final_row["Fund_Balance"] = 0.0
        final_row["sl"] = 0.0  # Stop Loss
        final_row["tp"] = 0.0  # Take Profit
        final_rows.append(final_row)

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
                conn.row_factory = sqlite3.Row
                existing_rows = conn.execute(
                    "SELECT * FROM broker_transactions"
                ).fetchall()
                conn.row_factory = None

                # Create unique IDs for comparison with robust error handling
                try:
                    logger.debug("Creating unique IDs for existing records")
                    existing_ids = {
                        f"{row['broker_name']}_{get_unique_transaction_id(dict(row))}"
                        for row in existing_rows
                    }

                    logger.debug("Creating unique IDs for new records")
                    new_records = [
                        row
                        for row in final_rows
                        if f"{row['broker_name']}_{get_unique_transaction_id(row)}"
                        not in existing_ids
                    ]

                except Exception as e:
                    logger.error(f"Error creating unique IDs: {str(e)}")
                    logger.debug(f"Final columns: {db_columns}")
                    logger.debug(traceback.format_exc())
                    raise

                # Find new records
                logger.info(f"Found {len(new_records)} new records to import")

                if new_records:
                    _insert_rows(conn, db_columns, new_records)
                    logger.info(f"Successfully imported {len(new_records)} new records")
                else:
                    logger.info("No new records to import")
            else:
                # No existing records, create new table
                _replace_table(conn, db_columns, final_rows)
                logger.info(
                    f"Imported {len(final_rows)} records as no existing data was found"
                )
        else:
            # Table doesn't exist, create it
            _replace_table(conn, db_columns, final_rows)
            logger.info(f"Created new table and imported {len(final_rows)} records")

        conn.commit()

    except Exception as e:
        logger.error(f"Error during database operation: {str(e)}")
        logger.debug(traceback.format_exc())
        raise
    finally:
        conn.close()

    # Verify the import by reading back from the database
    conn = sqlite3.connect(DATABASE_PATH)
    total_rows = conn.execute("SELECT COUNT(*) FROM broker_transactions").fetchone()[0]
    conn.close()

    logger.info("Import process completed successfully")
    return total_rows


def _quote(name):
    return '"' + name.replace('"', '""') + '"'


def _insert_rows(conn, columns, rows):
    """Append rows (dicts keyed by DB column name) to broker_transactions."""
    sql = (
        f"INSERT INTO broker_transactions ({', '.join(_quote(c) for c in columns)}) "
        f"VALUES ({', '.join('?' for _ in columns)})"
    )
    conn.executemany(sql, [[row.get(c) for c in columns] for row in rows])


def _replace_table(conn, columns, rows):
    """Drop and recreate broker_transactions with the given columns, then insert rows."""
    column_defs = ", ".join(
        f"{_quote(c)} {COLUMN_TYPES.get(c, 'TEXT')}" for c in columns
    )
    conn.execute("DROP TABLE IF EXISTS broker_transactions")
    conn.execute(f"CREATE TABLE broker_transactions ({column_defs})")
    _insert_rows(conn, columns, rows)
