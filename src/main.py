import sys
from PyQt6.QtWidgets import QApplication
from gui.main_window import TradingAnalyzerGUI
from create_database import create_db_schema  # Import the function to create the database schema


import logging

# Create console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)

# Create formatter
formatter = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)

# Add handler to root logger
root_logger = logging.getLogger()
root_logger.addHandler(console_handler)
root_logger.setLevel(logging.INFO)  # Default level

def main():
    root_logger.info("Starting Trading Analyzer application")
    
    #  Create the database schema if it doesn't exist
    try:
        create_db_schema()  # Call the function to create the database schema
        root_logger.info("Database schema created successfully")
    except Exception as e:
        root_logger.error(f"Failed to create database schema: {e}")
        return
    # Create Qt application
    app = QApplication(sys.argv)
    
    # Create main window
    window = TradingAnalyzerGUI()
    window.show()
    
    # Start event loop
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
