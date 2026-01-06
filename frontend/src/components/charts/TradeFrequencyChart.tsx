"use client";

import React from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Legend,
  CartesianGrid,
} from "recharts";
import { Activity, Calendar, TrendingUp, Hash } from "lucide-react";
import type { AccountTradeFrequency, TradeFrequencyResponse } from "@/lib/api";

interface TradeFrequencyChartProps {
  data: TradeFrequencyResponse | null;
  height?: number;
  showByAccount?: boolean;
}

interface StatCardProps {
  label: string;
  value: number | string;
  icon: React.ReactNode;
  subLabel?: string;
}

function StatCard({ label, value, icon, subLabel }: StatCardProps) {
  return (
    <div className="flex flex-col items-center justify-center p-3 rounded-lg border bg-muted/30">
      <div className="flex items-center gap-2 mb-1">
        {icon}
        <span className="text-xs text-muted-foreground">{label}</span>
      </div>
      <span className="text-xl font-bold">{value}</span>
      {subLabel && (
        <span className="text-xs text-muted-foreground mt-0.5">{subLabel}</span>
      )}
    </div>
  );
}

const ACCOUNT_COLORS = [
  "#3b82f6", // blue
  "#10b981", // emerald
  "#f59e0b", // amber
  "#ef4444", // red
  "#8b5cf6", // violet
  "#ec4899", // pink
  "#06b6d4", // cyan
  "#84cc16", // lime
];

