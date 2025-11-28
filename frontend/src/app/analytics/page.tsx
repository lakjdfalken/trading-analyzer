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
import { PositionSizeChart } from "@/components/charts/PositionSizeChart";
import { FundingChart } from "@/components/charts/FundingChart";
import { PointsChart } from "@/components/charts/PointsChart";
import type { PointsData } from "@/components/charts/PointsChart";
import type { AccountSeries } from "@/components/charts/MultiAccountBalanceChart";
import type { AccountPnLSeries } from "@/components/charts/MultiAccountMonthlyPnLChart";
import { DateRangePicker } from "@/components/filters/DateRangePicker";
import { useDashboardStore } from "@/store/dashboard";
import type { DateRangePreset } from "@/components/filters/types";

// API base URL
// Always use relative URL for same-origin requests (works with any port)
// This ensures the frontend works when served by the backend on any port
const API_BASE = "";

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
  const { defaultCurrency } = useCurrencyStore();

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
    Array<{ date: string; pnl: number; cumulativePnl: number; trades: number }>
  >([]);
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
    Array<{ date: string; balance: number }>
  >([]);
  const [pointsByInstrument, setPointsByInstrument] = React.useState<
    PointsData[]
  >([]);

  const {
    dateRange,
    balanceHistory,
    monthlyPnL,
    winRateByInstrument,
    loading,
    setDateRange,
    setBalanceHistory,
    setMonthlyPnL,
    setWinRateByInstrument,
    setLoading,
    isInitialized,
    setInitialized,
  } = useDashboardStore();

  // Wait for Zustand store to hydrate before fetching with date range
  React.useEffect(() => {
    setHasHydrated(true);
  }, []);

  // Build query string with date range - extracted to avoid stale closures
  const buildQueryString = React.useCallback(() => {
    const params = new URLSearchParams();
    if (dateRange.from) {
      params.append("from", dateRange.from.toISOString());
    }
    if (dateRange.to) {
      params.append("to", dateRange.to.toISOString());
    }
    return params.toString() ? `?${params.toString()}` : "";
  }, [dateRange.from, dateRange.to]);

  // Fetch data function
  const fetchData = React.useCallback(async () => {
    setLoading("dashboard", true);
    try {
      // Build query string with date range
      const queryString = buildQueryString();

      const [
        balanceRes,
        monthlyRes,
        winRateRes,
        balanceByAccRes,
        monthlyByAccRes,
        dailyPnLRes,
        hourlyRes,
        weekdayRes,
        streakRes,
        durationRes,
        positionSizeRes,
        fundingRes,
        equityCurveRes,
        pointsRes,
      ] = await Promise.allSettled([
        fetch(`${API_BASE}/api/dashboard/balance${queryString}`),
        fetch(`${API_BASE}/api/dashboard/monthly-pnl${queryString}`),
        fetch(`${API_BASE}/api/dashboard/win-rate-by-instrument${queryString}`),
        fetch(`${API_BASE}/api/dashboard/balance-by-account${queryString}`),
        fetch(`${API_BASE}/api/dashboard/monthly-pnl-by-account${queryString}`),
        fetch(`${API_BASE}/api/analytics/daily-pnl${queryString}`),
        fetch(`${API_BASE}/api/analytics/performance/hourly${queryString}`),
        fetch(`${API_BASE}/api/analytics/performance/weekday${queryString}`),
        fetch(`${API_BASE}/api/analytics/streaks${queryString}`),
        fetch(`${API_BASE}/api/analytics/trade-duration${queryString}`),
        fetch(`${API_BASE}/api/analytics/position-size${queryString}`),
        fetch(`${API_BASE}/api/analytics/funding${queryString}`),
        fetch(`${API_BASE}/api/dashboard/equity-curve${queryString}`),
        fetch(`${API_BASE}/api/dashboard/points-by-instrument${queryString}`),
      ]);

      if (balanceRes.status === "fulfilled" && balanceRes.value.ok) {
        const balanceResponse = await balanceRes.value.json();
        // Handle both old format (array) and new format (object with data and currency)
        const balanceData = Array.isArray(balanceResponse)
          ? balanceResponse
          : balanceResponse.data || [];
        setBalanceHistory(balanceData);
        if (balanceResponse.currency) {
          setDataCurrency(balanceResponse.currency);
        }
      }

      if (monthlyRes.status === "fulfilled" && monthlyRes.value.ok) {
        const monthlyResponse = await monthlyRes.value.json();
        // Handle both old format (array) and new format (object with data and currency)
        const monthlyData = Array.isArray(monthlyResponse)
          ? monthlyResponse
          : monthlyResponse.data || [];
        setMonthlyPnL(monthlyData);
        if (monthlyResponse.currency) {
          setDataCurrency(monthlyResponse.currency);
        }
      }

      if (winRateRes.status === "fulfilled" && winRateRes.value.ok) {
        const winRateData = await winRateRes.value.json();
        setWinRateByInstrument(winRateData);
      }

      // Process balance by account
      if (balanceByAccRes.status === "fulfilled" && balanceByAccRes.value.ok) {
        const balanceByAccData = await balanceByAccRes.value.json();
        setBalanceByAccount(balanceByAccData);
      }

      // Process monthly P&L by account
      if (monthlyByAccRes.status === "fulfilled" && monthlyByAccRes.value.ok) {
        const monthlyByAccData = await monthlyByAccRes.value.json();
        setMonthlyPnLByAccount(monthlyByAccData);
      }

      // Process daily P&L
      if (dailyPnLRes.status === "fulfilled" && dailyPnLRes.value.ok) {
        const dailyPnLData = await dailyPnLRes.value.json();
        setDailyPnL(dailyPnLData);
      }

      // Process hourly performance
      if (hourlyRes.status === "fulfilled" && hourlyRes.value.ok) {
        const hourlyData = await hourlyRes.value.json();
        setHourlyPerformance(hourlyData);
      }

      // Process weekday performance
      if (weekdayRes.status === "fulfilled" && weekdayRes.value.ok) {
        const weekdayData = await weekdayRes.value.json();
        setWeekdayPerformance(weekdayData);
      }

      // Process streak data
      if (streakRes.status === "fulfilled" && streakRes.value.ok) {
        const streakDataResult = await streakRes.value.json();
        setStreakData(streakDataResult);
      }

      // Process trade duration
      if (durationRes.status === "fulfilled" && durationRes.value.ok) {
        const durationData = await durationRes.value.json();
        setTradeDuration(durationData);
      }

      // Process position size
      if (positionSizeRes.status === "fulfilled" && positionSizeRes.value.ok) {
        const positionSizeResult = await positionSizeRes.value.json();
        setPositionSizeData(positionSizeResult);
      }

      // Process funding data
      if (fundingRes.status === "fulfilled" && fundingRes.value.ok) {
        const fundingResult = await fundingRes.value.json();
        setFundingData(fundingResult);
      }

      // Process equity curve (P/L based, excludes funding)
      if (equityCurveRes.status === "fulfilled" && equityCurveRes.value.ok) {
        const equityCurveResponse = await equityCurveRes.value.json();
        const equityData = Array.isArray(equityCurveResponse)
          ? equityCurveResponse
          : equityCurveResponse.data || [];
        setEquityCurve(equityData);
      }

      // Process points by instrument
      if (pointsRes.status === "fulfilled" && pointsRes.value.ok) {
        const pointsData = await pointsRes.value.json();
        setPointsByInstrument(pointsData);
      }

      setInitialized(true);
    } finally {
      setLoading("dashboard", false);
    }
  }, [
    buildQueryString,
    setLoading,
    setBalanceHistory,
    setMonthlyPnL,
    setWinRateByInstrument,
    setInitialized,
  ]);

  // Fetch data on mount - always fetch once when component mounts and hydrates
  React.useEffect(() => {
    if (hasHydrated && !hasFetchedOnce) {
      setHasFetchedOnce(true);
      fetchData();
    }
  }, [hasHydrated, hasFetchedOnce, fetchData]);

  // Refetch when date range changes (after initial load)
  React.useEffect(() => {
    if (hasFetchedOnce && hasHydrated) {
      fetchData();
    }
  }, [dateRange.from, dateRange.to, hasFetchedOnce, hasHydrated, fetchData]);

  // Get the display currency (from data or default)
  const displayCurrency = dataCurrency || defaultCurrency || "USD";

  // Format balance data
  const formattedBalanceData = React.useMemo(() => {
    return balanceHistory.map((point) => ({
      date: new Date(point.date).toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
      }),
      balance: point.balance,
    }));
  }, [balanceHistory]);

  // Categories for filtering
  const categories: {
    value: ChartCategory;
    label: string;
    icon: React.ElementType;
  }[] = [
    { value: "all", label: "All Charts", icon: BarChart3 },
    { value: "pnl", label: "P&L Analysis", icon: DollarSign },
    { value: "performance", label: "Performance", icon: Target },
    { value: "time", label: "Time Analysis", icon: Clock },
    { value: "instruments", label: "Instruments", icon: Activity },
    { value: "risk", label: "Risk Metrics", icon: TrendingDown },
  ];

  // Chart definitions
  const charts: ChartDefinition[] = [
    {
      id: "equity-curve",
      title: "Equity Curve",
      description: "Track your account balance over time",
      category: "pnl",
      icon: LineChart,
      component:
        balanceByAccount && balanceByAccount.series.length > 1 ? (
          <MultiAccountBalanceChart
            series={balanceByAccount.series}
            total={balanceByAccount.total}
            height={300}
            showTotal={true}
            showLegend={true}
          />
        ) : (
          <BalanceChart
            data={formattedBalanceData}
            height={300}
            startingBalance={10000}
            showGrid
            currency={displayCurrency}
          />
        ),
    },
    {
      id: "monthly-pnl",
      title: "Monthly P&L",
      description: "Profit and loss breakdown by month",
      category: "pnl",
      icon: BarChart3,
      component:
        monthlyPnLByAccount && monthlyPnLByAccount.series.length > 1 ? (
          <MultiAccountMonthlyPnLChart
            series={monthlyPnLByAccount.series}
            total={monthlyPnLByAccount.total}
            height={300}
            showTotal={false}
            stacked={true}
          />
        ) : (
          <MonthlyPnLChart
            data={monthlyPnL}
            height={300}
            currency={displayCurrency}
          />
        ),
    },
    {
      id: "win-rate-instrument",
      title: "Win Rate by Instrument",
      description: "Performance comparison across different markets",
      category: "instruments",
      icon: PieChart,
      component: (
        <WinRateChart
          data={winRateByInstrument}
          height={300}
          layout="horizontal"
        />
      ),
    },
    {
      id: "points-by-instrument",
      title: "Points by Instrument",
      description:
        "Total points/pips earned per instrument (Gold=0.1pts, Index=1pt, Forex=pips)",
      category: "instruments",
      icon: Target,
      component: (
        <PointsChart
          data={pointsByInstrument}
          height={300}
          layout="horizontal"
          metric="totalPoints"
        />
      ),
    },
    {
      id: "daily-pnl",
      title: "Daily P&L Distribution",
      description: "Distribution of daily profit and loss",
      category: "pnl",
      icon: BarChart3,
      component: (
        <DailyPnLChart
          data={dailyPnL}
          height={300}
          currency={displayCurrency}
        />
      ),
    },
    {
      id: "drawdown",
      title: "Drawdown Analysis",
      description:
        "Historical drawdown periods and recovery (P/L only, excludes deposits/withdrawals)",
      category: "risk",
      icon: TrendingDown,
      component: (
        <DrawdownChart
          balanceData={equityCurve}
          height={300}
          currency={displayCurrency}
        />
      ),
    },
    {
      id: "trade-duration",
      title: "Trade Duration",
      description: "Analysis of trade holding times",
      category: "time",
      icon: Clock,
      component: <TradeDurationChart data={tradeDuration} height={300} />,
    },
    {
      id: "hourly-performance",
      title: "Performance by Hour",
      description: "Best and worst trading hours",
      category: "time",
      icon: Calendar,
      component: (
        <HourlyPerformanceChart
          data={hourlyPerformance}
          height={300}
          currency={displayCurrency}
          metric="pnl"
        />
      ),
    },
    {
      id: "weekday-performance",
      title: "Performance by Weekday",
      description: "Trading performance across different days",
      category: "time",
      icon: Calendar,
      component: (
        <WeekdayPerformanceChart
          data={weekdayPerformance}
          height={300}
          currency={displayCurrency}
          metric="pnl"
        />
      ),
    },

    {
      id: "win-loss-streak",
      title: "Win/Loss Streaks",
      description: "Consecutive wins and losses analysis",
      category: "performance",
      icon: Activity,
      component: <StreakChart data={streakData} height={300} />,
    },
    {
      id: "cumulative-pnl",
      title: "Cumulative P&L",
      description: "Running total of profits and losses",
      category: "pnl",
      icon: TrendingUp,
      component: (
        <CumulativePnLChart
          data={dailyPnL}
          height={300}
          currency={displayCurrency}
        />
      ),
    },
    {
      id: "position-size",
      title: "Position Size Analysis",
      description: "Distribution and impact of position sizes",
      category: "risk",
      icon: Wallet,
      component: (
        <PositionSizeChart
          data={positionSizeData}
          height={300}
          currency={displayCurrency}
        />
      ),
    },
    {
      id: "funding",
      title: "Deposits & Withdrawals",
      description: "Track account deposits and withdrawals over time",
      category: "pnl",
      icon: Wallet,
      component: (
        <FundingChart
          data={fundingData}
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
  const handleDateRangeChange = (newRange: {
    from: Date | undefined;
    to: Date | undefined;
    preset?: DateRangePreset;
  }) => {
    setDateRange({
      from: newRange.from,
      to: newRange.to,
      preset: newRange.preset || "custom",
    });
  };

  return (
    <div className="min-h-screen bg-background p-6 md:p-8">
      <div className="container mx-auto max-w-7xl">
        {/* Page Header */}
        <div className="mb-8">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            <div>
              <h1 className="text-2xl font-bold tracking-tight">Analytics</h1>
              <p className="text-muted-foreground mt-1">
                In-depth analysis of your trading performance
              </p>
            </div>
            <DateRangePicker
              dateRange={{
                from: dateRange.from,
                to: dateRange.to,
                preset: dateRange.preset,
              }}
              onDateRangeChange={handleDateRangeChange}
            />
          </div>
        </div>

        {/* Category Filter */}
        <div className="mb-6">
          <div className="flex flex-wrap gap-2">
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
                  className="gap-2"
                >
                  <Icon className="h-4 w-4" />
                  {category.label}
                  <Badge
                    variant={isActive ? "secondary" : "outline"}
                    className="ml-1 h-5 px-1.5"
                  >
                    {count}
                  </Badge>
                </Button>
              );
            })}
          </div>
        </div>

        {/* Charts Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {filteredCharts.map((chart) => {
            const Icon = chart.icon;

            return (
              <Card key={chart.id} className="overflow-hidden">
                <CardHeader className="flex flex-row items-start justify-between space-y-0 pb-2">
                  <div className="flex items-start gap-3">
                    <div className="p-2 rounded-md bg-primary/10">
                      <Icon className="h-4 w-4 text-primary" />
                    </div>
                    <div>
                      <CardTitle className="text-base font-semibold">
                        {chart.title}
                      </CardTitle>
                      <p className="text-sm text-muted-foreground mt-0.5">
                        {chart.description}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-1">
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8"
                      onClick={() => setExpandedChart(chart.id)}
                    >
                      <Maximize2 className="h-4 w-4" />
                    </Button>
                    <Button variant="ghost" size="icon" className="h-8 w-8">
                      <Download className="h-4 w-4" />
                    </Button>
                  </div>
                </CardHeader>
                <CardContent className="pt-4">{chart.component}</CardContent>
              </Card>
            );
          })}
        </div>

        {/* Empty State */}
        {filteredCharts.length === 0 && (
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <Filter className="h-12 w-12 text-muted-foreground mb-4" />
            <h3 className="text-lg font-medium">No charts found</h3>
            <p className="text-muted-foreground mt-1">
              Try selecting a different category
            </p>
          </div>
        )}
      </div>

      {/* Expanded Chart Modal */}
      {expandedChart && (
        <ExpandedChartModal
          isOpen={!!expandedChart}
          onClose={() => setExpandedChart(null)}
          title={charts.find((c) => c.id === expandedChart)?.title || "Chart"}
          subtitle={charts.find((c) => c.id === expandedChart)?.description}
        >
          <div className="w-full h-full min-h-[500px]">
            {expandedChart === "equity-curve" &&
              (balanceByAccount && balanceByAccount.series.length > 1 ? (
                <MultiAccountBalanceChart
                  series={balanceByAccount.series}
                  total={balanceByAccount.total}
                  height={600}
                  showTotal={true}
                  showLegend={true}
                />
              ) : (
                <BalanceChart
                  data={formattedBalanceData}
                  height={600}
                  startingBalance={10000}
                  showGrid
                  currency={displayCurrency}
                />
              ))}
            {expandedChart === "monthly-pnl" &&
              (monthlyPnLByAccount && monthlyPnLByAccount.series.length > 1 ? (
                <MultiAccountMonthlyPnLChart
                  series={monthlyPnLByAccount.series}
                  total={monthlyPnLByAccount.total}
                  height={600}
                  showTotal={false}
                  stacked={true}
                />
              ) : (
                <MonthlyPnLChart
                  data={monthlyPnL}
                  height={600}
                  currency={displayCurrency}
                />
              ))}
            {expandedChart === "win-rate-instrument" && (
              <WinRateChart
                data={winRateByInstrument}
                height={600}
                layout="horizontal"
              />
            )}
            {expandedChart === "points-by-instrument" && (
              <PointsChart
                data={pointsByInstrument}
                height={600}
                layout="horizontal"
                metric="totalPoints"
              />
            )}
            {expandedChart === "daily-pnl" && (
              <DailyPnLChart
                data={dailyPnL}
                height={600}
                currency={displayCurrency}
              />
            )}
            {expandedChart === "drawdown" && (
              <DrawdownChart
                balanceData={equityCurve}
                height={600}
                currency={displayCurrency}
              />
            )}
            {expandedChart === "trade-duration" && (
              <TradeDurationChart data={tradeDuration} height={600} />
            )}
            {expandedChart === "hourly-performance" && (
              <HourlyPerformanceChart
                data={hourlyPerformance}
                height={600}
                currency={displayCurrency}
                metric="pnl"
              />
            )}
            {expandedChart === "weekday-performance" && (
              <WeekdayPerformanceChart
                data={weekdayPerformance}
                height={600}
                currency={displayCurrency}
                metric="pnl"
              />
            )}
            {expandedChart === "win-loss-streak" && (
              <StreakChart data={streakData} height={600} />
            )}
            {expandedChart === "cumulative-pnl" && (
              <CumulativePnLChart
                data={dailyPnL}
                height={600}
                currency={displayCurrency}
              />
            )}
            {expandedChart === "position-size" && (
              <PositionSizeChart
                data={positionSizeData}
                height={600}
                currency={displayCurrency}
              />
            )}
            {expandedChart === "funding" && (
              <FundingChart
                data={fundingData}
                height={600}
                currency={displayCurrency}
              />
            )}
          </div>
        </ExpandedChartModal>
      )}
    </div>
  );
}
