"use client";

import * as React from "react";
import { Expand, Download, MoreVertical, RefreshCw } from "lucide-react";
import { cn } from "@/lib/utils";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";

export type ChartType =
  | "line"
  | "bar"
  | "area"
  | "pie"
  | "scatter"
  | "candlestick"
  | "heatmap";

export interface ChartCardProps {
  title: string;
  subtitle?: string;
  chartType?: ChartType;
  children: React.ReactNode;
  loading?: boolean;
  error?: string;
  onExpand?: () => void;
  onDownload?: () => void;
  onRefresh?: () => void;
  className?: string;
  aspectRatio?: "square" | "video" | "wide" | "auto";
  showToolbar?: boolean;
  footer?: React.ReactNode;
}

const aspectRatioClasses = {
  square: "aspect-square",
  video: "aspect-video",
  wide: "aspect-[21/9]",
  auto: "",
};

function LoadingSkeleton({ aspectRatio }: { aspectRatio: string }) {
  return (
    <div
      className={cn(
        "w-full animate-pulse bg-muted rounded-md flex items-center justify-center",
        aspectRatioClasses[aspectRatio as keyof typeof aspectRatioClasses]
      )}
    >
      <div className="flex flex-col items-center gap-2 text-muted-foreground">
        <RefreshCw className="h-6 w-6 animate-spin" />
        <span className="text-sm">Loading chart...</span>
      </div>
    </div>
  );
}

function ErrorState({ message }: { message: string }) {
  return (
    <div className="w-full aspect-video bg-destructive/10 rounded-md flex items-center justify-center p-4">
      <div className="text-center">
        <p className="text-sm font-medium text-destructive">
          Failed to load chart
        </p>
        <p className="text-xs text-muted-foreground mt-1">{message}</p>
      </div>
    </div>
  );
}

function ChartToolbar({
  onExpand,
  onDownload,
  onRefresh,
}: {
  onExpand?: () => void;
  onDownload?: () => void;
  onRefresh?: () => void;
}) {
  const [menuOpen, setMenuOpen] = React.useState(false);

  return (
    <div className="flex items-center gap-1">
      {onRefresh && (
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8"
          onClick={onRefresh}
          title="Refresh"
        >
          <RefreshCw className="h-4 w-4" />
        </Button>
      )}

      {onExpand && (
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8"
          onClick={onExpand}
          title="Expand"
        >
          <Expand className="h-4 w-4" />
        </Button>
      )}

      {onDownload && (
        <Popover open={menuOpen} onOpenChange={setMenuOpen}>
          <PopoverTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8"
              title="More options"
            >
              <MoreVertical className="h-4 w-4" />
            </Button>
          </PopoverTrigger>
          <PopoverContent className="w-40 p-1" align="end">
            <Button
              variant="ghost"
              size="sm"
              className="w-full justify-start text-sm"
              onClick={() => {
                onDownload();
                setMenuOpen(false);
              }}
            >
              <Download className="h-4 w-4 mr-2" />
              Download PNG
            </Button>
          </PopoverContent>
        </Popover>
      )}
    </div>
  );
}

export function ChartCard({
  title,
  subtitle,
  children,
  loading = false,
  error,
  onExpand,
  onDownload,
  onRefresh,
  className,
  aspectRatio = "video",
  showToolbar = true,
  footer,
}: ChartCardProps) {
  return (
    <Card
      className={cn(
        "overflow-hidden transition-shadow hover:shadow-lg",
        className
      )}
    >
      <CardHeader className="flex flex-row items-start justify-between space-y-0 pb-2">
        <div className="space-y-1">
          <CardTitle className="text-base font-semibold">{title}</CardTitle>
          {subtitle && (
            <p className="text-xs text-muted-foreground">{subtitle}</p>
          )}
        </div>

        {showToolbar && (onExpand || onDownload || onRefresh) && (
          <ChartToolbar
            onExpand={onExpand}
            onDownload={onDownload}
            onRefresh={onRefresh}
          />
        )}
      </CardHeader>

      <CardContent className="p-4 pt-0">
        {loading ? (
          <LoadingSkeleton aspectRatio={aspectRatio} />
        ) : error ? (
          <ErrorState message={error} />
        ) : (
          <div
            className={cn(
              "w-full",
              aspectRatio !== "auto" &&
                aspectRatioClasses[aspectRatio as keyof typeof aspectRatioClasses]
            )}
          >
            {children}
          </div>
        )}

        {footer && (
          <div className="mt-3 pt-3 border-t border-border">{footer}</div>
        )}
      </CardContent>
    </Card>
  );
}

// Preset variants for common chart types
export function BalanceChartCard(props: Omit<ChartCardProps, "chartType">) {
  return <ChartCard {...props} aspectRatio="video" />;
}

export function PieChartCard(props: Omit<ChartCardProps, "chartType">) {
  return <ChartCard {...props} aspectRatio="square" />;
}

export function WideChartCard(props: Omit<ChartCardProps, "chartType">) {
  return <ChartCard {...props} aspectRatio="wide" />;
}

export default ChartCard;
