from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                           QComboBox, QPushButton, QLabel, QFrame, QTabWidget,
                           QTreeWidget, QTreeWidgetItem, QSlider, QLineEdit, QCheckBox,
                           QFileDialog, QMessageBox, QSizePolicy, QDialog)
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtGui import QAction, QKeySequence
import pandas as pd
import sqlite3, os
import logging
import platform
import shutil
from datetime import datetime, timedelta
from import_data import import_transaction_data
from visualize_data import create_visualization_figure
from settings import BROKERS, VALID_GRAPH_TYPES, WINDOW_CONFIG, UI_SETTINGS, DATA_COLUMNS
#from signals import TradeSignals
logger = logging.getLogger(__name__)


class TradingAnalyzerGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.cleanup_temp_graphs()  # Initial cleanup on startup
        self.setWindowTitle("Trading Data Analyzer")
        self.resize(WINDOW_CONFIG['default_width'], WINDOW_CONFIG['default_height'])
        self.webview = None # Store reference to webview for cleanup
    
        # Create the menu bar before other UI elements
        self.create_menu_bar()  # This line ensures menus are created
    
        # Initialize attributes
        self.broker_combo = QComboBox()
        self.current_sort_column = -1
        self.current_sort_order = Qt.SortOrder.AscendingOrder
        self.sort_states = {}  # Add this to track sort states per column    
        # Create central widget and main layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
    
        # Create and setup tabs
        self.data_tab = QWidget()
        self.graph_tab = QWidget()
        self.settings_tab = QWidget()
    
        self.tab_widget = QTabWidget()
        self.tab_widget.addTab(self.data_tab, "Data View")
        self.tab_widget.addTab(self.graph_tab, "Graphs")
        self.tab_widget.addTab(self.settings_tab, "Settings")
    
        # Setup UI components in correct order
        self.create_import_frame()
        self.main_layout.addWidget(self.tab_widget)
        self.setup_data_tab()
        self.setup_graph_tab()
        self.setup_settings_tab()
        self.load_existing_data()
    def create_import_frame(self):        
        import_frame = QFrame()
        import_layout = QHBoxLayout(import_frame)
        
        self.broker_combo.addItems(list(BROKERS.values()))
        self.broker_combo.setFixedWidth(UI_SETTINGS['broker_combo_width'])
        import_layout.addWidget(self.broker_combo)
        
        import_button = QPushButton("Import CSV")
        import_button.setFixedWidth(UI_SETTINGS['import_button_width'])
        import_button.clicked.connect(self.import_csv)
        import_layout.addWidget(import_button)
        
        self.main_layout.addWidget(import_frame)

    def filter_data(self):
        search_text = self.search_entry.text().lower()

    def setup_graph_tab(self):
        graph_layout = QHBoxLayout(self.graph_tab)

        # Add selection frame with fixed width
        selection_frame = QFrame()
        selection_frame.setFixedWidth(UI_SETTINGS['graph_selection_width'])
        selection_layout = QVBoxLayout(selection_frame)

        # Broker selection populated from settings
        self.graph_broker_combo = QComboBox()
        self.graph_broker_combo.addItems(['All'] + list(BROKERS.values()))
        selection_layout.addWidget(self.graph_broker_combo)

        # Date range selection
        selection_layout.addWidget(QLabel("Start Date:"))
        self.start_date = QLineEdit()
        selection_layout.addWidget(self.start_date)

        selection_layout.addWidget(QLabel("End Date:"))
        self.end_date = QLineEdit()
        selection_layout.addWidget(self.end_date)

        # Quick selection buttons
        quick_select_frame = QFrame()
        quick_select_layout = QHBoxLayout(quick_select_frame)

        seven_days_btn = QPushButton("7 Days")
        seven_days_btn.clicked.connect(lambda: self.set_date_range(7))
        quick_select_layout.addWidget(seven_days_btn)

        thirty_days_btn = QPushButton("30 Days")
        thirty_days_btn.clicked.connect(lambda: self.set_date_range(30))
        quick_select_layout.addWidget(thirty_days_btn)

        all_btn = QPushButton("All")
        all_btn.clicked.connect(self.reset_date_range)
        quick_select_layout.addWidget(all_btn)

        selection_layout.addWidget(quick_select_frame)

        # Graph type selection with controlled size
        selection_layout.addWidget(QLabel("Select Graph Type:"))
        self.graph_list = QTreeWidget()
        self.graph_list.setHeaderLabels(["Graph Types"])
        self.graph_list.setFixedWidth(UI_SETTINGS['graph_list_width'])  # Slightly smaller than frame
        self.graph_list.itemDoubleClicked.connect(self.on_graph_double_click)

        for graph_type in VALID_GRAPH_TYPES:
            item = QTreeWidgetItem([graph_type])
            self.graph_list.addTopLevelItem(item)

        selection_layout.addWidget(self.graph_list)

        display_button = QPushButton("Display Graph")
        display_button.clicked.connect(self.display_selected_graph)
        selection_layout.addWidget(display_button)

        graph_layout.addWidget(selection_frame)

        # Add graph display area that expands to fill space
        self.graph_display_frame = QFrame()
        self.graph_display_frame.setSizePolicy(
            QSizePolicy.Policy.Expanding, 
            QSizePolicy.Policy.Expanding
        )
        graph_layout.addWidget(self.graph_display_frame)

    def on_graph_double_click(self, item, column):
        """Handle double-click on graph type to display it immediately"""
        self.graph_list.setCurrentItem(item)  # Ensure the clicked item is selected
        self.display_selected_graph()  # Reuse existing display logic

    def set_date_range(self, days):
        if hasattr(self, 'df'):
            end_date = pd.Timestamp.now()
            start_date = end_date - pd.Timedelta(days=days)
            self.start_date.setText(start_date.strftime('%Y-%m-%d'))
            self.end_date.setText(end_date.strftime('%Y-%m-%d'))

    def reset_date_range(self):
        if hasattr(self, 'df'):
            self.start_date.clear()
            self.end_date.clear()

    def setup_settings_tab(self):
        settings_layout = QVBoxLayout(self.settings_tab)
    
        # Debug mode control
        debug_frame = QFrame()
        debug_layout = QHBoxLayout(debug_frame)
        debug_layout.addWidget(QLabel("Enable Debug Mode"))
        self.debug_checkbox = QCheckBox()
        self.debug_checkbox.setFixedWidth(30)
        self.debug_checkbox.stateChanged.connect(self.toggle_debug_mode)
        debug_layout.addWidget(self.debug_checkbox)
        debug_layout.addStretch()
        settings_layout.addWidget(debug_frame)
    
        # Theme selection
        theme_frame = QFrame()
        theme_layout = QHBoxLayout(theme_frame)
        theme_layout.addWidget(QLabel("Select Theme:"))
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(['Light', 'Dark'])
        self.theme_combo.setFixedWidth(100)
        self.theme_combo.currentTextChanged.connect(self.change_theme)
        theme_layout.addWidget(self.theme_combo)
        theme_layout.addStretch()
        settings_layout.addWidget(theme_frame)
    
        # Transparency control
        trans_frame = QFrame()
        trans_layout = QVBoxLayout(trans_frame)
        trans_layout.addWidget(QLabel("Window Transparency"))
        self.trans_slider = QSlider(Qt.Orientation.Horizontal)
        self.trans_slider.setRange(50, 100)
        self.trans_slider.setValue(100)
        self.trans_slider.setFixedWidth(200)
        self.trans_slider.valueChanged.connect(self.change_transparency)
        trans_layout.addWidget(self.trans_slider)
        settings_layout.addWidget(trans_frame)

        # About button in matching frame
        about_frame = QFrame()
        about_layout = QHBoxLayout(about_frame)
        about_layout.addWidget(QLabel("Application Info:"))
        about_button = QPushButton("About")
        about_button.setFixedWidth(100)
        about_button.clicked.connect(self.show_about)
        about_layout.addWidget(about_button)
        about_layout.addStretch()
        settings_layout.addWidget(about_frame)
    
        settings_layout.addStretch()

    def cleanup_temp_graphs(self):
        """Clean up graph files older than 24 hours"""
        temp_dir = os.path.join(os.getcwd(), 'temp_graphs')
        if os.path.exists(temp_dir):
            current_time = datetime.now()
            for filename in os.listdir(temp_dir):
                filepath = os.path.join(temp_dir, filename)
                file_modified = datetime.fromtimestamp(os.path.getmtime(filepath))
                if current_time - file_modified > timedelta(hours=24):
                    os.remove(filepath)
    
    def toggle_debug_mode(self, state):
        root_logger = logging.getLogger()
        if state == Qt.CheckState.Checked.value:
            root_logger.setLevel(logging.DEBUG)
            # Set all existing loggers to DEBUG
            for name in logging.root.manager.loggerDict:
                logger = logging.getLogger(name)
                logger.setLevel(logging.DEBUG)
            print("Debug mode enabled")
            logger.debug("Debug logging activated")
        else:
            root_logger.setLevel(logging.INFO)
            # Set all existing loggers to INFO
            for name in logging.root.manager.loggerDict:
                logger = logging.getLogger(name)
                logger.setLevel(logging.INFO)
            print("Debug mode disabled")

    def change_theme(self, theme):
        if theme == 'Dark':
            self.setStyleSheet("""
                QMainWindow, QWidget { background-color: #2b2b2b; color: #ffffff; }
                QTreeWidget { background-color: #363636; color: #ffffff; }
                QHeaderView::section { background-color: #404040; color: #ffffff; }
                QComboBox, QPushButton { background-color: #404040; color: #ffffff; }
            """)
        else:
            self.setStyleSheet("")

    def change_transparency(self, value):
        self.setWindowOpacity(value / 100)

    def load_existing_data(self):
        try:
            conn = sqlite3.connect('trading.db')
            self.df = pd.read_sql_query("SELECT * FROM broker_transactions", conn)
            conn.close()
            if not self.df.empty:
                self.update_display()
        except Exception as e:
            logger.warning(f"No existing data loaded: {e}")

    def import_csv(self):
        if self.broker_combo.currentText() == 'Select Broker':
            QMessageBox.warning(self, "Broker Selection", 
                              "Please select a broker before importing")
            return            
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select CSV File",
            "",
            "CSV Files (*.csv)"
        )
        
        if file_path:
            # Get broker key from selected value
            broker_key = [k for k, v in BROKERS.items() 
                         if v == self.broker_combo.currentText()][0]
            
            try:
                self.df = import_transaction_data(file_path, broker_key)
                self.update_display()
            except Exception as e:
                logger.error(f"Display update failed: {e}")
                QMessageBox.critical(self, "Error", 
                               f"Failed to import data: {str(e)}")
    def setup_data_tab(self):
        data_layout = QVBoxLayout(self.data_tab)
    
        # Create and configure tree widget
        self.tree = QTreeWidget()
        columns = ["broker_name", "Transaction Date", "Ref. No.", "Action", "Description", 
                  "Amount", "Open Period", "Opening", "Closing", "P/L", 
                  "Status", "Balance", "Currency", "Fund_Balance", "sl", "tp"]
        self.tree.setHeaderLabels(columns)
    
        # Enable sorting and visual indicators
        self.tree.setSortingEnabled(True)
        self.tree.header().setSectionsClickable(True)
        self.tree.header().setSortIndicatorShown(True)
        self.tree.header().sectionClicked.connect(self.sort_treeview)
    
        data_layout.addWidget(self.tree)

    def update_display(self):
        self.tree.clear()
        # Get column names from tree widget
        treeview_columns = DATA_COLUMNS
        
        for idx, row in self.df.iterrows():
            item = QTreeWidgetItem()
            for col, column_name in enumerate(treeview_columns):
                value = row[column_name]
                
                # Handle numeric fields with nan values
                if column_name in ["Amount", "Opening", "Closing", "P/L", "Balance", "Fund_Balance"]:
                    if pd.isna(value):
                        item.setText(col, "")  # Display empty string for nan
                        item.setData(col, Qt.ItemDataRole.UserRole, 0)
                    else:
                        try:
                            num_value = float(str(value).replace(',', ''))
                            item.setText(col, str(value))
                            item.setData(col, Qt.ItemDataRole.UserRole, num_value)
                        except:
                            item.setText(col, "0")
                            item.setData(col, Qt.ItemDataRole.UserRole, 0)
                else:
                    item.setText(col, str(value))
                    
            self.tree.addTopLevelItem(item)

        # Adjust column widths based on content
        for column in range(self.tree.columnCount()):
            self.tree.resizeColumnToContents(column)


    def display_selected_graph(self):
          try:
            self.cleanup_temp_graphs()  # Cleanup before generating new graph
            filtered_data = self.get_filtered_data()
            if filtered_data is None or filtered_data.empty:
                logger.warning("No data available after filtering")
                QMessageBox.warning(self, "Info", "No data available for selected date range")
                return
                    
            selection = self.graph_list.currentItem().text(0)
        
            # Create temp directory for HTML files
            temp_dir = os.path.join(os.getcwd(), 'temp_graphs')
            os.makedirs(temp_dir, exist_ok=True)

            # Clear any existing layout
            if self.graph_display_frame.layout():
                QWidget().setLayout(self.graph_display_frame.layout())
            
            # Create new layout
            layout = QVBoxLayout()
            self.graph_display_frame.setLayout(layout)
        
            # Create webview
            self.webview = QWebEngineView()
            layout.addWidget(self.webview)
        
            # Generate and display graph
            fig = create_visualization_figure(filtered_data, selection)
            temp_path = os.path.join(temp_dir, 'graph.html')
            fig.write_html(temp_path, include_plotlyjs=True, full_html=True)
            self.webview.load(QUrl.fromLocalFile(temp_path))
            
          except Exception as e:
            logger.error(f"Error displaying graph: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to create visualization: {str(e)}")
    def get_filtered_data(self):
        if not hasattr(self, 'df'):
            return None
            
        filtered_df = self.df.copy()
        
        # Apply broker filter if specific broker selected
        selected_broker = self.graph_broker_combo.currentText()
        if selected_broker != 'All':
            # Get broker key from selected value
            broker_key = [k for k, v in BROKERS.items() if v == selected_broker][0]
            filtered_df = filtered_df[filtered_df['broker_name'] == broker_key]
        
        # Validate and apply date range filter
        if not self.validate_date_range():
          return None

        start = self.start_date.text()
        end = self.end_date.text()
        
        if start and end:
            try:
                filtered_df['Transaction Date'] = pd.to_datetime(filtered_df['Transaction Date'])
                filtered_df = filtered_df[
                    (filtered_df['Transaction Date'].dt.date >= pd.to_datetime(start).date()) &
                    (filtered_df['Transaction Date'].dt.date <= pd.to_datetime(end).date())
                ]
            except ValueError:
                QMessageBox.critical(self, "Error", "Invalid date format. Use YYYY-MM-DD")
                return None
                
        return filtered_df

    def sort_treeview(self, column):
      # Initialize sort state for this column if needed
      if column not in self.sort_states:
          self.sort_states[column] = Qt.SortOrder.AscendingOrder
      
      # Toggle the sort state for this column
      self.sort_states[column] = (Qt.SortOrder.DescendingOrder 
          if self.sort_states[column] == Qt.SortOrder.AscendingOrder 
          else Qt.SortOrder.AscendingOrder)
      
      # Apply the sort
      self.tree.sortByColumn(column, self.sort_states[column])

    def closeEvent(self, event):
        """Handle proper cleanup when closing the application"""
        # Store reference to webview before clearing layout
        temp_dir = os.path.join(os.getcwd(), 'temp_graphs')
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)  # Remove entire temp directory on exit
        if hasattr(self, 'webview'):
            self.webview = None
        
        # Clear any existing layout
        if self.graph_display_frame.layout():
            while self.graph_display_frame.layout().count():
                item = self.graph_display_frame.layout().takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            QWidget().setLayout(self.graph_display_frame.layout())
        
        # Close database connections if any
        if hasattr(self, 'db_connection'):
            self.db_connection.close()
        
        event.accept()

    def create_menu_bar(self):
        menubar = self.menuBar()
        
        # Add Settings menu
        settings_menu = menubar.addMenu('Settings')
        preferences_action = QAction('Preferences...', self)
        # Use platform-independent shortcut
        # Replace the existing preferences shortcut with explicit platform-specific ones
        if platform.system() == 'Darwin':  # macOS
            preferences_action.setShortcut(QKeySequence("Cmd+,"))
        elif platform.system() == 'Windows':
            preferences_action.setShortcut(QKeySequence("Ctrl+P"))
        else:  # Linux and others
            preferences_action.setShortcut(QKeySequence("Ctrl+,"))

        preferences_action.triggered.connect(self.show_preferences)
        settings_menu.addAction(preferences_action)
        
        

    def show_preferences(self):
        dialog = QDialog(self)
        dialog.setWindowTitle('Preferences')
        layout = QVBoxLayout()

        # Theme settings
        theme_layout = QHBoxLayout()
        theme_layout.addWidget(QLabel("Theme:"))
        theme_combo = QComboBox()
        theme_combo.addItems(['Light', 'Dark'])
        theme_combo.currentTextChanged.connect(self.change_theme)
        theme_layout.addWidget(theme_combo)
        layout.addLayout(theme_layout)

        # Debug mode settings
        debug_layout = QHBoxLayout()
        debug_layout.addWidget(QLabel("Debug Mode:"))
        debug_checkbox = QCheckBox()
        debug_checkbox.setChecked(self.debug_checkbox.isChecked())
        debug_checkbox.stateChanged.connect(self.toggle_debug_mode)
        debug_layout.addWidget(debug_checkbox)
        layout.addLayout(debug_layout)

        # Transparency settings
        trans_layout = QVBoxLayout()
        trans_layout.addWidget(QLabel("Window Transparency"))
        trans_slider = QSlider(Qt.Orientation.Horizontal)
        trans_slider.setRange(
          UI_SETTINGS['transparency_slider']['min'],
          UI_SETTINGS['transparency_slider']['max']
        )
        trans_slider.setValue(UI_SETTINGS['transparency_slider']['default'])
        trans_slider.valueChanged.connect(self.change_transparency)
        trans_layout.addWidget(trans_slider)
        layout.addLayout(trans_layout)

        dialog.setLayout(layout)
        dialog.exec()

    def validate_date_range(self):
      """Validate date range inputs"""
      start = self.start_date.text()
      end = self.end_date.text()
      
      if not start or not end:
          return True  # Empty dates are valid (show all data)
          
      try:
          start_date = datetime.strptime(start, '%Y-%m-%d')
          end_date = datetime.strptime(end, '%Y-%m-%d')
          
          if start_date > end_date:
              QMessageBox.warning(self, "Invalid Date Range", 
                                "Start date must be before end date")
              return False
              
          if end_date > datetime.now():
              QMessageBox.warning(self, "Invalid Date Range", 
                                "End date cannot be in the future")
              return False
              
          return True
          
      except ValueError:
          QMessageBox.warning(self, "Invalid Date Format", 
                            "Please use YYYY-MM-DD format")
          return False

    def show_about(self):
        about_text = """
        Trading Analyzer
        Version 1.0
        
        A tool for analyzing trading data and generating insights.
        
        Features:
        - Trade data analysis
        - Performance metrics
        - Visual analytics
        - Custom reporting
        """
        QMessageBox.about(self, "About Trading Analyzer", about_text)
