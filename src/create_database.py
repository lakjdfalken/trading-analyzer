import sqlite3
import logging

logger = logging.getLogger(__name__)

def create_db_schema():
    conn = sqlite3.connect('trading.db')
    cursor = conn.cursor()

    logger.info("Creating database.")

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS broker_transactions (
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
        tp DECIMAL(10,2)
    )
    ''')
    conn.close()