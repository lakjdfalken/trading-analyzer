"use client";

import * as React from "react";
import { CalendarIcon, ChevronDown, X, Wallet } from "lucide-react";
import { format } from "date-fns";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { Calendar } from "@/components/ui/calendar";
import { Badge } from "@/components/ui/badge";
import type { Account } from "@/lib/api";

export interface DateRange {
  from: Date | undefined;
  to: Date | undefined;
}

export interface FilterBarProps {
  dateRange: DateRange;
  onDateRangeChange: (range: DateRange) => void;
  selectedInstruments: string[];
  onInstrumentsChange: (instruments: string[]) => void;
  availableInstruments: string[];
  selectedAccountId: number | null;
  onAccountChange: (accountId: number | null) => void;
  availableAccounts: Account[];
  onReset?: () => void;
  className?: string;
}

const presetRanges = [
  { label: "Today", days: 0 },
  { label: "7 Days", days: 7 },
  { label: "30 Days", days: 30 },
  { label: "90 Days", days: 90 },
  { label: "YTD", days: -1 },
  { label: "All Time", days: -2 },
];

export function FilterBar({
  dateRange,
  onDateRangeChange,
  selectedInstruments,
  onInstrumentsChange,
  availableInstruments,
  selectedAccountId,
  onAccountChange,
  availableAccounts,
  onReset,
  className,
}: FilterBarProps) {
  const [dateOpen, setDateOpen] = React.useState(false);
  const [instrumentOpen, setInstrumentOpen] = React.useState(false);
  const [accountOpen, setAccountOpen] = React.useState(false);

  const selectedAccount = availableAccounts.find(
    (a) => a.account_id === selectedAccountId,
  );

  const handlePresetClick = (days: number) => {
    const to = new Date();
    let from: Date;

    if (days === 0) {
      from = new Date();
      from.setHours(0, 0, 0, 0);
    } else if (days === -1) {
      // YTD
      from = new Date(to.getFullYear(), 0, 1);
    } else if (days === -2) {
      // All Time
      from = new Date(2000, 0, 1);
    } else {
      from = new Date();
      from.setDate(from.getDate() - days);
    }

    onDateRangeChange({ from, to });
    setDateOpen(false);
  };

  const handleInstrumentToggle = (instrument: string) => {
    if (selectedInstruments.includes(instrument)) {
      onInstrumentsChange(selectedInstruments.filter((i) => i !== instrument));
    } else {
      onInstrumentsChange([...selectedInstruments, instrument]);
    }
  };

  const handleClearInstruments = () => {
    onInstrumentsChange([]);
    setInstrumentOpen(false);
  };

  const hasActiveFilters =
    dateRange.from ||
    dateRange.to ||
    selectedInstruments.length > 0 ||
    selectedAccountId !== null;

  const formatDateRange = () => {
    if (dateRange.from && dateRange.to) {
      if (dateRange.from.toDateString() === dateRange.to.toDateString()) {
        return format(dateRange.from, "MMM d, yyyy");
      }
      return `${format(dateRange.from, "MMM d")} - ${format(dateRange.to, "MMM d, yyyy")}`;
    }
    if (dateRange.from) {
      return `From ${format(dateRange.from, "MMM d, yyyy")}`;
    }
    if (dateRange.to) {
      return `Until ${format(dateRange.to, "MMM d, yyyy")}`;
    }
    return "Select dates";
  };

  return (
    <div
      className={cn(
        "flex flex-wrap items-center gap-3 p-4 bg-card border border-border rounded-lg",
        className,
      )}
    >
      {/* Date Range Filter */}
      <Popover open={dateOpen} onOpenChange={setDateOpen}>
        <PopoverTrigger asChild>
          <Button
            variant="outline"
            className={cn(
              "justify-start text-left font-normal min-w-[200px]",
              !dateRange.from && !dateRange.to && "text-muted-foreground",
            )}
          >
            <CalendarIcon className="mr-2 h-4 w-4" />
            {formatDateRange()}
            <ChevronDown className="ml-auto h-4 w-4 opacity-50" />
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-auto p-0" align="start">
          <div className="flex">
            <div className="border-r border-border p-3 space-y-1">
              <p className="text-xs font-medium text-muted-foreground mb-2">
                Quick Select
              </p>
              {presetRanges.map((preset) => (
                <Button
                  key={preset.label}
                  variant="ghost"
                  size="sm"
                  className="w-full justify-start text-sm"
                  onClick={() => handlePresetClick(preset.days)}
                >
                  {preset.label}
                </Button>
              ))}
            </div>
            <div className="p-3">
              <Calendar
                initialFocus
                mode="range"
                defaultMonth={dateRange.from}
                selected={{ from: dateRange.from, to: dateRange.to }}
                onSelect={(range) => {
                  onDateRangeChange({
                    from: range?.from,
                    to: range?.to,
                  });
                }}
                numberOfMonths={2}
              />
            </div>
          </div>
        </PopoverContent>
      </Popover>

      {/* Account Filter */}
      <Popover open={accountOpen} onOpenChange={setAccountOpen}>
        <PopoverTrigger asChild>
          <Button
            variant="outline"
            className={cn(
              "justify-start text-left font-normal min-w-[160px]",
              selectedAccountId === null && "text-muted-foreground",
            )}
          >
            <Wallet className="mr-2 h-4 w-4" />
            {selectedAccount ? (
              <span className="truncate max-w-[120px]">
                {selectedAccount.account_name ||
                  `Account ${selectedAccount.account_id}`}
              </span>
            ) : (
              "All Accounts"
            )}
            <ChevronDown className="ml-auto h-4 w-4 opacity-50" />
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-[220px] p-0" align="start">
          <div className="p-2 border-b border-border">
            <p className="text-sm font-medium">Accounts</p>
          </div>
          <div className="max-h-[300px] overflow-y-auto p-2 space-y-1">
            <label
              className={cn(
                "flex items-center gap-2 px-2 py-1.5 rounded-md cursor-pointer transition-colors",
                "hover:bg-accent",
                selectedAccountId === null && "bg-accent",
              )}
              onClick={() => {
                onAccountChange(null);
                setAccountOpen(false);
              }}
            >
              <input
                type="radio"
                checked={selectedAccountId === null}
                onChange={() => {}}
                className="h-4 w-4 rounded-full border-border"
              />
              <span className="text-sm">All Accounts (converted)</span>
            </label>
            {availableAccounts.map((account) => (
              <label
                key={account.account_id}
                className={cn(
                  "flex items-center gap-2 px-2 py-1.5 rounded-md cursor-pointer transition-colors",
                  "hover:bg-accent",
                  selectedAccountId === account.account_id && "bg-accent",
                )}
                onClick={() => {
                  onAccountChange(account.account_id);
                  setAccountOpen(false);
                }}
              >
                <input
                  type="radio"
                  checked={selectedAccountId === account.account_id}
                  onChange={() => {}}
                  className="h-4 w-4 rounded-full border-border"
                />
                <span className="text-sm">
                  {account.account_name || `Account ${account.account_id}`}
                  {account.currency && (
                    <span className="text-muted-foreground ml-1">
                      ({account.currency})
                    </span>
                  )}
                </span>
              </label>
            ))}
            {availableAccounts.length === 0 && (
              <p className="text-sm text-muted-foreground text-center py-4">
                No accounts available
              </p>
            )}
          </div>
        </PopoverContent>
      </Popover>

      {/* Instrument Filter */}
      <Popover open={instrumentOpen} onOpenChange={setInstrumentOpen}>
        <PopoverTrigger asChild>
          <Button
            variant="outline"
            className={cn(
              "justify-start text-left font-normal min-w-[160px]",
              selectedInstruments.length === 0 && "text-muted-foreground",
            )}
          >
            {selectedInstruments.length > 0 ? (
              <>
                <span className="truncate max-w-[100px]">
                  {selectedInstruments.length === 1
                    ? selectedInstruments[0]
                    : `${selectedInstruments.length} instruments`}
                </span>
                <Badge
                  variant="secondary"
                  className="ml-2 h-5 w-5 p-0 flex items-center justify-center"
                >
                  {selectedInstruments.length}
                </Badge>
              </>
            ) : (
              "All Instruments"
            )}
            <ChevronDown className="ml-auto h-4 w-4 opacity-50" />
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-[220px] p-0" align="start">
          <div className="p-2 border-b border-border">
            <div className="flex items-center justify-between">
              <p className="text-sm font-medium">Instruments</p>
              {selectedInstruments.length > 0 && (
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-auto p-1 text-xs"
                  onClick={handleClearInstruments}
                >
                  Clear all
                </Button>
              )}
            </div>
          </div>
          <div className="max-h-[300px] overflow-y-auto p-2 space-y-1">
            {availableInstruments.map((instrument) => (
              <label
                key={instrument}
                className={cn(
                  "flex items-center gap-2 px-2 py-1.5 rounded-md cursor-pointer transition-colors",
                  "hover:bg-accent",
                  selectedInstruments.includes(instrument) && "bg-accent",
                )}
              >
                <input
                  type="checkbox"
                  checked={selectedInstruments.includes(instrument)}
                  onChange={() => handleInstrumentToggle(instrument)}
                  className="h-4 w-4 rounded border-border"
                />
                <span className="text-sm">{instrument}</span>
              </label>
            ))}
            {availableInstruments.length === 0 && (
              <p className="text-sm text-muted-foreground text-center py-4">
                No instruments available
              </p>
            )}
          </div>
        </PopoverContent>
      </Popover>

      {/* Selected Instrument Badges */}
      {selectedInstruments.length > 0 && selectedInstruments.length <= 3 && (
        <div className="flex flex-wrap gap-1">
          {selectedInstruments.map((instrument) => (
            <Badge key={instrument} variant="secondary" className="gap-1 pr-1">
              {instrument}
              <button
                onClick={() => handleInstrumentToggle(instrument)}
                className="ml-1 rounded-full hover:bg-muted-foreground/20 p-0.5"
              >
                <X className="h-3 w-3" />
              </button>
            </Badge>
          ))}
        </div>
      )}

      {/* Reset Button */}
      {hasActiveFilters && onReset && (
        <Button
          variant="ghost"
          size="sm"
          onClick={onReset}
          className="ml-auto text-muted-foreground hover:text-foreground"
        >
          <X className="h-4 w-4 mr-1" />
          Reset filters
        </Button>
      )}
    </div>
  );
}

export default FilterBar;
