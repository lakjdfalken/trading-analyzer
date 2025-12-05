"use client";

import React from "react";
import { useSettingsStore } from "@/store/settings";
import { cn } from "@/lib/utils";
import { ChevronDown, Check } from "lucide-react";

interface CurrencySelectorProps {
  className?: string;
  label?: string;
  showLabel?: boolean;
  size?: "sm" | "md" | "lg";
  variant?: "default" | "outline" | "ghost";
}

// Available currencies with their info
const CURRENCIES = [
  { code: "SEK", symbol: "kr", name: "Swedish Krona" },
  { code: "DKK", symbol: "kr", name: "Danish Krone" },
  { code: "EUR", symbol: "€", name: "Euro" },
  { code: "USD", symbol: "$", name: "US Dollar" },
  { code: "GBP", symbol: "£", name: "British Pound" },
  { code: "NOK", symbol: "kr", name: "Norwegian Krone" },
  { code: "CHF", symbol: "CHF", name: "Swiss Franc" },
];

/**
 * Currency selector dropdown component.
 * Allows user to select their default display currency.
 * Saves to backend via settings store.
 */
export function CurrencySelector({
  className,
  label = "Display Currency",
  showLabel = true,
  size = "md",
  variant = "default",
}: CurrencySelectorProps) {
  const [isOpen, setIsOpen] = React.useState(false);
  const [isSaving, setIsSaving] = React.useState(false);
  const dropdownRef = React.useRef<HTMLDivElement>(null);

  const { defaultCurrency, setDefaultCurrency } = useSettingsStore();

  // Close dropdown when clicking outside
  React.useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    }

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const selectedCurrency =
    CURRENCIES.find((c) => c.code === defaultCurrency) || CURRENCIES[0];

  const sizeClasses = {
    sm: "h-8 text-xs px-2",
    md: "h-9 text-sm px-3",
    lg: "h-10 text-base px-4",
  };

  const variantClasses = {
    default: "bg-secondary border border-border hover:bg-secondary/80",
    outline: "border border-border hover:bg-accent",
    ghost: "hover:bg-accent",
  };

  const handleSelectCurrency = async (currencyCode: string) => {
    setIsSaving(true);
    try {
      await setDefaultCurrency(currencyCode);
      setIsOpen(false);
    } catch (error) {
      console.error("Failed to save currency:", error);
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className={cn("relative", className)} ref={dropdownRef}>
      {showLabel && (
        <label className="block text-xs font-medium text-muted-foreground mb-1">
          {label}
        </label>
      )}

      {/* Trigger Button */}
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        disabled={isSaving}
        className={cn(
          "flex items-center justify-between gap-2 rounded-md font-medium transition-colors",
          "focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
          "disabled:opacity-50 disabled:cursor-not-allowed",
          sizeClasses[size],
          variantClasses[variant],
          "min-w-[120px]",
        )}
      >
        <span className="flex items-center gap-2">
          <span className="font-semibold">{selectedCurrency.symbol}</span>
          <span>{selectedCurrency.code}</span>
        </span>
        <ChevronDown
          className={cn(
            "h-4 w-4 opacity-50 transition-transform",
            isOpen && "rotate-180",
          )}
        />
      </button>

      {/* Dropdown Menu */}
      {isOpen && (
        <div
          className={cn(
            "absolute z-50 mt-1 w-full min-w-[180px]",
            "rounded-md border border-border bg-popover shadow-md",
            "animate-in fade-in-0 zoom-in-95",
          )}
        >
          <div className="p-1 max-h-[300px] overflow-auto">
            {CURRENCIES.map((currency) => (
              <CurrencyOption
                key={currency.code}
                currency={currency}
                isSelected={currency.code === defaultCurrency}
                onClick={() => handleSelectCurrency(currency.code)}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

interface CurrencyOptionProps {
  currency: { code: string; symbol: string; name: string };
  isSelected: boolean;
  onClick: () => void;
}

function CurrencyOption({
  currency,
  isSelected,
  onClick,
}: CurrencyOptionProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-sm",
        "hover:bg-accent hover:text-accent-foreground",
        "focus:outline-none focus:bg-accent",
        isSelected && "bg-accent",
      )}
    >
      <span className="w-6 font-semibold">{currency.symbol}</span>
      <span className="flex-1 text-left">{currency.code}</span>
      <span className="text-xs text-muted-foreground hidden sm:inline">
        {currency.name}
      </span>
      {isSelected && <Check className="h-4 w-4 text-primary" />}
    </button>
  );
}

/**
 * Toggle for showing/hiding converted currency values.
 * Saves to backend via settings store.
 */
export function ShowConvertedToggle({ className }: { className?: string }) {
  const { showConverted, setShowConverted } = useSettingsStore();
  const [isSaving, setIsSaving] = React.useState(false);

  const handleToggle = async () => {
    setIsSaving(true);
    try {
      await setShowConverted(!showConverted);
    } catch (error) {
      console.error("Failed to save setting:", error);
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <button
      type="button"
      onClick={handleToggle}
      disabled={isSaving}
      className={cn(
        "flex items-center gap-2 cursor-pointer select-none",
        "disabled:opacity-50 disabled:cursor-not-allowed",
        className,
      )}
    >
      <div
        className={cn(
          "relative h-5 w-9 rounded-full transition-colors",
          showConverted ? "bg-primary" : "bg-muted",
        )}
      >
        <div
          className={cn(
            "absolute top-0.5 h-4 w-4 rounded-full bg-white shadow-sm transition-transform",
            showConverted ? "translate-x-4" : "translate-x-0.5",
          )}
        />
      </div>
      <span className="text-sm text-muted-foreground">
        Show converted values
      </span>
    </button>
  );
}

export default CurrencySelector;
