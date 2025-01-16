import pandas as pd
import sqlite3

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
    
    # Ensure text columns are properly handled
    text_columns = ['Ref. No.', 'Action', 'Description', 
                   'Status', 'Currency']
    for col in text_columns:
        df[col] = df[col].astype(str)
    
    # Save to SQLite
    conn = sqlite3.connect('trading.db')
    df.to_sql('transactions', conn, if_exists='replace', index=False)
    conn.close()

    return df    