export function TradeFrequencyChart({
  data,
  height = 300,
  showByAccount = true,
}: TradeFrequencyChartProps) {
  const [view, setView] = React.useState<"daily" | "monthly" | "yearly">(
    "monthly",
  );

  if (!data || !data.aggregated) {
    return (
      <div
        className="flex items-center justify-center text-muted-foreground"
        style={{ height }}
      >
        <div className="text-center">
          <Activity className="h-12 w-12 mx-auto mb-2 opacity-50" />
          <p>No trade frequency data available</p>
        </div>
      </div>
    );
  }

  const { aggregated, by_account, date_range_days } = data;

  // Prepare chart data based on view
  const getChartData = () => {
    if (view === "daily") {
      // For daily, show last 30 days or all if less
      const dailyData = aggregated.daily.slice(-30);
      return dailyData.map((d) => ({
        label: new Date(d.date).toLocaleDateString("en-US", {
          month: "short",
          day: "numeric",
        }),
        fullDate: d.date,
        trades: d.trades,
      }));
    } else if (view === "monthly") {
      return aggregated.monthly.map((m) => {
        const [year, month] = m.month.split("-");
        const monthName = new Date(
          parseInt(year),
          parseInt(month) - 1,
        ).toLocaleDateString("en-US", { month: "short", year: "2-digit" });
        return {
          label: monthName,
          fullDate: m.month,
          trades: m.trades,
          tradingDays: m.trading_days,
        };
      });
    } else {
      return aggregated.yearly.map((y) => ({
        label: y.year.toString(),
        fullDate: y.year.toString(),
        trades: y.trades,
        tradingDays: y.trading_days,
        tradingMonths: y.trading_months,
      }));
    }
  };

  // Prepare multi-account chart data
  const getMultiAccountChartData = () => {
    if (by_account.length <= 1) return null;

    if (view === "monthly") {
      // Get all unique months
      const allMonths = new Set<string>();
      by_account.forEach((acc) => {
        acc.monthly.forEach((m) => allMonths.add(m.month));
      });

      const sortedMonths = Array.from(allMonths).sort();

      return sortedMonths.map((month) => {
        const [year, m] = month.split("-");
        const monthName = new Date(
          parseInt(year),
          parseInt(m) - 1,
        ).toLocaleDateString("en-US", { month: "short", year: "2-digit" });

        const dataPoint: Record<string, string | number> = {
          label: monthName,
          fullDate: month,
        };

        by_account.forEach((acc) => {
          const monthData = acc.monthly.find((md) => md.month === month);
          dataPoint[acc.account_name] = monthData?.trades || 0;
        });

        return dataPoint;
      });
    } else if (view === "yearly") {
      // Get all unique years
      const allYears = new Set<number>();
      by_account.forEach((acc) => {
        acc.yearly.forEach((y) => allYears.add(y.year));
      });

      const sortedYears = Array.from(allYears).sort();

      return sortedYears.map((year) => {
        const dataPoint: Record<string, string | number> = {
          label: year.toString(),
          fullDate: year.toString(),
        };

        by_account.forEach((acc) => {
          const yearData = acc.yearly.find((yd) => yd.year === year);
          dataPoint[acc.account_name] = yearData?.trades || 0;
        });

        return dataPoint;
      });
    }

    return null;
  };

  const chartData = getChartData();
  const multiAccountData = showByAccount ? getMultiAccountChartData() : null;
  // Only use multi-account stacked view if explicitly showing by account AND we have valid data
  const useMultiAccount =
    showByAccount &&
    multiAccountData &&
    multiAccountData.length > 0 &&
    by_account.length > 1 &&
    view !== "daily";

  // Always use aggregated chartData for consistent blue bars
  const displayData = chartData;

  const CustomTooltip = ({
    active,
    payload,
    label,
  }: {
    active?: boolean;
    payload?: Array<{ name: string; value: number; color: string }>;
    label?: string;
  }) => {
    if (!active || !payload || !payload.length) return null;

    return (
      <div className="bg-popover border border-border rounded-lg shadow-lg p-3">
        <p className="font-medium text-sm mb-2">{label}</p>
        {payload.map((entry, index) => (
          <div key={index} className="flex items-center gap-2 text-sm">
            <div
              className="w-3 h-3 rounded-full"
              style={{ backgroundColor: entry.color }}
            />
            <span className="text-muted-foreground">{entry.name}:</span>
            <span className="font-medium">{entry.value} trades</span>
          </div>
        ))}
      </div>
    );
  };

  return (
    <div className="space-y-4" style={{ minHeight: height }}>
      {/* View Selector */}
      <div className="flex justify-center gap-2">
        {(["daily", "monthly", "yearly"] as const).map((v) => (
          <button
            key={v}
            onClick={() => setView(v)}
            className={`px-3 py-1.5 text-sm rounded-md transition-colors ${
              view === v
                ? "bg-primary text-primary-foreground"
                : "bg-muted hover:bg-muted/80 text-muted-foreground"
            }`}
          >
            {v.charAt(0).toUpperCase() + v.slice(1)}
          </button>
        ))}
      </div>

      {/* Chart */}
      <div style={{ height: height - 180 }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={displayData}
            margin={{ top: 10, right: 10, left: 0, bottom: 20 }}
          >
            <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
            <XAxis
              dataKey="label"
              tick={{ fontSize: 11 }}
              tickLine={false}
              axisLine={false}
              angle={view === "daily" ? -45 : 0}
              textAnchor={view === "daily" ? "end" : "middle"}
              height={view === "daily" ? 60 : 30}
            />
            <YAxis
              tick={{ fontSize: 11 }}
              tickLine={false}
              axisLine={false}
              allowDecimals={false}
            />
            <Tooltip content={<CustomTooltip />} />
            <Bar
              dataKey="trades"
              fill="#3b82f6"
              radius={[4, 4, 0, 0]}
              name="Trades"
            />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Statistics Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2 px-2">
        <StatCard
          label="Total Trades"
          value={aggregated.total_trades.toLocaleString()}
          icon={<Hash className="h-4 w-4 text-blue-500" />}
        />
        <StatCard
          label="Trading Days"
          value={aggregated.total_trading_days.toLocaleString()}
          icon={<Calendar className="h-4 w-4 text-emerald-500" />}
          subLabel={`of ${date_range_days} days`}
        />
        <StatCard
          label="Avg/Trading Day"
          value={aggregated.avg_trades_per_trading_day.toFixed(1)}
          icon={<TrendingUp className="h-4 w-4 text-amber-500" />}
          subLabel="trades"
        />
        <StatCard
          label="Avg/Month"
          value={aggregated.avg_trades_per_month.toFixed(1)}
          icon={<Activity className="h-4 w-4 text-violet-500" />}
          subLabel="trades"
        />
      </div>

      {/* Per-Account Summary (if multiple accounts) */}
      {by_account.length > 1 && (
        <div className="border-t pt-4">
          <p className="text-sm font-medium text-muted-foreground mb-2 px-2">
            By Account
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2 px-2">
            {by_account.map((acc, idx) => (
              <div
                key={acc.account_id}
                className="flex items-center justify-between p-2 rounded-lg bg-muted/30 border"
              >
                <div className="flex items-center gap-2">
                  <div
                    className="w-3 h-3 rounded-full"
                    style={{
                      backgroundColor:
                        ACCOUNT_COLORS[idx % ACCOUNT_COLORS.length],
                    }}
                  />
                  <span className="text-sm font-medium truncate max-w-[150px]">
                    {acc.account_name}
                  </span>
                </div>
                <div className="flex items-center gap-4 text-sm">
                  <span className="text-muted-foreground">
                    {acc.total_trades.toLocaleString()} trades
                  </span>
                  <span className="text-muted-foreground">
                    {acc.avg_trades_per_trading_day.toFixed(1)}/day
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default TradeFrequencyChart;
