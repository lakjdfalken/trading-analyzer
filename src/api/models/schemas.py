"""
Pydantic models for API request/response schemas.
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field

# Generic type for paginated responses
T = TypeVar("T")


# Enums
class TradeDirection(str, Enum):
    LONG = "long"
    SHORT = "short"


class TradeStatus(str, Enum):
    OPEN = "open"
    CLOSED = "closed"
    CANCELLED = "cancelled"


class SortOrder(str, Enum):
    ASC = "asc"
    DESC = "desc"


# Base Models
class DateRange(BaseModel):
    """Date range filter."""

    start_date: Optional[datetime] = Field(None, alias="from")
    end_date: Optional[datetime] = Field(None, alias="to")

    class Config:
        populate_by_name = True


# Trade Models
class TradeBase(BaseModel):
    """Base trade model."""

    instrument: str
    direction: TradeDirection
    entry_price: float = Field(alias="entryPrice")
    exit_price: Optional[float] = Field(None, alias="exitPrice")
    entry_time: datetime = Field(alias="entryTime")
    exit_time: Optional[datetime] = Field(None, alias="exitTime")
    quantity: float = 1.0
    pnl: float = 0.0
    pnl_percent: float = Field(0.0, alias="pnlPercent")
    currency: Optional[str] = None

    class Config:
        populate_by_name = True


class Trade(TradeBase):
    """Trade model with ID."""

    id: str
    status: TradeStatus = TradeStatus.CLOSED
    commission: Optional[float] = None
    swap: Optional[float] = None
    notes: Optional[str] = None
    tags: Optional[List[str]] = None

    class Config:
        from_attributes = True
        populate_by_name = True


class TradeCreate(TradeBase):
    """Model for creating a trade."""

    pass


class TradeUpdate(BaseModel):
    """Model for updating a trade."""

    exit_price: Optional[float] = None
    exit_time: Optional[datetime] = None
    pnl: Optional[float] = None
    pnl_percent: Optional[float] = None
    status: Optional[TradeStatus] = None
    notes: Optional[str] = None
    tags: Optional[List[str]] = None


# KPI Models
class KPIMetrics(BaseModel):
    """Key Performance Indicator metrics."""

    total_pnl: float = Field(alias="totalPnl")
    total_trades: int = Field(alias="totalTrades")
    winning_trades: int = Field(alias="winningTrades")
    losing_trades: int = Field(alias="losingTrades")
    win_rate: float = Field(alias="winRate")
    avg_win: float = Field(alias="avgWin")
    avg_loss: float = Field(alias="avgLoss")
    profit_factor: float = Field(alias="profitFactor")
    max_drawdown: float = Field(alias="maxDrawdown")
    avg_pnl_per_trade: float = Field(default=0.0, alias="avgPnlPerTrade")
    daily_avg_pnl: float = Field(default=0.0, alias="dailyAvgPnl")
    best_trade: float = Field(default=0.0, alias="bestTrade")
    worst_trade: float = Field(default=0.0, alias="worstTrade")
    max_balance: float = Field(default=0.0, alias="maxBalance")
    min_balance: float = Field(default=0.0, alias="minBalance")
    today_pnl: float = Field(default=0.0, alias="todayPnl")
    today_trades: int = Field(default=0, alias="todayTrades")
    week_pnl: float = Field(default=0.0, alias="weekPnl")
    week_trades: int = Field(default=0, alias="weekTrades")
    month_pnl: float = Field(default=0.0, alias="monthPnl")
    month_trades: int = Field(default=0, alias="monthTrades")
    month_win_rate: float = Field(default=0.0, alias="monthWinRate")
    year_pnl: float = Field(default=0.0, alias="yearPnl")
    year_trades: int = Field(default=0, alias="yearTrades")
    year_win_rate: float = Field(default=0.0, alias="yearWinRate")
    trading_days: int = Field(default=0, alias="tradingDays")
    currency: Optional[str] = None

    # Legacy fields for backward compatibility (optional)
    open_positions: Optional[int] = Field(default=0, alias="openPositions")
    total_exposure: Optional[float] = Field(default=0.0, alias="totalExposure")
    avg_trade_duration: Optional[int] = Field(default=0, alias="avgTradeDuration")
    avg_daily_pnl: Optional[float] = Field(default=0.0, alias="avgDailyPnl")
    avg_daily_points: Optional[float] = Field(default=0.0, alias="avgDailyPoints")
    avg_trades_per_day: Optional[float] = Field(default=0.0, alias="avgTradesPerDay")
    best_day_pnl: Optional[float] = Field(default=0.0, alias="bestDayPnl")
    worst_day_pnl: Optional[float] = Field(default=0.0, alias="worstDayPnl")
    avg_monthly_pnl: Optional[float] = Field(default=0.0, alias="avgMonthlyPnl")
    avg_monthly_points: Optional[float] = Field(default=0.0, alias="avgMonthlyPoints")
    avg_trades_per_month: Optional[float] = Field(
        default=0.0, alias="avgTradesPerMonth"
    )
    best_month_pnl: Optional[float] = Field(default=0.0, alias="bestMonthPnl")
    worst_month_pnl: Optional[float] = Field(default=0.0, alias="worstMonthPnl")
    current_year_pnl: Optional[float] = Field(default=0.0, alias="currentYearPnl")
    current_year_points: Optional[float] = Field(default=0.0, alias="currentYearPoints")
    avg_yearly_pnl: Optional[float] = Field(default=0.0, alias="avgYearlyPnl")

    class Config:
        populate_by_name = True


# Chart Data Models
class BalanceDataPoint(BaseModel):
    """Balance history data point."""

    date: str
    balance: float
    equity: Optional[float] = None
    drawdown: Optional[float] = None


class BalanceHistoryResponse(BaseModel):
    """Balance history response with currency info."""

    data: List["BalanceDataPoint"]
    currency: Optional[str] = None


class MonthlyPnLDataPoint(BaseModel):
    """Monthly P&L data point."""

    month: str
    pnl: float
    trades: int = 0
    win_rate: Optional[float] = Field(default=0.0, alias="winRate")

    class Config:
        populate_by_name = True


class MonthlyPnLResponse(BaseModel):
    """Monthly P&L response with currency info."""

    data: List["MonthlyPnLDataPoint"]
    currency: Optional[str] = None


class DailyPnLDataPoint(BaseModel):
    """Daily P&L data point."""

    date: str
    pnl: float
    trades: int
    cumulative_pnl: float = Field(alias="cumulativePnl")
    previous_balance: Optional[float] = Field(None, alias="previousBalance")
    pnl_percent: Optional[float] = Field(None, alias="pnlPercent")
    currency: Optional[str] = None

    class Config:
        populate_by_name = True


class WinRateByInstrument(BaseModel):
    """Win rate statistics per instrument."""

    name: str
    win_rate: float = Field(alias="winRate")
    wins: int
    losses: int
    trades: int
    total_pnl: Optional[float] = Field(None, alias="totalPnl")

    class Config:
        populate_by_name = True


class HourlyPerformance(BaseModel):
    """Performance by hour of day."""

    hour: int
    pnl: float
    trades: int
    win_rate: float = Field(alias="winRate")

    class Config:
        populate_by_name = True


class WeekdayPerformance(BaseModel):
    """Performance by day of week."""

    weekday: str
    pnl: float
    trades: int
    win_rate: float = Field(alias="winRate")

    class Config:
        populate_by_name = True


# Instrument Models
class Instrument(BaseModel):
    """Trading instrument."""

    value: str
    label: str
    type: Optional[str] = None  # index, forex, commodity, crypto, stock
    pip_value: Optional[float] = None
    contract_size: Optional[float] = None
    currency: Optional[str] = None


# Dashboard Models
class DashboardData(BaseModel):
    """Complete dashboard data response."""

    kpis: KPIMetrics
    balance_history: List[BalanceDataPoint] = Field(alias="balanceHistory")
    monthly_pnl: List[MonthlyPnLDataPoint] = Field(alias="monthlyPnL")
    win_rate_by_instrument: List[WinRateByInstrument] = Field(
        alias="winRateByInstrument"
    )
    recent_trades: List[Trade] = Field(alias="recentTrades")

    class Config:
        populate_by_name = True


# Filter Models
class TradeFilters(BaseModel):
    """Trade filter parameters."""

    instruments: Optional[List[str]] = None
    direction: Optional[TradeDirection] = None
    status: Optional[TradeStatus] = None
    start_date: Optional[datetime] = Field(None, alias="from")
    end_date: Optional[datetime] = Field(None, alias="to")
    min_pnl: Optional[float] = None
    max_pnl: Optional[float] = None
    tags: Optional[List[str]] = None

    class Config:
        populate_by_name = True


class DashboardFilters(BaseModel):
    """Dashboard filter parameters."""

    start_date: Optional[datetime] = Field(None, alias="from")
    end_date: Optional[datetime] = Field(None, alias="to")
    instruments: Optional[List[str]] = None
    account_id: Optional[int] = None

    class Config:
        populate_by_name = True


# Pagination Models
class PaginationParams(BaseModel):
    """Pagination parameters."""

    page: int = Field(1, ge=1)
    page_size: int = Field(50, ge=1, le=100, alias="pageSize")
    sort_by: Optional[str] = Field(None, alias="sortBy")
    sort_order: SortOrder = Field(SortOrder.DESC, alias="sortOrder")

    class Config:
        populate_by_name = True


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated response wrapper."""

    items: List[T]
    total: int
    page: int
    page_size: int = Field(alias="pageSize")
    total_pages: int = Field(alias="totalPages")

    class Config:
        populate_by_name = True


