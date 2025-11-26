"""Main application window for Trading Data Analyzer."""

import logging
import platform

from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtWidgets import (
    QMainWindow,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from settings import WINDOW_CONFIG

from .data_manager import DataManager
from .settings_manager import SettingsManager
from .tabs.data_tab import DataTab
from .tabs.general_data_tab import DataOverviewTab
from .tabs.graph_tab import GraphTab
from .tabs.overview_tab import OverviewTab
from .tabs.settings_tab import SettingsTab
from .visualization_manager import VisualizationManager

logger = logging.getLogger(__name__)


class TradingAnalyzerGUI(QMainWindow):
    """Main application window for the Trading Data Analyzer."""

    def __init__(self):
        """Initialize the main window and all managers."""
        super().__init__()
        self.setWindowTitle("Trading Data Analyzer")
        self.resize(WINDOW_CONFIG["default_width"], WINDOW_CONFIG["default_height"])

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
        """Set up the main UI components."""
        # Create central widget and main layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)

        # Create tabs
        self.create_tabs()

    def create_tabs(self):
        """Create and set up all tabs."""
        self.tab_widget = QTabWidget()

        # Create tab instances
        self.data_tab = DataTab()
        self.graph_tab = GraphTab(
            self.data_manager, self.visualization_manager, self.settings_manager
        )
        self.settings_tab = SettingsTab(self.settings_manager)
        self.overview_tab = OverviewTab(self.data_manager, self.visualization_manager)
        self.general_data_tab = DataOverviewTab(
            self.data_manager, self.settings_manager
        )

        # Add tabs to widget
        self.tab_widget.addTab(self.data_tab, "Data View")
        self.tab_widget.addTab(self.graph_tab, "Graphs")
        self.tab_widget.addTab(self.settings_tab, "Settings")
        self.tab_widget.addTab(self.overview_tab, "Tax Overview")
        self.tab_widget.addTab(self.general_data_tab, "General Data")

        # Connect settings tab import signal
        self.settings_tab.import_requested.connect(self.handle_import)

        self.main_layout.addWidget(self.tab_widget)

    def handle_import(self, broker_key: str, file_path: str, account_id: str):
        """Handle CSV import request from settings tab."""
        self.data_manager.import_data(file_path, broker_key, account_id)
        self.data_tab.update_display(self.data_manager.get_data())
        self.overview_tab.update_year_combo(self.data_manager.get_data())

    def cleanup_temp_graphs(self):
        """Clean up graph files older than 24 hours."""
        self.visualization_manager.cleanup_temp_files()

    def create_menu_bar(self):
        """Create the application menu bar."""
        menubar = self.menuBar()

        settings_menu = menubar.addMenu("Settings")
        preferences_action = QAction("Preferences...", self)

        if platform.system() == "Darwin":  # macOS
            preferences_action.setShortcut(QKeySequence("Cmd+,"))
        elif platform.system() == "Windows":
            preferences_action.setShortcut(QKeySequence("Ctrl+P"))
        else:  # Linux and others
            preferences_action.setShortcut(QKeySequence("Ctrl+,"))

        preferences_action.triggered.connect(self.show_preferences)
        settings_menu.addAction(preferences_action)

    def show_preferences(self):
        """Show preferences dialog."""
        self.settings_tab.show_preferences_dialog()

    def closeEvent(self, event):
        """Handle application close and cleanup resources."""
        logger.info("Application closing, performing cleanup...")

        try:
            if hasattr(self, "cleanup_timer"):
                self.cleanup_timer.stop()

            self.visualization_manager.cleanup()
            self.data_manager.cleanup()

            event.accept()
            logger.info("Cleanup completed successfully")

        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            event.accept()
