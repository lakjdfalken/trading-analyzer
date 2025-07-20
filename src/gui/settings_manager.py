import logging
from PyQt6.QtWidgets import QMessageBox
from settings import (DEFAULT_EXCHANGE_RATES, AVAILABLE_CURRENCIES, 
                     DEFAULT_BASE_CURRENCY)

logger = logging.getLogger(__name__)


class SettingsManager:
    def __init__(self):
        self.exchange_rates = DEFAULT_EXCHANGE_RATES.copy()
        self.base_currency = DEFAULT_BASE_CURRENCY
        self.debug_mode = False
        self.theme = 'Light'
        self.transparency = 100

    def get_exchange_rates(self):
        """Return current exchange rates"""
        return self.exchange_rates.copy()

    def get_base_currency(self):
        """Return current base currency"""
        return self.base_currency

    def set_base_currency(self, new_currency):
        """Set new base currency and recalculate rates"""
        if new_currency not in AVAILABLE_CURRENCIES:
            raise ValueError(f"Invalid currency: {new_currency}")
            
        old_currency = self.base_currency
        self.base_currency = new_currency
        
        logger.info(f"Base currency changed from {old_currency} to {new_currency}")
        return True

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
        if self.theme == 'Dark':
            return """
                QMainWindow, QWidget { background-color: #2b2b2b; color: #ffffff; }
                QTreeWidget { background-color: #363636; color: #ffffff; }
                QHeaderView::section { background-color: #404040; color: #ffffff; }
                QComboBox, QPushButton { background-color: #404040; color: #ffffff; }
            """
        else:
            return ""