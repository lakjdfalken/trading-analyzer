from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel,
                           QComboBox, QPushButton, QCheckBox, QSlider, QLineEdit,
                           QMessageBox, QDialog, QFormLayout, QTextEdit, QDialogButtonBox, QSizePolicy, QScrollArea, QGridLayout)
from PyQt6.QtCore import Qt
import logging
import sqlite3
from settings import AVAILABLE_CURRENCIES, UI_SETTINGS
import pandas as pd

logger = logging.getLogger(__name__)

class SettingsTab(QWidget):
    def __init__(self, settings_manager, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.settings_manager = settings_manager
        self.exchange_rate_inputs = {}
        self.account_combo = None  # Initialize account_combo attribute
        self.setup_ui()

        # Connect signals for account updates
        self.settings_manager.accounts_updated.connect(self.load_accounts)

    def setup_ui(self):
        """Setup the settings tab UI with a more fluid layout"""
        # Create a main layout with a scroll area for better resizing
        main_layout = QVBoxLayout(self)
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        main_layout.addWidget(scroll_area)

        # Create a container widget for the scroll area
        container = QWidget()
        scroll_area.setWidget(container)

        # Create the main layout for the container
        layout = QVBoxLayout(container)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)  # Reduced spacing between sections

        # Create a grid layout for the settings
        grid_layout = QGridLayout()
        grid_layout.setSpacing(10)  # Reduced spacing between items
        grid_layout.setColumnStretch(0, 1)  # First column stretches
        grid_layout.setColumnStretch(1, 2)  # Second column stretches more

        # Debug mode control
        self.create_debug_control(grid_layout, 0, 0)

        # Theme selection
        self.create_theme_control(grid_layout, 1, 0)

        # Currency settings
        self.create_currency_settings(grid_layout, 2, 0)

        # Account settings
        self.create_account_settings(grid_layout, 3, 0)

        # Transparency control
        self.create_transparency_control(grid_layout, 4, 0)

        # About button
        self.create_about_section(grid_layout, 5, 0)

        layout.addLayout(grid_layout)

        # Add stretch to push content to the top
        layout.addStretch()

        # Set minimum size for the container
        container.setMinimumSize(400, 600)

        # Load accounts after UI is set up
        self.load_accounts()

    def create_debug_control(self, parent_layout, row, col):
        """Create debug mode control with improved layout"""
        debug_frame = QFrame()
        debug_frame.setFrameShape(QFrame.Shape.StyledPanel)
        debug_frame.setFrameShadow(QFrame.Shadow.Raised)
        debug_layout = QHBoxLayout(debug_frame)
        debug_layout.setContentsMargins(5, 5, 5, 5)  # Reduced margins

        debug_label = QLabel("Enable Debug Mode")
        debug_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        debug_layout.addWidget(debug_label)

        self.debug_checkbox = QCheckBox()
        self.debug_checkbox.setFixedWidth(30)
        self.debug_checkbox.stateChanged.connect(self.toggle_debug_mode)
        debug_layout.addWidget(self.debug_checkbox)

        parent_layout.addWidget(debug_frame, row, col)

    def create_theme_control(self, parent_layout, row, col):
        """Create theme selection control with improved layout"""
        theme_frame = QFrame()
        theme_frame.setFrameShape(QFrame.Shape.StyledPanel)
        theme_frame.setFrameShadow(QFrame.Shadow.Raised)
        theme_layout = QHBoxLayout(theme_frame)
        theme_layout.setContentsMargins(5, 5, 5, 5)  # Reduced margins

        theme_label = QLabel("Select Theme:")
        theme_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        theme_layout.addWidget(theme_label)

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(['Light', 'Dark'])
        self.theme_combo.setFixedWidth(100)
        self.theme_combo.currentTextChanged.connect(self.change_theme)
        theme_layout.addWidget(self.theme_combo)

        theme_layout.addStretch()

        parent_layout.addWidget(theme_frame, row, col)

    def create_currency_settings(self, parent_layout, row, col):
        """Create currency settings section with improved layout"""
        currency_frame = QFrame()
        currency_frame.setFrameShape(QFrame.Shape.StyledPanel)
        currency_frame.setFrameShadow(QFrame.Shadow.Raised)
        currency_frame.setStyleSheet("QFrame { margin: 5px; padding: 5px; }")  # Reduced padding
        currency_layout = QVBoxLayout(currency_frame)
        currency_layout.setContentsMargins(5, 5, 5, 5)  # Reduced margins
        currency_layout.setSpacing(5)  # Reduced spacing

        # Title
        currency_title = QLabel("Currency Settings")
        currency_title.setStyleSheet("font-weight: bold; font-size: 12px; margin-bottom: 5px;")  # Reduced font size and margin
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

        parent_layout.addWidget(currency_frame, row, col)

    def create_base_currency_control(self, parent_layout):
        """Create base currency selection with improved layout"""
        base_currency_layout = QHBoxLayout()
        base_currency_layout.setContentsMargins(0, 0, 0, 0)
        base_currency_layout.setSpacing(5)  # Reduced spacing

        base_currency_label = QLabel("Base Currency:")
        base_currency_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        base_currency_layout.addWidget(base_currency_label)

        self.base_currency_combo = QComboBox(self)
        self.base_currency_combo.addItems(AVAILABLE_CURRENCIES)
        self.base_currency_combo.setCurrentText(self.settings_manager.get_base_currency())
        self.base_currency_combo.setFixedWidth(80)
        # persist base currency when the user changes it
        self.base_currency_combo.currentTextChanged.connect(self._on_base_currency_changed)
        base_currency_layout.addWidget(self.base_currency_combo)

        info_label = QLabel("(All amounts will be converted to this currency)")
        info_label.setStyleSheet("font-size: 10px; color: gray;")
        info_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        base_currency_layout.addWidget(info_label)

        parent_layout.addLayout(base_currency_layout)

    def create_exchange_rates_section(self, parent_layout):
        """Create exchange rates section with improved layout"""
        rates_title = QLabel("Exchange Rates")
        rates_title.setStyleSheet("font-weight: bold; font-size: 12px; margin-top: 5px;")
        parent_layout.addWidget(rates_title)

        base_currency = self.settings_manager.get_base_currency()
        rates_info = QLabel(f"Enter how much 1 unit of each currency equals in {base_currency}")
        rates_info.setStyleSheet("font-size: 10px; color: gray; margin-bottom: 5px;")
        self.rates_info_label = rates_info
        parent_layout.addWidget(rates_info)

        # Create a scroll area for exchange rates with reduced height
        rates_scroll = QScrollArea()
        rates_scroll.setWidgetResizable(True)
        rates_scroll.setFixedHeight(80)  # Further reduced height
        rates_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        parent_layout.addWidget(rates_scroll)

        # Create a container widget for the scroll area
        rates_container = QWidget()
        rates_scroll.setWidget(rates_container)

        # Create the layout for the container
        self.rates_layout = QVBoxLayout(rates_container)
        self.rates_layout.setContentsMargins(0, 0, 0, 0)
        self.rates_layout.setSpacing(0)  # Removed spacing between exchange rate fields
        self.rates_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.create_exchange_rate_inputs()

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

    def create_transparency_control(self, parent_layout, row, col):
        """Create transparency control with improved layout"""
        trans_frame = QFrame()
        trans_frame.setFrameShape(QFrame.Shape.StyledPanel)
        trans_frame.setFrameShadow(QFrame.Shadow.Raised)
        trans_layout = QVBoxLayout(trans_frame)
        trans_layout.setContentsMargins(5, 5, 5, 5)  # Reduced margins

        trans_label = QLabel("Window Transparency")
        trans_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        trans_layout.addWidget(trans_label)

        self.trans_slider = QSlider(Qt.Orientation.Horizontal)
        self.trans_slider.setRange(50, 100)
        self.trans_slider.setValue(100)
        self.trans_slider.setFixedWidth(200)
        self.trans_slider.valueChanged.connect(self.change_transparency)
        trans_layout.addWidget(self.trans_slider, alignment=Qt.AlignmentFlag.AlignHCenter)

        parent_layout.addWidget(trans_frame, row, col)

    def create_about_section(self, parent_layout, row, col):
        """Create about section with improved layout"""
        about_frame = QFrame()
        about_frame.setFrameShape(QFrame.Shape.StyledPanel)
        about_frame.setFrameShadow(QFrame.Shadow.Raised)
        about_layout = QHBoxLayout(about_frame)
        about_layout.setContentsMargins(5, 5, 5, 5)  # Reduced margins

        about_label = QLabel("Application Info:")
        about_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        about_layout.addWidget(about_label)

        about_button = QPushButton("About")
        about_button.setFixedWidth(100)
        about_button.clicked.connect(self.show_about)
        about_layout.addWidget(about_button)

        about_layout.addStretch()

        parent_layout.addWidget(about_frame, row, col)

    def toggle_debug_mode(self, state):
        """Toggle debug mode"""
        enabled = state == Qt.CheckState.Checked.value
        self.settings_manager.set_debug_mode(enabled)

    def change_theme(self, theme):
        """Change application theme"""
        if self.settings_manager.set_theme(theme):
            # Apply theme to parent window
            parent_window = self.window()
            stylesheet = self.settings_manager.get_theme_stylesheet()
            if parent_window:
                parent_window.setStyleSheet(stylesheet)
            # Apply to all children in this tab
            self.setStyleSheet(stylesheet)

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

    def create_account_settings(self, parent_layout, row, col):
        """Create account settings section with improved layout"""
        account_frame = QFrame()
        account_frame.setFrameShape(QFrame.Shape.StyledPanel)
        account_frame.setFrameShadow(QFrame.Shadow.Raised)
        account_frame.setStyleSheet("QFrame { margin: 5px; padding: 5px; }")  # Reduced padding
        account_layout = QVBoxLayout(account_frame)
        account_layout.setContentsMargins(5, 5, 5, 5)  # Reduced margins
        account_layout.setSpacing(5)  # Reduced spacing

        # Title
        account_title = QLabel("Account Settings")
        account_title.setStyleSheet("font-weight: bold; font-size: 12px; margin-bottom: 5px;")  # Reduced font size and margin
        account_layout.addWidget(account_title)

        # Account selection
        account_select_layout = QHBoxLayout()
        account_select_layout.setContentsMargins(0, 0, 0, 0)
        account_select_layout.setSpacing(5)  # Reduced spacing

        account_label = QLabel("Select Account:")
        account_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        account_select_layout.addWidget(account_label)

        self.account_combo = QComboBox()
        self.account_combo.addItem("All Accounts", "all")
        self.account_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        account_select_layout.addWidget(self.account_combo)

        account_layout.addLayout(account_select_layout)

        # Account management buttons
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(5)  # Reduced spacing

        add_account_btn = QPushButton("Add Account")
        add_account_btn.clicked.connect(self.add_account)
        btn_layout.addWidget(add_account_btn)

        edit_account_btn = QPushButton("Edit Account")
        edit_account_btn.clicked.connect(self.edit_account)
        btn_layout.addWidget(edit_account_btn)

        delete_account_btn = QPushButton("Delete Account")
        delete_account_btn.clicked.connect(self.delete_account)
        btn_layout.addWidget(delete_account_btn)

        account_layout.addLayout(btn_layout)

        parent_layout.addWidget(account_frame, row, col)

    def add_account(self):
        """Add a new account"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Add New Account")
        layout = QFormLayout(dialog)

        account_name = QLineEdit()
        broker_name = QLineEdit()
        currency = QComboBox()
        currency.addItems(AVAILABLE_CURRENCIES)
        initial_balance = QLineEdit()
        notes = QTextEdit()

        layout.addRow("Account Name:", account_name)
        layout.addRow("Broker Name:", broker_name)
        layout.addRow("Currency:", currency)
        layout.addRow("Initial Balance:", initial_balance)
        layout.addRow("Notes:", notes)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)

        if dialog.exec():
            try:
                conn = sqlite3.connect('trading.db')
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO accounts (account_name, broker_name, currency, initial_balance, notes)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    account_name.text(),
                    broker_name.text(),
                    currency.currentText(),
                    float(initial_balance.text()) if initial_balance.text() else 0,
                    notes.toPlainText()
                ))
                conn.commit()
                conn.close()
                self.load_accounts()
                QMessageBox.information(self, "Success", "Account added successfully")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to add account: {str(e)}")

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

    def edit_account(self):
        """Edit an existing account"""
        # Get the selected account ID
        selected_account_id = self.account_combo.currentData()

        if not selected_account_id or selected_account_id == "all":
            QMessageBox.warning(self, "Account Selection", "Please select an account to edit")
            return

        # Fetch the account details from the database
        try:
            conn = sqlite3.connect('trading.db')
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM accounts WHERE account_id = ?", (selected_account_id,))
            account_data = cursor.fetchone()
            conn.close()

            if not account_data:
                QMessageBox.warning(self, "Error", "Selected account not found in database")
                return

            # Create a dialog for editing the account
            dialog = QDialog(self)
            dialog.setWindowTitle("Edit Account")
            layout = QFormLayout(dialog)

            # Create input fields with existing data
            # Convert each value to a string explicitly
            account_id = QLineEdit(str(account_data[0]))  # Convert to string
            account_id.setReadOnly(True)  # Account ID should not be editable
            account_name = QLineEdit(str(account_data[1]) if account_data[1] is not None else "")
            broker_name = QLineEdit(str(account_data[2]) if account_data[2] is not None else "")
            currency = QComboBox()
            currency.addItems(AVAILABLE_CURRENCIES)
            currency.setCurrentText(str(account_data[3]) if account_data[3] is not None else AVAILABLE_CURRENCIES[0])
            initial_balance = QLineEdit(str(account_data[4]) if account_data[4] is not None else "0")
            notes = QTextEdit()
            notes.setText(str(account_data[5]) if account_data[5] is not None else "")

            layout.addRow("Account ID:", account_id)
            layout.addRow("Account Name:", account_name)
            layout.addRow("Broker Name:", broker_name)
            layout.addRow("Currency:", currency)
            layout.addRow("Initial Balance:", initial_balance)
            layout.addRow("Notes:", notes)

            buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
            buttons.accepted.connect(dialog.accept)
            buttons.rejected.connect(dialog.reject)
            layout.addRow(buttons)

            if dialog.exec():
                try:
                    conn = sqlite3.connect('trading.db')
                    cursor = conn.cursor()
                    cursor.execute("""
                        UPDATE accounts
                        SET account_name = ?, broker_name = ?, currency = ?, initial_balance = ?, notes = ?
                        WHERE account_id = ?
                    """, (
                        account_name.text(),
                        broker_name.text(),
                        currency.currentText(),
                        float(initial_balance.text()) if initial_balance.text() else 0,
                        notes.toPlainText(),
                        account_id.text()
                    ))
                    conn.commit()
                    conn.close()
                    self.load_accounts()
                    QMessageBox.information(self, "Success", "Account updated successfully")
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed to update account: {str(e)}")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to fetch account details: {str(e)}")

    def delete_account(self):
        """Delete an existing account"""
        # Get the selected account ID
        selected_account_id = self.account_combo.currentData()

        if not selected_account_id or selected_account_id == "all":
            QMessageBox.warning(self, "Account Selection", "Please select an account to delete")
            return

        # Confirm deletion with the user
        reply = QMessageBox.question(
            self,
            "Confirm Deletion",
            f"Are you sure you want to delete account {selected_account_id}?\n"
            "This action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.No:
            return

        try:
            # Check if there are any transactions associated with this account
            conn = sqlite3.connect('trading.db')
            cursor = conn.cursor()

            # Count transactions for this account
            cursor.execute("SELECT COUNT(*) FROM broker_transactions WHERE account_id = ?", (selected_account_id,))
            transaction_count = cursor.fetchone()[0]

            if transaction_count > 0:
                # Ask user how to handle associated transactions
                transaction_reply = QMessageBox.question(
                    self,
                    "Transactions Found",
                    f"Found {transaction_count} transactions associated with this account.\n"
                    "What would you like to do with these transactions?",
                    "Delete Transactions|Reassign Transactions|Cancel",
                    QMessageBox.StandardButton.Cancel
                )

                if transaction_reply == QMessageBox.StandardButton.Cancel:
                    conn.close()
                    return

                if transaction_reply == 0:  # Delete Transactions
                    # Delete the account and its transactions
                    cursor.execute("DELETE FROM broker_transactions WHERE account_id = ?", (selected_account_id,))
                    cursor.execute("DELETE FROM accounts WHERE account_id = ?", (selected_account_id,))
                    conn.commit()
                    conn.close()
                    QMessageBox.information(self, "Success", "Account and associated transactions deleted successfully")
                elif transaction_reply == 1:  # Reassign Transactions
                    # Show dialog to select new account for transactions
                    reassign_dialog = QDialog(self)
                    reassign_dialog.setWindowTitle("Reassign Transactions")
                    reassign_layout = QVBoxLayout(reassign_dialog)

                    # Get list of other accounts
                    cursor.execute("SELECT account_id, account_name FROM accounts WHERE account_id != ?", (selected_account_id,))
                    other_accounts = cursor.fetchall()

                    if not other_accounts:
                        QMessageBox.warning(self, "Error", "No other accounts available to reassign transactions")
                        conn.close()
                        return

                    # Create account selection
                    account_label = QLabel("Select account to reassign transactions to:")
                    reassign_layout.addWidget(account_label)

                    account_combo = QComboBox()
                    for account_id, account_name in other_accounts:
                        account_combo.addItem(f"{account_name} ({account_id})", account_id)
                    reassign_layout.addWidget(account_combo)

                    # Add buttons
                    buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
                    buttons.accepted.connect(reassign_dialog.accept)
                    buttons.rejected.connect(reassign_dialog.reject)
                    reassign_layout.addWidget(buttons)

                    if reassign_dialog.exec():
                        new_account_id = account_combo.currentData()

                        # Reassign transactions to new account
                        cursor.execute(
                            "UPDATE broker_transactions SET account_id = ? WHERE account_id = ?",
                            (new_account_id, selected_account_id)
                        )

                        # Delete the account
                        cursor.execute("DELETE FROM accounts WHERE account_id = ?", (selected_account_id,))
                        conn.commit()
                        conn.close()
                        QMessageBox.information(
                            self,
                            "Success",
                            f"Account deleted successfully. Transactions reassigned to account {new_account_id}"
                        )
                    else:
                        conn.close()
                        return
            else:
                # No transactions, just delete the account
                cursor.execute("DELETE FROM accounts WHERE account_id = ?", (selected_account_id,))
                conn.commit()
                conn.close()
                QMessageBox.information(self, "Success", "Account deleted successfully")

            # Refresh the account list
            self.load_accounts()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to delete account: {str(e)}")
            if 'conn' in locals():
                conn.close()

    def showEvent(self, event):
        """Override showEvent to load accounts when the tab becomes visible"""
        super().showEvent(event)
        self.load_accounts()

    def _on_base_currency_changed(self, cur: str):
        """Persist base currency selection so charts use it across restarts."""
        try:
            self.settings_manager.set_base_currency(cur)
        except Exception:
            logging.getLogger(__name__).exception("Failed to persist base currency change")
