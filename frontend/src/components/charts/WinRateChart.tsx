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
  Legend,
  LabelList,
} from "recharts";
import { cn } from "@/lib/utils";

export interface WinRateData {
  name: string;
  winRate: number;
  wins: number;
  losses: number;
  trades: number;
}

export interface WinRateChartProps {
  data: WinRateData[];
  height?: number;
  showLegend?: boolean;
  showLabels?: boolean;
  className?: string;
  layout?: "horizontal" | "vertical";
  colors?: {
    win?: string;
    loss?: string;
    bar?: string;
  };
}

const defaultColors = {
  win: "#10B981",
  loss: "#EF4444",
  bar: "#3B82F6",
};

interface CustomTooltipProps {
  active?: boolean;
  payload?: Array<{
    name: string;
    value: number;
    payload: WinRateData;
  }>;
  label?: string;
}

function CustomTooltip({ active, payload }: CustomTooltipProps) {
  if (!active || !payload || payload.length === 0) {
    return null;
  }

  const data = payload[0].payload;

  return (
    <div className="bg-popover border border-border rounded-lg shadow-lg p-3 text-sm">
      <p className="font-medium text-foreground mb-2">{data.name}</p>
      <div className="space-y-1">
        <div className="flex items-center justify-between gap-4">
          <span className="text-muted-foreground">Win Rate:</span>
          <span className="font-medium text-foreground">
            {data.winRate.toFixed(1)}%
          </span>
        </div>
        <div className="flex items-center justify-between gap-4">
          <span className="text-green-500">Wins:</span>
          <span className="font-medium">{data.wins}</span>
        </div>
        <div className="flex items-center justify-between gap-4">
          <span className="text-red-500">Losses:</span>
          <span className="font-medium">{data.losses}</span>
        </div>
        <div className="flex items-center justify-between gap-4 pt-1 border-t border-border">
          <span className="text-muted-foreground">Total:</span>
          <span className="font-medium">{data.trades} trades</span>
        </div>
      </div>
    </div>
  );
}

function getBarColor(winRate: number): string {
  if (winRate >= 60) return "#10B981"; // Green for good
  if (winRate >= 50) return "#3B82F6"; // Blue for okay
  if (winRate >= 40) return "#F59E0B"; // Yellow for warning
  return "#EF4444"; // Red for poor
}

// Custom tick component for X-axis
interface CustomXAxisTickProps {
  x?: number;
  y?: number;
  index?: number;
  payload?: { value: string | number };
  data: WinRateData[];
}

function CustomXAxisTick({ x, y, index, payload, data }: CustomXAxisTickProps) {
  if (x === undefined || y === undefined) return null;

  // Use index to get the name directly from data array
  // payload.value from Recharts can be unreliable (sometimes returns index)
  const idx = index ?? 0;
  const item = data[idx];
  const displayName = item?.name ?? String(payload?.value ?? idx);
  const truncatedName =
    displayName.length > 15
      ? displayName.substring(0, 13) + "..."
      : displayName;

  return (
    <g transform={`translate(${x},${y})`}>
      <text
        x={0}
        y={0}
        dy={10}
        textAnchor="end"
        fill="hsl(var(--muted-foreground))"
        fontSize={10}
        transform="rotate(-45)"
      >
        {truncatedName}
      </text>
    </g>
  );
}

// Custom tick component for Y-axis (vertical layout)
interface CustomYAxisTickProps {
  x?: number;
  y?: number;
  index?: number;
  payload?: { value: string | number };
  data: WinRateData[];
}

function CustomYAxisTick({ x, y, index, payload, data }: CustomYAxisTickProps) {
  if (x === undefined || y === undefined) return null;

  // Use index to get the name directly from data array
  const idx = index ?? 0;
  const item = data[idx];
  const displayName = item?.name ?? String(payload?.value ?? idx);
  const truncatedName =
    displayName.length > 20
      ? displayName.substring(0, 18) + "..."
      : displayName;

  return (
    <g transform={`translate(${x},${y})`}>
      <text
        x={-5}
        y={0}
        dy={4}
        textAnchor="end"
        fill="hsl(var(--muted-foreground))"
        fontSize={11}
      >
        {truncatedName}
      </text>
    </g>
  );
}

