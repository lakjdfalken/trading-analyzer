/**
 * Hook for fetching and managing currency data from the API.
 */

import { useEffect, useCallback, useState } from 'react';
import { useCurrencyStore } from '@/store/currency';
import {
  getSupportedCurrencies,
  getCurrenciesInUse,
  getExchangeRates,
  getCurrencyPreferences,
  updateCurrencyPreferences,
  setDefaultCurrency as apiSetDefaultCurrency,
  CurrencyInfo,
  CurrencyPreferences,
  ExchangeRates,
} from '@/api/currency';

interface UseCurrencyOptions {
  /** Fetch data on mount */
  fetchOnMount?: boolean;
  /** Base currency for exchange rates */
  baseCurrency?: string;
}

interface UseCurrencyReturn {
  // Data
  supportedCurrencies: CurrencyInfo[];
  currenciesInUse: string[];
  exchangeRates: ExchangeRates | null;
  defaultCurrency: string;
  showConverted: boolean;

  // State
  isLoading: boolean;
  error: string | null;

  // Actions
  fetchCurrencies: () => Promise<void>;
  fetchRates: (base?: string) => Promise<void>;
  fetchPreferences: () => Promise<void>;
  setDefaultCurrency: (currency: string) => Promise<void>;
  setShowConverted: (show: boolean) => void;
  refreshAll: () => Promise<void>;

  // Utilities
  convert: (amount: number, fromCurrency: string, toCurrency?: string) => number | null;
  formatAmount: (amount: number, currency: string) => string;
  formatWithConversion: (amount: number, originalCurrency: string) => {
    original: string;
    converted: string | null;
    showBoth: boolean;
  };
}

export function useCurrency(options: UseCurrencyOptions = {}): UseCurrencyReturn {
  const { fetchOnMount = true, baseCurrency = 'SEK' } = options;

  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Get store state and actions
  const {
    defaultCurrency,
    showConverted,
    exchangeRates,
    currenciesInUse,
    supportedCurrencies,
    setDefaultCurrency: storeSetDefaultCurrency,
    setShowConverted: storeSetShowConverted,
    setExchangeRates,
    setCurrenciesInUse,
    setSupportedCurrencies,
    convert,
    formatAmount,
    formatWithConversion,
  } = useCurrencyStore();

  // Fetch supported currencies
  const fetchCurrencies = useCallback(async () => {
    try {
      const [supported, inUse] = await Promise.all([
        getSupportedCurrencies(),
        getCurrenciesInUse(),
      ]);

      setSupportedCurrencies(supported);
      setCurrenciesInUse(inUse);
    } catch (err) {
      console.error('Failed to fetch currencies:', err);
      // Use empty arrays as fallback - store has defaults
    }
  }, [setSupportedCurrencies, setCurrenciesInUse]);

  // Fetch exchange rates
  const fetchRates = useCallback(
    async (base?: string) => {
      try {
        const rates = await getExchangeRates(base || baseCurrency);
        setExchangeRates(rates);
      } catch (err) {
        console.error('Failed to fetch exchange rates:', err);
        // Store has default rates as fallback
      }
    },
    [baseCurrency, setExchangeRates]
  );

  // Fetch user preferences
  const fetchPreferences = useCallback(async () => {
    try {
      const prefs = await getCurrencyPreferences();
      storeSetDefaultCurrency(prefs.defaultCurrency);
      storeSetShowConverted(prefs.showConverted);
    } catch (err) {
      console.error('Failed to fetch currency preferences:', err);
      // Use store defaults
    }
  }, [storeSetDefaultCurrency, storeSetShowConverted]);

  // Set default currency (updates both store and API)
  const setDefaultCurrency = useCallback(
    async (currency: string) => {
      // Update store immediately for responsive UI
      storeSetDefaultCurrency(currency);

      // Persist to API
      try {
        await apiSetDefaultCurrency(currency);
      } catch (err) {
        console.error('Failed to save default currency:', err);
        // Store is already updated, so user sees the change
      }
    },
    [storeSetDefaultCurrency]
  );

  // Set show converted (updates store, optionally API)
  const setShowConverted = useCallback(
    (show: boolean) => {
      storeSetShowConverted(show);

      // Optionally persist to API
      updateCurrencyPreferences({
        defaultCurrency,
        showConverted: show,
      }).catch((err) => {
        console.error('Failed to save show converted preference:', err);
      });
    },
    [storeSetShowConverted, defaultCurrency]
  );

  // Refresh all currency data
  const refreshAll = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      await Promise.all([fetchCurrencies(), fetchRates(), fetchPreferences()]);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to fetch currency data';
      setError(message);
      console.error('Error refreshing currency data:', err);
    } finally {
      setIsLoading(false);
    }
  }, [fetchCurrencies, fetchRates, fetchPreferences]);

  // Fetch data on mount if requested
  useEffect(() => {
    if (fetchOnMount) {
      refreshAll();
    }
  }, [fetchOnMount, refreshAll]);

  return {
    // Data
    supportedCurrencies,
    currenciesInUse,
    exchangeRates,
    defaultCurrency,
    showConverted,

    // State
    isLoading,
    error,

    // Actions
    fetchCurrencies,
    fetchRates,
    fetchPreferences,
    setDefaultCurrency,
    setShowConverted,
    refreshAll,

    // Utilities
    convert,
    formatAmount,
    formatWithConversion,
  };
}

/**
 * Hook for simple currency formatting without API fetching.
 * Uses store state directly.
 */
export function useCurrencyFormat() {
  const { convert, formatAmount, formatWithConversion, defaultCurrency, showConverted } =
    useCurrencyStore();

  return {
    convert,
    formatAmount,
    formatWithConversion,
    defaultCurrency,
    showConverted,
  };
}

export default useCurrency;
