"use client";

import * as React from "react";
import {
  TrendingUp,
  TrendingDown,
  DollarSign,
  Percent,
  BarChart3,
  Target,
  RefreshCw,
  AlertCircle,
} from "lucide-react";

import { KPICard, KPIGrid } from "@/components/kpi";
import { ChartCard } from "@/components/charts/ChartCard";
import { BalanceChart } from "@/components/charts/BalanceChart";
import { MonthlyPnLChart } from "@/components/charts/MonthlyPnLChart";
import { WinRateChart } from "@/components/charts/WinRateChart";
import { ExpandedChartModal } from "@/components/charts/ExpandedChartModal";
import { MultiAccountBalanceChart } from "@/components/charts/MultiAccountBalanceChart";
import { MultiAccountMonthlyPnLChart } from "@/components/charts/MultiAccountMonthlyPnLChart";
import type { AccountSeries } from "@/components/charts/MultiAccountBalanceChart";
import type { AccountPnLSeries } from "@/components/charts/MultiAccountMonthlyPnLChart";
import { RecentTradesList } from "@/components/trades/RecentTradesList";
import { DateRangePicker } from "@/components/filters/DateRangePicker";
import { useDashboardStore, getDateRangeFromPreset } from "@/store/dashboard";
import type { DateRangePreset } from "@/components/filters/types";
import { cn } from "@/lib/utils";
import { useCurrencyStore } from "@/store/currency";

// API base URL for direct fetch calls
// Always use relative URL for same-origin requests (works with any port)
// This ensures the frontend works when served by the backend on any port
const API_BASE = "";

