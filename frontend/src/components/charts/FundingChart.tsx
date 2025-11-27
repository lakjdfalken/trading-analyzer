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
  Legend,
} from "recharts";
import { format } from "date-fns";
import { useCurrencyStore } from "@/store/currency";

interface FundingDataPoint {
  date: string;
  deposits: number;
  withdrawals: number;
  net: number;
  cumulative: number;
}

interface FundingChartProps {
  data: FundingDataPoint[];
  height?: number;
  currency?: string;
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: Array<{
    value: number;
    dataKey: string;
    payload: FundingDataPoint;
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
          <span className="text-muted-foreground">Deposits:</span>
          <span className="text-green-500">
            +{formatAmount(dataPoint.deposits, currency)}
          </span>
        </div>
        <div className="flex justify-between gap-4">
          <span className="text-muted-foreground">Withdrawals:</span>
          <span className="text-red-500">
            -{formatAmount(dataPoint.withdrawals, currency)}
          </span>
        </div>
        <div className="flex justify-between gap-4 border-t pt-1 mt-1">
          <span className="text-muted-foreground">Net:</span>
          <span className={dataPoint.net >= 0 ? "text-green-500" : "text-red-500"}>
            {dataPoint.net >= 0 ? "+" : ""}
            {formatAmount(dataPoint.net, currency)}
          </span>
        </div>
        <div className="flex justify-between gap-4">
          <span className="text-muted-foreground">Cumulative:</span>
          <span className={dataPoint.cumulative >= 0 ? "text-green-500" : "text-red-500"}>
            {dataPoint.cumulative >= 0 ? "+" : ""}
            {formatAmount(dataPoint.cumulative, currency)}
          </span>
        </div>
      </div>
    </div>
  );
}

export function FundingChart({
  data,
  height = 300,
  currency = "USD",
}: FundingChartProps) {
  const { formatAmount } = useCurrencyStore();

  const chartData = React.useMemo(() => {
    if (!data || data.length === 0) return [];

    return data.map((point) => ({
      ...point,
      // Make withdrawals negative for display
      withdrawalsDisplay: -point.withdrawals,
    }));
  }, [data]);

  const yDomain = React.useMemo(() => {
    if (chartData.length === 0) return [-100, 100];

    let min = 0;
    let max = 0;

    chartData.forEach((point) => {
      min = Math.min(min, -point.withdrawals);
      max = Math.max(max, point.deposits);
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
        <p>No deposits or withdrawals in this period</p>
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart
        data={chartData}
        margin={{ top: 20, right: 30, left: 20, bottom: 20 }}
        stackOffset="sign"
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
        <Legend
          wrapperStyle={{ paddingTop: "10px" }}
          formatter={(value) => (
            <span style={{ color: "hsl(var(--foreground))" }}>{value}</span>
          )}
        />
        <ReferenceLine y={0} stroke="hsl(var(--border))" strokeWidth={1} />
        <Bar
          dataKey="deposits"
          name="Deposits"
          fill="#22c55e"
          radius={[4, 4, 0, 0]}
          maxBarSize={50}
        />
        <Bar
          dataKey="withdrawalsDisplay"
          name="Withdrawals"
          fill="#ef4444"
          radius={[0, 0, 4, 4]}
          maxBarSize={50}
        />
      </BarChart>
    </ResponsiveContainer>
  );
}

export default FundingChart;
