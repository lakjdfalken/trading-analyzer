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

# Market Settings
MARKETS = {
    "Wall Street 30 (Dow)": 67995,
    "NASDAQ": 70433,
    "S&P 500": 67994
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
    'Win Rate',
    'Funding',
    'Funding Charges',
    'Long vs Short Positions',
    'Market Actions',
    'Market P/L',
    'Daily P/L',
    'Daily Trades',
    'Daily P/L vs Trades',
    'Monthly P/L',
    'Points Won/Lost'
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