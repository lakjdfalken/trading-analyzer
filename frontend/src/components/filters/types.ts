import { LucideIcon } from 'lucide-react';

export type DateRangePreset =
  | 'today'
  | 'yesterday'
  | 'last7days'
  | 'last30days'
  | 'thisMonth'
  | 'lastMonth'
  | 'thisQuarter'
  | 'lastQuarter'
  | 'thisYear'
  | 'lastYear'
  | 'allTime'
  | 'custom';

export interface DateRange {
  from: Date | undefined;
  to: Date | undefined;
  preset?: DateRangePreset;
}

export type TradeDirection = 'all' | 'long' | 'short';

export type TradeOutcome = 'all' | 'win' | 'loss' | 'breakeven';

export interface InstrumentOption {
  value: string;
  label: string;
  count?: number;
}

export interface FilterState {
  dateRange: DateRange;
  instruments: string[];
  direction: TradeDirection;
  outcome: TradeOutcome;
  minPnL?: number;
  maxPnL?: number;
  tags?: string[];
}

export interface FilterBarProps {
  filters: FilterState;
  onFiltersChange: (filters: FilterState) => void;
  instruments?: InstrumentOption[];
  tags?: string[];
  className?: string;
  showAdvanced?: boolean;
  loading?: boolean;
}

export interface DateRangePickerProps {
  dateRange: DateRange;
  onDateRangeChange: (range: DateRange) => void;
  className?: string;
}

export interface InstrumentFilterProps {
  selected: string[];
  onSelectionChange: (instruments: string[]) => void;
  options: InstrumentOption[];
  className?: string;
}

export interface QuickFilterProps {
  label: string;
  value: string;
  isActive: boolean;
  onClick: () => void;
  icon?: LucideIcon;
  count?: number;
}

export interface FilterChipProps {
  label: string;
  onRemove: () => void;
  variant?: 'default' | 'success' | 'warning' | 'danger';
}

export const DEFAULT_FILTER_STATE: FilterState = {
  dateRange: {
    from: undefined,
    to: undefined,
    preset: 'last30days',
  },
  instruments: [],
  direction: 'all',
  outcome: 'all',
};

export const DATE_RANGE_PRESETS: { value: DateRangePreset; label: string }[] = [
  { value: 'today', label: 'Today' },
  { value: 'yesterday', label: 'Yesterday' },
  { value: 'last7days', label: 'Last 7 Days' },
  { value: 'last30days', label: 'Last 30 Days' },
  { value: 'thisMonth', label: 'This Month' },
  { value: 'lastMonth', label: 'Last Month' },
  { value: 'thisQuarter', label: 'This Quarter' },
  { value: 'lastQuarter', label: 'Last Quarter' },
  { value: 'thisYear', label: 'This Year' },
  { value: 'lastYear', label: 'Last Year' },
  { value: 'allTime', label: 'All Time' },
  { value: 'custom', label: 'Custom Range' },
];
