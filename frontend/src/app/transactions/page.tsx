"use client";

import * as React from "react";
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
} from "lucide-react";

import { cn } from "@/lib/utils";
import { useCurrencyStore } from "@/store/currency";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { DateRangePicker } from "@/components/filters/DateRangePicker";
import { useDashboardStore } from "@/store/dashboard";
import type { Trade } from "@/components/trades/RecentTradesList";
import type { DateRangePreset } from "@/components/filters/types";

// API base URL
// Use relative URL for same-origin requests (works with any port)
const API_BASE =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/api\/?$/, "") || "";

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

  // Currency store
  const { formatAmount } = useCurrencyStore();

  // Store state
  const {
    dateRange,
    recentTrades,
    loading,
    setDateRange,
    setRecentTrades,
    setLoading,
    isInitialized,
    setInitialized,
  } = useDashboardStore();

  // Fetch data on mount - always fetch fresh data for transactions page
  React.useEffect(() => {
    const fetchData = async () => {
      setLoading("recentTrades", true);
      try {
        const response = await fetch(`${API_BASE}/api/trades/recent?limit=100`);
        if (response.ok) {
          const tradesData = await response.json();
          // Map API response to frontend Trade type
          const mappedTrades = tradesData.map((t: Record<string, unknown>) => ({
            id: t.id || t.transaction_id,
            instrument: t.instrument || t.description,
            direction: t.direction || "long",
            entryPrice: t.entry_price || t.entryPrice || 0,
            exitPrice: t.exit_price || t.exitPrice || 0,
            entryTime: new Date(
              (t.entry_time || t.entryTime || t.open_period || Date.now()) as
                | string
                | number,
            ),
            exitTime: new Date(
              (t.exit_time ||
                t.exitTime ||
                t.transaction_date ||
                Date.now()) as string | number,
            ),
            quantity: t.quantity || t.amount || 1,
            pnl: t.pnl || t.pl || 0,
            pnlPercent: t.pnl_percent || t.pnlPercent || 0,
            currency: t.currency,
          }));
          setRecentTrades(mappedTrades);
        }
        setInitialized(true);
      } finally {
        setLoading("recentTrades", false);
      }
    };
    fetchData();
  }, [setLoading, setRecentTrades, setInitialized]);

  // Use trades from store
  const trades = recentTrades;

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
        if (
          !trade.instrument.toLowerCase().includes(searchLower) &&
          !trade.id.toLowerCase().includes(searchLower)
        ) {
          return false;
        }
      }

      // Instrument filter
      if (filters.instruments.length > 0) {
        if (!filters.instruments.includes(trade.instrument)) {
          return false;
        }
      }

      // Direction filter
      if (filters.direction !== "all") {
        if (trade.direction !== filters.direction) {
          return false;
        }
      }

      // Outcome filter
      if (filters.outcome !== "all") {
        const isWin = trade.pnl >= 0;
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
          aValue = new Date(a.entryTime).getTime();
          bValue = new Date(b.entryTime).getTime();
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
          return 0;
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
      return <ArrowUpDown className="h-4 w-4 opacity-50" />;
    }
    return sortConfig.direction === "asc" ? (
      <ArrowUp className="h-4 w-4" />
    ) : (
      <ArrowDown className="h-4 w-4" />
    );
  };

  // Handle date range change
  const handleDateRangeChange = (newRange: {
    from: Date | undefined;
    to: Date | undefined;
    preset?: DateRangePreset;
  }) => {
    setDateRange({
      from: newRange.from,
      to: newRange.to,
      preset: newRange.preset || "custom",
    });
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
    filters.search ||
    filters.instruments.length > 0 ||
    filters.direction !== "all" ||
    filters.outcome !== "all";

  // Calculate summary stats
  const summaryStats = React.useMemo(() => {
    const totalPnl = filteredTrades.reduce((sum, t) => sum + t.pnl, 0);
    const wins = filteredTrades.filter((t) => t.pnl >= 0).length;
    const losses = filteredTrades.filter((t) => t.pnl < 0).length;
    const winRate =
      filteredTrades.length > 0 ? (wins / filteredTrades.length) * 100 : 0;

    return { totalPnl, wins, losses, winRate, total: filteredTrades.length };
  }, [filteredTrades]);

  return (
    <div className="min-h-screen bg-background p-6 md:p-8">
      <div className="container mx-auto max-w-7xl">
        {/* Page Header */}
        <div className="mb-6">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            <div>
              <h1 className="text-2xl font-bold tracking-tight">
                Transactions
              </h1>
              <p className="text-muted-foreground mt-1">
                View and analyze all your trading transactions
              </p>
            </div>
            <div className="flex items-center gap-3">
              <DateRangePicker
                dateRange={{
                  from: dateRange.from,
                  to: dateRange.to,
                  preset: dateRange.preset,
                }}
                onDateRangeChange={handleDateRangeChange}
              />
              <Button variant="outline" size="sm" className="gap-2">
                <Download className="h-4 w-4" />
                Export
              </Button>
            </div>
          </div>
        </div>

        {/* Summary Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <Card>
            <CardContent className="pt-4 pb-4">
              <p className="text-sm text-muted-foreground">Total Trades</p>
              <p className="text-2xl font-bold">{summaryStats.total}</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-4 pb-4">
              <p className="text-sm text-muted-foreground">Total P&L</p>
              <p
                className={cn(
                  "text-2xl font-bold",
                  summaryStats.totalPnl >= 0
                    ? "text-green-500"
                    : "text-red-500",
                )}
              >
                {filteredTrades[0]?.currency
                  ? formatAmount(
                      summaryStats.totalPnl,
                      filteredTrades[0].currency,
                    )
                  : summaryStats.totalPnl.toLocaleString("en-US", {
                      minimumFractionDigits: 2,
                    })}
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-4 pb-4">
              <p className="text-sm text-muted-foreground">Win Rate</p>
              <p className="text-2xl font-bold">
                {summaryStats.winRate.toFixed(1)}%
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-4 pb-4">
              <p className="text-sm text-muted-foreground">Wins / Losses</p>
              <p className="text-2xl font-bold">
                <span className="text-green-500">{summaryStats.wins}</span>
                <span className="text-muted-foreground mx-1">/</span>
                <span className="text-red-500">{summaryStats.losses}</span>
              </p>
            </CardContent>
          </Card>
        </div>

        {/* Filters */}
        <Card className="mb-6">
          <CardContent className="pt-4">
            <div className="flex flex-col gap-4">
              {/* Search and Filter Toggle */}
              <div className="flex flex-col sm:flex-row gap-3">
                <div className="relative flex-1">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  <input
                    type="text"
                    placeholder="Search by instrument or ID..."
                    value={filters.search}
                    onChange={(e) =>
                      setFilters((prev) => ({
                        ...prev,
                        search: e.target.value,
                      }))
                    }
                    className="w-full pl-10 pr-4 py-2 bg-background border border-input rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                  />
                </div>
                <Button
                  variant="outline"
                  onClick={() => setShowFilters(!showFilters)}
                  className={cn("gap-2", showFilters && "bg-accent")}
                >
                  <SlidersHorizontal className="h-4 w-4" />
                  Filters
                  {hasActiveFilters && (
                    <Badge variant="secondary" className="ml-1 h-5 px-1.5">
                      {filters.instruments.length +
                        (filters.direction !== "all" ? 1 : 0) +
                        (filters.outcome !== "all" ? 1 : 0)}
                    </Badge>
                  )}
                </Button>
                {hasActiveFilters && (
                  <Button variant="ghost" size="sm" onClick={clearFilters}>
                    <X className="h-4 w-4 mr-1" />
                    Clear
                  </Button>
                )}
              </div>

              {/* Expanded Filters */}
              {showFilters && (
                <div className="flex flex-wrap gap-4 pt-2 border-t border-border">
                  {/* Direction Filter */}
                  <div>
                    <p className="text-xs font-medium text-muted-foreground mb-2">
                      Direction
                    </p>
                    <div className="flex gap-1">
                      {(["all", "long", "short"] as const).map((dir) => (
                        <Button
                          key={dir}
                          variant={
                            filters.direction === dir ? "default" : "outline"
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
                  <div>
                    <p className="text-xs font-medium text-muted-foreground mb-2">
                      Outcome
                    </p>
                    <div className="flex gap-1">
                      {(["all", "win", "loss"] as const).map((outcome) => (
                        <Button
                          key={outcome}
                          variant={
                            filters.outcome === outcome ? "default" : "outline"
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
                  <div>
                    <p className="text-xs font-medium text-muted-foreground mb-2">
                      Instruments
                    </p>
                    <div className="flex flex-wrap gap-1">
                      {availableInstruments.map((instrument) => (
                        <Button
                          key={instrument}
                          variant={
                            filters.instruments.includes(instrument)
                              ? "default"
                              : "outline"
                          }
                          size="sm"
                          onClick={() => {
                            setFilters((prev) => ({
                              ...prev,
                              instruments: prev.instruments.includes(instrument)
                                ? prev.instruments.filter(
                                    (i) => i !== instrument,
                                  )
                                : [...prev.instruments, instrument],
                            }));
                          }}
                        >
                          {instrument}
                        </Button>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Trades Table */}
        <Card>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-border">
                    <th className="text-left p-4">
                      <button
                        onClick={() => handleSort("entryTime")}
                        className="flex items-center gap-2 text-sm font-medium text-muted-foreground hover:text-foreground"
                      >
                        Date/Time
                        {getSortIcon("entryTime")}
                      </button>
                    </th>
                    <th className="text-left p-4">
                      <button
                        onClick={() => handleSort("instrument")}
                        className="flex items-center gap-2 text-sm font-medium text-muted-foreground hover:text-foreground"
                      >
                        Instrument
                        {getSortIcon("instrument")}
                      </button>
                    </th>
                    <th className="text-left p-4">
                      <button
                        onClick={() => handleSort("direction")}
                        className="flex items-center gap-2 text-sm font-medium text-muted-foreground hover:text-foreground"
                      >
                        Direction
                        {getSortIcon("direction")}
                      </button>
                    </th>
                    <th className="text-right p-4">
                      <span className="text-sm font-medium text-muted-foreground">
                        Entry
                      </span>
                    </th>
                    <th className="text-right p-4">
                      <span className="text-sm font-medium text-muted-foreground">
                        Exit
                      </span>
                    </th>
                    <th className="text-right p-4">
                      <button
                        onClick={() => handleSort("pnl")}
                        className="flex items-center gap-2 text-sm font-medium text-muted-foreground hover:text-foreground ml-auto"
                      >
                        P&L
                        {getSortIcon("pnl")}
                      </button>
                    </th>
                    <th className="text-right p-4">
                      <button
                        onClick={() => handleSort("pnlPercent")}
                        className="flex items-center gap-2 text-sm font-medium text-muted-foreground hover:text-foreground ml-auto"
                      >
                        P&L %{getSortIcon("pnlPercent")}
                      </button>
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {paginatedTrades.map((trade) => (
                    <tr
                      key={trade.id}
                      className="border-b border-border hover:bg-accent/50 transition-colors cursor-pointer"
                    >
                      <td className="p-4">
                        <div>
                          <p className="text-sm font-medium">
                            {new Date(trade.entryTime).toLocaleDateString(
                              "en-US",
                              {
                                month: "short",
                                day: "numeric",
                                year: "numeric",
                              },
                            )}
                          </p>
                          <p className="text-xs text-muted-foreground">
                            {new Date(trade.entryTime).toLocaleTimeString(
                              "en-US",
                              {
                                hour: "2-digit",
                                minute: "2-digit",
                              },
                            )}
                          </p>
                        </div>
                      </td>
                      <td className="p-4">
                        <Badge variant="outline">{trade.instrument}</Badge>
                      </td>
                      <td className="p-4">
                        <Badge
                          variant={
                            trade.direction === "long" ? "default" : "secondary"
                          }
                          className={cn(
                            trade.direction === "long"
                              ? "bg-green-500/10 text-green-500 hover:bg-green-500/20"
                              : "bg-red-500/10 text-red-500 hover:bg-red-500/20",
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
                      <td className="p-4 text-right">
                        <span className="text-sm">
                          {trade.entryPrice.toLocaleString("en-US", {
                            minimumFractionDigits: 2,
                          })}
                        </span>
                      </td>
                      <td className="p-4 text-right">
                        <span className="text-sm">
                          {trade.exitPrice?.toLocaleString("en-US", {
                            minimumFractionDigits: 2,
                          }) || "-"}
                        </span>
                      </td>
                      <td className="p-4 text-right">
                        <span
                          className={cn(
                            "text-sm font-medium",
                            trade.pnl >= 0 ? "text-green-500" : "text-red-500",
                          )}
                        >
                          {trade.pnl >= 0 ? "+" : ""}
                          {trade.currency
                            ? formatAmount(trade.pnl, trade.currency)
                            : trade.pnl.toLocaleString("en-US", {
                                minimumFractionDigits: 2,
                              })}
                        </span>
                      </td>
                      <td className="p-4 text-right">
                        <span
                          className={cn(
                            "text-sm font-medium",
                            trade.pnlPercent >= 0
                              ? "text-green-500"
                              : "text-red-500",
                          )}
                        >
                          {trade.pnlPercent >= 0 ? "+" : ""}
                          {trade.pnlPercent.toFixed(2)}%
                        </span>
                      </td>
                    </tr>
                  ))}

                  {paginatedTrades.length === 0 && (
                    <tr>
                      <td colSpan={7} className="p-8 text-center">
                        <div className="flex flex-col items-center gap-2">
                          <Filter className="h-8 w-8 text-muted-foreground" />
                          <p className="text-muted-foreground">
                            No trades found
                          </p>
                          {hasActiveFilters && (
                            <Button variant="link" onClick={clearFilters}>
                              Clear filters
                            </Button>
                          )}
                        </div>
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            {sortedTrades.length > 0 && (
              <div className="flex items-center justify-between p-4 border-t border-border">
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <span>
                    Showing {startIndex} to {endIndex} of {sortedTrades.length}{" "}
                    trades
                  </span>
                  <select
                    value={pageSize}
                    onChange={(e) => {
                      setPageSize(Number(e.target.value));
                      setCurrentPage(1);
                    }}
                    className="ml-2 bg-background border border-input rounded-md px-2 py-1 text-sm"
                  >
                    <option value={10}>10 per page</option>
                    <option value={20}>20 per page</option>
                    <option value={50}>50 per page</option>
                    <option value={100}>100 per page</option>
                  </select>
                </div>
                <div className="flex items-center gap-1">
                  <Button
                    variant="outline"
                    size="icon"
                    className="h-8 w-8"
                    onClick={() => setCurrentPage(1)}
                    disabled={currentPage === 1}
                  >
                    <ChevronsLeft className="h-4 w-4" />
                  </Button>
                  <Button
                    variant="outline"
                    size="icon"
                    className="h-8 w-8"
                    onClick={() =>
                      setCurrentPage((prev) => Math.max(1, prev - 1))
                    }
                    disabled={currentPage === 1}
                  >
                    <ChevronLeft className="h-4 w-4" />
                  </Button>
                  <span className="px-3 text-sm">
                    Page {currentPage} of {totalPages}
                  </span>
                  <Button
                    variant="outline"
                    size="icon"
                    className="h-8 w-8"
                    onClick={() =>
                      setCurrentPage((prev) => Math.min(totalPages, prev + 1))
                    }
                    disabled={currentPage === totalPages}
                  >
                    <ChevronRight className="h-4 w-4" />
                  </Button>
                  <Button
                    variant="outline"
                    size="icon"
                    className="h-8 w-8"
                    onClick={() => setCurrentPage(totalPages)}
                    disabled={currentPage === totalPages}
                  >
                    <ChevronsRight className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
