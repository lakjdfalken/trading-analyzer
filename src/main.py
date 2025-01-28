import sys
import logging
from PyQt6.QtWidgets import QApplication
from trade_gui import TradingAnalyzerGUI
from logger import setup_logger

def main():
    # Set up logging
    logging.getLogger().handlers.clear()
    logger = setup_logger()
    logger.info("Starting Trading Analyzer application")
    
    # Create Qt application
    app = QApplication(sys.argv)
    
    # Create main window
    window = TradingAnalyzerGUI()
    window.show()
    
    # Start event loop
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
