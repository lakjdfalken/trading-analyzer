"use client";

import * as React from "react";
import { format } from "date-fns";
import {
  ArrowUpRight,
  ArrowDownRight,
  TrendingUp,
  TrendingDown,
  Clock,
  Circle,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useCurrencyStore } from "@/store/currency";
import { Badge } from "@/components/ui/badge";
import {
  TradeListItem,
  TradeDirection,
  TradeStatus,
  TradeOutcome,
  DIRECTION_LABELS,
  STATUS_LABELS,
  OUTCOME_LABELS,
} from "./types";

export interface TradeRowProps {
  trade: TradeListItem;
  onClick?: () => void;
  compact?: boolean;
  showStatus?: boolean;
  showDuration?: boolean;
  className?: string;
}

const directionConfig: Record<
  TradeDirection,
  { icon: typeof ArrowUpRight; color: string; bgColor: string }
> = {
  long: {
    icon: ArrowUpRight,
    color: "text-green-500",
    bgColor: "bg-green-500/10",
  },
  short: {
    icon: ArrowDownRight,
    color: "text-red-500",
    bgColor: "bg-red-500/10",
  },
};

const statusConfig: Record<TradeStatus, { color: string; dotColor: string }> = {
  open: { color: "text-blue-500", dotColor: "fill-blue-500" },
  closed: { color: "text-muted-foreground", dotColor: "fill-muted-foreground" },
  pending: { color: "text-yellow-500", dotColor: "fill-yellow-500" },
};

const outcomeConfig: Record<
  TradeOutcome,
  { color: string; bgColor: string; icon: typeof TrendingUp }
> = {
  win: {
    color: "text-green-500",
    bgColor: "bg-green-500/10",
    icon: TrendingUp,
  },
  loss: {
    color: "text-red-500",
    bgColor: "bg-red-500/10",
    icon: TrendingDown,
  },
  breakeven: {
    color: "text-muted-foreground",
    bgColor: "bg-muted",
    icon: TrendingUp,
  },
};

function getPnlColor(pnl: number | undefined): string {
  if (pnl === undefined) return "text-muted-foreground";
  if (pnl > 0) return "text-green-500";
  if (pnl < 0) return "text-red-500";
  return "text-muted-foreground";
}

function DirectionIcon({ direction }: { direction: TradeDirection }) {
  const config = directionConfig[direction];
  const Icon = config.icon;

  return (
    <div
      className={cn(
        "flex items-center justify-center w-8 h-8 rounded-full",
        config.bgColor,
      )}
    >
      <Icon className={cn("h-4 w-4", config.color)} />
    </div>
  );
}

function StatusIndicator({ status }: { status: TradeStatus }) {
  const config = statusConfig[status];

  return (
    <div className="flex items-center gap-1.5">
      <Circle className={cn("h-2 w-2", config.dotColor)} />
      <span className={cn("text-xs", config.color)}>
        {STATUS_LABELS[status]}
      </span>
    </div>
  );
}

function OutcomeBadge({ outcome }: { outcome: TradeOutcome }) {
  const config = outcomeConfig[outcome];

  return (
    <Badge
      variant="outline"
      className={cn("text-[10px] px-1.5 py-0", config.color, config.bgColor)}
    >
      {OUTCOME_LABELS[outcome]}
    </Badge>
  );
}

export function TradeRow({
  trade,
  onClick,
  compact = false,
  showStatus = false,
  showDuration = true,
  className,
}: TradeRowProps) {
  const directionCfg = directionConfig[trade.direction];
  const pnlColor = getPnlColor(trade.pnl);
  const { formatAmount } = useCurrencyStore();

  return (
    <div
      onClick={onClick}
      className={cn(
        "flex items-center justify-between transition-colors",
        "hover:bg-accent/50",
        onClick && "cursor-pointer",
        compact ? "p-2" : "p-3",
        "rounded-lg border-b border-border last:border-b-0",
        className,
      )}
    >
      {/* Left side: Direction icon and trade info */}
      <div className="flex items-center gap-3">
        <DirectionIcon direction={trade.direction} />

        <div className="flex flex-col">
          <div className="flex items-center gap-2">
            <span
              className={cn("font-medium", compact ? "text-xs" : "text-sm")}
            >
              {trade.instrument}
            </span>
            <Badge
              variant={trade.direction === "long" ? "success" : "danger"}
              className="text-[10px] px-1.5 py-0"
            >
              {DIRECTION_LABELS[trade.direction]}
            </Badge>
            {trade.outcome && <OutcomeBadge outcome={trade.outcome} />}
          </div>

          <div className="flex items-center gap-2 mt-0.5">
            <span className="text-xs text-muted-foreground">
              {trade.entryDate}
              {trade.exitDate && ` → ${trade.exitDate}`}
            </span>

            {showStatus && trade.status && (
              <>
                <span className="text-muted-foreground">•</span>
                <StatusIndicator status={trade.status} />
              </>
            )}

            {showDuration && trade.duration && (
              <>
                <span className="text-muted-foreground">•</span>
                <span className="text-xs text-muted-foreground flex items-center gap-1">
                  <Clock className="h-3 w-3" />
                  {trade.duration}
                </span>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Right side: P&L */}
      <div className="flex flex-col items-end">
        {trade.pnlFormatted !== undefined ? (
          <span
            className={cn(
              "font-semibold",
              compact ? "text-xs" : "text-sm",
              pnlColor,
            )}
          >
            {trade.pnl !== undefined && trade.pnl >= 0 ? "+" : ""}
            {trade.pnlFormatted}
          </span>
        ) : trade.pnl !== undefined ? (
          <span
            className={cn(
              "font-semibold",
              compact ? "text-xs" : "text-sm",
              pnlColor,
            )}
          >
            {trade.pnl >= 0 ? "+" : ""}
            {trade.currency
              ? formatAmount(trade.pnl, trade.currency)
              : trade.pnl.toFixed(2)}
          </span>
        ) : (
          <span className="text-xs text-muted-foreground">—</span>
        )}

        {trade.pnlPercent !== undefined && (
          <span
            className={cn(
              "text-xs flex items-center gap-0.5",
              getPnlColor(trade.pnlPercent),
            )}
          >
            {trade.pnlPercent >= 0 ? (
              <TrendingUp className="h-3 w-3" />
            ) : (
              <TrendingDown className="h-3 w-3" />
            )}
            {trade.pnlPercent >= 0 ? "+" : ""}
            {trade.pnlPercent.toFixed(2)}%
          </span>
        )}
      </div>
    </div>
  );
}

export default TradeRow;
