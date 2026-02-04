"use client";

import * as React from "react";
import { useSettingsStore } from "@/store/settings";
import {
  Upload,
  Plus,
  Trash2,
  FileSpreadsheet,
  Database,
  RefreshCw,
  Download,
  AlertCircle,
  CheckCircle,
  Loader2,
  Building,
  CreditCard,
  BarChart3,
} from "lucide-react";

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
import * as api from "@/lib/api";

// Use types from centralized API
type Account = api.Account & { transaction_count: number };
type Broker = api.Broker;
type DatabaseStats = api.DatabaseStats;
type ImportResult = api.ImportResult;

export default function ImportPage() {
  // State
  const [accounts, setAccounts] = React.useState<Account[]>([]);
  const [brokers, setBrokers] = React.useState<Broker[]>([]);
  const [stats, setStats] = React.useState<DatabaseStats | null>(null);
  const [isLoading, setIsLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);

  // Import state
  const [selectedAccountId, setSelectedAccountId] = React.useState<
    number | null
  >(null);
  const [selectedBroker, setSelectedBroker] =
    React.useState<string>("trade_nation");
  const [isUploading, setIsUploading] = React.useState(false);
  const [uploadResult, setUploadResult] = React.useState<ImportResult | null>(
    null,
  );

  // New account form - show by default when no accounts exist
  const [showNewAccount, setShowNewAccount] = React.useState(true);
  const { defaultCurrency } = useSettingsStore();
  const [newAccountName, setNewAccountName] = React.useState("");
  const [newAccountBroker, setNewAccountBroker] = React.useState("");
  const [newAccountCurrency, setNewAccountCurrency] = React.useState(
    defaultCurrency || "",
  );

  const [newAccountNotes, setNewAccountNotes] = React.useState("");

  // Fetch data using centralized API client
  const fetchData = React.useCallback(async () => {
    setIsLoading(true);
    setError(null);

    // Fetch brokers first - this should always work
    try {
      const brokersData = await api.getBrokers();
      setBrokers(brokersData);
    } catch (err) {
      console.error("Failed to fetch brokers:", err);
    }

    // Fetch accounts and stats - may fail on first run
    try {
      const [accountsResult, statsResult] = await Promise.allSettled([
        api.getAccounts(),
        api.getDatabaseStats(),
      ]);

      // Process accounts
      if (accountsResult.status === "fulfilled") {
        const accountsData = accountsResult.value as Account[];
        setAccounts(accountsData);

        // Select first account by default, hide new account form if accounts exist
        if (accountsData.length > 0) {
          if (!selectedAccountId) {
            setSelectedAccountId(accountsData[0].account_id);
          }
          setShowNewAccount(false);
        } else {
          setShowNewAccount(true);
        }
      } else {
        // No accounts or failed to fetch - show new account form
        setAccounts([]);
        setShowNewAccount(true);
      }

      // Process stats
      if (statsResult.status === "fulfilled") {
        setStats(statsResult.value);
      }
    } catch (err) {
      console.error("Failed to fetch data:", err);
      setShowNewAccount(true);
    } finally {
      setIsLoading(false);
    }
  }, [selectedAccountId]);

  React.useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Auto-select broker/file format when account is selected
  React.useEffect(() => {
    if (selectedAccountId && accounts.length > 0) {
      const account = accounts.find((a) => a.account_id === selectedAccountId);
      if (account?.broker_name) {
        setSelectedBroker(account.broker_name);
      }
    }
  }, [selectedAccountId, accounts]);

  // Handle file upload using centralized API client
  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !selectedAccountId) return;

    setIsUploading(true);
    setUploadResult(null);
    setError(null);

    try {
      const result = await api.uploadTransactionFile(
        file,
        selectedAccountId,
        selectedBroker,
      );
      setUploadResult(result);
      // Refresh data after successful import
      await fetchData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setIsUploading(false);
      // Reset file input
      e.target.value = "";
    }
  };

  // Create new account using centralized API client
  const handleCreateAccount = async () => {
    if (!newAccountName || !newAccountBroker) {
      setError("Account name and broker are required");
      return;
    }

    try {
      await api.createAccount({
        accountName: newAccountName,
        brokerName: newAccountBroker,
        currency: newAccountCurrency,
        initialBalance: 0,
        notes: newAccountNotes || null,
      });

      // Reset form and refresh
      setShowNewAccount(false);
      setNewAccountName("");
      setNewAccountBroker("");
      setNewAccountCurrency(defaultCurrency || "");
      setNewAccountNotes("");
      await fetchData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create account");
    }
  };

  // Toggle include in stats for an account
  const handleToggleIncludeInStats = async (
    accountId: number,
    currentValue: boolean,
  ) => {
    try {
      await api.updateAccount(accountId, {
        includeInStats: !currentValue,
      });
      await fetchData();
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Failed to update account settings",
      );
    }
  };

  // Delete account using centralized API client
  const handleDeleteAccount = async (
    accountId: number,
    accountName: string,
    hasTransactions: boolean,
  ) => {
    const confirmMsg = hasTransactions
      ? `Delete account "${accountName}" and all its transactions?`
      : `Delete account "${accountName}"?`;

    if (!confirm(confirmMsg)) return;

    try {
      await api.deleteAccount(accountId, hasTransactions);
      await fetchData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete account");
    }
  };

  // Export transactions
  const handleExport = async () => {
    try {
      const url = selectedAccountId
        ? `/api/import/export?accountId=${selectedAccountId}`
        : `/api/import/export`;

      window.open(url, "_blank");
    } catch (err) {
      setError("Failed to start export");
    }
  };

  // Format file size
  const formatBytes = (bytes: number) => {
    if (bytes === 0) return "0 B";
    const k = 1024;
    const sizes = ["B", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
  };

  return (
    <div className="min-h-screen bg-background p-6 md:p-8">
      <div className="container mx-auto max-w-6xl">
        {/* Page Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold tracking-tight">Data Import</h1>
              <p className="text-muted-foreground mt-1">
                Import transaction data from your broker CSV files
              </p>
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                onClick={fetchData}
                disabled={isLoading}
              >
                <RefreshCw
                  className={cn("h-4 w-4 mr-2", isLoading && "animate-spin")}
                />
                Refresh
              </Button>
              <Button variant="outline" onClick={handleExport}>
                <Download className="h-4 w-4 mr-2" />
                Export
              </Button>
            </div>
          </div>
        </div>

        {/* Error/Success Messages */}
        {error && (
          <div className="mb-6 p-4 bg-red-500/10 border border-red-500/50 rounded-lg flex items-center gap-3">
            <AlertCircle className="h-5 w-5 text-red-500" />
            <span className="text-red-500">{error}</span>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setError(null)}
              className="ml-auto"
            >
              Dismiss
            </Button>
          </div>
        )}

        {uploadResult && (
          <div className="mb-6 p-4 bg-green-500/10 border border-green-500/50 rounded-lg flex items-center gap-3">
            <CheckCircle className="h-5 w-5 text-green-500" />
            <div>
              <span className="text-green-500 font-medium">
                {uploadResult.message}
              </span>
              <span className="text-muted-foreground ml-2">
                ({uploadResult.recordsImported} new,{" "}
                {uploadResult.recordsSkipped} skipped)
              </span>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setUploadResult(null)}
              className="ml-auto"
            >
              Dismiss
            </Button>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column - Accounts */}
          <div className="lg:col-span-1 space-y-6">
            {/* Database Stats */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-base">
                  <Database className="h-4 w-4" />
                  Database
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {stats ? (
                  <>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">
                        Transactions
                      </span>
                      <span className="font-medium">
                        {stats.totalTransactions.toLocaleString()}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Accounts</span>
                      <span className="font-medium">{stats.totalAccounts}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Size</span>
                      <span className="font-medium">
                        {formatBytes(stats.databaseSizeBytes)}
                      </span>
                    </div>
                    {stats.dateRange && (
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">
                          Date Range
                        </span>
                        <span className="font-medium text-xs">
                          {new Date(stats.dateRange.from).toLocaleDateString()}{" "}
                          - {new Date(stats.dateRange.to).toLocaleDateString()}
                        </span>
                      </div>
                    )}
                    <div className="flex flex-wrap gap-1 pt-2">
                      {stats.currencies.map((currency) => (
                        <Badge
                          key={currency}
                          variant="secondary"
                          className="text-xs"
                        >
                          {currency}
                        </Badge>
                      ))}
                    </div>
                  </>
                ) : (
                  <div className="text-muted-foreground text-sm">
                    Loading...
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Accounts List */}
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle className="flex items-center gap-2 text-base">
                    <CreditCard className="h-4 w-4" />
                    Accounts
                  </CardTitle>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setShowNewAccount(!showNewAccount)}
                  >
                    <Plus className="h-4 w-4" />
                  </Button>
                </div>
              </CardHeader>
              <CardContent className="space-y-2">
                {/* New Account Form */}
                {showNewAccount && (
                  <div className="p-3 border rounded-lg space-y-3 mb-4">
                    {accounts.length === 0 && (
                      <div className="text-sm text-muted-foreground mb-2 pb-2 border-b">
                        <strong>Welcome!</strong> Create your first account to
                        start importing trading data.
                      </div>
                    )}
                    <input
                      type="text"
                      placeholder="Account Name"
                      value={newAccountName}
                      onChange={(e) => setNewAccountName(e.target.value)}
                      className="w-full px-3 py-2 bg-background border rounded-md text-sm"
                    />
                    <select
                      value={newAccountBroker}
                      onChange={(e) => setNewAccountBroker(e.target.value)}
                      className="w-full px-3 py-2 bg-background border rounded-md text-sm"
                    >
                      <option value="">Select Broker</option>
                      {brokers.map((broker) => (
                        <option key={broker.key} value={broker.key}>
                          {broker.name}
                        </option>
                      ))}
                    </select>
                    <select
                      value={newAccountCurrency}
                      onChange={(e) => setNewAccountCurrency(e.target.value)}
                      className="w-full px-3 py-2 bg-background border rounded-md text-sm"
                    >
                      <option value="SEK">SEK</option>
                      <option value="EUR">EUR</option>
                      <option value="USD">USD</option>
                      <option value="GBP">GBP</option>
                      <option value="DKK">DKK</option>
                    </select>
                    <textarea
                      placeholder="Notes (optional)"
                      value={newAccountNotes}
                      onChange={(e) => setNewAccountNotes(e.target.value)}
                      className="w-full px-3 py-2 bg-background border rounded-md text-sm resize-none"
                      rows={2}
                    />
                    <div className="flex gap-2">
                      <Button
                        size="sm"
                        onClick={handleCreateAccount}
                        className="flex-1"
                      >
                        Create
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => setShowNewAccount(false)}
                      >
                        Cancel
                      </Button>
                    </div>
                  </div>
                )}

                {/* Account List */}
                {accounts.length === 0 && !showNewAccount ? (
                  <div className="text-muted-foreground text-sm text-center py-4">
                    <p className="mb-2">No accounts yet.</p>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => setShowNewAccount(true)}
                    >
                      <Plus className="h-4 w-4 mr-1" />
                      Create Account
                    </Button>
                  </div>
                ) : accounts.length === 0 ? null : (
                  accounts.map((account) => (
                    <div
                      key={account.account_id}
                      className={cn(
                        "p-3 rounded-lg border cursor-pointer transition-colors",
                        selectedAccountId === account.account_id
                          ? "border-primary bg-primary/5"
                          : "hover:bg-accent",
                      )}
                      onClick={() => setSelectedAccountId(account.account_id)}
                    >
                      <div className="flex items-center justify-between">
                        <div>
                          <div className="font-medium">
                            {account.account_name}
                          </div>
                          <div className="text-xs text-muted-foreground">
                            {account.broker_name} • {account.currency}
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <Badge variant="secondary">
                            {account.transaction_count}
                          </Badge>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleToggleIncludeInStats(
                                account.account_id,
                                account.include_in_stats !== false,
                              );
                            }}
                            className="h-8 w-8 p-0"
                            title={
                              account.include_in_stats !== false
                                ? "Included in statistics - click to exclude"
                                : "Excluded from statistics - click to include"
                            }
                          >
                            <BarChart3
                              className={cn(
                                "h-4 w-4",
                                account.include_in_stats !== false
                                  ? "text-primary"
                                  : "text-muted-foreground/40",
                              )}
                            />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleDeleteAccount(
                                account.account_id,
                                account.account_name,
                                account.transaction_count > 0,
                              );
                            }}
                            className="h-8 w-8 p-0"
                          >
                            <Trash2 className="h-4 w-4 text-muted-foreground hover:text-red-500" />
                          </Button>
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </CardContent>
            </Card>
          </div>

          {/* Right Column - Import */}
          <div className="lg:col-span-2">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Upload className="h-5 w-5" />
                  Import Transactions
                </CardTitle>
                <CardDescription>
                  Upload a CSV file exported from your broker
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                {/* Account & Broker Selection */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="text-sm font-medium mb-2 block">
                      Target Account
                    </label>
                    <select
                      value={selectedAccountId || ""}
                      onChange={(e) =>
                        setSelectedAccountId(
                          e.target.value ? parseInt(e.target.value) : null,
                        )
                      }
                      className="w-full px-3 py-2 bg-background border rounded-md"
                    >
                      <option value="">Select Account</option>
                      {accounts.map((account) => (
                        <option
                          key={account.account_id}
                          value={account.account_id}
                        >
                          {account.account_name} ({account.currency})
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="text-sm font-medium mb-2 block">
                      File Format
                    </label>
                    <div className="w-full px-3 py-2 bg-muted border rounded-md text-muted-foreground">
                      {brokers.find((b) => b.key === selectedBroker)?.name ||
                        selectedBroker}
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">
                      Format is determined by the account&apos;s broker
                    </p>
                  </div>
                </div>

                {/* Upload Area */}
                <div className="flex items-center gap-4">
                  <input
                    type="file"
                    accept=".csv"
                    onChange={handleFileUpload}
                    disabled={!selectedAccountId || isUploading}
                    className="hidden"
                    id="csv-upload"
                  />
                  <label
                    htmlFor="csv-upload"
                    className={cn(
                      "inline-flex items-center gap-2 px-4 py-2 rounded-md font-medium transition-colors",
                      selectedAccountId && !isUploading
                        ? "bg-primary text-primary-foreground hover:bg-primary/90 cursor-pointer"
                        : "bg-muted text-muted-foreground cursor-not-allowed",
                    )}
                  >
                    {isUploading ? (
                      <>
                        <Loader2 className="h-4 w-4 animate-spin" />
                        Uploading...
                      </>
                    ) : (
                      <>
                        <FileSpreadsheet className="h-4 w-4" />
                        Choose CSV File
                      </>
                    )}
                  </label>
                  <p className="text-sm text-muted-foreground">
                    {selectedAccountId
                      ? "Supports TransactionHistory.csv from Trade Nation and TD365"
                      : "Select an account first"}
                  </p>
                </div>

                {/* Import Instructions */}
                <div className="bg-accent/50 rounded-lg p-4">
                  <h4 className="font-medium mb-2 flex items-center gap-2">
                    <Building className="h-4 w-4" />
                    How to Export from Your Broker
                  </h4>
                  <div className="space-y-3 text-sm text-muted-foreground">
                    <div>
                      <span className="font-medium text-foreground">
                        Trade Nation:
                      </span>{" "}
                      Go to History → Click Export → Select date range →
                      Download CSV
                    </div>
                    <div>
                      <span className="font-medium text-foreground">
                        TD365:
                      </span>{" "}
                      Go to Account → Transaction History → Export to CSV
                    </div>
                    <div className="pt-2 border-t border-border">
                      <span className="font-medium text-foreground">Tips:</span>
                      <ul className="list-disc list-inside mt-1 space-y-1">
                        <li>
                          Duplicate transactions are automatically skipped
                        </li>
                        <li>
                          Make sure to select the correct account and format
                        </li>
                        <li>
                          Files should include Transaction Date, Action, P/L
                          columns
                        </li>
                      </ul>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}
