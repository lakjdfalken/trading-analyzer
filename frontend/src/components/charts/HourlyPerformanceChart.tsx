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
  Cell,
  ReferenceLine,
} from "recharts";
import { useCurrencyStore } from "@/store/currency";

interface HourlyPerformance {
  hour: number;
  pnl: number;
  trades: number;
  winRate: number;
}

interface HourlyPerformanceChartProps {
  data: HourlyPerformance[];
  height?: number;
  currency?: string;
  metric?: "pnl" | "trades" | "winRate";
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: Array<{
    value: number;
    dataKey: string;
    payload: HourlyPerformance;
  }>;
  label?: string;
  currency: string;
  formatAmount: (amount: number, currency: string) => string;
}

function CustomTooltip({
  active,
  payload,
  currency,
  formatAmount,
}: CustomTooltipProps) {
  if (!active || !payload || payload.length === 0) return null;

  const dataPoint = payload[0].payload;
  const isProfit = dataPoint.pnl >= 0;

  const formatHour = (hour: number) => {
    const ampm = hour >= 12 ? "PM" : "AM";
    const displayHour = hour % 12 || 12;
    return `${displayHour}:00 ${ampm}`;
  };

  return (
    <div
      className="rounded-lg border bg-popover p-3 shadow-md"
      style={{ backgroundColor: "hsl(var(--popover))" }}
    >
      <p className="font-medium mb-2">{formatHour(dataPoint.hour)}</p>
      <div className="space-y-1 text-sm">
        <div className="flex justify-between gap-4">
          <span className="text-muted-foreground">P&L:</span>
          <span className={isProfit ? "text-green-500" : "text-red-500"}>
            {isProfit ? "+" : ""}
            {formatAmount(dataPoint.pnl, currency)}
          </span>
        </div>
        <div className="flex justify-between gap-4">
          <span className="text-muted-foreground">Trades:</span>
          <span>{dataPoint.trades}</span>
        </div>
        <div className="flex justify-between gap-4">
          <span className="text-muted-foreground">Win Rate:</span>
          <span
            className={
              dataPoint.winRate >= 50 ? "text-green-500" : "text-red-500"
            }
          >
            {dataPoint.winRate.toFixed(1)}%
          </span>
        </div>
      </div>
    </div>
  );
}

export function HourlyPerformanceChart({
  data,
  height = 300,
  currency = "USD",
  metric = "pnl",
}: HourlyPerformanceChartProps) {
  const { formatAmount } = useCurrencyStore();

  const chartData = React.useMemo(() => {
    if (!data || data.length === 0) {
      // Return empty hours if no data
      return Array.from({ length: 24 }, (_, i) => ({
        hour: i,
        pnl: 0,
        trades: 0,
        winRate: 0,
      }));
    }

    // Ensure all 24 hours are represented
    const hourMap = new Map<number, HourlyPerformance>();
    data.forEach((point) => {
      hourMap.set(point.hour, point);
    });

    return Array.from({ length: 24 }, (_, i) => {
      const existing = hourMap.get(i);
      return (
        existing || {
          hour: i,
          pnl: 0,
          trades: 0,
          winRate: 0,
        }
      );
    });
  }, [data]);

  const yDomain = React.useMemo(() => {
    if (chartData.length === 0) return [-100, 100];

    let min = 0;
    let max = 0;

    chartData.forEach((point) => {
      const value = point[metric];
      min = Math.min(min, value);
      max = Math.max(max, value);
    });

    if (metric === "winRate") {
      return [0, 100];
    }

    const padding = Math.max(Math.abs(max - min) * 0.1, 10);
    return [Math.floor(min - padding), Math.ceil(max + padding)];
  }, [chartData, metric]);

  const formatXAxis = (hour: number) => {
    if (hour % 4 === 0) {
      const ampm = hour >= 12 ? "PM" : "AM";
      const displayHour = hour % 12 || 12;
      return `${displayHour}${ampm}`;
    }
    return "";
  };

  const formatYAxis = (value: number) => {
    if (metric === "winRate") {
      return `${value}%`;
    }
    if (metric === "trades") {
      return value.toFixed(0);
    }
    if (Math.abs(value) >= 1000000) {
      return `${(value / 1000000).toFixed(1)}M`;
    }
    if (Math.abs(value) >= 1000) {
      return `${(value / 1000).toFixed(1)}K`;
    }
    return value.toFixed(0);
  };

  const getBarColor = (value: number) => {
    if (metric === "winRate") {
      return value >= 50 ? "#22c55e" : "#ef4444";
    }
    if (metric === "pnl") {
      return value >= 0 ? "#22c55e" : "#ef4444";
    }
    return "#3b82f6";
  };

  const hasData = data && data.some((d) => d.trades > 0);

  if (!hasData) {
    return (
      <div
        className="flex items-center justify-center text-muted-foreground"
        style={{ height }}
      >
        <p>No hourly performance data available</p>
      </div>
    );
  }

  // Find best and worst hours
  const sortedByPnL = [...chartData].sort((a, b) => b.pnl - a.pnl);
  const bestHour = sortedByPnL.find((h) => h.trades > 0);
  const worstHour = [...sortedByPnL].reverse().find((h) => h.trades > 0);

  const formatHourLabel = (hour: number) => {
    const ampm = hour >= 12 ? "PM" : "AM";
    const displayHour = hour % 12 || 12;
    return `${displayHour}:00 ${ampm}`;
  };

  return (
    <div className="space-y-2">
      <div className="flex gap-4 text-sm px-4">
        {bestHour && bestHour.trades > 0 && (
          <div>
            <span className="text-muted-foreground">Best Hour: </span>
            <span className="text-green-500 font-medium">
              {formatHourLabel(bestHour.hour)} (+
              {formatAmount(bestHour.pnl, currency)})
            </span>
          </div>
        )}
        {worstHour && worstHour.trades > 0 && worstHour.pnl < 0 && (
          <div>
            <span className="text-muted-foreground">Worst Hour: </span>
            <span className="text-red-500 font-medium">
              {formatHourLabel(worstHour.hour)} (
              {formatAmount(worstHour.pnl, currency)})
            </span>
          </div>
        )}
      </div>
      <ResponsiveContainer width="100%" height={height - 30}>
        <BarChart
          data={chartData}
          margin={{ top: 10, right: 30, left: 20, bottom: 20 }}
        >
          <CartesianGrid
            strokeDasharray="3 3"
            vertical={false}
            stroke="hsl(var(--border))"
          />
          <XAxis
            dataKey="hour"
            tickFormatter={formatXAxis}
            tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 12 }}
            tickLine={false}
            axisLine={{ stroke: "hsl(var(--border))" }}
            interval={0}
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
          {metric === "pnl" && (
            <ReferenceLine y={0} stroke="hsl(var(--border))" strokeWidth={1} />
          )}
          {metric === "winRate" && (
            <ReferenceLine
              y={50}
              stroke="hsl(var(--muted-foreground))"
              strokeWidth={1}
              strokeDasharray="3 3"
            />
          )}
          <Bar dataKey={metric} radius={[2, 2, 0, 0]} maxBarSize={30}>
            {chartData.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={getBarColor(entry[metric])} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export default HourlyPerformanceChart;
