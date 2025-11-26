"""
API Models package.

Contains Pydantic schemas for request/response validation.
"""

from .schemas import (
    # Account Models
    AccountInfo,
    # API Response Models
    APIResponse,
    # Chart Data Models
    BalanceDataPoint,
    BalanceHistoryResponse,
    DailyPnLDataPoint,
    # Dashboard Models
    DashboardData,
    DashboardFilters,
    # Base Models
    DateRange,
    # Analytics Models
    DrawdownPeriod,
    ErrorResponse,
    HourlyPerformance,
    # Instrument Models
    Instrument,
    # KPI Models
    KPIMetrics,
    MonthlyPnLDataPoint,
    MonthlyPnLResponse,
    PaginatedResponse,
    # Pagination Models
    PaginationParams,
    RiskRewardData,
    SortOrder,
    StreakData,
    # Trade Models
    Trade,
    TradeBase,
    TradeCreate,
    # Enums
    TradeDirection,
    TradeDurationStats,
    TradeFilters,
    TradeStatus,
    TradeUpdate,
    # Settings Models
    UserPreferences,
    WeekdayPerformance,
    WinRateByInstrument,
)

__all__ = [
    # Enums
    "TradeDirection",
    "TradeStatus",
    "SortOrder",
    # Base Models
    "DateRange",
    # Trade Models
    "Trade",
    "TradeBase",
    "TradeCreate",
    "TradeUpdate",
    "TradeFilters",
    # KPI Models
    "KPIMetrics",
    # Chart Data Models
    "BalanceDataPoint",
    "BalanceHistoryResponse",
    "MonthlyPnLDataPoint",
    "MonthlyPnLResponse",
    "DailyPnLDataPoint",
    "WinRateByInstrument",
    "HourlyPerformance",
    "WeekdayPerformance",
    # Instrument Models
    "Instrument",
    # Dashboard Models
    "DashboardData",
    "DashboardFilters",
    # Pagination Models
    "PaginationParams",
    "PaginatedResponse",
    # Analytics Models
    "DrawdownPeriod",
    "TradeDurationStats",
    "StreakData",
    "RiskRewardData",
    # Account Models
    "AccountInfo",
    # Settings Models
    "UserPreferences",
    # API Response Models
    "APIResponse",
    "ErrorResponse",
]
