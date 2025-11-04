# Visual Settings
FIGURE_SIZES = {
    'default': (10, 6),
    'wide': (12, 6),
    'square': (8, 8)
}

COLORS = {
    'profit': 'green',
    'loss': 'red',
    'neutral': 'gray',
    'trading': 'blue',
    'funding': 'white',
    'funding_charge': 'black'
}

# Market Settings - Enhanced version
MARKET_MAPPINGS = {
    # Standard mappings (broker-agnostic)
    'standard': {
        'Wall Street': [
            r'(?i)wall\s*street',
            r'(?i)dow',
            r'(?i)wall\s*st',
            r'(?i)dji',
            r'(?i)us\s*30'
        ],
        'NASDAQ': [
            r'(?i)nasdaq',
            r'(?i)nasdaq\s*100', 
            r'(?i)us\s*tech',
            r'(?i)ustec'
        ],
        'S&P 500': [
            r'(?i)s\s*&\s*p',
            r'(?i)spx',
            r'(?i)sp\s*500',
            r'(?i)us\s*500\s*-?\s*rolling\s*future\s*\(per\s*1\.0\)',
            r'(?i)us\s*500\s*\(per\s*1\.0\)'
        ],
        'Russell 2000': [
            r'(?i)russell\s*2000',
            r'(?i)us\s*2000\s*-?\s*rolling\s*future',
            r'(?i)rut',
            r'(?i)us\s*small\s*cap'
        ],
        'Germany 40': [
            r'(?i)germany\s*40\s*-?\s*rolling\s*future',
            r'(?i)dax',
            r'(?i)germany\s*40'
        ],
        'UK 100': [
            r'(?i)uk\s*100\s*-?\s*rolling\s*future',
            r'(?i)uk\s*100',
            r'(?i)ftse\s*100',
            r'(?i)ftse'
        ],
        'Gold': [
            r'(?i)gold',
            r'(?i)xau',
            r'(?i)gld'
        ],
        'Oil': [
            r'(?i)oil',
            r'(?i)crude',
            r'(?i)wti',
            r'(?i)brent'
        ],
        'EUR/USD': [
            r'(?i)eur\s*usd',
            r'(?i)euro\s*dollar'
        ],
        'GBP/USD': [
            r'(?i)gbp\s*usd',
            r'(?i)pound\s*dollar'
        ],
        'USD/JPY': [
            r'(?i)usd\s*jpy',
            r'(?i)dollar\s*yen'
        ],
        # Add a new category for individual stocks
        'Individual Stocks': [
            r'(?i)NOVO\s*NORDISK\s*AS',  # Add Novo Nordisk
            r'(?i)APPLE\s*INC',          # Example of other potential stocks
            r'(?i)MICROSOFT\s*CORP',     # Example of other potential stocks
            r'(?i)AMAZON\.COM',          # Example of other potential stocks
            r'(?i)TESLA\s*INC'           # Added Tesla Inc
        ],
    },
    
    # Broker-specific mappings (override or extend standard)
    'trade_nation': {
        'Wall Street': [
            r'(?i)wall\s*street\s*30'
        ],
        'S&P 500': [
            r'(?i)us\s*500\s*-?\s*rolling\s*future',
            r'(?i)us\s*500.*per\s*1\.0'
        ],
        'NVIDIA': [
            r'(?i)nvidia\s*corp',
            r'(?i)nvda'
        ],
        # Add other broker-specific patterns as needed
    },
    
    'td365': {
        'NASDAQ': [
            r'(?i)US\s*Tech\s*100'
        ],
        # Add other broker-specific patterns
    }
}

# Keep existing MARKETS dictionary for ID lookups
MARKETS = {
    "Wall Street 30": 67995,
    "NASDAQ": 70433,
    "S&P 500": 67994
}

# Map market IDs to standard names
MARKET_ID_MAPPING = {
    67995: "Wall Street",
    70433: "NASDAQ",
    67994: "S&P 500"
}

# Format: (start_hour, end_hour, spread)
MARKET_SPREADS = {
    'USTEC': {
        'normal_hours': (9.5, 17, 0.9),  # 09:30 - 17:00
        'closing_hours': (17, 18, 1.4),
        'off_hours': (18, 9.5, 1.5)
    },
    'Wall Street': {
        'normal_hours': (9.5, 17, 1.5),  # 09:30 - 17:00
        'closing_hours': (17, 18, 2.0),
        'off_hours': (18, 9.5, 4.0)
    }
}

# Currency Settings
CURRENCY_SYMBOLS = {
    'DKK': 'kr',
    'SEK': 'kr',
    'EUR': '€',
    'GBP': '£',
    'USD': '$'
}

# Default exchange rates (base currency: SEK)
DEFAULT_EXCHANGE_RATES = {
    'SEK': 1,  # 1 SEK = 1 SEK (base currency)
    'DKK': 1.52,  # 1 DKK = 1.52 SEK
    'EUR': 11.32,  # 1 EUR = 11.32 SEK
    'USD': 10.50,  # 1 USD = 10.50 SEK (example rate)
    'GBP': 13.20,  # 1 GBP = 13.20 SEK (example rate)
}

