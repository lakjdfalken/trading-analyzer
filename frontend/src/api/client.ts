import type { Trade } from "@/components/trades/RecentTradesList";

// API Configuration
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

// Types
export interface ApiResponse<T> {
  data: T;
  success: boolean;
  error?: string;
}

export interface DateRange {
  from: string; // ISO date string
  to: string; // ISO date string
}

export interface KPIResponse {
  totalPnl: number;
  winRate: number;
  avgWin: number;
  avgLoss: number;
  profitFactor: number;
  maxDrawdown: number;
  totalTrades: number;
  winningTrades: number;
  losingTrades: number;
  todayPnl: number;
  todayTrades: number;
  openPositions: number;
  totalExposure: number;
  avgTradeDuration: number; // in minutes
  dailyLossUsed: number;
  dailyLossLimit: number;
  currency?: string;
}

export interface BalanceDataPoint {
  date: string;
  balance: number;
}

export interface MonthlyPnLDataPoint {
  month: string;
  pnl: number;
  trades: number;
  winRate: number;
}

export interface WinRateByInstrument {
  name: string;
  winRate: number;
  wins: number;
  losses: number;
  trades: number;
}

export interface DashboardData {
  kpis: KPIResponse;
  balanceHistory: BalanceDataPoint[];
  monthlyPnL: MonthlyPnLDataPoint[];
  winRateByInstrument: WinRateByInstrument[];
  recentTrades: Trade[];
}

export interface InstrumentOption {
  value: string;
  label: string;
}

export interface FilterParams {
  dateRange?: DateRange;
  instruments?: string[];
}

// API Error class
export class ApiError extends Error {
  constructor(
    message: string,
    public status?: number,
    public code?: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

// Fetch wrapper with error handling
async function fetchApi<T>(
  endpoint: string,
  options?: RequestInit,
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;

  try {
    const response = await fetch(url, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...options?.headers,
      },
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new ApiError(
        errorData.message || `HTTP error ${response.status}`,
        response.status,
        errorData.code,
      );
    }

    return response.json();
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    throw new ApiError(
      error instanceof Error ? error.message : "Network error",
    );
  }
}

// Build query string from params
function buildQueryString(params: Record<string, unknown>): string {
  const searchParams = new URLSearchParams();

  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null) {
      if (Array.isArray(value)) {
        value.forEach((v) => searchParams.append(key, String(v)));
      } else if (typeof value === "object") {
        searchParams.append(key, JSON.stringify(value));
      } else {
        searchParams.append(key, String(value));
      }
    }
  });

  const queryString = searchParams.toString();
  return queryString ? `?${queryString}` : "";
}

// API Client
export const apiClient = {
  // Dashboard endpoints
  dashboard: {
    // Get all dashboard data in one call
    getData: async (filters?: FilterParams): Promise<DashboardData> => {
      const query = filters
        ? buildQueryString({
            from: filters.dateRange?.from,
            to: filters.dateRange?.to,
            instruments: filters.instruments,
          })
        : "";
      return fetchApi<DashboardData>(`/api/dashboard${query}`);
    },

    // Get KPIs only
    getKPIs: async (filters?: FilterParams): Promise<KPIResponse> => {
      const query = filters
        ? buildQueryString({
            from: filters.dateRange?.from,
            to: filters.dateRange?.to,
            instruments: filters.instruments,
          })
        : "";
      return fetchApi<KPIResponse>(`/api/dashboard/kpis${query}`);
    },

    // Get balance history
    getBalanceHistory: async (
      filters?: FilterParams,
    ): Promise<BalanceDataPoint[]> => {
      const query = filters
        ? buildQueryString({
            from: filters.dateRange?.from,
            to: filters.dateRange?.to,
            instruments: filters.instruments,
          })
        : "";
      return fetchApi<BalanceDataPoint[]>(`/api/dashboard/balance${query}`);
    },

    // Get monthly P&L
    getMonthlyPnL: async (
      filters?: FilterParams,
    ): Promise<MonthlyPnLDataPoint[]> => {
      const query = filters
        ? buildQueryString({
            from: filters.dateRange?.from,
            to: filters.dateRange?.to,
            instruments: filters.instruments,
          })
        : "";
      return fetchApi<MonthlyPnLDataPoint[]>(
        `/api/dashboard/monthly-pnl${query}`,
      );
    },

    // Get win rate by instrument
    getWinRateByInstrument: async (
      filters?: FilterParams,
    ): Promise<WinRateByInstrument[]> => {
      const query = filters
        ? buildQueryString({
            from: filters.dateRange?.from,
            to: filters.dateRange?.to,
            instruments: filters.instruments,
          })
        : "";
      return fetchApi<WinRateByInstrument[]>(
        `/api/dashboard/win-rate-by-instrument${query}`,
      );
    },
  },

  // Trades endpoints
  trades: {
    // Get recent trades
    getRecent: async (
      limit: number = 10,
      filters?: FilterParams,
    ): Promise<Trade[]> => {
      const query = buildQueryString({
        limit,
        from: filters?.dateRange?.from,
        to: filters?.dateRange?.to,
        instruments: filters?.instruments,
      });
      return fetchApi<Trade[]>(`/api/trades/recent${query}`);
    },

    // Get all trades with pagination
    getAll: async (
      page: number = 1,
      pageSize: number = 50,
      filters?: FilterParams,
    ): Promise<{ trades: Trade[]; total: number; pages: number }> => {
      const query = buildQueryString({
        page,
        pageSize,
        from: filters?.dateRange?.from,
        to: filters?.dateRange?.to,
        instruments: filters?.instruments,
      });
      return fetchApi(`/api/trades${query}`);
    },

    // Get single trade by ID
    getById: async (id: string): Promise<Trade> => {
      return fetchApi<Trade>(`/api/trades/${id}`);
    },
  },

  // Instruments endpoints
  instruments: {
    // Get available instruments
    getAll: async (): Promise<InstrumentOption[]> => {
      return fetchApi<InstrumentOption[]>("/api/instruments");
    },
  },

  // Health check
  health: async (): Promise<{ status: string }> => {
    return fetchApi<{ status: string }>("/api/health");
  },
};

export default apiClient;
