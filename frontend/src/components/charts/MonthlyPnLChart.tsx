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
  currency?: string;
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: Array<{
    payload: MonthlyPnLData;
    value: number;
  }>;
  label?: string;
  currency?: string;
}

function CustomTooltip({
  active,
  payload,
  label,
  currency = "USD",
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
  currency = "USD",
}: MonthlyPnLChartProps) {
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
    <div className={cn("w-full", className)} style={{ height }}>
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
              return `${value}`;
            }}
            width={60}
          />
          {showTooltip && (
            <Tooltip
              content={<CustomTooltip currency={currency} />}
              cursor={{ fill: "hsl(var(--accent))", opacity: 0.3 }}
            />
          )}
          <ReferenceLine y={0} stroke="hsl(var(--border))" strokeWidth={1} />
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
  );
}

export default MonthlyPnLChart;
