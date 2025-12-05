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
const EDITABLE_CURRENCIES = ["SEK", "DKK", "EUR", "USD", "GBP", "NOK", "CHF"];

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

  // Track initial currency settings for change detection
  const [initialCurrency, setInitialCurrency] = React.useState<string | null>(
    null,
  );
  const [initialShowConverted, setInitialShowConverted] = React.useState<
    boolean | null
  >(null);

  // Settings store (source of truth from backend)
  const {
    defaultCurrency,
    showConverted,
    setDefaultCurrency,
    setShowConverted,
    isLoaded: settingsLoaded,
  } = useSettingsStore();

  // Currency store (formatting only)
  const { formatAmount } = useCurrencyStore();

  // Local state for exchange rates (these are stored in backend)
  const [exchangeRates, setExchangeRates] = React.useState<{
    baseCurrency: string;
    rates: Record<string, number>;
    updatedAt: string | null;
  } | null>(null);
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

  // Initialize local rates and track initial values
  React.useEffect(() => {
    if (exchangeRates?.rates) {
      setLocalRates(exchangeRates.rates);
    }
    // Set initial values for change tracking (only once)
    if (initialCurrency === null) {
      setInitialCurrency(defaultCurrency);
    }
    if (initialShowConverted === null) {
      setInitialShowConverted(showConverted);
    }
  }, [
    exchangeRates,
    defaultCurrency,
    showConverted,
    initialCurrency,
    initialShowConverted,
  ]);

  // Recalculate rates when default currency changes
  React.useEffect(() => {
    if (defaultCurrency && exchangeRates) {
      const newRates = calculateRatesRelativeTo(defaultCurrency);
      setLocalRates(newRates);
      // Update the store with new base currency and rates
      setExchangeRates({
        baseCurrency: defaultCurrency,
        rates: newRates,
        updatedAt: new Date().toISOString(),
      });
    }
  }, [defaultCurrency]);

  // Track changes - include currency store changes
  React.useEffect(() => {
    const currencyChanged =
      initialCurrency !== null && defaultCurrency !== initialCurrency;
    const showConvertedChanged =
      initialShowConverted !== null && showConverted !== initialShowConverted;
    const ratesChanged =
      editingRates &&
      exchangeRates?.rates &&
      JSON.stringify(localRates) !== JSON.stringify(exchangeRates.rates);

    setHasChanges(currencyChanged || showConvertedChanged || !!ratesChanged);
  }, [
    defaultCurrency,
    showConverted,
    initialCurrency,
    initialShowConverted,
    localRates,
    editingRates,
    exchangeRates,
  ]);

  // Handle save - saves to backend via settings store
  const handleSave = async () => {
    try {
      // Save currency preferences to backend
      await setDefaultCurrency(defaultCurrency);
      await setShowConverted(showConverted);

      // Save exchange rates
      if (exchangeRates) {
        setExchangeRates({
          baseCurrency: defaultCurrency,
          rates: localRates,
          updatedAt: new Date().toISOString(),
        });
      }

      // Update initial values to current (so changes are relative to saved state)
      setInitialCurrency(defaultCurrency);
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
    }
    // Recalculate rates for the initial currency
    const resetRates = calculateRatesRelativeTo(initialCurrency || "SEK");
    setLocalRates(resetRates);
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
                    (c) => c !== (exchangeRates?.baseCurrency || "SEK"),
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
                          type="number"
                          step="0.01"
                          value={localRates[currency] || ""}
                          onChange={(e) =>
                            updateRate(
                              currency,
                              parseFloat(e.target.value) || 0,
                            )
                          }
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
                          const res = await fetch(
                            "/api/import/transactions?confirm=true",
                            { method: "DELETE" },
                          );
                          if (!res.ok) {
                            const err = await res.json();
                            throw new Error(
                              err.detail || "Failed to delete data",
                            );
                          }
                          const result = await res.json();
                          setDeleteSuccess(
                            result.message || "All data deleted successfully",
                          );
                        } else {
                          // Delete transactions for specific account (not the account itself)
                          const res = await fetch(
                            `/api/import/transactions?accountId=${selectedAccountToDelete}&confirm=true`,
                            { method: "DELETE" },
                          );
                          if (!res.ok) {
                            const err = await res.json();
                            throw new Error(
                              err.detail || "Failed to delete transactions",
                            );
                          }
                          const result = await res.json();
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
