"use client";

import * as React from "react";
import { isValid } from "date-fns";
import {
  TrendingUp,
  TrendingDown,
  DollarSign,
  Percent,
  BarChart3,
  Target,
  RefreshCw,
  AlertCircle,
  Calendar,
  CalendarDays,
  CalendarRange,
  Activity,
} from "lucide-react";

import { KPICard, KPIGrid } from "@/components/kpi";
import { ChartCard } from "@/components/charts/ChartCard";
import { BalanceChart } from "@/components/charts/BalanceChart";

import { ExpandedChartModal } from "@/components/charts/ExpandedChartModal";
import { MultiAccountBalanceChart } from "@/components/charts/MultiAccountBalanceChart";
import type { AccountSeries } from "@/components/charts/MultiAccountBalanceChart";
import { DateRangePicker } from "@/components/filters/DateRangePicker";
import { useDashboardStore, getDateRangeFromPreset } from "@/store/dashboard";
import type { DateRangePreset } from "@/components/filters/types";
import { cn } from "@/lib/utils";
import { useCurrencyStore } from "@/store/currency";
import { useSettingsStore } from "@/store/settings";
import * as api from "@/lib/api";

export default function Home() {
  const { formatAmount } = useCurrencyStore();
  const { defaultCurrency, isLoaded: settingsLoaded } = useSettingsStore();
  const [dataCurrency, setDataCurrency] = React.useState<string | null>(null);
  const [hasHydrated, setHasHydrated] = React.useState(false);
  const [version, setVersion] = React.useState<string | null>(null);

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

  const {
    dateRange,
    selectedInstruments,
    availableInstruments,
    selectedAccountId,
    availableAccounts,
    kpis,
    balanceHistory,
    monthlyPnL,
    loading,
    errors,
    lastUpdated,
    isInitialized,
    setDateRange,
    setSelectedInstruments,
    setSelectedAccountId,
    setAvailableAccounts,
    setKPIs,
    setBalanceHistory,
    setMonthlyPnL,
    setAvailableInstruments,
    setLoading,
    setError,
    setLastUpdated,
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

  // Track if initial fetch has been done this session
  const [hasFetchedOnce, setHasFetchedOnce] = React.useState(false);

  // Wait for Zustand store to hydrate before fetching with date range
  React.useEffect(() => {
    setHasHydrated(true);
  }, []);

  // Fetch version on mount
  React.useEffect(() => {
    api
      .healthCheck()
      .then((data) => setVersion(data.version))
      .catch(() => setVersion(null));
  }, []);

  // Build date range object for API calls
  const getDateRangeForApi = React.useCallback(() => {
    return {
      from: dateRange.from,
      to: dateRange.to,
    };
  }, [dateRange.from, dateRange.to]);

  // Fetch dashboard data using centralized API client
  const fetchDashboardData = React.useCallback(async () => {
    if (!effectiveCurrency) return;

    setLoading("dashboard", true);
    setError("dashboard", null);

    try {
      const dateRangeParam = getDateRangeForApi();

      // Fetch all data in parallel using centralized API client
      const [
        kpisResult,
        balanceResult,
        monthlyResult,
        instrumentsResult,
        accountsResult,
        balanceByAccResult,
      ] = await Promise.allSettled([
        api.getKPIs(
          effectiveCurrency,
          dateRangeParam,
          selectedInstruments.length > 0 ? selectedInstruments : undefined,
          selectedAccountId,
        ),
        api.getBalanceHistory(
          effectiveCurrency,
          dateRangeParam,
          selectedAccountId,
        ),
        api.getMonthlyPnL(
          effectiveCurrency,
          dateRangeParam,
          selectedInstruments.length > 0 ? selectedInstruments : undefined,
          selectedAccountId,
        ),
        api.getInstruments(),
        api.getAccounts(),
        api.getBalanceByAccount(
          effectiveCurrency,
          dateRangeParam,
          selectedAccountId,
        ),
      ]);

      // Process KPIs
      if (kpisResult.status === "fulfilled") {
        setKPIs(kpisResult.value);
        if (kpisResult.value.currency) {
          setDataCurrency(kpisResult.value.currency);
        }
      }

      // Process balance history
      if (balanceResult.status === "fulfilled") {
        const balanceData = Array.isArray(balanceResult.value)
          ? balanceResult.value
          : (
              balanceResult.value as {
                data?: api.BalanceDataPoint[];
                currency?: string;
              }
            ).data || [];
        setBalanceHistory(balanceData);
        const response = balanceResult.value as { currency?: string };
        if (response.currency) {
          setDataCurrency(response.currency);
        }
      }

      // Process monthly P&L
      if (monthlyResult.status === "fulfilled") {
        const monthlyData = Array.isArray(monthlyResult.value)
          ? monthlyResult.value
          : (monthlyResult.value as { data?: api.MonthlyPnLDataPoint[] })
              .data || [];
        setMonthlyPnL(monthlyData);
        const response = monthlyResult.value as { currency?: string };
        if (response.currency) {
          setDataCurrency(response.currency);
        }
      }

      // Process instruments
      if (instrumentsResult.status === "fulfilled") {
        setAvailableInstruments(instrumentsResult.value);
      }

      // Process accounts
      if (accountsResult.status === "fulfilled") {
        setAvailableAccounts(accountsResult.value);
      }

      // Process balance by account
      if (balanceByAccResult.status === "fulfilled") {
        setBalanceByAccount(
          balanceByAccResult.value as typeof balanceByAccount,
        );
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
    effectiveCurrency,
    getDateRangeForApi,
    selectedInstruments,
    selectedAccountId,
    setLoading,
    setError,
    setKPIs,
    setBalanceHistory,
    setMonthlyPnL,
    setAvailableInstruments,
    setAvailableAccounts,
    setLastUpdated,
    setInitialized,
  ]);

  // Initial data fetch - wait for settings to load before fetching data
  React.useEffect(() => {
    if (hasHydrated && settingsLoaded && !hasFetchedOnce) {
      setHasFetchedOnce(true);
      fetchDashboardData();
    }
  }, [hasHydrated, settingsLoaded, hasFetchedOnce, fetchDashboardData]);

  // Refetch when account selection changes (after initial load)
  React.useEffect(() => {
    if (hasFetchedOnce && hasHydrated) {
      fetchDashboardData();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedAccountId]);

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

  // Get the display currency (from data or effective currency)
  // No fallback per .rules - effectiveCurrency must be set from settings
  const displayCurrency = dataCurrency || effectiveCurrency;

  // Currency is required for all charts - show message if not set
  const currencyNotSet = !displayCurrency;

  // Handle account change
  const handleAccountChange = React.useCallback(
    (accountId: number | null) => {
      setSelectedAccountId(accountId);
      // Refetch is triggered by the useEffect watching selectedAccountId
    },
    [setSelectedAccountId],
  );

  // Build KPI items from store data
  const kpiItems = React.useMemo(() => {
    if (!kpis) return [];

    const currency = kpis.currency || displayCurrency;

    return [
      {
        title: "Total P&L",
        value: kpis.totalPnl,
        subtitle: "Selected period",
        icon: DollarSign,
        variant:
          kpis.totalPnl >= 0 ? ("success" as const) : ("danger" as const),
        isCurrency: true,
        currency,
      },
      {
        title: "Win Rate",
        value: `${(kpis.winRate ?? 0).toFixed(1)}%`,
        subtitle: `${kpis.totalTrades ?? 0} trades`,
        icon: Target,
        variant:
          (kpis.winRate ?? 0) >= 50
            ? ("success" as const)
            : ("warning" as const),
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
        value: (kpis.profitFactor ?? 0).toFixed(2),
        subtitle: "Risk/Reward ratio",
        icon: BarChart3,
        variant:
          (kpis.profitFactor ?? 0) >= 1.5
            ? ("success" as const)
            : ("default" as const),
        tooltip:
          "Total profits ÷ Total losses. Values above 1.0 mean you're profitable overall. Above 1.5 is considered good.",
      },
      {
        title: "Max Drawdown",
        value: `${(kpis.maxDrawdown ?? 0).toFixed(1)}%`,
        subtitle: "Peak to trough",
        icon: Percent,
        variant:
          (kpis.maxDrawdown ?? 0) > 10
            ? ("danger" as const)
            : ("warning" as const),
        tooltip:
          "Largest percentage drop from a peak balance to a subsequent low point. Lower is better.",
      },
    ];
  }, [kpis, displayCurrency]);

  // Build daily average KPI items
  const dailyKpiItems = React.useMemo(() => {
    if (!kpis) return [];

    const currency = kpis.currency || displayCurrency;

    return [
      {
        title: "Avg Daily P&L",
        value: kpis.avgDailyPnl ?? 0,
        subtitle: "Per trading day",
        icon: Calendar,
        variant:
          (kpis.avgDailyPnl ?? 0) >= 0
            ? ("success" as const)
            : ("danger" as const),
        isCurrency: true,
        currency,
      },
      {
        title: "Avg Daily Points",
        value: (kpis.avgDailyPoints ?? 0).toFixed(1),
        subtitle: "Points per day",
        icon: Activity,
        variant: "default" as const,
      },
      {
        title: "Avg Trades/Day",
        value: (kpis.avgTradesPerDay ?? 0).toFixed(1),
        subtitle: "Trade frequency",
        icon: BarChart3,
        variant: "default" as const,
      },
      {
        title: "Best Day",
        value: kpis.bestDayPnl ?? 0,
        subtitle: "Highest daily P&L",
        icon: TrendingUp,
        variant: "success" as const,
        isCurrency: true,
        currency,
      },
      {
        title: "Worst Day",
        value: kpis.worstDayPnl ?? 0,
        subtitle: "Lowest daily P&L",
        icon: TrendingDown,
        variant: "danger" as const,
        isCurrency: true,
        currency,
      },
    ];
  }, [kpis, displayCurrency]);

  // Build monthly average KPI items
  const monthlyKpiItems = React.useMemo(() => {
    if (!kpis) return [];

    const currency = kpis.currency || displayCurrency;

    return [
      {
        title: "Avg Monthly P&L",
        value: kpis.avgMonthlyPnl ?? 0,
        subtitle: "Per month",
        icon: CalendarDays,
        variant:
          (kpis.avgMonthlyPnl ?? 0) >= 0
            ? ("success" as const)
            : ("danger" as const),
        isCurrency: true,
        currency,
      },
      {
        title: "Avg Monthly Points",
        value: (kpis.avgMonthlyPoints ?? 0).toFixed(1),
        subtitle: "Points per month",
        icon: Activity,
        variant: "default" as const,
      },
      {
        title: "Avg Trades/Month",
        value: (kpis.avgTradesPerMonth ?? 0).toFixed(1),
        subtitle: "Monthly frequency",
        icon: BarChart3,
        variant: "default" as const,
      },
      {
        title: "Best Month",
        value: kpis.bestMonthPnl ?? 0,
        subtitle: "Highest monthly P&L",
        icon: TrendingUp,
        variant: "success" as const,
        isCurrency: true,
        currency,
      },
      {
        title: "Worst Month",
        value: kpis.worstMonthPnl ?? 0,
        subtitle: "Lowest monthly P&L",
        icon: TrendingDown,
        variant: "danger" as const,
        isCurrency: true,
        currency,
      },
    ];
  }, [kpis, displayCurrency]);

  // Build yearly KPI items
  const yearlyKpiItems = React.useMemo(() => {
    if (!kpis) return [];

    const currency = kpis.currency || displayCurrency;

    return [
      {
        title: "Current Year P&L",
        value: kpis.currentYearPnl ?? 0,
        subtitle: new Date().getFullYear().toString(),
        icon: CalendarRange,
        variant:
          (kpis.currentYearPnl ?? 0) >= 0
            ? ("success" as const)
            : ("danger" as const),
        isCurrency: true,
        currency,
      },
      {
        title: "Current Year Points",
        value: (kpis.currentYearPoints ?? 0).toFixed(1),
        subtitle: new Date().getFullYear().toString(),
        icon: Activity,
        variant: "default" as const,
      },
      {
        title: "Avg Yearly P&L",
        value: kpis.avgYearlyPnl ?? 0,
        subtitle: "Per year average",
        icon: CalendarRange,
        variant:
          (kpis.avgYearlyPnl ?? 0) >= 0
            ? ("success" as const)
            : ("danger" as const),
        isCurrency: true,
        currency,
      },
    ];
  }, [kpis, displayCurrency]);

  // Format balance data for chart
  const formattedBalanceData = React.useMemo(() => {
    return balanceHistory.map((point) => ({
      date: new Date(point.date).toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
        year: "numeric",
      }),
      balance: point.balance,
    }));
  }, [balanceHistory]);

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
  const hasNoData = !kpis && balanceHistory.length === 0;

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

          {/* Last updated and version */}
          <div className="flex items-center gap-4 mt-2">
            {lastUpdated && (
              <p className="text-xs text-muted-foreground">
                Last updated: {lastUpdated.toLocaleTimeString()}
              </p>
            )}
            {version && (
              <p className="text-xs text-muted-foreground">v{version}</p>
            )}
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-6 space-y-6">
        {/* KPI Grid - Main Metrics */}
        {kpiItems.length > 0 && (
          <section>
            <h2 className="text-lg font-semibold mb-3">Performance Overview</h2>
            <KPIGrid items={kpiItems} columns={6} />
          </section>
        )}

        {/* KPI Grid - Daily Averages */}
        {dailyKpiItems.length > 0 && (
          <section>
            <h2 className="text-lg font-semibold mb-3">Daily Averages</h2>
            <KPIGrid items={dailyKpiItems} columns={5} />
          </section>
        )}

        {/* KPI Grid - Monthly Averages */}
        {monthlyKpiItems.length > 0 && (
          <section>
            <h2 className="text-lg font-semibold mb-3">Monthly Averages</h2>
            <KPIGrid items={monthlyKpiItems} columns={5} />
          </section>
        )}

        {/* KPI Grid - Yearly Summary */}
        {yearlyKpiItems.length > 0 && (
          <section>
            <h2 className="text-lg font-semibold mb-3">Yearly Summary</h2>
            <KPIGrid items={yearlyKpiItems} columns={3} />
          </section>
        )}

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
            ) : currencyNotSet ? (
              <div className="flex items-center justify-center h-[300px] text-muted-foreground">
                Please set your default currency in Settings
              </div>
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
        ) : currencyNotSet ? (
          <div className="flex items-center justify-center h-[600px] text-muted-foreground">
            Please set your default currency in Settings
          </div>
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
    </div>
  );
}
