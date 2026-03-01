"use client";

import * as React from "react";
import { useCurrencyStore } from "@/store/currency";
import { useSettingsStore } from "@/store/settings";
import { useDashboardStore, type DateRangePreset } from "@/store/dashboard";
import * as api from "@/lib/api";
import type { PointsData } from "@/components/charts/PointsChart";
import type { AccountSeries } from "@/components/charts/MultiAccountBalanceChart";
import type { AccountPnLSeries } from "@/components/charts/MultiAccountMonthlyPnLChart";
import type { AccountPnLSeries as CumulativePnLAccountSeries } from "@/components/charts/MultiAccountCumulativePnLChart";
import type {
  AnalyticsDataState,
  BalanceByAccountData,
  MonthlyPnLByAccountData,
  DailyPnLEntry,
  DailyPnLByAccountData,
  HourlyPerformanceEntry,
  WeekdayPerformanceEntry,
  StreakDataEntry,
  TradeDurationEntry,
  PositionSizeEntry,
  FundingDataEntry,
  EquityCurveEntry,
} from "./types";
import { INITIAL_ANALYTICS_STATE } from "./types";

export interface UseAnalyticsDataReturn extends AnalyticsDataState {
  // Shared dashboard store state
  dateRange: { from: Date | undefined; to: Date | undefined; preset: string };
  balanceHistory: api.BalanceDataPoint[];
  monthlyPnL: api.MonthlyPnLDataPoint[];
  winRateByInstrument: api.WinRateByInstrument[];
  loading: { dashboard: boolean };
  selectedAccountId: number | null;
  availableAccounts: api.Account[];
  isInitialized: boolean;

  // Derived state
  effectiveCurrency: string | undefined;
  displayCurrency: string;
  currencyNotSet: boolean;
  formatAmount: (amount: number, currency: string) => string;

  // Actions
  fetchData: () => Promise<void>;
  setSelectedAccountId: (id: number | null) => void;
  setDateRange: (range: {
    from?: Date;
    to?: Date;
    preset?: DateRangePreset;
  }) => void;
}

