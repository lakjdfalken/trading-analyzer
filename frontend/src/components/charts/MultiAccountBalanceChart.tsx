"use client";

import * as React from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  Legend,
} from "recharts";
import { format } from "date-fns";
import { cn } from "@/lib/utils";
import { useCurrencyStore } from "@/store/currency";
import { Button } from "@/components/ui/button";
import { ChevronDown, Check } from "lucide-react";

// Color palette for different accounts
const ACCOUNT_COLORS = [
  "#3B82F6", // Blue
  "#10B981", // Green
  "#F59E0B", // Amber
  "#EF4444", // Red
  "#8B5CF6", // Purple
  "#EC4899", // Pink
  "#06B6D4", // Cyan
  "#84CC16", // Lime
];

export interface AccountSeries {
  accountId: number;
  accountName: string;
  currency?: string;
  data: Array<{
    date: string;
    balance: number;
  }>;
}

export interface MultiAccountBalanceChartProps {
  series: AccountSeries[];
  total?: {
    accountName: string;
    data: Array<{
      date: string;
      balance: number;
    }>;
  };
  height?: number | string;
  showTotal?: boolean;
  showLegend?: boolean;
  showGrid?: boolean;
  showTooltip?: boolean;
  animate?: boolean;
  className?: string;
}

interface ChartDataPoint {
  date: string;
  [key: string]: string | number;
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: Array<{
    name: string;
    value: number;
    color: string;
    dataKey: string;
  }>;
  label?: string;
  currency: string;
  formatAmount: (amount: number, currency: string) => string;
}

