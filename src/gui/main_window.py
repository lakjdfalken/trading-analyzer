from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                           QComboBox, QPushButton, QLabel, QFrame, QTabWidget,
                           QFileDialog, QMessageBox, QDialog)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QAction, QKeySequence
import logging
import platform
import shutil
from datetime import datetime, timedelta

from settings import WINDOW_CONFIG, UI_SETTINGS, BROKERS
from .data_manager import DataManager
from .visualization_manager import VisualizationManager
from .settings_manager import SettingsManager
from .tabs.data_tab import DataTab
from .tabs.graph_tab import GraphTab
from .tabs.settings_tab import SettingsTab
from .tabs.overview_tab import OverviewTab

logger = logging.getLogger(__name__)


class TradingAnalyzerGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Trading Data Analyzer")
        self.resize(WINDOW_CONFIG['default_width'], WINDOW_CONFIG['default_height'])
        
        # Initialize managers
        self.data_manager = DataManager()
        self.visualization_manager = VisualizationManager()
        self.settings_manager = SettingsManager()
        
        # Initialize cleanup timer
        self.cleanup_timer = QTimer()
        self.cleanup_timer.timeout.connect(self.cleanup_temp_graphs)
        self.cleanup_timer.start(300000)  # Cleanup every 5 minutes
        
        # Setup UI
        self.create_menu_bar()
        self.setup_ui()
        
        # Load existing data
        self.data_manager.load_existing_data()
        if self.data_manager.has_data():
            self.data_tab.update_display(self.data_manager.get_data())
            self.overview_tab.update_year_combo(self.data_manager.get_data())

    def setup_ui(self):
        """Setup the main UI components"""
        # Create central widget and main layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        
        # Create import frame
        self.create_import_frame()
        
        # Create tabs
        self.create_tabs()
        
    def create_import_frame(self):
        """Create the import controls frame"""
        import_frame = QFrame()
        import_layout = QHBoxLayout(import_frame)
        
        self.broker_combo = QComboBox()
        self.broker_combo.addItems(list(BROKERS.values()))
        self.broker_combo.setFixedWidth(UI_SETTINGS['broker_combo_width'])
        import_layout.addWidget(self.broker_combo)
        
        import_button = QPushButton("Import CSV")
        import_button.setFixedWidth(UI_SETTINGS['import_button_width'])
        import_button.clicked.connect(self.import_csv)
        import_layout.addWidget(import_button)
        
        self.main_layout.addWidget(import_frame)

    def create_tabs(self):
        """Create and setup all tabs"""
        self.tab_widget = QTabWidget()
        
        # Create tab instances
        self.data_tab = DataTab()
        self.graph_tab = GraphTab(self.data_manager, self.visualization_manager, self.settings_manager)
        self.settings_tab = SettingsTab(self.settings_manager)
        self.overview_tab = OverviewTab(self.data_manager, self.visualization_manager)
        
        # Add tabs to widget
        self.tab_widget.addTab(self.data_tab, "Data View")
        self.tab_widget.addTab(self.graph_tab, "Graphs")
        self.tab_widget.addTab(self.settings_tab, "Settings")
        self.tab_widget.addTab(self.overview_tab, "Tax Overview")
        
        self.main_layout.addWidget(self.tab_widget)

    def import_csv(self):
        """Handle CSV import"""
        # Get selected account from settings tab
        selected_account_id = None
        if hasattr(self.settings_tab, "account_combo"):
            selected_account_id = self.settings_tab.account_combo.currentData()
        if not selected_account_id or selected_account_id == "all":
            QMessageBox.warning(self, "Account Selection",
                          "Please select an account in the Settings tab before importing data")
            return

        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select CSV File", "", "CSV Files (*.csv)")

        if file_path:
            selected_broker = self.broker_combo.currentText()
            if selected_broker == 'Select Broker':
                QMessageBox.warning(self, "Broker Selection", "Please select a broker before importing")
                return

            # Find the correct broker key
            broker_key = None
            for k, v in BROKERS.items():
                if v == selected_broker:
                    broker_key = k
                    break

            if not broker_key or broker_key == "none":
                QMessageBox.warning(self, "Broker Selection", "Please select a valid broker before importing")
                return

            self.data_manager.import_data(file_path, broker_key, selected_account_id)
            self.data_tab.update_display(self.data_manager.get_data())
            self.overview_tab.update_year_combo(self.data_manager.get_data())

    def cleanup_temp_graphs(self):
        """Clean up graph files older than 24 hours"""
        self.visualization_manager.cleanup_temp_files()

    def create_menu_bar(self):
        """Create the application menu bar"""
        menubar = self.menuBar()
        
        settings_menu = menubar.addMenu('Settings')
        preferences_action = QAction('Preferences...', self)
        
        if platform.system() == 'Darwin':  # macOS
            preferences_action.setShortcut(QKeySequence("Cmd+,"))
        elif platform.system() == 'Windows':
            preferences_action.setShortcut(QKeySequence("Ctrl+P"))
        else:  # Linux and others
            preferences_action.setShortcut(QKeySequence("Ctrl+,"))

        preferences_action.triggered.connect(self.show_preferences)
        settings_menu.addAction(preferences_action)

    def show_preferences(self):
        """Show preferences dialog"""
        self.settings_tab.show_preferences_dialog()

    def closeEvent(self, event):
        """Handle application close"""
        logger.info("Application closing, performing cleanup...")
        
        try:
            if hasattr(self, 'cleanup_timer'):
                self.cleanup_timer.stop()
            
            self.visualization_manager.cleanup()
            self.data_manager.cleanup()
            
            event.accept()
            logger.info("Cleanup completed successfully")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            event.accept()