"use client";

import React from "react";
import { useSettingsStore } from "@/store/settings";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  Legend,
  ReferenceLine,
} from "recharts";
import { format } from "date-fns";
import { cn } from "@/lib/utils";
import { useCurrencyStore } from "@/store/currency";
import { Info } from "lucide-react";

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
    date: string;
    pnl: number;
    trades: number;
    cumulativePnl: number;
  }>;
}

export interface MultiAccountCumulativePnLChartProps {
  series: AccountPnLSeries[];
  total?: {
    accountName: string;
    currency?: string;
    data: Array<{
      date: string;
      pnl: number;
      trades: number;
      cumulativePnl: number;
    }>;
  };
  height?: number | string;
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
  seriesCurrencies: Map<string, string>;
  formatAmount: (amount: number, currency: string) => string;
}

function CustomTooltip({
  active,
  payload,
  label,
  seriesCurrencies,
  formatAmount,
}: CustomTooltipProps) {
  if (!active || !payload || payload.length === 0) return null;

  let formattedDate = label || "";
  try {
    formattedDate = format(new Date(label || ""), "MMM d, yyyy");
  } catch {
    // Keep original if parsing fails
  }

  return (
    <div
      className="rounded-lg border bg-popover p-3 shadow-md text-sm"
      style={{ backgroundColor: "hsl(var(--popover))" }}
    >
      <p className="font-medium mb-2">{formattedDate}</p>
      <div className="space-y-1">
        {payload.map((entry, index) => {
          const isPositive = entry.value >= 0;
          const currency = seriesCurrencies.get(entry.name);
          // Skip entries without currency - per .rules, currency is required
          if (!currency) return null;
          return (
            <div
              key={index}
              className="flex items-center justify-between gap-4"
            >
              <div className="flex items-center gap-2">
                <div
                  className="w-3 h-3 rounded-full"
                  style={{ backgroundColor: entry.color }}
                />
                <span className="text-muted-foreground">{entry.name}:</span>
              </div>
              <span className={isPositive ? "text-green-500" : "text-red-500"}>
                {isPositive ? "+" : ""}
                {formatAmount(entry.value, currency)}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export function MultiAccountCumulativePnLChart({
  series,
  height = 300,
  showLegend = true,
  showGrid = true,
  showTooltip = true,
  animate = true,
  className,
}: MultiAccountCumulativePnLChartProps) {
  const { formatAmount } = useCurrencyStore();
  const { showConverted, defaultCurrency } = useSettingsStore();

  // Build a map of account name to currency for tooltip
  const seriesCurrencies = React.useMemo(() => {
    const map = new Map<string, string>();
    series.forEach((s) => {
      // Only add if currency is defined - per .rules, no fallbacks
      if (s.currency) {
        map.set(s.accountName, s.currency);
      }
    });
    if (showConverted && defaultCurrency) {
      map.set("Total (Converted)", defaultCurrency);
    }
    return map;
  }, [series, showConverted, defaultCurrency]);

  // Check if accounts have different currencies
  const currencies = React.useMemo(() => {
    const currencySet = new Set<string>();
    series.forEach((s) => {
      if (s.currency) currencySet.add(s.currency);
    });
    return Array.from(currencySet);
  }, [series]);

  const hasMultipleCurrencies = currencies.length > 1;

  // Backend already converts values to target currency
  // No frontend conversion needed - just pass through the values
  const convertValue = React.useCallback(
    (value: number, _fromCurrency?: string): number => {
      return value;
    },
    [],
  );

  // Transform data for recharts - show all accounts
  const chartData = React.useMemo(() => {
    // Collect all unique dates
    const allDates = new Set<string>();
    series.forEach((s) => {
      s.data.forEach((d) => allDates.add(d.date));
    });

    const sortedDates = Array.from(allDates).sort(
      (a, b) => new Date(a).getTime() - new Date(b).getTime(),
    );

    // Build data points
    const accountDataMaps = new Map<number, Map<string, number>>();
    series.forEach((s) => {
      const dateToValue = new Map<string, number>();
      s.data.forEach((d) => {
        dateToValue.set(d.date, d.cumulativePnl);
      });
      accountDataMaps.set(s.accountId, dateToValue);
    });

    const result: ChartDataPoint[] = [];
    const lastKnownValues = new Map<number, number>();
    const lastKnownRawValues = new Map<
      number,
      { value: number; currency?: string }
    >();

    for (const date of sortedDates) {
      const point: ChartDataPoint = { date };

      series.forEach((s) => {
        const dateToValue = accountDataMaps.get(s.accountId);
        const value = dateToValue?.get(date);

        if (value !== undefined) {
          point[s.accountName] = value;
          lastKnownValues.set(s.accountId, value);
          lastKnownRawValues.set(s.accountId, { value, currency: s.currency });
        } else {
          // Use last known value for continuity
          const lastValue = lastKnownValues.get(s.accountId);
          if (lastValue !== undefined) {
            point[s.accountName] = lastValue;
          }
        }
      });

      // Calculate converted total if showConverted is enabled
      if (showConverted && defaultCurrency) {
        let total = 0;
        series.forEach((s) => {
          const rawData = lastKnownRawValues.get(s.accountId);
          if (rawData) {
            total += convertValue(rawData.value, rawData.currency);
          }
        });
        point["Total (Converted)"] = total;
      }

      result.push(point);
    }

    return result;
  }, [series, showConverted, defaultCurrency, convertValue]);

  // Get account names for the chart
  const accountNames = React.useMemo(() => {
    const names = series.map((s) => s.accountName);
    if (showConverted && defaultCurrency) {
      names.push("Total (Converted)");
    }
    return names;
  }, [series, showConverted, defaultCurrency]);

  // Calculate Y-axis domain
  const yDomain = React.useMemo(() => {
    if (chartData.length === 0) return [-100, 100];

    let min = 0;
    let max = 0;

    chartData.forEach((point) => {
      accountNames.forEach((name) => {
        const value = point[name];
        if (typeof value === "number") {
          min = Math.min(min, value);
          max = Math.max(max, value);
        }
      });
    });

    const range = max - min;
    const padding = Math.max(range * 0.1, 10);
    return [Math.floor(min - padding), Math.ceil(max + padding)];
  }, [chartData, accountNames]);

  const formatXAxis = (dateStr: string) => {
    try {
      const date = new Date(dateStr);
      return format(date, "MMM d");
    } catch {
      return dateStr;
    }
  };

  const formatYAxis = (value: number) => {
    if (Math.abs(value) >= 1000000) {
      return `${(value / 1000000).toFixed(1)}M`;
    }
    if (Math.abs(value) >= 1000) {
      return `${(value / 1000).toFixed(1)}K`;
    }
    return value.toFixed(0);
  };

  if (!series || series.length === 0) {
    return (
      <div
        className={cn(
          "flex items-center justify-center text-muted-foreground",
          className,
        )}
        style={{ height }}
      >
        <p>No P&L data available</p>
      </div>
    );
  }

  return (
    <div className={cn("space-y-2", className)}>
      {/* Info banner */}
      <div className="flex items-center gap-2 px-4 text-xs text-muted-foreground">
        <Info className="h-3.5 w-3.5" />
        <span>
          Showing cumulative P&L for each account separately
          {hasMultipleCurrencies &&
            !showConverted &&
            " (accounts have different currencies)"}
          {showConverted &&
            defaultCurrency &&
            ` with total converted to ${defaultCurrency}`}
        </span>
      </div>

      {/* Chart */}
      <ResponsiveContainer
        width="100%"
        height={typeof height === "number" ? height - 30 : height}
      >
        <AreaChart
          data={chartData}
          margin={{ top: 10, right: 30, left: 20, bottom: 20 }}
        >
          <defs>
            {accountNames.map((name, index) => {
              const isTotal = name === "Total (Converted)";
              const color = isTotal
                ? "#22c55e"
                : ACCOUNT_COLORS[index % ACCOUNT_COLORS.length];
              return (
                <linearGradient
                  key={name}
                  id={`gradient-cumulative-${name.replace(/\s+/g, "-")}`}
                  x1="0"
                  y1="0"
                  x2="0"
                  y2="1"
                >
                  <stop
                    offset="5%"
                    stopColor={color}
                    stopOpacity={isTotal ? 0.4 : 0.3}
                  />
                  <stop offset="95%" stopColor={color} stopOpacity={0.05} />
                </linearGradient>
              );
            })}
          </defs>

          {showGrid && (
            <CartesianGrid
              strokeDasharray="3 3"
              vertical={false}
              stroke="hsl(var(--border))"
            />
          )}

          <XAxis
            dataKey="date"
            tickFormatter={formatXAxis}
            tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 12 }}
            tickLine={false}
            axisLine={{ stroke: "hsl(var(--border))" }}
            interval="preserveStartEnd"
            minTickGap={30}
          />

          <YAxis
            tickFormatter={formatYAxis}
            tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 12 }}
            tickLine={false}
            axisLine={false}
            domain={yDomain}
          />

          <ReferenceLine y={0} stroke="hsl(var(--border))" strokeWidth={1} />

          {showTooltip && (
            <Tooltip
              content={
                <CustomTooltip
                  seriesCurrencies={seriesCurrencies}
                  formatAmount={formatAmount}
                />
              }
            />
          )}

          {showLegend && accountNames.length > 1 && (
            <Legend
              verticalAlign="bottom"
              height={36}
              iconType="circle"
              iconSize={8}
            />
          )}

          {accountNames.map((name, index) => {
            const isTotal = name === "Total (Converted)";
            const color = isTotal
              ? "#22c55e"
              : ACCOUNT_COLORS[index % ACCOUNT_COLORS.length];

            return (
              <Area
                key={name}
                type="monotone"
                dataKey={name}
                name={name}
                stroke={color}
                strokeWidth={isTotal ? 3 : 2}
                fill={`url(#gradient-cumulative-${name.replace(/\s+/g, "-")})`}
                isAnimationActive={animate}
                connectNulls
                strokeDasharray={isTotal ? "5 5" : undefined}
              />
            );
          })}
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

export default MultiAccountCumulativePnLChart;
