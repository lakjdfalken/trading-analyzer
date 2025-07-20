import pandas as pd
import sqlite3
import logging
from import_data import import_transaction_data

logger = logging.getLogger(__name__)


class DataManager:
    def __init__(self):
        self.df = None
        self.db_connection = None

    def load_existing_data(self):
        """Load existing data from database"""
        try:
            self.db_connection = sqlite3.connect('trading.db')
            self.df = pd.read_sql_query("SELECT * FROM broker_transactions", self.db_connection)
            self.db_connection.close()
            self.db_connection = None
            
            if not self.df.empty:
                logger.info(f"Loaded {len(self.df)} existing records")
            else:
                logger.info("No existing data found")
                
        except Exception as e:
            logger.warning(f"No existing data loaded: {e}")
            if self.db_connection:
                self.db_connection.close()
                self.db_connection = None

    def import_data(self, file_path, broker_key):
        """Import data from CSV file"""
        try:
            self.df = import_transaction_data(file_path, broker_key)
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

    def get_filtered_data(self, broker_filter=None, start_date=None, end_date=None):
        """Get filtered data based on criteria"""
        if not self.has_data():
            return None
            
        filtered_df = self.df.copy()
        
        # Apply broker filter
        if broker_filter and broker_filter != 'All':
            filtered_df = filtered_df[filtered_df['broker_name'] == broker_filter]
        
        # Apply date filter
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