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

interface WeekdayPerformance {
  weekday: string;
  pnl: number;
  trades: number;
  winRate: number;
}

interface WeekdayPerformanceChartProps {
  data: WeekdayPerformance[];
  height?: number;
  currency?: string;
  metric?: "pnl" | "trades" | "winRate";
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: Array<{
    value: number;
    dataKey: string;
    payload: WeekdayPerformance;
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

  return (
    <div
      className="rounded-lg border bg-popover p-3 shadow-md"
      style={{ backgroundColor: "hsl(var(--popover))" }}
    >
      <p className="font-medium mb-2">{dataPoint.weekday}</p>
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

const WEEKDAY_ORDER = [
  "Monday",
  "Tuesday",
  "Wednesday",
  "Thursday",
  "Friday",
  "Saturday",
  "Sunday",
];

const WEEKDAY_ABBREV: Record<string, string> = {
  Monday: "Mon",
  Tuesday: "Tue",
  Wednesday: "Wed",
  Thursday: "Thu",
  Friday: "Fri",
  Saturday: "Sat",
  Sunday: "Sun",
};

export function WeekdayPerformanceChart({
  data,
  height = 300,
  currency = "USD",
  metric = "pnl",
}: WeekdayPerformanceChartProps) {
  const { formatAmount } = useCurrencyStore();

  const chartData = React.useMemo(() => {
    if (!data || data.length === 0) {
      // Return empty weekdays if no data
      return WEEKDAY_ORDER.map((day) => ({
        weekday: day,
        pnl: 0,
        trades: 0,
        winRate: 0,
      }));
    }

    // Create a map of existing data
    const dayMap = new Map<string, WeekdayPerformance>();
    data.forEach((point) => {
      dayMap.set(point.weekday, point);
    });

    // Return data in correct weekday order
    return WEEKDAY_ORDER.map((day) => {
      const existing = dayMap.get(day);
      return (
        existing || {
          weekday: day,
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

  const formatXAxis = (weekday: string) => {
    return WEEKDAY_ABBREV[weekday] || weekday.slice(0, 3);
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
        <p>No weekday performance data available</p>
      </div>
    );
  }

  // Find best and worst days
  const sortedByPnL = [...chartData].sort((a, b) => b.pnl - a.pnl);
  const bestDay = sortedByPnL.find((d) => d.trades > 0);
  const worstDay = [...sortedByPnL].reverse().find((d) => d.trades > 0);

  return (
    <div className="space-y-2">
      <div className="flex gap-4 text-sm px-4">
        {bestDay && bestDay.trades > 0 && (
          <div>
            <span className="text-muted-foreground">Best Day: </span>
            <span className="text-green-500 font-medium">
              {bestDay.weekday} (+{formatAmount(bestDay.pnl, currency)})
            </span>
          </div>
        )}
        {worstDay && worstDay.trades > 0 && worstDay.pnl < 0 && (
          <div>
            <span className="text-muted-foreground">Worst Day: </span>
            <span className="text-red-500 font-medium">
              {worstDay.weekday} ({formatAmount(worstDay.pnl, currency)})
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
            dataKey="weekday"
            tickFormatter={formatXAxis}
            tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 12 }}
            tickLine={false}
            axisLine={{ stroke: "hsl(var(--border))" }}
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
          <Bar dataKey={metric} radius={[4, 4, 0, 0]} maxBarSize={60}>
            {chartData.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={getBarColor(entry[metric])} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export default WeekdayPerformanceChart;
