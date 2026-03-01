"""
API Models package.

Contains Pydantic schemas for request/response validation.
"""

from .schemas import (
    # Account Models
    AccountInfo,
    AccountTradeFrequency,
    # API Response Models
    APIResponse,
    # Chart Data Models
    BalanceDataPoint,
    BalanceHistoryResponse,
    DailyPnLDataPoint,
    # Trade Frequency Models
    DailyTradeCount,
    # Dashboard Models
    DashboardData,
    DashboardFilters,
    # Base Models
    DateRange,
    # Analytics Models
    DrawdownPeriod,
    ErrorResponse,
    # Funding Models
    FundingChargeByMarket,
    FundingDataPoint,
    FundingResponse,
    HourlyPerformance,
    # Instrument Models
    Instrument,
    # KPI Models
    KPIMetrics,
    MonthlyPnLDataPoint,
    MonthlyPnLResponse,
    MonthlyTradeCount,
    PaginatedResponse,
    # Pagination Models
    PaginationParams,
    RiskRewardData,
    SortOrder,
    SpreadCostByInstrument,
    # Spread Cost Models
    SpreadCostDataPoint,
    SpreadCostResponse,
    StreakData,
    # Trade Models
    Trade,
    TradeBase,
    TradeCreate,
    # Enums
    TradeDirection,
    TradeDurationStats,
    TradeFilters,
    TradeFrequencyResponse,
    TradeStatus,
    TradeUpdate,
    # Settings Models
    UserPreferences,
    WeekdayPerformance,
    WinRateByInstrument,
    YearlyTradeCount,
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
    # Funding Models
    "FundingChargeByMarket",
    "FundingDataPoint",
    "FundingResponse",
    # Spread Cost Models
    "SpreadCostDataPoint",
    "SpreadCostByInstrument",
    "SpreadCostResponse",
    # Trade Frequency Models
    "DailyTradeCount",
    "MonthlyTradeCount",
    "YearlyTradeCount",
    "AccountTradeFrequency",
    "TradeFrequencyResponse",
]
