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
  ReferenceLine,
} from "recharts";
import { format } from "date-fns";
import { cn, formatCurrency } from "@/lib/utils";

export interface BalanceDataPoint {
  date: string | Date;
  balance: number;
  drawdown?: number;
  deposit?: number;
  withdrawal?: number;
}

export interface BalanceChartProps {
  data: BalanceDataPoint[];
  height?: number | string;
  showDrawdown?: boolean;
  showGrid?: boolean;
  showTooltip?: boolean;
  animate?: boolean;
  className?: string;
  currency?: string;
  startingBalance?: number;
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
  currency?: string;
}

function CustomTooltip({ active, payload, label, currency = "USD" }: CustomTooltipProps) {
  if (!active || !payload || payload.length === 0) {
    return null;
  }

  const balanceData = payload.find((p) => p.dataKey === "balance");
  const drawdownData = payload.find((p) => p.dataKey === "drawdown");

  return (
    <div className="bg-popover border border-border rounded-lg shadow-lg p-3 text-sm">
      <p className="text-muted-foreground text-xs mb-2">{label}</p>
      {balanceData && (
        <div className="flex items-center justify-between gap-4">
          <span className="text-muted-foreground">Balance:</span>
          <span className="font-semibold">
            {formatCurrency(balanceData.value, currency)}
          </span>
        </div>
      )}
      {drawdownData && drawdownData.value !== undefined && (
        <div className="flex items-center justify-between gap-4 mt-1">
          <span className="text-muted-foreground">Drawdown:</span>
          <span className={cn("font-semibold", drawdownData.value < 0 ? "text-red-500" : "text-muted-foreground")}>
            {drawdownData.value.toFixed(2)}%
          </span>
        </div>
      )}
    </div>
  );
}

export function BalanceChart({
  data,
  height = 300,
  showDrawdown = false,
  showGrid = true,
  showTooltip = true,
  animate = true,
  className,
  currency = "USD",
  startingBalance,
}: BalanceChartProps) {
  // Format data for the chart
  const chartData = React.useMemo(() => {
    return data.map((point) => ({
      ...point,
      date:
        typeof point.date === "string"
          ? point.date
          : format(point.date, "MMM d, yyyy"),
      balance: point.balance,
      drawdown: point.drawdown,
    }));
  }, [data]);

  // Calculate domain for Y axis
  const yDomain = React.useMemo(() => {
    if (chartData.length === 0) return [0, 100];

    const values = chartData.map((d) => d.balance);
    const min = Math.min(...values);
    const max = Math.max(...values);
    const padding = (max - min) * 0.1;

    return [Math.floor(min - padding), Math.ceil(max + padding)];
  }, [chartData]);

  // Calculate if we're in profit or loss overall
  const isProfit = React.useMemo(() => {
    if (chartData.length === 0) return true;
    const start = startingBalance ?? chartData[0]?.balance ?? 0;
    const end = chartData[chartData.length - 1]?.balance ?? 0;
    return end >= start;
  }, [chartData, startingBalance]);

  const gradientId = React.useId();
  const drawdownGradientId = React.useId();

  if (chartData.length === 0) {
    return (
      <div
        className={cn(
          "flex items-center justify-center text-muted-foreground",
          className
        )}
        style={{ height }}
      >
        No data available
      </div>
    );
  }

  return (
    <div className={cn("w-full", className)} style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart
          data={chartData}
          margin={{ top: 10, right: 10, left: 0, bottom: 0 }}
        >
          <defs>
            <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
              <stop
                offset="5%"
                stopColor={isProfit ? "hsl(142, 76%, 36%)" : "hsl(0, 84%, 60%)"}
                stopOpacity={0.3}
              />
              <stop
                offset="95%"
                stopColor={isProfit ? "hsl(142, 76%, 36%)" : "hsl(0, 84%, 60%)"}
                stopOpacity={0}
              />
            </linearGradient>
            {showDrawdown && (
              <linearGradient id={drawdownGradientId} x1="0" y1="0" x2="0" y2="1">
                <stop
                  offset="5%"
                  stopColor="hsl(0, 84%, 60%)"
                  stopOpacity={0.2}
                />
                <stop
                  offset="95%"
                  stopColor="hsl(0, 84%, 60%)"
                  stopOpacity={0}
                />
              </linearGradient>
            )}
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
            minTickGap={50}
          />

          <YAxis
            domain={yDomain}
            axisLine={false}
            tickLine={false}
            tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 12 }}
            tickMargin={8}
            tickFormatter={(value) => formatCurrency(value, currency)}
            width={80}
          />

          {showTooltip && (
            <Tooltip
              content={<CustomTooltip currency={currency} />}
              cursor={{
                stroke: "hsl(var(--muted-foreground))",
                strokeWidth: 1,
                strokeDasharray: "4 4",
              }}
            />
          )}

          {/* Reference line at starting balance */}
          {startingBalance && (
            <ReferenceLine
              y={startingBalance}
              stroke="hsl(var(--muted-foreground))"
              strokeDasharray="3 3"
              strokeOpacity={0.5}
            />
          )}

          {/* Main balance area */}
          <Area
            type="monotone"
            dataKey="balance"
            stroke={isProfit ? "hsl(142, 76%, 36%)" : "hsl(0, 84%, 60%)"}
            strokeWidth={2}
            fill={`url(#${gradientId})`}
            isAnimationActive={animate}
            animationDuration={1000}
            animationEasing="ease-out"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

export default BalanceChart;