export default function Home() {
  const { formatAmount, defaultCurrency } = useCurrencyStore();
  const [dataCurrency, setDataCurrency] = React.useState<string | null>(null);
  const [hasHydrated, setHasHydrated] = React.useState(false);

  // Expanded chart state
  const [expandedChart, setExpandedChart] = React.useState<string | null>(null);

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
  const {
    dateRange,
    selectedInstruments,
    availableInstruments,
    kpis,
    balanceHistory,
    monthlyPnL,
    winRateByInstrument,
    recentTrades,
    loading,
    errors,
    lastUpdated,
    isInitialized,
    setDateRange,
    setSelectedInstruments,
    setKPIs,
    setBalanceHistory,
    setMonthlyPnL,
    setWinRateByInstrument,
    setRecentTrades,
    setAvailableInstruments,
    setLoading,
    setError,
    setLastUpdated,
    setInitialized,
  } = useDashboardStore();

  // Track if initial fetch has been done this session
  const [hasFetchedOnce, setHasFetchedOnce] = React.useState(false);

  // Wait for Zustand store to hydrate before fetching with date range
  React.useEffect(() => {
    setHasHydrated(true);
  }, []);

  // Build query string with date range - extracted to avoid stale closures
  const buildQueryString = React.useCallback(() => {
    const params = new URLSearchParams();
    if (dateRange.from) {
      const fromDate =
        dateRange.from instanceof Date
          ? dateRange.from
          : new Date(dateRange.from);
      params.append("from", fromDate.toISOString().split(".")[0] + "Z");
    }
    if (dateRange.to) {
      const toDate =
        dateRange.to instanceof Date ? dateRange.to : new Date(dateRange.to);
      params.append("to", toDate.toISOString().split(".")[0] + "Z");
    }
    return params.toString() ? `?${params.toString()}` : "";
  }, [dateRange.from, dateRange.to]);

  // Fetch dashboard data
  const fetchDashboardData = React.useCallback(async () => {
    setLoading("dashboard", true);
    setError("dashboard", null);

    try {
      // Build query string with date range
      const queryString = buildQueryString();
      const params = new URLSearchParams(queryString.replace("?", ""));

      // Fetch from real API
      const [
        kpisRes,
        balanceRes,
        monthlyRes,
        tradesRes,
        instrumentsRes,
        balanceByAccRes,
        monthlyByAccRes,
        winRateRes,
      ] = await Promise.allSettled([
        fetch(`${API_BASE}/api/dashboard/kpis${queryString}`),
        fetch(`${API_BASE}/api/dashboard/balance${queryString}`),
        fetch(`${API_BASE}/api/dashboard/monthly-pnl${queryString}`),
        fetch(
          `${API_BASE}/api/trades/recent?limit=10${queryString ? "&" + params.toString() : ""}`,
        ),
        fetch(`${API_BASE}/api/instruments`),
        fetch(`${API_BASE}/api/dashboard/balance-by-account${queryString}`),
        fetch(`${API_BASE}/api/dashboard/monthly-pnl-by-account${queryString}`),
        fetch(`${API_BASE}/api/dashboard/win-rate-by-instrument${queryString}`),
      ]);

      // Process KPIs
      if (kpisRes.status === "fulfilled" && kpisRes.value.ok) {
        const kpisData = await kpisRes.value.json();
        setKPIs(kpisData);
        // Set the data currency from KPIs if available
        if (kpisData.currency) {
          setDataCurrency(kpisData.currency);
        }
      }

      // Process balance history (new format with currency)
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

      // Process monthly P&L (new format with currency)
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

      // Process recent trades (includes currency)
      if (tradesRes.status === "fulfilled" && tradesRes.value.ok) {
        const tradesData = await tradesRes.value.json();
        // Map API response to frontend Trade type
        const mappedTrades = tradesData.map((t: Record<string, unknown>) => ({
          id: t.id || t.transaction_id,
          instrument: t.instrument || t.description,
          direction: t.direction || "long",
          entryPrice: t.entry_price || t.entryPrice || 0,
          exitPrice: t.exit_price || t.exitPrice || 0,
          entryTime: new Date(
            (t.entry_time || t.entryTime || t.open_period || Date.now()) as
              | string
              | number,
          ),
          exitTime: new Date(
            (t.exit_time || t.exitTime || t.transaction_date || Date.now()) as
              | string
              | number,
          ),
          quantity: t.quantity || t.amount || 1,
          pnl: t.pnl || t.pl || 0,
          pnlPercent: t.pnl_percent || t.pnlPercent || 0,
          currency: t.currency, // Use actual currency from trade data
        }));
        setRecentTrades(mappedTrades);
      }

      // Process instruments
      if (instrumentsRes.status === "fulfilled" && instrumentsRes.value.ok) {
        const instrumentsData = await instrumentsRes.value.json();
        setAvailableInstruments(instrumentsData);
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

      // Process win rate by instrument
      if (winRateRes.status === "fulfilled" && winRateRes.value.ok) {
        const winRateData = await winRateRes.value.json();
        setWinRateByInstrument(winRateData);
      }

      setLastUpdated(new Date());
      setInitialized(true);
    } catch (error) {
      console.error("Dashboard fetch error:", error);
      setError(
        "dashboard",
        error instanceof Error ? error.message : "Failed to fetch data",
      );
    } finally {
      setLoading("dashboard", false);
    }
  }, [
    buildQueryString,
    setLoading,
    setError,
    setKPIs,
    setBalanceHistory,
    setMonthlyPnL,
    setWinRateByInstrument,
    setRecentTrades,
    setAvailableInstruments,
    setLastUpdated,
    setInitialized,
  ]);

  // Initial data fetch - always fetch once when component mounts and hydrates
  React.useEffect(() => {
    if (hasHydrated && !hasFetchedOnce) {
      setHasFetchedOnce(true);
      fetchDashboardData();
    }
  }, [hasHydrated, hasFetchedOnce, fetchDashboardData]);

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
      // Trigger a refetch with the new date range
      fetchDashboardData();
    },
    [setDateRange, fetchDashboardData],
  );

  // Get the display currency (from data or default)
  const displayCurrency = dataCurrency || defaultCurrency || "USD";

  // Build KPI items from store data
  const kpiItems = React.useMemo(() => {
    if (!kpis) return [];

    const currency = kpis.currency || displayCurrency;

    return [
      {
        title: "Total P&L",
        value: kpis.totalPnl,
        subtitle: "Last 30 days",
        icon: DollarSign,
        variant:
          kpis.totalPnl >= 0 ? ("success" as const) : ("danger" as const),
        isCurrency: true,
        currency,
      },
      {
        title: "Win Rate",
        value: `${kpis.winRate.toFixed(1)}%`,
        subtitle: `${kpis.totalTrades} trades`,
        icon: Target,
        variant:
          kpis.winRate >= 50 ? ("success" as const) : ("warning" as const),
      },
      {
        title: "Avg Win",
        value: kpis.avgWin,
        subtitle: "Per winning trade",
        icon: TrendingUp,
        variant: "default" as const,
        isCurrency: true,
        currency,
      },
      {
        title: "Avg Loss",
        value: kpis.avgLoss,
        subtitle: "Per losing trade",
        icon: TrendingDown,
        variant: "danger" as const,
        isCurrency: true,
        currency,
      },
      {
        title: "Profit Factor",
        value: kpis.profitFactor.toFixed(2),
        subtitle: "Risk/Reward ratio",
        icon: BarChart3,
        variant:
          kpis.profitFactor >= 1.5
            ? ("success" as const)
            : ("default" as const),
        tooltip:
          "Total profits ÷ Total losses. Values above 1.0 mean you're profitable overall. Above 1.5 is considered good.",
      },
      {
        title: "Max Drawdown",
        value: `${kpis.maxDrawdown.toFixed(1)}%`,
        subtitle: "Peak to trough",
        icon: Percent,
        variant:
          kpis.maxDrawdown > 10 ? ("danger" as const) : ("warning" as const),
        tooltip:
          "Largest percentage drop from a peak balance to a subsequent low point. Lower is better.",
      },
    ];
  }, [kpis, displayCurrency]);

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

  // Format win rate data for chart
  const formattedWinRateData = React.useMemo(() => {
    return winRateByInstrument;
  }, [winRateByInstrument]);

  // Loading state
  if (loading.dashboard && !isInitialized) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="flex flex-col items-center gap-4">
          <RefreshCw className="h-8 w-8 animate-spin text-primary" />
          <p className="text-muted-foreground">Loading dashboard...</p>
        </div>
      </div>
    );
  }

  // Error state
  if (errors.dashboard && !isInitialized) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="flex flex-col items-center gap-4 text-center">
          <AlertCircle className="h-12 w-12 text-red-500" />
          <div>
            <h2 className="text-lg font-semibold">Failed to load dashboard</h2>
            <p className="text-muted-foreground mt-1">{errors.dashboard}</p>
          </div>
          <button
            onClick={fetchDashboardData}
            className="mt-4 px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  // Empty state when no data
  const hasNoData =
    !kpis && balanceHistory.length === 0 && recentTrades.length === 0;

  if (hasNoData && isInitialized) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="flex flex-col items-center gap-4 text-center max-w-md">
          <BarChart3 className="h-16 w-16 text-muted-foreground" />
          <div>
            <h2 className="text-xl font-semibold">No Trading Data</h2>
            <p className="text-muted-foreground mt-2">
              Import your trading data to see analytics and performance metrics.
              Go to the Import tab to upload your broker CSV files.
            </p>
          </div>
          <a
            href="/import"
            className="mt-4 px-6 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90"
          >
            Import Data
          </a>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border bg-card/50 backdrop-blur-sm sticky top-0 z-40">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold tracking-tight">Dashboard</h1>
              <p className="text-sm text-muted-foreground">
                Trading performance overview
              </p>
            </div>

            <div className="flex items-center gap-4">
              {/* Date Range Picker */}
              <DateRangePicker
                dateRange={dateRange}
                onDateRangeChange={handleDateRangeChange}
              />

              {/* Refresh Button */}
              <button
                onClick={fetchDashboardData}
                disabled={loading.dashboard}
                className={cn(
                  "flex items-center gap-2 px-3 py-2 rounded-md text-sm font-medium",
                  "bg-secondary text-secondary-foreground hover:bg-secondary/80",
                  "disabled:opacity-50 disabled:cursor-not-allowed",
                )}
              >
                <RefreshCw
                  className={cn("h-4 w-4", loading.dashboard && "animate-spin")}
                />
                Refresh
              </button>
            </div>
          </div>

          {/* Last updated */}
          {lastUpdated && (
            <p className="text-xs text-muted-foreground mt-2">
              Last updated: {lastUpdated.toLocaleTimeString()}
            </p>
          )}
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-6 space-y-6">
        {/* KPI Grid */}
        {kpiItems.length > 0 && (
          <section>
            <KPIGrid items={kpiItems} columns={6} />
          </section>
        )}

        {/* Charts Row */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Balance Chart */}
          {formattedBalanceData.length > 0 && (
            <ChartCard
              title="Account Balance"
              subtitle="Equity curve over time"
              onExpand={() => setExpandedChart("balance")}
              onDownload={() => console.log("Download balance chart")}
            >
              {balanceByAccount && balanceByAccount.series.length > 1 ? (
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
              )}
            </ChartCard>
          )}

          {/* Win Rate Chart */}
          {formattedWinRateData.length > 0 && (
            <ChartCard
              title="Win Rate by Instrument"
              subtitle="Performance breakdown"
              onExpand={() => setExpandedChart("winRate")}
            >
              <WinRateChart data={formattedWinRateData} height={300} />
            </ChartCard>
          )}
        </div>

        {/* Second Row */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Monthly P&L Chart */}
          {monthlyPnL.length > 0 && (
            <div className="lg:col-span-2">
              <ChartCard
                title="Monthly P&L"
                subtitle="Profit and loss by month"
                onExpand={() => setExpandedChart("monthlyPnL")}
              >
                {monthlyPnLByAccount &&
                monthlyPnLByAccount.series.length > 1 ? (
                  <MultiAccountMonthlyPnLChart
                    series={monthlyPnLByAccount.series}
                    total={monthlyPnLByAccount.total}
                    height={280}
                    showTotal={false}
                    stacked={true}
                  />
                ) : (
                  <MonthlyPnLChart
                    data={monthlyPnL}
                    height={280}
                    currency={displayCurrency}
                  />
                )}
              </ChartCard>
            </div>
          )}

          {/* Recent Trades */}
          <div className="lg:col-span-1">
            <RecentTradesList
              trades={recentTrades}
              maxItems={5}
              showHeader
              title="Recent Trades"
              loading={loading.recentTrades}
            />
          </div>
        </div>
      </main>

      {/* Expanded Balance Chart Modal */}
      <ExpandedChartModal
        isOpen={expandedChart === "balance"}
        onClose={() => setExpandedChart(null)}
        title="Account Balance"
        subtitle="Equity curve over time - All accounts"
      >
        {balanceByAccount && balanceByAccount.series.length > 1 ? (
          <MultiAccountBalanceChart
            series={balanceByAccount.series}
            total={balanceByAccount.total}
            height={550}
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
        )}
      </ExpandedChartModal>

      {/* Expanded Monthly P&L Chart Modal */}
      <ExpandedChartModal
        isOpen={expandedChart === "monthlyPnL"}
        onClose={() => setExpandedChart(null)}
        title="Monthly P&L"
        subtitle="Profit and loss by month - All accounts"
      >
        {monthlyPnLByAccount && monthlyPnLByAccount.series.length > 1 ? (
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
        )}
      </ExpandedChartModal>

      {/* Expanded Win Rate Chart Modal */}
      <ExpandedChartModal
        isOpen={expandedChart === "winRate"}
        onClose={() => setExpandedChart(null)}
        title="Win Rate by Instrument"
        subtitle="Performance breakdown across different markets"
      >
        <WinRateChart
          data={formattedWinRateData}
          height={600}
          layout="horizontal"
        />
      </ExpandedChartModal>
    </div>
  );
}
