"""Settings manager for application configuration and persistence."""

import json
import logging
import os

from PyQt6.QtCore import QObject, pyqtSignal

import settings as _settings
from settings import (
    AVAILABLE_CURRENCIES,
    DEFAULT_BASE_CURRENCY,
    DEFAULT_EXCHANGE_RATES,
)

logger = logging.getLogger(__name__)

CONFIG_DIR = os.path.expanduser("~/.trading-analyzer")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")


class SettingsManager(QObject):
    """Manages application settings and configuration persistence."""

    accounts_updated = pyqtSignal()

    def __init__(self):
        """Initialize the settings manager with default values."""
        super().__init__()
        self.exchange_rates = DEFAULT_EXCHANGE_RATES.copy()
        self.base_currency = DEFAULT_BASE_CURRENCY
        self.debug_mode = False
        self.theme = "Light"
        self.transparency = 100

    def _load_config(self):
        """
        Load configuration from JSON file.

        Returns:
            dict: Configuration dictionary, or empty dict if file doesn't exist
        """
        try:
            if not os.path.isdir(CONFIG_DIR):
                os.makedirs(CONFIG_DIR, exist_ok=True)
            if os.path.exists(CONFIG_PATH):
                with open(CONFIG_PATH, "r", encoding="utf-8") as fh:
                    return json.load(fh)
        except Exception as e:
            logger.warning(f"Failed to load config: {e}")
        return {}

    def _save_config(self, cfg: dict):
        """
        Save configuration to JSON file.

        Args:
            cfg: Configuration dictionary to save
        """
        try:
            if not os.path.isdir(CONFIG_DIR):
                os.makedirs(CONFIG_DIR, exist_ok=True)
            with open(CONFIG_PATH, "w", encoding="utf-8") as fh:
                json.dump(cfg, fh, indent=2)
        except Exception:
            logger.exception("Failed to save settings config")

    def get_exchange_rates(self):
        """
        Get current exchange rates.

        Returns:
            dict: Copy of current exchange rates
        """
        return self.exchange_rates.copy()

    def get_base_currency(self):
        """
        Get the persisted base currency.

        Returns:
            str: Base currency code (e.g., 'USD', 'SEK')
        """
        cfg = self._load_config()
        val = cfg.get("base_currency")
        if val:
            return val
        return getattr(_settings, "DEFAULT_BASE_CURRENCY", "USD")

    def set_base_currency(self, cur: str):
        """
        Set and persist base currency.

        Also updates the runtime settings module so other modules see the change.

        Args:
            cur: Currency code to set as base currency
        """
        cfg = self._load_config()
        cfg["base_currency"] = cur
        self._save_config(cfg)
        try:
            # Update settings module at runtime
            setattr(_settings, "DEFAULT_BASE_CURRENCY", cur)
        except Exception as e:
            logger.warning(f"Failed to update runtime settings: {e}")

    def update_exchange_rate(self, currency, rate):
        """
        Update exchange rate for a currency.

        Args:
            currency: Currency code to update
            rate: New exchange rate value

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            rate_value = float(rate)
            if rate_value <= 0:
                raise ValueError("Rate must be positive")

            # Convert rate to USD-based rate for internal storage
            if self.base_currency == "USD":
                self.exchange_rates[currency] = rate_value
            else:
                # Convert: rate is currency to base_currency
                # We need currency to USD = rate * (base_currency to USD)
                base_to_usd = self.exchange_rates.get(self.base_currency, 1.0)
                self.exchange_rates[currency] = rate_value * base_to_usd

            logger.debug(
                f"Updated exchange rate for {currency}: {rate} {self.base_currency}"
            )
            return True

        except ValueError as e:
            logger.warning(f"Invalid exchange rate for {currency}: {rate} - {e}")
            return False

    def reset_exchange_rates(self):
        """Reset exchange rates to default values."""
        self.exchange_rates = DEFAULT_EXCHANGE_RATES.copy()
        logger.info("Exchange rates reset to defaults")

    def calculate_rate_for_display(self, currency):
        """
        Calculate exchange rate for display in current base currency.

        Args:
            currency: Currency code to calculate rate for

        Returns:
            float: Exchange rate relative to base currency
        """
        if currency == self.base_currency:
            return 1.0

        if currency in self.exchange_rates:
            if self.base_currency == "USD":
                return self.exchange_rates[currency]
            else:
                # Convert: (currency to USD) / (base_currency to USD)
                currency_to_usd = self.exchange_rates.get(currency, 1.0)
                base_to_usd = self.exchange_rates.get(self.base_currency, 1.0)
                return currency_to_usd / base_to_usd if base_to_usd else 1.0
        else:
            return 1.0

    def set_debug_mode(self, enabled):
        """
        Set debug mode and update logging levels.

        Args:
            enabled: True to enable debug mode, False to disable
        """
        self.debug_mode = enabled

        # Update logging level
        root_logger = logging.getLogger()
        if enabled:
            root_logger.setLevel(logging.DEBUG)
            for name in logging.root.manager.loggerDict:
                logger_instance = logging.getLogger(name)
                logger_instance.setLevel(logging.DEBUG)
        else:
            root_logger.setLevel(logging.INFO)
            for name in logging.root.manager.loggerDict:
                logger_instance = logging.getLogger(name)
                logger_instance.setLevel(logging.INFO)

        logger.info(f"Debug mode {'enabled' if enabled else 'disabled'}")

    def set_theme(self, theme):
        """
        Set application theme.

        Args:
            theme: Theme name ('Light' or 'Dark')

        Returns:
            bool: True if successful, False otherwise
        """
        if theme in ["Light", "Dark"]:
            self.theme = theme
            logger.info(f"Theme changed to {theme}")
            return True
        return False

    def set_transparency(self, value):
        """
        Set window transparency.

        Args:
            value: Transparency value (0-100)

        Returns:
            bool: True if successful, False otherwise
        """
        if 0 <= value <= 100:
            self.transparency = value
            return True
        return False

    def get_theme_stylesheet(self):
        """
        Get stylesheet for current theme.

        Returns:
            str: Qt stylesheet string
        """
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