export function WinRateChart({
  data,
  height = 300,
  showLegend = false,
  showLabels = true,
  className,
  layout = "horizontal",
}: WinRateChartProps) {
  if (!data || data.length === 0) {
    return (
      <div
        className={cn(
          "flex items-center justify-center text-muted-foreground",
          className,
        )}
        style={{ height }}
      >
        <p className="text-sm">No data available</p>
      </div>
    );
  }

  const isVertical = layout === "vertical";

  return (
    <div className={cn("w-full", className)} style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={data}
          layout={isVertical ? "vertical" : "horizontal"}
          margin={{
            top: 20,
            right: 30,
            left: isVertical ? 120 : 20,
            bottom: isVertical ? 5 : 80,
          }}
        >
          <CartesianGrid
            strokeDasharray="3 3"
            stroke="hsl(var(--border))"
            horizontal={!isVertical}
            vertical={isVertical}
          />

          {isVertical ? (
            <>
              <XAxis
                type="number"
                domain={[0, 100]}
                tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 12 }}
                tickLine={{ stroke: "hsl(var(--border))" }}
                axisLine={{ stroke: "hsl(var(--border))" }}
                tickFormatter={(value) => `${value}%`}
              />
              <YAxis
                type="category"
                dataKey="name"
                tick={(props) => <CustomYAxisTick {...props} data={data} />}
                tickLine={{ stroke: "hsl(var(--border))" }}
                axisLine={{ stroke: "hsl(var(--border))" }}
                width={115}
              />
            </>
          ) : (
            <>
              <XAxis
                dataKey="name"
                tick={(props) => <CustomXAxisTick {...props} data={data} />}
                tickLine={{ stroke: "hsl(var(--border))" }}
                axisLine={{ stroke: "hsl(var(--border))" }}
                height={80}
                interval={0}
              />
              <YAxis
                domain={[0, 100]}
                tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 12 }}
                tickLine={{ stroke: "hsl(var(--border))" }}
                axisLine={{ stroke: "hsl(var(--border))" }}
                tickFormatter={(value) => `${value}%`}
              />
            </>
          )}

          <Tooltip
            content={<CustomTooltip />}
            cursor={{ fill: "hsl(var(--accent))", opacity: 0.3 }}
          />

          {showLegend && (
            <Legend
              wrapperStyle={{
                paddingTop: "10px",
              }}
            />
          )}

          <Bar
            dataKey="winRate"
            name="Win Rate"
            radius={[4, 4, 0, 0]}
            maxBarSize={60}
          >
            {data.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={getBarColor(entry.winRate)} />
            ))}
            {showLabels && (
              <LabelList
                dataKey="winRate"
                position={isVertical ? "right" : "top"}
                formatter={(value: number) => `${value.toFixed(0)}%`}
                fill="hsl(var(--foreground))"
                fontSize={11}
                fontWeight={500}
              />
            )}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

// Stacked version showing wins/losses
export interface StackedWinLossChartProps {
  data: WinRateData[];
  height?: number;
  showLegend?: boolean;
  className?: string;
  colors?: {
    win?: string;
    loss?: string;
  };
}

export function StackedWinLossChart({
  data,
  height = 300,
  showLegend = true,
  className,
  colors = defaultColors,
}: StackedWinLossChartProps) {
  if (!data || data.length === 0) {
    return (
      <div
        className={cn(
          "flex items-center justify-center text-muted-foreground",
          className,
        )}
        style={{ height }}
      >
        <p className="text-sm">No data available</p>
      </div>
    );
  }

  return (
    <div className={cn("w-full", className)} style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={data}
          margin={{ top: 20, right: 30, left: 20, bottom: 80 }}
        >
          <CartesianGrid
            strokeDasharray="3 3"
            stroke="hsl(var(--border))"
            vertical={false}
          />
          <XAxis
            dataKey="name"
            tick={(props) => <CustomXAxisTick {...props} data={data} />}
            tickLine={{ stroke: "hsl(var(--border))" }}
            axisLine={{ stroke: "hsl(var(--border))" }}
            height={80}
            interval={0}
          />
          <YAxis
            tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 12 }}
            tickLine={{ stroke: "hsl(var(--border))" }}
            axisLine={{ stroke: "hsl(var(--border))" }}
          />
          <Tooltip
            content={<CustomTooltip />}
            cursor={{ fill: "hsl(var(--accent))", opacity: 0.3 }}
          />
          {showLegend && (
            <Legend
              wrapperStyle={{ paddingTop: "10px" }}
              formatter={(value) => (
                <span className="text-sm text-foreground">{value}</span>
              )}
            />
          )}
          <Bar
            dataKey="wins"
            name="Wins"
            stackId="trades"
            fill={colors.win}
            radius={[0, 0, 0, 0]}
          />
          <Bar
            dataKey="losses"
            name="Losses"
            stackId="trades"
            fill={colors.loss}
            radius={[4, 4, 0, 0]}
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export default WinRateChart;
