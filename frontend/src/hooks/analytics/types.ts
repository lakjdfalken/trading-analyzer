import type { PointsData } from "@/components/charts/PointsChart";
import type { AccountSeries } from "@/components/charts/MultiAccountBalanceChart";
import type { AccountPnLSeries } from "@/components/charts/MultiAccountMonthlyPnLChart";
import type { AccountPnLSeries as CumulativePnLAccountSeries } from "@/components/charts/MultiAccountCumulativePnLChart";
import type * as api from "@/lib/api";

// ============================================================================
// Analytics Data State Types
// ============================================================================

export interface DailyPnLEntry {
  date: string;
  pnl: number;
  cumulativePnl: number;
  trades: number;
  previousBalance?: number | null;
  pnlPercent?: number | null;
}

export interface DailyPnLByAccountData {
  series: CumulativePnLAccountSeries[];
  total?: {
    accountName: string;
    currency?: string;
    data: Array<{
      date: string;
      pnl: number;
      trades: number;
      cumulativePnl: number;
    }>;
  };
}

export interface HourlyPerformanceEntry {
  hour: number;
  pnl: number;
  trades: number;
  winRate: number;
}

export interface WeekdayPerformanceEntry {
  weekday: string;
  pnl: number;
  trades: number;
  winRate: number;
}

export interface StreakDataEntry {
  currentStreak: number;
  currentStreakType: "win" | "loss" | "none";
  maxWinStreak: number;
  maxLossStreak: number;
  avgWinStreak: number;
  avgLossStreak: number;
}

export interface TradeDurationEntry {
  avgDurationMinutes: number;
  minDurationMinutes: number;
  maxDurationMinutes: number;
  avgWinnerDuration: number;
  avgLoserDuration: number;
}

export interface SizeDistributionEntry {
  range: string;
  rangeMin: number;
  rangeMax: number;
  count: number;
  totalPnL: number;
  avgPnL: number;
}

export interface PositionSizeEntry {
  avgPositionSize: number;
  minPositionSize: number;
  maxPositionSize: number;
  avgWinnerSize: number;
  avgLoserSize: number;
  sizeDistribution: SizeDistributionEntry[];
  sizePnLCorrelation: Array<{ size: number; pnl: number }>;
}

export interface FundingDailyEntry {
  date: string;
  deposits: number;
  withdrawals: number;
  funding_charges: number;
  net: number;
  cumulative: number;
}

export interface FundingChargeByMarket {
  market: string;
  total_charges: number;
  count: number;
}

export interface FundingDataEntry {
  daily: FundingDailyEntry[];
  charges_by_market: FundingChargeByMarket[];
  total_funding_charges: number;
}

export interface EquityCurveEntry {
  date: string;
  balance: number;
  drawdown?: number;
}

export interface BalanceByAccountData {
  series: AccountSeries[];
  total: {
    accountName: string;
    data: Array<{ date: string; balance: number }>;
  };
}

export interface MonthlyPnLByAccountData {
  series: AccountPnLSeries[];
  total: {
    accountName: string;
    data: Array<{
      month: string;
      pnl: number;
      trades?: number;
      winRate?: number;
    }>;
  };
}

// ============================================================================
// Complete Analytics Data State
// ============================================================================

export interface AnalyticsDataState {
  // Multi-account data
  balanceByAccount: BalanceByAccountData | null;
  monthlyPnLByAccount: MonthlyPnLByAccountData | null;

  // P&L data
  dailyPnL: DailyPnLEntry[];
  dailyPnLByAccount: DailyPnLByAccountData | null;
  equityCurve: EquityCurveEntry[];

  // Performance data
  hourlyPerformance: HourlyPerformanceEntry[];
  weekdayPerformance: WeekdayPerformanceEntry[];
  streakData: StreakDataEntry | null;
  tradeDuration: TradeDurationEntry | null;

  // Instrument data
  pointsByInstrument: PointsData[];

  // Risk data
  positionSizeData: PositionSizeEntry | null;
  fundingData: FundingDataEntry;
  spreadCostData: api.SpreadCostResponse | null;

  // Frequency data
  tradeFrequencyData: api.TradeFrequencyResponse | null;

  // Currency tracking
  dataCurrency: string | null;
}

export const INITIAL_ANALYTICS_STATE: AnalyticsDataState = {
  balanceByAccount: null,
  monthlyPnLByAccount: null,
  dailyPnL: [],
  dailyPnLByAccount: null,
  equityCurve: [],
  hourlyPerformance: [],
  weekdayPerformance: [],
  streakData: null,
  tradeDuration: null,
  pointsByInstrument: [],
  positionSizeData: null,
  fundingData: { daily: [], charges_by_market: [], total_funding_charges: 0 },
  spreadCostData: null,
  tradeFrequencyData: null,
  dataCurrency: null,
};
