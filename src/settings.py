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
    'trading': ['blue', 'darkblue', 'navy'],
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
    'GBP': '£',
    'USD': '$',
    'EUR': '€'
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
    'import_button_width': 80,
    'theme_combo_width': 100,
    'debug_checkbox_width': 30,
    'transparency_slider': {
        'min': 50,
        'max': 100,
        'default': 100,
        'width': 200
    },
    'graph_selection_width': 250,
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