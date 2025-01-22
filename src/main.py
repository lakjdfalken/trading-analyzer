import signal
import sys
import logging
import os
import matplotlib.pyplot as plt
import tkinter as tk
from trade_gui import TradingAnalyzerGUI

logger = logging.getLogger(__name__)

def signal_handler(signum, frame):
    """Handle CTRL-C signal"""
    logger.info("CTRL-C detected, initiating shutdown")
    try:
        # Close all matplotlib figures
        plt.close('all')
        
        # If root exists, destroy it
        if 'root' in globals():
            global root
            root.destroy()
            
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error during CTRL-C shutdown: {e}")
        os._exit(1)

def main():
    # Register CTRL-C handler
    signal.signal(signal.SIGINT, signal_handler)
    
    logger.info("Starting Trading Analyzer application")
    root = tk.Tk()
    app = TradingAnalyzerGUI(root)
    
    try:
        root.mainloop()
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt received")
        signal_handler(signal.SIGINT, None)

if __name__ == "__main__":
    main()
