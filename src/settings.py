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
    'Daily P/L vs Trades'
]

# Add to existing settings
BROKERS = {
    'none': 'Select Broker',
    'trade_nation': 'Trade Nation',
    'td365': 'TD365'
}
