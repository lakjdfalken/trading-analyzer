"use client";

import * as React from "react";
import { BarChart3, RefreshCw } from "lucide-react";

import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ChartCard } from "@/components/charts/ChartCard";
import { ExpandedChartModal } from "@/components/charts/ExpandedChartModal";
import { DateRangePicker } from "@/components/filters/DateRangePicker";
import type { DateRangePreset } from "@/components/filters/types";
import { useAnalyticsData } from "@/hooks/analytics";
import {
  buildChartDefinitions,
  CHART_CATEGORIES,
  type ChartCategory,
} from "./chartDefinitions";

export default function AnalyticsPage() {
  const [selectedCategory, setSelectedCategory] =
    React.useState<ChartCategory>("all");
  const [expandedChart, setExpandedChart] = React.useState<string | null>(null);

  const data = useAnalyticsData();

  const {
    dateRange,
    balanceHistory,
    loading,
    selectedAccountId,
    availableAccounts,
    displayCurrency,
    fetchData,
    setSelectedAccountId,
    setDateRange,
  } = data;

  // Format balance data for chart
  const formattedBalanceData = React.useMemo(() => {
    return balanceHistory.map((point) => ({
      date: new Date(point.date).toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
      }),
      balance: point.balance,
    }));
  }, [balanceHistory]);

  // Build chart definitions from data
  const charts = React.useMemo(
    () => buildChartDefinitions(data, formattedBalanceData),
    [data, formattedBalanceData],
  );

  // Filter charts by category
  const filteredCharts =
    selectedCategory === "all"
      ? charts
      : charts.filter((chart) => chart.category === selectedCategory);

  // Handle account change
  const handleAccountChange = React.useCallback(
    (accountId: number | null) => {
      setSelectedAccountId(accountId);
    },
    [setSelectedAccountId],
  );

  // Handle date range change
  const handleDateRangeChange = React.useCallback(
    (newRange: {
      from: Date | undefined;
      to: Date | undefined;
      preset?: DateRangePreset;
    }) => {
      setDateRange({
        from: newRange.from,
        to: newRange.to,
        preset: newRange.preset || "custom",
      });
    },
    [setDateRange],
  );

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border bg-card/50 backdrop-blur-sm sticky top-0 z-40">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold tracking-tight">Analytics</h1>
              <p className="text-sm text-muted-foreground">
                Detailed trading analysis and insights
              </p>
            </div>

            <div className="flex items-center gap-4">
              {/* Date Range Picker */}
              <DateRangePicker
                dateRange={{
                  from: dateRange.from,
                  to: dateRange.to,
                  preset: dateRange.preset as DateRangePreset,
                }}
                onDateRangeChange={handleDateRangeChange}
              />

              {/* Account Filter */}
              {availableAccounts.length > 0 && (
                <select
                  value={selectedAccountId ?? ""}
                  onChange={(e) =>
                    handleAccountChange(
                      e.target.value ? parseInt(e.target.value, 10) : null,
                    )
                  }
                  className="px-3 py-2 rounded-md text-sm font-medium bg-secondary text-secondary-foreground border border-border"
                >
                  <option value="">All Accounts (converted)</option>
                  {availableAccounts.map((account) => (
                    <option key={account.account_id} value={account.account_id}>
                      {account.account_name || `Account ${account.account_id}`}
                      {account.currency ? ` (${account.currency})` : ""}
                    </option>
                  ))}
                </select>
              )}

              {/* Refresh Button */}
              <Button
                variant="outline"
                size="sm"
                onClick={fetchData}
                disabled={loading.dashboard}
                className="flex items-center gap-2"
              >
                <RefreshCw
                  className={cn("h-4 w-4", loading.dashboard && "animate-spin")}
                />
                Refresh
              </Button>
            </div>
          </div>

          {/* Category Filter */}
          <div className="mt-4 flex gap-2 overflow-x-auto pb-2">
            {CHART_CATEGORIES.map((category) => {
              const Icon = category.icon;
              const isActive = selectedCategory === category.value;
              const count =
                category.value === "all"
                  ? charts.length
                  : charts.filter((c) => c.category === category.value).length;

              return (
                <Button
                  key={category.value}
                  variant={isActive ? "default" : "outline"}
                  size="sm"
                  onClick={() => setSelectedCategory(category.value)}
                  className={cn(
                    "flex items-center gap-2 whitespace-nowrap",
                    isActive && "bg-primary text-primary-foreground",
                  )}
                >
                  <Icon className="h-4 w-4" />
                  {category.label}
                  <Badge
                    variant={isActive ? "secondary" : "outline"}
                    className="ml-1 h-5 px-1.5 text-xs"
                  >
                    {count}
                  </Badge>
                </Button>
              );
            })}
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {filteredCharts.map((chart) => {
            return (
              <ChartCard
                key={chart.id}
                title={chart.title}
                subtitle={chart.description}
                onExpand={() => setExpandedChart(chart.id)}
              >
                {chart.component}
              </ChartCard>
            );
          })}
        </div>

        {filteredCharts.length === 0 && (
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <BarChart3 className="h-12 w-12 text-muted-foreground mb-4" />
            <h3 className="text-lg font-medium">No charts in this category</h3>
            <p className="text-muted-foreground mt-1">
              Select a different category to view charts
            </p>
          </div>
        )}
      </main>

      {/* Expanded Chart Modals */}
      {charts.map((chart) => (
        <ExpandedChartModal
          key={chart.id}
          isOpen={expandedChart === chart.id}
          onClose={() => setExpandedChart(null)}
          title={chart.title}
          subtitle={chart.description}
        >
          {React.cloneElement(chart.component as React.ReactElement, {
            height: 500,
          })}
        </ExpandedChartModal>
      ))}
    </div>
  );
}
