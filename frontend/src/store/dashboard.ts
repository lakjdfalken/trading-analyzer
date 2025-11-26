import { create } from "zustand";
import { devtools, persist } from "zustand/middleware";
import type { Trade } from "@/components/trades/RecentTradesList";
import type {
  KPIResponse,
  BalanceDataPoint,
  MonthlyPnLDataPoint,
  WinRateByInstrument,
  FilterParams,
  InstrumentOption,
} from "@/api/client";

// Date range preset type - matches filter types
export type DateRangePreset =
  | "today"
  | "yesterday"
  | "last7days"
  | "last30days"
  | "thisMonth"
  | "lastMonth"
  | "thisQuarter"
  | "lastQuarter"
  | "thisYear"
  | "lastYear"
  | "allTime"
  | "custom";

// Date range state
export interface DateRangeState {
  from: Date | undefined;
  to: Date | undefined;
  preset: DateRangePreset;
}

// Loading state for different data sections
export interface LoadingState {
  kpis: boolean;
  balanceHistory: boolean;
  monthlyPnL: boolean;
  winRateByInstrument: boolean;
  recentTrades: boolean;
  instruments: boolean;
  dashboard: boolean;
}

// Error state
export interface ErrorState {
  kpis: string | null;
  balanceHistory: string | null;
  monthlyPnL: string | null;
  winRateByInstrument: string | null;
  recentTrades: string | null;
  instruments: string | null;
  dashboard: string | null;
}

// Dashboard store state
export interface DashboardState {
  // Filters
  dateRange: DateRangeState;
  selectedInstruments: string[];
  availableInstruments: InstrumentOption[];

  // Data
  kpis: KPIResponse | null;
  balanceHistory: BalanceDataPoint[];
  monthlyPnL: MonthlyPnLDataPoint[];
  winRateByInstrument: WinRateByInstrument[];
  recentTrades: Trade[];

  // UI State
  loading: LoadingState;
  errors: ErrorState;
  lastUpdated: Date | null;
  isInitialized: boolean;

  // Actions - Filters
  setDateRange: (dateRange: Partial<DateRangeState>) => void;
  setDateRangePreset: (preset: DateRangePreset) => void;
  setSelectedInstruments: (instruments: string[]) => void;
  toggleInstrument: (instrument: string) => void;
  clearFilters: () => void;

  // Actions - Data
  setKPIs: (kpis: KPIResponse) => void;
  setBalanceHistory: (data: BalanceDataPoint[]) => void;
  setMonthlyPnL: (data: MonthlyPnLDataPoint[]) => void;
  setWinRateByInstrument: (data: WinRateByInstrument[]) => void;
  setRecentTrades: (trades: Trade[]) => void;
  setAvailableInstruments: (instruments: InstrumentOption[]) => void;

  // Actions - Loading
  setLoading: (key: keyof LoadingState, value: boolean) => void;
  setAllLoading: (value: boolean) => void;

  // Actions - Errors
  setError: (key: keyof ErrorState, error: string | null) => void;
  clearErrors: () => void;

  // Actions - Utility
  setLastUpdated: (date: Date) => void;
  setInitialized: (value: boolean) => void;
  getFilterParams: () => FilterParams;
  reset: () => void;
}

