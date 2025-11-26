/**
 * Currency types and API functions.
 */

// API Configuration
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// Types
export interface CurrencyInfo {
  code: string;
  symbol: string;
  name: string;
}

export interface ExchangeRates {
  baseCurrency: string;
  rates: Record<string, number>;
  updatedAt: string | null;
}

export interface ExchangeRate {
  fromCurrency: string;
  toCurrency: string;
  rate: number;
}

export interface CurrencyPreferences {
  defaultCurrency: string;
  showConverted: boolean;
}

export interface ConversionResult {
  originalAmount: number;
  originalCurrency: string;
  convertedAmount: number;
  targetCurrency: string;
  rate: number;
  formattedOriginal: string;
  formattedConverted: string;
}

export interface BrokerCurrencies {
  broker: string;
  currencies: string[];
}

export interface AccountCurrency {
  accountId: number;
  accountName: string;
  broker: string;
  currency: string;
}

export interface FormattedAmount {
  original: {
    amount: number;
    currency: string;
    formatted: string;
  };
  converted: {
    amount: number;
    currency: string;
    formatted: string;
  } | null;
}

// Currency symbols mapping (for client-side formatting)
export const CURRENCY_SYMBOLS: Record<string, string> = {
  SEK: "kr",
  DKK: "kr",
  EUR: "€",
  USD: "$",
  GBP: "£",
  NOK: "kr",
  CHF: "CHF",
  JPY: "¥",
  AUD: "A$",
  CAD: "C$",
  NZD: "NZ$",
};

// Default values for fallback
const DEFAULT_CURRENCIES: CurrencyInfo[] = [
  { code: "SEK", symbol: "kr", name: "Swedish Krona" },
  { code: "DKK", symbol: "kr", name: "Danish Krone" },
  { code: "EUR", symbol: "€", name: "Euro" },
  { code: "USD", symbol: "$", name: "US Dollar" },
  { code: "GBP", symbol: "£", name: "British Pound" },
];

const DEFAULT_EXCHANGE_RATES: ExchangeRates = {
  baseCurrency: "SEK",
  rates: {
    SEK: 1.0,
    DKK: 1.52,
    EUR: 11.32,
    USD: 10.5,
    GBP: 13.2,
  },
  updatedAt: null,
};

const DEFAULT_PREFERENCES: CurrencyPreferences = {
  defaultCurrency: "SEK",
  showConverted: true,
};

// Fetch helper
async function fetchApi<T>(
  endpoint: string,
  options?: RequestInit,
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;

  const response = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });

  if (!response.ok) {
    throw new Error(`HTTP error ${response.status}`);
  }

  return response.json();
}

// API Functions

/**
 * Get list of all supported currencies.
 */
export async function getSupportedCurrencies(): Promise<CurrencyInfo[]> {
  try {
    return await fetchApi<CurrencyInfo[]>("/api/currency/supported");
  } catch {
    return DEFAULT_CURRENCIES;
  }
}

/**
 * Get list of currencies actually used in trading data.
 */
export async function getCurrenciesInUse(): Promise<string[]> {
  try {
    return await fetchApi<string[]>("/api/currency/in-use");
  } catch {
    return [];
  }
}

/**
 * Get all exchange rates relative to a base currency.
 */
export async function getExchangeRates(
  baseCurrency: string = "SEK",
): Promise<ExchangeRates> {
  try {
    return await fetchApi<ExchangeRates>(
      `/api/currency/rates?base=${baseCurrency}`,
    );
  } catch {
    return DEFAULT_EXCHANGE_RATES;
  }
}

/**
 * Get exchange rate between two specific currencies.
 */
export async function getExchangeRate(
  fromCurrency: string,
  toCurrency: string,
): Promise<ExchangeRate> {
  try {
    return await fetchApi<ExchangeRate>(
      `/api/currency/rates/${fromCurrency}/${toCurrency}`,
    );
  } catch {
    // Calculate from default rates
    const fromRate = DEFAULT_EXCHANGE_RATES.rates[fromCurrency] || 1;
    const toRate = DEFAULT_EXCHANGE_RATES.rates[toCurrency] || 1;
    return {
      fromCurrency,
      toCurrency,
      rate: fromRate / toRate,
    };
  }
}

/**
 * Update a single exchange rate.
 */
export async function updateExchangeRate(
  fromCurrency: string,
  toCurrency: string,
  rate: number,
): Promise<{ success: boolean; message: string }> {
  return fetchApi("/api/currency/rates", {
    method: "PUT",
    body: JSON.stringify({
      fromCurrency,
      toCurrency,
      rate,
    }),
  });
}

/**
 * Bulk update exchange rates.
 */
export async function bulkUpdateRates(
  rates: Record<string, number>,
  baseCurrency: string = "SEK",
): Promise<{ success: boolean; message: string }> {
  return fetchApi("/api/currency/rates/bulk", {
    method: "PUT",
    body: JSON.stringify({
      baseCurrency,
      rates,
    }),
  });
}

/**
 * Convert an amount between currencies.
 */
export async function convertCurrency(
  amount: number,
  fromCurrency: string,
  toCurrency: string,
): Promise<ConversionResult> {
  try {
    return await fetchApi("/api/currency/convert", {
      method: "POST",
      body: JSON.stringify({
        amount,
        fromCurrency,
        toCurrency,
      }),
    });
  } catch {
    // Calculate locally
    const rate = await getExchangeRate(fromCurrency, toCurrency);
    const converted = amount * rate.rate;
    return {
      originalAmount: amount,
      originalCurrency: fromCurrency,
      convertedAmount: converted,
      targetCurrency: toCurrency,
      rate: rate.rate,
      formattedOriginal: formatCurrency(amount, fromCurrency),
      formattedConverted: formatCurrency(converted, toCurrency),
    };
  }
}

