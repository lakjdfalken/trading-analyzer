// API Endpoints Constants

export const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

export const ENDPOINTS = {
  // Dashboard
  DASHBOARD: "/dashboard",
  DASHBOARD_KPIS: "/dashboard/kpis",
  DASHBOARD_BALANCE: "/dashboard/balance",
  DASHBOARD_MONTHLY_PNL: "/dashboard/monthly-pnl",
  DASHBOARD_WIN_RATE_BY_INSTRUMENT: "/dashboard/win-rate-by-instrument",

  // Trades
  TRADES: "/trades",
  TRADES_RECENT: "/trades/recent",
  TRADE_BY_ID: (id: string) => `/trades/${id}`,

  // Instruments
  INSTRUMENTS: "/instruments",

  // Account
  ACCOUNT: "/account",
  ACCOUNT_INFO: "/account/info",
  ACCOUNT_BALANCE: "/account/balance",

  // Analytics
  ANALYTICS: "/analytics",
  ANALYTICS_PERFORMANCE: "/analytics/performance",
  ANALYTICS_DRAWDOWN: "/analytics/drawdown",
  ANALYTICS_DISTRIBUTION: "/analytics/distribution",

  // Settings
  SETTINGS: "/settings",
  SETTINGS_PREFERENCES: "/settings/preferences",
  SETTINGS_ALERTS: "/settings/alerts",

  // Health
  HEALTH: "/health",
} as const;

// Full URL builders
export const buildUrl = (endpoint: string, params?: Record<string, string | number | boolean | undefined>): string => {
  const url = new URL(`${API_BASE}${endpoint}`);

  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        url.searchParams.append(key, String(value));
      }
    });
  }

  return url.toString();
};

export default ENDPOINTS;
