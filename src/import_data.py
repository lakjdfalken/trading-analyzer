import pandas as pd
import sqlite3
import logging
from file_handler import clean_csv_format, detect_file_format

logger = logging.getLogger(__name__)

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
    logger.debug("Columns before:", new_df.columns.tolist())
    
    # Create broker_name column without using insert
    new_df = pd.concat([pd.Series(broker_name, index=new_df.index, name='broker_name'), new_df], axis=1)
    
    # Print columns after modification
    logger.debug("Columns after:", new_df.columns.tolist())
    
    # Ensure the broker name is a string
    new_df['broker_name'] = new_df['broker_name'].astype(str)
    
    # Process datetime columns with error tracking
    datetime_columns = ['Transaction Date', 'Open Period']
    for col in datetime_columns:
        if col not in new_df.columns:
            logger.error(f"Missing required column: {col}")
            raise KeyError(f"Required column '{col}' not found in CSV file")
        
        try:
            new_df[col] = pd.to_datetime(new_df[col], format='%d/%m/%Y %H:%M:%S')
        except ValueError as e:
            # Find problematic rows
            for idx, value in new_df[col].items():
                try:
                    pd.to_datetime(value, format='%d/%m/%Y %H:%M:%S')
                except ValueError:
                    logger.error(f"Date parsing error in column {col}")
                    logger.error(f"Row index: {idx}")
                    logger.error(f"Problematic value: {value}")
                    logger.error(f"Full row data: {new_df.iloc[idx]}")
                    raise ValueError(f"Date parsing error in {col} at row {idx}: value '{value}'") from e
    
    # Convert numeric columns
    numeric_columns = ['Amount', 'P/L', 'Balance', 'Opening', 'Closing']
    for col in numeric_columns:
        new_df[col] = pd.to_numeric(new_df[col], errors='coerce')
    
    # Ensure text columns are strings
    text_columns = ['Ref. No.', 'Action', 'Description', 'Status', 'Currency']
    for col in text_columns:
        new_df[col] = new_df[col].astype(str)
    # Initialize Fund_Balance, SL and TP columns with zeros as Decimal type
    new_df['Fund_Balance'] = pd.Series(0, index=new_df.index, dtype='float64')
    new_df['sl'] = pd.Series(0.0, index=new_df.index, dtype='float64')  # Stop Loss
    new_df['tp'] = pd.Series(0.0, index=new_df.index, dtype='float64')  # Take Profit
    fund_receivable_mask = new_df['Action'].str.contains('Fund receivable', case=False, na=False)
    new_df.loc[fund_receivable_mask, 'Fund_Balance'] = new_df.loc[fund_receivable_mask, 'P/L']
    
    # Connect to database and check for existing records
    conn = sqlite3.connect('trading.db')
    try:
        existing_df = pd.read_sql('SELECT * FROM broker_transactions', conn)
        logger.info(f"Found {len(existing_df)} existing records")
        
        # Create unique IDs for comparison including broker name
        existing_df['unique_id'] = existing_df.apply(
            lambda x: f"{x['broker_name']}_{get_unique_transaction_id(x)}", axis=1)
        new_df['unique_id'] = new_df.apply(
            lambda x: f"{x['broker_name']}_{get_unique_transaction_id(x)}", axis=1)
        
        # Identify and add only new records
        new_records = new_df[~new_df['unique_id'].isin(existing_df['unique_id'])]
        logger.info(f"Found {len(new_records)} new records to import")
        
        if not new_records.empty:
            new_records = new_records.drop('unique_id', axis=1)
            new_records.to_sql('broker_transactions', conn, if_exists='append', index=False)
            logger.info(f"Successfully imported {len(new_records)} new records")
    except pd.io.sql.DatabaseError:
        logger.info("No existing database found, creating new one")
        new_df.to_sql('broker_transactions', conn, if_exists='replace', index=False)
    
    # Read final combined dataset
    final_df = pd.read_sql('SELECT * FROM broker_transactions', conn)
    conn.close()
    
    logger.info("Import process completed successfully")
    return final_df

def get_unique_transaction_id(row):
    # Combine relevant fields to create a unique identifier
    return f"{row['Transaction Date']}_{row['Ref. No.']}_{row['Action']}"
