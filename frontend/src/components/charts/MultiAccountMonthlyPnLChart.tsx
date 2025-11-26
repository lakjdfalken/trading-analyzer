"use client";

import * as React from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  ReferenceLine,
} from "recharts";
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

export interface AccountPnLSeries {
  accountId: number;
  accountName: string;
  currency?: string;
  data: Array<{
    month: string;
    month_key?: string;
    pnl: number;
    trades?: number;
    winRate?: number;
  }>;
}

export interface MultiAccountMonthlyPnLChartProps {
  series: AccountPnLSeries[];
  total?: {
    accountName: string;
    data: Array<{
      month: string;
      month_key?: string;
      pnl: number;
      trades?: number;
      winRate?: number;
    }>;
  };
  height?: number | string;
  showTotal?: boolean;
  showLegend?: boolean;
  showGrid?: boolean;
  showTooltip?: boolean;
  animate?: boolean;
  stacked?: boolean;
  className?: string;
}

interface ChartDataPoint {
  month: string;
  [key: string]: string | number;
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: Array<{
    name: string;
    value: number;
    color: string;
    dataKey: string;
    payload: ChartDataPoint;
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
    <div className="bg-popover border border-border rounded-lg shadow-lg p-3 min-w-[180px]">
      <p className="text-sm font-medium text-foreground mb-2">{label}</p>
      <div className="space-y-1.5">
        {payload.map((entry, index) => {
          const isProfit = entry.value >= 0;
          return (
            <div
              key={index}
              className="flex items-center justify-between gap-4"
            >
              <div className="flex items-center gap-2">
                <div
                  className="w-3 h-3 rounded-sm"
                  style={{ backgroundColor: entry.color }}
                />
                <span className="text-xs text-muted-foreground">
                  {entry.name}
                </span>
              </div>
              <span
                className={cn(
                  "text-sm font-semibold",
                  isProfit ? "text-green-500" : "text-red-500",
                )}
              >
                {isProfit ? "+" : ""}
                {formatAmount(entry.value, currency)}
              </span>
            </div>
          );
        })}
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
      const newSelection = selectedIds.filter((id) => id !== accountId);
      onSelectionChange(newSelection);
    } else {
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

export function MultiAccountMonthlyPnLChart({
  series,
  total,
  height = 400,
  showTotal = false,
  showLegend = true,
  showGrid = true,
  showTooltip = true,
  animate = true,
  stacked = true,
  className,
}: MultiAccountMonthlyPnLChartProps) {
  const { formatAmount, defaultCurrency, convert } = useCurrencyStore();

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

  // Determine display mode based on selection
  const displayMode = React.useMemo(() => {
    if (selectedAccountIds.length === 0) {
      return "converted";
    }
    if (selectedAccountIds.length === 1) {
      return "native";
    }
    const selectedCurrencies = new Set(
      series
        .filter((s) => selectedAccountIds.includes(s.accountId))
        .map((s) => s.currency),
    );
    if (selectedCurrencies.size === 1) {
      return "native";
    }
    return "converted";
  }, [selectedAccountIds, series]);

  // Get the display currency
  const displayCurrency = React.useMemo(() => {
    if (displayMode === "converted") {
      return defaultCurrency;
    }
    if (selectedAccountIds.length === 1) {
      const account = series.find((s) => s.accountId === selectedAccountIds[0]);
      return account?.currency || defaultCurrency;
    }
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

  // Convert PnL if needed
  const convertPnL = React.useCallback(
    (pnl: number, fromCurrency: string | undefined): number => {
      if (displayMode === "native" || !fromCurrency) {
        return pnl;
      }
      if (fromCurrency === displayCurrency) {
        return pnl;
      }
      const converted = convert(pnl, fromCurrency, displayCurrency);
      return converted ?? pnl;
    },
    [displayMode, displayCurrency, convert],
  );

  // Merge all series data into a single dataset
  const chartData = React.useMemo(() => {
    const monthMap = new Map<string, ChartDataPoint>();

    // Get all unique months from all series
    const allMonths = new Set<string>();
    filteredSeries.forEach((account) => {
      account.data.forEach((point) => {
        allMonths.add(point.month_key || point.month);
      });
    });
    if (total?.data && selectedAccountIds.length === 0) {
      total.data.forEach((point) => {
        allMonths.add(point.month_key || point.month);
      });
    }

    // Initialize all months with zero values
    Array.from(allMonths)
      .sort()
      .forEach((monthKey) => {
        monthMap.set(monthKey, { month: monthKey });
      });

    // Add account data - first initialize all accounts to 0 for all months
    const allMonthKeys = Array.from(allMonths).sort();
    filteredSeries.forEach((account) => {
      // Initialize all months to 0 for this account
      allMonthKeys.forEach((monthKey) => {
        const existing = monthMap.get(monthKey);
        if (existing && existing[account.accountName] === undefined) {
          existing[account.accountName] = 0;
        }
      });
      // Then fill in actual data
      account.data.forEach((point) => {
        const key = point.month_key || point.month;
        const existing = monthMap.get(key);
        if (existing) {
          const convertedPnL = convertPnL(point.pnl, account.currency);
          existing[account.accountName] = convertedPnL;
          if (point.month && point.month.length <= 3) {
            existing.month = point.month;
          }
        }
      });
    });

    // Add total data if showing all accounts
    if (showTotal && total?.data && selectedAccountIds.length === 0) {
      // Recalculate total from converted values
      const months = Array.from(monthMap.keys());
      months.forEach((monthKey) => {
        const point = monthMap.get(monthKey)!;
        let totalValue = 0;
        filteredSeries.forEach((account) => {
          const value = point[account.accountName];
          if (typeof value === "number") {
            totalValue += value;
          }
        });
        point["Total"] = totalValue;
      });
    }

    return Array.from(monthMap.values()).sort((a, b) => {
      const aKey = a.month;
      const bKey = b.month;
      return aKey.localeCompare(bKey);
    });
  }, [filteredSeries, total, showTotal, selectedAccountIds, convertPnL]);

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
    if (chartData.length === 0) return [-100, 100];

    let min = 0;
    let max = 0;

    chartData.forEach((point) => {
      if (stacked) {
        let posSum = 0;
        let negSum = 0;
        filteredSeries.forEach((account) => {
          const value = point[account.accountName] as number;
          if (typeof value === "number") {
            if (value >= 0) posSum += value;
            else negSum += value;
          }
        });
        max = Math.max(max, posSum);
        min = Math.min(min, negSum);
      } else {
        accountNames.forEach((name) => {
          const value = point[name] as number;
          if (typeof value === "number") {
            max = Math.max(max, value);
            min = Math.min(min, value);
          }
        });
      }
    });

    const padding = Math.max(Math.abs(max), Math.abs(min)) * 0.1;
    return [Math.floor(min - padding), Math.ceil(max + padding)];
  }, [chartData, accountNames, filteredSeries, stacked]);

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
          <BarChart
            data={chartData}
            margin={{ top: 10, right: 10, left: 10, bottom: 0 }}
          >
            {showGrid && (
              <CartesianGrid
                strokeDasharray="3 3"
                stroke="hsl(var(--border))"
                vertical={false}
              />
            )}

            <XAxis
              dataKey="month"
              axisLine={false}
              tickLine={false}
              tick={{ fontSize: 12, fill: "hsl(var(--muted-foreground))" }}
              dy={10}
            />

            <YAxis
              domain={yDomain}
              axisLine={false}
              tickLine={false}
              tick={{ fontSize: 12, fill: "hsl(var(--muted-foreground))" }}
              tickFormatter={(value) => {
                if (Math.abs(value) >= 1000) {
                  return `${(value / 1000).toFixed(0)}k`;
                }
                return `${value}`;
              }}
              width={60}
            />

            {showTooltip && (
              <Tooltip
                content={
                  <CustomTooltip
                    currency={displayCurrency}
                    formatAmount={formatAmount}
                  />
                }
                cursor={{ fill: "hsl(var(--accent))", opacity: 0.3 }}
              />
            )}

            <ReferenceLine y={0} stroke="hsl(var(--border))" strokeWidth={1} />

            {showLegend && (
              <Legend
                verticalAlign="top"
                height={36}
                formatter={(value) => (
                  <span className="text-sm text-muted-foreground">{value}</span>
                )}
              />
            )}

            {/* Render each account bar */}
            {filteredSeries.map((account, index) => {
              const color = ACCOUNT_COLORS[index % ACCOUNT_COLORS.length];
              return (
                <Bar
                  key={account.accountId}
                  dataKey={account.accountName}
                  name={account.accountName}
                  fill={color}
                  fillOpacity={0.9}
                  radius={stacked ? [0, 0, 0, 0] : [4, 4, 0, 0]}
                  stackId={stacked ? "stack" : undefined}
                  isAnimationActive={animate}
                  animationDuration={500}
                  animationEasing="ease-out"
                />
              );
            })}

            {/* Render total bar if showing and not stacked */}
            {showTotal &&
              total &&
              !stacked &&
              selectedAccountIds.length === 0 && (
                <Bar
                  dataKey="Total"
                  name="Total"
                  fill="#6B7280"
                  fillOpacity={0.7}
                  radius={[4, 4, 0, 0]}
                  isAnimationActive={animate}
                  animationDuration={500}
                  animationEasing="ease-out"
                />
              )}
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

export default MultiAccountMonthlyPnLChart;
