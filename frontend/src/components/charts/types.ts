import { LucideIcon } from 'lucide-react';

export type ChartType =
  | 'line'
  | 'area'
  | 'bar'
  | 'pie'
  | 'donut'
  | 'scatter'
  | 'composed'
  | 'candlestick';

export type ChartTimeframe =
  | '1D'
  | '1W'
  | '1M'
  | '3M'
  | '6M'
  | '1Y'
  | 'YTD'
  | 'ALL';

export type ChartInterval = 'minute' | 'hour' | 'day' | 'week' | 'month';

export interface ChartDataPoint {
  date: string | Date;
  value: number;
  [key: string]: unknown;
}

export interface ChartSeries {
  id: string;
  name: string;
  data: ChartDataPoint[];
  color?: string;
  type?: ChartType;
  yAxisId?: string;
  hidden?: boolean;
}

export interface ChartAxis {
  id: string;
  label?: string;
  position?: 'left' | 'right' | 'top' | 'bottom';
  domain?: [number | 'auto' | 'dataMin' | 'dataMax', number | 'auto' | 'dataMin' | 'dataMax'];
  tickFormatter?: (value: number) => string;
  hide?: boolean;
}

export interface ChartTooltipProps {
  active?: boolean;
  payload?: Array<{
    name: string;
    value: number;
    color: string;
    dataKey: string;
  }>;
  label?: string;
}

export interface ChartLegendItem {
  id: string;
  name: string;
  color: string;
  hidden?: boolean;
}

export interface BaseChartProps {
  data: ChartDataPoint[] | ChartSeries[];
  height?: number | string;
  width?: number | string;
  className?: string;
  loading?: boolean;
  error?: string;
  emptyMessage?: string;
  showGrid?: boolean;
  showLegend?: boolean;
  showTooltip?: boolean;
  animate?: boolean;
}

export interface LineChartProps extends BaseChartProps {
  type?: 'linear' | 'monotone' | 'step';
  dot?: boolean;
  strokeWidth?: number;
  fill?: boolean;
  colors?: string[];
}

export interface AreaChartProps extends BaseChartProps {
  type?: 'linear' | 'monotone' | 'step';
  stackOffset?: 'none' | 'expand' | 'wiggle' | 'silhouette';
  gradient?: boolean;
  colors?: string[];
}

export interface BarChartProps extends BaseChartProps {
  layout?: 'horizontal' | 'vertical';
  stacked?: boolean;
  barSize?: number;
  barGap?: number;
  colors?: string[];
}

export interface PieChartProps extends BaseChartProps {
  innerRadius?: number | string;
  outerRadius?: number | string;
  paddingAngle?: number;
  colors?: string[];
  showLabels?: boolean;
  labelType?: 'percent' | 'value' | 'name';
}

// Trading-specific chart types
export interface EquityCurveData {
  date: string;
  equity: number;
  drawdown?: number;
  benchmark?: number;
}

export interface MonthlyPnLData {
  month: string;
  pnl: number;
  trades: number;
  winRate?: number;
}

export interface WinRateByInstrumentData {
  instrument: string;
  wins: number;
  losses: number;
  winRate: number;
  totalPnl: number;
}

export interface TradeDistributionData {
  range: string;
  count: number;
  percentage: number;
}

export interface DayOfWeekData {
  day: string;
  trades: number;
  pnl: number;
  winRate: number;
}

export interface HourlyData {
  hour: number;
  trades: number;
  pnl: number;
  winRate: number;
}

export interface DrawdownData {
  date: string;
  drawdown: number;
  equity: number;
  peak: number;
}

export interface CumulativePnLData {
  date: string;
  cumulativePnl: number;
  dailyPnl?: number;
}

// Chart card for gallery view
export interface ChartCardData {
  id: string;
  title: string;
  description?: string;
  type: ChartType;
  thumbnail?: string;
  data: ChartDataPoint[];
  lastUpdated?: Date;
}

export interface ChartCardProps {
  chart: ChartCardData;
  onClick?: (chart: ChartCardData) => void;
  selected?: boolean;
  className?: string;
}

export interface ChartGalleryProps {
  charts: ChartCardData[];
  onChartSelect?: (chart: ChartCardData) => void;
  selectedChartId?: string;
  columns?: 2 | 3 | 4;
  className?: string;
  loading?: boolean;
}

// Chart container with header, controls, and footer
export interface ChartContainerProps {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
  timeframe?: ChartTimeframe;
  onTimeframeChange?: (timeframe: ChartTimeframe) => void;
  actions?: React.ReactNode;
  loading?: boolean;
  error?: string;
  className?: string;
  fullscreen?: boolean;
  onFullscreenToggle?: () => void;
}

// Color palettes
export const CHART_COLORS = {
  primary: [
    'hsl(var(--primary))',
    'hsl(221, 83%, 53%)',
    'hsl(250, 95%, 64%)',
    'hsl(280, 87%, 65%)',
    'hsl(330, 81%, 60%)',
  ],
  profit: 'hsl(142, 76%, 36%)',
  loss: 'hsl(0, 84%, 60%)',
  neutral: 'hsl(var(--muted-foreground))',
  grid: 'hsl(var(--border))',
  background: 'hsl(var(--background))',
  foreground: 'hsl(var(--foreground))',
} as const;

export const TIMEFRAME_OPTIONS: { value: ChartTimeframe; label: string }[] = [
  { value: '1D', label: '1 Day' },
  { value: '1W', label: '1 Week' },
  { value: '1M', label: '1 Month' },
  { value: '3M', label: '3 Months' },
  { value: '6M', label: '6 Months' },
  { value: '1Y', label: '1 Year' },
  { value: 'YTD', label: 'Year to Date' },
  { value: 'ALL', label: 'All Time' },
];

export const DEFAULT_CHART_HEIGHT = 300;
export const DEFAULT_CHART_MARGIN = { top: 10, right: 30, left: 0, bottom: 0 };
