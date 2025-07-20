from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel,
                           QComboBox, QPushButton, QCheckBox, QSlider, QLineEdit,
                           QMessageBox, QDialog)
from PyQt6.QtCore import Qt
import logging
from settings import AVAILABLE_CURRENCIES, UI_SETTINGS

logger = logging.getLogger(__name__)


class SettingsTab(QWidget):
    def __init__(self, settings_manager):
        super().__init__()
        self.settings_manager = settings_manager
        self.exchange_rate_inputs = {}
        self.setup_ui()

    def setup_ui(self):
        """Setup the settings tab UI"""
        layout = QVBoxLayout(self)

        # Debug mode control
        self.create_debug_control(layout)
        
        # Theme selection
        self.create_theme_control(layout)
        
        # Currency settings
        self.create_currency_settings(layout)
        
        # Transparency control
        self.create_transparency_control(layout)
        
        # About button
        self.create_about_section(layout)
        
        layout.addStretch()

    def create_debug_control(self, parent_layout):
        """Create debug mode control"""
        debug_frame = QFrame()
        debug_layout = QHBoxLayout(debug_frame)
        debug_layout.addWidget(QLabel("Enable Debug Mode"))
        
        self.debug_checkbox = QCheckBox()
        self.debug_checkbox.setFixedWidth(30)
        self.debug_checkbox.stateChanged.connect(self.toggle_debug_mode)
        debug_layout.addWidget(self.debug_checkbox)
        debug_layout.addStretch()
        
        parent_layout.addWidget(debug_frame)

    def create_theme_control(self, parent_layout):
        """Create theme selection control"""
        theme_frame = QFrame()
        theme_layout = QHBoxLayout(theme_frame)
        theme_layout.addWidget(QLabel("Select Theme:"))
        
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(['Light', 'Dark'])
        self.theme_combo.setFixedWidth(100)
        self.theme_combo.currentTextChanged.connect(self.change_theme)
        theme_layout.addWidget(self.theme_combo)
        theme_layout.addStretch()
        
        parent_layout.addWidget(theme_frame)

    def create_currency_settings(self, parent_layout):
        """Create currency settings section"""
        currency_frame = QFrame()
        currency_frame.setStyleSheet("QFrame { border: 1px solid gray; margin: 5px; padding: 10px; }")
        currency_layout = QVBoxLayout(currency_frame)
        
        # Title
        currency_title = QLabel("Currency Settings")
        currency_title.setStyleSheet("font-weight: bold; font-size: 14px; margin-bottom: 10px;")
        currency_layout.addWidget(currency_title)
        
        # Base currency selection
        self.create_base_currency_control(currency_layout)
        
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        currency_layout.addWidget(separator)
        
        # Exchange rates
        self.create_exchange_rates_section(currency_layout)
        
        parent_layout.addWidget(currency_frame)

    def create_base_currency_control(self, parent_layout):
        """Create base currency selection"""
        base_currency_layout = QHBoxLayout()
        base_currency_layout.addWidget(QLabel("Base Currency:"))
        
        self.base_currency_combo = QComboBox()
        self.base_currency_combo.addItems(AVAILABLE_CURRENCIES)
        self.base_currency_combo.setCurrentText(self.settings_manager.get_base_currency())
        self.base_currency_combo.setFixedWidth(80)
        self.base_currency_combo.currentTextChanged.connect(self.change_base_currency)
        base_currency_layout.addWidget(self.base_currency_combo)
        
        base_currency_layout.addWidget(QLabel("(All amounts will be converted to this currency)"))
        base_currency_layout.addStretch()
        
        parent_layout.addLayout(base_currency_layout)

    def create_exchange_rates_section(self, parent_layout):
        """Create exchange rates section"""
        rates_title = QLabel("Exchange Rates")
        rates_title.setStyleSheet("font-weight: bold; font-size: 12px; margin-top: 10px;")
        parent_layout.addWidget(rates_title)
        
        base_currency = self.settings_manager.get_base_currency()
        rates_info = QLabel(f"Enter how much 1 unit of each currency equals in {base_currency}")
        rates_info.setStyleSheet("font-size: 10px; color: gray; margin-bottom: 5px;")
        self.rates_info_label = rates_info
        parent_layout.addWidget(rates_info)
        
        # Create exchange rate inputs
        self.rates_layout = QVBoxLayout()
        parent_layout.addLayout(self.rates_layout)
        
        self.create_exchange_rate_inputs()
        
        # Reset button
        reset_rates_button = QPushButton("Reset Exchange Rates to Defaults")
        reset_rates_button.setFixedWidth(200)
        reset_rates_button.clicked.connect(self.reset_exchange_rates)
        parent_layout.addWidget(reset_rates_button)

    def create_exchange_rate_inputs(self):
        """Create exchange rate input fields"""
        # Clear existing inputs
        while self.rates_layout.count():
            child = self.rates_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        self.exchange_rate_inputs.clear()
        base_currency = self.settings_manager.get_base_currency()
        
        # Create inputs for all currencies except base currency
        for currency in AVAILABLE_CURRENCIES:
            if currency != base_currency:
                rate_layout = QHBoxLayout()
                rate_layout.addWidget(QLabel(f"1 {currency} ="))
                
                rate_input = QLineEdit()
                rate_input.setFixedWidth(100)
                
                # Get current rate for display
                rate_value = self.settings_manager.calculate_rate_for_display(currency)
                rate_input.setText(f"{rate_value:.4f}")
                rate_input.textChanged.connect(
                    lambda text, curr=currency: self.update_exchange_rate(curr, text)
                )
                self.exchange_rate_inputs[currency] = rate_input
                rate_layout.addWidget(rate_input)
                
                rate_layout.addWidget(QLabel(base_currency))
                rate_layout.addStretch()
                
                # Create widget to hold the layout
                rate_widget = QWidget()
                rate_widget.setLayout(rate_layout)
                self.rates_layout.addWidget(rate_widget)

    def create_transparency_control(self, parent_layout):
        """Create transparency control"""
        trans_frame = QFrame()
        trans_layout = QVBoxLayout(trans_frame)
        trans_layout.addWidget(QLabel("Window Transparency"))
        
        self.trans_slider = QSlider(Qt.Orientation.Horizontal)
        self.trans_slider.setRange(50, 100)
        self.trans_slider.setValue(100)
        self.trans_slider.setFixedWidth(200)
        self.trans_slider.valueChanged.connect(self.change_transparency)
        trans_layout.addWidget(self.trans_slider)
        
        parent_layout.addWidget(trans_frame)

    def create_about_section(self, parent_layout):
        """Create about section"""
        about_frame = QFrame()
        about_layout = QHBoxLayout(about_frame)
        about_layout.addWidget(QLabel("Application Info:"))
        
        about_button = QPushButton("About")
        about_button.setFixedWidth(100)
        about_button.clicked.connect(self.show_about)
        about_layout.addWidget(about_button)
        about_layout.addStretch()
        
        parent_layout.addWidget(about_frame)

    def toggle_debug_mode(self, state):
        """Toggle debug mode"""
        enabled = state == Qt.CheckState.Checked.value
        self.settings_manager.set_debug_mode(enabled)

    def change_theme(self, theme):
        """Change application theme"""
        if self.settings_manager.set_theme(theme):
            # Apply theme to parent window
            parent_window = self.window()
            if parent_window:
                parent_window.setStyleSheet(self.settings_manager.get_theme_stylesheet())

    def change_transparency(self, value):
        """Change window transparency"""
        if self.settings_manager.set_transparency(value):
            # Apply transparency to parent window
            parent_window = self.window()
            if parent_window:
                parent_window.setWindowOpacity(value / 100)

    def change_base_currency(self, new_base_currency):
        """Handle base currency change"""
        if self.settings_manager.set_base_currency(new_base_currency):
            # Update the info label
            self.rates_info_label.setText(
                f"Enter how much 1 unit of each currency equals in {new_base_currency}"
            )
            
            # Recreate exchange rate inputs
            self.create_exchange_rate_inputs()
            
            # Show confirmation message
            QMessageBox.information(
                self, 
                "Base Currency Changed", 
                f"Base currency changed to {new_base_currency}.\n"
                f"Exchange rates have been recalculated.\n"
                f"Please verify the rates are correct."
            )

    def update_exchange_rate(self, currency, text):
        """Update exchange rate when user changes input"""
        self.settings_manager.update_exchange_rate(currency, text)

    def reset_exchange_rates(self):
        """Reset exchange rates to defaults"""
        self.settings_manager.reset_exchange_rates()
        
        # Recreate the input fields with default values
        self.create_exchange_rate_inputs()
        
        QMessageBox.information(self, "Exchange Rates", "Exchange rates have been reset to default values")

    def show_about(self):
        """Show about dialog"""
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

    def show_preferences_dialog(self):
        """Show preferences dialog (called from menu)"""
        dialog = QDialog(self)
        dialog.setWindowTitle('Preferences')
        layout = QVBoxLayout()

        # Theme settings
        theme_layout = QHBoxLayout()
        theme_layout.addWidget(QLabel("Theme:"))
        theme_combo = QComboBox()
        theme_combo.addItems(['Light', 'Dark'])
        theme_combo.setCurrentText(self.settings_manager.theme)
        theme_combo.currentTextChanged.connect(self.change_theme)
        theme_layout.addWidget(theme_combo)
        layout.addLayout(theme_layout)

        # Debug mode settings
        debug_layout = QHBoxLayout()
        debug_layout.addWidget(QLabel("Debug Mode:"))
        debug_checkbox = QCheckBox()
        debug_checkbox.setChecked(self.settings_manager.debug_mode)
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
        trans_slider.setValue(self.settings_manager.transparency)
        trans_slider.valueChanged.connect(self.change_transparency)
        trans_layout.addWidget(trans_slider)
        layout.addLayout(trans_layout)

        dialog.setLayout(layout)
        dialog.exec()