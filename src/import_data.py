import pandas as pd
import sqlite3
import logging
from file_handler import clean_csv_format, detect_file_format

logger = logging.getLogger(__name__)

def import_transaction_data(file_path):
    logger.debug(f"Attempting to import data from {file_path}")
    
    file_format = detect_file_format(file_path)
    logger.debug(f"Detected file format: {file_format}")
    
    if file_format == 'windows':
        temp_file = clean_csv_format(file_path)
        df = pd.read_csv(temp_file)
    elif file_format == 'mac':
        df = pd.read_csv(file_path, encoding='utf-16le')
    else:
        raise ValueError("Unsupported file format")
    
    # Enhanced date parsing with error tracking
    datetime_columns = ['Transaction Date', 'Open Period']
    for col in datetime_columns:
        if col not in df.columns:
            logger.error(f"Missing required column: {col}")
            raise KeyError(f"Required column '{col}' not found in CSV file")
        
        try:
            df[col] = pd.to_datetime(df[col], format='%d/%m/%Y %H:%M:%S')
        except ValueError as e:
            # Find the problematic row
            for idx, value in df[col].items():
                try:
                    pd.to_datetime(value, format='%d/%m/%Y %H:%M:%S')
                except ValueError:
                    logger.error(f"Date parsing error in column {col}")
                    logger.error(f"Row index: {idx}")
                    logger.error(f"Problematic value: {value}")
                    logger.error(f"Full row data: {df.iloc[idx]}")
                    raise ValueError(f"Date parsing error in {col} at row {idx}: value '{value}'") from e
    
    # Convert numeric columns
    numeric_columns = ['Amount', 'P/L', 'Balance', 'Opening', 'Closing']
    for col in numeric_columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Ensure text columns are strings
    text_columns = ['Ref. No.', 'Action', 'Description', 'Status', 'Currency']
    for col in text_columns:
        df[col] = df[col].astype(str)    
    # Initialize Fund_Balance column with zeros as Decimal type
    df['Fund_Balance'] = pd.Series(0, index=df.index, dtype='float64')
    
    # Copy P/L values directly to Fund_Balance for Fund receivable entries
    fund_receivable_mask = df['Action'].str.contains('Fund receivable', case=False, na=False)
    df.loc[fund_receivable_mask, 'Fund_Balance'] = df.loc[fund_receivable_mask, 'P/L']
    
    # Save to SQLite including the Fund_Balance column with DECIMAL type
    conn = sqlite3.connect('trading.db')
    df.to_sql('transactions', conn, if_exists='replace', index=False, dtype={
        'Fund_Balance': 'DECIMAL(10,2)'
    })
    conn.close()
    logger.info("Market analysis completed")    
    return df