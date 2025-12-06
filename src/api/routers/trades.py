"""
Trades API router.

Provides endpoints for accessing and managing trade data.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from api.models import PaginatedResponse, Trade
from api.services.currency import CurrencyService
from api.services.database import db


def serialize_trade(trade_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Convert a trade dict to camelCase format for API response."""
    return {
        "id": trade_dict.get("id", ""),
        "instrument": trade_dict.get("instrument", ""),
        "direction": trade_dict.get("direction", "long"),
        "entryPrice": trade_dict.get("entryPrice", 0)
        or trade_dict.get("entry_price", 0)
        or 0,
        "exitPrice": trade_dict.get("exitPrice") or trade_dict.get("exit_price") or 0,
        "entryTime": trade_dict.get("entryTime") or trade_dict.get("entry_time") or "",
        "exitTime": trade_dict.get("exitTime") or trade_dict.get("exit_time") or "",
        "quantity": trade_dict.get("quantity", 1) or 1,
        "pnl": trade_dict.get("pnl", 0) or 0,
        "pnlPercent": trade_dict.get("pnlPercent", 0)
        or trade_dict.get("pnl_percent", 0)
        or 0,
        "currency": trade_dict.get("currency"),
        "status": trade_dict.get("status", "closed"),
        "commission": trade_dict.get("commission"),
        "swap": trade_dict.get("swap"),
        "notes": trade_dict.get("notes"),
        "tags": trade_dict.get("tags"),
    }


def convert_trade_currency(
    trade_dict: Dict[str, Any], target_currency: str
) -> Dict[str, Any]:
    """Convert trade P&L to target currency."""
    trade_currency = trade_dict.get("currency")

    if not trade_currency or trade_currency == target_currency:
        trade_dict["currency"] = target_currency
        return trade_dict

    pnl = trade_dict.get("pnl", 0) or 0
    converted_pnl = CurrencyService.convert(pnl, trade_currency, target_currency)

    if converted_pnl is not None:
        trade_dict["pnl"] = converted_pnl
        trade_dict["currency"] = target_currency

    return trade_dict


router = APIRouter()


@router.get("/recent", response_model=List[Trade])
async def get_recent_trades(
    limit: int = Query(10, ge=1, le=500),
    start_date: Optional[datetime] = Query(None, alias="from"),
    end_date: Optional[datetime] = Query(None, alias="to"),
    instruments: Optional[List[str]] = Query(None),
    account_id: Optional[int] = Query(None, alias="accountId"),
    currency: str = Query(
        ..., description="Target currency for P&L conversion (required)"
    ),
):
    """
    Get the most recent trades.

    Args:
        limit: Maximum number of trades to return (1-500)
        start_date: Filter trades from this date
        end_date: Filter trades until this date
        instruments: Filter by specific instruments
        account_id: Filter by specific account (default: all accounts)
        currency: Target currency for P&L conversion

    Returns:
        List of recent trades
    """
    try:
        trades = db.get_recent_trades(
            limit=limit,
            start_date=start_date,
            end_date=end_date,
            instruments=instruments,
            account_id=account_id,
        )

        # Convert P&L to target currency
        trades = [convert_trade_currency(t, currency) for t in trades]

        # Serialize to camelCase for frontend
        return [serialize_trade(t) for t in trades]
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error fetching recent trades: {str(e)}"
        )


@router.get("", response_model=Dict)
async def get_all_trades(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100, alias="pageSize"),
    start_date: Optional[datetime] = Query(None, alias="from"),
    end_date: Optional[datetime] = Query(None, alias="to"),
    instruments: Optional[List[str]] = Query(None),
    direction: Optional[str] = Query(None),
    sort_by: Optional[str] = Query("entryTime", alias="sortBy"),
    sort_order: Optional[str] = Query("desc", alias="sortOrder"),
    currency: str = Query(
        ..., description="Target currency for P&L conversion (required)"
    ),
):
    """
    Get paginated list of all trades with optional filters.

    Args:
        page: Page number (starts at 1)
        page_size: Number of trades per page (1-100)
        start_date: Filter trades from this date
        end_date: Filter trades until this date
        instruments: Filter by specific instruments
        direction: Filter by trade direction (long/short)
        sort_by: Field to sort by
        sort_order: Sort order (asc/desc)
        currency: Target currency for P&L conversion

    Returns:
        Paginated response with trades, total count, and page info
    """
    try:
        offset = (page - 1) * page_size

        trades, total = db.get_all_trades(
            start_date=start_date,
            end_date=end_date,
            instruments=instruments,
            limit=page_size,
            offset=offset,
        )

        # Filter by direction if specified
        if direction:
            trades = [t for t in trades if t.get("direction") == direction]

        # Convert P&L to target currency
        trades = [convert_trade_currency(t, currency) for t in trades]

        total_pages = (total + page_size - 1) // page_size

        return {
            "trades": [serialize_trade(t) for t in trades],
            "total": total,
            "page": page,
            "pageSize": page_size,
            "pages": total_pages,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching trades: {str(e)}")


@router.get("/{trade_id}", response_model=Trade)
async def get_trade_by_id(trade_id: str):
    """
    Get a single trade by its ID.

    Args:
        trade_id: The unique identifier of the trade

    Returns:
        Trade details
    """
    try:
        trade = db.get_trade_by_id(trade_id)
        if not trade:
            raise HTTPException(status_code=404, detail="Trade not found")
        return serialize_trade(trade)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching trade: {str(e)}")


@router.get("/stats/summary")
async def get_trade_stats(
    start_date: Optional[datetime] = Query(None, alias="from"),
    end_date: Optional[datetime] = Query(None, alias="to"),
    instruments: Optional[List[str]] = Query(None),
):
    """
    Get summary statistics for trades.

    Args:
        start_date: Filter trades from this date
        end_date: Filter trades until this date
        instruments: Filter by specific instruments

    Returns:
        Summary statistics including total trades, P&L, win rate, etc.
    """
    try:
        trades, total = db.get_all_trades(
            start_date=start_date,
            end_date=end_date,
            instruments=instruments,
        )

        if not trades:
            return {
                "totalTrades": 0,
                "totalPnl": 0,
                "winRate": 0,
                "avgPnl": 0,
                "avgWin": 0,
                "avgLoss": 0,
                "largestWin": 0,
                "largestLoss": 0,
                "longTrades": 0,
                "shortTrades": 0,
            }

        pnls = [t.get("pnl", 0) or 0 for t in trades]
        wins = [p for p in pnls if p >= 0]
        losses = [p for p in pnls if p < 0]

        long_trades = len([t for t in trades if t.get("direction") == "long"])
        short_trades = len([t for t in trades if t.get("direction") == "short"])

        return {
            "totalTrades": total,
            "totalPnl": round(sum(pnls), 2),
            "winRate": round(len(wins) / len(pnls) * 100, 1) if pnls else 0,
            "avgPnl": round(sum(pnls) / len(pnls), 2) if pnls else 0,
            "avgWin": round(sum(wins) / len(wins), 2) if wins else 0,
            "avgLoss": round(sum(losses) / len(losses), 2) if losses else 0,
            "largestWin": round(max(wins), 2) if wins else 0,
            "largestLoss": round(min(losses), 2) if losses else 0,
            "longTrades": long_trades,
            "shortTrades": short_trades,
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error calculating trade stats: {str(e)}"
        )
