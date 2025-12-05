"use client";

import React from "react";
import { useCurrencyStore } from "@/store/currency";
import { useSettingsStore } from "@/store/settings";
import { cn } from "@/lib/utils";

interface CurrencyDisplayProps {
  amount: number;
  currency: string;
  className?: string;
  convertedClassName?: string;
  showOriginal?: boolean;
  colorize?: boolean; // Color positive/negative amounts
  size?: "sm" | "md" | "lg";
}

/**
 * Displays a currency amount.
 * Formatting only - no conversion (backend handles conversion).
 */
export function CurrencyDisplay({
  amount,
  currency,
  className,
  colorize = false,
  size = "md",
}: CurrencyDisplayProps) {
  const { formatAmount } = useCurrencyStore();
  const formatted = formatAmount(amount, currency);

  const sizeClasses = {
    sm: "text-sm",
    md: "text-base",
    lg: "text-lg font-semibold",
  };

  const colorClass = colorize
    ? amount >= 0
      ? "text-emerald-500"
      : "text-red-500"
    : "";

  return (
    <span className={cn(sizeClasses[size], colorClass, className)}>
      {formatted}
    </span>
  );
}

/**
 * Inline version - same as CurrencyDisplay but explicitly inline.
 */
export function CurrencyDisplayInline({
  amount,
  currency,
  className,
  colorize = false,
}: Omit<CurrencyDisplayProps, "size" | "convertedClassName" | "showOriginal">) {
  const { formatAmount } = useCurrencyStore();
  const formatted = formatAmount(amount, currency);

  const colorClass = colorize
    ? amount >= 0
      ? "text-emerald-500"
      : "text-red-500"
    : "";

  return <span className={cn(colorClass, className)}>{formatted}</span>;
}

/**
 * Compact version for tables - shows only primary value.
 * Uses the default currency from settings.
 */
export function CurrencyDisplayCompact({
  amount,
  currency,
  className,
  colorize = false,
}: Omit<CurrencyDisplayProps, "size" | "convertedClassName" | "showOriginal">) {
  const { formatAmount } = useCurrencyStore();
  const { defaultCurrency } = useSettingsStore();

  // Display in the currency provided (backend should have already converted if needed)
  const displayCurrency = currency || defaultCurrency;
  const formatted = displayCurrency
    ? formatAmount(amount, displayCurrency)
    : amount.toFixed(2);

  const colorClass = colorize
    ? amount >= 0
      ? "text-emerald-500"
      : "text-red-500"
    : "";

  return <span className={cn(colorClass, className)}>{formatted}</span>;
}

export default CurrencyDisplay;
