"use client";

import * as React from "react";
import {
  DollarSign,
  Save,
  RotateCcw,
  Check,
  RefreshCw,
  Trash2,
  Database,
  AlertTriangle,
  Settings,
  Moon,
  Sun,
  Monitor,
  TrendingUp,
  Plus,
  X,
} from "lucide-react";
import { useTheme } from "next-themes";

import { cn } from "@/lib/utils";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { CurrencySelector, ShowConvertedToggle } from "@/components/currency";
import { useCurrencyStore } from "@/store/currency";
import { useSettingsStore } from "@/store/settings";
import * as api from "@/lib/api";

// Exchange rates that can be edited
const EDITABLE_CURRENCIES = ["SEK", "DKK", "EUR", "USD", "GBP"];

// Base rates relative to USD (as a neutral base for calculations)
const BASE_RATES_TO_USD: Record<string, number> = {
  USD: 1.0,
  SEK: 0.095,
  DKK: 0.14,
  EUR: 1.08,
  GBP: 1.27,
  NOK: 0.091,
  CHF: 1.13,
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

export default function SettingsPage() {
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = React.useState(false);
  const [saved, setSaved] = React.useState(false);
  const [hasChanges, setHasChanges] = React.useState(false);
  const [editingRates, setEditingRates] = React.useState(false);
  const [localRates, setLocalRates] = React.useState<Record<string, number>>(
    {},
  );
  const [rateInputs, setRateInputs] = React.useState<Record<string, string>>(
    {},
  );
  const [ratesInitialized, setRatesInitialized] = React.useState(false);

  // Data management state
  const [accounts, setAccounts] = React.useState<
    Array<{
      account_id: number;
      account_name: string;
      broker_name: string;
      currency?: string;
      transaction_count?: number;
    }>
  >([]);
  const [selectedAccountToDelete, setSelectedAccountToDelete] = React.useState<
    number | "all" | null
  >(null);
  const [deleteConfirmText, setDeleteConfirmText] = React.useState("");
  const [isDeleting, setIsDeleting] = React.useState(false);
  const [deleteError, setDeleteError] = React.useState<string | null>(null);
  const [deleteSuccess, setDeleteSuccess] = React.useState<string | null>(null);

  // Instrument point factors state
  const [pointFactors, setPointFactors] = React.useState<
    Record<string, number>
  >({});
  const [savedPointFactors, setSavedPointFactors] = React.useState<
    Record<string, number>
  >({});
  const [newInstrumentName, setNewInstrumentName] = React.useState("");
  const [newInstrumentFactor, setNewInstrumentFactor] = React.useState("1.0");
  const [pointFactorsLoaded, setPointFactorsLoaded] = React.useState(false);

  // Track initial currency settings for change detection
  const [initialCurrency, setInitialCurrency] = React.useState<
    string | undefined
  >(undefined);
  const [initialShowConverted, setInitialShowConverted] = React.useState<
    boolean | null
  >(null);

  // Settings store (source of truth from backend)
  const {
    defaultCurrency,
    showConverted,
    spreadCostValidFrom,
    setDefaultCurrency,
    setShowConverted,
    setSpreadCostValidFrom,
    isLoaded: settingsLoaded,
  } = useSettingsStore();

  // Local state for spread cost valid from date editing
  const [localSpreadCostValidFrom, setLocalSpreadCostValidFrom] =
    React.useState<string>("2025-06-08");
  const [spreadCostValidFromInitialized, setSpreadCostValidFromInitialized] =
    React.useState(false);

  // Currency store (formatting only)
  const { formatAmount } = useCurrencyStore();

  // Local state for exchange rates (these are stored in backend)
  const [exchangeRates, setExchangeRates] = React.useState<{
    baseCurrency: string;
    rates: Record<string, number>;
    updatedAt: string | null;
  } | null>(null);
  const [savedRates, setSavedRates] = React.useState<Record<string, number>>(
    {},
  );
  const [currenciesInUse, setCurrenciesInUse] = React.useState<string[]>([]);

  // Set mounted state for theme hydration
  React.useEffect(() => {
    setMounted(true);
  }, []);

  // Fetch accounts for data management using centralized API
  React.useEffect(() => {
    const fetchAccounts = async () => {
      try {
        const data = await api.getAccounts();
        setAccounts(Array.isArray(data) ? data : []);
      } catch (err) {
        console.error("Failed to fetch accounts:", err);
        setAccounts([]);
      }
    };
    fetchAccounts();
  }, [deleteSuccess]);

  // Load point factors from backend
  React.useEffect(() => {
    const loadPointFactors = async () => {
      try {
        const response = await fetch("/api/currency/point-factors");
        if (response.ok) {
          const data = await response.json();
          setPointFactors(data.factors || {});
          setSavedPointFactors(data.factors || {});
          setPointFactorsLoaded(true);
        }
      } catch (err) {
        console.error("Failed to load point factors:", err);
        // Set defaults
        const defaults = { "Gold (per 0.1)": 0.1 };
        setPointFactors(defaults);
        setSavedPointFactors(defaults);
        setPointFactorsLoaded(true);
      }
    };
    loadPointFactors();
  }, []);

  // Load exchange rates from backend on mount
  React.useEffect(() => {
    const loadRates = async () => {
      if (!defaultCurrency) return;
      try {
        const data = await api.getExchangeRates(defaultCurrency);
        if (data && data.rates && Object.keys(data.rates).length > 0) {
          setExchangeRates({
            baseCurrency: data.baseCurrency,
            rates: data.rates,
            updatedAt: new Date().toISOString(),
          });
          setLocalRates(data.rates);
          setSavedRates(data.rates);
          setRateInputs(
            Object.fromEntries(
              Object.entries(data.rates).map(([k, v]) => [k, String(v)]),
            ),
          );
          setRatesInitialized(true);
        } else {
          // No rates in backend, use calculated defaults
          const defaultRates = calculateRatesRelativeTo(defaultCurrency);
          setLocalRates(defaultRates);
          setSavedRates(defaultRates);
          setRateInputs(
            Object.fromEntries(
              Object.entries(defaultRates).map(([k, v]) => [k, String(v)]),
            ),
          );
          setRatesInitialized(true);
          setExchangeRates({
            baseCurrency: defaultCurrency,
            rates: defaultRates,
            updatedAt: null,
          });
        }
      } catch {
        // Failed to load, use calculated defaults
        const defaultRates = calculateRatesRelativeTo(defaultCurrency);
        setLocalRates(defaultRates);
        setSavedRates(defaultRates);
        setRateInputs(
          Object.fromEntries(
            Object.entries(defaultRates).map(([k, v]) => [k, String(v)]),
          ),
        );
        setRatesInitialized(true);
      }
    };
    if (settingsLoaded && defaultCurrency) {
      loadRates();
    }
  }, [settingsLoaded, defaultCurrency]);

  // Sync local spread cost valid from with store value (only once when loaded)
  React.useEffect(() => {
    if (settingsLoaded && !spreadCostValidFromInitialized) {
      setLocalSpreadCostValidFrom(spreadCostValidFrom || "2025-06-08");
      setSpreadCostValidFromInitialized(true);
    }
  }, [settingsLoaded, spreadCostValidFrom, spreadCostValidFromInitialized]);

  // Set initial values for change tracking (only once)
  React.useEffect(() => {
    if (initialCurrency === undefined && defaultCurrency) {
      setInitialCurrency(defaultCurrency);
    }
    if (initialShowConverted === null) {
      setInitialShowConverted(showConverted);
    }
  }, [defaultCurrency, showConverted, initialCurrency, initialShowConverted]);

  // Track changes - compare against saved values
  React.useEffect(() => {
    const currencyChanged =
      initialCurrency !== null && defaultCurrency !== initialCurrency;
    const showConvertedChanged =
      initialShowConverted !== null && showConverted !== initialShowConverted;
    const ratesChanged =
      ratesInitialized &&
      Object.keys(localRates).length > 0 &&
      JSON.stringify(localRates) !== JSON.stringify(savedRates);
    const pointFactorsChanged =
      pointFactorsLoaded &&
      JSON.stringify(pointFactors) !== JSON.stringify(savedPointFactors);
    const spreadCostValidFromChanged =
      spreadCostValidFromInitialized &&
      localSpreadCostValidFrom !== (spreadCostValidFrom || "2025-06-08");

    setHasChanges(
      currencyChanged ||
        showConvertedChanged ||
        !!ratesChanged ||
        pointFactorsChanged ||
        spreadCostValidFromChanged,
    );
  }, [
    defaultCurrency,
    showConverted,
    initialCurrency,
    initialShowConverted,
    localRates,
    savedRates,
    ratesInitialized,
    pointFactors,
    savedPointFactors,
    pointFactorsLoaded,
    localSpreadCostValidFrom,
    spreadCostValidFrom,
    spreadCostValidFromInitialized,
  ]);

  // Handle save - saves to backend via settings store
  const handleSave = async () => {
    if (!defaultCurrency) {
      console.error("Cannot save: default currency is not set");
      return;
    }
    try {
      // Save currency preferences to backend
      await setDefaultCurrency(defaultCurrency);
      await setShowConverted(showConverted);
      await setSpreadCostValidFrom(localSpreadCostValidFrom);

      // Save exchange rates to backend
      if (defaultCurrency && Object.keys(localRates).length > 0) {
        await api.updateExchangeRates(defaultCurrency, localRates);
        setSavedRates(localRates);
        setExchangeRates({
          baseCurrency: defaultCurrency,
          rates: localRates,
          updatedAt: new Date().toISOString(),
        });
      }

      // Save point factors to backend
      if (Object.keys(pointFactors).length > 0) {
        const response = await fetch("/api/currency/point-factors", {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(pointFactors),
        });
        if (response.ok) {
          setSavedPointFactors(pointFactors);
        }
      }

      // Update initial values to current (so changes are relative to saved state)
      if (defaultCurrency) {
        setInitialCurrency(defaultCurrency);
      }
      setInitialShowConverted(showConverted);

      setSaved(true);
      setHasChanges(false);
      setEditingRates(false);
      setTimeout(() => setSaved(false), 2000);
    } catch (error) {
      console.error("Failed to save settings:", error);
    }
  };

  // Handle reset
  const handleReset = () => {
    // Reset currency to initial saved value
    if (initialCurrency) {
      setDefaultCurrency(initialCurrency);
      // Recalculate rates for the initial currency
      const resetRates = calculateRatesRelativeTo(initialCurrency);
      setLocalRates(resetRates);
    }
    setEditingRates(false);
  };

  // Update exchange rate
  const updateRate = (currency: string, rate: number) => {
    setLocalRates((prev) => ({ ...prev, [currency]: rate }));
    setHasChanges(true);
  };

  return (
    <div className="min-h-screen bg-background p-6 md:p-8">
      <div className="container mx-auto max-w-4xl">
        {/* Page Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold tracking-tight">Settings</h1>
              <p className="text-muted-foreground mt-1">
                Manage your account preferences and display options
              </p>
            </div>
            <div className="flex items-center gap-2">
              {saved && (
                <Badge
                  variant="outline"
                  className="gap-1 bg-green-500/10 text-green-500"
                >
                  <Check className="h-3 w-3" />
                  Saved
                </Badge>
              )}
              <Button
                variant="outline"
                onClick={handleReset}
                disabled={!hasChanges}
              >
                <RotateCcw className="h-4 w-4 mr-2" />
                Reset
              </Button>
              <Button onClick={handleSave} disabled={!hasChanges}>
                <Save className="h-4 w-4 mr-2" />
                Save Changes
              </Button>
            </div>
          </div>
        </div>

        <div className="space-y-6">
          {/* Currency Settings - New Section */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <DollarSign className="h-5 w-5" />
                Currency Settings
              </CardTitle>
              <CardDescription>
                Configure your default currency and conversion display
                preferences
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Default Currency Selector */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <CurrencySelector
                    label="Default Display Currency"
                    showLabel={true}
                    size="md"
                  />
                  <p className="text-xs text-muted-foreground mt-2">
                    All amounts can be converted to this currency for comparison
                  </p>
                </div>

                <div>
                  <label className="block text-xs font-medium text-muted-foreground mb-2">
                    Conversion Display
                  </label>
                  <ShowConvertedToggle />
                  <p className="text-xs text-muted-foreground mt-2">
                    Show amounts in both original and default currency
                  </p>
                </div>
              </div>

              {/* Currencies In Use */}
              {currenciesInUse.length > 0 && (
                <div>
                  <label className="text-sm font-medium mb-2 block">
                    Currencies in Your Portfolio
                  </label>
                  <div className="flex gap-2 flex-wrap">
                    {currenciesInUse.map((currency) => (
                      <Badge
                        key={currency}
                        variant={
                          currency === defaultCurrency ? "default" : "secondary"
                        }
                      >
                        {currency}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}

              {/* Exchange Rates */}
              <div>
                <div className="flex items-center justify-between mb-3">
                  <label className="text-sm font-medium">
                    Exchange Rates (1 unit = X {defaultCurrency})
                  </label>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setEditingRates(!editingRates)}
                    className="gap-2"
                  >
                    <RefreshCw className="h-4 w-4" />
                    {editingRates ? "Cancel Edit" : "Edit Rates"}
                  </Button>
                </div>

                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
                  {EDITABLE_CURRENCIES.filter(
                    (c) => c !== exchangeRates?.baseCurrency,
                  ).map((currency) => (
                    <div
                      key={currency}
                      className={cn(
                        "p-3 rounded-lg border",
                        editingRates
                          ? "bg-background border-input"
                          : "bg-accent/50 border-transparent",
                      )}
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-sm font-medium">{currency}</span>
                        {currenciesInUse.includes(currency) && (
                          <Badge variant="outline" className="text-xs py-0">
                            In use
                          </Badge>
                        )}
                      </div>
                      {editingRates ? (
                        <input
                          type="text"
                          inputMode="decimal"
                          value={rateInputs[currency] ?? ""}
                          onChange={(e) => {
                            const value = e.target.value.replace(",", ".");
                            setRateInputs((prev) => ({
                              ...prev,
                              [currency]: value,
                            }));
                            const parsed = parseFloat(value);
                            if (!isNaN(parsed)) {
                              updateRate(currency, parsed);
                            } else if (value === "" || value === ".") {
                              updateRate(currency, 0);
                            }
                          }}
                          className="w-full px-2 py-1 bg-background border border-input rounded text-sm"
                        />
                      ) : (
                        <span className="text-lg font-semibold">
                          {(localRates[currency] || 0).toFixed(2)}
                        </span>
                      )}
                    </div>
                  ))}
                </div>

                <p className="text-xs text-muted-foreground mt-2">
                  Exchange rates are used to convert amounts between currencies.
                  Update these rates periodically for accurate conversions.
                </p>
              </div>

              {/* Example Conversion */}
              {defaultCurrency && (
                <div className="p-4 bg-accent/30 rounded-lg">
                  <label className="text-sm font-medium mb-2 block">
                    Conversion Example
                  </label>
                  <div className="flex items-center gap-4 text-sm">
                    <span>100 USD</span>
                    <span className="text-muted-foreground">=</span>
                    <span className="font-semibold">
                      {formatAmount(
                        100 * (localRates["USD"] || 1.0),
                        defaultCurrency,
                      )}
                    </span>
                  </div>
                  <div className="flex items-center gap-4 text-sm mt-2">
                    <span>100 EUR</span>
                    <span className="text-muted-foreground">=</span>
                    <span className="font-semibold">
                      {formatAmount(
                        100 * (localRates["EUR"] || 1.0),
                        defaultCurrency,
                      )}
                    </span>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Instrument Point Factors */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <TrendingUp className="h-5 w-5" />
                Instrument Point Factors
              </CardTitle>
              <CardDescription>
                Configure how points are calculated for different instruments.
                For example, Gold (per 0.1) has a factor of 0.1 because the
                price difference needs to be multiplied by 0.1 to get actual
                points.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Existing Factors */}
              <div className="space-y-2">
                {Object.entries(pointFactors).map(([instrument, factor]) => (
                  <div
                    key={instrument}
                    className="flex items-center gap-3 p-3 bg-accent/50 rounded-lg"
                  >
                    <div className="flex-1">
                      <span className="font-medium">{instrument}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-sm text-muted-foreground">
                        Factor:
                      </span>
                      <input
                        type="text"
                        inputMode="decimal"
                        value={factor}
                        onChange={(e) => {
                          const value = e.target.value.replace(",", ".");
                          const parsed = parseFloat(value);
                          if (!isNaN(parsed)) {
                            setPointFactors((prev) => ({
                              ...prev,
                              [instrument]: parsed,
                            }));
                          }
                        }}
                        className="w-20 px-2 py-1 bg-background border border-input rounded text-sm text-right"
                      />
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => {
                          setPointFactors((prev) => {
                            const newFactors = { ...prev };
                            delete newFactors[instrument];
                            return newFactors;
                          });
                        }}
                        className="h-8 w-8 p-0 text-muted-foreground hover:text-destructive"
                      >
                        <X className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                ))}
                {Object.keys(pointFactors).length === 0 && (
                  <p className="text-sm text-muted-foreground text-center py-4">
                    No instrument factors configured. Add one below.
                  </p>
                )}
              </div>

              {/* Add New Factor */}
              <div className="flex items-end gap-3 pt-4 border-t">
                <div className="flex-1">
                  <label className="text-xs font-medium text-muted-foreground mb-1 block">
                    Instrument Name
                  </label>
                  <input
                    type="text"
                    value={newInstrumentName}
                    onChange={(e) => setNewInstrumentName(e.target.value)}
                    placeholder="e.g., Gold (per 0.1)"
                    className="w-full px-3 py-2 bg-background border border-input rounded-md text-sm"
                  />
                </div>
                <div className="w-24">
                  <label className="text-xs font-medium text-muted-foreground mb-1 block">
                    Factor
                  </label>
                  <input
                    type="text"
                    inputMode="decimal"
                    value={newInstrumentFactor}
                    onChange={(e) =>
                      setNewInstrumentFactor(e.target.value.replace(",", "."))
                    }
                    placeholder="0.1"
                    className="w-full px-3 py-2 bg-background border border-input rounded-md text-sm"
                  />
                </div>
                <Button
                  variant="outline"
                  onClick={() => {
                    if (newInstrumentName.trim()) {
                      const factor = parseFloat(newInstrumentFactor) || 1.0;
                      setPointFactors((prev) => ({
                        ...prev,
                        [newInstrumentName.trim()]: factor,
                      }));
                      setNewInstrumentName("");
                      setNewInstrumentFactor("1.0");
                    }
                  }}
                  disabled={!newInstrumentName.trim()}
                  className="gap-2"
                >
                  <Plus className="h-4 w-4" />
                  Add
                </Button>
              </div>

              <p className="text-xs text-muted-foreground">
                Points are calculated as: |Closing - Opening| × Factor. A factor
                of 1.0 means no adjustment. Use 0.1 for instruments quoted per
                0.1 (like Gold), or 0.0001 for forex pips.
              </p>

              {/* Spread Cost Valid From Date */}
              <div className="mt-6 space-y-3">
                <label className="text-sm font-medium">
                  Spread Cost Analysis Valid From
                </label>
                <div className="flex items-center gap-3">
                  <input
                    type="date"
                    value={localSpreadCostValidFrom}
                    onChange={(e) =>
                      setLocalSpreadCostValidFrom(e.target.value)
                    }
                    className="px-3 py-2 rounded-md border border-input bg-background text-sm"
                  />
                </div>
                <p className="text-xs text-muted-foreground">
                  Spread cost analysis will only include transactions from this
                  date onwards. Set this to the date when reliable spread data
                  became available.
                </p>
              </div>

              {/* Spread Data Source Note */}
              <div className="mt-4 p-3 bg-muted/50 border border-border rounded-lg">
                <p className="text-xs text-muted-foreground">
                  <span className="font-medium">Spread Data Source:</span>{" "}
                  Market spread data and trading hours were last updated on{" "}
                  <span className="font-medium">January 6, 2026</span>. Data
                  sourced from{" "}
                  <a
                    href="https://tradenation.com/en-bs/tntrader-market-information-sheet/"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-primary hover:underline"
                  >
                    Trade Nation Market Information Sheet
                  </a>
                  .
                </p>
              </div>
            </CardContent>
          </Card>

          {/* Appearance */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Monitor className="h-5 w-5" />
                Appearance
              </CardTitle>
              <CardDescription>
                Customize how the application looks
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div>
                <label className="text-sm font-medium mb-3 block">Theme</label>
                <div className="flex gap-2">
                  {(
                    [
                      { value: "light", label: "Light", icon: Sun },
                      { value: "dark", label: "Dark", icon: Moon },
                      { value: "system", label: "System", icon: Monitor },
                    ] as const
                  ).map((option) => {
                    const Icon = option.icon;
                    return (
                      <Button
                        key={option.value}
                        variant={
                          mounted && theme === option.value
                            ? "default"
                            : "outline"
                        }
                        onClick={() => setTheme(option.value)}
                        className="gap-2"
                      >
                        <Icon className="h-4 w-4" />
                        {option.label}
                      </Button>
                    );
                  })}
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Data Management */}
          <Card className="border-destructive/50">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-destructive">
                <Database className="h-5 w-5" />
                Data Management
              </CardTitle>
              <CardDescription>
                Delete account data or clear the entire database
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Success/Error Messages */}
              {deleteSuccess && (
                <div className="p-3 bg-green-500/10 border border-green-500/20 rounded-lg flex items-center gap-2 text-green-500">
                  <Check className="h-4 w-4" />
                  <span className="text-sm">{deleteSuccess}</span>
                </div>
              )}
              {deleteError && (
                <div className="p-3 bg-destructive/10 border border-destructive/20 rounded-lg flex items-center gap-2 text-destructive">
                  <AlertTriangle className="h-4 w-4" />
                  <span className="text-sm">{deleteError}</span>
                </div>
              )}

              {/* Account Selection */}
              <div>
                <label className="text-sm font-medium mb-3 block">
                  Select Data to Delete
                </label>
                <select
                  value={selectedAccountToDelete ?? ""}
                  onChange={(e) => {
                    const val = e.target.value;
                    setSelectedAccountToDelete(
                      val === "all" ? "all" : val ? Number(val) : null,
                    );
                    setDeleteConfirmText("");
                    setDeleteError(null);
                    setDeleteSuccess(null);
                  }}
                  className="w-full max-w-md px-3 py-2 bg-background border border-input rounded-md text-sm"
                >
                  <option value="">-- Select an option --</option>
                  {accounts &&
                    accounts.length > 0 &&
                    accounts.map((acc) => (
                      <option key={acc.account_id} value={acc.account_id}>
                        {acc.account_name} ({acc.broker_name}) - Account #
                        {acc.account_id}
                      </option>
                    ))}
                  <option value="all">⚠️ ALL DATA (Entire Database)</option>
                </select>
              </div>

              {/* Warning and Confirmation */}
              {selectedAccountToDelete !== null && (
                <div className="space-y-4">
                  <div className="p-4 bg-destructive/10 border border-destructive/30 rounded-lg">
                    <div className="flex items-start gap-3">
                      <AlertTriangle className="h-5 w-5 text-destructive mt-0.5" />
                      <div>
                        <p className="font-medium text-destructive">
                          {selectedAccountToDelete === "all"
                            ? "Warning: This will delete ALL data!"
                            : "Warning: This will delete all transactions for this account!"}
                        </p>
                        <p className="text-sm text-muted-foreground mt-1">
                          {selectedAccountToDelete === "all"
                            ? "All accounts, transactions, and imported data will be permanently removed. This action cannot be undone."
                            : "All transactions associated with this account will be permanently deleted. This action cannot be undone."}
                        </p>
                      </div>
                    </div>
                  </div>

                  {/* Confirmation Input */}
                  <div>
                    <label className="text-sm font-medium mb-2 block">
                      Type{" "}
                      <span className="font-mono bg-muted px-1.5 py-0.5 rounded text-destructive">
                        {selectedAccountToDelete === "all"
                          ? "DELETE ALL"
                          : "DELETE"}
                      </span>{" "}
                      to confirm
                    </label>
                    <input
                      type="text"
                      value={deleteConfirmText}
                      onChange={(e) => setDeleteConfirmText(e.target.value)}
                      placeholder={
                        selectedAccountToDelete === "all"
                          ? "DELETE ALL"
                          : "DELETE"
                      }
                      className="w-full max-w-md px-3 py-2 bg-background border border-input rounded-md text-sm"
                    />
                  </div>

                  {/* Delete Button */}
                  <Button
                    variant="destructive"
                    disabled={
                      isDeleting ||
                      (selectedAccountToDelete === "all"
                        ? deleteConfirmText !== "DELETE ALL"
                        : deleteConfirmText !== "DELETE")
                    }
                    onClick={async () => {
                      setIsDeleting(true);
                      setDeleteError(null);
                      setDeleteSuccess(null);

                      try {
                        if (selectedAccountToDelete === "all") {
                          // Delete all transactions
                          const result = await api.deleteTransactions();
                          setDeleteSuccess(
                            result.message || "All data deleted successfully",
                          );
                        } else {
                          // Delete transactions for specific account (not the account itself)
                          const result = await api.deleteTransactions(
                            selectedAccountToDelete,
                          );
                          setDeleteSuccess(
                            result.message ||
                              "Transactions deleted successfully",
                          );
                        }
                        setSelectedAccountToDelete(null);
                        setDeleteConfirmText("");
                      } catch (err) {
                        setDeleteError(
                          err instanceof Error
                            ? err.message
                            : "An error occurred",
                        );
                      } finally {
                        setIsDeleting(false);
                      }
                    }}
                    className="gap-2"
                  >
                    <Trash2 className="h-4 w-4" />
                    {isDeleting
                      ? "Deleting..."
                      : selectedAccountToDelete === "all"
                        ? "Delete All Data"
                        : "Delete Account Data"}
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Account Info */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Settings className="h-5 w-5" />
                Account Information
              </CardTitle>
              <CardDescription>Your trading account details</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {accounts && accounts.length > 0 ? (
                  accounts.map((acc) => (
                    <div
                      key={acc.account_id}
                      className="p-4 bg-accent/50 rounded-lg"
                    >
                      <p className="text-sm text-muted-foreground">
                        {acc.broker_name}
                      </p>
                      <p className="font-medium">{acc.account_name}</p>
                      <p className="text-xs text-muted-foreground">
                        Account #{acc.account_id}
                      </p>
                    </div>
                  ))
                ) : (
                  <div className="col-span-2 p-4 bg-accent/50 rounded-lg text-center text-muted-foreground">
                    No accounts found. Import data to get started.
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
