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
  ScatterChart,
  Scatter,
  ZAxis,
} from "recharts";
import { Wallet, TrendingUp, TrendingDown } from "lucide-react";
import { useCurrencyStore } from "@/store/currency";

interface SizeDistribution {
  range: string;
  rangeMin: number;
  rangeMax: number;
  count: number;
  totalPnL: number;
  avgPnL: number;
}

interface PositionSizeData {
  avgPositionSize: number;
  minPositionSize: number;
  maxPositionSize: number;
  avgWinnerSize: number;
  avgLoserSize: number;
  sizeDistribution: SizeDistribution[];
  sizePnLCorrelation: Array<{ size: number; pnl: number }>;
}

interface PositionSizeChartProps {
  data: PositionSizeData | null;
  height?: number;
  currency: string;
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: Array<{
    value: number;
    dataKey: string;
    payload: SizeDistribution;
  }>;
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

  return (
    <div
      className="rounded-lg border bg-popover p-3 shadow-md"
      style={{ backgroundColor: "hsl(var(--popover))" }}
    >
      <p className="font-medium mb-2">Size: {dataPoint.range}</p>
      <div className="space-y-1 text-sm">
        <div className="flex justify-between gap-4">
          <span className="text-muted-foreground">Trades:</span>
          <span>{dataPoint.count}</span>
        </div>
        <div className="flex justify-between gap-4">
          <span className="text-muted-foreground">Total P&L:</span>
          <span
            className={
              dataPoint.totalPnL >= 0 ? "text-green-500" : "text-red-500"
            }
          >
            {dataPoint.totalPnL >= 0 ? "+" : ""}
            {formatAmount(dataPoint.totalPnL, currency)}
          </span>
        </div>
        <div className="flex justify-between gap-4">
          <span className="text-muted-foreground">Avg P&L:</span>
          <span
            className={
              dataPoint.avgPnL >= 0 ? "text-green-500" : "text-red-500"
            }
          >
            {dataPoint.avgPnL >= 0 ? "+" : ""}
            {formatAmount(dataPoint.avgPnL, currency)}
          </span>
        </div>
      </div>
    </div>
  );
}

interface StatCardProps {
  label: string;
  value: string;
  icon: React.ReactNode;
  color: "green" | "red" | "blue" | "neutral";
}

function StatCard({ label, value, icon, color }: StatCardProps) {
  const colorClasses = {
    green: "text-green-500 bg-green-500/10 border-green-500/20",
    red: "text-red-500 bg-red-500/10 border-red-500/20",
    blue: "text-blue-500 bg-blue-500/10 border-blue-500/20",
    neutral: "text-muted-foreground bg-muted/50 border-border",
  };

  const textColorClasses = {
    green: "text-green-500",
    red: "text-red-500",
    blue: "text-blue-500",
    neutral: "text-foreground",
  };

  return (
    <div
      className={`flex flex-col items-center justify-center p-3 rounded-lg border ${colorClasses[color]}`}
    >
      <div className="flex items-center gap-2 mb-1">
        {icon}
        <span className="text-xs text-muted-foreground">{label}</span>
      </div>
      <span className={`text-lg font-bold ${textColorClasses[color]}`}>
        {value}
      </span>
    </div>
  );
}

export function PositionSizeChart({
  data,
  height = 300,
  currency,
}: PositionSizeChartProps) {
  const { formatAmount } = useCurrencyStore();

  if (!data || data.avgPositionSize === 0) {
    return (
      <div
        className="flex items-center justify-center text-muted-foreground"
        style={{ height }}
      >
        <div className="text-center">
          <Wallet className="h-12 w-12 mx-auto mb-2 opacity-50" />
          <p>No position size data available</p>
        </div>
      </div>
    );
  }

  const {
    avgPositionSize,
    minPositionSize,
    maxPositionSize,
    avgWinnerSize,
    avgLoserSize,
    sizeDistribution,
  } = data;

  const formatSize = (size: number) => {
    if (size >= 1000000) {
      return `${(size / 1000000).toFixed(1)}M`;
    }
    if (size >= 1000) {
      return `${(size / 1000).toFixed(1)}K`;
    }
    return size.toFixed(0);
  };

  // Find best performing size range
  const bestRange = [...sizeDistribution]
    .filter((d) => d.count > 0)
    .sort((a, b) => b.avgPnL - a.avgPnL)[0];
  const worstRange = [...sizeDistribution]
    .filter((d) => d.count > 0)
    .sort((a, b) => a.avgPnL - b.avgPnL)[0];

  return (
    <div className="space-y-4" style={{ minHeight: height }}>
      {/* Stats Grid */}
      <div className="grid grid-cols-4 gap-2 px-2">
        <StatCard
          label="Avg Size"
          value={formatSize(avgPositionSize)}
          icon={<Wallet className="h-3 w-3 text-blue-500" />}
          color="blue"
        />
        <StatCard
          label="Winner Avg"
          value={formatSize(avgWinnerSize)}
          icon={<TrendingUp className="h-3 w-3 text-green-500" />}
          color="green"
        />
        <StatCard
          label="Loser Avg"
          value={formatSize(avgLoserSize)}
          icon={<TrendingDown className="h-3 w-3 text-red-500" />}
          color="red"
        />
        <StatCard
          label="Max Size"
          value={formatSize(maxPositionSize)}
          icon={<Wallet className="h-3 w-3 text-muted-foreground" />}
          color="neutral"
        />
      </div>

      {/* Best/Worst Range Summary */}
      {bestRange && worstRange && (
        <div className="flex gap-4 text-sm px-4">
          <div>
            <span className="text-muted-foreground">Best Size Range: </span>
            <span className="text-green-500 font-medium">
              {bestRange.range} (avg {formatAmount(bestRange.avgPnL, currency)})
            </span>
          </div>
          {worstRange.avgPnL < 0 && (
            <div>
              <span className="text-muted-foreground">Worst: </span>
              <span className="text-red-500 font-medium">
                {worstRange.range} (avg{" "}
                {formatAmount(worstRange.avgPnL, currency)})
              </span>
            </div>
          )}
        </div>
      )}

      {/* Distribution Chart */}
      <ResponsiveContainer width="100%" height={height - 120}>
        <BarChart
          data={sizeDistribution}
          margin={{ top: 10, right: 30, left: 20, bottom: 40 }}
        >
          <CartesianGrid
            strokeDasharray="3 3"
            vertical={false}
            stroke="hsl(var(--border))"
          />
          <XAxis
            dataKey="range"
            tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 10 }}
            tickLine={false}
            axisLine={{ stroke: "hsl(var(--border))" }}
            angle={-45}
            textAnchor="end"
            height={60}
          />
          <YAxis
            tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 12 }}
            tickLine={false}
            axisLine={false}
            label={{
              value: "Trades",
              angle: -90,
              position: "insideLeft",
              style: { fill: "hsl(var(--muted-foreground))", fontSize: 12 },
            }}
          />
          <Tooltip
            content={
              <CustomTooltip currency={currency} formatAmount={formatAmount} />
            }
            cursor={{ fill: "hsl(var(--muted))", opacity: 0.3 }}
          />
          <Bar dataKey="count" radius={[4, 4, 0, 0]} maxBarSize={50}>
            {sizeDistribution.map((entry, index) => (
              <Cell
                key={`cell-${index}`}
                fill={entry.avgPnL >= 0 ? "#22c55e" : "#ef4444"}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export default PositionSizeChart;
