'use client';

import React from 'react';
import { useCurrencyStore } from '@/store/currency';
import { cn } from '@/lib/utils';

interface CurrencyDisplayProps {
  amount: number;
  currency: string;
  className?: string;
  convertedClassName?: string;
  showOriginal?: boolean;
  colorize?: boolean; // Color positive/negative amounts
  size?: 'sm' | 'md' | 'lg';
}

/**
 * Displays a currency amount with optional conversion to default currency.
 *
 * Shows:
 * - Original amount in original currency
 * - Converted amount in user's default currency (if showConverted is enabled)
 */
export function CurrencyDisplay({
  amount,
  currency,
  className,
  convertedClassName,
  showOriginal = true,
  colorize = false,
  size = 'md',
}: CurrencyDisplayProps) {
  const { formatWithConversion } = useCurrencyStore();
  const { original, converted, showBoth } = formatWithConversion(amount, currency);

  const sizeClasses = {
    sm: 'text-sm',
    md: 'text-base',
    lg: 'text-lg font-semibold',
  };

  const colorClass = colorize
    ? amount >= 0
      ? 'text-emerald-500'
      : 'text-red-500'
    : '';

  if (!showBoth || !converted) {
    return (
      <span className={cn(sizeClasses[size], colorClass, className)}>
        {showOriginal ? original : converted || original}
      </span>
    );
  }

  return (
    <span className={cn('inline-flex flex-col', className)}>
      <span className={cn(sizeClasses[size], colorClass)}>
        {original}
      </span>
      <span
        className={cn(
          'text-xs text-muted-foreground',
          convertedClassName
        )}
      >
        ({converted})
      </span>
    </span>
  );
}

/**
 * Inline version that shows converted amount in parentheses on same line.
 */
export function CurrencyDisplayInline({
  amount,
  currency,
  className,
  colorize = false,
}: Omit<CurrencyDisplayProps, 'size' | 'convertedClassName' | 'showOriginal'>) {
  const { formatWithConversion } = useCurrencyStore();
  const { original, converted, showBoth } = formatWithConversion(amount, currency);

  const colorClass = colorize
    ? amount >= 0
      ? 'text-emerald-500'
      : 'text-red-500'
    : '';

  return (
    <span className={cn(colorClass, className)}>
      {original}
      {showBoth && converted && (
        <span className="text-muted-foreground ml-1">
          ({converted})
        </span>
      )}
    </span>
  );
}

/**
 * Compact version for tables - shows only primary value.
 */
export function CurrencyDisplayCompact({
  amount,
  currency,
  className,
  colorize = false,
  useDefault = false, // If true, show in default currency; otherwise show original
}: Omit<CurrencyDisplayProps, 'size' | 'convertedClassName' | 'showOriginal'> & {
  useDefault?: boolean;
}) {
  const { formatAmount, convert, defaultCurrency } = useCurrencyStore();

  let displayAmount = amount;
  let displayCurrency = currency;

  if (useDefault && currency !== defaultCurrency) {
    const converted = convert(amount, currency, defaultCurrency);
    if (converted !== null) {
      displayAmount = converted;
      displayCurrency = defaultCurrency;
    }
  }

  const formatted = formatAmount(displayAmount, displayCurrency);

  const colorClass = colorize
    ? amount >= 0
      ? 'text-emerald-500'
      : 'text-red-500'
    : '';

  return (
    <span className={cn(colorClass, className)}>
      {formatted}
    </span>
  );
}

export default CurrencyDisplay;
