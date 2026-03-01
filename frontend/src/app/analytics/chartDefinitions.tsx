"use client";

import * as React from "react";
import {
  TrendingUp,
  DollarSign,
  Calendar,
  Target,
  PieChart,
  BarChart3,
  LineChart,
  Activity,
  Clock,
  Wallet,
} from "lucide-react";

import { BalanceChart } from "@/components/charts/BalanceChart";
import { MonthlyPnLChart } from "@/components/charts/MonthlyPnLChart";
import { WinRateChart } from "@/components/charts/WinRateChart";
import { MultiAccountCumulativePnLChart } from "@/components/charts/MultiAccountCumulativePnLChart";
import { DailyPnLChart } from "@/components/charts/DailyPnLChart";
import { HourlyPerformanceChart } from "@/components/charts/HourlyPerformanceChart";
import { WeekdayPerformanceChart } from "@/components/charts/WeekdayPerformanceChart";
import { StreakChart } from "@/components/charts/StreakChart";
import { TradeDurationChart } from "@/components/charts/TradeDurationChart";
import { CumulativePnLChart } from "@/components/charts/CumulativePnLChart";
import { PositionSizeChart } from "@/components/charts/PositionSizeChart";
import { FundingChart } from "@/components/charts/FundingChart";
import { SpreadCostChart } from "@/components/charts/SpreadCostChart";
import { TradeFrequencyChart } from "@/components/charts/TradeFrequencyChart";
import { PointsChart } from "@/components/charts/PointsChart";
import type { UseAnalyticsDataReturn } from "@/hooks/analytics";

// ============================================================================
// Types
// ============================================================================

export type ChartCategory =
  | "all"
  | "pnl"
  | "performance"
  | "time"
  | "instruments"
  | "risk";

export interface ChartDefinition {
  id: string;
  title: string;
  description: string;
  category: ChartCategory;
  icon: React.ElementType;
  component: React.ReactNode;
}

export interface CategoryDefinition {
  value: ChartCategory;
  label: string;
  icon: React.ElementType;
}

// ============================================================================
// Categories
// ============================================================================

export const CHART_CATEGORIES: CategoryDefinition[] = [
  { value: "all", label: "All Charts", icon: BarChart3 },
  { value: "pnl", label: "P&L", icon: DollarSign },
  { value: "performance", label: "Performance", icon: Target },
  { value: "time", label: "Time Analysis", icon: Clock },
  { value: "instruments", label: "Instruments", icon: PieChart },
  { value: "risk", label: "Risk", icon: Activity },
];

// ============================================================================
// Currency Not Set Placeholder
// ============================================================================

function CurrencyNotSetPlaceholder() {
  return (
    <div className="flex items-center justify-center h-[300px] text-muted-foreground">
      Please set your default currency in Settings
    </div>
  );
}

// ============================================================================
// Chart Definitions Builder
// ============================================================================

