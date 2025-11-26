"use client";

import * as React from "react";
import { CalendarIcon } from "lucide-react";
import { format, subDays, startOfMonth, endOfMonth, startOfYear, subMonths, startOfQuarter, subQuarters } from "date-fns";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { Calendar, DateRange } from "@/components/ui/calendar";
import { DateRangePreset, DATE_RANGE_PRESETS } from "./types";

export interface DateRangePickerProps {
  dateRange: {
    from: Date | undefined;
    to: Date | undefined;
    preset?: DateRangePreset;
  };
  onDateRangeChange: (range: {
    from: Date | undefined;
    to: Date | undefined;
    preset?: DateRangePreset;
  }) => void;
  className?: string;
  disabled?: boolean;
  placeholder?: string;
}

function getPresetDateRange(preset: DateRangePreset): { from: Date; to: Date } {
  const today = new Date();
  today.setHours(23, 59, 59, 999);

  const startOfToday = new Date();
  startOfToday.setHours(0, 0, 0, 0);

  switch (preset) {
    case "today":
      return { from: startOfToday, to: today };
    case "yesterday": {
      const yesterday = subDays(startOfToday, 1);
      const endOfYesterday = new Date(yesterday);
      endOfYesterday.setHours(23, 59, 59, 999);
      return { from: yesterday, to: endOfYesterday };
    }
    case "last7days":
      return { from: subDays(startOfToday, 6), to: today };
    case "last30days":
      return { from: subDays(startOfToday, 29), to: today };
    case "thisMonth":
      return { from: startOfMonth(today), to: today };
    case "lastMonth": {
      const lastMonth = subMonths(today, 1);
      return { from: startOfMonth(lastMonth), to: endOfMonth(lastMonth) };
    }
    case "thisQuarter":
      return { from: startOfQuarter(today), to: today };
    case "lastQuarter": {
      const lastQuarter = subQuarters(today, 1);
      return { from: startOfQuarter(lastQuarter), to: endOfMonth(subMonths(startOfQuarter(today), 1)) };
    }
    case "thisYear":
      return { from: startOfYear(today), to: today };
    case "lastYear": {
      const lastYear = new Date(today.getFullYear() - 1, 0, 1);
      const endOfLastYear = new Date(today.getFullYear() - 1, 11, 31, 23, 59, 59, 999);
      return { from: lastYear, to: endOfLastYear };
    }
    case "allTime":
      return { from: new Date(2000, 0, 1), to: today };
    case "custom":
    default:
      return { from: subDays(startOfToday, 29), to: today };
  }
}

export function DateRangePicker({
  dateRange,
  onDateRangeChange,
  className,
  disabled = false,
  placeholder = "Select date range",
}: DateRangePickerProps) {
  const [open, setOpen] = React.useState(false);
  const [selectedPreset, setSelectedPreset] = React.useState<DateRangePreset | undefined>(
    dateRange.preset
  );

  const handlePresetClick = (preset: DateRangePreset) => {
    if (preset === "custom") {
      setSelectedPreset("custom");
      return;
    }

    const range = getPresetDateRange(preset);
    setSelectedPreset(preset);
    onDateRangeChange({
      from: range.from,
      to: range.to,
      preset,
    });
    setOpen(false);
  };

  const handleCalendarSelect = (range: DateRange | undefined) => {
    setSelectedPreset("custom");
    onDateRangeChange({
      from: range?.from,
      to: range?.to,
      preset: "custom",
    });
  };

  const formatDateRange = () => {
    if (!dateRange.from && !dateRange.to) {
      return placeholder;
    }

    // If using a preset (not custom), show the preset label
    if (selectedPreset && selectedPreset !== "custom") {
      const presetLabel = DATE_RANGE_PRESETS.find((p) => p.value === selectedPreset)?.label;
      if (presetLabel) {
        return presetLabel;
      }
    }

    // Otherwise show the actual date range
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

    return placeholder;
  };

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          disabled={disabled}
          className={cn(
            "justify-start text-left font-normal min-w-[200px]",
            !dateRange.from && !dateRange.to && "text-muted-foreground",
            className
          )}
        >
          <CalendarIcon className="mr-2 h-4 w-4" />
          <span className="truncate">{formatDateRange()}</span>
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-auto p-0" align="start">
        <div className="flex">
          {/* Presets sidebar */}
          <div className="border-r border-border p-2 space-y-1 min-w-[140px]">
            <p className="text-xs font-medium text-muted-foreground px-2 py-1">
              Quick Select
            </p>
            {DATE_RANGE_PRESETS.map((preset) => (
              <Button
                key={preset.value}
                variant={selectedPreset === preset.value ? "secondary" : "ghost"}
                size="sm"
                className={cn(
                  "w-full justify-start text-sm h-8",
                  selectedPreset === preset.value && "bg-accent"
                )}
                onClick={() => handlePresetClick(preset.value)}
              >
                {preset.label}
              </Button>
            ))}
          </div>

          {/* Calendar */}
          <div className="p-2">
            <Calendar
              initialFocus
              mode="range"
              defaultMonth={dateRange.from || new Date()}
              selected={{
                from: dateRange.from,
                to: dateRange.to,
              }}
              onSelect={handleCalendarSelect}
              numberOfMonths={2}
            />

            {/* Footer with selected range info */}
            <div className="border-t border-border mt-2 pt-2 px-2">
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">
                  {dateRange.from && dateRange.to ? (
                    <>
                      {format(dateRange.from, "MMM d, yyyy")} -{" "}
                      {format(dateRange.to, "MMM d, yyyy")}
                    </>
                  ) : (
                    "Select a range"
                  )}
                </span>
                <Button
                  size="sm"
                  variant="default"
                  onClick={() => setOpen(false)}
                  disabled={!dateRange.from || !dateRange.to}
                >
                  Apply
                </Button>
              </div>
            </div>
          </div>
        </div>
      </PopoverContent>
    </Popover>
  );
}

export default DateRangePicker;
