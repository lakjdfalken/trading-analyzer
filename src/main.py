import sys
from trade_gui import TradingAnalyzerGUI
import tkinter as tk

if __name__ == "__main__":
    # GUI mode
    root = tk.Tk()
    app = TradingAnalyzerGUI(root)
    root.mainloop()
