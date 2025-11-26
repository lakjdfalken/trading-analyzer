"use client";

import React from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  Cell,
} from "recharts";
import { format } from "date-fns";
import { useCurrencyStore } from "@/store/currency";

interface DailyPnLDataPoint {
  date: string;
  pnl: number;
  cumulativePnl: number;
  trades: number;
}

interface DailyPnLChartProps {
  data: DailyPnLDataPoint[];
  height?: number;
  showCumulative?: boolean;
  currency?: string;
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: Array<{
    value: number;
    dataKey: string;
    payload: DailyPnLDataPoint;
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
  if (!active || !payload || payload.length === 0) return null;

  const dataPoint = payload[0].payload;
  const isProfit = dataPoint.pnl >= 0;

  let formattedDate = label || "";
  try {
    formattedDate = format(new Date(label || ""), "MMM d, yyyy");
  } catch {
    // Keep original if parsing fails
  }

  return (
    <div
      className="rounded-lg border bg-popover p-3 shadow-md"
      style={{ backgroundColor: "hsl(var(--popover))" }}
    >
      <p className="font-medium mb-2">{formattedDate}</p>
      <div className="space-y-1 text-sm">
        <div className="flex justify-between gap-4">
          <span className="text-muted-foreground">P&L:</span>
          <span className={isProfit ? "text-green-500" : "text-red-500"}>
            {isProfit ? "+" : ""}
            {formatAmount(dataPoint.pnl, currency)}
          </span>
        </div>
        <div className="flex justify-between gap-4">
          <span className="text-muted-foreground">Cumulative:</span>
          <span
            className={
              dataPoint.cumulativePnl >= 0 ? "text-green-500" : "text-red-500"
            }
          >
            {dataPoint.cumulativePnl >= 0 ? "+" : ""}
            {formatAmount(dataPoint.cumulativePnl, currency)}
          </span>
        </div>
        <div className="flex justify-between gap-4">
          <span className="text-muted-foreground">Trades:</span>
          <span>{dataPoint.trades}</span>
        </div>
      </div>
    </div>
  );
}

export function DailyPnLChart({
  data,
  height = 300,
  showCumulative = false,
  currency = "USD",
}: DailyPnLChartProps) {
  const { formatAmount } = useCurrencyStore();

  const chartData = React.useMemo(() => {
    if (!data || data.length === 0) return [];

    return data.map((point) => ({
      ...point,
      displayDate: point.date,
    }));
  }, [data]);

  const yDomain = React.useMemo(() => {
    if (chartData.length === 0) return [-100, 100];

    let min = 0;
    let max = 0;

    chartData.forEach((point) => {
      const value = showCumulative ? point.cumulativePnl : point.pnl;
      min = Math.min(min, value);
      max = Math.max(max, value);
    });

    const padding = Math.max(Math.abs(max - min) * 0.1, 10);
    return [Math.floor(min - padding), Math.ceil(max + padding)];
  }, [chartData, showCumulative]);

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

  if (!data || data.length === 0) {
    return (
      <div
        className="flex items-center justify-center text-muted-foreground"
        style={{ height }}
      >
        <p>No daily P&L data available</p>
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart
        data={chartData}
        margin={{ top: 20, right: 30, left: 20, bottom: 20 }}
      >
        <CartesianGrid
          strokeDasharray="3 3"
          vertical={false}
          stroke="hsl(var(--border))"
        />
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
        <Tooltip
          content={
            <CustomTooltip currency={currency} formatAmount={formatAmount} />
          }
          cursor={{ fill: "hsl(var(--muted))", opacity: 0.3 }}
        />
        <ReferenceLine y={0} stroke="hsl(var(--border))" strokeWidth={1} />
        <Bar
          dataKey={showCumulative ? "cumulativePnl" : "pnl"}
          radius={[4, 4, 0, 0]}
          maxBarSize={50}
        >
          {chartData.map((entry, index) => {
            const value = showCumulative ? entry.cumulativePnl : entry.pnl;
            return (
              <Cell
                key={`cell-${index}`}
                fill={value >= 0 ? "#22c55e" : "#ef4444"}
              />
            );
          })}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

export default DailyPnLChart;
