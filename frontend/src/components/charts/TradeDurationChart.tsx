"use client";

import React from "react";
import { Clock, TrendingUp, TrendingDown, Timer } from "lucide-react";

interface TradeDurationStats {
  avgDurationMinutes: number;
  minDurationMinutes: number;
  maxDurationMinutes: number;
  avgWinnerDuration: number;
  avgLoserDuration: number;
}

interface TradeDurationChartProps {
  data: TradeDurationStats | null;
  height?: number;
}

interface StatCardProps {
  label: string;
  value: string;
  icon: React.ReactNode;
  color: "green" | "red" | "blue" | "neutral";
  subLabel?: string;
}

function formatDuration(minutes: number): string {
  if (minutes < 1) {
    return "< 1m";
  }
  if (minutes < 60) {
    return `${Math.round(minutes)}m`;
  }
  if (minutes < 1440) {
    // Less than a day
    const hours = Math.floor(minutes / 60);
    const mins = Math.round(minutes % 60);
    return mins > 0 ? `${hours}h ${mins}m` : `${hours}h`;
  }
  const days = Math.floor(minutes / 1440);
  const hours = Math.floor((minutes % 1440) / 60);
  return hours > 0 ? `${days}d ${hours}h` : `${days}d`;
}

function StatCard({ label, value, icon, color, subLabel }: StatCardProps) {
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
      className={`flex flex-col items-center justify-center p-4 rounded-lg border ${colorClasses[color]}`}
    >
      <div className="flex items-center gap-2 mb-1">
        {icon}
        <span className="text-sm text-muted-foreground">{label}</span>
      </div>
      <span className={`text-2xl font-bold ${textColorClasses[color]}`}>
        {value}
      </span>
      {subLabel && (
        <span className="text-xs text-muted-foreground mt-1">{subLabel}</span>
      )}
    </div>
  );
}

function DurationBar({
  value,
  maxValue,
  color,
  label,
}: {
  value: number;
  maxValue: number;
  color: "green" | "red" | "blue";
  label: string;
}) {
  const percentage = maxValue > 0 ? (value / maxValue) * 100 : 0;
  const bgColors = {
    green: "bg-green-500",
    red: "bg-red-500",
    blue: "bg-blue-500",
  };

  return (
    <div className="flex items-center gap-3">
      <span className="text-sm text-muted-foreground w-28">{label}</span>
      <div className="flex-1 h-6 bg-muted rounded-full overflow-hidden">
        <div
          className={`h-full ${bgColors[color]} rounded-full transition-all duration-500`}
          style={{ width: `${Math.min(percentage, 100)}%` }}
        />
      </div>
      <span className="text-sm font-medium w-16 text-right">
        {formatDuration(value)}
      </span>
    </div>
  );
}

export function TradeDurationChart({
  data,
  height = 300,
}: TradeDurationChartProps) {
  if (!data) {
    return (
      <div
        className="flex items-center justify-center text-muted-foreground"
        style={{ height }}
      >
        <div className="text-center">
          <Clock className="h-12 w-12 mx-auto mb-2 opacity-50" />
          <p>No trade duration data available</p>
        </div>
      </div>
    );
  }

  const {
    avgDurationMinutes,
    minDurationMinutes,
    maxDurationMinutes,
    avgWinnerDuration,
    avgLoserDuration,
  } = data;

  const maxDuration = Math.max(
    maxDurationMinutes,
    avgWinnerDuration,
    avgLoserDuration,
    1
  );

  // Determine if winners or losers are held longer
  const winnerVsLoser =
    avgWinnerDuration > avgLoserDuration
      ? "Winners held longer"
      : avgLoserDuration > avgWinnerDuration
        ? "Losers held longer"
        : "Similar hold times";

  return (
    <div className="space-y-6" style={{ minHeight: height }}>
      {/* Average Duration Highlight */}
      <div className="flex justify-center">
        <div className="flex flex-col items-center p-6 rounded-xl border-2 border-blue-500/50 bg-blue-500/5">
          <div className="flex items-center gap-2 mb-2">
            <Timer className="h-5 w-5 text-blue-500" />
            <span className="text-sm font-medium text-muted-foreground">
              Average Duration
            </span>
          </div>
          <span className="text-4xl font-bold text-blue-500">
            {formatDuration(avgDurationMinutes)}
          </span>
          <span className="text-sm text-muted-foreground mt-1">
            {winnerVsLoser}
          </span>
        </div>
      </div>

      {/* Duration Comparison Bars */}
      <div className="space-y-3 px-4">
        <DurationBar
          value={avgWinnerDuration}
          maxValue={maxDuration}
          color="green"
          label="Avg Winner"
        />
        <DurationBar
          value={avgLoserDuration}
          maxValue={maxDuration}
          color="red"
          label="Avg Loser"
        />
        <DurationBar
          value={maxDurationMinutes}
          maxValue={maxDuration}
          color="blue"
          label="Max Duration"
        />
      </div>

      {/* Statistics Grid */}
      <div className="grid grid-cols-2 gap-3 px-4">
        <StatCard
          label="Avg Winner Hold"
          value={formatDuration(avgWinnerDuration)}
          icon={<TrendingUp className="h-4 w-4 text-green-500" />}
          color="green"
        />
        <StatCard
          label="Avg Loser Hold"
          value={formatDuration(avgLoserDuration)}
          icon={<TrendingDown className="h-4 w-4 text-red-500" />}
          color="red"
        />
        <StatCard
          label="Shortest Trade"
          value={formatDuration(minDurationMinutes)}
          icon={<Clock className="h-4 w-4 text-muted-foreground" />}
          color="neutral"
        />
        <StatCard
          label="Longest Trade"
          value={formatDuration(maxDurationMinutes)}
          icon={<Clock className="h-4 w-4 text-blue-500" />}
          color="blue"
        />
      </div>
    </div>
  );
}

export default TradeDurationChart;
