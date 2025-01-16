import sqlite3

def create_db_schema():
    conn = sqlite3.connect('trading.db')
    cursor = conn.cursor()
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS transactions (
        transaction_date DATETIME,
        ref_no TEXT,
        action TEXT,
        description TEXT,
        amount DECIMAL(10,2),
        open_period DATETIME,
        opening DECIMAL(10,5),
        closing DECIMAL(10,5),
        pl DECIMAL(10,2),
        status TEXT,
        balance DECIMAL(10,2),
        currency TEXT
    )
    ''')
    conn.close()