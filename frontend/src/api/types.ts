// API Response Types

export interface ApiResponse<T> {
  data: T;
  status: 'success' | 'error';
  message?: string;
  timestamp: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
}

// Trade Types

export type TradeDirection = 'long' | 'short';
export type TradeStatus = 'open' | 'closed' | 'cancelled';

export interface Trade {
  id: string;
  instrument: string;
  direction: TradeDirection;
  status: TradeStatus;
  entryPrice: number;
  exitPrice?: number;
  entryTime: string; // ISO 8601
  exitTime?: string; // ISO 8601
  quantity: number;
  pnl?: number;
  pnlPercent?: number;
  commission?: number;
  swap?: number;
  notes?: string;
  tags?: string[];
}

export interface TradeFilters {
  instruments?: string[];
  direction?: TradeDirection;
  status?: TradeStatus;
  startDate?: string;
  endDate?: string;
  minPnl?: number;
  maxPnl?: number;
  tags?: string[];
}

// KPI Types

export interface KPIMetrics {
  totalPnl: number;
  totalPnlPercent: number;
  winRate: number;
  totalTrades: number;
  winningTrades: number;
  losingTrades: number;
  avgWin: number;
  avgLoss: number;
  profitFactor: number;
  maxDrawdown: number;
  maxDrawdownPercent: number;
  avgTradeDuration: number; // in minutes
  expectancy: number;
  sharpeRatio?: number;
  sortinoRatio?: number;
  recoveryFactor?: number;
}

export interface DailyStats {
  date: string;
  pnl: number;
  trades: number;
  winRate: number;
  balance: number;
}

export interface MonthlyStats {
  month: string;
  year: number;
  pnl: number;
  trades: number;
  winRate: number;
  avgTradePnl: number;
}

export interface InstrumentStats {
  instrument: string;
  totalTrades: number;
  winRate: number;
  wins: number;
  losses: number;
  totalPnl: number;
  avgPnl: number;
}

// Chart Data Types

export interface BalanceDataPoint {
  date: string;
  balance: number;
  equity?: number;
  drawdown?: number;
}

export interface PnLDataPoint {
  date: string;
  pnl: number;
  cumulativePnl: number;
}

// Dashboard Types

export interface DashboardData {
  kpis: KPIMetrics;
  balanceHistory: BalanceDataPoint[];
  monthlyStats: MonthlyStats[];
  instrumentStats: InstrumentStats[];
  recentTrades: Trade[];
  openPositions: Trade[];
  dailyStats: DailyStats;
}

export interface DashboardFilters {
  dateRange: {
    startDate: string;
    endDate: string;
  };
  instruments?: string[];
  preset?: string;
}

// Instrument Types

export interface Instrument {
  id: string;
  symbol: string;
  name: string;
  type: 'index' | 'forex' | 'commodity' | 'crypto' | 'stock';
  pipValue?: number;
  contractSize?: number;
  currency: string;
}

// Account Types

export interface AccountInfo {
  id: string;
  name: string;
  balance: number;
  equity: number;
  margin: number;
  freeMargin: number;
  currency: string;
  leverage: number;
  broker: string;
}

// API Request Types

export interface GetTradesRequest {
  filters?: TradeFilters;
  page?: number;
  pageSize?: number;
  sortBy?: keyof Trade;
  sortOrder?: 'asc' | 'desc';
}

export interface GetDashboardRequest {
  filters: DashboardFilters;
}

// API Error

export interface ApiError {
  code: string;
  message: string;
  details?: Record<string, unknown>;
}
