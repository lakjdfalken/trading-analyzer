# Trading Analyzer

A modern web-based tool for analyzing trading data and generating insights from broker transaction exports.

## Features

- **Dashboard**: Real-time KPIs, balance history, monthly P/L, win rate by instrument
- **Transactions**: Browse, search, and filter all trades with pagination
- **Analytics**: Daily P/L, drawdown analysis, hourly/weekday performance, streaks, trade duration
- **Import**: CSV import with automatic column mapping for multiple brokers
- **Multi-Account**: Support for multiple trading accounts and brokers
- **Multi-Currency**: Currency conversion and per-currency analysis
- **Dark Mode**: Modern UI built with Next.js and Tailwind CSS

## Architecture

- **Frontend**: Next.js 14, TypeScript, Tailwind CSS, shadcn/ui, Recharts
- **Backend**: FastAPI (Python), SQLite database
- **Desktop**: Standalone app via PyInstaller + pywebview

## Prerequisites

- Python 3.9+
- Node.js 18+

## Quick Start

### Option 1: Development Mode (Recommended for Development)

**Terminal 1 - Start the API server:**
```bash
cd trading-analyzer
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python run_api.py
```

**Terminal 2 - Start the frontend:**
```bash
cd trading-analyzer/frontend
npm install
npm run dev
```

Open http://localhost:3000

### Option 2: Production Mode (Single Server)

```bash
# Build frontend
cd frontend
npm install
npm run build
cd ..

# Run (serves both API and frontend)
python run_api.py
```

Open http://localhost:8000

### Option 3: Standalone Desktop App

```bash
python app.py
```

This opens a native window with the full application.

## Building Standalone Executables

### macOS

```bash
# Setup
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Build frontend
cd frontend && npm install && npm run build && cd ..

# Build app
pyinstaller trading_analyzer.spec

# Run
xattr -cr "dist/Trading Analyzer.app"  # Remove quarantine
open "dist/Trading Analyzer.app"
```

### Windows

```powershell
# Setup
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# Build frontend
cd frontend
npm install
npm run build
cd ..

# Build app
pyinstaller trading_analyzer.spec

# Run
dist\Trading Analyzer\Trading Analyzer.exe
```

## Supported Brokers

- **Trade Nation** (Serial column format)
- **TD365** (Ref. No. column format)
- **Generic** (configurable column mapping)

## CSV Import

The application accepts CSV exports with the following columns:
- Transaction Date
- Serial / Ref. No. (reference number)
- Action
- Description
- Amount
- Open Period
- Opening / Closing prices
- P/L
- Status
- Balance
- Currency

## API Documentation

When the API server is running, visit:
- Swagger UI: http://localhost:8000/api/docs
- ReDoc: http://localhost:8000/api/redoc

## Project Structure

```
trading-analyzer/
├── frontend/              # Next.js frontend
│   ├── src/
│   │   ├── app/          # Pages (dashboard, transactions, analytics, etc.)
│   │   ├── components/   # React components
│   │   └── store/        # Zustand state management
│   └── package.json
├── src/
│   ├── api/              # FastAPI backend
│   │   ├── routers/      # API endpoints
│   │   ├── models/       # Pydantic schemas
│   │   └── services/     # Database services
│   ├── create_database.py
│   ├── import_data.py
│   └── settings.py
├── app.py                # Standalone app entry point
├── run_api.py            # API server runner
├── trading_analyzer.spec # PyInstaller config
└── requirements.txt
```

## License

MIT License - See LICENSE file for details

## Contributing

Contributions are welcome:
- Open an issue to discuss proposed changes
- Submit a pull request with improvements
- Share bug reports or feature requests