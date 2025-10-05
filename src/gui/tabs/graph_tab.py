from PyQt6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QFrame, QLabel,
                           QComboBox, QPushButton, QLineEdit, QTreeWidget, 
                           QTreeWidgetItem, QSizePolicy, QMessageBox)
from PyQt6.QtCore import Qt
import pandas as pd
import logging
import sqlite3
from datetime import datetime
from settings import BROKERS, VALID_GRAPH_TYPES, UI_SETTINGS
from visualize_data import create_visualization_figure

logger = logging.getLogger(__name__)

class GraphTab(QWidget):
    def __init__(self, data_manager, visualization_manager, settings_manager):
        super().__init__()
        self.data_manager = data_manager
        self.visualization_manager = visualization_manager
        self.settings_manager = settings_manager
        self.setup_ui()
        self.load_accounts()  # Ensure accounts are loaded after UI setup

    def setup_ui(self):
        """Setup the graph tab UI"""
        layout = QHBoxLayout(self)

        # Create selection frame
        self.create_selection_frame(layout)
        
        # Create graph display area
        self.graph_display_frame = QFrame()
        self.graph_display_frame.setSizePolicy(
            QSizePolicy.Policy.Expanding, 
            QSizePolicy.Policy.Expanding
        )
        layout.addWidget(self.graph_display_frame)

    def create_selection_frame(self, parent_layout):
        """Create the graph selection controls"""
        selection_frame = QFrame()
        selection_frame.setFixedWidth(UI_SETTINGS['graph_selection_width'])
        selection_layout = QVBoxLayout(selection_frame)

        # Broker selection
        self.broker_combo = QComboBox()
        self.broker_combo.clear()  # Ensure it's empty before adding items
        # Deduplicate broker display names (case-insensitive, strip whitespace)
        seen = set()
        unique_brokers = []
        for name in BROKERS.values():
            normalized = name.strip().lower()
            if normalized not in seen:
                seen.add(normalized)
                unique_brokers.append(name.strip())
        self.broker_combo.addItems(['All'] + unique_brokers)
        self.broker_combo.setCurrentText('Trade Nation')
        selection_layout.addWidget(self.broker_combo)

        # Account filter
        self.create_account_filter(selection_layout)

        # Date range selection
        selection_layout.addWidget(QLabel("Start Date:"))
        self.start_date = QLineEdit()
        selection_layout.addWidget(self.start_date)

        selection_layout.addWidget(QLabel("End Date:"))
        self.end_date = QLineEdit()
        selection_layout.addWidget(self.end_date)

        # Quick selection buttons
        self.create_quick_select_buttons(selection_layout)

        # Graph type selection
        selection_layout.addWidget(QLabel("Select Graph Type:"))
        self.graph_list = QTreeWidget()
        self.graph_list.setHeaderLabels(["Graph Types"])
        self.graph_list.setFixedWidth(UI_SETTINGS['graph_list_width'])
        self.graph_list.itemDoubleClicked.connect(self.on_graph_double_click)

        for graph_type in VALID_GRAPH_TYPES:
            item = QTreeWidgetItem([graph_type])
            self.graph_list.addTopLevelItem(item)

        selection_layout.addWidget(self.graph_list)

        # Display button
        display_button = QPushButton("Display Graph")
        display_button.clicked.connect(self.display_selected_graph)
        selection_layout.addWidget(display_button)

        parent_layout.addWidget(selection_frame)

    def create_account_filter(self, parent_layout):
        """Create account filter dropdown"""
        account_frame = QFrame()
        account_layout = QHBoxLayout(account_frame)

        account_label = QLabel("Filter by Account:")
        account_layout.addWidget(account_label)

        self.account_combo = QComboBox()
        self.account_combo.addItem("All Accounts", "all")
        account_layout.addWidget(self.account_combo)

        parent_layout.addWidget(account_frame)

    def load_accounts(self):
        """Load accounts into the combo box"""
        try:
            conn = sqlite3.connect('trading.db')
            accounts_df = pd.read_sql_query("SELECT * FROM accounts", conn)
            conn.close()

            self.account_combo.clear()
            self.account_combo.addItem("All Accounts", "all")

            for _, row in accounts_df.iterrows():
                self.account_combo.addItem(f"{row['account_name']} ({row['account_id']})", row['account_id'])

        except Exception as e:
            logger.error(f"Failed to load accounts: {str(e)}")

    def create_quick_select_buttons(self, parent_layout):
        """Create quick date selection buttons"""
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

        parent_layout.addWidget(quick_select_frame)

    def set_date_range(self, days):
        """Set date range for last N days"""
        if self.data_manager.has_data():
            end_date = pd.Timestamp.now()
            start_date = end_date - pd.Timedelta(days=days)
            self.start_date.setText(start_date.strftime('%Y-%m-%d'))
            self.end_date.setText(end_date.strftime('%Y-%m-%d'))

    def reset_date_range(self):
        """Clear date range filters"""
        self.start_date.clear()
        self.end_date.clear()

    def on_graph_double_click(self, item, column):
        """Handle double-click on graph type"""
        self.graph_list.setCurrentItem(item)
        self.display_selected_graph()

    def display_selected_graph(self):
        """Display the selected graph"""
        try:
            # Get filtered data
            filtered_data = self.get_filtered_data()
            if filtered_data is None or filtered_data.empty:
                logger.warning("No data available after filtering")
                QMessageBox.warning(self, "Info", "No data available for selected date range")
                return

            # Get selected graph type
            current_item = self.graph_list.currentItem()
            if not current_item:
                QMessageBox.warning(self, "Selection", "Please select a graph type")
                return
                
            selection = current_item.text(0)

            # Generate visualization
            fig = create_visualization_figure(
                filtered_data, 
                selection, 
                self.settings_manager.get_exchange_rates(), 
                self.settings_manager.get_base_currency()
            )
            
            # Display in webview
            self.visualization_manager.display_plotly_figure(
                self.graph_display_frame, 
                fig, 
                "graph_display"
            )
            
        except Exception as e:
            logger.error(f"Error displaying graph: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to create visualization: {str(e)}")

    def get_filtered_data(self):
        """Get filtered data based on current selections"""
        if not self.data_manager.has_data():
            logger.warning("No data in data_manager")
            return None

        logger.debug(f"Data shape before filtering: {self.data_manager.df.shape}")
        selected_broker = self.broker_combo.currentText()
        broker_key = None
        if selected_broker != 'All':
            broker_key = [k for k, v in BROKERS.items() if v == selected_broker]
            broker_key = broker_key[0] if broker_key else None

        account_id = None
        if hasattr(self, "account_combo"):
            account_id = self.account_combo.currentData()
            if account_id == "all":
                account_id = None

        start_date = self.start_date.text() if self.start_date.text() else None
        end_date = self.end_date.text() if self.end_date.text() else None

        logger.debug(f"Filters - broker_key: {broker_key}, account_id: {account_id}, start_date: {start_date}, end_date: {end_date}")

        return self.data_manager.get_filtered_data(
            broker_key, account_id, start_date, end_date
        )

    def validate_date_range(self):
        """Validate date range inputs"""
        start = self.start_date.text()
        end = self.end_date.text()
        
        if not start or not end:
            return True  # Empty dates are valid
            
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