"use client";

import React from "react";
import { Activity, TrendingUp, TrendingDown } from "lucide-react";

interface StreakData {
  currentStreak: number;
  currentStreakType: "win" | "loss" | "none";
  maxWinStreak: number;
  maxLossStreak: number;
  avgWinStreak: number;
  avgLossStreak: number;
}

interface StreakChartProps {
  data: StreakData | null;
  height?: number;
}

interface StatCardProps {
  label: string;
  value: number | string;
  icon: React.ReactNode;
  color: "green" | "red" | "neutral";
  subLabel?: string;
}

function StatCard({ label, value, icon, color, subLabel }: StatCardProps) {
  const colorClasses = {
    green: "text-green-500 bg-green-500/10 border-green-500/20",
    red: "text-red-500 bg-red-500/10 border-red-500/20",
    neutral: "text-muted-foreground bg-muted/50 border-border",
  };

  const textColorClasses = {
    green: "text-green-500",
    red: "text-red-500",
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

function StreakBar({
  value,
  maxValue,
  color,
  label,
}: {
  value: number;
  maxValue: number;
  color: "green" | "red";
  label: string;
}) {
  const percentage = maxValue > 0 ? (value / maxValue) * 100 : 0;
  const bgColor = color === "green" ? "bg-green-500" : "bg-red-500";

  return (
    <div className="flex items-center gap-3">
      <span className="text-sm text-muted-foreground w-24">{label}</span>
      <div className="flex-1 h-6 bg-muted rounded-full overflow-hidden">
        <div
          className={`h-full ${bgColor} rounded-full transition-all duration-500`}
          style={{ width: `${Math.min(percentage, 100)}%` }}
        />
      </div>
      <span className="text-sm font-medium w-8 text-right">{value}</span>
    </div>
  );
}

export function StreakChart({ data, height = 300 }: StreakChartProps) {
  if (!data) {
    return (
      <div
        className="flex items-center justify-center text-muted-foreground"
        style={{ height }}
      >
        <div className="text-center">
          <Activity className="h-12 w-12 mx-auto mb-2 opacity-50" />
          <p>No streak data available</p>
        </div>
      </div>
    );
  }

  const {
    currentStreak,
    currentStreakType,
    maxWinStreak,
    maxLossStreak,
    avgWinStreak,
    avgLossStreak,
  } = data;

  const isWinning = currentStreakType === "win";
  const isLosing = currentStreakType === "loss";
  const maxStreak = Math.max(maxWinStreak, maxLossStreak, 1);

  return (
    <div className="space-y-6" style={{ minHeight: height }}>
      {/* Current Streak */}
      <div className="flex justify-center">
        <div
          className={`flex flex-col items-center p-6 rounded-xl border-2 ${
            isWinning
              ? "border-green-500/50 bg-green-500/5"
              : isLosing
                ? "border-red-500/50 bg-red-500/5"
                : "border-border bg-muted/20"
          }`}
        >
          <div className="flex items-center gap-2 mb-2">
            {isWinning ? (
              <TrendingUp className="h-5 w-5 text-green-500" />
            ) : isLosing ? (
              <TrendingDown className="h-5 w-5 text-red-500" />
            ) : (
              <Activity className="h-5 w-5 text-muted-foreground" />
            )}
            <span className="text-sm font-medium text-muted-foreground">
              Current Streak
            </span>
          </div>
          <span
            className={`text-4xl font-bold ${
              isWinning
                ? "text-green-500"
                : isLosing
                  ? "text-red-500"
                  : "text-muted-foreground"
            }`}
          >
            {currentStreak}
          </span>
          <span className="text-sm text-muted-foreground mt-1 capitalize">
            {currentStreakType === "none"
              ? "No trades"
              : `${currentStreakType}${currentStreak !== 1 ? "s" : ""}`}
          </span>
        </div>
      </div>

      {/* Streak Comparison Bars */}
      <div className="space-y-3 px-4">
        <StreakBar
          value={maxWinStreak}
          maxValue={maxStreak}
          color="green"
          label="Max Win"
        />
        <StreakBar
          value={maxLossStreak}
          maxValue={maxStreak}
          color="red"
          label="Max Loss"
        />
      </div>

      {/* Statistics Grid */}
      <div className="grid grid-cols-2 gap-3 px-4">
        <StatCard
          label="Max Win Streak"
          value={maxWinStreak}
          icon={<TrendingUp className="h-4 w-4 text-green-500" />}
          color="green"
        />
        <StatCard
          label="Max Loss Streak"
          value={maxLossStreak}
          icon={<TrendingDown className="h-4 w-4 text-red-500" />}
          color="red"
        />
        <StatCard
          label="Avg Win Streak"
          value={avgWinStreak.toFixed(1)}
          icon={<Activity className="h-4 w-4 text-green-500" />}
          color="neutral"
          subLabel="trades"
        />
        <StatCard
          label="Avg Loss Streak"
          value={avgLossStreak.toFixed(1)}
          icon={<Activity className="h-4 w-4 text-red-500" />}
          color="neutral"
          subLabel="trades"
        />
      </div>
    </div>
  );
}

export default StreakChart;
