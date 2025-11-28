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
  LabelList,
} from "recharts";
import { cn } from "@/lib/utils";

export interface PointsData {
  name: string;
  totalPoints: number;
  winPoints: number;
  lossPoints: number;
  trades: number;
  wins: number;
  losses: number;
  avgPointsPerTrade: number;
  avgWinPoints: number;
  avgLossPoints: number;
  multiplier: number;
}

export interface PointsChartProps {
  data: PointsData[];
  height?: number;
  showLabels?: boolean;
  className?: string;
  layout?: "horizontal" | "vertical";
  metric?: "totalPoints" | "avgPointsPerTrade";
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: Array<{
    name: string;
    value: number;
    payload: PointsData;
  }>;
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
          <span className="text-muted-foreground">Total Points:</span>
          <span
            className={cn(
              "font-medium",
              data.totalPoints >= 0 ? "text-green-500" : "text-red-500"
            )}
          >
            {data.totalPoints.toFixed(1)}
          </span>
        </div>
        <div className="flex items-center justify-between gap-4">
          <span className="text-muted-foreground">Avg/Trade:</span>
          <span
            className={cn(
              "font-medium",
              data.avgPointsPerTrade >= 0 ? "text-green-500" : "text-red-500"
            )}
          >
            {data.avgPointsPerTrade.toFixed(2)}
          </span>
        </div>
        <div className="flex items-center justify-between gap-4">
          <span className="text-green-500">Win Points:</span>
          <span className="font-medium">{data.winPoints.toFixed(1)}</span>
        </div>
        <div className="flex items-center justify-between gap-4">
          <span className="text-red-500">Loss Points:</span>
          <span className="font-medium">{data.lossPoints.toFixed(1)}</span>
        </div>
        <div className="flex items-center justify-between gap-4 pt-1 border-t border-border">
          <span className="text-muted-foreground">Trades:</span>
          <span className="font-medium">
            {data.trades} ({data.wins}W / {data.losses}L)
          </span>
        </div>
      </div>
    </div>
  );
}

function getBarColor(value: number): string {
  if (value >= 100) return "#10B981"; // Green for strong positive
  if (value >= 0) return "#3B82F6"; // Blue for positive
  if (value >= -50) return "#F59E0B"; // Yellow for slight negative
  return "#EF4444"; // Red for negative
}

// Custom tick component for X-axis
interface CustomXAxisTickProps {
  x?: number;
  y?: number;
  index?: number;
  payload?: { value: string | number };
  data: PointsData[];
}

function CustomXAxisTick({ x, y, index, payload, data }: CustomXAxisTickProps) {
  if (x === undefined || y === undefined) return null;

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
  data: PointsData[];
}

function CustomYAxisTick({ x, y, index, payload, data }: CustomYAxisTickProps) {
  if (x === undefined || y === undefined) return null;

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

export function PointsChart({
  data,
  height = 300,
  showLabels = true,
  className,
  layout = "horizontal",
  metric = "totalPoints",
}: PointsChartProps) {
  if (!data || data.length === 0) {
    return (
      <div
        className={cn(
          "flex items-center justify-center text-muted-foreground",
          className
        )}
        style={{ height }}
      >
        <p className="text-sm">No points data available</p>
      </div>
    );
  }

  const isVertical = layout === "vertical";
  const dataKey = metric;

  // Calculate domain to include negative values
  const values = data.map((d) => d[dataKey]);
  const minValue = Math.min(0, ...values);
  const maxValue = Math.max(0, ...values);
  const padding = Math.abs(maxValue - minValue) * 0.1;

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
                domain={[minValue - padding, maxValue + padding]}
                tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 12 }}
                tickLine={{ stroke: "hsl(var(--border))" }}
                axisLine={{ stroke: "hsl(var(--border))" }}
                tickFormatter={(value) => value.toFixed(0)}
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
                domain={[minValue - padding, maxValue + padding]}
                tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 12 }}
                tickLine={{ stroke: "hsl(var(--border))" }}
                axisLine={{ stroke: "hsl(var(--border))" }}
                tickFormatter={(value) => value.toFixed(0)}
              />
            </>
          )}

          <Tooltip
            content={<CustomTooltip />}
            cursor={{ fill: "hsl(var(--accent))", opacity: 0.3 }}
          />

          <Bar
            dataKey={dataKey}
            name={metric === "totalPoints" ? "Total Points" : "Avg Points/Trade"}
            radius={[4, 4, 0, 0]}
            maxBarSize={60}
          >
            {data.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={getBarColor(entry[dataKey])} />
            ))}
            {showLabels && (
              <LabelList
                dataKey={dataKey}
                position={isVertical ? "right" : "top"}
                formatter={(value: number) => value.toFixed(0)}
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

export default PointsChart;
