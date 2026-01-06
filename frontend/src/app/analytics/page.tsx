"use client";

import * as React from "react";
import {
  TrendingUp,
  TrendingDown,
  DollarSign,
  Calendar,
  Target,
  PieChart,
  BarChart3,
  LineChart,
  Activity,
  Clock,
  Percent,
  Wallet,
  Filter,
  Maximize2,
  Download,
} from "lucide-react";

import { cn } from "@/lib/utils";
import { useCurrencyStore } from "@/store/currency";
import { useSettingsStore } from "@/store/settings";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ChartCard } from "@/components/charts/ChartCard";
import { BalanceChart } from "@/components/charts/BalanceChart";
import { MonthlyPnLChart } from "@/components/charts/MonthlyPnLChart";
import { WinRateChart } from "@/components/charts/WinRateChart";
import { ExpandedChartModal } from "@/components/charts/ExpandedChartModal";
import { MultiAccountBalanceChart } from "@/components/charts/MultiAccountBalanceChart";
import { MultiAccountMonthlyPnLChart } from "@/components/charts/MultiAccountMonthlyPnLChart";
import { DailyPnLChart } from "@/components/charts/DailyPnLChart";
import { DrawdownChart } from "@/components/charts/DrawdownChart";
import { HourlyPerformanceChart } from "@/components/charts/HourlyPerformanceChart";
import { WeekdayPerformanceChart } from "@/components/charts/WeekdayPerformanceChart";
import { StreakChart } from "@/components/charts/StreakChart";
import { TradeDurationChart } from "@/components/charts/TradeDurationChart";
import { CumulativePnLChart } from "@/components/charts/CumulativePnLChart";
import { MultiAccountCumulativePnLChart } from "@/components/charts/MultiAccountCumulativePnLChart";
import type { AccountPnLSeries as CumulativePnLAccountSeries } from "@/components/charts/MultiAccountCumulativePnLChart";
import { PositionSizeChart } from "@/components/charts/PositionSizeChart";
import { FundingChart } from "@/components/charts/FundingChart";
import { SpreadCostChart } from "@/components/charts/SpreadCostChart";
import { TradeFrequencyChart } from "@/components/charts/TradeFrequencyChart";
import { PointsChart } from "@/components/charts/PointsChart";
import type { PointsData } from "@/components/charts/PointsChart";
import type { AccountSeries } from "@/components/charts/MultiAccountBalanceChart";
import type { AccountPnLSeries } from "@/components/charts/MultiAccountMonthlyPnLChart";
import { DateRangePicker } from "@/components/filters/DateRangePicker";
import { useDashboardStore } from "@/store/dashboard";
import type { DateRangePreset } from "@/components/filters/types";
import * as api from "@/lib/api";

// Chart category types
type ChartCategory =
  | "all"
  | "pnl"
  | "performance"
  | "time"
  | "instruments"
  | "risk";

interface ChartDefinition {
  id: string;
  title: string;
  description: string;
  category: ChartCategory;
  icon: React.ElementType;
  component: React.ReactNode;
}

