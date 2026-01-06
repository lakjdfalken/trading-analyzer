# Trading Analyzer

A modern desktop application for analyzing trading data and generating insights from broker transaction exports.

![Trading Analyzer Dashboard](docs/screenshot.png)

## Download

### Pre-built Releases

| Platform | Download |
|----------|----------|
| macOS | [TradingAnalyzer-macOS.dmg](https://github.com/lakjdfalken/trading-analyzer/releases/latest/download/TradingAnalyzer-macOS.dmg) |
| Windows | [TradingAnalyzer-Windows-x64.zip](https://github.com/lakjdfalken/trading-analyzer/releases/latest/download/TradingAnalyzer-Windows-x64.zip) |

Or visit the [Releases page](https://github.com/lakjdfalken/trading-analyzer/releases) for all versions.

## Features

### Dashboard
- Real-time KPIs: Total P/L, Win Rate, Profit Factor, Max Drawdown
- Account Balance chart with multi-account support
- Monthly P/L breakdown
- Win rate by instrument
- Recent trades overview
- Account selector (view all accounts combined or individual accounts)

### Transactions
- Browse, search, and filter all trades
- Sort by any column
- Date range filtering
- Export to CSV
- Pagination with customizable page size

### Analytics
- **P&L Analysis**
  - Daily P/L chart with percentage returns
  - Cumulative P/L over time
  - Monthly P/L breakdown
  - Equity Curve (P/L only, excludes deposits/withdrawals)
  - Balance History (includes funding)
  - Funding Activity (deposits, withdrawals, net with totals)
- **Time-based Analysis**
  - Hourly performance patterns
  - Weekday performance breakdown
  - Trade duration statistics
- **Instrument Analysis**
  - Win rate by instrument
  - Points/pips by instrument
- **Performance Metrics**
  - Win/loss streaks
  - Position size analysis
- All charts support account filtering and proper currency conversion

### Data Import
- CSV import with automatic column mapping
- Support for multiple brokers
- Multi-account tracking

### Settings
- Default currency selection
- Exchange rate management
- Currency conversion for multi-currency accounts

### User Interface
- Modern dark mode UI
- Responsive charts with tooltips
- Expandable chart views
- Persistent filter preferences
- Account selector across all pages

## Multi-Currency Support

The application properly handles accounts in different currencies:

- **Backend converts, frontend displays**: All P&L aggregation and conversion happens on the backend
- **Account-aware**: When viewing a single account, data displays in that account's native currency
- **Combined view**: When viewing all accounts, values are converted to your default currency before aggregation
- **Exchange rates**: Configurable in Settings page

## Supported Brokers

- **Trade Nation** (Serial column format)
- **TD365** (Ref. No. column format)

## Installation

### Option 1: Download Pre-built App (Recommended)

1. Download the appropriate installer for your platform from the [Releases page](https://github.com/lakjdfalken/trading-analyzer/releases)
2. **macOS**: Open the DMG and drag to Applications. On first run, right-click and select "Open" to bypass Gatekeeper
3. **Windows**: Extract the ZIP and run `Trading Analyzer.exe`

### Option 2: Run from Source

**Prerequisites:**
- Python 3.9+
- Node.js 18+

**Setup:**

```bash
# Clone repository
git clone https://github.com/lakjdfalken/trading-analyzer.git
cd trading-analyzer

# Setup Python environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Build frontend
cd frontend
npm install
npm run build
cd ..

# Run the application
python app.py
```

### Option 3: Development Mode

**Terminal 1 - API Server:**
```bash
source .venv/bin/activate
python run_api.py
```

**Terminal 2 - Frontend Dev Server:**
```bash
cd frontend
npm run dev
```

Open http://localhost:3000

## CSV Import Format

The application accepts CSV exports with the following columns:

| Column | Description |
|--------|-------------|
| Transaction Date | Date/time of the trade |
| Serial / Ref. No. | Unique reference number |
| Action | Buy/Sell action |
| Description | Instrument name |
| Amount | Position size |
| Open Period | Entry date/time |
| Opening | Entry price |
| Closing | Exit price |
| P/L | Profit/Loss |
| Status | Trade status |
| Balance | Account balance after trade |
| Currency | Trade currency |

## Building from Source

### macOS

```bash
source .venv/bin/activate
cd frontend && npm run build && cd ..
pyinstaller trading_analyzer.spec

# Remove quarantine attribute
xattr -cr "dist/Trading Analyzer.app"

# Run
open "dist/Trading Analyzer.app"
```

### Windows

```powershell
.venv\Scripts\activate
cd frontend
npm run build
cd ..
pyinstaller trading_analyzer.spec

# Run
dist\Trading Analyzer\Trading Analyzer.exe
```

## Architecture

```
trading-analyzer/
├── frontend/                 # Next.js frontend
│   ├── src/
│   │   ├── app/             # Pages
│   │   │   ├── page.tsx     # Dashboard
│   │   │   ├── analytics/   # Analytics page
│   │   │   ├── transactions/# Transactions page
│   │   │   ├── import/      # Data import page
│   │   │   └── settings/    # Settings page
│   │   ├── components/      # React components
│   │   │   └── charts/      # Chart components (18 charts)
│   │   ├── store/           # Zustand state management
│   │   │   ├── dashboard.ts # Dashboard state & filters
│   │   │   ├── settings.ts  # User settings
│   │   │   └── currency.ts  # Currency formatting
│   │   └── lib/
│   │       └── api.ts       # Centralized API client
│   └── package.json
├── src/
│   └── api/                 # FastAPI backend
│       ├── routers/         # API endpoints
│       │   ├── dashboard.py # Dashboard data
│       │   ├── analytics.py # Analytics data
│       │   ├── trades.py    # Trade operations
│       │   ├── currency.py  # Currency & settings
│       │   ├── imports.py   # CSV import
│       │   └── instruments.py
│       ├── services/
│       │   ├── database.py  # SQLite operations
│       │   └── currency.py  # Currency conversion
│       └── models/          # Pydantic schemas
├── app.py                   # Desktop app entry point
├── run_api.py               # API server runner
├── trading_analyzer.spec    # PyInstaller configuration
└── requirements.txt
```

## Versioning

The app version is managed from a single `VERSION` file in the project root.

**To release a new version:**

```bash
# 1. Update VERSION file
echo "2.1.0" > VERSION

# 2. Sync version to frontend package.json
python scripts/sync_version.py

# 3. Commit and tag
git add -A
git commit -m "Bump version to 2.1.0"
git tag v2.1.0
git push origin main --tags
```

## API Documentation

When running in development mode, API documentation is available at:
- Swagger UI: http://localhost:8000/api/docs
- ReDoc: http://localhost:8000/api/redoc

## Data Storage

The application stores data in a platform-specific location:

| Platform | Location |
|----------|----------|
| macOS | `~/Library/Application Support/TradingAnalyzer/trading.db` |
| Windows | `%LOCALAPPDATA%\TradingAnalyzer\trading.db` |
| Linux | `~/.local/share/TradingAnalyzer/trading.db` |

## Changelog

### v2.0.18 (January 6, 2026)

- **Trade Frequency Chart**: New chart in Analytics → Performance showing trades per day, month, and year with totals and averages per account and aggregated
- **Monthly P&L Totals**: Added positive/negative month totals to the Monthly P&L chart alongside yearly totals
- **Spread Cost Analysis**: New chart in Analytics → Risk showing spread cost per trade based on Trade Nation market data with time-based spread lookups
- **Spread Data Source Note**: Settings page now shows when spread data was last updated with reference URL to Trade Nation Market Information Sheet

## License

MIT License - See [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please:

1. Open an issue to discuss proposed changes
2. Fork the repository
3. Create a feature branch
4. Submit a pull request

## Support

- [Open an issue](https://github.com/lakjdfalken/trading-analyzer/issues) for bug reports
- [Discussions](https://github.com/lakjdfalken/trading-analyzer/discussions) for questions and ideas