export function buildChartDefinitions(
  data: UseAnalyticsDataReturn,
  formattedBalanceData: Array<{ date: string; balance: number }>,
): ChartDefinition[] {
  const {
    dailyPnL,
    dailyPnLByAccount,
    monthlyPnL,
    equityCurve,
    balanceHistory,
    winRateByInstrument,
    hourlyPerformance,
    weekdayPerformance,
    streakData,
    tradeFrequencyData,
    tradeDuration,
    positionSizeData,
    pointsByInstrument,
    fundingData,
    spreadCostData,
    displayCurrency,
    currencyNotSet,
    formatAmount,
  } = data;

  return [
    {
      id: "dailyPnL",
      title: "Daily P&L",
      description: "Daily profit and loss with percentage returns",
      category: "pnl",
      icon: BarChart3,
      component: currencyNotSet ? (
        <CurrencyNotSetPlaceholder />
      ) : (
        <DailyPnLChart
          data={dailyPnL}
          height={300}
          currency={displayCurrency}
        />
      ),
    },
    {
      id: "cumulativePnL",
      title: "Cumulative P&L",
      description: "Running total of profits and losses over time",
      category: "pnl",
      icon: LineChart,
      component: currencyNotSet ? (
        <CurrencyNotSetPlaceholder />
      ) : dailyPnLByAccount &&
        dailyPnLByAccount.series.length > 1 ? (
        <MultiAccountCumulativePnLChart
          series={dailyPnLByAccount.series}
          total={dailyPnLByAccount.total}
          height={300}
          showLegend={true}
        />
      ) : (
        <CumulativePnLChart
          data={dailyPnL}
          height={300}
          currency={displayCurrency}
        />
      ),
    },
    {
      id: "monthlyPnL",
      title: "Monthly P&L",
      description: "Monthly breakdown of trading performance",
      category: "pnl",
      icon: Calendar,
      component: currencyNotSet ? (
        <CurrencyNotSetPlaceholder />
      ) : (
        <MonthlyPnLChart
          data={monthlyPnL}
          height={300}
          currency={displayCurrency}
        />
      ),
    },
    {
      id: "equityCurve",
      title: "Equity Curve",
      description:
        "Account equity over time (P/L only, excludes deposits/withdrawals)",
      category: "pnl",
      icon: TrendingUp,
      component: currencyNotSet ? (
        <CurrencyNotSetPlaceholder />
      ) : (
        <BalanceChart
          data={equityCurve.map((p) => ({
            date: new Date(p.date).toLocaleDateString("en-US", {
              month: "short",
              day: "numeric",
            }),
            balance: p.balance,
          }))}
          height={300}
          currency={displayCurrency}
        />
      ),
    },
    {
      id: "balanceHistory",
      title: "Balance History",
      description: "Account balance over time (includes funding)",
      category: "pnl",
      icon: Wallet,
      component: currencyNotSet ? (
        <CurrencyNotSetPlaceholder />
      ) : (
        <BalanceChart
          data={formattedBalanceData}
          height={300}
          showDrawdown={true}
          currency={displayCurrency}
        />
      ),
    },
    {
      id: "funding",
      title: "Funding Activity",
      description:
        "Track deposits, withdrawals, and their impact on account balance",
      category: "pnl",
      icon: DollarSign,
      component: currencyNotSet ? (
        <CurrencyNotSetPlaceholder />
      ) : (
        <FundingChart
          data={fundingData.daily}
          chargesByMarket={fundingData.charges_by_market}
          height={300}
          currency={displayCurrency}
        />
      ),
    },
    {
      id: "winRate",
      title: "Win Rate by Instrument",
      description: "Win rate breakdown across different instruments",
      category: "instruments",
      icon: Target,
      component: <WinRateChart data={winRateByInstrument} height={300} />,
    },
    {
      id: "hourly",
      title: "Hourly Performance",
      description: "Performance breakdown by hour of day",
      category: "time",
      icon: Clock,
      component: currencyNotSet ? (
        <CurrencyNotSetPlaceholder />
      ) : (
        <HourlyPerformanceChart
          data={hourlyPerformance}
          height={300}
          currency={displayCurrency}
        />
      ),
    },
    {
      id: "weekday",
      title: "Weekday Performance",
      description: "Performance breakdown by day of week",
      category: "time",
      icon: Calendar,
      component: currencyNotSet ? (
        <CurrencyNotSetPlaceholder />
      ) : (
        <WeekdayPerformanceChart
          data={weekdayPerformance}
          height={300}
          currency={displayCurrency}
        />
      ),
    },
    {
      id: "streaks",
      title: "Win/Loss Streaks",
      description: "Current and historical winning/losing streaks",
      category: "performance",
      icon: Activity,
      component: <StreakChart data={streakData} height={300} />,
    },
    {
      id: "tradeFrequency",
      title: "Trade Frequency",
      description: "Daily, monthly, and yearly trade counts with averages",
      category: "performance",
      icon: BarChart3,
      component: (
        <TradeFrequencyChart
          data={tradeFrequencyData}
          height={300}
          showByAccount={true}
        />
      ),
    },
    {
      id: "duration",
      title: "Trade Duration Analysis",
      description: "Performance by trade holding time",
      category: "time",
      icon: Clock,
      component: <TradeDurationChart data={tradeDuration} height={300} />,
    },
    {
      id: "positionSize",
      title: "Position Size Analysis",
      description: "Performance by position size",
      category: "risk",
      icon: BarChart3,
      component: currencyNotSet ? (
        <CurrencyNotSetPlaceholder />
      ) : (
        <PositionSizeChart
          data={positionSizeData}
          height={300}
          currency={displayCurrency}
        />
      ),
    },
    {
      id: "points",
      title: "Points by Instrument",
      description: "Total points/pips gained or lost per instrument",
      category: "instruments",
      icon: Target,
      component: (
        <PointsChart
          data={pointsByInstrument}
          height={300}
          currency={displayCurrency}
          formatAmount={formatAmount}
        />
      ),
    },
    {
      id: "spreadCost",
      title: "Spread Cost Analysis",
      description: "Monthly breakdown of spread costs paid per trade",
      category: "risk",
      icon: DollarSign,
      component: currencyNotSet ? (
        <CurrencyNotSetPlaceholder />
      ) : (
        <SpreadCostChart
          data={spreadCostData?.monthly || []}
          byInstrument={spreadCostData?.by_instrument || []}
          totalSpreadCost={spreadCostData?.total_spread_cost || 0}
          totalTrades={spreadCostData?.total_trades || 0}
          avgSpreadPerTrade={spreadCostData?.avg_spread_per_trade || 0}
          height={300}
          currency={displayCurrency}
        />
      ),
    },
  ];
}
