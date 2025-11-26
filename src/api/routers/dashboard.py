"""
Dashboard API router.

Provides endpoints for dashboard data including KPIs, charts, and summaries.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query

from api.models import (
    BalanceDataPoint,
    BalanceHistoryResponse,
    DashboardData,
    KPIMetrics,
    MonthlyPnLDataPoint,
    MonthlyPnLResponse,
    Trade,
    WinRateByInstrument,
)
from api.services.database import db

router = APIRouter()


@router.get("", response_model=DashboardData)
async def get_dashboard_data(
    start_date: Optional[datetime] = Query(None, alias="from"),
    end_date: Optional[datetime] = Query(None, alias="to"),
    instruments: Optional[List[str]] = Query(None),
    account_id: Optional[int] = Query(None),
):
    """
    Get all dashboard data in a single request.

    Returns KPIs, balance history, monthly P&L, win rate by instrument,
    and recent trades.
    """
    try:
        # Get KPIs
        kpis = db.get_kpi_metrics(
            start_date=start_date,
            end_date=end_date,
            instruments=instruments,
        )

        # Get balance history
        balance_history = db.get_balance_history(
            start_date=start_date,
            end_date=end_date,
            account_id=account_id,
        )

        # Get monthly P&L
        monthly_pnl = db.get_monthly_pnl(
            start_date=start_date,
            end_date=end_date,
            instruments=instruments,
        )

        # Get win rate by instrument
        win_rate_by_instrument = db.get_win_rate_by_instrument(
            start_date=start_date,
            end_date=end_date,
        )

        # Get recent trades
        recent_trades = db.get_recent_trades(
            limit=10,
            start_date=start_date,
            end_date=end_date,
            instruments=instruments,
        )

        return {
            "kpis": kpis,
            "balanceHistory": balance_history.get("data", [])
            if isinstance(balance_history, dict)
            else balance_history,
            "monthlyPnL": monthly_pnl.get("data", [])
            if isinstance(monthly_pnl, dict)
            else monthly_pnl,
            "winRateByInstrument": win_rate_by_instrument,
            "recentTrades": recent_trades,
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error fetching dashboard data: {str(e)}"
        )


@router.get("/kpis", response_model=KPIMetrics)
async def get_kpis(
    start_date: Optional[datetime] = Query(None, alias="from"),
    end_date: Optional[datetime] = Query(None, alias="to"),
    instruments: Optional[List[str]] = Query(None),
):
    """Get KPI metrics for the dashboard."""
    try:
        kpis = db.get_kpi_metrics(
            start_date=start_date,
            end_date=end_date,
            instruments=instruments,
        )
        return kpis
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching KPIs: {str(e)}")


@router.get("/balance", response_model=BalanceHistoryResponse)
async def get_balance_history(
    start_date: Optional[datetime] = Query(None, alias="from"),
    end_date: Optional[datetime] = Query(None, alias="to"),
    account_id: Optional[int] = Query(None),
):
    """Get balance history for the equity curve chart."""
    try:
        result = db.get_balance_history(
            start_date=start_date,
            end_date=end_date,
            account_id=account_id,
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error fetching balance history: {str(e)}"
        )


@router.get("/monthly-pnl", response_model=MonthlyPnLResponse)
async def get_monthly_pnl(
    start_date: Optional[datetime] = Query(None, alias="from"),
    end_date: Optional[datetime] = Query(None, alias="to"),
    instruments: Optional[List[str]] = Query(None),
):
    """Get monthly P&L data for the bar chart."""
    try:
        result = db.get_monthly_pnl(
            start_date=start_date,
            end_date=end_date,
            instruments=instruments,
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error fetching monthly P&L: {str(e)}"
        )


@router.get("/win-rate-by-instrument", response_model=List[WinRateByInstrument])
async def get_win_rate_by_instrument(
    start_date: Optional[datetime] = Query(None, alias="from"),
    end_date: Optional[datetime] = Query(None, alias="to"),
):
    """Get win rate statistics grouped by instrument."""
    try:
        win_rate_data = db.get_win_rate_by_instrument(
            start_date=start_date,
            end_date=end_date,
        )
        return win_rate_data
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error fetching win rate data: {str(e)}"
        )


@router.get("/balance-by-account")
async def get_balance_history_by_account(
    start_date: Optional[datetime] = Query(None, alias="from"),
    end_date: Optional[datetime] = Query(None, alias="to"),
) -> Dict[str, Any]:
    """Get balance history grouped by account for multi-account charting."""
    try:
        result = db.get_balance_history_by_account(
            start_date=start_date,
            end_date=end_date,
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error fetching balance by account: {str(e)}"
        )


@router.get("/monthly-pnl-by-account")
async def get_monthly_pnl_by_account(
    start_date: Optional[datetime] = Query(None, alias="from"),
    end_date: Optional[datetime] = Query(None, alias="to"),
) -> Dict[str, Any]:
    """Get monthly P&L grouped by account for multi-account charting."""
    try:
        result = db.get_monthly_pnl_by_account(
            start_date=start_date,
            end_date=end_date,
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error fetching monthly P&L by account: {str(e)}"
        )
