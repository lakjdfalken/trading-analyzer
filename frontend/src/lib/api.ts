/**
 * Centralized API client for Trading Analyzer
 *
 * All data fetching goes through this module.
 * No direct fetch() calls in components.
 */

const API_BASE = "";

// Types
export interface DateRange {
  from?: Date;
  to?: Date;
}

export interface Settings {
  defaultCurrency: string | null;
  showConverted: boolean;
}

export interface KPIMetrics {
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
  avgTradeDuration: number;
  dailyLossUsed: number;
  dailyLossLimit: number;
  currency: string;
  // Daily averages
  avgDailyPnl: number;
  avgDailyPoints: number;
  avgTradesPerDay: number;
  bestDayPnl: number;
  worstDayPnl: number;
  // Monthly averages
  avgMonthlyPnl: number;
  avgMonthlyPoints: number;
  avgTradesPerMonth: number;
  bestMonthPnl: number;
  worstMonthPnl: number;
  // Yearly summary
  currentYearPnl: number;
  currentYearPoints: number;
  avgYearlyPnl: number;
}

export interface Trade {
  id: string;
  instrument: string;
  direction: "long" | "short";
  entryPrice: number;
  exitPrice: number;
  entryTime: string;
  exitTime: string;
  quantity: number;
  pnl: number;
  pnlPercent: number;
  currency: string;
}

export interface BalanceDataPoint {
  date: string;
  balance: number;
  equity?: number;
  drawdown?: number;
}

export interface MonthlyPnLDataPoint {
  month: string;
  pnl: number;
  trades: number;
  winRate: number;
}

export interface DailyPnLDataPoint {
  date: string;
  pnl: number;
  cumulativePnl: number;
  trades: number;
  previousBalance?: number | null;
  pnlPercent?: number | null;
  currency?: string;
}

export interface WinRateByInstrument {
  name: string;
  winRate: number;
  wins: number;
  losses: number;
  trades: number;
  totalPnl?: number;
}

export interface Account {
  account_id: number;
  account_name: string;
  broker_name: string;
  currency: string;
  initial_balance?: number;
  notes?: string;
  transaction_count?: number;
}

export interface Instrument {
  value: string;
  label: string;
}

// Alias types for backward compatibility with dashboard store
export type KPIResponse = KPIMetrics;
export type InstrumentOption = Instrument;

export interface FilterParams {
  dateRange?: {
    from: string;
    to: string;
  };
  instruments?: string[];
}

// Helper to build query string
function buildQueryString(params: Record<string, string | undefined>): string {
  const searchParams = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== "") {
      searchParams.append(key, value);
    }
  }
  const str = searchParams.toString();
  return str ? `?${str}` : "";
}

// Format date for API
function formatDate(date: Date | undefined): string | undefined {
  if (!date) return undefined;
  return date.toISOString().split(".")[0] + "Z";
}

// API Error class
export class APIError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "APIError";
  }
}

// Generic fetch wrapper
async function apiFetch<T>(url: string): Promise<T> {
  const response = await fetch(`${API_BASE}${url}`);
  if (!response.ok) {
    throw new APIError(response.status, `API error: ${response.statusText}`);
  }
  return response.json();
}

async function apiPost<T>(url: string, body: unknown): Promise<T> {
  const response = await fetch(`${API_BASE}${url}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    throw new APIError(response.status, `API error: ${response.statusText}`);
  }
  return response.json();
}

async function apiPut<T>(url: string, body: unknown): Promise<T> {
  const response = await fetch(`${API_BASE}${url}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    throw new APIError(response.status, `API error: ${response.statusText}`);
  }
  return response.json();
}