# Base currency for conversions
DEFAULT_BASE_CURRENCY = 'SEK'

# Explicit authoritative list of supported currencies (do not infer at runtime)
SUPPORTED_CURRENCIES = ['SEK', 'DKK', 'EUR', 'USD', 'GBP']

# Keep AVAILABLE_CURRENCIES for backward compatibility but make it authoritative from SUPPORTED_CURRENCIES
AVAILABLE_CURRENCIES = SUPPORTED_CURRENCIES.copy()

# Canonical exchange-rates format (per-base): mapping base_currency -> { currency: rate_relative_to_base }
# This makes it explicit that DEFAULT_EXCHANGE_RATES maps each currency to its value in DEFAULT_BASE_CURRENCY.
EXCHANGE_RATES_BASE = DEFAULT_BASE_CURRENCY
DEFAULT_EXCHANGE_RATES_PER_BASE = {
    EXCHANGE_RATES_BASE: DEFAULT_EXCHANGE_RATES.copy()
}

# Graph Types
VALID_GRAPH_TYPES = [
    'Balance History',
    'P/L History',
    'Daily P/L',
    'Monthly P/L',
    'Market P/L',
    'Daily Trades',
    'Daily P/L vs Trades',
    'Points Daily',
    'Points Monthly',
    'Points per Market',
    'Win Rate',
    'Funding',
#    'Funding Charges',
    'Long vs Short Positions',
#    'Market Actions',
]

# Add to existing settings
BROKERS = {
    'none': 'Select Broker',
    'trade_nation': 'Trade Nation',
    'td365': 'TD365'
}

# Add these new configuration sections

# Window Settings
WINDOW_CONFIG = {
    'default_width': 1600,
    'default_height': 800,
    'min_width': 800,
    'min_height': 600
}

# UI Component Settings
UI_SETTINGS = {
    'broker_combo_width': 120,
    'import_button_width': 100,
    'theme_combo_width': 100,
    'debug_checkbox_width': 30,
    'transparency_slider': {
        'min': 50,
        'max': 100,
        'default': 100,
        'width': 200
    },
    'graph_selection_width': 230,
    'graph_list_width': 230
}

# Data View Columns
DATA_COLUMNS = [
    "broker_name", 
    "Transaction Date", 
    "Ref. No.", 
    "Action", 
    "Description",
    "Amount", 
    "Open Period", 
    "Opening", 
    "Closing", 
    "P/L",
    "Status", 
    "Balance", 
    "Currency", 
    "Fund_Balance", 
    "sl", 
    "tp"
]

# Column Mappings for CSV Imports
COLUMN_MAPPINGS = {
    'default': {
        'transaction_date': ['Transaction Date'],
        'open_period': ['Open Period', 'Open date'],  # Support both old and new names
        'reference': ['Ref. No.', 'Serial'],  # Support both old and new reference field names
        'action': ['Action'],
        'description': ['Description'],
        'amount': ['Amount'],
        'pl': ['P/L'],
        'balance': ['Balance'],
        'opening': ['Opening'],
        'closing': ['Closing'],
        'status': ['Status'],
        'currency': ['Currency']
    }
    # You can add broker-specific mappings if needed
    # 'trade_nation': { ... },
    # 'td365': { ... }
}

# Market-specific point calculation multipliers
# Format: market_name: points_multiplier
MARKET_POINT_MULTIPLIERS = {
    'Gold': 10,  # Gold increments by 0.1, so 1 price unit = 10 points
    'Oil': 1,    # Default multiplier (1 price unit = 1 point)
    'S&P 500': 1,
    'NASDAQ': 1,
    'Wall Street': 1,
    'Russell 2000': 1,
    'UK 100': 1,
    'Germany 40': 1,
    # Add more markets and their multipliers as needed
    # For forex pairs, you might need specific multipliers based on the pip value
    'EUR/USD': 10000,  # Example: 0.0001 change = 1 pip
    'GBP/USD': 10000,
    'USD/JPY': 100,    # Example: 0.01 change = 1 pip
}

# Default multiplier for markets not specifically listed
DEFAULT_POINT_MULTIPLIER = 1

# Overview tab specific settings
OVERVIEW_SETTINGS = {
    'year_all_label': 'All Years',
    'all_brokers_label': 'All',
    'view_types': ['Tax Overview Table', 'Yearly Summary Chart'],
    'export': {
        'filename_template': 'tax_overview_{year}{broker_suffix}.csv',
        'csv_filter': 'CSV Files (*.csv)',
        'internal_broker_col': 'broker_name',
        'column_renames': {
            'Broker_Display': 'Broker',
            'Description': 'Market',
            'Total_PL': 'Total_P/L',
            'Trade_Count': 'Number_of_Trades',
            'First_Trade': 'First_Trade_Date',
            'Last_Trade': 'Last_Trade_Date'
        }
    }
}

TRANSACTION_TYPE_PATTERNS = {
    'funding': [r'fund', r'deposit'],
    'charge': [r'charge', r'fee'],
    'withdrawal': [r'withdraw'],
    'trading': [r'buy', r'sell', r'open', r'close', r'trade', r'executed'],
}