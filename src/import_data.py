import pandas as pd
import sqlite3
import logging
from file_handler import clean_csv_format, detect_file_format
from settings import COLUMN_MAPPINGS

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

def import_transaction_data(file_path, broker_name='default'):
    logger.debug(f"Attempting to import data from {file_path} for broker: {broker_name}")
    
    # Detect and handle file format
    file_format = detect_file_format(file_path)
    logger.debug(f"Detected file format: {file_format}")
    
    # Read new data with appropriate format handling
    if file_format == 'windows':
        temp_file = clean_csv_format(file_path)
        new_df = pd.read_csv(temp_file)
    elif file_format == 'mac':
        new_df = pd.read_csv(file_path, encoding='utf-16le')
    else:
        raise ValueError("Unsupported file format")

    # Print columns before modification
    logger.debug("Columns before: %s", new_df.columns.tolist())
    
    # Get column mapping for this broker (fallback to default if no specific mapping)
    mapping = COLUMN_MAPPINGS.get(broker_name, COLUMN_MAPPINGS['default'])
    
    # Standardize column names
    standardized_df = standardize_columns(new_df, mapping)
    logger.debug("Standardized columns: %s", standardized_df.columns.tolist())
    
    # Create broker_name column without using insert
    standardized_df = pd.concat([pd.Series(broker_name, index=standardized_df.index, name='broker_name'), standardized_df], axis=1)
    
    # Ensure the broker name is a string
    standardized_df['broker_name'] = standardized_df['broker_name'].astype(str)
    
    # Process datetime columns with error tracking
    datetime_columns = ['transaction_date', 'open_period']
    for col in datetime_columns:
        if col not in standardized_df.columns:
            logger.error(f"Missing required column: {col}")
            raise KeyError(f"Required column '{col}' not found in CSV file after standardization")
        
        try:
            standardized_df[col] = pd.to_datetime(standardized_df[col], format='%d/%m/%Y %H:%M:%S')
        except ValueError as e:
            # Find problematic rows
            for idx, value in standardized_df[col].items():
                try:
                    pd.to_datetime(value, format='%d/%m/%Y %H:%M:%S')
                except ValueError:
                    logger.error(f"Date parsing error in column {col}")
                    logger.error(f"Row index: {idx}")
                    logger.error(f"Problematic value: {value}")
                    logger.error(f"Full row data: {standardized_df.iloc[idx]}")
                    raise ValueError(f"Date parsing error in {col} at row {idx}: value '{value}'") from e
    
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
    fund_receivable_mask = standardized_df['action'].str.contains('Fund receivable', case=False, na=False)
    standardized_df.loc[fund_receivable_mask, 'Fund_Balance'] = standardized_df.loc[fund_receivable_mask, 'pl']
    
    # Map the standardized column names back to the original names for database compatibility
    # This ensures the database schema remains consistent
    reverse_mapping = {std_name: possible_names[0] for std_name, possible_names in mapping.items()}
    final_df = standardized_df.rename(columns=reverse_mapping)
    
    # Connect to database and check for existing records
    conn = sqlite3.connect('trading.db')
    try:
        existing_df = pd.read_sql('SELECT * FROM broker_transactions', conn)
        logger.info(f"Found {len(existing_df)} existing records")
        
        # Create unique IDs for comparison including broker name
        existing_df['unique_id'] = existing_df.apply(
            lambda x: f"{x['broker_name']}_{get_unique_transaction_id(x)}", axis=1)
        final_df['unique_id'] = final_df.apply(
            lambda x: f"{x['broker_name']}_{get_unique_transaction_id(x)}", axis=1)
        
        # Identify and add only new records
        new_records = final_df[~final_df['unique_id'].isin(existing_df['unique_id'])]
        logger.info(f"Found {len(new_records)} new records to import")
        
        if not new_records.empty:
            new_records = new_records.drop('unique_id', axis=1)
            new_records.to_sql('broker_transactions', conn, if_exists='append', index=False)
            logger.info(f"Successfully imported {len(new_records)} new records")
    except pd.io.sql.DatabaseError:
        logger.info("No existing database found, creating new one")
        final_df = final_df.drop('unique_id', axis=1) if 'unique_id' in final_df.columns else final_df
        final_df.to_sql('broker_transactions', conn, if_exists='replace', index=False)
    
    # Read final combined dataset
    result_df = pd.read_sql('SELECT * FROM broker_transactions', conn)
    conn.close()
    
    logger.info("Import process completed successfully")
    return result_df

def get_unique_transaction_id(row):
    # Adapt this function to work with both standardized and original column names
    if 'Transaction Date' in row:
        date_col = 'Transaction Date'
    else:
        date_col = 'transaction_date'
        
    if 'Ref. No.' in row:
        ref_col = 'Ref. No.'
    else:
        ref_col = 'reference'
        
    if 'Action' in row:
        action_col = 'Action'
    else:
        action_col = 'action'
        
    # Combine relevant fields to create a unique identifier
    return f"{row[date_col]}_{row[ref_col]}_{row[action_col]}"
