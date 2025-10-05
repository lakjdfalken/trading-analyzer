import pandas as pd
import sqlite3
import logging
from import_data import import_transaction_data

logger = logging.getLogger(__name__)

class DataManager:
    def __init__(self):
        self.df = None
        self.accounts_df = None
        self.db_connection = None
            
    def load_existing_data(self):
        """Load existing data from database with account information"""
        try:
            from create_database import create_db_schema
            create_db_schema()

            self.db_connection = sqlite3.connect('trading.db')
            # Always load transactions with account info
            self.df = pd.read_sql_query("""
                SELECT t.*, a.account_name, a.broker_name as account_broker
                FROM broker_transactions t
                LEFT JOIN accounts a ON t.account_id = a.account_id
            """, self.db_connection)
            self.accounts_df = pd.read_sql_query("SELECT * FROM accounts", self.db_connection)

            self.db_connection.close()
            self.db_connection = None

            if not self.df.empty:
                logger.info(f"Loaded {len(self.df)} existing records")
                if not self.accounts_df.empty:
                    logger.info(f"Loaded {len(self.accounts_df)} accounts")
            else:
                logger.info("No existing data found")

        except Exception as e:
            logger.warning(f"No existing data loaded: {e}")
            if self.db_connection:
                self.db_connection.close()
                self.db_connection = None

    def import_data(self, file_path, broker_key, account_id=None):
        """Import data from CSV file"""
        try:
            # Ensure account_id is integer
            if account_id is not None:
                account_id = int(account_id)
            import_transaction_data(file_path, broker_key, account_id)
            # After import, reload data with account info
            self.load_existing_data()
            logger.info(f"Successfully imported {len(self.df)} records")
            return True
        except Exception as e:
            logger.error(f"Failed to import data: {e}")
            raise

    def get_data(self):
        """Get the current dataframe"""
        return self.df

    def has_data(self):
        """Check if data is available"""
        return self.df is not None and not self.df.empty

    def get_filtered_data(self, broker_filter=None, account_id=None, start_date=None, end_date=None):
        """Get filtered data based on criteria"""
        if not self.has_data():
            return None
            
        filtered_df = self.df.copy()

        if broker_filter and broker_filter != 'All':
            filtered_df = filtered_df[filtered_df['broker_name'] == broker_filter]

        if account_id and account_id != 'all':
            try:
                filtered_df = filtered_df[filtered_df['account_id'] == int(account_id)]
            except ValueError:
                logger.error(f"Invalid account_id for filtering: {account_id}")
                return None

        if start_date and end_date:
            try:
                filtered_df['Transaction Date'] = pd.to_datetime(filtered_df['Transaction Date'])
                filtered_df = filtered_df[
                    (filtered_df['Transaction Date'].dt.date >= pd.to_datetime(start_date).date()) &
                    (filtered_df['Transaction Date'].dt.date <= pd.to_datetime(end_date).date())
                ]
            except ValueError as e:
                logger.error(f"Date filtering error: {e}")
                return None
                
        return filtered_df

    def cleanup(self):
        """Clean up database connections"""
        try:
            if self.db_connection:
                self.db_connection.close()
                self.db_connection = None
        except Exception as e:
            logger.error(f"Error cleaning up database connections: {e}")
