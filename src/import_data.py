import pandas as pd
import sqlite3
import logging
import os
import traceback
from datetime import datetime
from file_handler import clean_csv_format, detect_file_format
from settings import COLUMN_MAPPINGS
from logger import setup_logger

# Initialize logger
logger = logging.getLogger(__name__)

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
            logger.warning(f"No match found for required column '{std_name}'. Expected one of: {possible_names}")
    
    # Rename the columns
    standardized_df = standardized_df.rename(columns=column_map)
    
    return standardized_df

def get_unique_transaction_id(row):
    """
    Create a unique identifier for a transaction row.
    Works with both standardized and original column names.
    """
    # Find the appropriate date column
    date_col = None
    if 'Transaction Date' in row:
        date_col = 'Transaction Date'
    elif 'transaction_date' in row:
        date_col = 'transaction_date'
    else:
        # List available columns for debugging
        available_cols = list(row.keys()) if hasattr(row, 'keys') else list(row.index)
        logger.error(f"Cannot find date column. Available columns: {available_cols}")
        raise KeyError(f"Missing date column in transaction row")
        
    # Find the appropriate reference column
    ref_col = None
    if 'Ref. No.' in row:
        ref_col = 'Ref. No.'
    elif 'reference' in row:
        ref_col = 'reference'
    else:
        available_cols = list(row.keys()) if hasattr(row, 'keys') else list(row.index)
        logger.error(f"Cannot find reference column. Available columns: {available_cols}")
        raise KeyError(f"Missing reference column in transaction row")
        
    # Find the appropriate action column
    action_col = None
    if 'Action' in row:
        action_col = 'Action'
    elif 'action' in row:
        action_col = 'action'
    else:
        available_cols = list(row.keys()) if hasattr(row, 'keys') else list(row.index)
        logger.error(f"Cannot find action column. Available columns: {available_cols}")
        raise KeyError(f"Missing action column in transaction row")
    
    # Use string representation for date to avoid datetime comparison issues
    date_value = str(row[date_col])
    ref_value = str(row[ref_col])
    action_value = str(row[action_col])
    
    # Combine relevant fields to create a unique identifier
    return f"{date_value}_{ref_value}_{action_value}"

def fix_future_dates(df, date_columns=['transaction_date', 'open_period']):
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
                df[col] = pd.to_datetime(df[col], errors='coerce')
            
            # Check for future dates
            future_mask = df[col] > datetime.now()
            future_count = future_mask.sum()
            
            if future_count > 0:
                logger.warning(f"Found {future_count} dates in the future in column '{col}'")
                
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
                                fixed_date = date.replace(year=date.year - 1, month=date.day, day=date.month)
                                fixed_dates.iloc[i] = fixed_date
                                logger.debug(f"Fixed future date: {date} -> {fixed_date}")
                        except Exception as e:
                            logger.error(f"Failed to fix future date {date}: {str(e)}")
                
                # Apply fixed dates
                df.loc[future_mask, col] = fixed_dates
                
                # Check if we still have future dates
                still_future = (df[col] > datetime.now()).sum()
                if still_future > 0:
                    logger.warning(f"Still have {still_future} future dates after fixing")
                else:
                    logger.info(f"Successfully fixed all future dates in column '{col}'")
    
    return df

def parse_dates_with_multiple_formats(df, columns):
    """
    Try to parse date columns with multiple formats
    """
    date_formats = [
        '%d/%m/%Y %H:%M:%S',  # EU format with seconds
        '%m/%d/%Y %H:%M:%S',  # US format with seconds
        '%d/%m/%Y %H:%M',     # EU format without seconds
        '%m/%d/%Y %H:%M',     # US format without seconds
        '%Y-%m-%d %H:%M:%S',  # ISO format with seconds
        '%Y-%m-%d %H:%M'      # ISO format without seconds
    ]
    
    for col in columns:
        if col not in df.columns:
            logger.error(f"Missing column {col} for date parsing")
            continue
            
        # Try each format
        for date_format in date_formats:
            try:
                logger.debug(f"Trying to parse {col} with format {date_format}")
                df[col] = pd.to_datetime(df[col], format=date_format)
                logger.info(f"Successfully parsed {col} with format {date_format}")
                break
            except ValueError:
                continue
        else:
            # If none of the formats work, try the pandas default parser
            logger.warning(f"Could not parse {col} with specified formats, trying pandas default")
            df[col] = pd.to_datetime(df[col], errors='coerce')
            
            # Check for NaT values
            nat_count = df[col].isna().sum()
            if nat_count > 0:
                logger.warning(f"Found {nat_count} unparseable dates in column {col}")
                
    return df

