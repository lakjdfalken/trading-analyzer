"use client";

import * as React from "react";
import { format, isValid } from "date-fns";
import {
  ArrowUpRight,
  ArrowDownRight,
  TrendingUp,
  TrendingDown,
  MoreHorizontal,
} from "lucide-react";
import { cn, getProfitLossColor } from "@/lib/utils";
import { useCurrencyStore } from "@/store/currency";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

export interface Trade {
  id: string;
  instrument: string;
  direction: "long" | "short";
  entryPrice: number;
  exitPrice: number;
  entryTime: Date;
  exitTime: Date;
  quantity: number;
  pnl: number;
  pnlPercent: number;
  commission?: number;
  notes?: string;
  tags?: string[];
  currency?: string;
}

export interface RecentTradesListProps {
  trades: Trade[];
  maxItems?: number;
  showHeader?: boolean;
  title?: string;
  onTradeClick?: (trade: Trade) => void;
  onViewAll?: () => void;
  loading?: boolean;
  className?: string;
}

function TradeRow({
  trade,
  onClick,
}: {
  trade: Trade;
  onClick?: (trade: Trade) => void;
}) {
  const isProfit = trade.pnl >= 0;
  const isLong = trade.direction === "long";
  const { formatAmount } = useCurrencyStore();

  return (
    <div
      onClick={() => onClick?.(trade)}
      className={cn(
        "flex items-center justify-between p-3 rounded-lg transition-colors",
        "hover:bg-accent/50 cursor-pointer",
        "border-b border-border last:border-b-0",
      )}
    >
      <div className="flex items-center gap-3">
        {/* Direction Icon */}
        <div
          className={cn(
            "flex items-center justify-center w-8 h-8 rounded-full",
            isLong ? "bg-green-500/10" : "bg-red-500/10",
          )}
        >
          {isLong ? (
            <ArrowUpRight className="h-4 w-4 text-green-500" />
          ) : (
            <ArrowDownRight className="h-4 w-4 text-red-500" />
          )}
        </div>

        {/* Trade Details */}
        <div className="flex flex-col">
          <div className="flex items-center gap-2">
            <span className="font-medium text-sm">{trade.instrument}</span>
            <Badge
              variant={isLong ? "success" : "danger"}
              className="text-[10px] px-1.5 py-0"
            >
              {isLong ? "LONG" : "SHORT"}
            </Badge>
          </div>
          <span className="text-xs text-muted-foreground">
            {trade.exitTime && isValid(trade.exitTime)
              ? format(trade.exitTime, "MMM d, HH:mm")
              : "—"}
          </span>
        </div>
      </div>

      {/* P&L */}
      <div className="flex flex-col items-end">
        <span
          className={cn(
            "font-semibold text-sm",
            getProfitLossColor(trade.pnl ?? 0),
          )}
        >
          {(trade.pnl ?? 0) >= 0 ? "+" : ""}
          {trade.currency
            ? formatAmount(trade.pnl ?? 0, trade.currency)
            : (trade.pnl ?? 0).toFixed(2)}
        </span>
        <span
          className={cn(
            "text-xs flex items-center gap-0.5",
            getProfitLossColor(trade.pnlPercent ?? 0),
          )}
        >
          {isProfit ? (
            <TrendingUp className="h-3 w-3" />
          ) : (
            <TrendingDown className="h-3 w-3" />
          )}
          {(trade.pnlPercent ?? 0) >= 0 ? "+" : ""}
          {(trade.pnlPercent ?? 0).toFixed(2)}%
        </span>
      </div>
    </div>
  );
}

function LoadingSkeleton() {
  return (
    <div className="space-y-2">
      {[...Array(5)].map((_, i) => (
        <div
          key={i}
          className="flex items-center justify-between p-3 rounded-lg animate-pulse"
        >
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-muted" />
            <div className="space-y-2">
              <div className="h-4 w-20 bg-muted rounded" />
              <div className="h-3 w-16 bg-muted rounded" />
            </div>
          </div>
          <div className="space-y-2">
            <div className="h-4 w-16 bg-muted rounded" />
            <div className="h-3 w-12 bg-muted rounded ml-auto" />
          </div>
        </div>
      ))}
    </div>
  );
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center py-8 text-center">
      <div className="w-12 h-12 rounded-full bg-muted flex items-center justify-center mb-3">
        <TrendingUp className="h-6 w-6 text-muted-foreground" />
      </div>
      <p className="text-sm font-medium">No trades yet</p>
      <p className="text-xs text-muted-foreground mt-1">
        Your recent trades will appear here
      </p>
    </div>
  );
}

export function RecentTradesList({
  trades,
  maxItems = 10,
  showHeader = true,
  title = "Recent Trades",
  onTradeClick,
  onViewAll,
  loading = false,
  className,
}: RecentTradesListProps) {
  const displayedTrades = trades.slice(0, maxItems);
  const hasMoreTrades = trades.length > maxItems;
  const { formatAmount } = useCurrencyStore();

  // Calculate summary stats
  const totalPnl = displayedTrades.reduce((sum, t) => sum + t.pnl, 0);
  const winCount = displayedTrades.filter((t) => t.pnl > 0).length;
  const winRate =
    displayedTrades.length > 0
      ? ((winCount / displayedTrades.length) * 100).toFixed(0)
      : "0";

  // Get the most common currency for summary display
  const currencyCounts = displayedTrades.reduce(
    (acc, t) => {
      const curr = t.currency;
      if (curr) {
        acc[curr] = (acc[curr] || 0) + 1;
      }
      return acc;
    },
    {} as Record<string, number>,
  );
  const summaryCurrency =
    Object.entries(currencyCounts).sort((a, b) => b[1] - a[1])[0]?.[0] || null;

  return (
    <Card className={className}>
      {showHeader && (
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <div>
            <CardTitle className="text-base font-semibold">{title}</CardTitle>
            {!loading && displayedTrades.length > 0 && (
              <p className="text-xs text-muted-foreground mt-1">
                {displayedTrades.length} trades •{" "}
                <span className={getProfitLossColor(totalPnl)}>
                  {totalPnl >= 0 ? "+" : ""}
                  {summaryCurrency
                    ? formatAmount(totalPnl, summaryCurrency)
                    : totalPnl.toFixed(2)}
                </span>{" "}
                • {winRate}% win rate
              </p>
            )}
          </div>
          {onViewAll && !loading && trades.length > 0 && (
            <Button variant="ghost" size="sm" onClick={onViewAll}>
              View all
              <MoreHorizontal className="ml-1 h-4 w-4" />
            </Button>
          )}
        </CardHeader>
      )}

      <CardContent className={cn(!showHeader && "pt-6")}>
        {loading ? (
          <LoadingSkeleton />
        ) : displayedTrades.length === 0 ? (
          <EmptyState />
        ) : (
          <div className="space-y-1">
            {displayedTrades.map((trade) => (
              <TradeRow key={trade.id} trade={trade} onClick={onTradeClick} />
            ))}

            {hasMoreTrades && onViewAll && (
              <div className="pt-2 text-center">
                <Button
                  variant="ghost"
                  size="sm"
                  className="text-muted-foreground"
                  onClick={onViewAll}
                >
                  View {trades.length - maxItems} more trades
                </Button>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export default RecentTradesList;
