import pandas as pd
import sqlite3
import logging

logger = logging.getLogger(__name__)

def import_transaction_data(file_path):
    # Read CSV with proper encoding
    df = pd.read_csv(file_path, encoding='utf-16le')
    
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