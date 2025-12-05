# =============================================================================
# DESIGN SYSTEM
# =============================================================================

# Theme Mode: 'dark', 'light', or 'system'
THEME_MODE = "dark"

# -----------------------------------------------------------------------------
# Color Palettes
# -----------------------------------------------------------------------------

COLORS_DARK = {
    # Backgrounds
    "bg_primary": "#0F172A",  # Main background (Slate 900)
    "bg_secondary": "#1E293B",  # Cards, panels (Slate 800)
    "bg_tertiary": "#334155",  # Hover states (Slate 700)
    # Text
    "text_primary": "#F8FAFC",  # Primary text (Slate 50)
    "text_secondary": "#94A3B8",  # Secondary text (Slate 400)
    "text_muted": "#64748B",  # Muted text (Slate 500)
    # Semantic Colors
    "profit": "#10B981",  # Green (Emerald 500)
    "profit_bg": "#064E3B",  # Green background (Emerald 900)
    "loss": "#EF4444",  # Red (Red 500)
    "loss_bg": "#7F1D1D",  # Red background (Red 900)
    "neutral": "#6B7280",  # Gray (Gray 500)
    # Accent Colors
    "accent_primary": "#3B82F6",  # Blue (Blue 500)
    "accent_secondary": "#8B5CF6",  # Purple (Violet 500)
    "accent_tertiary": "#F59E0B",  # Amber (Amber 500)
    # Borders
    "border": "#334155",  # Border color (Slate 700)
    "border_light": "#475569",  # Light border (Slate 600)
    # Chart Colors (for multi-series)
    "chart_1": "#3B82F6",  # Blue
    "chart_2": "#10B981",  # Green
    "chart_3": "#F59E0B",  # Amber
    "chart_4": "#EF4444",  # Red
    "chart_5": "#8B5CF6",  # Purple
    "chart_6": "#EC4899",  # Pink
    "chart_7": "#06B6D4",  # Cyan
    "chart_8": "#84CC16",  # Lime
    # Legacy mappings (for backward compatibility)
    "trading": "#3B82F6",
    "funding": "#1E293B",
    "funding_charge": "#EF4444",
}

COLORS_LIGHT = {
    # Backgrounds
    "bg_primary": "#F8FAFC",  # Main background
    "bg_secondary": "#FFFFFF",  # Cards, panels
    "bg_tertiary": "#F1F5F9",  # Hover states
    # Text
    "text_primary": "#0F172A",  # Primary text
    "text_secondary": "#475569",  # Secondary text
    "text_muted": "#94A3B8",  # Muted text
    # Semantic Colors
    "profit": "#059669",  # Darker green for light bg (Emerald 600)
    "profit_bg": "#D1FAE5",  # Light green background (Emerald 100)
    "loss": "#DC2626",  # Darker red for light bg (Red 600)
    "loss_bg": "#FEE2E2",  # Light red background (Red 100)
    "neutral": "#6B7280",  # Gray (Gray 500)
    # Accent Colors
    "accent_primary": "#2563EB",  # Blue (Blue 600)
    "accent_secondary": "#7C3AED",  # Purple (Violet 600)
    "accent_tertiary": "#D97706",  # Amber (Amber 600)
    # Borders
    "border": "#E2E8F0",  # Border color (Slate 200)
    "border_light": "#CBD5E1",  # Light border (Slate 300)
    # Chart Colors (for multi-series)
    "chart_1": "#2563EB",  # Blue
    "chart_2": "#059669",  # Green
    "chart_3": "#D97706",  # Amber
    "chart_4": "#DC2626",  # Red
    "chart_5": "#7C3AED",  # Purple
    "chart_6": "#DB2777",  # Pink
    "chart_7": "#0891B2",  # Cyan
    "chart_8": "#65A30D",  # Lime
    # Legacy mappings (for backward compatibility)
    "trading": "#2563EB",
    "funding": "#FFFFFF",
    "funding_charge": "#DC2626",
}


# Active color palette based on theme mode
def get_colors():
    """Get the active color palette based on current theme mode."""
    if THEME_MODE == "light":
        return COLORS_LIGHT
    return COLORS_DARK