async function apiDelete<T>(url: string): Promise<T> {
  const response = await fetch(`${API_BASE}${url}`, {
    method: "DELETE",
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new APIError(
      response.status,
      error.detail || `API error: ${response.statusText}`,
    );
  }
  return response.json();
}

// ============================================================================
// Settings API - Must be loaded before any other data
// ============================================================================

export async function getSettings(): Promise<Settings> {
  const response = await apiFetch<{
    defaultCurrency: string | null;
    showConverted: boolean;
  }>("/api/currency/preferences");
  return {
    defaultCurrency: response.defaultCurrency,
    showConverted: response.showConverted,
  };
}

export async function updateSettings(settings: Settings): Promise<void> {
  await apiPut("/api/currency/preferences", {
    defaultCurrency: settings.defaultCurrency,
    showConverted: settings.showConverted,
  });
}

// ============================================================================
// Dashboard API
// ============================================================================

export async function getKPIs(
  currency: string,
  dateRange?: DateRange,
  instruments?: string[],
  accountId?: number | null,
): Promise<KPIMetrics> {
  const params = buildQueryString({
    currency,
    from: formatDate(dateRange?.from),
    to: formatDate(dateRange?.to),
    instruments: instruments?.join(","),
    accountId: accountId?.toString(),
  });
  return apiFetch<KPIMetrics>(`/api/dashboard/kpis${params}`);
}

export async function getBalanceHistory(
  currency: string,
  dateRange?: DateRange,
  accountId?: number | null,
): Promise<{ data: BalanceDataPoint[]; currency?: string }> {
  const params = buildQueryString({
    currency,
    from: formatDate(dateRange?.from),
    to: formatDate(dateRange?.to),
    accountId: accountId?.toString(),
  });
  return apiFetch(`/api/dashboard/balance${params}`);
}

export async function getMonthlyPnL(
  currency: string,
  dateRange?: DateRange,
  instruments?: string[],
  accountId?: number | null,
): Promise<{ data: MonthlyPnLDataPoint[]; currency?: string }> {
  const params = buildQueryString({
    currency,
    from: formatDate(dateRange?.from),
    to: formatDate(dateRange?.to),
    instruments: instruments?.join(","),
    accountId: accountId?.toString(),
  });
  return apiFetch(`/api/dashboard/monthly-pnl${params}`);
}

export async function getWinRateByInstrument(
  dateRange?: DateRange,
  accountId?: number | null,
): Promise<WinRateByInstrument[]> {
  const params = buildQueryString({
    from: formatDate(dateRange?.from),
    to: formatDate(dateRange?.to),
    accountId: accountId?.toString(),
  });
  return apiFetch(`/api/dashboard/win-rate-by-instrument${params}`);
}

export async function getEquityCurve(
  currency: string,
  dateRange?: DateRange,
  accountId?: number | null,
): Promise<{ data: BalanceDataPoint[]; currency?: string }> {
  const params = buildQueryString({
    currency,
    from: formatDate(dateRange?.from),
    to: formatDate(dateRange?.to),
    accountId: accountId?.toString(),
  });
  return apiFetch(`/api/dashboard/equity-curve${params}`);
}

export async function getBalanceByAccount(
  currency: string,
  dateRange?: DateRange,
  accountId?: number | null,
): Promise<unknown> {
  const params = buildQueryString({
    currency,
    from: formatDate(dateRange?.from),
    to: formatDate(dateRange?.to),
    accountId: accountId?.toString(),
  });
  return apiFetch(`/api/dashboard/balance-by-account${params}`);
}

export async function getMonthlyPnLByAccount(
  currency: string,
  dateRange?: DateRange,
  accountId?: number | null,
): Promise<unknown> {
  const params = buildQueryString({
    currency,
    from: formatDate(dateRange?.from),
    to: formatDate(dateRange?.to),
    accountId: accountId?.toString(),
  });
  return apiFetch(`/api/dashboard/monthly-pnl-by-account${params}`);
}

export async function getPointsByInstrument(
  dateRange?: DateRange,
  accountId?: number | null,
): Promise<unknown> {
  const params = buildQueryString({
    from: formatDate(dateRange?.from),
    to: formatDate(dateRange?.to),
    accountId: accountId?.toString(),
  });
  return apiFetch(`/api/dashboard/points-by-instrument${params}`);
}

// ============================================================================
// Analytics API
// ============================================================================

export async function getDailyPnL(
  currency: string,
  dateRange?: DateRange,
  accountId?: number | null,
): Promise<DailyPnLDataPoint[]> {
  const params = buildQueryString({
    currency,
    from: formatDate(dateRange?.from),
    to: formatDate(dateRange?.to),
    accountId: accountId?.toString(),
  });
  return apiFetch(`/api/analytics/daily-pnl${params}`);
}

export async function getDailyPnLByAccount(
  currency: string,
  dateRange?: DateRange,
  accountId?: number | null,
): Promise<unknown> {
  const params = buildQueryString({
    currency,
    from: formatDate(dateRange?.from),
    to: formatDate(dateRange?.to),
    accountId: accountId?.toString(),
  });
  return apiFetch(`/api/analytics/daily-pnl-by-account${params}`);
}

export async function getHourlyPerformance(
  currency: string,
  dateRange?: DateRange,
  accountId?: number | null,
): Promise<unknown> {
  const params = buildQueryString({
    currency,
    from: formatDate(dateRange?.from),
    to: formatDate(dateRange?.to),
    accountId: accountId?.toString(),
  });
  return apiFetch(`/api/analytics/performance/hourly${params}`);
}

export async function getWeekdayPerformance(
  currency: string,
  dateRange?: DateRange,
  accountId?: number | null,
): Promise<unknown> {
  const params = buildQueryString({
    currency,
    from: formatDate(dateRange?.from),
    to: formatDate(dateRange?.to),
    accountId: accountId?.toString(),
  });
  return apiFetch(`/api/analytics/performance/weekday${params}`);
}

export async function getStreaks(
  dateRange?: DateRange,
  accountId?: number | null,
): Promise<unknown> {
  const params = buildQueryString({
    from: formatDate(dateRange?.from),
    to: formatDate(dateRange?.to),
    accountId: accountId?.toString(),
  });
  return apiFetch(`/api/analytics/streaks${params}`);
}

export async function getTradeDuration(
  dateRange?: DateRange,
  accountId?: number | null,
): Promise<unknown> {
  const params = buildQueryString({
    from: formatDate(dateRange?.from),
    to: formatDate(dateRange?.to),
    accountId: accountId?.toString(),
  });
  return apiFetch(`/api/analytics/trade-duration${params}`);
}

export async function getPositionSize(
  currency: string,
  dateRange?: DateRange,
  accountId?: number | null,
): Promise<unknown> {
  const params = buildQueryString({
    currency,
    from: formatDate(dateRange?.from),
    to: formatDate(dateRange?.to),
    accountId: accountId?.toString(),
  });
  return apiFetch(`/api/analytics/position-size${params}`);
}

export async function getFunding(
  currency: string,
  dateRange?: DateRange,
  accountId?: number | null,
): Promise<unknown> {
  const params = buildQueryString({
    currency,
    from: formatDate(dateRange?.from),
    to: formatDate(dateRange?.to),
    accountId: accountId?.toString(),
  });
  return apiFetch(`/api/analytics/funding${params}`);
}

// Spread Cost Types
export interface SpreadCostDataPoint {
  month: string;
  month_key: string;
  spread_cost: number;
  trades: number;
  avg_spread_cost: number;
  instruments: Record<string, number>;
}

export interface SpreadCostByInstrument {
  instrument: string;
  spread_cost: number;
  trades: number;
  avg_spread_cost: number;
}

export interface SpreadCostResponse {
  monthly: SpreadCostDataPoint[];
  by_instrument: SpreadCostByInstrument[];
  total_spread_cost: number;
  total_trades: number;
  avg_spread_per_trade: number;
  currency: string;
}

// Trade Frequency Types
export interface DailyTradeCount {
  date: string;
  trades: number;
}

export interface MonthlyTradeCount {
  month: string;
  trades: number;
  trading_days: number;
}

export interface YearlyTradeCount {
  year: number;
  trades: number;
  trading_days: number;
  trading_months: number;
}

export interface AccountTradeFrequency {
  account_id: number;
  account_name: string;
  daily: DailyTradeCount[];
  monthly: MonthlyTradeCount[];
  yearly: YearlyTradeCount[];
  total_trades: number;
  total_trading_days: number;
  avg_trades_per_day: number;
  avg_trades_per_trading_day: number;
  avg_trades_per_month: number;
}

export interface TradeFrequencyResponse {
  by_account: AccountTradeFrequency[];
  aggregated: AccountTradeFrequency;
  date_range_days: number;
}

export async function getTradeFrequency(
  dateRange?: DateRange,
  accountId?: number | null,
): Promise<TradeFrequencyResponse> {
  const params = buildQueryString({
    from: formatDate(dateRange?.from),
    to: formatDate(dateRange?.to),
    accountId: accountId?.toString(),
  });
  return apiFetch(`/api/analytics/trade-frequency${params}`);
}

export async function getSpreadCost(
  currency: string,
  dateRange?: DateRange,
  accountId?: number | null,
): Promise<SpreadCostResponse> {
  const params = buildQueryString({
    currency,
    from: formatDate(dateRange?.from),
    to: formatDate(dateRange?.to),
    accountId: accountId?.toString(),
  });
  return apiFetch(`/api/analytics/spread-cost${params}`);
}

// ============================================================================
// Trades API
// ============================================================================

export async function getRecentTrades(
  currency: string,
  limit: number = 10,
  dateRange?: DateRange,
  instruments?: string[],
  accountId?: number | null,
): Promise<Trade[]> {
  const params = buildQueryString({
    limit: limit.toString(),
    from: formatDate(dateRange?.from),
    to: formatDate(dateRange?.to),
    instruments: instruments?.join(","),
    accountId: accountId?.toString(),
    currency,
  });
  return apiFetch(`/api/trades/recent${params}`);
}

export async function getAllTrades(
  currency: string,
  page: number = 1,
  pageSize: number = 50,
  dateRange?: DateRange,
  instruments?: string[],
  direction?: string,
  sortBy?: string,
  sortOrder?: string,
): Promise<{
  trades: Trade[];
  total: number;
  page: number;
  pageSize: number;
  pages: number;
}> {
  const params = buildQueryString({
    page: page.toString(),
    pageSize: pageSize.toString(),
    from: formatDate(dateRange?.from),
    to: formatDate(dateRange?.to),
    instruments: instruments?.join(","),
    direction,
    sortBy,
    sortOrder,
    currency,
  });
  return apiFetch(`/api/trades${params}`);
}

export async function getTradeStats(
  dateRange?: DateRange,
  instruments?: string[],
): Promise<unknown> {
  const params = buildQueryString({
    from: formatDate(dateRange?.from),
    to: formatDate(dateRange?.to),
    instruments: instruments?.join(","),
  });
  return apiFetch(`/api/trades/stats/summary${params}`);
}

// ============================================================================
// Instruments API
// ============================================================================

export async function getInstruments(): Promise<Instrument[]> {
  return apiFetch("/api/instruments");
}

// ============================================================================
// Accounts API
// ============================================================================

export async function getAccounts(): Promise<Account[]> {
  return apiFetch("/api/import/accounts");
}

// ============================================================================
// Import API
// ============================================================================

export interface Broker {
  key: string;
  name: string;
  supportedFormats: string[];
}

export interface DatabaseStats {
  totalTransactions: number;
  totalAccounts: number;
  brokers: string[];
  currencies: string[];
  dateRange: { from: string; to: string } | null;
  databaseSizeBytes: number;
}

export interface ImportResult {
  success: boolean;
  message: string;
  recordsImported: number;
  recordsSkipped: number;
  totalRecords: number;
  accountId: number;
  broker: string;
}

export interface CreateAccountParams {
  accountName: string;
  brokerName: string;
  currency: string;
  initialBalance?: number;
  notes?: string | null;
}

export async function getBrokers(): Promise<Broker[]> {
  return apiFetch("/api/import/brokers");
}

export async function getDatabaseStats(): Promise<DatabaseStats> {
  return apiFetch("/api/import/stats");
}

export async function createAccount(
  params: CreateAccountParams,
): Promise<Account> {
  return apiPost("/api/import/accounts", params);
}

export async function deleteAccount(
  accountId: number,
  deleteTransactions: boolean = false,
): Promise<{ success: boolean; message: string }> {
  return apiDelete(
    `/api/import/accounts/${accountId}${deleteTransactions ? "?deleteTransactions=true" : ""}`,
  );
}

export async function uploadTransactionFile(
  file: File,
  accountId: number,
  broker: string,
): Promise<ImportResult> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("accountId", accountId.toString());
  formData.append("broker", broker);

  const response = await fetch(`${API_BASE}/api/import/upload`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json();
    throw new APIError(response.status, error.detail || "Upload failed");
  }

  return response.json();
}

export async function deleteTransactions(
  accountId?: number | string,
): Promise<{ success: boolean; message: string }> {
  const params = accountId
    ? `accountId=${accountId}&confirm=true`
    : "confirm=true";
  return apiDelete(`/api/import/transactions?${params}`);
}

// ============================================================================
// Currency API
// ============================================================================

export async function getSupportedCurrencies(): Promise<
  { code: string; symbol: string; name: string }[]
> {
  return apiFetch("/api/currency/supported");
}

export async function getCurrenciesInUse(): Promise<string[]> {
  return apiFetch("/api/currency/in-use");
}

export async function getExchangeRates(
  baseCurrency: string,
): Promise<{ baseCurrency: string; rates: Record<string, number> }> {
  const params = buildQueryString({ base: baseCurrency });
  return apiFetch(`/api/currency/rates${params}`);
}

export async function updateExchangeRates(
  baseCurrency: string,
  rates: Record<string, number>,
): Promise<void> {
  await apiPut("/api/currency/rates/bulk", {
    baseCurrency,
    rates,
  });
}

// ============================================================================
// Health API
// ============================================================================

export async function healthCheck(): Promise<{
  status: string;
  timestamp: string;
  version: string;
}> {
  return apiFetch("/api/health");
}
