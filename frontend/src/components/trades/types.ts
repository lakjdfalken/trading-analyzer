import { LucideIcon } from "lucide-react";

export type TradeDirection = "long" | "short";

export type TradeStatus = "open" | "closed" | "pending";

export type TradeOutcome = "win" | "loss" | "breakeven";

export interface Trade {
  id: string;
  instrument: string;
  direction: TradeDirection;
  status: TradeStatus;
  outcome?: TradeOutcome;
  entryDate: Date;
  exitDate?: Date;
  entryPrice: number;
  exitPrice?: number;
  quantity: number;
  pnl?: number;
  pnlPercent?: number;
  commission?: number;
  netPnl?: number;
  duration?: number; // in minutes
  notes?: string;
  tags?: string[];
  riskRewardRatio?: number;
  stopLoss?: number;
  takeProfit?: number;
  currency?: string;
}

export interface TradeListItem {
  id: string;
  instrument: string;
  direction: TradeDirection;
  status: TradeStatus;
  outcome?: TradeOutcome;
  entryDate: string; // formatted date string
  exitDate?: string;
  pnl?: number;
  pnlFormatted?: string;
  pnlPercent?: number;
  duration?: string; // formatted duration string
  currency?: string;
}

export interface RecentTradesProps {
  trades: TradeListItem[];
  onTradeClick?: (trade: TradeListItem) => void;
  maxItems?: number;
  showViewAll?: boolean;
  onViewAllClick?: () => void;
  className?: string;
  loading?: boolean;
  emptyMessage?: string;
}

export interface TradeRowProps {
  trade: TradeListItem;
  onClick?: () => void;
  className?: string;
}

export interface TradeDetailsProps {
  trade: Trade;
  onClose?: () => void;
  onEdit?: (trade: Trade) => void;
  onDelete?: (id: string) => void;
  className?: string;
}

export interface TradeSummaryStats {
  totalTrades: number;
  winningTrades: number;
  losingTrades: number;
  breakEvenTrades: number;
  winRate: number;
  totalPnl: number;
  avgWin: number;
  avgLoss: number;
  largestWin: number;
  largestLoss: number;
  profitFactor: number;
  avgHoldTime: number; // in minutes
  expectancy: number;
}

export interface TradeColumnDef {
  key: keyof TradeListItem | string;
  label: string;
  sortable?: boolean;
  width?: string;
  align?: "left" | "center" | "right";
  render?: (value: unknown, trade: TradeListItem) => React.ReactNode;
}

export type SortDirection = "asc" | "desc";

export interface TradeTableSort {
  column: string;
  direction: SortDirection;
}

export interface TradeTableProps {
  trades: TradeListItem[];
  columns?: TradeColumnDef[];
  onTradeClick?: (trade: TradeListItem) => void;
  onSort?: (sort: TradeTableSort) => void;
  currentSort?: TradeTableSort;
  loading?: boolean;
  emptyMessage?: string;
  className?: string;
  stickyHeader?: boolean;
  virtualized?: boolean;
  rowHeight?: number;
}

export interface TradeFilters {
  dateRange?: {
    from: Date | undefined;
    to: Date | undefined;
  };
  instruments?: string[];
  direction?: TradeDirection | "all";
  outcome?: TradeOutcome | "all";
  status?: TradeStatus | "all";
  minPnl?: number;
  maxPnl?: number;
  tags?: string[];
}

export const DEFAULT_TRADE_COLUMNS: TradeColumnDef[] = [
  { key: "entryDate", label: "Date", sortable: true, width: "120px" },
  { key: "instrument", label: "Instrument", sortable: true, width: "100px" },
  {
    key: "direction",
    label: "Side",
    sortable: true,
    width: "70px",
    align: "center",
  },
  {
    key: "status",
    label: "Status",
    sortable: true,
    width: "80px",
    align: "center",
  },
  {
    key: "pnlFormatted",
    label: "P&L",
    sortable: true,
    width: "100px",
    align: "right",
  },
  {
    key: "pnlPercent",
    label: "%",
    sortable: true,
    width: "70px",
    align: "right",
  },
  {
    key: "duration",
    label: "Duration",
    sortable: true,
    width: "90px",
    align: "right",
  },
];

export const DIRECTION_LABELS: Record<TradeDirection, string> = {
  long: "Long",
  short: "Short",
};

export const STATUS_LABELS: Record<TradeStatus, string> = {
  open: "Open",
  closed: "Closed",
  pending: "Pending",
};

export const OUTCOME_LABELS: Record<TradeOutcome, string> = {
  win: "Win",
  loss: "Loss",
  breakeven: "Break Even",
};

export const DIRECTION_COLORS: Record<TradeDirection, string> = {
  long: "text-green-500",
  short: "text-red-500",
};

export const OUTCOME_COLORS: Record<TradeOutcome, string> = {
  win: "text-green-500",
  loss: "text-red-500",
  breakeven: "text-muted-foreground",
};

export const STATUS_COLORS: Record<TradeStatus, string> = {
  open: "text-blue-500",
  closed: "text-muted-foreground",
  pending: "text-yellow-500",
};