# Legacy COLORS dict - now dynamically references theme colors
# This maintains backward compatibility with existing code
COLORS = {
    "profit": COLORS_DARK["profit"],
    "loss": COLORS_DARK["loss"],
    "neutral": COLORS_DARK["neutral"],
    "trading": COLORS_DARK["trading"],
    "funding": COLORS_DARK["funding"],
    "funding_charge": COLORS_DARK["funding_charge"],
}

# -----------------------------------------------------------------------------
# Typography
# -----------------------------------------------------------------------------

TYPOGRAPHY = {
    "font_family": '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif',
    "font_family_mono": '"SF Mono", "Fira Code", "Fira Mono", Menlo, Monaco, monospace',
    "sizes": {
        "xs": 10,
        "sm": 12,
        "base": 14,
        "lg": 16,
        "xl": 20,
        "2xl": 24,
        "3xl": 30,
        "4xl": 36,
        "5xl": 48,
    },
    "weights": {
        "normal": 400,
        "medium": 500,
        "semibold": 600,
        "bold": 700,
    },
    "line_heights": {
        "tight": 1.25,
        "normal": 1.5,
        "relaxed": 1.75,
    },
}

# -----------------------------------------------------------------------------
# Spacing (8px grid system)
# -----------------------------------------------------------------------------

SPACING = {
    "xs": 4,
    "sm": 8,
    "md": 16,
    "lg": 24,
    "xl": 32,
    "2xl": 48,
    "3xl": 64,
}

# -----------------------------------------------------------------------------
# Border Radius
# -----------------------------------------------------------------------------

BORDER_RADIUS = {
    "none": 0,
    "sm": 4,
    "md": 8,
    "lg": 12,
    "xl": 16,
    "2xl": 24,
    "full": 9999,
}

# -----------------------------------------------------------------------------
# Shadows (for dark mode - subtle)
# -----------------------------------------------------------------------------

SHADOWS = {
    "sm": "0 1px 2px 0 rgba(0, 0, 0, 0.05)",
    "md": "0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)",
    "lg": "0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)",
    "xl": "0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)",
}

# -----------------------------------------------------------------------------
# Chart/Plotly Theme Settings
# -----------------------------------------------------------------------------

CHART_THEME = {
    "dark": {
        "paper_bgcolor": "#0F172A",
        "plot_bgcolor": "#0F172A",
        "font_color": "#F8FAFC",
        "grid_color": "#334155",
        "zero_line_color": "#475569",
        "axis_line_color": "#475569",
        "title_font_size": 16,
        "axis_font_size": 12,
        "legend_bgcolor": "rgba(30, 41, 59, 0.8)",
        "legend_border_color": "#334155",
        "annotation_bgcolor": "#1E293B",
        "annotation_border_color": "#334155",
        "annotation_font_color": "#F8FAFC",
        "hoverlabel_bgcolor": "#1E293B",
        "hoverlabel_font_color": "#F8FAFC",
        "bar_line_color": "#0F172A",
        "bar_line_width": 1,
    },
    "light": {
        "paper_bgcolor": "#FFFFFF",
        "plot_bgcolor": "#FFFFFF",
        "font_color": "#0F172A",
        "grid_color": "#E2E8F0",
        "zero_line_color": "#CBD5E1",
        "axis_line_color": "#CBD5E1",
        "title_font_size": 16,
        "axis_font_size": 12,
        "legend_bgcolor": "rgba(255, 255, 255, 0.9)",
        "legend_border_color": "#E2E8F0",
        "annotation_bgcolor": "#FFFFFF",
        "annotation_border_color": "#E2E8F0",
        "annotation_font_color": "#0F172A",
        "hoverlabel_bgcolor": "#FFFFFF",
        "hoverlabel_font_color": "#0F172A",
        "bar_line_color": "#FFFFFF",
        "bar_line_width": 1,
    },
}


def get_chart_theme():
    """Get the active chart theme based on current theme mode."""
    if THEME_MODE == "light":
        return CHART_THEME["light"]
    return CHART_THEME["dark"]


# =============================================================================
# VISUAL SETTINGS (Legacy)
# =============================================================================

FIGURE_SIZES = {"default": (10, 6), "wide": (12, 6), "square": (8, 8)}

