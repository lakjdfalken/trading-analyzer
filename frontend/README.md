# Trading Analyzer Frontend

Modern React frontend for the Trading Analyzer application, built with Next.js 14, TypeScript, and Tailwind CSS.

## Tech Stack

- **Framework**: Next.js 14 (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **UI Components**: Radix UI primitives
- **Charts**: Recharts
- **State Management**: Zustand
- **Icons**: Lucide React
- **Date Handling**: date-fns

## Getting Started

### Prerequisites

- Node.js 18+ 
- npm or yarn

### Installation

```bash
# Install dependencies
npm install

# Create environment file (optional - defaults are provided)
cp .env.example .env.local
```

### Development

```bash
# Start development server
npm run dev

# The app will be available at http://localhost:3000
```

### Production Build

```bash
# Type check
npm run type-check

# Build for production
npm run build

# Start production server
npm run start
```

## Project Structure

```
src/
├── app/                    # Next.js App Router pages
│   ├── page.tsx           # Dashboard (home)
│   ├── analytics/         # Analytics page
│   ├── transactions/      # Transactions page
│   ├── settings/          # Settings page
│   ├── layout.tsx         # Root layout with header
│   └── globals.css        # Global styles & CSS variables
│
├── components/
│   ├── charts/            # Chart components (Recharts)
│   │   ├── BalanceChart.tsx
│   │   ├── MonthlyPnLChart.tsx
│   │   ├── WinRateChart.tsx
│   │   └── ChartCard.tsx
│   ├── filters/           # Filter components
│   │   ├── DateRangePicker.tsx
│   │   ├── FilterBar.tsx
│   │   └── types.ts
│   ├── kpi/               # KPI card components
│   │   ├── KPICard.tsx
│   │   ├── KPIGrid.tsx
│   │   └── types.ts
│   ├── layout/            # Layout components
│   │   └── Header.tsx
│   ├── trades/            # Trade list components
│   │   ├── RecentTradesList.tsx
│   │   └── TradeRow.tsx
│   └── ui/                # Base UI primitives
│       ├── button.tsx
│       ├── card.tsx
│       ├── badge.tsx
│       └── ...
│
├── api/                   # API layer
│   ├── client.ts          # API client with fetch wrapper
│   ├── endpoints.ts       # Endpoint constants
│   ├── mockData.ts        # Mock data for development
│   └── types.ts           # API type definitions
│
├── store/                 # Zustand state management
│   └── dashboard.ts       # Dashboard store
│
├── hooks/                 # Custom React hooks
│   ├── useDashboard.ts    # Dashboard data hook
│   ├── useDebounce.ts     # Debounce utility
│   └── useLocalStorage.ts # LocalStorage hook
│
└── lib/
    └── utils.ts           # Utility functions (cn, formatters)
```

## Pages

### Dashboard (`/`)
- KPI cards showing key metrics (Total P&L, Win Rate, etc.)
- Equity curve chart
- Monthly P&L bar chart
- Win rate by instrument chart
- Recent trades list

### Analytics (`/analytics`)
- Chart gallery with category filtering
- 12+ chart types organized by category:
  - P&L Analysis
  - Performance
  - Time Analysis
  - Instruments
  - Risk Metrics

### Transactions (`/transactions`)
- Full trade list with pagination
- Search by instrument or ID
- Filters: direction, outcome, instruments
- Sortable columns
- Summary statistics bar

### Settings (`/settings`)
- Theme selection (Light/Dark/System)
- Currency and date format preferences
- Notification settings
- Risk management parameters
- Account information

## Environment Variables

Create a `.env.local` file in the frontend directory:

```env
# API Base URL - points to the Python FastAPI backend
NEXT_PUBLIC_API_URL=http://localhost:8000/api

# Enable mock data fallback when API is unavailable
NEXT_PUBLIC_USE_MOCK_FALLBACK=true
```

## API Integration

The frontend connects to a Python FastAPI backend. Key endpoints:

- `GET /api/dashboard` - Full dashboard data
- `GET /api/trades` - Paginated trades
- `GET /api/instruments` - Available instruments
- `GET /api/analytics/*` - Analytics endpoints

If the backend is unavailable and `NEXT_PUBLIC_USE_MOCK_FALLBACK=true`, the app will use mock data for development.

## Component Usage Examples

### KPICard

```tsx
import { KPICard } from '@/components/kpi';

<KPICard
  title="Total P&L"
  value="$12,450.00"
  subtitle="Last 30 days"
  icon={DollarSign}
  trend={{ value: 12.5, isPositive: true }}
  variant="success"
/>
```

### ChartCard with BalanceChart

```tsx
import { ChartCard } from '@/components/charts/ChartCard';
import { BalanceChart } from '@/components/charts/BalanceChart';

<ChartCard
  title="Account Balance"
  subtitle="Equity curve over time"
  onExpand={() => {}}
>
  <BalanceChart
    data={balanceData}
    height={300}
    startingBalance={10000}
    showGrid
  />
</ChartCard>
```

### DateRangePicker

```tsx
import { DateRangePicker } from '@/components/filters/DateRangePicker';

<DateRangePicker
  dateRange={{ from: startDate, to: endDate, preset: 'last30days' }}
  onDateRangeChange={(range) => setDateRange(range)}
/>
```

## Scripts

| Command | Description |
|---------|-------------|
| `npm run dev` | Start development server |
| `npm run build` | Build for production |
| `npm run start` | Start production server |
| `npm run lint` | Run ESLint |
| `npm run type-check` | Run TypeScript type checking |

## Styling

The app uses Tailwind CSS with a custom design system:

- **Colors**: Defined in `tailwind.config.ts` and CSS variables in `globals.css`
- **Dark Mode**: Default theme, with light mode support
- **Spacing**: 8px grid system
- **Border Radius**: Consistent rounded corners

## License

MIT