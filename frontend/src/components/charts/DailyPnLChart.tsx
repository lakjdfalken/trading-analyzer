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
import { Info } from "lucide-react";
import { useCurrencyStore } from "@/store/currency";

interface DailyPnLDataPoint {
  date: string;
  pnl: number;
  cumulativePnl: number;
  trades: number;
  previousBalance?: number | null;
  pnlPercent?: number | null;
}

interface DailyPnLChartProps {
  data: DailyPnLDataPoint[];
  height?: number;
  showCumulative?: boolean;
  currency: string;
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
        {dataPoint.pnlPercent != null && (
          <div className="flex justify-between gap-4">
            <span className="text-muted-foreground">P&L %:</span>
            <span className={isProfit ? "text-green-500" : "text-red-500"}>
              {isProfit ? "+" : ""}
              {dataPoint.pnlPercent.toFixed(2)}%
            </span>
          </div>
        )}
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
        {dataPoint.previousBalance != null && (
          <div className="flex justify-between gap-4 pt-1 border-t border-border mt-1">
            <span className="text-muted-foreground text-xs">
              Prev. Balance:
            </span>
            <span className="text-xs">
              {formatAmount(dataPoint.previousBalance, currency)}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}

function InfoTooltip() {
  const [isVisible, setIsVisible] = React.useState(false);

  return (
    <div className="relative inline-block">
      <button
        onMouseEnter={() => setIsVisible(true)}
        onMouseLeave={() => setIsVisible(false)}
        onClick={() => setIsVisible(!isVisible)}
        className="text-muted-foreground hover:text-foreground transition-colors ml-2"
        aria-label="Information about P&L percentage calculation"
      >
        <Info className="h-4 w-4" />
      </button>
      {isVisible && (
        <div className="absolute z-50 bottom-full left-1/2 -translate-x-1/2 mb-2 w-64 p-3 bg-popover border border-border rounded-lg shadow-lg text-sm">
          <p className="text-foreground font-medium mb-1">P&L % Calculation</p>
          <p className="text-muted-foreground text-xs">
            The daily P&L percentage is calculated as the day&apos;s profit or
            loss divided by the previous day&apos;s closing account balance.
          </p>
          <p className="text-muted-foreground text-xs mt-2">
            Formula: (Daily P&L ÷ Previous Day Balance) × 100
          </p>
          <div className="absolute bottom-0 left-1/2 -translate-x-1/2 translate-y-full">
            <div className="border-8 border-transparent border-t-border" />
          </div>
        </div>
      )}
    </div>
  );
}

export function DailyPnLChart({
  data,
  height = 300,
  showCumulative = false,
  currency,
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

  // Calculate summary stats
  const stats = React.useMemo(() => {
    if (chartData.length === 0) return null;

    const percentages = chartData
      .filter((d) => d.pnlPercent != null)
      .map((d) => d.pnlPercent as number);

    if (percentages.length === 0) return null;

    const avgPercent =
      percentages.reduce((a, b) => a + b, 0) / percentages.length;
    const maxPercent = Math.max(...percentages);
    const minPercent = Math.min(...percentages);

    return { avgPercent, maxPercent, minPercent };
  }, [chartData]);

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
    <div>
      {stats && (
        <div className="flex items-center gap-4 mb-3 text-sm">
          <div className="flex items-center">
            <span className="text-muted-foreground">Avg Daily %:</span>
            <span
              className={`ml-1 font-medium ${stats.avgPercent >= 0 ? "text-green-500" : "text-red-500"}`}
            >
              {stats.avgPercent >= 0 ? "+" : ""}
              {stats.avgPercent.toFixed(2)}%
            </span>
            <InfoTooltip />
          </div>
          <div>
            <span className="text-muted-foreground">Best:</span>
            <span className="ml-1 font-medium text-green-500">
              +{stats.maxPercent.toFixed(2)}%
            </span>
          </div>
          <div>
            <span className="text-muted-foreground">Worst:</span>
            <span className="ml-1 font-medium text-red-500">
              {stats.minPercent.toFixed(2)}%
            </span>
          </div>
        </div>
      )}
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
            wrapperStyle={{ zIndex: 1000 }}
            position={{ y: 50 }}
            allowEscapeViewBox={{ x: false, y: true }}
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
    </div>
  );
}

export default DailyPnLChart;