# Market Settings - Enhanced version
MARKET_MAPPINGS = {
    # Standard mappings (broker-agnostic)
    "standard": {
        "Wall Street": [
            r"(?i)wall\s*street",
            r"(?i)dow",
            r"(?i)wall\s*st",
            r"(?i)dji",
            r"(?i)us\s*30",
        ],
        "NASDAQ": [r"(?i)nasdaq", r"(?i)nasdaq\s*100", r"(?i)us\s*tech", r"(?i)ustec"],
        "S&P 500": [
            r"(?i)s\s*&\s*p",
            r"(?i)spx",
            r"(?i)sp\s*500",
            r"(?i)us\s*500\s*-?\s*rolling\s*future\s*\(per\s*1\.0\)",
            r"(?i)us\s*500\s*\(per\s*1\.0\)",
        ],
        "Russell 2000": [
            r"(?i)russell\s*2000",
            r"(?i)us\s*2000\s*-?\s*rolling\s*future",
            r"(?i)rut",
            r"(?i)us\s*small\s*cap",
        ],
        "Germany 40": [
            r"(?i)germany\s*40\s*-?\s*rolling\s*future",
            r"(?i)dax",
            r"(?i)germany\s*40",
        ],
        "UK 100": [
            r"(?i)uk\s*100\s*-?\s*rolling\s*future",
            r"(?i)uk\s*100",
            r"(?i)ftse\s*100",
            r"(?i)ftse",
        ],
        "Gold": [r"(?i)gold", r"(?i)xau", r"(?i)gld"],
        "Oil": [r"(?i)oil", r"(?i)crude", r"(?i)wti", r"(?i)brent"],
        "EUR/USD": [r"(?i)eur\s*usd", r"(?i)euro\s*dollar"],
        "GBP/USD": [r"(?i)gbp\s*usd", r"(?i)pound\s*dollar"],
        "USD/JPY": [r"(?i)usd\s*jpy", r"(?i)dollar\s*yen"],
        # Add a new category for individual stocks
        "Individual Stocks": [
            r"(?i)NOVO\s*NORDISK\s*AS",  # Add Novo Nordisk
            r"(?i)APPLE\s*INC",  # Example of other potential stocks
            r"(?i)MICROSOFT\s*CORP",  # Example of other potential stocks
            r"(?i)AMAZON\.COM",  # Example of other potential stocks
            r"(?i)TESLA\s*INC",  # Added Tesla Inc
        ],
    },
    # Broker-specific mappings (override or extend standard)
    "trade_nation": {
        "Wall Street": [r"(?i)wall\s*street\s*30"],
        "S&P 500": [
            r"(?i)us\s*500\s*-?\s*rolling\s*future",
            r"(?i)us\s*500.*per\s*1\.0",
        ],
        "NVIDIA": [r"(?i)nvidia\s*corp", r"(?i)nvda"],
        # Add other broker-specific patterns as needed
    },
    "td365": {
        "NASDAQ": [r"(?i)US\s*Tech\s*100"],
        # Add other broker-specific patterns
    },
}

# Keep existing MARKETS dictionary for ID lookups
MARKETS = {"Wall Street 30": 67995, "NASDAQ": 70433, "S&P 500": 67994}

# Map market IDs to standard names
MARKET_ID_MAPPING = {67995: "Wall Street", 70433: "NASDAQ", 67994: "S&P 500"}

# Format: (start_hour, end_hour, spread)
MARKET_SPREADS = {
    "USTEC": {
        "normal_hours": (9.5, 17, 0.9),  # 09:30 - 17:00
        "closing_hours": (17, 18, 1.4),
        "off_hours": (18, 9.5, 1.5),
    },
    "Wall Street": {
        "normal_hours": (9.5, 17, 1.5),  # 09:30 - 17:00
        "closing_hours": (17, 18, 2.0),
        "off_hours": (18, 9.5, 4.0),
    },
}

# Currency Settings
CURRENCY_SYMBOLS = {"DKK": "kr", "SEK": "kr", "EUR": "€", "GBP": "£", "USD": "$"}

# No default exchange rates - rates must be configured by user per .rules
# No hardcoded base currency - must be set by user in settings

# Explicit authoritative list of supported currencies (do not infer at runtime)
SUPPORTED_CURRENCIES = ["SEK", "DKK", "EUR", "USD", "GBP"]

