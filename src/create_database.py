import logging
import sqlite3

from db_path import DATABASE_PATH
from logger import setup_logger

logger = logging.getLogger(__name__)


def create_db_schema():
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    logger.info(f"Creating database at {DATABASE_PATH}")

    # Create accounts table with INTEGER account_id
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS accounts (
        account_id INTEGER PRIMARY KEY AUTOINCREMENT,
        account_name TEXT,
        broker_name TEXT,
        currency TEXT,
        initial_balance DECIMAL(10,2),
        notes TEXT,
        include_in_stats INTEGER DEFAULT 1
    )
    """)

    # Create broker_transactions table with INTEGER account_id and foreign key constraint
    cursor.execute("""
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
    """)

    # Create indexes for performance optimization
    # Index on Transaction Date - used in almost every WHERE/ORDER BY clause
    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_bt_transaction_date
    ON broker_transactions("Transaction Date")
    """)

    # Index on account_id - used for filtering by account
    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_bt_account_id
    ON broker_transactions(account_id)
    """)

    # Composite index on account_id and Transaction Date - used together frequently
    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_bt_account_date
    ON broker_transactions(account_id, "Transaction Date")
    """)

    # Index on Description - used for instrument filtering
    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_bt_description
    ON broker_transactions("Description")
    """)

    # Index on Action - used for filtering trades vs funding
    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_bt_action
    ON broker_transactions("Action")
    """)

    # Migrate existing databases: add include_in_stats column if missing
    cursor.execute("PRAGMA table_info(accounts)")
    columns = [col[1] for col in cursor.fetchall()]
    if "include_in_stats" not in columns:
        logger.info("Adding include_in_stats column to accounts table...")
        cursor.execute(
            "ALTER TABLE accounts ADD COLUMN include_in_stats INTEGER DEFAULT 1"
        )

    # Index on accounts include_in_stats for filtering
    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_accounts_include_stats
    ON accounts(include_in_stats)
    """)

    conn.commit()
    conn.close()


def create_indexes_if_missing():
    """Create indexes on existing database if they don't exist."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    # Check existing indexes
    cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
    existing_indexes = {row[0] for row in cursor.fetchall()}

    indexes_to_create = [
        ("idx_bt_transaction_date", 'broker_transactions("Transaction Date")'),
        ("idx_bt_account_id", "broker_transactions(account_id)"),
        ("idx_bt_account_date", 'broker_transactions(account_id, "Transaction Date")'),
        ("idx_bt_description", 'broker_transactions("Description")'),
        ("idx_bt_action", 'broker_transactions("Action")'),
        ("idx_accounts_include_stats", "accounts(include_in_stats)"),
    ]

    created = []
    for index_name, index_def in indexes_to_create:
        if index_name not in existing_indexes:
            try:
                cursor.execute(
                    f"CREATE INDEX IF NOT EXISTS {index_name} ON {index_def}"
                )
                created.append(index_name)
            except Exception as e:
                logger.warning(f"Could not create index {index_name}: {e}")

    if created:
        conn.commit()
        logger.info(f"Created indexes: {', '.join(created)}")

    conn.close()
    return created