# Analytics Models
class DrawdownPeriod(BaseModel):
    """Drawdown period data."""

    start_date: str = Field(alias="startDate")
    end_date: Optional[str] = Field(None, alias="endDate")
    max_drawdown: float = Field(alias="maxDrawdown")
    max_drawdown_percent: float = Field(alias="maxDrawdownPercent")
    recovery_days: Optional[int] = Field(None, alias="recoveryDays")
    recovered: bool = False

    class Config:
        populate_by_name = True


class TradeDurationStats(BaseModel):
    """Trade duration statistics."""

    avg_duration_minutes: int = Field(alias="avgDurationMinutes")
    min_duration_minutes: int = Field(alias="minDurationMinutes")
    max_duration_minutes: int = Field(alias="maxDurationMinutes")
    avg_winner_duration: int = Field(alias="avgWinnerDuration")
    avg_loser_duration: int = Field(alias="avgLoserDuration")

    class Config:
        populate_by_name = True


class StreakData(BaseModel):
    """Win/loss streak data."""

    current_streak: int = Field(alias="currentStreak")
    current_streak_type: str = Field(alias="currentStreakType")  # "win" or "loss"
    max_win_streak: int = Field(alias="maxWinStreak")
    max_loss_streak: int = Field(alias="maxLossStreak")
    avg_win_streak: float = Field(alias="avgWinStreak")
    avg_loss_streak: float = Field(alias="avgLossStreak")

    class Config:
        populate_by_name = True


