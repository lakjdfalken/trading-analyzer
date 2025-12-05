"use client";

import * as React from "react";
import { isValid } from "date-fns";
import {
  Search,
  Filter,
  Download,
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  TrendingUp,
  TrendingDown,
  Calendar,
  X,
  SlidersHorizontal,
  Building2,
} from "lucide-react";

import { cn } from "@/lib/utils";
import { useCurrencyStore } from "@/store/currency";
import { useSettingsStore } from "@/store/settings";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { DateRangePicker } from "@/components/filters/DateRangePicker";
import type { Trade } from "@/components/trades/RecentTradesList";
import type { DateRangePreset } from "@/components/filters/types";
import * as api from "@/lib/api";

// Sort configuration
type SortField =
  | "entryTime"
  | "instrument"
  | "direction"
  | "pnl"
  | "pnlPercent";
type SortDirection = "asc" | "desc";

interface SortConfig {
  field: SortField;
  direction: SortDirection;
}

// Filter state
interface FilterState {
  search: string;
  instruments: string[];
  direction: "all" | "long" | "short";
  outcome: "all" | "win" | "loss";
}

export default function TransactionsPage() {
  // Pagination state
  const [currentPage, setCurrentPage] = React.useState(1);
  const [pageSize, setPageSize] = React.useState(20);

  // Local date range state - default to last 3 days
  const [localDateRange, setLocalDateRange] = React.useState<{
    from: Date | undefined;
    to: Date | undefined;
    preset: DateRangePreset;
  }>({
    from: undefined,
    to: undefined,
    preset: "custom",
  });

  // Initialize date range on client side to avoid hydration issues
  const [isClient, setIsClient] = React.useState(false);
  React.useEffect(() => {
    const now = new Date();
    const threeDaysAgo = new Date(now);
    threeDaysAgo.setDate(now.getDate() - 3);
    threeDaysAgo.setHours(0, 0, 0, 0);
    setLocalDateRange({
      from: threeDaysAgo,
      to: now,
      preset: "custom",
    });
    setIsClient(true);
  }, []);

  // Sort state
  const [sortConfig, setSortConfig] = React.useState<SortConfig>({
    field: "entryTime",
    direction: "desc",
  });

  // Filter state
  const [filters, setFilters] = React.useState<FilterState>({
    search: "",
    instruments: [],
    direction: "all",
    outcome: "all",
  });

  const [showFilters, setShowFilters] = React.useState(false);

  // Currency store (formatting only)
  const { formatAmount } = useCurrencyStore();

  // Settings store (default currency from backend)
  const { defaultCurrency, isLoaded: settingsLoaded } = useSettingsStore();

  // Export notification state
  const [exportNotification, setExportNotification] = React.useState<
    string | null
  >(null);

  // Local trades state for this page
  const [trades, setTrades] = React.useState<Trade[]>([]);
  const [isLoading, setIsLoading] = React.useState(false);

  // Account state
  const [accounts, setAccounts] = React.useState<api.Account[]>([]);
  const [selectedAccountId, setSelectedAccountId] = React.useState<
    number | null
  >(null);

  // Fetch accounts on mount using centralized API
  React.useEffect(() => {
    const fetchAccounts = async () => {
      try {
        const accountsData = await api.getAccounts();
        setAccounts(accountsData);
      } catch (error) {
        console.error("Failed to fetch accounts:", error);
      }
    };
    fetchAccounts();
  }, []);

  // Fetch data when date range or account changes (wait for settings)
  React.useEffect(() => {
    if (!isClient || !localDateRange.from || !settingsLoaded) return;

    const fetchData = async () => {
      setIsLoading(true);
      try {
        const tradesData = await api.getRecentTrades(
          500,
          {
            from: localDateRange.from,
            to: localDateRange.to,
          },
          undefined,
          selectedAccountId ?? undefined,
        );

        // Map API response to frontend Trade type
        const mappedTrades: Trade[] = tradesData.map((t) => {
          const entryTime = t.entryTime ? new Date(t.entryTime) : new Date();
          const exitTime = t.exitTime ? new Date(t.exitTime) : new Date();
          return {
            id: t.id,
            instrument: t.instrument,
            direction: t.direction,
            entryPrice: t.entryPrice,
            exitPrice: t.exitPrice,
            entryTime: isValid(entryTime) ? entryTime : new Date(),
            exitTime: isValid(exitTime) ? exitTime : new Date(),
            quantity: t.quantity,
            pnl: t.pnl,
            pnlPercent: t.pnlPercent,
            currency: t.currency,
          };
        });
        setTrades(mappedTrades);
      } catch (error) {
        console.error("Failed to fetch trades:", error);
      } finally {
        setIsLoading(false);
      }
    };
    fetchData();
  }, [localDateRange, isClient, selectedAccountId, settingsLoaded]);

  // Get unique instruments for filter
  const availableInstruments = React.useMemo(() => {
    return Array.from(new Set(trades.map((t) => t.instrument))).sort();
  }, [trades]);

  // Filter trades
  const filteredTrades = React.useMemo(() => {
    return trades.filter((trade) => {
      // Search filter
      if (filters.search) {
        const searchLower = filters.search.toLowerCase();
        if (!trade.instrument.toLowerCase().includes(searchLower)) {
          return false;
        }
      }

      // Instrument filter
      if (
        filters.instruments.length > 0 &&
        !filters.instruments.includes(trade.instrument)
      ) {
        return false;
      }

      // Direction filter
      if (
        filters.direction !== "all" &&
        trade.direction !== filters.direction
      ) {
        return false;
      }

      // Outcome filter
      if (filters.outcome !== "all") {
        const isWin = trade.pnl > 0;
        if (filters.outcome === "win" && !isWin) return false;
        if (filters.outcome === "loss" && isWin) return false;
      }

      return true;
    });
  }, [trades, filters]);

  // Sort trades
  const sortedTrades = React.useMemo(() => {
    return [...filteredTrades].sort((a, b) => {
      let aValue: string | number | Date;
      let bValue: string | number | Date;

      switch (sortConfig.field) {
        case "entryTime":
          aValue = a.entryTime;
          bValue = b.entryTime;
          break;
        case "instrument":
          aValue = a.instrument;
          bValue = b.instrument;
          break;
        case "direction":
          aValue = a.direction;
          bValue = b.direction;
          break;
        case "pnl":
          aValue = a.pnl;
          bValue = b.pnl;
          break;
        case "pnlPercent":
          aValue = a.pnlPercent;
          bValue = b.pnlPercent;
          break;
        default:
          aValue = a.entryTime;
          bValue = b.entryTime;
      }

      if (aValue < bValue) return sortConfig.direction === "asc" ? -1 : 1;
      if (aValue > bValue) return sortConfig.direction === "asc" ? 1 : -1;
      return 0;
    });
  }, [filteredTrades, sortConfig]);

  // Paginate trades
  const paginatedTrades = React.useMemo(() => {
    const startIndex = (currentPage - 1) * pageSize;
    return sortedTrades.slice(startIndex, startIndex + pageSize);
  }, [sortedTrades, currentPage, pageSize]);

  // Pagination info
  const totalPages = Math.ceil(sortedTrades.length / pageSize);
  const startIndex = (currentPage - 1) * pageSize + 1;
  const endIndex = Math.min(currentPage * pageSize, sortedTrades.length);

  // Handle sort
  const handleSort = (field: SortField) => {
    setSortConfig((prev) => ({
      field,
      direction:
        prev.field === field && prev.direction === "asc" ? "desc" : "asc",
    }));
  };

  // Get sort icon
  const getSortIcon = (field: SortField) => {
    if (sortConfig.field !== field) {
      return <ArrowUpDown className="h-4 w-4 ml-1 opacity-50" />;
    }
    return sortConfig.direction === "asc" ? (
      <ArrowUp className="h-4 w-4 ml-1" />
    ) : (
      <ArrowDown className="h-4 w-4 ml-1" />
    );
  };

  // Handle date range change
  const handleDateRangeChange = (newRange: {
    from: Date | undefined;
    to: Date | undefined;
    preset?: DateRangePreset;
  }) => {
    setLocalDateRange({
      from: newRange.from,
      to: newRange.to,
      preset: newRange.preset || "custom",
    });
    setCurrentPage(1);
  };

  // Handle account change
  const handleAccountChange = (accountId: number | null) => {
    setSelectedAccountId(accountId);
    setCurrentPage(1);
  };

  // Clear filters
  const clearFilters = () => {
    setFilters({
      search: "",
      instruments: [],
      direction: "all",
      outcome: "all",
    });
  };

  const hasActiveFilters =
    filters.search !== "" ||
    filters.instruments.length > 0 ||
    filters.direction !== "all" ||
    filters.outcome !== "all";

  // Export to CSV
  const handleExport = () => {
    const tradesToExport = sortedTrades;

    const headers = [
      "Date",
      "Time",
      "Instrument",
      "Direction",
      "Entry Price",
      "Exit Price",
      "Quantity",
      "P&L",
      "P&L %",
      "Currency",
    ];

    const csvRows = tradesToExport.map((trade) => {
      const entryDate = new Date(trade.entryTime);
      return [
        entryDate.toLocaleDateString(),
        entryDate.toLocaleTimeString([], {
          hour: "2-digit",
          minute: "2-digit",
        }),
        trade.instrument,
        trade.direction,
        trade.entryPrice.toFixed(2),
        trade.exitPrice.toFixed(2),
        trade.quantity,
        trade.pnl.toFixed(2),
        trade.pnlPercent.toFixed(2),
        trade.currency || defaultCurrency,
      ].join(",");
    });

    const csvContent = [headers.join(","), ...csvRows].join("\n");
    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.setAttribute("href", url);
    link.setAttribute(
      "download",
      `trades-${new Date().toISOString().split("T")[0]}.csv`,
    );
    link.style.visibility = "hidden";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    setExportNotification(`Exported ${tradesToExport.length} trades to CSV`);
    setTimeout(() => setExportNotification(null), 3000);
  };

  // Summary stats
  const summaryStats = React.useMemo(() => {
    if (sortedTrades.length === 0) return null;

    const totalPnl = sortedTrades.reduce((sum, t) => sum + t.pnl, 0);
    const wins = sortedTrades.filter((t) => t.pnl > 0).length;
    const losses = sortedTrades.filter((t) => t.pnl < 0).length;
    const winRate =
      sortedTrades.length > 0 ? (wins / sortedTrades.length) * 100 : 0;

    return {
      totalPnl,
      wins,
      losses,
      winRate,
      total: sortedTrades.length,
    };
  }, [sortedTrades]);

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border bg-card/50 backdrop-blur-sm sticky top-0 z-40">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold tracking-tight">
                Transactions
              </h1>
              <p className="text-sm text-muted-foreground">
                View and analyze your trading history
              </p>
            </div>

            <div className="flex items-center gap-4">
              {/* Account Selector */}
              <div className="flex items-center gap-2">
                <Building2 className="h-4 w-4 text-muted-foreground" />
                <select
                  value={selectedAccountId ?? ""}
                  onChange={(e) =>
                    handleAccountChange(
                      e.target.value ? parseInt(e.target.value) : null,
                    )
                  }
                  className="h-9 rounded-md border border-input bg-background px-3 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                >
                  <option value="">All Accounts</option>
                  {accounts.map((account) => (
                    <option key={account.account_id} value={account.account_id}>
                      {account.account_name}
                    </option>
                  ))}
                </select>
              </div>

              {/* Date Range Picker */}
              <DateRangePicker
                dateRange={{
                  from: localDateRange.from,
                  to: localDateRange.to,
                  preset: localDateRange.preset,
                }}
                onDateRangeChange={handleDateRangeChange}
              />

              {/* Export Button */}
              <Button
                variant="outline"
                size="sm"
                onClick={handleExport}
                disabled={sortedTrades.length === 0}
                className="gap-2"
              >
                <Download className="h-4 w-4" />
                Export
              </Button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-6 space-y-6">
        {/* Export Notification */}
        {exportNotification && (
          <div className="fixed bottom-4 right-4 bg-green-600 text-white px-4 py-2 rounded-md shadow-lg z-50">
            {exportNotification}
          </div>
        )}

        {/* Summary Stats */}
        {summaryStats && (
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            <Card>
              <CardContent className="pt-4">
                <div className="text-2xl font-bold">{summaryStats.total}</div>
                <p className="text-xs text-muted-foreground">Total Trades</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-4">
                <div
                  className={cn(
                    "text-2xl font-bold",
                    summaryStats.totalPnl >= 0
                      ? "text-green-500"
                      : "text-red-500",
                  )}
                >
                  {formatAmount(summaryStats.totalPnl, defaultCurrency)}
                </div>
                <p className="text-xs text-muted-foreground">Total P&L</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-4">
                <div className="text-2xl font-bold text-green-500">
                  {summaryStats.wins}
                </div>
                <p className="text-xs text-muted-foreground">Winning Trades</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-4">
                <div className="text-2xl font-bold text-red-500">
                  {summaryStats.losses}
                </div>
                <p className="text-xs text-muted-foreground">Losing Trades</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-4">
                <div
                  className={cn(
                    "text-2xl font-bold",
                    (summaryStats.winRate ?? 0) >= 50
                      ? "text-green-500"
                      : "text-yellow-500",
                  )}
                >
                  {(summaryStats.winRate ?? 0).toFixed(1)}%
                </div>
                <p className="text-xs text-muted-foreground">Win Rate</p>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Filters */}
        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                {/* Search */}
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  <input
                    type="text"
                    placeholder="Search instruments..."
                    value={filters.search}
                    onChange={(e) =>
                      setFilters((prev) => ({
                        ...prev,
                        search: e.target.value,
                      }))
                    }
                    className="h-9 w-64 rounded-md border border-input bg-background pl-9 pr-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                  />
                </div>

                {/* Toggle Filters */}
                <Button
                  variant={showFilters ? "secondary" : "outline"}
                  size="sm"
                  onClick={() => setShowFilters(!showFilters)}
                  className="gap-2"
                >
                  <SlidersHorizontal className="h-4 w-4" />
                  Filters
                  {hasActiveFilters && (
                    <Badge variant="default" className="ml-1 h-5 px-1.5">
                      {filters.instruments.length +
                        (filters.direction !== "all" ? 1 : 0) +
                        (filters.outcome !== "all" ? 1 : 0)}
                    </Badge>
                  )}
                </Button>

                {hasActiveFilters && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={clearFilters}
                    className="gap-1 text-muted-foreground"
                  >
                    <X className="h-4 w-4" />
                    Clear
                  </Button>
                )}
              </div>

              <div className="text-sm text-muted-foreground">
                {sortedTrades.length} trades
              </div>
            </div>

            {/* Filter Options */}
            {showFilters && (
              <div className="mt-4 flex flex-wrap gap-4 pt-4 border-t">
                {/* Direction Filter */}
                <div className="flex items-center gap-2">
                  <span className="text-sm text-muted-foreground">
                    Direction:
                  </span>
                  <div className="flex gap-1">
                    {(["all", "long", "short"] as const).map((dir) => (
                      <Button
                        key={dir}
                        variant={
                          filters.direction === dir ? "secondary" : "ghost"
                        }
                        size="sm"
                        onClick={() =>
                          setFilters((prev) => ({ ...prev, direction: dir }))
                        }
                      >
                        {dir === "all"
                          ? "All"
                          : dir === "long"
                            ? "Long"
                            : "Short"}
                      </Button>
                    ))}
                  </div>
                </div>

                {/* Outcome Filter */}
                <div className="flex items-center gap-2">
                  <span className="text-sm text-muted-foreground">
                    Outcome:
                  </span>
                  <div className="flex gap-1">
                    {(["all", "win", "loss"] as const).map((outcome) => (
                      <Button
                        key={outcome}
                        variant={
                          filters.outcome === outcome ? "secondary" : "ghost"
                        }
                        size="sm"
                        onClick={() =>
                          setFilters((prev) => ({ ...prev, outcome }))
                        }
                      >
                        {outcome === "all"
                          ? "All"
                          : outcome === "win"
                            ? "Winners"
                            : "Losers"}
                      </Button>
                    ))}
                  </div>
                </div>

                {/* Instrument Filter */}
                {availableInstruments.length > 0 && (
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-muted-foreground">
                      Instruments:
                    </span>
                    <div className="flex flex-wrap gap-1">
                      {availableInstruments.slice(0, 8).map((instrument) => (
                        <Button
                          key={instrument}
                          variant={
                            filters.instruments.includes(instrument)
                              ? "secondary"
                              : "ghost"
                          }
                          size="sm"
                          onClick={() =>
                            setFilters((prev) => ({
                              ...prev,
                              instruments: prev.instruments.includes(instrument)
                                ? prev.instruments.filter(
                                    (i) => i !== instrument,
                                  )
                                : [...prev.instruments, instrument],
                            }))
                          }
                        >
                          {instrument}
                        </Button>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </CardHeader>
        </Card>

        {/* Trades Table */}
        <Card>
          <CardContent className="p-0">
            {isLoading ? (
              <div className="flex items-center justify-center py-12">
                <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
              </div>
            ) : paginatedTrades.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12 text-center">
                <Calendar className="h-12 w-12 text-muted-foreground mb-4" />
                <h3 className="text-lg font-medium">No trades found</h3>
                <p className="text-muted-foreground mt-1">
                  Try adjusting your filters or date range
                </p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b">
                      <th
                        className="text-left p-4 font-medium cursor-pointer hover:bg-muted/50"
                        onClick={() => handleSort("entryTime")}
                      >
                        <div className="flex items-center">
                          Date/Time
                          {getSortIcon("entryTime")}
                        </div>
                      </th>
                      <th
                        className="text-left p-4 font-medium cursor-pointer hover:bg-muted/50"
                        onClick={() => handleSort("instrument")}
                      >
                        <div className="flex items-center">
                          Instrument
                          {getSortIcon("instrument")}
                        </div>
                      </th>
                      <th
                        className="text-left p-4 font-medium cursor-pointer hover:bg-muted/50"
                        onClick={() => handleSort("direction")}
                      >
                        <div className="flex items-center">
                          Direction
                          {getSortIcon("direction")}
                        </div>
                      </th>
                      <th className="text-right p-4 font-medium">Entry</th>
                      <th className="text-right p-4 font-medium">Exit</th>
                      <th className="text-right p-4 font-medium">Qty</th>
                      <th
                        className="text-right p-4 font-medium cursor-pointer hover:bg-muted/50"
                        onClick={() => handleSort("pnl")}
                      >
                        <div className="flex items-center justify-end">
                          P&L
                          {getSortIcon("pnl")}
                        </div>
                      </th>
                      <th
                        className="text-right p-4 font-medium cursor-pointer hover:bg-muted/50"
                        onClick={() => handleSort("pnlPercent")}
                      >
                        <div className="flex items-center justify-end">
                          P&L %{getSortIcon("pnlPercent")}
                        </div>
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {paginatedTrades.map((trade) => (
                      <tr
                        key={trade.id}
                        className="border-b last:border-0 hover:bg-muted/50"
                      >
                        <td className="p-4">
                          <div className="text-sm">
                            {new Date(trade.entryTime).toLocaleDateString(
                              "en-US",
                              {
                                month: "short",
                                day: "numeric",
                                year: "numeric",
                              },
                            )}
                          </div>
                          <div className="text-xs text-muted-foreground">
                            {new Date(trade.entryTime).toLocaleTimeString([], {
                              hour: "2-digit",
                              minute: "2-digit",
                            })}
                          </div>
                        </td>
                        <td className="p-4 font-medium">{trade.instrument}</td>
                        <td className="p-4">
                          <Badge
                            variant={
                              trade.direction === "long"
                                ? "default"
                                : "secondary"
                            }
                            className={cn(
                              "text-xs",
                              trade.direction === "long"
                                ? "bg-green-500/10 text-green-500"
                                : "bg-red-500/10 text-red-500",
                            )}
                          >
                            {trade.direction === "long" ? (
                              <TrendingUp className="h-3 w-3 mr-1" />
                            ) : (
                              <TrendingDown className="h-3 w-3 mr-1" />
                            )}
                            {trade.direction.toUpperCase()}
                          </Badge>
                        </td>
                        <td className="p-4 text-right font-mono text-sm">
                          {(trade.entryPrice ?? 0).toLocaleString(undefined, {
                            minimumFractionDigits: 2,
                          })}
                        </td>
                        <td className="p-4 text-right font-mono text-sm">
                          {(trade.exitPrice ?? 0).toLocaleString(undefined, {
                            minimumFractionDigits: 2,
                          })}
                        </td>
                        <td className="p-4 text-right font-mono text-sm">
                          {trade.quantity}
                        </td>
                        <td
                          className={cn(
                            "p-4 text-right font-mono text-sm font-medium",
                            trade.pnl >= 0 ? "text-green-500" : "text-red-500",
                          )}
                        >
                          {formatAmount(
                            trade.pnl,
                            trade.currency || defaultCurrency,
                          )}
                        </td>
                        <td
                          className={cn(
                            "p-4 text-right font-mono text-sm",
                            trade.pnl >= 0 ? "text-green-500" : "text-red-500",
                          )}
                        >
                          {(trade.pnlPercent ?? 0) >= 0 ? "+" : ""}
                          {(trade.pnlPercent ?? 0).toFixed(2)}%
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between border-t px-4 py-3">
              <div className="text-sm text-muted-foreground">
                Showing {startIndex} to {endIndex} of {sortedTrades.length}{" "}
                trades
              </div>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="icon"
                  onClick={() => setCurrentPage(1)}
                  disabled={currentPage === 1}
                >
                  <ChevronsLeft className="h-4 w-4" />
                </Button>
                <Button
                  variant="outline"
                  size="icon"
                  onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                  disabled={currentPage === 1}
                >
                  <ChevronLeft className="h-4 w-4" />
                </Button>
                <span className="text-sm px-2">
                  Page {currentPage} of {totalPages}
                </span>
                <Button
                  variant="outline"
                  size="icon"
                  onClick={() =>
                    setCurrentPage((p) => Math.min(totalPages, p + 1))
                  }
                  disabled={currentPage === totalPages}
                >
                  <ChevronRight className="h-4 w-4" />
                </Button>
                <Button
                  variant="outline"
                  size="icon"
                  onClick={() => setCurrentPage(totalPages)}
                  disabled={currentPage === totalPages}
                >
                  <ChevronsRight className="h-4 w-4" />
                </Button>
              </div>
            </div>
          )}
        </Card>
      </main>
    </div>
  );
}
