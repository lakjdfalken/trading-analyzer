import { useCallback, useEffect, useRef } from "react";
import { useDashboardStore, type DateRangePreset } from "@/store/dashboard";
import { apiClient, type FilterParams } from "@/api/client";

// Hook options
interface UseDashboardOptions {
  autoFetch?: boolean;
  refetchInterval?: number | null; // in milliseconds, null to disable
  onError?: (error: Error) => void;
  onSuccess?: () => void;
}

// Default options
const defaultOptions: UseDashboardOptions = {
  autoFetch: true,
  refetchInterval: null,
  onError: undefined,
  onSuccess: undefined,
};

export function useDashboard(options: UseDashboardOptions = {}) {
  const opts = { ...defaultOptions, ...options };
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  // Store state
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
    setDateRangePreset,
    setSelectedInstruments,
    toggleInstrument,
    clearFilters,
    setKPIs,
    setBalanceHistory,
    setMonthlyPnL,
    setWinRateByInstrument,
    setRecentTrades,
    setAvailableInstruments,
    setLoading,
    setAllLoading,
    setError,
    clearErrors,
    setLastUpdated,
    setInitialized,
    getFilterParams,
  } = useDashboardStore();

  // Build filter params from current state
  const buildFilterParams = useCallback((): FilterParams => {
    return {
      dateRange:
        dateRange.from && dateRange.to
          ? {
              from: dateRange.from.toISOString(),
              to: dateRange.to.toISOString(),
            }
          : undefined,
      instruments:
        selectedInstruments.length > 0 ? selectedInstruments : undefined,
    };
  }, [dateRange, selectedInstruments]);

  // Fetch all dashboard data
  const fetchDashboardData = useCallback(async () => {
    const filterParams = buildFilterParams();

    setLoading("dashboard", true);
    clearErrors();

    try {
      const data = await apiClient.dashboard.getData(filterParams);

      setKPIs(data.kpis);
      setBalanceHistory(data.balanceHistory);
      setMonthlyPnL(data.monthlyPnL);
      setWinRateByInstrument(data.winRateByInstrument);
      setRecentTrades(data.recentTrades);
      setLastUpdated(new Date());
      setInitialized(true);

      opts.onSuccess?.();
    } catch (error) {
      const errorMessage =
        error instanceof Error ? error.message : "Failed to fetch dashboard data";
      setError("dashboard", errorMessage);
      opts.onError?.(error instanceof Error ? error : new Error(errorMessage));
    } finally {
      setLoading("dashboard", false);
    }
  }, [
    buildFilterParams,
    setLoading,
    clearErrors,
    setKPIs,
    setBalanceHistory,
    setMonthlyPnL,
    setWinRateByInstrument,
    setRecentTrades,
    setLastUpdated,
    setInitialized,
    setError,
    opts,
  ]);

  // Fetch KPIs only
  const fetchKPIs = useCallback(async () => {
    const filterParams = buildFilterParams();
    setLoading("kpis", true);
    setError("kpis", null);

    try {
      const data = await apiClient.dashboard.getKPIs(filterParams);
      setKPIs(data);
      opts.onSuccess?.();
    } catch (error) {
      const errorMessage =
        error instanceof Error ? error.message : "Failed to fetch KPIs";
      setError("kpis", errorMessage);
      opts.onError?.(error instanceof Error ? error : new Error(errorMessage));
    } finally {
      setLoading("kpis", false);
    }
  }, [buildFilterParams, setLoading, setError, setKPIs, opts]);

  // Fetch balance history only
  const fetchBalanceHistory = useCallback(async () => {
    const filterParams = buildFilterParams();
    setLoading("balanceHistory", true);
    setError("balanceHistory", null);

    try {
      const data = await apiClient.dashboard.getBalanceHistory(filterParams);
      setBalanceHistory(data);
      opts.onSuccess?.();
    } catch (error) {
      const errorMessage =
        error instanceof Error ? error.message : "Failed to fetch balance history";
      setError("balanceHistory", errorMessage);
      opts.onError?.(error instanceof Error ? error : new Error(errorMessage));
    } finally {
      setLoading("balanceHistory", false);
    }
  }, [buildFilterParams, setLoading, setError, setBalanceHistory, opts]);

  // Fetch monthly P&L only
  const fetchMonthlyPnL = useCallback(async () => {
    const filterParams = buildFilterParams();
    setLoading("monthlyPnL", true);
    setError("monthlyPnL", null);

    try {
      const data = await apiClient.dashboard.getMonthlyPnL(filterParams);
      setMonthlyPnL(data);
      opts.onSuccess?.();
    } catch (error) {
      const errorMessage =
        error instanceof Error ? error.message : "Failed to fetch monthly P&L";
      setError("monthlyPnL", errorMessage);
      opts.onError?.(error instanceof Error ? error : new Error(errorMessage));
    } finally {
      setLoading("monthlyPnL", false);
    }
  }, [buildFilterParams, setLoading, setError, setMonthlyPnL, opts]);

  // Fetch win rate by instrument only
  const fetchWinRateByInstrument = useCallback(async () => {
    const filterParams = buildFilterParams();
    setLoading("winRateByInstrument", true);
    setError("winRateByInstrument", null);

    try {
      const data = await apiClient.dashboard.getWinRateByInstrument(filterParams);
      setWinRateByInstrument(data);
      opts.onSuccess?.();
    } catch (error) {
      const errorMessage =
        error instanceof Error ? error.message : "Failed to fetch win rate data";
      setError("winRateByInstrument", errorMessage);
      opts.onError?.(error instanceof Error ? error : new Error(errorMessage));
    } finally {
      setLoading("winRateByInstrument", false);
    }
  }, [buildFilterParams, setLoading, setError, setWinRateByInstrument, opts]);

  // Fetch recent trades only
  const fetchRecentTrades = useCallback(
    async (limit: number = 10) => {
      const filterParams = buildFilterParams();
      setLoading("recentTrades", true);
      setError("recentTrades", null);

      try {
        const data = await apiClient.trades.getRecent(limit, filterParams);
        setRecentTrades(data);
        opts.onSuccess?.();
      } catch (error) {
        const errorMessage =
          error instanceof Error ? error.message : "Failed to fetch recent trades";
        setError("recentTrades", errorMessage);
        opts.onError?.(error instanceof Error ? error : new Error(errorMessage));
      } finally {
        setLoading("recentTrades", false);
      }
    },
    [buildFilterParams, setLoading, setError, setRecentTrades, opts]
  );

  // Fetch available instruments
  const fetchInstruments = useCallback(async () => {
    setLoading("instruments", true);
    setError("instruments", null);

    try {
      const data = await apiClient.instruments.getAll();
      setAvailableInstruments(data);
      opts.onSuccess?.();
    } catch (error) {
      const errorMessage =
        error instanceof Error ? error.message : "Failed to fetch instruments";
      setError("instruments", errorMessage);
      opts.onError?.(error instanceof Error ? error : new Error(errorMessage));
    } finally {
      setLoading("instruments", false);
    }
  }, [setLoading, setError, setAvailableInstruments, opts]);

  // Refresh all data
  const refresh = useCallback(() => {
    return fetchDashboardData();
  }, [fetchDashboardData]);

  // Update date range and optionally refetch
  const updateDateRange = useCallback(
    (from: Date | undefined, to: Date | undefined, shouldRefetch = true) => {
      setDateRange({ from, to, preset: "custom" });
      if (shouldRefetch) {
        // Use setTimeout to ensure state is updated before fetching
        setTimeout(() => fetchDashboardData(), 0);
      }
    },
    [setDateRange, fetchDashboardData]
  );

  // Update date range preset and optionally refetch
  const updateDateRangePreset = useCallback(
    (preset: DateRangePreset, shouldRefetch = true) => {
      setDateRangePreset(preset);
      if (shouldRefetch) {
        setTimeout(() => fetchDashboardData(), 0);
      }
    },
    [setDateRangePreset, fetchDashboardData]
  );

  // Update selected instruments and optionally refetch
  const updateInstruments = useCallback(
    (instruments: string[], shouldRefetch = true) => {
      setSelectedInstruments(instruments);
      if (shouldRefetch) {
        setTimeout(() => fetchDashboardData(), 0);
      }
    },
    [setSelectedInstruments, fetchDashboardData]
  );

  // Reset filters and refetch
  const resetFilters = useCallback(() => {
    clearFilters();
    setTimeout(() => fetchDashboardData(), 0);
  }, [clearFilters, fetchDashboardData]);

  // Auto-fetch on mount if enabled
  useEffect(() => {
    if (opts.autoFetch && !isInitialized) {
      fetchDashboardData();
      fetchInstruments();
    }
  }, [opts.autoFetch, isInitialized, fetchDashboardData, fetchInstruments]);

  // Set up refetch interval if enabled
  useEffect(() => {
    if (opts.refetchInterval && opts.refetchInterval > 0) {
      intervalRef.current = setInterval(() => {
        fetchDashboardData();
      }, opts.refetchInterval);

      return () => {
        if (intervalRef.current) {
          clearInterval(intervalRef.current);
        }
      };
    }
  }, [opts.refetchInterval, fetchDashboardData]);

  // Computed values
  const isLoading = loading.dashboard || Object.values(loading).some(Boolean);
  const hasErrors = Object.values(errors).some(Boolean);
  const activeErrors = Object.entries(errors)
    .filter(([, error]) => error !== null)
    .map(([key, error]) => ({ key, error: error as string }));

  return {
    // State
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

    // Computed
    isLoading,
    hasErrors,
    activeErrors,

    // Actions - Fetch
    fetchDashboardData,
    fetchKPIs,
    fetchBalanceHistory,
    fetchMonthlyPnL,
    fetchWinRateByInstrument,
    fetchRecentTrades,
    fetchInstruments,
    refresh,

    // Actions - Filters
    updateDateRange,
    updateDateRangePreset,
    updateInstruments,
    toggleInstrument,
    resetFilters,
    clearFilters,

    // Utilities
    getFilterParams,
  };
}

export default useDashboard;