function CustomTooltip({
  active,
  payload,
  label,
  currency,
  formatAmount,
}: CustomTooltipProps) {
  if (!active || !payload || payload.length === 0) {
    return null;
  }

  return (
    <div className="bg-popover border border-border rounded-lg shadow-lg p-3 text-sm">
      <p className="text-muted-foreground text-xs mb-2 font-medium">{label}</p>
      <div className="space-y-1.5">
        {payload.map((entry, index) => (
          <div key={index} className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-2">
              <div
                className="w-3 h-3 rounded-sm"
                style={{ backgroundColor: entry.color }}
              />
              <span className="text-muted-foreground">{entry.name}:</span>
            </div>
            <span className="font-semibold">
              {formatAmount(entry.value, currency)}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

// Account selector dropdown
interface AccountSelectorProps {
  accounts: Array<{ id: number; name: string; currency?: string }>;
  selectedIds: number[];
  onSelectionChange: (ids: number[]) => void;
  showAllOption?: boolean;
  allLabel?: string;
}

function AccountSelector({
  accounts,
  selectedIds,
  onSelectionChange,
  showAllOption = true,
  allLabel = "All Accounts (Converted)",
}: AccountSelectorProps) {
  const [isOpen, setIsOpen] = React.useState(false);
  const dropdownRef = React.useRef<HTMLDivElement>(null);

  // Close dropdown when clicking outside
  React.useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const isAllSelected = selectedIds.length === 0;
  const selectedCount = isAllSelected ? accounts.length : selectedIds.length;

  const getDisplayText = () => {
    if (isAllSelected) return allLabel;
    if (selectedIds.length === 1) {
      const account = accounts.find((a) => a.id === selectedIds[0]);
      return account
        ? `${account.name}${account.currency ? ` (${account.currency})` : ""}`
        : "Select Account";
    }
    return `${selectedCount} accounts selected`;
  };

  const handleToggleAccount = (accountId: number) => {
    if (selectedIds.includes(accountId)) {
      // Remove from selection
      const newSelection = selectedIds.filter((id) => id !== accountId);
      onSelectionChange(newSelection);
    } else {
      // Add to selection
      onSelectionChange([...selectedIds, accountId]);
    }
  };

  const handleSelectAll = () => {
    onSelectionChange([]);
  };

  return (
    <div className="relative" ref={dropdownRef}>
      <Button
        variant="outline"
        size="sm"
        onClick={() => setIsOpen(!isOpen)}
        className="gap-2 min-w-[180px] justify-between"
      >
        <span className="truncate">{getDisplayText()}</span>
        <ChevronDown
          className={cn(
            "h-4 w-4 opacity-50 transition-transform flex-shrink-0",
            isOpen && "rotate-180",
          )}
        />
      </Button>

      {isOpen && (
        <div className="absolute z-50 mt-1 w-full min-w-[220px] rounded-md border border-border bg-popover shadow-md animate-in fade-in-0 zoom-in-95">
          <div className="p-1 max-h-[300px] overflow-auto">
            {showAllOption && (
              <>
                <button
                  type="button"
                  onClick={handleSelectAll}
                  className={cn(
                    "flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-sm",
                    "hover:bg-accent hover:text-accent-foreground",
                    isAllSelected && "bg-accent",
                  )}
                >
                  <div className="w-4 h-4 flex items-center justify-center">
                    {isAllSelected && (
                      <Check className="h-4 w-4 text-primary" />
                    )}
                  </div>
                  <span className="flex-1 text-left">{allLabel}</span>
                </button>
                <div className="my-1 h-px bg-border" />
              </>
            )}
            {accounts.map((account) => {
              const isSelected = selectedIds.includes(account.id);
              return (
                <button
                  key={account.id}
                  type="button"
                  onClick={() => handleToggleAccount(account.id)}
                  className={cn(
                    "flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-sm",
                    "hover:bg-accent hover:text-accent-foreground",
                    isSelected && !isAllSelected && "bg-accent",
                  )}
                >
                  <div className="w-4 h-4 flex items-center justify-center">
                    {isSelected && !isAllSelected && (
                      <Check className="h-4 w-4 text-primary" />
                    )}
                  </div>
                  <span className="flex-1 text-left">{account.name}</span>
                  {account.currency && (
                    <span className="text-xs text-muted-foreground">
                      {account.currency}
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

export function MultiAccountBalanceChart({
  series,
  total,
  height = 400,
  showTotal = true,
  showLegend = true,
  showGrid = true,
  showTooltip = true,
  animate = true,
  className,
}: MultiAccountBalanceChartProps) {
  const { formatAmount, showConverted, defaultCurrency, convert } =
    useCurrencyStore();

  // Track selected accounts (empty = all with conversion)
  const [selectedAccountIds, setSelectedAccountIds] = React.useState<number[]>(
    [],
  );

  // Determine if we have multiple currencies
  const currencies = React.useMemo(() => {
    const currencySet = new Set<string>();
    series.forEach((s) => {
      if (s.currency) currencySet.add(s.currency);
    });
    return Array.from(currencySet);
  }, [series]);

  const hasMultipleCurrencies = currencies.length > 1;

  // Determine display mode based on selection and showConverted
  const displayMode = React.useMemo(() => {
    if (selectedAccountIds.length === 0) {
      // All selected - must convert to show meaningful totals
      return "converted";
    }
    if (selectedAccountIds.length === 1) {
      // Single account - show in native currency
      return "native";
    }
    // Multiple accounts selected
    const selectedCurrencies = new Set(
      series
        .filter((s) => selectedAccountIds.includes(s.accountId))
        .map((s) => s.currency),
    );
    if (selectedCurrencies.size === 1) {
      // All selected accounts have same currency
      return "native";
    }
    // Mixed currencies - must convert
    return "converted";
  }, [selectedAccountIds, series]);

  // Get the display currency
  const displayCurrency = React.useMemo(() => {
    if (displayMode === "converted") {
      return defaultCurrency;
    }
    // Native mode - get currency from selected account(s)
    if (selectedAccountIds.length === 1) {
      const account = series.find((s) => s.accountId === selectedAccountIds[0]);
      return account?.currency || defaultCurrency;
    }
    // Multiple accounts with same currency
    const firstSelected = series.find((s) =>
      selectedAccountIds.includes(s.accountId),
    );
    return firstSelected?.currency || defaultCurrency;
  }, [displayMode, selectedAccountIds, series, defaultCurrency]);

  // Filter series based on selection
  const filteredSeries = React.useMemo(() => {
    if (selectedAccountIds.length === 0) {
      return series;
    }
    return series.filter((s) => selectedAccountIds.includes(s.accountId));
  }, [series, selectedAccountIds]);

  // Convert balance if needed
  const convertBalance = React.useCallback(
    (balance: number, fromCurrency: string | undefined): number => {
      if (displayMode === "native" || !fromCurrency) {
        return balance;
      }
      if (fromCurrency === displayCurrency) {
        return balance;
      }
      const converted = convert(balance, fromCurrency, displayCurrency);
      return converted ?? balance;
    },
    [displayMode, displayCurrency, convert],
  );

  // Merge all series data into a single dataset
  const chartData = React.useMemo(() => {
    // Collect all unique dates from all accounts
    const allDates = new Set<string>();
    filteredSeries.forEach((account) => {
      account.data.forEach((point) => {
        allDates.add(point.date);
      });
    });

    // Sort dates chronologically
    const sortedDates = Array.from(allDates).sort(
      (a, b) => new Date(a).getTime() - new Date(b).getTime(),
    );

    // Build a map of account -> date -> balance for quick lookup
    const accountDataMaps = new Map<string, Map<string, number>>();
    filteredSeries.forEach((account) => {
      const dateToBalance = new Map<string, number>();
      account.data.forEach((point) => {
        const convertedBalance = convertBalance(
          point.balance,
          account.currency,
        );
        dateToBalance.set(point.date, convertedBalance);
      });
      accountDataMaps.set(account.accountName, dateToBalance);
    });

    // Build chart data with interpolated values
    const result: ChartDataPoint[] = [];
    const lastKnownValues = new Map<string, number>();

    sortedDates.forEach((date) => {
      const point: ChartDataPoint = { date };

      filteredSeries.forEach((account) => {
        const dateToBalance = accountDataMaps.get(account.accountName);
        if (dateToBalance?.has(date)) {
          // Use actual value
          const value = dateToBalance.get(date)!;
          point[account.accountName] = value;
          lastKnownValues.set(account.accountName, value);
        } else if (lastKnownValues.has(account.accountName)) {
          // Use last known value (carry forward)
          point[account.accountName] = lastKnownValues.get(
            account.accountName,
          )!;
        }
        // If no value yet, leave undefined (line will start when data begins)
      });

      result.push(point);
    });

    // Add total data (only when showing all accounts)
    if (showTotal && total?.data && selectedAccountIds.length === 0) {
      // Recalculate total from converted values
      result.forEach((point) => {
        let totalValue = 0;
        let hasAnyValue = false;
        filteredSeries.forEach((account) => {
          const value = point[account.accountName];
          if (typeof value === "number") {
            totalValue += value;
            hasAnyValue = true;
          }
        });
        if (hasAnyValue) {
          point["Total"] = totalValue;
        }
      });
    }

    return result;
  }, [filteredSeries, total, showTotal, selectedAccountIds, convertBalance]);

  // Get all account names for the legend
  const accountNames = React.useMemo(() => {
    const names = filteredSeries.map((s) => s.accountName);
    if (showTotal && total && selectedAccountIds.length === 0) {
      names.push("Total");
    }
    return names;
  }, [filteredSeries, total, showTotal, selectedAccountIds]);

  // Calculate Y-axis domain
  const yDomain = React.useMemo(() => {
    if (chartData.length === 0) return [0, 100];

    let min = Infinity;
    let max = -Infinity;

    chartData.forEach((point) => {
      accountNames.forEach((name) => {
        const value = point[name] as number;
        if (typeof value === "number") {
          min = Math.min(min, value);
          max = Math.max(max, value);
        }
      });
    });

    if (min === Infinity) min = 0;
    if (max === -Infinity) max = 100;

    const padding = (max - min) * 0.1;
    return [Math.floor(min - padding), Math.ceil(max + padding)];
  }, [chartData, accountNames]);

  // Format date for X-axis
  const formatXAxis = (dateStr: string) => {
    try {
      const date = new Date(dateStr);
      return format(date, "MMM d");
    } catch {
      return dateStr;
    }
  };

  // Account options for selector
  const accountOptions = React.useMemo(
    () =>
      series.map((s) => ({
        id: s.accountId,
        name: s.accountName,
        currency: s.currency,
      })),
    [series],
  );

  if (chartData.length === 0) {
    return (
      <div
        className={cn(
          "flex items-center justify-center text-muted-foreground",
          className,
        )}
        style={{ height }}
      >
        No data available
      </div>
    );
  }

  return (
    <div className={cn("w-full", className)}>
      {/* Header with account selector */}
      {hasMultipleCurrencies && series.length > 1 && (
        <div className="flex items-center justify-between mb-4 px-2">
          <div className="flex items-center gap-2">
            <AccountSelector
              accounts={accountOptions}
              selectedIds={selectedAccountIds}
              onSelectionChange={setSelectedAccountIds}
              allLabel={`All Accounts (${defaultCurrency})`}
            />
            {displayMode === "converted" && (
              <span className="text-xs text-muted-foreground">
                Values converted to {displayCurrency}
              </span>
            )}
          </div>
          <div className="text-xs text-muted-foreground">{displayCurrency}</div>
        </div>
      )}

      <div style={{ height }}>
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart
            data={chartData}
            margin={{ top: 10, right: 10, left: 0, bottom: 0 }}
          >
            <defs>
              {accountNames.map((name, index) => {
                const color =
                  name === "Total"
                    ? "#6B7280"
                    : ACCOUNT_COLORS[index % ACCOUNT_COLORS.length];
                return (
                  <linearGradient
                    key={name}
                    id={`gradient-${name.replace(/\s+/g, "-")}`}
                    x1="0"
                    y1="0"
                    x2="0"
                    y2="1"
                  >
                    <stop offset="5%" stopColor={color} stopOpacity={0.3} />
                    <stop offset="95%" stopColor={color} stopOpacity={0} />
                  </linearGradient>
                );
              })}
            </defs>

            {showGrid && (
              <CartesianGrid
                strokeDasharray="3 3"
                stroke="hsl(var(--border))"
                vertical={false}
              />
            )}

            <XAxis
              dataKey="date"
              axisLine={false}
              tickLine={false}
              tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 12 }}
              tickMargin={8}
              tickFormatter={formatXAxis}
              minTickGap={50}
            />

            <YAxis
              domain={yDomain}
              axisLine={false}
              tickLine={false}
              tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 12 }}
              tickMargin={8}
              tickFormatter={(value) => formatAmount(value, displayCurrency)}
              width={80}
            />

            {showTooltip && (
              <Tooltip
                content={
                  <CustomTooltip
                    currency={displayCurrency}
                    formatAmount={formatAmount}
                  />
                }
                cursor={{
                  stroke: "hsl(var(--muted-foreground))",
                  strokeWidth: 1,
                  strokeDasharray: "4 4",
                }}
              />
            )}

            {showLegend && (
              <Legend
                verticalAlign="top"
                height={36}
                formatter={(value) => (
                  <span className="text-sm text-muted-foreground">{value}</span>
                )}
              />
            )}

            {/* Render total first (behind) if shown */}
            {showTotal && total && selectedAccountIds.length === 0 && (
              <Area
                type="monotone"
                dataKey="Total"
                name="Total"
                stroke="#6B7280"
                strokeWidth={2}
                strokeDasharray="5 5"
                fill={`url(#gradient-Total)`}
                isAnimationActive={animate}
                animationDuration={1000}
                animationEasing="ease-out"
              />
            )}

            {/* Render each account series */}
            {filteredSeries.map((account, index) => {
              const color = ACCOUNT_COLORS[index % ACCOUNT_COLORS.length];
              return (
                <Area
                  key={account.accountId}
                  type="monotone"
                  dataKey={account.accountName}
                  name={account.accountName}
                  stroke={color}
                  strokeWidth={2}
                  fill={`url(#gradient-${account.accountName.replace(/\s+/g, "-")})`}
                  isAnimationActive={animate}
                  animationDuration={1000}
                  animationEasing="ease-out"
                />
              );
            })}
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

export default MultiAccountBalanceChart;
