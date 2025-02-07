import sys
from PyQt6.QtWidgets import QApplication
from trade_gui import TradingAnalyzerGUI

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
#    logging.getLogger().handlers.clear()
    root_logger.info("Starting Trading Analyzer application")
    
    # Create Qt application
    app = QApplication(sys.argv)
    
    # Create main window
    window = TradingAnalyzerGUI()
    window.show()
    
    # Start event loop
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
