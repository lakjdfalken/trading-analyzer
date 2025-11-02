import json
import logging
import os
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QMessageBox
import settings as _settings

from settings import (DEFAULT_EXCHANGE_RATES, AVAILABLE_CURRENCIES, 
                     DEFAULT_BASE_CURRENCY)

logger = logging.getLogger(__name__)

CONFIG_DIR = os.path.expanduser("~/.trading-analyzer")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")

class SettingsManager(QObject):
    accounts_updated = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.exchange_rates = DEFAULT_EXCHANGE_RATES.copy()
        self.base_currency = DEFAULT_BASE_CURRENCY
        self.debug_mode = False
        self.theme = 'Light'
        self.transparency = 100

    def add_account(self, account_data):
        # ... existing code ...
        self.accounts_updated.emit()  # Emit signal after adding an account

    def update_account(self, account_id, account_data):
        # ... existing code ...
        self.accounts_updated.emit()  # Emit signal after updating an account

    def delete_account(self, account_id):
        # ... existing code ...
        self.accounts_updated.emit()  # Emit signal after deleting an account

    def _load_config(self):
        try:
            if not os.path.isdir(CONFIG_DIR):
                os.makedirs(CONFIG_DIR, exist_ok=True)
            if os.path.exists(CONFIG_PATH):
                with open(CONFIG_PATH, "r", encoding="utf-8") as fh:
                    return json.load(fh)
        except Exception:
            pass
        return {}

    def _save_config(self, cfg: dict):
        try:
            if not os.path.isdir(CONFIG_DIR):
                os.makedirs(CONFIG_DIR, exist_ok=True)
            with open(CONFIG_PATH, "w", encoding="utf-8") as fh:
                json.dump(cfg, fh, indent=2)
        except Exception:
            logger = __import__("logging").getLogger(__name__)
            logger.exception("Failed to save settings config")

    def get_exchange_rates(self):
        """Return current exchange rates"""
        return self.exchange_rates.copy()

    def get_base_currency(self):
        """Return the persisted base currency or fallback to settings module DEFAULT_BASE_CURRENCY."""
        cfg = self._load_config()
        val = cfg.get("base_currency")
        if val:
            return val
        return getattr(_settings, "DEFAULT_BASE_CURRENCY", "USD")

    def set_base_currency(self, cur: str):
        """Persist base currency and update runtime settings module so other modules see the change."""
        cfg = self._load_config()
        cfg["base_currency"] = cur
        self._save_config(cfg)
        try:
            # update settings module at runtime so chart code that reads settings.* sees the new default
            setattr(_settings, "DEFAULT_BASE_CURRENCY", cur)
        except Exception:
            pass

    def update_exchange_rate(self, currency, rate):
        """Update exchange rate for a currency"""
        try:
            rate_value = float(rate)
            if rate_value <= 0:
                raise ValueError("Rate must be positive")
                
            # Convert rate to USD-based rate for internal storage
            if self.base_currency == 'USD':
                self.exchange_rates[currency] = rate_value
            else:
                # Convert: rate is currency to base_currency
                # We need currency to USD = rate * (base_currency to USD)
                base_to_usd = self.exchange_rates.get(self.base_currency, 1.0)
                self.exchange_rates[currency] = rate_value * base_to_usd
            
            logger.debug(f"Updated exchange rate for {currency}: {rate} {self.base_currency}")
            return True
            
        except ValueError as e:
            logger.warning(f"Invalid exchange rate for {currency}: {rate} - {e}")
            return False

    def reset_exchange_rates(self):
        """Reset exchange rates to defaults"""
        self.exchange_rates = DEFAULT_EXCHANGE_RATES.copy()
        logger.info("Exchange rates reset to defaults")

    def calculate_rate_for_display(self, currency):
        """Calculate rate for display in current base currency"""
        if currency == self.base_currency:
            return 1.0
            
        if currency in self.exchange_rates:
            if self.base_currency == 'USD':
                return self.exchange_rates[currency]
            else:
                # Convert: (currency to USD) / (base_currency to USD)
                currency_to_usd = self.exchange_rates.get(currency, 1.0)
                base_to_usd = self.exchange_rates.get(self.base_currency, 1.0)
                return currency_to_usd / base_to_usd
        else:
            return 1.0

    def set_debug_mode(self, enabled):
        """Set debug mode"""
        self.debug_mode = enabled
        
        # Update logging level
        root_logger = logging.getLogger()
        if enabled:
            root_logger.setLevel(logging.DEBUG)
            for name in logging.root.manager.loggerDict:
                logger = logging.getLogger(name)
                logger.setLevel(logging.DEBUG)
        else:
            root_logger.setLevel(logging.INFO)
            for name in logging.root.manager.loggerDict:
                logger = logging.getLogger(name)
                logger.setLevel(logging.INFO)
                
        logger.info(f"Debug mode {'enabled' if enabled else 'disabled'}")

    def set_theme(self, theme):
        """Set application theme"""
        if theme in ['Light', 'Dark']:
            self.theme = theme
            logger.info(f"Theme changed to {theme}")
            return True
        return False

    def set_transparency(self, value):
        """Set window transparency"""
        if 0 <= value <= 100:
            self.transparency = value
            return True
        return False

    def get_theme_stylesheet(self):
        """Get stylesheet for current theme"""
        if self.theme == "Dark":
            return """
                QWidget { background-color: #232629; color: #f0f0f0; }
                QLabel, QLineEdit, QComboBox, QCheckBox, QPushButton, QTextEdit {
                    color: #f0f0f0;
                    background-color: #232629;
                }
                QFrame { background-color: #232629; }
                QScrollArea { background-color: #232629; }
            """
        else:
            return ""