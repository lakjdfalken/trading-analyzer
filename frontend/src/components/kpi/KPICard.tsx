"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { LucideIcon } from "lucide-react";
import { useCurrencyStore } from "@/store/currency";

export interface KPICardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon?: LucideIcon;
  trend?: {
    value: number;
    isPositive: boolean;
  };
  variant?: "default" | "success" | "warning" | "danger";
  className?: string;
  /** Currency code for the value (if it's a monetary amount) */
  currency?: string;
  /** Whether to show the value as a currency amount */
  isCurrency?: boolean;
}

const variantStyles = {
  default: "border-border",
  success: "border-green-500/50 bg-green-500/5",
  warning: "border-yellow-500/50 bg-yellow-500/5",
  danger: "border-red-500/50 bg-red-500/5",
};

const iconVariantStyles = {
  default: "text-muted-foreground",
  success: "text-green-500",
  warning: "text-yellow-500",
  danger: "text-red-500",
};

export function KPICard({
  title,
  value,
  subtitle,
  icon: Icon,
  trend,
  variant = "default",
  className,
  currency,
  isCurrency = false,
}: KPICardProps) {
  const { formatWithConversion, formatAmount } = useCurrencyStore();

  // Format the display value
  const renderValue = () => {
    if (!isCurrency || !currency || typeof value !== "number") {
      return <div className="text-2xl font-bold">{value}</div>;
    }

    const { original, converted, showBoth } = formatWithConversion(
      value,
      currency,
    );

    return (
      <div className="flex flex-col">
        <div className="text-2xl font-bold">{original}</div>
        {showBoth && converted && (
          <div className="text-sm text-muted-foreground">({converted})</div>
        )}
      </div>
    );
  };

  return (
    <Card className={cn(variantStyles[variant], className)}>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">
          {title}
        </CardTitle>
        {Icon && <Icon className={cn("h-4 w-4", iconVariantStyles[variant])} />}
      </CardHeader>
      <CardContent>
        {renderValue()}
        {(subtitle || trend) && (
          <div className="flex items-center gap-2 mt-1">
            {trend && (
              <span
                className={cn(
                  "text-xs font-medium",
                  trend.isPositive ? "text-green-500" : "text-red-500",
                )}
              >
                {trend.isPositive ? "+" : ""}
                {trend.value}%
              </span>
            )}
            {subtitle && (
              <p className="text-xs text-muted-foreground">{subtitle}</p>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

/**
 * KPI Card specifically for monetary values with built-in currency support.
 */
export interface CurrencyKPICardProps
  extends Omit<KPICardProps, "value" | "isCurrency"> {
  /** Monetary amount */
  amount: number;
  /** Currency code for the amount */
  currency: string;
  /** Color based on positive/negative */
  colorByValue?: boolean;
}

export function CurrencyKPICard({
  amount,
  currency,
  colorByValue = false,
  variant,
  ...props
}: CurrencyKPICardProps) {
  // Determine variant based on value if colorByValue is true
  const computedVariant = colorByValue
    ? amount >= 0
      ? "success"
      : "danger"
    : variant;

  return (
    <KPICard
      {...props}
      value={amount}
      currency={currency}
      isCurrency={true}
      variant={computedVariant}
    />
  );
}

export default KPICard;
