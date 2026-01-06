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
  Cell,
  ReferenceLine,
} from "recharts";
import { cn, formatCurrency } from "@/lib/utils";

export interface MonthlyPnLData {
  month: string;
  month_key?: string;
  pnl: number;
  trades?: number;
  winRate?: number;
}

export interface MonthlyPnLChartProps {
  data: MonthlyPnLData[];
  height?: number;
  showGrid?: boolean;
  showTooltip?: boolean;
  animate?: boolean;
  className?: string;
  profitColor?: string;
  lossColor?: string;
  currency: string;
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: Array<{
    payload: MonthlyPnLData;
    value: number;
  }>;
  label?: string;
  currency: string;
}

interface YearlyTotal {
  year: string;
  pnl: number;
  trades: number;
}

function CustomTooltip({
  active,
  payload,
  label,
  currency,
}: CustomTooltipProps) {
  if (!active || !payload || !payload.length) {
    return null;
  }

  const data = payload[0].payload;
  const isProfit = data.pnl >= 0;

  return (
    <div className="bg-popover border border-border rounded-lg shadow-lg p-3 min-w-[160px]">
      <p className="text-sm font-medium text-foreground mb-2">{label}</p>
      <div className="space-y-1">
        <div className="flex items-center justify-between gap-4">
          <span className="text-xs text-muted-foreground">P&L</span>
          <span
            className={cn(
              "text-sm font-semibold",
              isProfit ? "text-green-500" : "text-red-500",
            )}
          >
            {isProfit ? "+" : ""}
            {formatCurrency(data.pnl, currency)}
          </span>
        </div>
        {data.trades !== undefined && (
          <div className="flex items-center justify-between gap-4">
            <span className="text-xs text-muted-foreground">Trades</span>
            <span className="text-sm text-foreground">{data.trades}</span>
          </div>
        )}
        {data.winRate !== undefined && (
          <div className="flex items-center justify-between gap-4">
            <span className="text-xs text-muted-foreground">Win Rate</span>
            <span className="text-sm text-foreground">
              {data.winRate.toFixed(1)}%
            </span>
          </div>
        )}
      </div>
    </div>
  );
}

