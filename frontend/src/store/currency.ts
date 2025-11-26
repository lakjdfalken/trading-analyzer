/**
 * Currency store using Zustand.
 *
 * Manages:
 * - User's default/display currency
 * - Show converted toggle
 * - Exchange rates cache
 * - Currencies in use
 */

import { create } from "zustand";
import { persist } from "zustand/middleware";

export interface ExchangeRates {
  baseCurrency: string;
  rates: Record<string, number>;
  updatedAt: string | null;
}

export interface CurrencyState {
  // User preferences
  defaultCurrency: string;
  showConverted: boolean;

  // Data
  exchangeRates: ExchangeRates | null;
  currenciesInUse: string[];
  supportedCurrencies: Array<{ code: string; symbol: string; name: string }>;

  // Loading states
  isLoading: boolean;
  error: string | null;

  // Actions
  setDefaultCurrency: (currency: string) => void;
  setShowConverted: (show: boolean) => void;
  setExchangeRates: (rates: ExchangeRates) => void;
  setCurrenciesInUse: (currencies: string[]) => void;
  setSupportedCurrencies: (
    currencies: Array<{ code: string; symbol: string; name: string }>,
  ) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;

  // Conversion helpers
  convert: (
    amount: number,
    fromCurrency: string,
    toCurrency?: string,
  ) => number | null;
  getRate: (fromCurrency: string, toCurrency: string) => number | null;
  formatAmount: (amount: number, currency: string) => string;
  formatWithConversion: (
    amount: number,
    originalCurrency: string,
  ) => {
    original: string;
    converted: string | null;
    showBoth: boolean;
  };
}

// Currency symbols mapping
const CURRENCY_SYMBOLS: Record<string, string> = {
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

// Base rates relative to USD (as a neutral base for calculations)
const BASE_RATES_TO_USD: Record<string, number> = {
  USD: 1.0,
  SEK: 0.095,
  DKK: 0.14,
  EUR: 1.08,
  GBP: 1.27,
  NOK: 0.091,
  CHF: 1.13,
  JPY: 0.0067,
  AUD: 0.65,
  CAD: 0.74,
  NZD: 0.6,
};

// Calculate rates relative to a target currency
function calculateRatesRelativeTo(
  targetCurrency: string,
): Record<string, number> {
  const targetToUsd = BASE_RATES_TO_USD[targetCurrency] || 1.0;
  const rates: Record<string, number> = {};

  for (const [currency, usdRate] of Object.entries(BASE_RATES_TO_USD)) {
    if (currency === targetCurrency) {
      rates[currency] = 1.0;
    } else {
      // Rate = how many units of targetCurrency per 1 unit of this currency
      rates[currency] = usdRate / targetToUsd;
    }
  }

  return rates;
}

// Default exchange rates (calculated relative to default currency)
const DEFAULT_CURRENCY = "DKK";
const DEFAULT_RATES = calculateRatesRelativeTo(DEFAULT_CURRENCY);

export const useCurrencyStore = create<CurrencyState>()(
  persist(
    (set, get) => ({
      // Initial state
      defaultCurrency: DEFAULT_CURRENCY,
      showConverted: true,
      exchangeRates: {
        baseCurrency: DEFAULT_CURRENCY,
        rates: DEFAULT_RATES,
        updatedAt: null,
      },
      currenciesInUse: [],
      supportedCurrencies: [],
      isLoading: false,
      error: null,

      // Actions
      setDefaultCurrency: (currency) => set({ defaultCurrency: currency }),

      setShowConverted: (show) => set({ showConverted: show }),

      setExchangeRates: (rates) => set({ exchangeRates: rates }),

      setCurrenciesInUse: (currencies) => set({ currenciesInUse: currencies }),

      setSupportedCurrencies: (currencies) =>
        set({ supportedCurrencies: currencies }),

      setLoading: (loading) => set({ isLoading: loading }),

      setError: (error) => set({ error }),

      // Get exchange rate between two currencies
      getRate: (fromCurrency, toCurrency) => {
        if (fromCurrency === toCurrency) return 1.0;

        const { exchangeRates } = get();
        if (!exchangeRates) return null;

        const { rates, baseCurrency } = exchangeRates;

        // If converting to/from base currency
        if (toCurrency === baseCurrency && rates[fromCurrency]) {
          return rates[fromCurrency];
        }
        if (fromCurrency === baseCurrency && rates[toCurrency]) {
          return 1.0 / rates[toCurrency];
        }

        // Convert via base currency
        const fromRate = rates[fromCurrency];
        const toRate = rates[toCurrency];

        if (fromRate && toRate) {
          return fromRate / toRate;
        }

        return null;
      },

      // Convert amount between currencies
      convert: (amount, fromCurrency, toCurrency) => {
        const target = toCurrency || get().defaultCurrency;
        const rate = get().getRate(fromCurrency, target);

        if (rate === null) return null;
        return amount * rate;
      },

      // Format amount with currency symbol
      formatAmount: (amount, currency) => {
        const symbol = CURRENCY_SYMBOLS[currency] || currency;
        const formatted = new Intl.NumberFormat("en-US", {
          minimumFractionDigits: 2,
          maximumFractionDigits: 2,
        }).format(amount);

        // Symbol placement varies by currency
        if (["USD", "GBP", "AUD", "CAD", "NZD"].includes(currency)) {
          return `${symbol}${formatted}`;
        }
        return `${formatted} ${symbol}`;
      },

      // Format with optional conversion display
      formatWithConversion: (amount, originalCurrency) => {
        const { defaultCurrency, showConverted, formatAmount, convert } = get();

        const original = formatAmount(amount, originalCurrency);

        if (!showConverted || originalCurrency === defaultCurrency) {
          return {
            original,
            converted: null,
            showBoth: false,
          };
        }

        const convertedAmount = convert(
          amount,
          originalCurrency,
          defaultCurrency,
        );

        return {
          original,
          converted:
            convertedAmount !== null
              ? formatAmount(convertedAmount, defaultCurrency)
              : null,
          showBoth: showConverted && convertedAmount !== null,
        };
      },
    }),
    {
      name: "currency-preferences",
      partialize: (state) => ({
        defaultCurrency: state.defaultCurrency,
        showConverted: state.showConverted,
        exchangeRates: state.exchangeRates,
      }),
      onRehydrateStorage: () => (state) => {
        // Recalculate rates if base currency doesn't match default currency
        if (state && state.exchangeRates) {
          if (state.exchangeRates.baseCurrency !== state.defaultCurrency) {
            const newRates = calculateRatesRelativeTo(state.defaultCurrency);
            state.exchangeRates = {
              baseCurrency: state.defaultCurrency,
              rates: newRates,
              updatedAt: new Date().toISOString(),
            };
          }
        }
      },
    },
  ),
);

// Selector hooks for common use cases
export const useDefaultCurrency = () =>
  useCurrencyStore((state) => state.defaultCurrency);
export const useShowConverted = () =>
  useCurrencyStore((state) => state.showConverted);
export const useExchangeRates = () =>
  useCurrencyStore((state) => state.exchangeRates);
export const useCurrenciesInUse = () =>
  useCurrencyStore((state) => state.currenciesInUse);
export const useCurrencyActions = () =>
  useCurrencyStore((state) => ({
    setDefaultCurrency: state.setDefaultCurrency,
    setShowConverted: state.setShowConverted,
    setExchangeRates: state.setExchangeRates,
    setCurrenciesInUse: state.setCurrenciesInUse,
    convert: state.convert,
    formatAmount: state.formatAmount,
    formatWithConversion: state.formatWithConversion,
  }));
