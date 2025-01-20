import pandas as pd
import sqlite3
import logging

logger = logging.getLogger(__name__)

def clean_csv_format(file_path):
    with open(file_path, 'r', encoding='utf-16le') as file:
        content = file.read()
    
    # Remove the '=' signs and quotes
    content = content.replace('="', '')
    content = content.replace('"', '')
    
    # Replace multiple spaces with commas
    content = ','.join(content.split())
    
    # Write to a temporary file
    temp_file = file_path + '.tmp'
    with open(temp_file, 'w', encoding='utf-8') as file:
        file.write(content)
    
    return temp_file

def detect_file_format(file_path):
    """Detect if file is in Windows format (="Column") or Mac format (standard CSV)"""
    try:
        # Try reading first line with utf-16le (Windows format)
        with open(file_path, 'r', encoding='utf-16le') as file:
            first_line = file.readline()
            if '="' in first_line:
                return 'windows'
    except UnicodeError:
        pass
    
    # Try reading as standard CSV (Mac format)
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            first_line = file.readline()
            if ',' in first_line and '="' not in first_line:
                return 'mac'
    except UnicodeError:
        pass
    
    return 'unknown'

def import_transaction_data(file_path):
    logger.debug(f"Attempting to import data from {file_path}")
    # Read CSV with proper encoding
    df = pd.read_csv(file_path, encoding='utf-16le')

    logger.debug(f"Columns found in file: {df.columns.tolist()}")

    # Convert both date fields to datetime with consistent format
    datetime_columns = ['Transaction Date', 'Open Period']
    for col in datetime_columns:
        df[col] = pd.to_datetime(df[col], format='%d/%m/%Y %H:%M:%S')
    
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