export function MonthlyPnLChart({
  data,
  height = 300,
  showGrid = true,
  showTooltip = true,
  animate = true,
  className,
  profitColor = "#10B981",
  lossColor = "#EF4444",
  currency,
}: MonthlyPnLChartProps) {
  // Calculate yearly totals
  const yearlyTotals = React.useMemo(() => {
    const totals: Record<string, YearlyTotal> = {};

    data.forEach((item) => {
      // Extract year from month_key (YYYY-MM) or month (e.g., "Jan 2024")
      let year: string;
      if (item.month_key) {
        year = item.month_key.substring(0, 4);
      } else {
        // Try to extract year from month string like "Jan 2024"
        const match = item.month.match(/\d{4}/);
        year = match ? match[0] : "Unknown";
      }

      if (!totals[year]) {
        totals[year] = { year, pnl: 0, trades: 0 };
      }
      totals[year].pnl += item.pnl;
      totals[year].trades += item.trades || 0;
    });

    return Object.values(totals).sort((a, b) => a.year.localeCompare(b.year));
  }, [data]);

  // Calculate grand total
  const grandTotal = React.useMemo(() => {
    return data.reduce(
      (acc, item) => ({
        pnl: acc.pnl + item.pnl,
        trades: acc.trades + (item.trades || 0),
      }),
      { pnl: 0, trades: 0 },
    );
  }, [data]);

  // Calculate positive and negative month totals
  const posNegTotals = React.useMemo(() => {
    const positive = { pnl: 0, count: 0 };
    const negative = { pnl: 0, count: 0 };

    data.forEach((item) => {
      if (item.pnl >= 0) {
        positive.pnl += item.pnl;
        positive.count += 1;
      } else {
        negative.pnl += item.pnl;
        negative.count += 1;
      }
    });

    return { positive, negative };
  }, [data]);

  if (!data || data.length === 0) {
    return (
      <div
        className={cn(
          "flex items-center justify-center text-muted-foreground",
          className,
        )}
        style={{ height }}
      >
        <p className="text-sm">No monthly data available</p>
      </div>
    );
  }

  // Calculate max absolute value for symmetric Y axis
  const maxAbsValue = Math.max(...data.map((d) => Math.abs(d.pnl)));
  const yDomain = [-maxAbsValue * 1.1, maxAbsValue * 1.1];

  return (
    <div className={cn("w-full", className)}>
      {/* Totals Summary */}
      <div className="mb-4 px-2">
        <div className="flex flex-wrap gap-4 text-sm">
          {/* Yearly Totals */}
          {yearlyTotals.map((yearly) => {
            const isProfit = yearly.pnl >= 0;
            return (
              <div
                key={yearly.year}
                className="flex items-center gap-2 px-3 py-1.5 rounded-md bg-muted/50"
              >
                <span className="text-muted-foreground font-medium">
                  {yearly.year}:
                </span>
                <span
                  className={cn(
                    "font-semibold",
                    isProfit ? "text-green-500" : "text-red-500",
                  )}
                >
                  {isProfit ? "+" : ""}
                  {formatCurrency(yearly.pnl, currency)}
                </span>
                {yearly.trades > 0 && (
                  <span className="text-xs text-muted-foreground">
                    ({yearly.trades} trades)
                  </span>
                )}
              </div>
            );
          })}

          {/* Grand Total (if more than one year) */}
          {yearlyTotals.length > 1 && (
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-md bg-primary/10 border border-primary/20">
              <span className="text-muted-foreground font-medium">Total:</span>
              <span
                className={cn(
                  "font-semibold",
                  grandTotal.pnl >= 0 ? "text-green-500" : "text-red-500",
                )}
              >
                {grandTotal.pnl >= 0 ? "+" : ""}
                {formatCurrency(grandTotal.pnl, currency)}
              </span>
              {grandTotal.trades > 0 && (
                <span className="text-xs text-muted-foreground">
                  ({grandTotal.trades} trades)
                </span>
              )}
            </div>
          )}

          {/* Positive Months Total */}
          {posNegTotals.positive.count > 0 && (
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-md bg-green-500/10 border border-green-500/20">
              <span className="text-muted-foreground font-medium">
                Winning:
              </span>
              <span className="font-semibold text-green-500">
                +{formatCurrency(posNegTotals.positive.pnl, currency)}
              </span>
              <span className="text-xs text-muted-foreground">
                ({posNegTotals.positive.count} months)
              </span>
            </div>
          )}

          {/* Negative Months Total */}
          {posNegTotals.negative.count > 0 && (
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-md bg-red-500/10 border border-red-500/20">
              <span className="text-muted-foreground font-medium">Losing:</span>
              <span className="font-semibold text-red-500">
                {formatCurrency(posNegTotals.negative.pnl, currency)}
              </span>
              <span className="text-xs text-muted-foreground">
                ({posNegTotals.negative.count} months)
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Chart */}
      <div style={{ height }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={data}
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
                return `${Math.round(value)}`;
              }}
              ticks={[yDomain[0], 0, yDomain[1]]}
              width={60}
            />
            {showTooltip && (
              <Tooltip
                content={<CustomTooltip currency={currency} />}
                cursor={{ fill: "hsl(var(--accent))", opacity: 0.3 }}
              />
            )}
            <ReferenceLine
              y={0}
              stroke="hsl(var(--muted-foreground))"
              strokeWidth={1}
            />
            <Bar
              dataKey="pnl"
              radius={[4, 4, 0, 0]}
              isAnimationActive={animate}
              animationDuration={500}
              animationEasing="ease-out"
            >
              {data.map((entry, index) => (
                <Cell
                  key={`cell-${index}`}
                  fill={entry.pnl >= 0 ? profitColor : lossColor}
                  fillOpacity={0.9}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

export default MonthlyPnLChart;
