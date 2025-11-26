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

interface DrawdownPeriod {
  startDate: string;
  endDate: string | null;
  maxDrawdown: number;
  maxDrawdownPercent: number;
  recoveryDays: number | null;
  recovered: boolean;
}

interface BalanceDataPoint {
  date: string;
  balance: number;
}

interface DrawdownChartProps {
  balanceData: BalanceDataPoint[];
  drawdownPeriods?: DrawdownPeriod[];
  height?: number;
  currency?: string;
}

interface ChartDataPoint {
  date: string;
  balance: number;
  peak: number;
  drawdown: number;
  drawdownPercent: number;
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: Array<{
    value: number;
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
  if (!active || !payload || payload.length === 0) return null;

  const dataPoint = payload[0].payload;

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
          <span className="text-muted-foreground">Balance:</span>
          <span>{formatAmount(dataPoint.balance, currency)}</span>
        </div>
        <div className="flex justify-between gap-4">
          <span className="text-muted-foreground">Peak:</span>
          <span>{formatAmount(dataPoint.peak, currency)}</span>
        </div>
        <div className="flex justify-between gap-4">
          <span className="text-muted-foreground">Drawdown:</span>
          <span className={dataPoint.drawdown > 0 ? "text-red-500" : ""}>
            {dataPoint.drawdown > 0 ? "-" : ""}
            {formatAmount(dataPoint.drawdown, currency)}
          </span>
        </div>
        <div className="flex justify-between gap-4">
          <span className="text-muted-foreground">Drawdown %:</span>
          <span className={dataPoint.drawdownPercent > 0 ? "text-red-500" : ""}>
            {dataPoint.drawdownPercent > 0 ? "-" : ""}
            {dataPoint.drawdownPercent.toFixed(2)}%
          </span>
        </div>
      </div>
    </div>
  );
}

export function DrawdownChart({
  balanceData,
  height = 300,
  currency = "USD",
}: DrawdownChartProps) {
  const { formatAmount } = useCurrencyStore();

  const chartData = React.useMemo(() => {
    if (!balanceData || balanceData.length === 0) return [];

    let peak = 0;
    return balanceData.map((point) => {
      const balance = point.balance;
      if (balance > peak) {
        peak = balance;
      }
      const drawdown = peak - balance;
      const drawdownPercent = peak > 0 ? (drawdown / peak) * 100 : 0;

      return {
        date: point.date,
        balance,
        peak,
        drawdown,
        drawdownPercent: -drawdownPercent, // Negative for display below zero line
      };
    });
  }, [balanceData]);

  const yDomain = React.useMemo(() => {
    if (chartData.length === 0) return [-10, 0];

    let minPercent = 0;
    chartData.forEach((point) => {
      minPercent = Math.min(minPercent, point.drawdownPercent);
    });

    const padding = Math.abs(minPercent) * 0.1;
    return [Math.floor(minPercent - padding), 5];
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
    return `${value.toFixed(0)}%`;
  };

  if (!balanceData || balanceData.length === 0) {
    return (
      <div
        className="flex items-center justify-center text-muted-foreground"
        style={{ height }}
      >
        <p>No balance data available for drawdown analysis</p>
      </div>
    );
  }

  // Calculate summary statistics
  const maxDrawdownPercent = Math.min(
    ...chartData.map((d) => d.drawdownPercent),
  );
  const currentDrawdownPercent =
    chartData[chartData.length - 1]?.drawdownPercent || 0;

  return (
    <div className="space-y-2">
      <div className="flex gap-4 text-sm px-4">
        <div>
          <span className="text-muted-foreground">Max Drawdown: </span>
          <span className="text-red-500 font-medium">
            {Math.abs(maxDrawdownPercent).toFixed(2)}%
          </span>
        </div>
        <div>
          <span className="text-muted-foreground">Current: </span>
          <span
            className={
              currentDrawdownPercent < 0
                ? "text-red-500 font-medium"
                : "text-green-500 font-medium"
            }
          >
            {Math.abs(currentDrawdownPercent).toFixed(2)}%
          </span>
        </div>
      </div>
      <ResponsiveContainer width="100%" height={height - 30}>
        <AreaChart
          data={chartData}
          margin={{ top: 10, right: 30, left: 20, bottom: 20 }}
        >
          <defs>
            <linearGradient id="drawdownGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#ef4444" stopOpacity={0.1} />
              <stop offset="95%" stopColor="#ef4444" stopOpacity={0.6} />
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
            dataKey="drawdownPercent"
            stroke="#ef4444"
            strokeWidth={2}
            fill="url(#drawdownGradient)"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

export default DrawdownChart;
