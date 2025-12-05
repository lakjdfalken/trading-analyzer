/**
 * Currency store - Formatting utilities only
 *
 * Settings (defaultCurrency, showConverted) come from the settings store.
 * This store only provides formatting functions.
 */

import { create } from "zustand";

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

export interface CurrencyState {
  // Format amount with currency symbol
  formatAmount: (amount: number, currency: string) => string;

  // Get currency symbol
  getSymbol: (currency: string) => string;
}

export const useCurrencyStore = create<CurrencyState>()(() => ({
  // Format amount with currency symbol
  formatAmount: (amount: number, currency: string): string => {
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

  // Get currency symbol
  getSymbol: (currency: string): string => {
    return CURRENCY_SYMBOLS[currency] || currency;
  },
}));

// Selector hooks
export const useFormatAmount = () =>
  useCurrencyStore((state) => state.formatAmount);
export const useGetSymbol = () => useCurrencyStore((state) => state.getSymbol);