/**
 * Convert an amount between currencies (GET version).
 */
export async function convertCurrencyGet(
  amount: number,
  fromCurrency: string,
  toCurrency: string,
): Promise<ConversionResult> {
  try {
    return await fetchApi<ConversionResult>(
      `/api/currency/convert?amount=${amount}&from=${fromCurrency}&to=${toCurrency}`,
    );
  } catch {
    return convertCurrency(amount, fromCurrency, toCurrency);
  }
}

/**
 * Get user currency preferences.
 */
export async function getCurrencyPreferences(): Promise<CurrencyPreferences> {
  try {
    return await fetchApi<CurrencyPreferences>("/api/currency/preferences");
  } catch {
    return DEFAULT_PREFERENCES;
  }
}

/**
 * Update user currency preferences.
 */
export async function updateCurrencyPreferences(
  prefs: CurrencyPreferences,
): Promise<{ success: boolean; preferences: CurrencyPreferences }> {
  try {
    return await fetchApi("/api/currency/preferences", {
      method: "PUT",
      body: JSON.stringify(prefs),
    });
  } catch {
    return { success: false, preferences: prefs };
  }
}

/**
 * Get the default display currency.
 */
export async function getDefaultCurrency(): Promise<{
  defaultCurrency: string;
}> {
  try {
    return await fetchApi<{ defaultCurrency: string }>(
      "/api/currency/preferences/default",
    );
  } catch {
    return { defaultCurrency: DEFAULT_PREFERENCES.defaultCurrency };
  }
}

/**
 * Set the default display currency.
 */
export async function setDefaultCurrency(
  currency: string,
): Promise<{ success: boolean; defaultCurrency: string }> {
  try {
    return await fetchApi(
      `/api/currency/preferences/default?currency=${currency}`,
      {
        method: "PUT",
      },
    );
  } catch {
    return { success: false, defaultCurrency: currency };
  }
}

/**
 * Get list of brokers with their associated currencies.
 */
export async function getBrokersWithCurrencies(): Promise<BrokerCurrencies[]> {
  try {
    return await fetchApi<BrokerCurrencies[]>("/api/currency/brokers");
  } catch {
    return [];
  }
}

/**
 * Get currencies associated with each account.
 */
export async function getAccountCurrencies(): Promise<AccountCurrency[]> {
  try {
    return await fetchApi<AccountCurrency[]>("/api/currency/accounts");
  } catch {
    return [];
  }
}

/**
 * Format a currency amount (server-side).
 */
export async function formatCurrencyServer(
  amount: number,
  currency: string,
  includeSymbol: boolean = true,
  decimalPlaces: number = 2,
): Promise<{ amount: number; currency: string; formatted: string }> {
  try {
    return await fetchApi(
      `/api/currency/format?amount=${amount}&currency=${currency}&includeSymbol=${includeSymbol}&decimalPlaces=${decimalPlaces}`,
    );
  } catch {
    return {
      amount,
      currency,
      formatted: formatCurrency(amount, currency, {
        includeSymbol,
        decimalPlaces,
      }),
    };
  }
}

/**
 * Format amount with optional conversion display (server-side).
 */
export async function formatWithConversion(
  amount: number,
  originalCurrency: string,
  targetCurrency?: string,
): Promise<FormattedAmount> {
  try {
    let url = `/api/currency/format-with-conversion?amount=${amount}&originalCurrency=${originalCurrency}`;
    if (targetCurrency) {
      url += `&targetCurrency=${targetCurrency}`;
    }
    return await fetchApi<FormattedAmount>(url);
  } catch {
    return {
      original: {
        amount,
        currency: originalCurrency,
        formatted: formatCurrency(amount, originalCurrency),
      },
      converted: null,
    };
  }
}

// Client-side formatting utilities

/**
 * Format currency amount on client side.
 */
export function formatCurrency(
  amount: number,
  currency: string,
  options?: {
    includeSymbol?: boolean;
    decimalPlaces?: number;
    locale?: string;
  },
): string {
  const {
    includeSymbol = true,
    decimalPlaces = 2,
    locale = "en-US",
  } = options || {};

  const formatted = new Intl.NumberFormat(locale, {
    minimumFractionDigits: decimalPlaces,
    maximumFractionDigits: decimalPlaces,
  }).format(amount);

  if (!includeSymbol) {
    return formatted;
  }

  const symbol = CURRENCY_SYMBOLS[currency] || currency;

  // Symbol placement varies by currency
  if (["USD", "GBP", "AUD", "CAD", "NZD"].includes(currency)) {
    return `${symbol}${formatted}`;
  }

  return `${formatted} ${symbol}`;
}

/**
 * Format currency with both original and converted amounts.
 */
export function formatWithConversionClient(
  amount: number,
  originalCurrency: string,
  targetCurrency: string,
  exchangeRate: number,
): FormattedAmount {
  const convertedAmount = amount * exchangeRate;

  return {
    original: {
      amount,
      currency: originalCurrency,
      formatted: formatCurrency(amount, originalCurrency),
    },
    converted:
      originalCurrency !== targetCurrency
        ? {
            amount: convertedAmount,
            currency: targetCurrency,
            formatted: formatCurrency(convertedAmount, targetCurrency),
          }
        : null,
  };
}

/**
 * Get currency symbol.
 */
export function getCurrencySymbol(currency: string): string {
  return CURRENCY_SYMBOLS[currency] || currency;
}
