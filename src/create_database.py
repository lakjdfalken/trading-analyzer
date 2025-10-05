import sqlite3
import logging
from logger import setup_logger

logger = logging.getLogger(__name__)

def create_db_schema():
    conn = sqlite3.connect('trading.db')
    cursor = conn.cursor()

    logger.info("Creating database.")

    # Create accounts table with INTEGER account_id
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS accounts (
        account_id INTEGER PRIMARY KEY AUTOINCREMENT,
        account_name TEXT,
        broker_name TEXT,
        currency TEXT,
        initial_balance DECIMAL(10,2),
        notes TEXT
    )
    ''')

    # Create broker_transactions table with INTEGER account_id and foreign key constraint
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS broker_transactions (
        transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
        broker_name TEXT,
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
        currency TEXT,
        fund_balance DECIMAL(10,2),
        sl DECIMAL(10,2),
        tp DECIMAL(10,2),
        account_id INTEGER NOT NULL,
        FOREIGN KEY (account_id) REFERENCES accounts(account_id) ON DELETE CASCADE
    )
    ''')

    conn.commit()
    conn.close()