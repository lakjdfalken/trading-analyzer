import sys
from trade_gui import TradingAnalyzerGUI
import tkinter as tk
from logger import setup_logger

# Setup logger at application startup
logger = setup_logger()

def main():
    logger.info("Main Starting Trading Analyzer application")
    try:
        # Your existing code here
        logger.debug("Initializing components...")
        root = tk.Tk()
        app = TradingAnalyzerGUI(root)
        root.mainloop()
    except Exception as e:
        logger.error(f"Application error: {str(e)}", exc_info=True)

if __name__ == "__main__":
    main()
