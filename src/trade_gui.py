import tkinter as tk
import sqlite3
import pandas as pd
from tkinter import ttk, filedialog, messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from import_data import import_transaction_data
from visualize_data import create_visualization_figure
import logging
import os, sys

# Configure logging
logger = logging.getLogger(__name__)

class TradingAnalyzerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Trading Data Analyzer")
        self.root.geometry("1600x800")
    
        # Configure root grid
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
    
        # Create main container
        self.main_frame = ttk.Frame(self.root, padding="10")
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
    
        # Configure main frame grid
        self.main_frame.grid_rowconfigure(1, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)
    
        # Import button
        self.import_btn = ttk.Button(self.main_frame, text="Import CSV", 
                command=self.import_csv)
        self.import_btn.grid(row=0, column=0, pady=10, padx=5)
    
        # Create tabs for different views
        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.grid(row=1, column=0, sticky="nsew")
    
        # Configure notebook frames
        self.data_frame = ttk.Frame(self.notebook)
        self.data_frame.grid_rowconfigure(1, weight=1)
        self.data_frame.grid_columnconfigure(0, weight=1)

        self.graph_frame = ttk.Frame(self.notebook)
        self.graph_frame.grid_rowconfigure(0, weight=1)
        self.graph_frame.grid_columnconfigure(1, weight=1)
    
        self.notebook.add(self.data_frame, text="Data View")
        self.notebook.add(self.graph_frame, text="Graphs")
        
        # Create treeview for data display
        self.create_treeview()
        
        # Add graph selection components to graph frame
        self.create_graph_selector()

        # Load existing data if available
        self.load_existing_data()

        # Bind search entry to search function
        self.search_var.trace_add('write', lambda name, index, mode: self.search_treeview())

        # Bind window close event
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def on_closing(self):
        """Handle application shutdown cleanly"""
        logger.info("Shutting down application")
        try:
            # Clean up any open database connections
            if hasattr(self, 'db_connection'):
                self.db_connection.close()
            
            # Destroy all matplotlib figures
            plt.close('all')
            
            # Destroy the root window
            self.root.destroy()
            
            # Force exit the program
            sys.exit(0)
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
            # Ensure program exits even if cleanup fails
            os._exit(1)


    def create_search_frame(self):
        search_frame = ttk.Frame(self.data_frame)
        search_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
    
        ttk.Label(search_frame, text="Search:").pack(side=tk.LEFT, padx=5)
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
        self.search_entry.pack(side=tk.LEFT, padx=5)
    
        # Add search field dropdown
        self.search_column = ttk.Combobox(search_frame, values=self.tree["columns"])
        self.search_column.pack(side=tk.LEFT, padx=5)
        self.search_column.set("Description")  # Default search column

    def search_treeview(self, event=None):
        search_term = self.search_var.get().lower()
        search_column = self.search_column.get()
    
        # Clear tree
        for item in self.tree.get_children():
            self.tree.delete(item)
    
        # Repopulate with filtered data
        for idx, row in self.df.iterrows():
            if search_term in str(row[search_column]).lower():
                self.tree.insert("", "end", values=tuple(row))

    def reset_date_range(self):
        if hasattr(self, 'df'):
            self.start_date.delete(0, tk.END)
            self.end_date.delete(0, tk.END)

    def set_date_range(self, days):
        if hasattr(self, 'df'):
            end_date = pd.Timestamp.now()
            start_date = end_date - pd.Timedelta(days=days)
            self.start_date.delete(0, tk.END)
            self.end_date.delete(0, tk.END)
            self.start_date.insert(0, start_date.strftime('%Y-%m-%d'))
            self.end_date.insert(0, end_date.strftime('%Y-%m-%d'))

    def get_filtered_data(self):
        if not hasattr(self, 'df'):
            return None
            
        filtered_df = self.df.copy()
        
        start = self.start_date.get()
        end = self.end_date.get()
        
        if start and end:
            try:
                filtered_df['Transaction Date'] = pd.to_datetime(filtered_df['Transaction Date'])
                filtered_df = filtered_df[
                    (filtered_df['Transaction Date'].dt.date >= pd.to_datetime(start).date()) &
                    (filtered_df['Transaction Date'].dt.date <= pd.to_datetime(end).date())
                ]
            except ValueError:
                messagebox.showerror("Error", "Invalid date format. Use YYYY-MM-DD")
                return None
                
        return filtered_df
    def create_treeview(self):
        # First create the tree
        columns = ("Transaction Date", "Ref. No.", "Action", "Description", 
                  "Amount", "Open Period", "Opening", "Closing", "P/L", 
                  "Status", "Balance", "Currency", "Fund_Balance")
        self.tree = ttk.Treeview(self.data_frame, columns=columns, show="headings", height=20)
        
        # Set up column headings and widths
        for col in columns:
            self.tree.heading(col, text=col)
            if col in ["Transaction Date", "Action", "Open Period"]:
                self.tree.column(col, width=150)  # Wider for datetime
            elif col in ["Description"]:
                self.tree.column(col, width=200)  # Medium for numbers
            elif col in ["Amount", "Opening", "Closing", "P/L", "Balance"]:
                self.tree.column(col, width=100)  # Medium for numbers
            elif col in ["Status", "Currency"]:
                self.tree.column(col, width=50)  # Narrow for text
            else:
                self.tree.column(col, width=80)  # Default for text

        # Now create search frame since tree exists
        self.create_search_frame()
        
        # Finally set up layout
        self.tree.grid(row=1, column=0, sticky="nsew")
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(self.data_frame, orient="vertical", 
                                command=self.tree.yview)
        scrollbar.grid(row=1, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=scrollbar.set)

    def create_search_frame(self):
        search_frame = ttk.Frame(self.data_frame)
        search_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        
        ttk.Label(search_frame, text="Search:").pack(side=tk.LEFT, padx=5)
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
        self.search_entry.pack(side=tk.LEFT, padx=5)
        
        # Now we can safely access self.tree["columns"]
        self.search_column = ttk.Combobox(search_frame, values=self.tree["columns"])
        self.search_column.pack(side=tk.LEFT, padx=5)
        self.search_column.set("Description")

    def import_csv(self):
        file_path = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")])
        if file_path:
            self.df = import_transaction_data(file_path)
            try:
                self.update_display()
            except Exception as e:
                logger.error(f"Display update failed: {e}")

    def update_display(self):
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Add new data
        for idx, row in self.df.iterrows():
            self.tree.insert("", "end", values=tuple(row))

    def show_graphs(self):
        if hasattr(self, 'df'):
            graph_types = [
                'Balance History',
                'P/L Distribution',
                'Amount Distribution',
                'Status Distribution',
                'Market Actions',
                'Market P/L',
                'Daily P/L'
            ]
            
            # Create graph selection dialog
            dialog = tk.Toplevel(self.root)
            dialog.title("Select Graph Type")
            dialog.geometry("300x200")
            dialog.transient(self.root)  # Make dialog modal
            dialog.grab_set()  # Make dialog modal
            
            def on_select():
                if listbox.curselection():  # Check if selection exists
                    selection = listbox.get(listbox.curselection())
                    dialog.destroy()
                    create_visualization_figure(self.df, selection)
            
            listbox = tk.Listbox(dialog, selectmode=tk.SINGLE)
            for graph_type in graph_types:
                listbox.insert(tk.END, graph_type)
            listbox.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)
            
            # Double click binding
            listbox.bind('<Double-Button-1>', lambda e: on_select())
            
            select_btn = ttk.Button(dialog, text="Show Graph", command=on_select)
            select_btn.pack(pady=10)
            
            # Center the dialog
            dialog.update_idletasks()
            width = dialog.winfo_width()
            height = dialog.winfo_height()
            x = (dialog.winfo_screenwidth() // 2) - (width // 2)
            y = (dialog.winfo_screenheight() // 2) - (height // 2)
            dialog.geometry('{}x{}+{}+{}'.format(width, height, x, y))
            
        else:
            messagebox.showinfo("Info", "Please import data first")  

    def load_existing_data(self):
        try:
            conn = sqlite3.connect('trading.db')
            self.df = pd.read_sql_query("SELECT * FROM transactions", conn)
            conn.close()
            if not self.df.empty:
                self.update_display()
        except:
            pass
    def create_graph_selector(self):
        # Create selection frame in the graphs tab
        selection_frame = ttk.Frame(self.graph_frame)
        selection_frame.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)
    
        # Add date range selection
        date_frame = ttk.LabelFrame(selection_frame, text="Date Range")
        date_frame.pack(pady=10, fill=tk.X)
    
        # Start date
        ttk.Label(date_frame, text="Start Date:").pack(pady=2)
        self.start_date = ttk.Entry(date_frame)
        self.start_date.pack(pady=2)
    
        # End date
        ttk.Label(date_frame, text="End Date:").pack(pady=2)
        self.end_date = ttk.Entry(date_frame)
        self.end_date.pack(pady=2)
    
        # Quick selection buttons
        quick_select_frame = ttk.Frame(date_frame)
        quick_select_frame.pack(pady=5)
    
        ttk.Button(quick_select_frame, text="7 Days", 
               command=lambda: self.set_date_range(7)).pack(side=tk.LEFT, padx=2)
        ttk.Button(quick_select_frame, text="30 Days", 
               command=lambda: self.set_date_range(30)).pack(side=tk.LEFT, padx=2)
        ttk.Button(quick_select_frame, text="All", 
               command=self.reset_date_range).pack(side=tk.LEFT, padx=2)
    
        # Graph type selection
        ttk.Label(selection_frame, text="Select Graph Type:").pack(pady=5)
        self.graph_listbox = tk.Listbox(selection_frame, height=10)
        self.graph_listbox.pack(pady=5)
    
        # Use VALID_GRAPH_TYPES from settings
        from settings import VALID_GRAPH_TYPES
        for graph_type in VALID_GRAPH_TYPES:
            self.graph_listbox.insert(tk.END, graph_type)
    
        ttk.Button(selection_frame, text="Display Graph", 
               command=self.display_selected_graph).pack(pady=5)
    
        self.graph_display_frame = ttk.Frame(self.graph_frame)
        self.graph_display_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

    def show_graphs(self):
        if hasattr(self, 'df'):
            graph_types = [
                'Balance History',
                'Distribution Days',
                'Funding',
                'Funding Charges',
                'Long vs Short Positions',
                'Market Actions',
                'Market P/L',
                'Daily P/L'
            ]    

    def display_selected_graph(self):
        try:
            if not hasattr(self, 'df'):
                logger.warning("Attempted to display graph without data")
                messagebox.showinfo("Info", "Please import data first")
                return
                
            if not self.graph_listbox.curselection():
                logger.warning("No graph type selected")
                messagebox.showinfo("Info", "Please select a graph type")
                return
                
            filtered_data = self.get_filtered_data()
            if filtered_data is None or filtered_data.empty:
                logger.warning("No data available after filtering")
                messagebox.showinfo("Info", "No data available for selected date range")
                return
                
            selection = self.graph_listbox.get(self.graph_listbox.curselection())
            
            # Clear previous graph
            for widget in self.graph_display_frame.winfo_children():
                widget.destroy()
            
            fig = create_visualization_figure(filtered_data, selection)
            canvas = FigureCanvasTkAgg(fig, self.graph_display_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
            
        except Exception as e:
            logger.error(f"Error displaying graph: {str(e)}")
            messagebox.showerror("Error", f"Failed to create visualization: {str(e)}")

def reset_date_range(self):
    if hasattr(self, 'df'):
        self.start_date.delete(0, tk.END)
        self.end_date.delete(0, tk.END)

def set_date_range(self, days):
    if hasattr(self, 'df'):
        end_date = pd.Timestamp.now()
        start_date = end_date - pd.Timedelta(days=days)
        self.start_date.delete(0, tk.END)
        self.end_date.delete(0, tk.END)
        self.start_date.insert(0, start_date.strftime('%Y-%m-%d'))
        self.end_date.insert(0, end_date.strftime('%Y-%m-%d'))

def get_filtered_data(self):
    if not hasattr(self, 'df'):
        return None
        
    filtered_df = self.df.copy()
    
    start = self.start_date.get()
    end = self.end_date.get()
    
    if start and end:
        try:
            filtered_df['Transaction Date'] = pd.to_datetime(filtered_df['Transaction Date'])
            filtered_df = filtered_df[
                (filtered_df['Transaction Date'].dt.date >= pd.to_datetime(start).date()) &
                (filtered_df['Transaction Date'].dt.date <= pd.to_datetime(end).date())
            ]
        except ValueError:
            messagebox.showerror("Error", "Invalid date format. Use YYYY-MM-DD")
            return None
            
    return filtered_df