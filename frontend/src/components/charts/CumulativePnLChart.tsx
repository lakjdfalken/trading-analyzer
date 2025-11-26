"use client";

import React from "react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";
import { format } from "date-fns";
import { useCurrencyStore } from "@/store/currency";

interface DailyPnLDataPoint {
  date: string;
  pnl: number;
  cumulativePnl: number;
  trades: number;
}

interface CumulativePnLChartProps {
  data: DailyPnLDataPoint[];
  height?: number;
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
  const isProfit = dataPoint.cumulativePnl >= 0;

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
          <span className="text-muted-foreground">Cumulative P&L:</span>
          <span className={isProfit ? "text-green-500" : "text-red-500"}>
            {isProfit ? "+" : ""}
            {formatAmount(dataPoint.cumulativePnl, currency)}
          </span>
        </div>
        <div className="flex justify-between gap-4">
          <span className="text-muted-foreground">Day P&L:</span>
          <span
            className={dataPoint.pnl >= 0 ? "text-green-500" : "text-red-500"}
          >
            {dataPoint.pnl >= 0 ? "+" : ""}
            {formatAmount(dataPoint.pnl, currency)}
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

export function CumulativePnLChart({
  data,
  height = 300,
  currency = "USD",
}: CumulativePnLChartProps) {
  const { formatAmount } = useCurrencyStore();

  const chartData = React.useMemo(() => {
    if (!data || data.length === 0) return [];
    return data;
  }, [data]);

  const yDomain = React.useMemo(() => {
    if (chartData.length === 0) return [-100, 100];

    let min = 0;
    let max = 0;

    chartData.forEach((point) => {
      min = Math.min(min, point.cumulativePnl);
      max = Math.max(max, point.cumulativePnl);
    });

    const padding = Math.max(Math.abs(max - min) * 0.1, 10);
    return [Math.floor(min - padding), Math.ceil(max + padding)];
  }, [chartData]);

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
        <p>No P&L data available</p>
      </div>
    );
  }

  // Calculate summary stats
  const finalCumulative = chartData[chartData.length - 1]?.cumulativePnl || 0;
  const maxCumulative =
    chartData.length > 0
      ? Math.max(...chartData.map((d) => d.cumulativePnl))
      : 0;
  const minCumulative =
    chartData.length > 0
      ? Math.min(...chartData.map((d) => d.cumulativePnl))
      : 0;

  // Determine if overall profitable
  const isPositive = finalCumulative >= 0;

  return (
    <div className="space-y-2">
      <div className="flex gap-4 text-sm px-4">
        <div>
          <span className="text-muted-foreground">Total P&L: </span>
          <span
            className={`font-medium ${isPositive ? "text-green-500" : "text-red-500"}`}
          >
            {isPositive ? "+" : ""}
            {formatAmount(finalCumulative, currency)}
          </span>
        </div>
        <div>
          <span className="text-muted-foreground">Peak: </span>
          <span className="text-green-500 font-medium">
            +{formatAmount(maxCumulative, currency)}
          </span>
        </div>
        {minCumulative < 0 && (
          <div>
            <span className="text-muted-foreground">Trough: </span>
            <span className="text-red-500 font-medium">
              {formatAmount(minCumulative, currency)}
            </span>
          </div>
        )}
      </div>
      <ResponsiveContainer width="100%" height={height - 30}>
        <AreaChart
          data={chartData}
          margin={{ top: 10, right: 30, left: 20, bottom: 20 }}
        >
          <defs>
            <linearGradient
              id="cumulativeGradientPos"
              x1="0"
              y1="0"
              x2="0"
              y2="1"
            >
              <stop offset="5%" stopColor="#22c55e" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#22c55e" stopOpacity={0.05} />
            </linearGradient>
            <linearGradient
              id="cumulativeGradientNeg"
              x1="0"
              y1="1"
              x2="0"
              y2="0"
            >
              <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#ef4444" stopOpacity={0.05} />
            </linearGradient>
          </defs>
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
          />
          <ReferenceLine y={0} stroke="hsl(var(--border))" strokeWidth={1} />
          <Area
            type="monotone"
            dataKey="cumulativePnl"
            stroke={isPositive ? "#22c55e" : "#ef4444"}
            strokeWidth={2}
            fill={
              isPositive
                ? "url(#cumulativeGradientPos)"
                : "url(#cumulativeGradientNeg)"
            }
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

export default CumulativePnLChart;