# Keep AVAILABLE_CURRENCIES for backward compatibility but make it authoritative from SUPPORTED_CURRENCIES
AVAILABLE_CURRENCIES = SUPPORTED_CURRENCIES.copy()


# Graph Types
VALID_GRAPH_TYPES = [
    "Balance History",
    "P/L History",
    "Daily P/L",
    "Monthly P/L",
    "Market P/L",
    "Daily Trades",
    "Daily P/L vs Trades",
    "Points Daily",
    "Points Monthly",
    "Points per Market",
    "Win Rate",
    "Funding",
    #    'Funding Charges',
    "Long vs Short Positions",
    #    'Market Actions',
]

# Add to existing settings
BROKERS = {"none": "Select Broker", "trade_nation": "Trade Nation", "td365": "TD365"}

# Add these new configuration sections

# Window Settings
WINDOW_CONFIG = {
    "default_width": 1600,
    "default_height": 800,
    "min_width": 800,
    "min_height": 600,
}

# UI Component Settings
UI_SETTINGS = {
    "broker_combo_width": 120,
    "import_button_width": 100,
    "theme_combo_width": 100,
    "debug_checkbox_width": 30,
    "transparency_slider": {"min": 50, "max": 100, "default": 100, "width": 200},
    "graph_selection_width": 230,
    "graph_list_width": 230,
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
    "tp",
]

# Column Mappings for CSV Imports
COLUMN_MAPPINGS = {
    "trade_nation": {
        "transaction_date": ["Transaction Date"],
        "open_period": ["Open Period", "Open date"],
        "reference": ["Serial", "Ref. No."],  # Trade Nation uses Serial
        "action": ["Action"],
        "description": ["Description"],
        "amount": ["Amount"],
        "pl": ["P/L"],
        "balance": ["Balance"],
        "opening": ["Opening"],
        "closing": ["Closing"],
        "status": ["Status"],
        "currency": ["Currency"],
    },
    "td365": {
        "transaction_date": ["Transaction Date"],
        "open_period": ["Open Period", "Open date"],
        "reference": ["Ref. No.", "Serial"],
        "action": ["Action"],
        "description": ["Description"],
        "amount": ["Amount"],
        "pl": ["P/L"],
        "balance": ["Balance"],
        "opening": ["Opening"],
        "closing": ["Closing"],
        "status": ["Status"],
        "currency": ["Currency"],
    },
}

# Market-specific point calculation multipliers
# Format: market_name: points_multiplier
MARKET_POINT_MULTIPLIERS = {
    "Gold": 10,  # Gold increments by 0.1, so 1 price unit = 10 points
    "Oil": 1,  # Default multiplier (1 price unit = 1 point)
    "S&P 500": 1,
    "NASDAQ": 1,
    "Wall Street": 1,
    "Russell 2000": 1,
    "UK 100": 1,
    "Germany 40": 1,
    # Add more markets and their multipliers as needed
    # For forex pairs, you might need specific multipliers based on the pip value
    "EUR/USD": 10000,  # Example: 0.0001 change = 1 pip
    "GBP/USD": 10000,
    "USD/JPY": 100,  # Example: 0.01 change = 1 pip
}

# Default multiplier for markets not specifically listed
DEFAULT_POINT_MULTIPLIER = 1

# Overview tab specific settings
OVERVIEW_SETTINGS = {
    "year_all_label": "All Years",
    "all_brokers_label": "All",
    "view_types": ["Tax Overview Table", "Yearly Summary Chart"],
    "export": {
        "filename_template": "tax_overview_{year}{broker_suffix}.csv",
        "csv_filter": "CSV Files (*.csv)",
        "internal_broker_col": "broker_name",
        "column_renames": {
            "Broker_Display": "Broker",
            "Description": "Market",
            "Total_PL": "Total_P/L",
            "Trade_Count": "Number_of_Trades",
            "First_Trade": "First_Trade_Date",
            "Last_Trade": "Last_Trade_Date",
        },
    },
}

TRANSACTION_TYPE_PATTERNS = {
    "funding": [r"fund", r"deposit"],
    "charge": [r"charge", r"fee"],
    "withdrawal": [r"withdraw"],
    "trading": [r"buy", r"sell", r"open", r"close", r"trade", r"executed"],
}