def import_transaction_data(file_path, broker_name='default', account_id=None):
    """
    Import transaction data from a CSV file into the database.
    
    Args:
        file_path: Path to the CSV file
        broker_name: Name of the broker (default='default')
        account_id: Account ID for the transactions
        
    Returns:
        DataFrame with the imported data
    """
    logger.debug(f"Attempting to import data from {file_path} for broker: {broker_name}, with account_id: {account_id}")

    # Check if account_id is provided
    if account_id is None:
        raise ValueError("Account ID must be provided for importing transactions")

    # Detect and handle file format
    try:
        file_format = detect_file_format(file_path)
        logger.debug(f"Detected file format: {file_format}")

        # Read new data with appropriate format handling
        if file_format == 'windows':
            temp_file = clean_csv_format(file_path)
            new_df = pd.read_csv(temp_file)
            logger.debug(f"Successfully read Windows format CSV, shape: {new_df.shape}")
        elif file_format == 'mac':
            new_df = pd.read_csv(file_path, encoding='utf-16le')
            logger.debug(f"Successfully read Mac format CSV, shape: {new_df.shape}")
        else:
            # Try standard encoding as fallback
            try:
                logger.warning(f"Unsupported file format: {file_format}, trying standard CSV")
                new_df = pd.read_csv(file_path)
                logger.debug(f"Successfully read standard CSV, shape: {new_df.shape}")
            except Exception as e:
                logger.error(f"Error reading CSV with standard encoding: {str(e)}")
                # Try UTF-8 encoding
                try:
                    new_df = pd.read_csv(file_path, encoding='utf-8')
                    logger.debug(f"Successfully read UTF-8 CSV, shape: {new_df.shape}")
                except Exception as e2:
                    logger.error(f"Error reading CSV with UTF-8 encoding: {str(e2)}")
                    raise ValueError(f"Could not read file: {file_path}") from e2
    except Exception as e:
        logger.error(f"Error detecting file format: {str(e)}")
        logger.debug(traceback.format_exc())
        raise

    logger.debug(f"Original columns: {new_df.columns.tolist()}")
    logger.debug(f"Sample data:\n{new_df.head(2)}")

    # Get the appropriate column mapping for this broker
    mapping = COLUMN_MAPPINGS.get(broker_name, COLUMN_MAPPINGS['default'])

    # Standardize column names
    standardized_df = standardize_columns(new_df, mapping)
    logger.debug(f"Standardized columns: {standardized_df.columns.tolist()}")

    # Add broker_name and account_id columns
    standardized_df['broker_name'] = broker_name
    standardized_df['account_id'] = account_id

    # Process datetime columns
    datetime_columns = ['transaction_date', 'open_period']
    for col in datetime_columns:
        if col not in standardized_df.columns:
            logger.error(f"Missing required column: {col}")
            raise KeyError(f"Required column '{col}' not found in CSV file after standardization")
    
    # Parse dates with multiple formats
    standardized_df = parse_dates_with_multiple_formats(standardized_df, datetime_columns)
    
    # Fix any dates that appear to be in the future (which might indicate a format issue)
    standardized_df = fix_future_dates(standardized_df, datetime_columns)

    # Convert numeric columns
    numeric_columns = ['amount', 'pl', 'balance', 'opening', 'closing']
    for col in numeric_columns:
        if col in standardized_df.columns:
            standardized_df[col] = pd.to_numeric(standardized_df[col], errors='coerce')

    # Ensure text columns are strings
    text_columns = ['reference', 'action', 'description', 'status', 'currency']
    for col in text_columns:
        if col in standardized_df.columns:
            standardized_df[col] = standardized_df[col].astype(str)

    # Initialize Fund_Balance, SL and TP columns with zeros as Decimal type
    standardized_df['Fund_Balance'] = pd.Series(0, index=standardized_df.index, dtype='float64')
    standardized_df['sl'] = pd.Series(0.0, index=standardized_df.index, dtype='float64')  # Stop Loss
    standardized_df['tp'] = pd.Series(0.0, index=standardized_df.index, dtype='float64')  # Take Profit
    
    # Set Fund_Balance for fund receivable rows
    fund_receivable_mask = standardized_df['action'].str.contains('Fund receivable', case=False, na=False)
    standardized_df.loc[fund_receivable_mask, 'Fund_Balance'] = standardized_df.loc[fund_receivable_mask, 'pl']

    # Map the standardized column names back to the original names for database compatibility
    reverse_mapping = {std_name: possible_names[0] for std_name, possible_names in mapping.items()}
    final_df = standardized_df.rename(columns=reverse_mapping)

    # Ensure account_id is present and is integer
    final_df['account_id'] = int(account_id)

    # Connect to database and check for existing records
    conn = sqlite3.connect('trading.db')
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='broker_transactions'")
        table_exists = cursor.fetchone() is not None

        if table_exists:
            cursor.execute("SELECT COUNT(*) FROM broker_transactions")
            existing_count = cursor.fetchone()[0]
            logger.info(f"Found {existing_count} existing records")

            if existing_count > 0:
                # Load existing data for comparison
                existing_df = pd.read_sql('SELECT * FROM broker_transactions', conn)
                
                # Create unique IDs for comparison with robust error handling
                try:
                    logger.debug("Creating unique IDs for existing records")
                    existing_df['unique_id'] = existing_df.apply(
                        lambda x: f"{x['broker_name']}_{get_unique_transaction_id(x)}", axis=1)
                    
                    logger.debug("Creating unique IDs for new records")
                    final_df['unique_id'] = final_df.apply(
                        lambda x: f"{x['broker_name']}_{get_unique_transaction_id(x)}", axis=1)
                    
                except Exception as e:
                    logger.error(f"Error creating unique IDs: {str(e)}")
                    logger.debug(f"Existing columns: {existing_df.columns.tolist()}")
                    logger.debug(f"Final columns: {final_df.columns.tolist()}")
                    logger.debug(traceback.format_exc())
                    raise
                
                # Find new records
                new_records = final_df[~final_df['unique_id'].isin(existing_df['unique_id'])]
                logger.info(f"Found {len(new_records)} new records to import")
                
                if not new_records.empty:
                    new_records = new_records.drop('unique_id', axis=1)
                    new_records.to_sql('broker_transactions', conn, if_exists='append', index=False)
                    logger.info(f"Successfully imported {len(new_records)} new records")
                else:
                    logger.info("No new records to import")
            else:
                # No existing records, create new table
                final_df.to_sql('broker_transactions', conn, if_exists='replace', index=False)
                logger.info(f"Imported {len(final_df)} records as no existing data was found")
        else:
            # Table doesn't exist, create it
            final_df.to_sql('broker_transactions', conn, if_exists='replace', index=False)
            logger.info(f"Created new table and imported {len(final_df)} records")

    except Exception as e:
        logger.error(f"Error during database operation: {str(e)}")
        logger.debug(traceback.format_exc())
        raise
    finally:
        conn.close()

    # Verify the import by reading back from the database
    conn = sqlite3.connect('trading.db')
    result_df = pd.read_sql('SELECT * FROM broker_transactions', conn)
    conn.close()

    logger.info("Import process completed successfully")
    return result_df