export default function AnalyticsPage() {
  const [selectedCategory, setSelectedCategory] =
    React.useState<ChartCategory>("all");
  const [expandedChart, setExpandedChart] = React.useState<string | null>(null);
  const [dataCurrency, setDataCurrency] = React.useState<string | null>(null);
  const [hasHydrated, setHasHydrated] = React.useState(false);
  const [hasFetchedOnce, setHasFetchedOnce] = React.useState(false);
  const { formatAmount } = useCurrencyStore();
  const { defaultCurrency, isLoaded: settingsLoaded } = useSettingsStore();

  // Multi-account data state
  const [balanceByAccount, setBalanceByAccount] = React.useState<{
    series: AccountSeries[];
    total: {
      accountName: string;
      data: Array<{ date: string; balance: number }>;
    };
  } | null>(null);
  const [monthlyPnLByAccount, setMonthlyPnLByAccount] = React.useState<{
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
  } | null>(null);

  // New analytics data states
  const [dailyPnL, setDailyPnL] = React.useState<
    Array<{
      date: string;
      pnl: number;
      cumulativePnl: number;
      trades: number;
      previousBalance?: number | null;
      pnlPercent?: number | null;
    }>
  >([]);
  const [dailyPnLByAccount, setDailyPnLByAccount] = React.useState<{
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
  } | null>(null);

  const [hourlyPerformance, setHourlyPerformance] = React.useState<
    Array<{ hour: number; pnl: number; trades: number; winRate: number }>
  >([]);
  const [weekdayPerformance, setWeekdayPerformance] = React.useState<
    Array<{ weekday: string; pnl: number; trades: number; winRate: number }>
  >([]);
  const [streakData, setStreakData] = React.useState<{
    currentStreak: number;
    currentStreakType: "win" | "loss" | "none";
    maxWinStreak: number;
    maxLossStreak: number;
    avgWinStreak: number;
    avgLossStreak: number;
  } | null>(null);
  const [tradeDuration, setTradeDuration] = React.useState<{
    avgDurationMinutes: number;
    minDurationMinutes: number;
    maxDurationMinutes: number;
    avgWinnerDuration: number;
    avgLoserDuration: number;
  } | null>(null);
  const [positionSizeData, setPositionSizeData] = React.useState<{
    avgPositionSize: number;
    minPositionSize: number;
    maxPositionSize: number;
    avgWinnerSize: number;
    avgLoserSize: number;
    sizeDistribution: Array<{
      range: string;
      rangeMin: number;
      rangeMax: number;
      count: number;
      totalPnL: number;
      avgPnL: number;
    }>;
    sizePnLCorrelation: Array<{ size: number; pnl: number }>;
  } | null>(null);

  const [fundingData, setFundingData] = React.useState<
    Array<{
      date: string;
      deposits: number;
      withdrawals: number;
      net: number;
      cumulative: number;
    }>
  >([]);
  const [equityCurve, setEquityCurve] = React.useState<
    Array<{ date: string; balance: number; drawdown?: number }>
  >([]);

  const [pointsByInstrument, setPointsByInstrument] = React.useState<
    PointsData[]
  >([]);

  const [spreadCostData, setSpreadCostData] =
    React.useState<api.SpreadCostResponse | null>(null);

  const [tradeFrequencyData, setTradeFrequencyData] =
    React.useState<api.TradeFrequencyResponse | null>(null);

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

  // Determine the display currency based on account selection
  const selectedAccount = availableAccounts.find(
    (a) => a.account_id === selectedAccountId,
  );
  // When viewing a single account, use its native currency; otherwise use default
  const effectiveCurrency = selectedAccountId
    ? selectedAccount?.currency || defaultCurrency
    : defaultCurrency;

  // Wait for Zustand store to hydrate before fetching with date range
  React.useEffect(() => {
    setHasHydrated(true);
  }, []);

  // Build date range object for API calls
  const getDateRangeForApi = React.useCallback(() => {
    return {
      from: dateRange.from,
      to: dateRange.to,
    };
  }, [dateRange.from, dateRange.to]);

  // Fetch data function using centralized API client
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
        api.getPointsByInstrument(dateRangeParam, selectedAccountId),
        api.getSpreadCost(effectiveCurrency, dateRangeParam, selectedAccountId),
        api.getTradeFrequency(dateRangeParam, selectedAccountId),
        api.getAccounts(),
      ]);

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

      if (winRateResult.status === "fulfilled") {
        setWinRateByInstrument(winRateResult.value);
      }

      // Process balance by account
      if (balanceByAccResult.status === "fulfilled") {
        setBalanceByAccount(
          balanceByAccResult.value as typeof balanceByAccount,
        );
      }

      // Process monthly P&L by account
      if (monthlyByAccResult.status === "fulfilled") {
        setMonthlyPnLByAccount(
          monthlyByAccResult.value as typeof monthlyPnLByAccount,
        );
      }

      // Process daily P&L
      if (dailyPnLResult.status === "fulfilled") {
        setDailyPnL(dailyPnLResult.value);
      }

      // Process daily P&L by account
      if (dailyPnLByAccResult.status === "fulfilled") {
        setDailyPnLByAccount(
          dailyPnLByAccResult.value as typeof dailyPnLByAccount,
        );
      }

      // Process hourly performance
      if (hourlyResult.status === "fulfilled") {
        setHourlyPerformance(hourlyResult.value as typeof hourlyPerformance);
      }

      // Process weekday performance
      if (weekdayResult.status === "fulfilled") {
        setWeekdayPerformance(weekdayResult.value as typeof weekdayPerformance);
      }

      // Process streak data
      if (streakResult.status === "fulfilled") {
        setStreakData(streakResult.value as typeof streakData);
      }

      // Process trade duration
      if (durationResult.status === "fulfilled") {
        setTradeDuration(durationResult.value as typeof tradeDuration);
      }

      // Process position size
      if (positionSizeResult.status === "fulfilled") {
        setPositionSizeData(
          positionSizeResult.value as typeof positionSizeData,
        );
      }

      // Process funding data - API returns array directly with date, deposits, withdrawals, net, cumulative
      if (fundingResult.status === "fulfilled") {
        const result = fundingResult.value as Array<{
          date: string;
          deposits: number;
          withdrawals: number;
          net: number;
          cumulative: number;
        }>;
        if (Array.isArray(result)) {
          setFundingData(result);
        }
      }

      // Process equity curve (P/L based, excludes funding)
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

  // Fetch data on mount - always fetch once when component mounts and hydrates
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

  // Get the display currency (from data or effective currency)
  // No fallback per .rules - effectiveCurrency must be set from settings
  const displayCurrency = dataCurrency || effectiveCurrency;

  // Currency is required for all charts - show message if not set
  const currencyNotSet = !displayCurrency;

  // Handle account change
  const handleAccountChange = React.useCallback(
    (accountId: number | null) => {
      setSelectedAccountId(accountId);
    },
    [setSelectedAccountId],
  );

  // Format balance data for chart
  const formattedBalanceData = React.useMemo(() => {
    return balanceHistory.map((point) => ({
      date: new Date(point.date).toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
      }),
      balance: point.balance,
    }));
  }, [balanceHistory]);

  // Chart categories
  const categories: {
    value: ChartCategory;
    label: string;
    icon: React.ElementType;
  }[] = [
    { value: "all", label: "All Charts", icon: BarChart3 },
    { value: "pnl", label: "P&L", icon: DollarSign },
    { value: "performance", label: "Performance", icon: Target },
    { value: "time", label: "Time Analysis", icon: Clock },
    { value: "instruments", label: "Instruments", icon: PieChart },
    { value: "risk", label: "Risk", icon: Activity },
  ];

  // Chart definitions
  const charts: ChartDefinition[] = [
    {
      id: "dailyPnL",
      title: "Daily P&L",
      description: "Daily profit and loss with percentage returns",
      category: "pnl",
      icon: BarChart3,
      component: currencyNotSet ? (
        <div className="flex items-center justify-center h-[300px] text-muted-foreground">
          Please set your default currency in Settings
        </div>
      ) : (
        <DailyPnLChart
          data={dailyPnL}
          height={300}
          currency={displayCurrency}
        />
      ),
    },
    {
      id: "cumulativePnL",
      title: "Cumulative P&L",
      description: "Running total of profits and losses over time",
      category: "pnl",
      icon: LineChart,
      component: currencyNotSet ? (
        <div className="flex items-center justify-center h-[300px] text-muted-foreground">
          Please set your default currency in Settings
        </div>
      ) : dailyPnLByAccount && dailyPnLByAccount.series.length > 1 ? (
        <MultiAccountCumulativePnLChart
          series={dailyPnLByAccount.series}
          total={dailyPnLByAccount.total}
          height={300}
          showLegend={true}
        />
      ) : (
        <CumulativePnLChart
          data={dailyPnL}
          height={300}
          currency={displayCurrency}
        />
      ),
    },
    {
      id: "monthlyPnL",
      title: "Monthly P&L",
      description: "Monthly breakdown of trading performance",
      category: "pnl",
      icon: Calendar,
      component: currencyNotSet ? (
        <div className="flex items-center justify-center h-[300px] text-muted-foreground">
          Please set your default currency in Settings
        </div>
      ) : (
        <MonthlyPnLChart
          data={monthlyPnL}
          height={300}
          currency={displayCurrency}
        />
      ),
    },
    {
      id: "equityCurve",
      title: "Equity Curve",
      description:
        "Account equity over time (P/L only, excludes deposits/withdrawals)",
      category: "pnl",
      icon: TrendingUp,
      component: currencyNotSet ? (
        <div className="flex items-center justify-center h-[300px] text-muted-foreground">
          Please set your default currency in Settings
        </div>
      ) : (
        <BalanceChart
          data={equityCurve.map((p) => ({
            date: new Date(p.date).toLocaleDateString("en-US", {
              month: "short",
              day: "numeric",
            }),
            balance: p.balance,
          }))}
          height={300}
          currency={displayCurrency}
        />
      ),
    },
    {
      id: "balanceHistory",
      title: "Balance History",
      description: "Account balance over time (includes funding)",
      category: "pnl",
      icon: Wallet,
      component: currencyNotSet ? (
        <div className="flex items-center justify-center h-[300px] text-muted-foreground">
          Please set your default currency in Settings
        </div>
      ) : (
        <BalanceChart
          data={formattedBalanceData}
          height={300}
          showDrawdown={true}
          currency={displayCurrency}
        />
      ),
    },
    {
      id: "funding",
      title: "Funding Activity",
      description:
        "Track deposits, withdrawals, and their impact on account balance",
      category: "pnl",
      icon: DollarSign,
      component: currencyNotSet ? (
        <div className="flex items-center justify-center h-[300px] text-muted-foreground">
          Please set your default currency in Settings
        </div>
      ) : (
        <FundingChart
          data={fundingData}
          height={300}
          currency={displayCurrency}
        />
      ),
    },
    {
      id: "winRate",
      title: "Win Rate by Instrument",
      description: "Win rate breakdown across different instruments",
      category: "instruments",
      icon: Target,
      component: <WinRateChart data={winRateByInstrument} height={300} />,
    },
    {
      id: "hourly",
      title: "Hourly Performance",
      description: "Performance breakdown by hour of day",
      category: "time",
      icon: Clock,
      component: currencyNotSet ? (
        <div className="flex items-center justify-center h-[300px] text-muted-foreground">
          Please set your default currency in Settings
        </div>
      ) : (
        <HourlyPerformanceChart
          data={hourlyPerformance}
          height={300}
          currency={displayCurrency}
        />
      ),
    },
    {
      id: "weekday",
      title: "Weekday Performance",
      description: "Performance breakdown by day of week",
      category: "time",
      icon: Calendar,
      component: currencyNotSet ? (
        <div className="flex items-center justify-center h-[300px] text-muted-foreground">
          Please set your default currency in Settings
        </div>
      ) : (
        <WeekdayPerformanceChart
          data={weekdayPerformance}
          height={300}
          currency={displayCurrency}
        />
      ),
    },
    {
      id: "streaks",
      title: "Win/Loss Streaks",
      description: "Current and historical winning/losing streaks",
      category: "performance",
      icon: Activity,
      component: <StreakChart data={streakData} height={300} />,
    },
    {
      id: "tradeFrequency",
      title: "Trade Frequency",
      description: "Daily, monthly, and yearly trade counts with averages",
      category: "performance",
      icon: BarChart3,
      component: (
        <TradeFrequencyChart
          data={tradeFrequencyData}
          height={300}
          showByAccount={true}
        />
      ),
    },
    {
      id: "duration",
      title: "Trade Duration Analysis",
      description: "Performance by trade holding time",
      category: "time",
      icon: Clock,
      component: <TradeDurationChart data={tradeDuration} height={300} />,
    },
    {
      id: "positionSize",
      title: "Position Size Analysis",
      description: "Performance by position size",
      category: "risk",
      icon: BarChart3,
      component: currencyNotSet ? (
        <div className="flex items-center justify-center h-[300px] text-muted-foreground">
          Please set your default currency in Settings
        </div>
      ) : (
        <PositionSizeChart
          data={positionSizeData}
          height={300}
          currency={displayCurrency}
        />
      ),
    },
    {
      id: "points",
      title: "Points by Instrument",
      description: "Total points/pips gained or lost per instrument",
      category: "instruments",
      icon: Target,
      component: <PointsChart data={pointsByInstrument} height={300} />,
    },
    {
      id: "spreadCost",
      title: "Spread Cost Analysis",
      description: "Monthly breakdown of spread costs paid per trade",
      category: "risk",
      icon: DollarSign,
      component: currencyNotSet ? (
        <div className="flex items-center justify-center h-[300px] text-muted-foreground">
          Please set your default currency in Settings
        </div>
      ) : (
        <SpreadCostChart
          data={spreadCostData?.monthly || []}
          byInstrument={spreadCostData?.by_instrument || []}
          totalSpreadCost={spreadCostData?.total_spread_cost || 0}
          totalTrades={spreadCostData?.total_trades || 0}
          avgSpreadPerTrade={spreadCostData?.avg_spread_per_trade || 0}
          height={300}
          currency={displayCurrency}
        />
      ),
    },
  ];

  // Filter charts by category
  const filteredCharts =
    selectedCategory === "all"
      ? charts
      : charts.filter((chart) => chart.category === selectedCategory);

  // Handle date range change
  const handleDateRangeChange = React.useCallback(
    (newRange: {
      from: Date | undefined;
      to: Date | undefined;
      preset?: DateRangePreset;
    }) => {
      setDateRange({
        from: newRange.from,
        to: newRange.to,
        preset: newRange.preset || "custom",
      });
    },
    [setDateRange],
  );

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border bg-card/50 backdrop-blur-sm sticky top-0 z-40">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold tracking-tight">Analytics</h1>
              <p className="text-sm text-muted-foreground">
                Detailed trading analysis and insights
              </p>
            </div>

            <div className="flex items-center gap-4">
              {/* Date Range Picker */}
              <DateRangePicker
                dateRange={{
                  from: dateRange.from,
                  to: dateRange.to,
                  preset: dateRange.preset as DateRangePreset,
                }}
                onDateRangeChange={handleDateRangeChange}
              />

              {/* Account Filter */}
              {availableAccounts.length > 0 && (
                <select
                  value={selectedAccountId ?? ""}
                  onChange={(e) =>
                    handleAccountChange(
                      e.target.value ? parseInt(e.target.value, 10) : null,
                    )
                  }
                  className="px-3 py-2 rounded-md text-sm font-medium bg-secondary text-secondary-foreground border border-border"
                >
                  <option value="">All Accounts (converted)</option>
                  {availableAccounts.map((account) => (
                    <option key={account.account_id} value={account.account_id}>
                      {account.account_name || `Account ${account.account_id}`}
                      {account.currency ? ` (${account.currency})` : ""}
                    </option>
                  ))}
                </select>
              )}
            </div>
          </div>

          {/* Category Filter */}
          <div className="mt-4 flex gap-2 overflow-x-auto pb-2">
            {categories.map((category) => {
              const Icon = category.icon;
              const isActive = selectedCategory === category.value;
              const count =
                category.value === "all"
                  ? charts.length
                  : charts.filter((c) => c.category === category.value).length;

              return (
                <Button
                  key={category.value}
                  variant={isActive ? "default" : "outline"}
                  size="sm"
                  onClick={() => setSelectedCategory(category.value)}
                  className={cn(
                    "flex items-center gap-2 whitespace-nowrap",
                    isActive && "bg-primary text-primary-foreground",
                  )}
                >
                  <Icon className="h-4 w-4" />
                  {category.label}
                  <Badge
                    variant={isActive ? "secondary" : "outline"}
                    className="ml-1 h-5 px-1.5 text-xs"
                  >
                    {count}
                  </Badge>
                </Button>
              );
            })}
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {filteredCharts.map((chart) => {
            const Icon = chart.icon;
            return (
              <ChartCard
                key={chart.id}
                title={chart.title}
                subtitle={chart.description}
                onExpand={() => setExpandedChart(chart.id)}
              >
                {chart.component}
              </ChartCard>
            );
          })}
        </div>

        {filteredCharts.length === 0 && (
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <BarChart3 className="h-12 w-12 text-muted-foreground mb-4" />
            <h3 className="text-lg font-medium">No charts in this category</h3>
            <p className="text-muted-foreground mt-1">
              Select a different category to view charts
            </p>
          </div>
        )}
      </main>

      {/* Expanded Chart Modals */}
      {charts.map((chart) => (
        <ExpandedChartModal
          key={chart.id}
          isOpen={expandedChart === chart.id}
          onClose={() => setExpandedChart(null)}
          title={chart.title}
          subtitle={chart.description}
        >
          {React.cloneElement(chart.component as React.ReactElement, {
            height: 500,
          })}
        </ExpandedChartModal>
      ))}
    </div>
  );
}
