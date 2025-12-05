"use client";

import React from "react";
import { useSettingsStore } from "@/store/settings";

interface AppProviderProps {
  children: React.ReactNode;
}

/**
 * AppProvider - Initializes app-wide state
 *
 * Loads settings from the backend before rendering children.
 * All pages wait for settings to be loaded before fetching data.
 */
export function AppProvider({ children }: AppProviderProps) {
  const loadSettings = useSettingsStore((state) => state.loadSettings);
  const isLoaded = useSettingsStore((state) => state.isLoaded);
  const isLoading = useSettingsStore((state) => state.isLoading);
  const error = useSettingsStore((state) => state.error);

  React.useEffect(() => {
    loadSettings();
  }, [loadSettings]);

  // Show loading state while settings are being fetched
  if (!isLoaded && isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="flex flex-col items-center gap-4">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
          <p className="text-muted-foreground text-sm">Loading settings...</p>
        </div>
      </div>
    );
  }

  // Show error state if settings failed to load
  if (error && !isLoaded) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="flex flex-col items-center gap-4 p-8 max-w-md text-center">
          <div className="h-12 w-12 rounded-full bg-destructive/10 flex items-center justify-center">
            <span className="text-destructive text-xl">!</span>
          </div>
          <h2 className="text-lg font-semibold">Failed to Load Settings</h2>
          <p className="text-muted-foreground text-sm">{error}</p>
          <button
            onClick={() => loadSettings()}
            className="px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 text-sm"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}
