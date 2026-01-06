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
} from "recharts";
import { cn, formatCurrency } from "@/lib/utils";
import type { SpreadCostDataPoint, SpreadCostByInstrument } from "@/lib/api";

interface SpreadCostChartProps {
  data: SpreadCostDataPoint[];
  byInstrument: SpreadCostByInstrument[];
  totalSpreadCost: number;
  totalTrades: number;
  avgSpreadPerTrade: number;
  height?: number;
  currency: string;
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: Array<{
    payload: SpreadCostDataPoint;
    value: number;
  }>;
  label?: string;
  currency: string;
}

function CustomTooltip({ active, payload, label, currency }: CustomTooltipProps) {
  if (!active || !payload || !payload.length) {
    return null;
  }

  const data = payload[0].payload;

  return (
    <div className="bg-popover border border-border rounded-lg shadow-lg p-3 min-w-[200px]">
      <p className="text-sm font-medium text-foreground mb-2">{label}</p>
      <div className="space-y-1">
        <div className="flex items-center justify-between gap-4">
          <span className="text-xs text-muted-foreground">Spread Cost</span>
          <span className="text-sm font-semibold text-orange-500">
            {formatCurrency(data.spread_cost, currency)}
          </span>
        </div>
        <div className="flex items-center justify-between gap-4">
          <span className="text-xs text-muted-foreground">Trades</span>
          <span className="text-sm text-foreground">{data.trades}</span>
        </div>
        <div className="flex items-center justify-between gap-4">
          <span className="text-xs text-muted-foreground">Avg per Trade</span>
          <span className="text-sm text-foreground">
            {formatCurrency(data.avg_spread_cost, currency)}
          </span>
        </div>
        {Object.keys(data.instruments).length > 0 && (
          <div className="border-t border-border mt-2 pt-2">
            <p className="text-xs text-muted-foreground mb-1">By Instrument:</p>
            {Object.entries(data.instruments)
              .sort(([, a], [, b]) => b - a)
              .slice(0, 5)
              .map(([inst, cost]) => (
                <div key={inst} className="flex items-center justify-between gap-4">
                  <span className="text-xs text-muted-foreground truncate max-w-[120px]">
                    {inst}
                  </span>
                  <span className="text-xs text-foreground">
                    {formatCurrency(cost, currency)}
                  </span>
                </div>
              ))}
          </div>
        )}
      </div>
    </div>
  );
}

export function SpreadCostChart({
  data,
  byInstrument,
  totalSpreadCost,
  totalTrades,
  avgSpreadPerTrade,
  height = 300,
  currency,
}: SpreadCostChartProps) {
  // Calculate yearly totals
  const yearlyTotals = React.useMemo(() => {
    const totals: Record<string, { year: string; cost: number; trades: number }> = {};

    data.forEach((item) => {
      const year = item.month_key.substring(0, 4);
      if (!totals[year]) {
        totals[year] = { year, cost: 0, trades: 0 };
      }
      totals[year].cost += item.spread_cost;
      totals[year].trades += item.trades;
    });

    return Object.values(totals).sort((a, b) => a.year.localeCompare(b.year));
  }, [data]);

  if (!data || data.length === 0) {
    return (
      <div
        className={cn("flex items-center justify-center text-muted-foreground")}
        style={{ height }}
      >
        <p className="text-sm">No spread cost data available</p>
      </div>
    );
  }

  const maxValue = Math.max(...data.map((d) => d.spread_cost));

  return (
    <div className="w-full">
      {/* Summary */}
      <div className="mb-4 px-2">
        <div className="flex flex-wrap gap-4 text-sm">
          {/* Total Spread Cost */}
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-md bg-orange-500/10 border border-orange-500/20">
            <span className="text-muted-foreground font-medium">Total:</span>
            <span className="font-semibold text-orange-500">
              {formatCurrency(totalSpreadCost, currency)}
            </span>
            <span className="text-xs text-muted-foreground">
              ({totalTrades} trades)
            </span>
          </div>

          {/* Average per Trade */}
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-md bg-muted/50">
            <span className="text-muted-foreground font-medium">Avg/Trade:</span>
            <span className="font-semibold text-foreground">
              {formatCurrency(avgSpreadPerTrade, currency)}
            </span>
          </div>

          {/* Yearly Totals */}
          {yearlyTotals.map((yearly) => (
            <div
              key={yearly.year}
              className="flex items-center gap-2 px-3 py-1.5 rounded-md bg-muted/50"
            >
              <span className="text-muted-foreground font-medium">{yearly.year}:</span>
              <span className="font-semibold text-orange-500">
                {formatCurrency(yearly.cost, currency)}
              </span>
              <span className="text-xs text-muted-foreground">
                ({yearly.trades} trades)
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Chart */}
      <div style={{ height }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={data}
            margin={{ top: 10, right: 10, left: 10, bottom: 0 }}
          >
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="hsl(var(--border))"
              vertical={false}
            />
            <XAxis
              dataKey="month"
              axisLine={false}
              tickLine={false}
              tick={{ fontSize: 12, fill: "hsl(var(--muted-foreground))" }}
              dy={10}
            />
            <YAxis
              domain={[0, maxValue * 1.1]}
              axisLine={false}
              tickLine={false}
              tick={{ fontSize: 12, fill: "hsl(var(--muted-foreground))" }}
              tickFormatter={(value) => {
                if (Math.abs(value) >= 1000) {
                  return `${(value / 1000).toFixed(0)}k`;
                }
                return `${Math.round(value)}`;
              }}
              width={60}
            />
            <Tooltip
              content={<CustomTooltip currency={currency} />}
              cursor={{ fill: "hsl(var(--accent))", opacity: 0.3 }}
            />
            <Bar
              dataKey="spread_cost"
              radius={[4, 4, 0, 0]}
              isAnimationActive={true}
              animationDuration={500}
              animationEasing="ease-out"
            >
              {data.map((entry, index) => (
                <Cell key={`cell-${index}`} fill="#f97316" fillOpacity={0.9} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Top Instruments by Spread Cost */}
      {byInstrument.length > 0 && (
        <div className="mt-4 px-2">
          <p className="text-sm font-medium text-muted-foreground mb-2">
            Top Instruments by Spread Cost
          </p>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-2">
            {byInstrument.slice(0, 8).map((inst) => (
              <div
                key={inst.instrument}
                className="flex items-center justify-between px-3 py-2 rounded-md bg-muted/30 border border-border/50"
              >
                <span className="text-xs text-muted-foreground truncate max-w-[100px]">
                  {inst.instrument}
                </span>
                <span className="text-xs font-medium text-orange-500">
                  {formatCurrency(inst.spread_cost, currency)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default SpreadCostChart;