class RiskRewardData(BaseModel):
    """Risk/reward distribution data."""

    avg_risk_reward: float = Field(alias="avgRiskReward")
    trades_above_1rr: int = Field(alias="tradesAbove1RR")
    trades_above_2rr: int = Field(alias="tradesAbove2RR")
    trades_below_1rr: int = Field(alias="tradesBelow1RR")
    distribution: List[dict] = []

    class Config:
        populate_by_name = True


# Account Models
class AccountInfo(BaseModel):
    """Trading account information."""

    id: int
    name: str
    broker: str
    currency: str
    balance: float
    equity: Optional[float] = None
    margin: Optional[float] = None
    free_margin: Optional[float] = Field(None, alias="freeMargin")
    leverage: Optional[str] = None
    initial_balance: Optional[float] = Field(None, alias="initialBalance")

    class Config:
        populate_by_name = True


# Settings Models
class UserPreferences(BaseModel):
    """User preferences settings."""

    currency: str  # Required - no default per .rules

    class Config:
        populate_by_name = True


# API Response Models
class APIResponse(BaseModel, Generic[T]):
    """Standard API response wrapper."""

    data: T
    success: bool = True
    message: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ErrorResponse(BaseModel):
    """Error response model."""

    error: str
    code: str
    details: Optional[dict] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
