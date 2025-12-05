/**
 * Settings store - Single source of truth for user settings
 *
 * Settings are stored in the backend database.
 * This store loads them on app init and caches them.
 * All changes are saved to the backend immediately.
 */

import { create } from "zustand";
import * as api from "@/lib/api";

export interface SettingsState {
  // Settings values
  defaultCurrency: string | undefined;
  showConverted: boolean;

  // Loading state
  isLoaded: boolean;
  isLoading: boolean;
  error: string | null;

  // Actions
  loadSettings: () => Promise<void>;
  setDefaultCurrency: (currency: string) => Promise<void>;
  setShowConverted: (show: boolean) => Promise<void>;
  updateSettings: (
    settings: Partial<Pick<SettingsState, "defaultCurrency" | "showConverted">>,
  ) => Promise<void>;
}

export const useSettingsStore = create<SettingsState>((set, get) => ({
  // Initial state - empty until loaded from backend
  defaultCurrency: "",
  showConverted: true,
  isLoaded: false,
  isLoading: false,
  error: null,

  // Load settings from backend - MUST be called before fetching any data
  loadSettings: async () => {
    const { isLoaded, isLoading } = get();

    // Don't reload if already loaded or currently loading
    if (isLoaded || isLoading) return;

    set({ isLoading: true, error: null });

    try {
      const settings = await api.getSettings();
      set({
        defaultCurrency: settings.defaultCurrency,
        showConverted: settings.showConverted,
        isLoaded: true,
        isLoading: false,
        error: null,
      });
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Failed to load settings";
      set({
        error: message,
        isLoading: false,
        // No defaults per .rules - currency must be set by user
        defaultCurrency: undefined,
        showConverted: true,
        isLoaded: true,
      });
      console.error("Failed to load settings:", error);
    }
  },

  // Update default currency
  setDefaultCurrency: async (currency: string) => {
    const { showConverted } = get();
    const previousCurrency = get().defaultCurrency;

    // Optimistic update
    set({ defaultCurrency: currency });

    try {
      await api.updateSettings({
        defaultCurrency: currency,
        showConverted,
      });
    } catch (error) {
      // Revert on failure
      set({ defaultCurrency: previousCurrency });
      console.error("Failed to update default currency:", error);
      throw error;
    }
  },

  // Update show converted preference
  setShowConverted: async (show: boolean) => {
    const { defaultCurrency } = get();
    const previousShow = get().showConverted;

    // Can't update if defaultCurrency is not set
    if (!defaultCurrency) {
      console.error("Cannot update showConverted: defaultCurrency is not set");
      return;
    }

    // Optimistic update
    set({ showConverted: show });

    try {
      await api.updateSettings({
        defaultCurrency,
        showConverted: show,
      });
    } catch (error) {
      // Revert on failure
      set({ showConverted: previousShow });
      console.error("Failed to update show converted:", error);
      throw error;
    }
  },

  // Update multiple settings at once
  updateSettings: async (settings) => {
    const currentState = get();
    const newDefaultCurrency =
      settings.defaultCurrency ?? currentState.defaultCurrency;
    const newShowConverted =
      settings.showConverted ?? currentState.showConverted;

    // Can't update if defaultCurrency is not set
    if (!newDefaultCurrency) {
      console.error("Cannot update settings: defaultCurrency is not set");
      return;
    }

    const newSettings = {
      defaultCurrency: newDefaultCurrency,
      showConverted: newShowConverted,
    };

    // Optimistic update
    set(newSettings);

    try {
      await api.updateSettings(newSettings);
    } catch (error) {
      // Revert on failure
      set({
        defaultCurrency: currentState.defaultCurrency,
        showConverted: currentState.showConverted,
      });
      console.error("Failed to update settings:", error);
      throw error;
    }
  },
}));

// Selector hooks for common use cases
export const useDefaultCurrency = () =>
  useSettingsStore((state) => state.defaultCurrency);
export const useShowConverted = () =>
  useSettingsStore((state) => state.showConverted);
export const useSettingsLoaded = () =>
  useSettingsStore((state) => state.isLoaded);
export const useSettingsLoading = () =>
  useSettingsStore((state) => state.isLoading);
