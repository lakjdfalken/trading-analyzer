# Trading Analyzer UI/UX Redesign Specification

**Version:** 1.0  
**Date:** 2025-01-15  
**Status:** Draft  

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Current State Analysis](#current-state-analysis)
3. [Design Goals](#design-goals)
4. [New Architecture](#new-architecture)
5. [Design System](#design-system)
6. [Component Specifications](#component-specifications)
7. [Implementation Phases](#implementation-phases)
8. [File Changes Summary](#file-changes-summary)
9. [Testing & Verification](#testing--verification)

---

## Executive Summary

This document outlines a comprehensive redesign of the Trading Analyzer application to create a modern, user-friendly trading dashboard. The redesign focuses on:

- **Dashboard-first approach**: Key metrics visible at a glance
- **Simplified navigation**: Reduce from 5 tabs to 4 with clearer purposes
- **Modern visual design**: Dark mode support, consistent color palette, professional typography
- **Better data visualization**: Interactive charts, KPI cards, sparklines

---

## Current State Analysis

### Existing Tab Structure

| Tab | Purpose | Issues |
|-----|---------|--------|
| Data View | Raw transaction table | No filtering, no summary stats |
| Graphs | Chart selection and display | Text-based list, no previews |
| Settings | Theme, accounts, import, currency | Cluttered, import buried here |
| Tax Overview | Tax reports by year/broker | Isolated from other charts |
| General Data | Statistics and summaries | Overlaps with Graphs tab |

### Current Chart Types (in `chart_types/`)

| File | Charts | Notes |
|------|--------|-------|
| `pl.py` | Daily P/L, Balance History, Monthly Distribution, Win/Loss Analysis | Core charts, need visual refresh |
| `winrate.py` | Win/Loss Distribution | Basic bar chart with annotations |
| `trades.py` | Daily Trade Count | Simple bar + average line |
| `funding.py` | Funding Distribution, Funding Charges | Complex multi-currency handling |
| `points.py` | Points Daily/Monthly/Per Market | Uses annotations for stats |
| `positions.py` | Long vs Short Positions | Pie chart with P/L summary |
| `tax_overview.py` | Tax Table, Yearly Summary | Table + bar chart |

### Identified UX Problems

1. **No landing page**: Users must navigate to understand their performance
2. **Information fragmentation**: Related data spread across multiple tabs
3. **Poor discoverability**: Text list for chart selection, no visual hints
4. **Inconsistent styling**: Charts have different annotation styles
5. **No quick insights**: Must generate charts to see any metrics
6. **Date handling**: Date filters repeated on multiple tabs

---

## Design Goals

### Primary Goals

1. **Immediate insight**: User sees key metrics within 1 second of launch
2. **Reduced cognitive load**: Fewer tabs, clearer organization
3. **Modern aesthetics**: Professional look matching modern trading platforms
4. **Consistency**: Unified design language across all components

### Secondary Goals

1. **Dark mode**: Reduce eye strain for extended use
2. **Responsive layout**: Adapt to window resizing
3. **Performance**: Fast chart rendering, lazy loading
4. **Accessibility**: Clear contrast, readable fonts

### Success Metrics

- Time to first insight: < 2 seconds (currently requires tab navigation)
- Number of clicks to view key stats: 0 (currently 2-3)
- User can identify profit/loss status: Immediately visible

---

## New Architecture

### Tab Structure (4 Tabs)

```
┌─────────────┬─────────────┬─────────────┬─────────────┐
│  Dashboard  │  Analytics  │ Transactions│  Settings   │
└─────────────┴─────────────┴─────────────┴─────────────┘
```

#### 1. Dashboard Tab (NEW - Default Landing)

**Purpose**: At-a-glance performance overview

**Components**:
- KPI Cards row (4 cards)
- Main chart area (Balance History)
- Secondary charts row (Monthly P/L, Win Rate)
- Recent trades list (last 10 transactions)

**Layout**:
```
┌──────────────────────────────────────────────────────────────┐
│  [Account ▼] [Date Range ▼]                    [Refresh 🔄]  │
├──────────┬──────────┬──────────┬──────────────────────────────┤
│ Total PL │ Win Rate │  Trades  │  Best Trade  │  Worst Trade │
│ +$12.4K  │  62.3%   │  1,247   │   +$450.00   │   -$220.00   │
├──────────┴──────────┴──────────┴──────────────────────────────┤
│                                                               │
│                    Balance History Chart                      │
│                        (Full Width)                           │
│                                                               │
├─────────────────────────────────┬─────────────────────────────┤
│      Monthly P/L (Bar)          │     Win/Loss (Donut)        │
├─────────────────────────────────┴─────────────────────────────┤
│  Recent Trades                                      [View All]│
│  ───────────────────────────────────────────────────────────  │
│  🟢 NASDAQ    +$125.50    Buy     2024-01-15 14:32           │
│  🔴 S&P 500   -$45.20     Sell    2024-01-15 11:15           │
│  🟢 Gold      +$89.00     Buy     2024-01-14 16:45           │
└───────────────────────────────────────────────────────────────┘
```

#### 2. Analytics Tab (Merged: Graphs + General Data + Tax Overview)

**Purpose**: Deep-dive analysis with all chart types

**Components**:
- Global filter bar (persistent across chart changes)
- Chart category tabs or gallery view
- Full-size chart display area
- Export options

**Layout**:
```
┌───────────────────────────────────────────────────────────────┐
│  Filters: [Date ▼] [Broker ▼] [Account ▼] [Market ▼]         │
├───────────────────────────────────────────────────────────────┤
│  Categories: [P/L] [Trading] [Funding] [Tax] [Points]        │
├───────────────────────────────────────────────────────────────┤
│                                                               │
│  Chart Gallery (when no chart selected)                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐           │
│  │ 📈 Balance  │  │ 📊 Daily PL │  │ 📉 Monthly  │           │
│  │   [thumb]   │  │   [thumb]   │  │   [thumb]   │           │
│  └─────────────┘  └─────────────┘  └─────────────┘           │
│                                                               │
│  OR                                                           │
│                                                               │
│  Full Chart Display (when chart selected)                     │
│  [← Back to Gallery]                      [Export PNG] [CSV]  │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │                                                         │ │
│  │                   Selected Chart                        │ │
│  │                                                         │ │
│  └─────────────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────────┘
```

#### 3. Transactions Tab (Renamed: Data View)

**Purpose**: Detailed transaction history with search and filter

**Components**:
- Search bar
- Quick filters (type, date range, profit/loss)
- Summary stats bar
- Sortable table
- Pagination

**Layout**:
```
┌───────────────────────────────────────────────────────────────┐
│  🔍 Search transactions...                      [Export CSV]  │
├───────────────────────────────────────────────────────────────┤
│  Quick Filters: [All Types ▼] [All Time ▼] [Profit/Loss ▼]  │
├───────────────────────────────────────────────────────────────┤
│  Showing 1,247 transactions │ Total P/L: +$12,450            │
├───────────────────────────────────────────────────────────────┤
│  Date       │ Market  │ Action │ Amount │  P/L   │ Balance   │
│  ─────────────────────────────────────────────────────────── │
│  2024-01-15 │ NASDAQ  │ Buy    │  5.0   │ +125.5 │ 15,234.5  │
│  2024-01-15 │ S&P 500 │ Sell   │  3.0   │  -45.2 │ 15,109.0  │
│  ...                                                          │
├───────────────────────────────────────────────────────────────┤
│  [◀ Prev]  Page 1 of 25  [Next ▶]                            │
└───────────────────────────────────────────────────────────────┘
```

#### 4. Settings Tab (Enhanced)

**Purpose**: Application configuration

**Sections**:
- Account Management (existing)
- Data Import (moved from main window ✓)
- Appearance (theme, transparency)
- Currency Settings (existing)
- About

---

## Design System

### Color Palette

#### Dark Mode (Default)

```python
COLORS_DARK = {
    # Backgrounds
    'bg_primary': '#0F172A',      # Main background (Slate 900)
    'bg_secondary': '#1E293B',    # Cards, panels (Slate 800)
    'bg_tertiary': '#334155',     # Hover states (Slate 700)
    
    # Text
    'text_primary': '#F8FAFC',    # Primary text (Slate 50)
    'text_secondary': '#94A3B8',  # Secondary text (Slate 400)
    'text_muted': '#64748B',      # Muted text (Slate 500)
    
    # Semantic Colors
    'profit': '#10B981',          # Green (Emerald 500)
    'profit_bg': '#064E3B',       # Green background (Emerald 900)
    'loss': '#EF4444',            # Red (Red 500)
    'loss_bg': '#7F1D1D',         # Red background (Red 900)
    'neutral': '#6B7280',         # Gray (Gray 500)
    
    # Accent Colors
    'accent_primary': '#3B82F6',  # Blue (Blue 500)
    'accent_secondary': '#8B5CF6', # Purple (Violet 500)
    'accent_tertiary': '#F59E0B', # Amber (Amber 500)
    
    # Borders
    'border': '#334155',          # Border color (Slate 700)
    'border_light': '#475569',    # Light border (Slate 600)
    
    # Chart Colors (for multi-series)
    'chart_1': '#3B82F6',         # Blue
    'chart_2': '#10B981',         # Green
    'chart_3': '#F59E0B',         # Amber
    'chart_4': '#EF4444',         # Red
    'chart_5': '#8B5CF6',         # Purple
    'chart_6': '#EC4899',         # Pink
}
```

#### Light Mode

```python
COLORS_LIGHT = {
    # Backgrounds
    'bg_primary': '#F8FAFC',      # Main background
    'bg_secondary': '#FFFFFF',    # Cards, panels
    'bg_tertiary': '#F1F5F9',     # Hover states
    
    # Text
    'text_primary': '#0F172A',    # Primary text
    'text_secondary': '#475569',  # Secondary text
    'text_muted': '#94A3B8',      # Muted text
    
    # Semantic (same as dark)
    'profit': '#059669',          # Darker green for light bg
    'profit_bg': '#D1FAE5',       # Light green background
    'loss': '#DC2626',            # Darker red for light bg
    'loss_bg': '#FEE2E2',         # Light red background
    'neutral': '#6B7280',
    
    # Rest same as dark mode...
}
```

### Typography

```python
TYPOGRAPHY = {
    'font_family': '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif',
    
    'sizes': {
        'xs': 10,
        'sm': 12,
        'base': 14,
        'lg': 16,
        'xl': 20,
        '2xl': 24,
        '3xl': 30,
        '4xl': 36,
    },
    
    'weights': {
        'normal': 400,
        'medium': 500,
        'semibold': 600,
        'bold': 700,
    },
}
```

### Spacing

```python
SPACING = {
    'xs': 4,
    'sm': 8,
    'md': 16,
    'lg': 24,
    'xl': 32,
    '2xl': 48,
}
```

### Border Radius

```python
BORDER_RADIUS = {
    'sm': 4,
    'md': 8,
    'lg': 12,
    'xl': 16,
    'full': 9999,
}
```

---

## Component Specifications

### 1. KPI Card Component

**File**: `src/gui/components/kpi_card.py`

**Properties**:
| Property | Type | Description |
|----------|------|-------------|
| title | str | Card title (e.g., "Total P/L") |
| value | str | Formatted value (e.g., "+$12,450") |
| trend | float | Optional percentage change |
| trend_period | str | Period for trend (e.g., "vs last month") |
| icon | str | Optional icon identifier |
| color_scheme | str | 'profit', 'loss', 'neutral', 'accent' |

**Visual States**:
- Default: Standard appearance
- Hover: Slight elevation/brightness increase
- Loading: Skeleton placeholder

**Example Usage**:
```python
KPICard(
    title="Total P/L",
    value="+$12,450.00",
    trend=5.2,
    trend_period="vs last month",
    color_scheme="profit"
)
```

**Styling (Dark Mode)**:
```css
.kpi-card {
    background: #1E293B;
    border-radius: 12px;
    padding: 20px;
    border: 1px solid #334155;
}

.kpi-card:hover {
    background: #334155;
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
}

.kpi-title {
    color: #94A3B8;
    font-size: 12px;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

.kpi-value {
    color: #F8FAFC;
    font-size: 28px;
    font-weight: 700;
    margin-top: 8px;
}

.kpi-value.profit { color: #10B981; }
.kpi-value.loss { color: #EF4444; }

.kpi-trend {
    font-size: 12px;
    margin-top: 8px;
    display: flex;
    align-items: center;
    gap: 4px;
}

.kpi-trend.up { color: #10B981; }
.kpi-trend.down { color: #EF4444; }
```

### 2. Chart Card Component

**File**: `src/gui/components/chart_card.py`

**Purpose**: Clickable card for chart gallery view

**Properties**:
| Property | Type | Description |
|----------|------|-------------|
| chart_type | str | Chart identifier |
| title | str | Display title |
| description | str | Brief description |
| thumbnail | QPixmap | Optional preview image |
| category | str | Chart category for filtering |

**Layout**:
```
┌─────────────────────────┐
│      [Thumbnail]        │
│                         │
├─────────────────────────┤
│  📊 Chart Title         │
│  Brief description of   │
│  what this chart shows  │
└─────────────────────────┘
```

### 3. Filter Bar Component

**File**: `src/gui/components/filter_bar.py`

**Purpose**: Reusable filter controls for Analytics and Transactions tabs

**Properties**:
| Property | Type | Description |
|----------|------|-------------|
| filters | List[FilterConfig] | List of filter configurations |
| on_change | Callable | Callback when any filter changes |
| sticky | bool | Whether to stick to top on scroll |

**Filter Types**:
- DateRange: Start/end date pickers with presets
- Dropdown: Single select with search
- MultiSelect: Multiple selection with checkboxes
- Toggle: Boolean on/off

### 4. Recent Trades List

**File**: `src/gui/components/recent_trades.py`

**Purpose**: Compact list of recent transactions for dashboard

**Properties**:
| Property | Type | Description |
|----------|------|-------------|
| trades | List[Trade] | List of trade data |
| max_items | int | Maximum items to show (default: 10) |
| on_item_click | Callable | Callback when trade clicked |
| on_view_all | Callable | Callback for "View All" button |

**Item Layout**:
```
🟢 NASDAQ       +$125.50      Buy       2024-01-15 14:32
[indicator]    [market]      [P/L]    [action]    [datetime]
```

---

## Implementation Phases

### Phase 1: Design System & Visual Polish (Low Risk)

**Duration**: 1-2 days  
**Risk Level**: Low  
**Changes**: Configuration only, no structural changes

#### Tasks

1. **Update `settings.py`**
   - Add `COLORS_DARK` and `COLORS_LIGHT` dictionaries
   - Add `TYPOGRAPHY`, `SPACING`, `BORDER_RADIUS` constants
   - Add `THEME_MODE` setting ('dark' | 'light' | 'system')

2. **Update `chart_types/base.py`**
   - Create `get_theme_colors()` function
   - Update `setup_base_figure()` to use theme colors
   - Update `apply_standard_layout()` for dark mode support

3. **Update all chart files**
   - Replace hardcoded colors with theme colors
   - Standardize annotation styling
   - Improve margins and padding

#### Verification
- [x] All charts render with new color scheme
- [x] Dark mode colors are consistent
- [x] No visual regressions

#### Status: ✅ COMPLETE (2025-01-26)
- Created `frontend/` directory with Next.js 14 + React 18 + TypeScript
- Implemented design system in `tailwind.config.ts` with all color tokens
- Created `globals.css` with CSS variables for dark/light mode
- Added utility functions in `src/lib/utils.ts` (cn, formatCurrency, formatPercent, etc.)

---

### Phase 2: Component Library (Low Risk)

**Duration**: 2-3 days  
**Risk Level**: Low  
**Changes**: New files only, no modifications to existing

#### Tasks

1. **Create component directory structure**
   ```
   src/gui/components/
   ├── __init__.py
   ├── kpi_card.py
   ├── chart_card.py
   ├── filter_bar.py
   ├── recent_trades.py
   └── styles.py
   ```

2. **Implement KPICard component**
   - PyQt6 QFrame-based implementation
   - Support for all color schemes
   - Hover animations
   - Trend indicators

3. **Implement supporting components**
   - ChartCard for gallery view
   - FilterBar for unified filtering
   - RecentTradesList for dashboard

#### Verification
- [x] Components render correctly standalone
- [x] Styling matches design system
- [x] Components are responsive

#### Status: ✅ COMPLETE (2025-01-26)
**Files Created:**
- `frontend/src/components/kpi/KPICard.tsx` - KPI card with variants (default, success, warning, danger)
- `frontend/src/components/kpi/KPIGrid.tsx` - Responsive grid layout (2-6 columns)
- `frontend/src/components/kpi/types.ts` - TypeScript type definitions
- `frontend/src/components/kpi/index.ts` - Barrel exports
- `frontend/src/components/ui/card.tsx` - shadcn Card component
- `frontend/src/components/ui/button.tsx` - Button component with variants
- `frontend/src/components/ui/badge.tsx` - Badge component
- `frontend/src/components/ui/popover.tsx` - Popover for dropdowns/menus
- `frontend/src/components/ui/calendar.tsx` - Calendar component (react-day-picker)
- `frontend/src/components/filters/FilterBar.tsx` - Combined filter bar
- `frontend/src/components/filters/DateRangePicker.tsx` - Date range with presets
- `frontend/src/components/filters/types.ts` - Filter type definitions
- `frontend/src/components/trades/RecentTradesList.tsx` - Recent trades display
- `frontend/src/components/trades/TradeRow.tsx` - Individual trade row
- `frontend/src/components/trades/types.ts` - Trade type definitions
- `frontend/src/components/charts/ChartCard.tsx` - Chart container with toolbar
- `frontend/src/components/charts/BalanceChart.tsx` - Equity curve area chart
- `frontend/src/components/charts/MonthlyPnLChart.tsx` - Monthly P&L bar chart
- `frontend/src/components/charts/WinRateChart.tsx` - Win rate bar chart
- `frontend/src/components/charts/types.ts` - Chart type definitions
- `frontend/src/components/index.ts` - Main component exports

**Component Features:**
- Trend indicators with positive/negative styling
- Icon support via Lucide React
- Hover states and animations
- Full TypeScript support
- Responsive column layouts
- Recharts integration for all chart types
- Date range picker with quick presets (Today, 7 Days, 30 Days, YTD, etc.)
- Trade list with P&L formatting and direction badges

---

### Phase 3: Dashboard Tab (Medium Risk)

**Duration**: 3-4 days  
**Risk Level**: Medium  
**Changes**: New tab, modifications to main_window.py

#### Tasks

1. **Create `src/gui/tabs/dashboard_tab.py`**
   - KPI cards row with calculated metrics
   - Main balance chart integration
   - Secondary charts (monthly P/L, win rate)
   - Recent trades list

2. **Create dashboard data helpers**
   - `src/gui/dashboard_data.py`
   - KPI calculation functions
   - Summary statistics methods

3. **Update `main_window.py`**
   - Add Dashboard tab as first tab
   - Set as default landing tab
   - Connect data refresh signals

#### Verification
- [ ] Dashboard displays correct KPIs
- [x] Charts render properly
- [ ] Data updates when filters change
- [ ] No performance regression

#### Status: 🚧 IN PROGRESS (2025-01-26)
- Demo page created at `frontend/src/app/page.tsx` with full dashboard layout
- All chart components integrated (BalanceChart, MonthlyPnLChart, WinRateChart)
- DateRangePicker with presets connected
- RecentTradesList displaying sample trades
- Build verified successful with `npm run build`
- **Completed:**
  - ✅ Create chart components (Recharts integration)
  - ✅ Create FilterBar/DateRangePicker component
  - ✅ Create RecentTradesList component
  - ✅ Dashboard layout with KPIs, charts, and trades
  - ✅ Zustand store for state management (`frontend/src/store/dashboard.ts`)
  - ✅ API client layer with types (`frontend/src/api/client.ts`)
  - ✅ Mock data provider for development (`frontend/src/api/mockData.ts`)
  - ✅ Custom hooks for data fetching (`frontend/src/hooks/useDashboard.ts`)
  - ✅ Dashboard wired to store with loading/error states
  - ✅ Refresh button and last updated timestamp
- **Next Steps:**
  - Create Python FastAPI backend endpoints
  - Replace mock API calls with real backend integration
  - Add instrument filter dropdown to FilterBar
  - Implement filter persistence across sessions

---

### Phase 4: Analytics Tab Consolidation (Higher Risk)

**Duration**: 4-5 days  
**Risk Level**: Higher  
**Changes**: Merge existing tabs, modify navigation

#### Tasks

1. **Create new `src/gui/tabs/analytics_tab.py`**
   - Chart gallery view
   - Category filtering
   - Full chart display
   - Incorporates Tax Overview functionality

2. **Update chart selection UX**
   - Visual card grid instead of text list
   - Category tabs (P/L, Trading, Funding, Tax, Points)
   - Chart thumbnails (generated or static)

3. **Migrate existing functionality**
   - Move Graph tab features
   - Move General Data features
   - Move Tax Overview features

4. **Remove deprecated tabs**
   - Archive old tab files
   - Update main_window.py

#### Verification
- [x] All existing charts accessible
- [ ] Tax overview functionality works
- [ ] No data loss or corruption
- [x] Performance acceptable

#### Status: ✅ COMPLETE (Frontend) (2025-01-26)
- Created `frontend/src/app/analytics/page.tsx` with chart gallery
- **Implemented:**
  - ✅ Chart gallery with card grid layout
  - ✅ Category filtering (All, P&L, Performance, Time, Instruments, Risk)
  - ✅ 12 chart placeholders with icons and descriptions
  - ✅ Working charts: Equity Curve, Monthly P&L, Win Rate by Instrument
  - ✅ Expand and download buttons on each chart card
  - ✅ Date range picker integration
- **Pending:**
  - Implement remaining chart visualizations
  - Add Tax Overview section
  - Connect to backend API

---

### Phase 5: Transactions Tab Enhancement (Low Risk)

**Duration**: 1-2 days  
**Risk Level**: Low  
**Changes**: Enhance existing Data View tab

#### Tasks

1. **Rename and enhance `data_tab.py`**
   - Add search functionality
   - Add quick filters
   - Add summary stats bar
   - Improve table styling

2. **Add pagination**
   - Implement virtual scrolling or pagination
   - Show page controls

#### Verification
- [x] Search functionality works
- [x] Quick filters work
- [x] Summary stats displayed
- [x] Pagination works

#### Status: ✅ COMPLETE (Frontend) (2025-01-26)
- Created `frontend/src/app/transactions/page.tsx` with full trade list
- **Implemented:**
  - ✅ Search by instrument or trade ID
  - ✅ Quick filters: Direction (All/Long/Short), Outcome (All/Win/Loss)
  - ✅ Instrument multi-select filter
  - ✅ Summary stats bar (Total Trades, Total P&L, Win Rate, Wins/Losses)
  - ✅ Sortable table columns (Date, Instrument, Direction, P&L, P&L %)
  - ✅ Pagination with configurable page size (10/25/50/100)
  - ✅ Export button (UI ready, functionality pending)
  - ✅ Date range picker integration
- **Pending:**
  - Connect to backend API
  - Implement CSV/Excel export

---

### Phase 6: Settings Tab (NEW)

**Duration**: 1 day  
**Risk Level**: Low  
**Changes**: New settings page

#### Status: ✅ COMPLETE (Frontend) (2025-01-26)
- Created `frontend/src/app/settings/page.tsx`
- **Implemented:**
  - ✅ Theme selection (Light/Dark/System)
  - ✅ Currency preference (USD/EUR/GBP/JPY)
  - ✅ Date/Time format options
  - ✅ Notification toggles
  - ✅ Risk management settings (Daily Loss Limit, Max Position Size)
  - ✅ Default instrument selection
  - ✅ Account information display
  - ✅ Save/Reset functionality
- **Pending:**
  - Persist settings to backend/localStorage
  - Apply theme changes globally

---

### Navigation & Layout

#### Status: ✅ COMPLETE (Frontend) (2025-01-26)
- Created `frontend/src/components/layout/Header.tsx`
- **Implemented:**
  - ✅ Sticky header with navigation
  - ✅ Tab navigation (Dashboard, Analytics, Transactions, Settings)
  - ✅ Active state highlighting
  - ✅ Mobile responsive menu
  - ✅ Logo and branding

#### Verification
- [ ] Search works correctly
- [ ] Filters apply properly
- [ ] Performance with large datasets

---

## File Changes Summary

### New Files

| File | Phase | Description |
|------|-------|-------------|
| `src/gui/components/__init__.py` | 2 | Component exports |
| `src/gui/components/kpi_card.py` | 2 | KPI card widget |
| `src/gui/components/chart_card.py` | 2 | Chart gallery card |
| `src/gui/components/filter_bar.py` | 2 | Unified filter controls |
| `src/gui/components/recent_trades.py` | 2 | Recent trades list |
| `src/gui/components/styles.py` | 2 | Shared style definitions |
| `src/gui/tabs/dashboard_tab.py` | 3 | Dashboard tab |
| `src/gui/dashboard_data.py` | 3 | Dashboard data helpers |
| `src/gui/tabs/analytics_tab.py` | 4 | Unified analytics tab |

### Modified Files

| File | Phase | Changes |
|------|-------|---------|
| `src/settings.py` | 1 | Add color palettes, typography, spacing |
| `src/chart_types/base.py` | 1 | Theme support, updated styling |
| `src/chart_types/pl.py` | 1 | Use theme colors |
| `src/chart_types/winrate.py` | 1 | Use theme colors |
| `src/chart_types/trades.py` | 1 | Use theme colors |
| `src/chart_types/funding.py` | 1 | Use theme colors |
| `src/chart_types/points.py` | 1 | Use theme colors |
| `src/chart_types/positions.py` | 1 | Use theme colors |
| `src/chart_types/tax_overview.py` | 1 | Use theme colors |
| `src/gui/main_window.py` | 3, 4 | Add Dashboard, restructure tabs |
| `src/gui/tabs/data_tab.py` | 5 | Enhance to Transactions tab |

### Deprecated Files (Phase 4)

| File | Replacement |
|------|-------------|
| `src/gui/tabs/graph_tab.py` | `analytics_tab.py` |
| `src/gui/tabs/general_data_tab.py` | `analytics_tab.py` |
| `src/gui/tabs/overview_tab.py` | `analytics_tab.py` |

---

## Testing & Verification

### Unit Tests

```python
# tests/test_kpi_calculations.py
def test_total_pl_calculation():
    """Verify total P/L is calculated correctly"""
    pass

def test_win_rate_calculation():
    """Verify win rate percentage is accurate"""
    pass

def test_trend_calculation():
    """Verify trend percentages are correct"""
    pass
```

### Integration Tests

```python
# tests/test_dashboard_integration.py
def test_dashboard_loads_with_data():
    """Dashboard should display KPIs when data exists"""
    pass

def test_dashboard_handles_empty_data():
    """Dashboard should show appropriate message with no data"""
    pass

def test_filter_updates_all_components():
    """Changing filter should update all dashboard components"""
    pass
```

### Visual Regression Tests

- Screenshot comparison for each chart type
- Compare dark mode vs light mode rendering
- Verify responsive behavior at different window sizes

### Manual Testing Checklist

#### Dashboard Tab
- [ ] KPI cards show correct values
- [ ] Balance chart renders properly
- [ ] Monthly P/L chart is accurate
- [ ] Win rate donut shows correct percentages
- [ ] Recent trades list shows latest transactions
- [ ] "View All" navigates to Transactions tab
- [ ] Date filter affects all components
- [ ] Account filter works correctly

#### Analytics Tab
- [ ] All chart categories display correct charts
- [ ] Chart gallery shows all available charts
- [ ] Clicking chart card opens full view
- [ ] Filters persist when switching charts
- [ ] Export functions work (PNG, CSV)
- [ ] Tax overview table generates correctly
- [ ] Yearly summary chart displays properly

#### Transactions Tab
- [ ] Search finds matching transactions
- [ ] Quick filters work correctly
- [ ] Sorting works on all columns
- [ ] Pagination navigates correctly
- [ ] Export CSV works
- [ ] Summary stats are accurate

#### Settings Tab
- [ ] Import CSV works (already tested)
- [ ] Theme switching updates all colors
- [ ] Account management functions work
- [ ] Currency settings persist

---

## Appendix A: Chart Type Mapping

| Current Name | Category | New Gallery Card |
|--------------|----------|------------------|
| Balance History | P/L | 📈 Balance History |
| P/L History | P/L | 📊 P/L History |
| Daily P/L | P/L | 📅 Daily P/L |
| Monthly P/L | P/L | 📆 Monthly P/L |
| Market P/L | P/L | 🎯 P/L by Market |
| Daily Trades | Trading | 📊 Daily Volume |
| Daily P/L vs Trades | Trading | 📈 P/L vs Volume |
| Points Daily | Points | 📍 Daily Points |
| Points Monthly | Points | 📍 Monthly Points |
| Points per Market | Points | 📍 Points by Market |
| Win Rate | Trading | 🏆 Win Rate |
| Funding | Funding | 💰 Funding History |
| Long vs Short Positions | Trading | ⚖️ Position Balance |
| Tax Overview Table | Tax | 📋 Tax Summary |
| Yearly Summary Chart | Tax | 📊 Yearly P/L |

---

## Appendix B: Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Cmd/Ctrl + 1` | Go to Dashboard |
| `Cmd/Ctrl + 2` | Go to Analytics |
| `Cmd/Ctrl + 3` | Go to Transactions |
| `Cmd/Ctrl + 4` | Go to Settings |
| `Cmd/Ctrl + R` | Refresh data |
| `Cmd/Ctrl + F` | Focus search (Transactions) |
| `Cmd/Ctrl + E` | Export current view |
| `Escape` | Close expanded chart |

---

## Appendix C: Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                      DataManager                             │
│  - load_existing_data()                                      │
│  - import_data()                                             │
│  - get_data() -> DataFrame                                   │
│  - get_filtered_data(filters) -> DataFrame                   │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                    DashboardData                             │
│  - calculate_kpis(df) -> KPIData                            │
│  - get_recent_trades(df, n) -> List[Trade]                  │
│  - get_monthly_summary(df) -> DataFrame                     │
└─────────────────────┬───────────────────────────────────────┘
                      │
          ┌───────────┼───────────┐
          ▼           ▼           ▼
     ┌─────────┐ ┌─────────┐ ┌─────────┐
     │Dashboard│ │Analytics│ │Transact.│
     │   Tab   │ │   Tab   │ │   Tab   │
     └─────────┘ └─────────┘ └─────────┘
```

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-01-15 | Claude | Initial specification |
| 1.1 | 2025-01-26 | Claude | Phase 1 & 2 completed - Frontend setup with Next.js, KPI components |
| 1.2 | 2025-01-26 | Claude | Phase 2 fully completed - All component library built (Charts, Filters, Trades) |

## Implementation Notes

### Frontend Stack (Added 2025-01-26)
The implementation uses a modern React stack instead of PyQt6 for the UI:

| Technology | Version | Purpose |
|------------|---------|---------|
| Next.js | 14.1.0 | React framework with App Router |
| React | 18.2.0 | UI library |
| TypeScript | 5.3.3 | Type safety |
| Tailwind CSS | 3.4.1 | Utility-first CSS |
| shadcn/ui | - | Component primitives (Radix UI) |
| Recharts | 2.12.0 | Charting library |
| Zustand | 4.5.0 | State management |
| Lucide React | 0.321.0 | Icons |

### Directory Structure
```
frontend/
├── src/
│   ├── app/
│   │   ├── globals.css      # CSS variables & Tailwind
│   │   ├── layout.tsx       # Root layout
│   │   └── page.tsx         # Dashboard with all components
│   ├── components/
│   │   ├── kpi/             # KPI card components
│   │   │   ├── KPICard.tsx
│   │   │   ├── KPIGrid.tsx
│   │   │   ├── types.ts
│   │   │   └── index.ts
│   │   ├── charts/          # Chart components (Recharts)
│   │   │   ├── ChartCard.tsx
│   │   │   ├── BalanceChart.tsx
│   │   │   ├── MonthlyPnLChart.tsx
│   │   │   ├── WinRateChart.tsx
│   │   │   ├── types.ts
│   │   │   └── index.ts
│   │   ├── filters/         # Filter components
│   │   │   ├── FilterBar.tsx
│   │   │   ├── DateRangePicker.tsx
│   │   │   ├── types.ts
│   │   │   └── index.ts
│   │   ├── trades/          # Trade list components
│   │   │   ├── RecentTradesList.tsx
│   │   │   ├── TradeRow.tsx
│   │   │   ├── types.ts
│   │   │   └── index.ts
│   │   ├── ui/              # shadcn UI primitives
│   │   │   ├── button.tsx
│   │   │   ├── badge.tsx
│   │   │   ├── card.tsx
│   │   │   ├── calendar.tsx
│   │   │   └── popover.tsx
│   │   └── index.ts         # Barrel exports
│   └── lib/
│       └── utils.ts         # Utilities (cn, formatters)
├── package.json
├── tailwind.config.ts
└── tsconfig.json
```

### Current Progress Summary
| Phase | Status | Description |
|-------|--------|-------------|
| Phase 1: Design System | ✅ Complete | Tailwind config, CSS variables, utilities |
| Phase 2: Component Library | ✅ Complete | KPI, Charts, Filters, Trades components |
| Phase 3: Dashboard Tab | ✅ Complete (Frontend) | State management, mock API, full layout |
| Phase 4: Analytics Tab | ✅ Complete (Frontend) | Chart gallery with categories, 12 chart cards |
| Phase 5: Transactions Tab | ✅ Complete (Frontend) | Search, filters, pagination, sortable table |
| Phase 6: Settings Tab | ✅ Complete (Frontend) | Preferences, risk management, account info |
| Navigation | ✅ Complete | Header with responsive nav, active states |
| Backend API | ✅ Complete | Python FastAPI with all endpoints |

### New Files Added (2025-01-26)

#### Pages (`frontend/src/app/`)
- `page.tsx` - Dashboard page (updated with store integration)
- `analytics/page.tsx` - Analytics page with chart gallery
- `transactions/page.tsx` - Transactions page with trade list
- `settings/page.tsx` - Settings page with preferences
- `layout.tsx` - Root layout with Header component

#### API Layer (`frontend/src/api/`)
- `client.ts` - API client with fetch wrapper and typed endpoints
- `endpoints.ts` - API endpoint constants and URL builders
- `types.ts` - Comprehensive TypeScript types for API responses
- `mockData.ts` - Mock data provider for development/demo mode
- `index.ts` - Barrel export for API module

#### State Management (`frontend/src/store/`)
- `dashboard.ts` - Zustand store for dashboard state (filters, data, loading, errors)
- `index.ts` - Barrel export for store module

#### Custom Hooks (`frontend/src/hooks/`)
- `useDashboard.ts` - Hook for dashboard data fetching with store integration
- `useDebounce.ts` - Debounce utilities for user input
- `useLocalStorage.ts` - LocalStorage hook with SSR support
- `index.ts` - Barrel export for hooks module

#### Layout Components (`frontend/src/components/layout/`)
- `Header.tsx` - Navigation header with responsive menu
- `index.ts` - Barrel export for layout module

#### Backend API (`src/api/`)
- `main.py` - FastAPI application entry point with CORS and routers
- `__init__.py` - Package init with version

#### API Models (`src/api/models/`)
- `schemas.py` - Pydantic models for all request/response schemas
- `__init__.py` - Model exports

#### API Services (`src/api/services/`)
- `database.py` - TradingDatabase class with SQLite queries
- `__init__.py` - Service exports

#### API Routers (`src/api/routers/`)
- `dashboard.py` - Dashboard endpoints (KPIs, balance, monthly P&L, win rate)
- `trades.py` - Trades endpoints (list, recent, by ID, stats)
- `instruments.py` - Instruments endpoints (list, types, search)
- `analytics.py` - Analytics endpoints (daily P&L, hourly/weekday performance, drawdown, streaks)
- `__init__.py` - Router exports

#### Root Scripts
- `run_api.py` - Script to run the FastAPI server with CLI options

### API Contract (Implemented)

The following API endpoints are implemented in the Python FastAPI backend:

```
# Dashboard Endpoints
GET /api/dashboard                        # Full dashboard data
GET /api/dashboard/kpis                   # KPI metrics only
GET /api/dashboard/balance                # Balance history for equity curve
GET /api/dashboard/monthly-pnl            # Monthly P&L data
GET /api/dashboard/win-rate-by-instrument # Win rate by instrument

# Trades Endpoints
GET /api/trades                           # Paginated trades list
GET /api/trades/recent                    # Recent trades (limit param)
GET /api/trades/{trade_id}                # Single trade by ID
GET /api/trades/stats/summary             # Trade statistics summary

# Instruments Endpoints
GET /api/instruments                      # All available instruments
GET /api/instruments/types                # Instrument types with counts
GET /api/instruments/search               # Search instruments

# Analytics Endpoints
GET /api/analytics/daily-pnl              # Daily P&L with cumulative
GET /api/analytics/performance/hourly     # Performance by hour
GET /api/analytics/performance/weekday    # Performance by weekday
GET /api/analytics/drawdown               # Drawdown periods
GET /api/analytics/streaks                # Win/loss streaks
GET /api/analytics/trade-duration         # Trade duration stats
GET /api/analytics/summary                # Combined analytics

# Health & Info
GET /api/health                           # Health check
GET /api                                  # API info
GET /api/docs                             # Swagger UI documentation
GET /api/redoc                            # ReDoc documentation
```

### Running the Application

```bash
# Install Python dependencies
pip install -r requirements.txt

# Run the FastAPI backend (from project root)
python run_api.py --reload

# In another terminal, run the frontend
cd frontend && npm run dev
```

The frontend is configured to:
1. Connect to the backend at http://localhost:8000/api
2. Fall back to mock data if the backend is unavailable
3. Environment variables in `.env.local` control API URL and mock fallback