export function useAnalyticsData(): UseAnalyticsDataReturn {
  const { formatAmount } = useCurrencyStore();
  const { defaultCurrency, isLoaded: settingsLoaded } = useSettingsStore();

  const [hasHydrated, setHasHydrated] = React.useState(false);
  const [hasFetchedOnce, setHasFetchedOnce] = React.useState(false);

  // Analytics-specific data states
  const [balanceByAccount, setBalanceByAccount] =
    React.useState<BalanceByAccountData | null>(null);
  const [monthlyPnLByAccount, setMonthlyPnLByAccount] =
    React.useState<MonthlyPnLByAccountData | null>(null);
  const [dailyPnL, setDailyPnL] = React.useState<DailyPnLEntry[]>([]);
  const [dailyPnLByAccount, setDailyPnLByAccount] =
    React.useState<DailyPnLByAccountData | null>(null);
  const [hourlyPerformance, setHourlyPerformance] = React.useState<
    HourlyPerformanceEntry[]
  >([]);
  const [weekdayPerformance, setWeekdayPerformance] = React.useState<
    WeekdayPerformanceEntry[]
  >([]);
  const [streakData, setStreakData] = React.useState<StreakDataEntry | null>(
    null,
  );
  const [tradeDuration, setTradeDuration] =
    React.useState<TradeDurationEntry | null>(null);
  const [positionSizeData, setPositionSizeData] =
    React.useState<PositionSizeEntry | null>(null);
  const [fundingData, setFundingData] = React.useState<FundingDataEntry>(
    INITIAL_ANALYTICS_STATE.fundingData,
  );
  const [equityCurve, setEquityCurve] = React.useState<EquityCurveEntry[]>([]);
  const [pointsByInstrument, setPointsByInstrument] = React.useState<
    PointsData[]
  >([]);
  const [spreadCostData, setSpreadCostData] =
    React.useState<api.SpreadCostResponse | null>(null);
  const [tradeFrequencyData, setTradeFrequencyData] =
    React.useState<api.TradeFrequencyResponse | null>(null);
  const [dataCurrency, setDataCurrency] = React.useState<string | null>(null);

  // Dashboard store
  const {
    dateRange,
    balanceHistory,
    monthlyPnL,
    winRateByInstrument,
    loading,
    selectedAccountId,
    availableAccounts,
    setDateRange,
    setBalanceHistory,
    setMonthlyPnL,
    setWinRateByInstrument,
    setLoading,
    setSelectedAccountId,
    setAvailableAccounts,
    isInitialized,
    setInitialized,
  } = useDashboardStore();

  // Determine effective currency
  const selectedAccount = availableAccounts.find(
    (a) => a.account_id === selectedAccountId,
  );
  const effectiveCurrency = selectedAccountId
    ? selectedAccount?.currency || defaultCurrency
    : defaultCurrency;

  const displayCurrency = dataCurrency || effectiveCurrency || "";
  const currencyNotSet = !displayCurrency;

  // Wait for Zustand store to hydrate
  React.useEffect(() => {
    setHasHydrated(true);
  }, []);

  // Build date range for API
  const getDateRangeForApi = React.useCallback(() => {
    return {
      from: dateRange.from,
      to: dateRange.to,
    };
  }, [dateRange.from, dateRange.to]);

  // Main data fetching function
  const fetchData = React.useCallback(async () => {
    if (!effectiveCurrency) return;

    setLoading("dashboard", true);
    try {
      const dateRangeParam = getDateRangeForApi();

      const [
        balanceResult,
        monthlyResult,
        winRateResult,
        balanceByAccResult,
        monthlyByAccResult,
        dailyPnLResult,
        dailyPnLByAccResult,
        hourlyResult,
        weekdayResult,
        streakResult,
        durationResult,
        positionSizeResult,
        fundingResult,
        equityCurveResult,
        pointsResult,
        spreadCostResult,
        tradeFrequencyResult,
        accountsResult,
      ] = await Promise.allSettled([
        api.getBalanceHistory(
          effectiveCurrency,
          dateRangeParam,
          selectedAccountId,
        ),
        api.getMonthlyPnL(
          effectiveCurrency,
          dateRangeParam,
          undefined,
          selectedAccountId,
        ),
        api.getWinRateByInstrument(dateRangeParam, selectedAccountId),
        api.getBalanceByAccount(
          effectiveCurrency,
          dateRangeParam,
          selectedAccountId,
        ),
        api.getMonthlyPnLByAccount(
          effectiveCurrency,
          dateRangeParam,
          selectedAccountId,
        ),
        api.getDailyPnL(effectiveCurrency, dateRangeParam, selectedAccountId),
        api.getDailyPnLByAccount(
          effectiveCurrency,
          dateRangeParam,
          selectedAccountId,
        ),
        api.getHourlyPerformance(
          effectiveCurrency,
          dateRangeParam,
          selectedAccountId,
        ),
        api.getWeekdayPerformance(
          effectiveCurrency,
          dateRangeParam,
          selectedAccountId,
        ),
        api.getStreaks(dateRangeParam, selectedAccountId),
        api.getTradeDuration(dateRangeParam, selectedAccountId),
        api.getPositionSize(
          effectiveCurrency,
          dateRangeParam,
          selectedAccountId,
        ),
        api.getFunding(effectiveCurrency, dateRangeParam, selectedAccountId),
        api.getEquityCurve(
          effectiveCurrency,
          dateRangeParam,
          selectedAccountId,
        ),
        api.getPointsByInstrument(
          effectiveCurrency,
          dateRangeParam,
          selectedAccountId,
        ),
        api.getSpreadCost(effectiveCurrency, dateRangeParam, selectedAccountId),
        api.getTradeFrequency(dateRangeParam, selectedAccountId),
        api.getAccounts(),
      ]);

      // Process balance history
      if (balanceResult.status === "fulfilled") {
        const response = balanceResult.value as
          | api.BalanceDataPoint[]
          | { data?: api.BalanceDataPoint[]; currency?: string };
        const balanceData = Array.isArray(response)
          ? response
          : response.data || [];
        setBalanceHistory(balanceData);
        if (!Array.isArray(response) && response.currency) {
          setDataCurrency(response.currency);
        }
      }

      // Process monthly P&L
      if (monthlyResult.status === "fulfilled") {
        const response = monthlyResult.value as
          | api.MonthlyPnLDataPoint[]
          | { data?: api.MonthlyPnLDataPoint[]; currency?: string };
        const monthlyData = Array.isArray(response)
          ? response
          : response.data || [];
        setMonthlyPnL(monthlyData);
        if (!Array.isArray(response) && response.currency) {
          setDataCurrency(response.currency);
        }
      }

      // Process win rate
      if (winRateResult.status === "fulfilled") {
        setWinRateByInstrument(winRateResult.value);
      }

      // Process balance by account
      if (balanceByAccResult.status === "fulfilled") {
        setBalanceByAccount(balanceByAccResult.value as BalanceByAccountData);
      }

      // Process monthly P&L by account
      if (monthlyByAccResult.status === "fulfilled") {
        setMonthlyPnLByAccount(
          monthlyByAccResult.value as MonthlyPnLByAccountData,
        );
      }

      // Process daily P&L
      if (dailyPnLResult.status === "fulfilled") {
        setDailyPnL(dailyPnLResult.value);
      }

      // Process daily P&L by account
      if (dailyPnLByAccResult.status === "fulfilled") {
        setDailyPnLByAccount(
          dailyPnLByAccResult.value as DailyPnLByAccountData,
        );
      }

      // Process hourly performance
      if (hourlyResult.status === "fulfilled") {
        setHourlyPerformance(hourlyResult.value as HourlyPerformanceEntry[]);
      }

      // Process weekday performance
      if (weekdayResult.status === "fulfilled") {
        setWeekdayPerformance(weekdayResult.value as WeekdayPerformanceEntry[]);
      }

      // Process streak data
      if (streakResult.status === "fulfilled") {
        setStreakData(streakResult.value as StreakDataEntry);
      }

      // Process trade duration
      if (durationResult.status === "fulfilled") {
        setTradeDuration(durationResult.value as TradeDurationEntry);
      }

      // Process position size
      if (positionSizeResult.status === "fulfilled") {
        setPositionSizeData(positionSizeResult.value as PositionSizeEntry);
      }

      // Process funding data
      if (fundingResult.status === "fulfilled") {
        setFundingData(fundingResult.value as FundingDataEntry);
      }

      // Process equity curve
      if (equityCurveResult.status === "fulfilled") {
        const response = equityCurveResult.value as
          | api.BalanceDataPoint[]
          | { data?: api.BalanceDataPoint[] };
        const equityData = Array.isArray(response)
          ? response
          : response.data || [];
        setEquityCurve(equityData);
      }

      // Process points by instrument
      if (pointsResult.status === "fulfilled" && pointsResult.value) {
        setPointsByInstrument(
          Array.isArray(pointsResult.value)
            ? pointsResult.value
            : [pointsResult.value],
        );
      }

      // Process spread cost data
      if (spreadCostResult.status === "fulfilled") {
        setSpreadCostData(spreadCostResult.value as api.SpreadCostResponse);
      }

      // Process trade frequency data
      if (tradeFrequencyResult.status === "fulfilled") {
        setTradeFrequencyData(
          tradeFrequencyResult.value as api.TradeFrequencyResponse,
        );
      }

      // Process accounts
      if (accountsResult.status === "fulfilled") {
        setAvailableAccounts(accountsResult.value);
      }

      setInitialized(true);
    } finally {
      setLoading("dashboard", false);
    }
  }, [
    effectiveCurrency,
    selectedAccountId,
    getDateRangeForApi,
    setLoading,
    setBalanceHistory,
    setMonthlyPnL,
    setWinRateByInstrument,
    setAvailableAccounts,
    setInitialized,
  ]);

  // Initial fetch after hydration and settings load
  React.useEffect(() => {
    if (hasHydrated && settingsLoaded && !hasFetchedOnce) {
      setHasFetchedOnce(true);
      fetchData();
    }
  }, [hasHydrated, settingsLoaded, hasFetchedOnce, fetchData]);

  // Refetch when date range or account changes (after initial load)
  React.useEffect(() => {
    if (hasFetchedOnce && hasHydrated) {
      fetchData();
    }
  }, [
    dateRange.from,
    dateRange.to,
    selectedAccountId,
    hasFetchedOnce,
    hasHydrated,
    fetchData,
  ]);

  return {
    // Analytics-specific data
    balanceByAccount,
    monthlyPnLByAccount,
    dailyPnL,
    dailyPnLByAccount,
    equityCurve,
    hourlyPerformance,
    weekdayPerformance,
    streakData,
    tradeDuration,
    pointsByInstrument,
    positionSizeData,
    fundingData,
    spreadCostData,
    tradeFrequencyData,
    dataCurrency,

    // Dashboard store state
    dateRange,
    balanceHistory,
    monthlyPnL,
    winRateByInstrument,
    loading,
    selectedAccountId,
    availableAccounts,
    isInitialized,

    // Derived state
    effectiveCurrency,
    displayCurrency,
    currencyNotSet,
    formatAmount,

    // Actions
    fetchData,
    setSelectedAccountId,
    setDateRange,
  };
}
