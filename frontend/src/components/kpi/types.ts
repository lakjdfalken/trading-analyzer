import { LucideIcon } from 'lucide-react';

export type TrendDirection = 'up' | 'down' | 'neutral';

export interface KPITrend {
  value: number;
  isPositive: boolean;
  direction?: TrendDirection;
}

export type KPIVariant = 'default' | 'success' | 'warning' | 'danger';

export interface KPIValue {
  raw: number;
  formatted: string;
  prefix?: string;
  suffix?: string;
}

export interface KPIData {
  id: string;
  title: string;
  value: string | number | KPIValue;
  subtitle?: string;
  icon?: LucideIcon;
  trend?: KPITrend;
  variant?: KPIVariant;
  tooltip?: string;
}

export interface KPICardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon?: LucideIcon;
  trend?: {
    value: number;
    isPositive: boolean;
  };
  variant?: KPIVariant;
  className?: string;
}

export interface KPIGridProps {
  data: KPIData[];
  columns?: 2 | 3 | 4 | 5 | 6;
  className?: string;
  loading?: boolean;
}