// Helper to calculate date range from preset
export function getDateRangeFromPreset(preset: DateRangePreset): {
  from: Date;
  to: Date;
} {
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const to = new Date(today);
  to.setHours(23, 59, 59, 999);

  switch (preset) {
    case "today":
      return { from: today, to };

    case "yesterday": {
      const yesterday = new Date(today);
      yesterday.setDate(yesterday.getDate() - 1);
      const yesterdayEnd = new Date(yesterday);
      yesterdayEnd.setHours(23, 59, 59, 999);
      return { from: yesterday, to: yesterdayEnd };
    }

    case "last7days": {
      const from = new Date(today);
      from.setDate(from.getDate() - 6);
      return { from, to };
    }

    case "last30days": {
      const from = new Date(today);
      from.setDate(from.getDate() - 29);
      return { from, to };
    }

    case "thisMonth": {
      const from = new Date(today.getFullYear(), today.getMonth(), 1);
      return { from, to };
    }

    case "lastMonth": {
      const from = new Date(today.getFullYear(), today.getMonth() - 1, 1);
      const lastDayLastMonth = new Date(
        today.getFullYear(),
        today.getMonth(),
        0,
      );
      lastDayLastMonth.setHours(23, 59, 59, 999);
      return { from, to: lastDayLastMonth };
    }

    case "thisQuarter": {
      const quarter = Math.floor(today.getMonth() / 3);
      const from = new Date(today.getFullYear(), quarter * 3, 1);
      return { from, to };
    }

    case "lastQuarter": {
      const quarter = Math.floor(today.getMonth() / 3);
      const lastQuarter = quarter === 0 ? 3 : quarter - 1;
      const year =
        quarter === 0 ? today.getFullYear() - 1 : today.getFullYear();
      const from = new Date(year, lastQuarter * 3, 1);
      const lastDayLastQuarter = new Date(year, lastQuarter * 3 + 3, 0);
      lastDayLastQuarter.setHours(23, 59, 59, 999);
      return { from, to: lastDayLastQuarter };
    }

    case "thisYear": {
      const from = new Date(today.getFullYear(), 0, 1);
      return { from, to };
    }

    case "lastYear": {
      const from = new Date(today.getFullYear() - 1, 0, 1);
      const lastDayLastYear = new Date(today.getFullYear() - 1, 11, 31);
      lastDayLastYear.setHours(23, 59, 59, 999);
      return { from, to: lastDayLastYear };
    }

    case "allTime": {
      const from = new Date(2000, 0, 1);
      return { from, to };
    }

    case "custom":
    default:
      return { from: today, to };
  }
}

// Initial state
const initialDateRange = getDateRangeFromPreset("last30days");

const initialState: Omit<
  DashboardState,
  | "setDateRange"
  | "setDateRangePreset"
  | "setSelectedInstruments"
  | "toggleInstrument"
  | "clearFilters"
  | "setKPIs"
  | "setBalanceHistory"
  | "setMonthlyPnL"
  | "setWinRateByInstrument"
  | "setRecentTrades"
  | "setAvailableInstruments"
  | "setLoading"
  | "setAllLoading"
  | "setError"
  | "clearErrors"
  | "setLastUpdated"
  | "setInitialized"
  | "getFilterParams"
  | "reset"
> = {
  // Filters
  dateRange: {
    from: initialDateRange.from,
    to: initialDateRange.to,
    preset: "last30days",
  },
  selectedInstruments: [],
  availableInstruments: [],

  // Data
  kpis: null,
  balanceHistory: [],
  monthlyPnL: [],
  winRateByInstrument: [],
  recentTrades: [],

  // UI State
  loading: {
    kpis: false,
    balanceHistory: false,
    monthlyPnL: false,
    winRateByInstrument: false,
    recentTrades: false,
    instruments: false,
    dashboard: false,
  },
  errors: {
    kpis: null,
    balanceHistory: null,
    monthlyPnL: null,
    winRateByInstrument: null,
    recentTrades: null,
    instruments: null,
    dashboard: null,
  },
  lastUpdated: null,
  isInitialized: false,
};

