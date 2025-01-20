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
    'funding': ['green', 'darkgreen', 'forestgreen']
}

# Market Settings
MARKET_SPREADS = {
    'USTEC': {
        'normal_hours': (9, 17, 0.9),
        'closing_hours': (17, 18, 1.4),
        'off_hours': (18, 9, 1.5)
    },
    'Wall Street': {
        'normal_hours': (9, 17, 1.5),
        'closing_hours': (17, 18, 2.0),
        'off_hours': (18, 9, 4.0)
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
    'Distribution Days',
    'Funding',
    'Funding Charges',
    'Long vs Short Positions',
    'Market Actions',
    'Market P/L',
    'Daily P/L'
]