// Create the store
export const useDashboardStore = create<DashboardState>()(
  devtools(
    persist(
      (set, get) => ({
        ...initialState,

        // Filter actions
        setDateRange: (dateRange) =>
          set(
            (state) => ({
              dateRange: { ...state.dateRange, ...dateRange },
            }),
            false,
            "setDateRange",
          ),

        setDateRangePreset: (preset) => {
          const { from, to } = getDateRangeFromPreset(preset);
          set({ dateRange: { from, to, preset } }, false, "setDateRangePreset");
        },

        setSelectedInstruments: (instruments) =>
          set(
            { selectedInstruments: instruments },
            false,
            "setSelectedInstruments",
          ),

        toggleInstrument: (instrument) =>
          set(
            (state) => ({
              selectedInstruments: state.selectedInstruments.includes(
                instrument,
              )
                ? state.selectedInstruments.filter((i) => i !== instrument)
                : [...state.selectedInstruments, instrument],
            }),
            false,
            "toggleInstrument",
          ),

        clearFilters: () => {
          const { from, to } = getDateRangeFromPreset("last30days");
          set(
            {
              dateRange: { from, to, preset: "last30days" },
              selectedInstruments: [],
            },
            false,
            "clearFilters",
          );
        },

        // Data actions
        setKPIs: (kpis) => set({ kpis }, false, "setKPIs"),

        setBalanceHistory: (balanceHistory) =>
          set({ balanceHistory }, false, "setBalanceHistory"),

        setMonthlyPnL: (monthlyPnL) =>
          set({ monthlyPnL }, false, "setMonthlyPnL"),

        setWinRateByInstrument: (winRateByInstrument) =>
          set({ winRateByInstrument }, false, "setWinRateByInstrument"),

        setRecentTrades: (recentTrades) =>
          set({ recentTrades }, false, "setRecentTrades"),

        setAvailableInstruments: (availableInstruments) =>
          set({ availableInstruments }, false, "setAvailableInstruments"),

        // Loading actions
        setLoading: (key, value) =>
          set(
            (state) => ({
              loading: { ...state.loading, [key]: value },
            }),
            false,
            "setLoading",
          ),

        setAllLoading: (value) =>
          set(
            {
              loading: {
                kpis: value,
                balanceHistory: value,
                monthlyPnL: value,
                winRateByInstrument: value,
                recentTrades: value,
                instruments: value,
                dashboard: value,
              },
            },
            false,
            "setAllLoading",
          ),

        // Error actions
        setError: (key, error) =>
          set(
            (state) => ({
              errors: { ...state.errors, [key]: error },
            }),
            false,
            "setError",
          ),

        clearErrors: () =>
          set(
            {
              errors: {
                kpis: null,
                balanceHistory: null,
                monthlyPnL: null,
                winRateByInstrument: null,
                recentTrades: null,
                instruments: null,
                dashboard: null,
              },
            },
            false,
            "clearErrors",
          ),

        // Utility actions
        setLastUpdated: (date) =>
          set({ lastUpdated: date }, false, "setLastUpdated"),

        setInitialized: (value) =>
          set({ isInitialized: value }, false, "setInitialized"),

        getFilterParams: () => {
          const state = get();
          return {
            dateRange: {
              from: state.dateRange.from?.toISOString() || "",
              to: state.dateRange.to?.toISOString() || "",
            },
            instruments:
              state.selectedInstruments.length > 0
                ? state.selectedInstruments
                : undefined,
          };
        },

        reset: () => set(initialState, false, "reset"),
      }),
      {
        name: "dashboard-store",
        partialize: (state) => ({
          dateRange: state.dateRange,
          selectedInstruments: state.selectedInstruments,
          // Note: isInitialized is intentionally NOT persisted
          // so data is always fetched fresh on page load
        }),
        onRehydrateStorage: () => (state) => {
          // Reset isInitialized after rehydration so data fetches on new page load
          if (state) {
            state.isInitialized = false;
          }
        },
      },
    ),
    { name: "DashboardStore" },
  ),
);

// Selectors for common derived state
export const selectIsLoading = (state: DashboardState) =>
  Object.values(state.loading).some(Boolean);

export const selectHasErrors = (state: DashboardState) =>
  Object.values(state.errors).some(Boolean);

export const selectActiveErrors = (state: DashboardState) =>
  Object.entries(state.errors)
    .filter(([, error]) => error !== null)
    .map(([key, error]) => ({ key, error }));

export default useDashboardStore;
