"""
Analytics API router.

Provides endpoints for advanced analytics and performance metrics.
"""

from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from api.models import (
    AccountTradeFrequency,
    DailyPnLDataPoint,
    DailyTradeCount,
    DrawdownPeriod,
    FundingChargeByMarket,
    FundingDataPoint,
    FundingResponse,
    HourlyPerformance,
    MonthlyTradeCount,
    RiskRewardData,
    SpreadCostByInstrument,
    SpreadCostDataPoint,
    SpreadCostResponse,
    StreakData,
    TradeDurationStats,
    TradeFrequencyResponse,
    WeekdayPerformance,
    YearlyTradeCount,
)
from api.services.database import db, get_db_connection

router = APIRouter()


@router.get("/daily-pnl", response_model=List[DailyPnLDataPoint])
async def get_daily_pnl(
    start_date: Optional[datetime] = Query(None, alias="from"),
    end_date: Optional[datetime] = Query(None, alias="to"),
    account_id: Optional[int] = Query(None, alias="accountId"),
    currency: str = Query(
        ..., description="Target currency for P&L conversion (required)"
    ),
):
    """
    Get daily P&L data for the date range. Currency parameter is required.

    Args:
        start_date: Start of date range
        end_date: End of date range
        currency: Target currency to convert all P&L values to (required)

    Returns:
        List of daily P&L data points with cumulative totals
    """
    try:
        daily_pnl = db.get_daily_pnl(
            start_date=start_date,
            end_date=end_date,
            target_currency=currency,
            account_id=account_id,
        )
        return daily_pnl
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error fetching daily P&L: {str(e)}"
        )


@router.get("/daily-pnl-by-account")
async def get_daily_pnl_by_account(
    start_date: Optional[datetime] = Query(None, alias="from"),
    end_date: Optional[datetime] = Query(None, alias="to"),
    account_id: Optional[int] = Query(None, alias="accountId"),
    currency: str = Query(
        ..., description="Target currency for P&L conversion (required)"
    ),
):
    """
    Get daily P&L data per account for multi-account charting.

    Args:
        start_date: Start of date range
        end_date: End of date range
        account_id: Filter to specific account
        currency: Target currency for P&L conversion

    Returns:
        Object with series (per account) and total (all accounts)
    """
    try:
        result = db.get_daily_pnl_by_account(
            start_date=start_date,
            end_date=end_date,
            target_currency=currency,
            account_id=account_id,
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error fetching daily P&L by account: {str(e)}"
        )


@router.get("/performance/hourly", response_model=List[HourlyPerformance])
async def get_hourly_performance(
    start_date: Optional[datetime] = Query(None, alias="from"),
    end_date: Optional[datetime] = Query(None, alias="to"),
    instruments: Optional[List[str]] = Query(None),
    account_id: Optional[int] = Query(None, alias="accountId"),
    currency: str = Query(
        ..., description="Target currency for P&L conversion (required)"
    ),
):
    """
    Get trading performance broken down by hour of day.

    Args:
        start_date: Start of date range
        end_date: End of date range
        instruments: Filter by specific instruments
        currency: Target currency for P&L conversion (required)

    Returns:
        List of performance metrics for each hour
    """
    from api.services.currency import CurrencyService

    try:
        trades, _ = db.get_all_trades(
            start_date=start_date,
            end_date=end_date,
            instruments=instruments,
            account_id=account_id,
        )

        # Aggregate by hour
        hourly_data = {}
        for i in range(24):
            hourly_data[i] = {"hour": i, "pnl": 0, "trades": 0, "wins": 0}

        for trade in trades:
            entry_time = trade.get("entryTime")
            if entry_time:
                try:
                    if isinstance(entry_time, str):
                        dt = datetime.fromisoformat(entry_time.replace("Z", "+00:00"))
                    else:
                        dt = entry_time
                    hour = dt.hour
                    pnl = trade.get("pnl", 0) or 0
                    trade_currency = trade.get("currency")

                    # Convert P&L to target currency
                    if trade_currency and trade_currency != currency:
                        converted = CurrencyService.convert(
                            pnl, trade_currency, currency
                        )
                        if converted is not None:
                            pnl = converted

                    hourly_data[hour]["pnl"] += pnl
                    hourly_data[hour]["trades"] += 1
                    if pnl >= 0:
                        hourly_data[hour]["wins"] += 1
                except (ValueError, AttributeError):
                    pass

        # Calculate win rates
        result = []
        for hour in range(24):
            data = hourly_data[hour]
            win_rate = (
                (data["wins"] / data["trades"] * 100) if data["trades"] > 0 else 0
            )
            result.append(
                {
                    "hour": hour,
                    "pnl": round(data["pnl"], 2),
                    "trades": data["trades"],
                    "winRate": round(win_rate, 1),
                }
            )

        return result
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error fetching hourly performance: {str(e)}"
        )


@router.get("/performance/weekday", response_model=List[WeekdayPerformance])
async def get_weekday_performance(
    start_date: Optional[datetime] = Query(None, alias="from"),
    end_date: Optional[datetime] = Query(None, alias="to"),
    instruments: Optional[List[str]] = Query(None),
    account_id: Optional[int] = Query(None, alias="accountId"),
    currency: str = Query(
        ..., description="Target currency for P&L conversion (required)"
    ),
):
    """
    Get trading performance broken down by day of week.

    Args:
        start_date: Start of date range
        end_date: End of date range
        instruments: Filter by specific instruments
        currency: Target currency for P&L conversion (required)

    Returns:
        List of performance metrics for each weekday
    """
    from api.services.currency import CurrencyService

    try:
        trades, _ = db.get_all_trades(
            start_date=start_date,
            end_date=end_date,
            instruments=instruments,
            account_id=account_id,
        )

        weekdays = [
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
            "Sunday",
        ]
        weekday_data = {
            day: {"weekday": day, "pnl": 0, "trades": 0, "wins": 0} for day in weekdays
        }

        for trade in trades:
            entry_time = trade.get("entryTime")
            if entry_time:
                try:
                    if isinstance(entry_time, str):
                        dt = datetime.fromisoformat(entry_time.replace("Z", "+00:00"))
                    else:
                        dt = entry_time
                    weekday = weekdays[dt.weekday()]
                    pnl = trade.get("pnl", 0) or 0
                    trade_currency = trade.get("currency")

                    # Convert P&L to target currency
                    if trade_currency and trade_currency != currency:
                        converted = CurrencyService.convert(
                            pnl, trade_currency, currency
                        )
                        if converted is not None:
                            pnl = converted

                    weekday_data[weekday]["pnl"] += pnl
                    weekday_data[weekday]["trades"] += 1
                    if pnl >= 0:
                        weekday_data[weekday]["wins"] += 1
                except (ValueError, AttributeError):
                    pass

        # Calculate win rates and build result
        result = []
        for day in weekdays:
            data = weekday_data[day]
            win_rate = (
                (data["wins"] / data["trades"] * 100) if data["trades"] > 0 else 0
            )
            result.append(
                {
                    "weekday": day,
                    "pnl": round(data["pnl"], 2),
                    "trades": data["trades"],
                    "winRate": round(win_rate, 1),
                }
            )

        return result
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error fetching weekday performance: {str(e)}"
        )


@router.get("/drawdown", response_model=List[DrawdownPeriod])
async def get_drawdown_periods(
    start_date: Optional[datetime] = Query(None, alias="from"),
    end_date: Optional[datetime] = Query(None, alias="to"),
    account_id: Optional[int] = Query(None, alias="accountId"),
):
    """
    Get drawdown periods and analysis.

    Args:
        start_date: Start of date range
        end_date: End of date range

    Returns:
        List of drawdown periods with recovery information
    """
    try:
        balance_history = db.get_balance_history(
            start_date=start_date,
            end_date=end_date,
            account_id=account_id,
        )

        if not balance_history:
            return []

        drawdown_periods = []
        peak = balance_history[0].get("balance", 0)
        peak_date = balance_history[0].get("date")
        in_drawdown = False
        current_drawdown_start = None
        max_drawdown_in_period = 0
        max_drawdown_percent_in_period = 0

        for point in balance_history:
            balance = point.get("balance", 0)
            date = point.get("date")

            if balance >= peak:
                # New peak or recovery
                if in_drawdown:
                    # Record the completed drawdown period
                    drawdown_periods.append(
                        {
                            "startDate": current_drawdown_start,
                            "endDate": date,
                            "maxDrawdown": round(max_drawdown_in_period, 2),
                            "maxDrawdownPercent": round(
                                max_drawdown_percent_in_period, 2
                            ),
                            "recoveryDays": None,  # Would need calculation
                            "recovered": True,
                        }
                    )
                    in_drawdown = False
                    max_drawdown_in_period = 0
                    max_drawdown_percent_in_period = 0

                peak = balance
                peak_date = date
            else:
                # In drawdown
                drawdown = peak - balance
                drawdown_percent = (drawdown / peak * 100) if peak > 0 else 0

                if not in_drawdown:
                    in_drawdown = True
                    current_drawdown_start = peak_date

                if drawdown > max_drawdown_in_period:
                    max_drawdown_in_period = drawdown
                    max_drawdown_percent_in_period = drawdown_percent

        # Handle ongoing drawdown
        if in_drawdown:
            drawdown_periods.append(
                {
                    "startDate": current_drawdown_start,
                    "endDate": None,
                    "maxDrawdown": round(max_drawdown_in_period, 2),
                    "maxDrawdownPercent": round(max_drawdown_percent_in_period, 2),
                    "recoveryDays": None,
                    "recovered": False,
                }
            )

        return drawdown_periods
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error fetching drawdown periods: {str(e)}"
        )


@router.get("/streaks", response_model=StreakData)
async def get_streak_data(
    start_date: Optional[datetime] = Query(None, alias="from"),
    end_date: Optional[datetime] = Query(None, alias="to"),
    instruments: Optional[List[str]] = Query(None),
    account_id: Optional[int] = Query(None, alias="accountId"),
):
    """
    Get win/loss streak analysis.

    Args:
        start_date: Start of date range
        end_date: End of date range
        instruments: Filter by specific instruments

    Returns:
        Streak statistics including current, max, and average streaks
    """
    try:
        trades, _ = db.get_all_trades(
            start_date=start_date,
            end_date=end_date,
            instruments=instruments,
            account_id=account_id,
        )

        if not trades:
            return {
                "currentStreak": 0,
                "currentStreakType": "none",
                "maxWinStreak": 0,
                "maxLossStreak": 0,
                "avgWinStreak": 0,
                "avgLossStreak": 0,
            }

        # Sort trades by date
        sorted_trades = sorted(
            trades,
            key=lambda x: x.get("entryTime", "") or "",
        )

        # Calculate streaks
        current_streak = 0
        current_type = None
        max_win_streak = 0
        max_loss_streak = 0
        win_streaks = []
        loss_streaks = []

        for trade in sorted_trades:
            pnl = trade.get("pnl", 0) or 0
            is_win = pnl >= 0

            if current_type is None:
                current_type = "win" if is_win else "loss"
                current_streak = 1
            elif (is_win and current_type == "win") or (
                not is_win and current_type == "loss"
            ):
                current_streak += 1
            else:
                # Streak broken
                if current_type == "win":
                    win_streaks.append(current_streak)
                    max_win_streak = max(max_win_streak, current_streak)
                else:
                    loss_streaks.append(current_streak)
                    max_loss_streak = max(max_loss_streak, current_streak)

                current_type = "win" if is_win else "loss"
                current_streak = 1

        # Handle the final streak
        if current_type == "win":
            win_streaks.append(current_streak)
            max_win_streak = max(max_win_streak, current_streak)
        elif current_type == "loss":
            loss_streaks.append(current_streak)
            max_loss_streak = max(max_loss_streak, current_streak)

        avg_win_streak = sum(win_streaks) / len(win_streaks) if win_streaks else 0
        avg_loss_streak = sum(loss_streaks) / len(loss_streaks) if loss_streaks else 0

        return {
            "currentStreak": current_streak,
            "currentStreakType": current_type or "none",
            "maxWinStreak": max_win_streak,
            "maxLossStreak": max_loss_streak,
            "avgWinStreak": round(avg_win_streak, 1),
            "avgLossStreak": round(avg_loss_streak, 1),
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error fetching streak data: {str(e)}"
        )


@router.get("/trade-duration", response_model=TradeDurationStats)
async def get_trade_duration_stats(
    start_date: Optional[datetime] = Query(None, alias="from"),
    end_date: Optional[datetime] = Query(None, alias="to"),
    instruments: Optional[List[str]] = Query(None),
    account_id: Optional[int] = Query(None, alias="accountId"),
):
    """
    Get trade duration statistics.

    Args:
        start_date: Start of date range
        end_date: End of date range
        instruments: Filter by specific instruments

    Returns:
        Statistics about trade holding times
    """
    try:
        trades, _ = db.get_all_trades(
            start_date=start_date,
            end_date=end_date,
            instruments=instruments,
            account_id=account_id,
        )

        durations = []
        winner_durations = []
        loser_durations = []

        for trade in trades:
            entry_time = trade.get("entryTime")
            exit_time = trade.get("exitTime")
            pnl = trade.get("pnl", 0) or 0

            if entry_time and exit_time:
                try:
                    if isinstance(entry_time, str):
                        entry_dt = datetime.fromisoformat(
                            entry_time.replace("Z", "+00:00")
                        )
                    else:
                        entry_dt = entry_time

                    if isinstance(exit_time, str):
                        exit_dt = datetime.fromisoformat(
                            exit_time.replace("Z", "+00:00")
                        )
                    else:
                        exit_dt = exit_time

                    duration_minutes = int((exit_dt - entry_dt).total_seconds() / 60)
                    if duration_minutes > 0:
                        durations.append(duration_minutes)
                        if pnl >= 0:
                            winner_durations.append(duration_minutes)
                        else:
                            loser_durations.append(duration_minutes)
                except (ValueError, AttributeError, TypeError):
                    pass

        if not durations:
            return {
                "avgDurationMinutes": 0,
                "minDurationMinutes": 0,
                "maxDurationMinutes": 0,
                "avgWinnerDuration": 0,
                "avgLoserDuration": 0,
            }

        return {
            "avgDurationMinutes": int(sum(durations) / len(durations)),
            "minDurationMinutes": min(durations),
            "maxDurationMinutes": max(durations),
            "avgWinnerDuration": (
                int(sum(winner_durations) / len(winner_durations))
                if winner_durations
                else 0
            ),
            "avgLoserDuration": (
                int(sum(loser_durations) / len(loser_durations))
                if loser_durations
                else 0
            ),
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error fetching trade duration stats: {str(e)}"
        )


@router.get("/summary")
async def get_analytics_summary(
    start_date: Optional[datetime] = Query(None, alias="from"),
    end_date: Optional[datetime] = Query(None, alias="to"),
    instruments: Optional[List[str]] = Query(None),
    account_id: Optional[int] = Query(None, alias="accountId"),
    currency: str = Query(
        ..., description="Target currency for P&L conversion (required)"
    ),
):
    """
    Get a comprehensive analytics summary.

    Args:
        start_date: Start of date range
        end_date: End of date range
        instruments: Filter by specific instruments

    Returns:
        Combined analytics data for the period
    """
    try:
        # Get KPIs
        kpis = db.get_kpi_metrics(
            start_date=start_date,
            end_date=end_date,
            instruments=instruments,
            target_currency=currency,
            account_id=account_id,
        )

        # Get daily P&L
        daily_pnl = db.get_daily_pnl(
            start_date=start_date,
            end_date=end_date,
            target_currency=currency,
            account_id=account_id,
        )

        # Get monthly P&L
        monthly_pnl = db.get_monthly_pnl(
            start_date=start_date,
            end_date=end_date,
            instruments=instruments,
            target_currency=currency,
            account_id=account_id,
        )

        # Get instrument breakdown
        instrument_stats = db.get_win_rate_by_instrument(
            start_date=start_date,
            end_date=end_date,
            account_id=account_id,
        )

        return {
            "kpis": kpis,
            "dailyPnl": daily_pnl,
            "monthlyPnl": monthly_pnl,
            "instrumentStats": instrument_stats,
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error fetching analytics summary: {str(e)}"
        )


@router.get("/position-size")
async def get_position_size_analysis(
    start_date: Optional[datetime] = Query(None, alias="from"),
    end_date: Optional[datetime] = Query(None, alias="to"),
    instruments: Optional[List[str]] = Query(None),
    account_id: Optional[int] = Query(None, alias="accountId"),
    currency: str = Query(
        ..., description="Target currency for P&L conversion (required)"
    ),
):
    """
    Get position size analysis data.

    Args:
        start_date: Start of date range
        end_date: End of date range
        instruments: Filter by specific instruments
        currency: Target currency for P&L conversion (required)

    Returns:
        Position size statistics and distribution
    """
    from api.services.currency import CurrencyService

    try:
        trades, _ = db.get_all_trades(
            start_date=start_date,
            end_date=end_date,
            instruments=instruments,
            account_id=account_id,
        )

        if not trades:
            return {
                "avgPositionSize": 0,
                "minPositionSize": 0,
                "maxPositionSize": 0,
                "avgWinnerSize": 0,
                "avgLoserSize": 0,
                "sizeDistribution": [],
                "sizePnLCorrelation": [],
            }

        # Extract position sizes (using quantity field, which is mapped from Amount)
        position_sizes = []
        winner_sizes = []
        loser_sizes = []
        size_pnl_data = []

        for trade in trades:
            size = abs(trade.get("quantity", 0) or 0)
            pnl = trade.get("pnl", 0) or 0
            trade_currency = trade.get("currency")

            # Convert P&L to target currency
            if trade_currency and trade_currency != currency:
                converted = CurrencyService.convert(pnl, trade_currency, currency)
                if converted is not None:
                    pnl = converted

            if size > 0:
                position_sizes.append(size)
                size_pnl_data.append({"size": size, "pnl": pnl})

                if pnl >= 0:
                    winner_sizes.append(size)
                else:
                    loser_sizes.append(size)

        if not position_sizes:
            return {
                "avgPositionSize": 0,
                "minPositionSize": 0,
                "maxPositionSize": 0,
                "avgWinnerSize": 0,
                "avgLoserSize": 0,
                "sizeDistribution": [],
                "sizePnLCorrelation": [],
            }

        # Calculate statistics
        avg_size = sum(position_sizes) / len(position_sizes)
        min_size = min(position_sizes)
        max_size = max(position_sizes)
        avg_winner = sum(winner_sizes) / len(winner_sizes) if winner_sizes else 0
        avg_loser = sum(loser_sizes) / len(loser_sizes) if loser_sizes else 0

        # Create size distribution buckets
        bucket_count = 10
        bucket_size = (max_size - min_size) / bucket_count if max_size > min_size else 1
        distribution = []

        for i in range(bucket_count):
            bucket_min = min_size + (i * bucket_size)
            bucket_max = min_size + ((i + 1) * bucket_size)
            bucket_trades = [s for s in position_sizes if bucket_min <= s < bucket_max]
            if i == bucket_count - 1:  # Include max in last bucket
                bucket_trades = [
                    s for s in position_sizes if bucket_min <= s <= bucket_max
                ]

            bucket_pnl = sum(
                d["pnl"]
                for d in size_pnl_data
                if (bucket_min <= d["size"] < bucket_max)
                or (i == bucket_count - 1 and bucket_min <= d["size"] <= bucket_max)
            )

            distribution.append(
                {
                    "range": f"{bucket_min:.0f}-{bucket_max:.0f}",
                    "rangeMin": bucket_min,
                    "rangeMax": bucket_max,
                    "count": len(bucket_trades),
                    "totalPnL": round(bucket_pnl, 2),
                    "avgPnL": round(bucket_pnl / len(bucket_trades), 2)
                    if bucket_trades
                    else 0,
                }
            )

        return {
            "avgPositionSize": round(avg_size, 2),
            "minPositionSize": round(min_size, 2),
            "maxPositionSize": round(max_size, 2),
            "avgWinnerSize": round(avg_winner, 2),
            "avgLoserSize": round(avg_loser, 2),
            "sizeDistribution": distribution,
            "sizePnLCorrelation": size_pnl_data[:100],  # Limit for performance
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error fetching position size analysis: {str(e)}"
        )


@router.get("/funding", response_model=FundingResponse)
async def get_funding_data(
    start_date: Optional[datetime] = Query(None, alias="from"),
    end_date: Optional[datetime] = Query(None, alias="to"),
    account_id: Optional[int] = Query(None, alias="accountId"),
    currency: str = Query(
        ..., description="Target currency for funding conversion (required)"
    ),
):
    """
    Get deposits and withdrawals data for the date range.

    Fund receivable = deposits (money coming in)
    Fund payable = withdrawals (money going out)

    Args:
        start_date: Start of date range
        end_date: End of date range

    Returns:
        List of funding data points with deposits, withdrawals, and cumulative totals
    """
    try:
        from api.services.currency import CurrencyService

        conditions = [
            "(\"Action\" = 'Fund receivable' OR \"Action\" = 'Fund payable' OR \"Action\" = 'Funding Charges')"
        ]
        params: List[Any] = []

        if start_date:
            conditions.append('"Transaction Date" >= ?')
            params.append(start_date.strftime("%Y-%m-%d"))
        if end_date:
            conditions.append('"Transaction Date" <= ?')
            params.append(end_date.strftime("%Y-%m-%d") + " 23:59:59")
        if account_id:
            conditions.append("bt.account_id = ?")
            params.append(account_id)
        else:
            # Filter to only accounts included in statistics
            from api.services.database import get_included_account_ids

            included_ids = get_included_account_ids()
            if included_ids:
                placeholders = ",".join("?" * len(included_ids))
                conditions.append(f"bt.account_id IN ({placeholders})")
                params.extend(included_ids)

        where_clause = " AND ".join(conditions)

        # Get account currencies for conversion
        query = f"""
            SELECT
                DATE(bt."Transaction Date") as date,
                SUM(CASE WHEN bt."Action" = 'Fund receivable' THEN COALESCE(bt."P/L", 0) ELSE 0 END) as deposits,
                SUM(CASE WHEN bt."Action" = 'Fund payable' THEN ABS(COALESCE(bt."P/L", 0)) ELSE 0 END) as withdrawals,
                SUM(CASE WHEN bt."Action" = 'Funding Charges' THEN ABS(COALESCE(bt."P/L", 0)) ELSE 0 END) as funding_charges,
                a.currency as account_currency
            FROM broker_transactions bt
            LEFT JOIN accounts a ON bt.account_id = a.account_id
            WHERE {where_clause}
            GROUP BY DATE(bt."Transaction Date"), a.currency
            ORDER BY date ASC
        """

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()

        # Aggregate by date with currency conversion
        date_data: Dict[str, Dict[str, float]] = {}

        for row in rows:
            date_str = row[0]
            deposits = float(row[1] or 0)
            withdrawals = float(row[2] or 0)
            funding_charges = float(row[3] or 0)
            account_currency = row[4] or currency

            # Convert to target currency if needed
            if account_currency != currency:
                rate = CurrencyService.get_exchange_rate(account_currency, currency)
                if rate:
                    deposits *= rate
                    withdrawals *= rate
                    funding_charges *= rate

            if date_str not in date_data:
                date_data[date_str] = {
                    "deposits": 0,
                    "withdrawals": 0,
                    "funding_charges": 0,
                }
            date_data[date_str]["deposits"] += deposits
            date_data[date_str]["withdrawals"] += withdrawals
            date_data[date_str]["funding_charges"] += funding_charges

        result = []
        cumulative = 0.0

        for date_str in sorted(date_data.keys()):
            data = date_data[date_str]
            deposits = data["deposits"]
            withdrawals = data["withdrawals"]
            funding_charges = data["funding_charges"]
            net = deposits - withdrawals - funding_charges
            cumulative += net

            result.append(
                FundingDataPoint(
                    date=date_str,
                    deposits=round(deposits, 2),
                    withdrawals=round(withdrawals, 2),
                    funding_charges=round(funding_charges, 2),
                    net=round(net, 2),
                    cumulative=round(cumulative, 2),
                )
            )

        # Get funding charges breakdown by market
        charges_conditions = ["\"Action\" = 'Funding Charges'"]
        charges_params: List[Any] = []

        if start_date:
            charges_conditions.append('"Transaction Date" >= ?')
            charges_params.append(start_date.strftime("%Y-%m-%d"))
        if end_date:
            charges_conditions.append('"Transaction Date" <= ?')
            charges_params.append(end_date.strftime("%Y-%m-%d") + " 23:59:59")
        if account_id:
            charges_conditions.append("bt.account_id = ?")
            charges_params.append(account_id)
        else:
            # Filter to only accounts included in statistics
            if included_ids:
                placeholders = ",".join("?" * len(included_ids))
                charges_conditions.append(f"bt.account_id IN ({placeholders})")
                charges_params.extend(included_ids)

        charges_where = " AND ".join(charges_conditions)

        charges_query = f"""
            SELECT
                bt."Description" as market,
                SUM(ABS(COALESCE(bt."P/L", 0))) as total_charges,
                COUNT(*) as count,
                a.currency as account_currency
            FROM broker_transactions bt
            LEFT JOIN accounts a ON bt.account_id = a.account_id
            WHERE {charges_where}
            GROUP BY bt."Description", a.currency
            ORDER BY total_charges DESC
        """

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(charges_query, charges_params)
            charges_rows = cursor.fetchall()

        # Aggregate by market with currency conversion
        market_data: Dict[str, Dict[str, float]] = {}
        total_funding_charges = 0.0

        for row in charges_rows:
            market = row[0] or "Unknown"
            total_charges = float(row[1] or 0)
            count = int(row[2] or 0)
            account_currency = row[3] or currency

            # Convert to target currency if needed
            if account_currency != currency:
                rate = CurrencyService.get_exchange_rate(account_currency, currency)
                if rate:
                    total_charges *= rate

            if market not in market_data:
                market_data[market] = {"total_charges": 0, "count": 0}
            market_data[market]["total_charges"] += total_charges
            market_data[market]["count"] += count
            total_funding_charges += total_charges

        charges_by_market = [
            FundingChargeByMarket(
                market=market,
                total_charges=round(data["total_charges"], 2),
                count=int(data["count"]),
            )
            for market, data in sorted(
                market_data.items(), key=lambda x: x[1]["total_charges"], reverse=True
            )
        ]

        return FundingResponse(
            daily=result,
            charges_by_market=charges_by_market,
            total_funding_charges=round(total_funding_charges, 2),
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error fetching funding data: {str(e)}"
        )


@router.get("/spread-cost")
async def get_spread_cost_analysis(
    start_date: Optional[datetime] = Query(None, alias="from"),
    end_date: Optional[datetime] = Query(None, alias="to"),
    account_id: Optional[int] = Query(None, alias="accountId"),
    currency: str = Query(
        ..., description="Target currency for spread cost calculation (required)"
    ),
):
    """
    Get spread cost analysis showing how much was spent on spreads.

    Spread cost = spread (points) × position size × point value

    Args:
        start_date: Start of date range
        end_date: End of date range
        account_id: Filter to specific account
        currency: Target currency for spread cost values

    Returns:
        Monthly breakdown and by-instrument breakdown of spread costs
    """
    try:
        from api.services.currency import CurrencyService
        from settings import (
            HISTORICAL_SPREADS,
            MARKET_SPREADS,
            get_instrument_spread_key,
            get_spread_for_time,
        )

        # Get the spread cost valid from date (when spread data became reliable)
        spread_cost_valid_from = CurrencyService.get_spread_cost_valid_from()

        conditions = ["(\"Action\" IN ('Trade Receivable', 'Trade Payable'))"]
        params: List[Any] = []

        # Apply spread_cost_valid_from as minimum date filter
        # If user-provided start_date is later, use that instead
        effective_start_date = None
        if spread_cost_valid_from:
            effective_start_date = spread_cost_valid_from
        if start_date:
            start_date_str = start_date.strftime("%Y-%m-%d")
            if effective_start_date is None or start_date_str > effective_start_date:
                effective_start_date = start_date_str

        if effective_start_date:
            conditions.append('"Transaction Date" >= ?')
            params.append(effective_start_date)
        if end_date:
            conditions.append('"Transaction Date" <= ?')
            params.append(end_date.strftime("%Y-%m-%d") + " 23:59:59")
        if account_id:
            conditions.append("account_id = ?")
            params.append(account_id)
        else:
            # Filter to only accounts included in statistics
            from api.services.database import get_included_account_ids

            included_ids = get_included_account_ids()
            if included_ids:
                placeholders = ",".join("?" * len(included_ids))
                conditions.append(f"account_id IN ({placeholders})")
                params.extend(included_ids)

        where_clause = " AND ".join(conditions)

        query = f"""
            SELECT
                "Transaction Date",
                "Open Period",
                "Description",
                "Amount",
                "Currency"
            FROM broker_transactions
            WHERE {where_clause}
            ORDER BY "Transaction Date" ASC
        """

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()

        # Calculate spread costs
        monthly_data: Dict[str, Dict[str, Any]] = {}
        instrument_data: Dict[str, Dict[str, Any]] = {}
        total_spread_cost = 0.0
        total_trades = 0

        for row in rows:
            tx_date = row[0]
            open_period = row[1]  # When the trade was opened
            description = row[2] or ""
            amount = abs(float(row[3] or 0))
            tx_currency = row[4] or "USD"

            if amount == 0:
                continue

            # Get instrument spread info
            spread_key = get_instrument_spread_key(description)
            if not spread_key:
                continue
            # Check if instrument exists in current or historical spreads
            has_spread_data = spread_key in MARKET_SPREADS or any(
                spread_key in hist for hist in HISTORICAL_SPREADS.values()
            )
            if not has_spread_data:
                continue

            # Extract date and time from open_period for opening spread lookup
            open_time = "12:00:00"  # Default to midday if no time available
            open_date = None
            if open_period:
                try:
                    if isinstance(open_period, str):
                        # Parse date and time from datetime string like "2025-10-09 19:28:33"
                        if " " in open_period:
                            open_date = open_period.split(" ")[0]
                            open_time = open_period.split(" ")[1]
                        elif "T" in open_period:
                            open_date = open_period.split("T")[0]
                            open_time = (
                                open_period.split("T")[1].split("+")[0].split("Z")[0]
                            )
                    else:
                        open_date = open_period.strftime("%Y-%m-%d")
                        open_time = open_period.strftime("%H:%M:%S")
                except (ValueError, AttributeError):
                    pass

            # Extract date and time from tx_date (Transaction Date) for closing spread lookup
            close_time = "12:00:00"  # Default to midday if no time available
            close_date = None
            if tx_date:
                try:
                    if isinstance(tx_date, str):
                        # Parse date and time from datetime string like "2025-10-09 19:28:33"
                        if " " in tx_date:
                            close_date = tx_date.split(" ")[0]
                            close_time = tx_date.split(" ")[1]
                        elif "T" in tx_date:
                            close_date = tx_date.split("T")[0]
                            close_time = (
                                tx_date.split("T")[1].split("+")[0].split("Z")[0]
                            )
                    else:
                        close_date = tx_date.strftime("%Y-%m-%d")
                        close_time = tx_date.strftime("%H:%M:%S")
                except (ValueError, AttributeError):
                    pass

            # Get spread at opening and closing times (with date for historical lookups)
            opening_spread = get_spread_for_time(spread_key, open_time, open_date)
            closing_spread = get_spread_for_time(spread_key, close_time, close_date)

            if opening_spread is None and closing_spread is None:
                continue

            # Use available spreads, defaulting to the other if one is missing
            if opening_spread is None:
                opening_spread = closing_spread
            if closing_spread is None:
                closing_spread = opening_spread

            # Spread cost = (half opening spread + half closing spread) × position size
            # You pay half the spread on entry (mid to ask/bid) and half on exit
            spread_cost = ((opening_spread / 2) + (closing_spread / 2)) * amount

            # Convert to target currency (spreads are in account currency)
            if tx_currency != currency:
                rate = CurrencyService.get_exchange_rate(tx_currency, currency)
                if rate:
                    spread_cost *= rate

            # Parse month
            if isinstance(tx_date, str):
                try:
                    dt = datetime.fromisoformat(tx_date.replace("Z", "+00:00"))
                except ValueError:
                    continue
            else:
                dt = tx_date

            month_key = dt.strftime("%Y-%m")
            month_label = dt.strftime("%b %Y")

            # Aggregate monthly
            if month_key not in monthly_data:
                monthly_data[month_key] = {
                    "month": month_label,
                    "month_key": month_key,
                    "spread_cost": 0.0,
                    "trades": 0,
                    "instruments": {},
                }
            monthly_data[month_key]["spread_cost"] += spread_cost
            monthly_data[month_key]["trades"] += 1

            # Track per instrument within month
            if spread_key not in monthly_data[month_key]["instruments"]:
                monthly_data[month_key]["instruments"][spread_key] = 0.0
            monthly_data[month_key]["instruments"][spread_key] += spread_cost

            # Aggregate by instrument
            if spread_key not in instrument_data:
                instrument_data[spread_key] = {
                    "instrument": spread_key,
                    "spread_cost": 0.0,
                    "trades": 0,
                }
            instrument_data[spread_key]["spread_cost"] += spread_cost
            instrument_data[spread_key]["trades"] += 1

            total_spread_cost += spread_cost
            total_trades += 1

        # Build response
        monthly_result = []
        for month_key in sorted(monthly_data.keys()):
            data = monthly_data[month_key]
            avg_spread = (
                data["spread_cost"] / data["trades"] if data["trades"] > 0 else 0
            )
            monthly_result.append(
                SpreadCostDataPoint(
                    month=data["month"],
                    month_key=data["month_key"],
                    spread_cost=round(data["spread_cost"], 2),
                    trades=data["trades"],
                    avg_spread_cost=round(avg_spread, 2),
                    instruments={
                        k: round(v, 2) for k, v in data["instruments"].items()
                    },
                )
            )

        instrument_result = []
        for inst_key in sorted(
            instrument_data.keys(),
            key=lambda x: instrument_data[x]["spread_cost"],
            reverse=True,
        ):
            data = instrument_data[inst_key]
            avg_spread = (
                data["spread_cost"] / data["trades"] if data["trades"] > 0 else 0
            )
            instrument_result.append(
                SpreadCostByInstrument(
                    instrument=data["instrument"],
                    spread_cost=round(data["spread_cost"], 2),
                    trades=data["trades"],
                    avg_spread_cost=round(avg_spread, 2),
                )
            )

        avg_spread_per_trade = (
            total_spread_cost / total_trades if total_trades > 0 else 0
        )

        return SpreadCostResponse(
            monthly=monthly_result,
            by_instrument=instrument_result,
            total_spread_cost=round(total_spread_cost, 2),
            total_trades=total_trades,
            avg_spread_per_trade=round(avg_spread_per_trade, 2),
            currency=currency,
            valid_from=spread_cost_valid_from,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error fetching spread cost analysis: {str(e)}"
        )


@router.get("/trade-frequency", response_model=TradeFrequencyResponse)
async def get_trade_frequency(
    start_date: Optional[datetime] = Query(None, alias="from"),
    end_date: Optional[datetime] = Query(None, alias="to"),
    account_id: Optional[int] = Query(None, alias="accountId"),
):
    """
    Get trade frequency analysis with daily, monthly, and yearly breakdowns.

    Args:
        start_date: Start of date range
        end_date: End of date range
        account_id: Filter by specific account

    Returns:
        Trade frequency data per account and aggregated
    """
    try:
        # Build WHERE clause for trades
        conditions = [
            "\"Action\" NOT LIKE '%Fund%'",
            "\"Action\" NOT LIKE '%Charge%'",
            "\"Action\" NOT LIKE '%Deposit%'",
            "\"Action\" NOT LIKE '%Withdraw%'",
        ]
        params: List[Any] = []

        if start_date:
            conditions.append('"Transaction Date" >= ?')
            params.append(start_date.isoformat())

        if end_date:
            conditions.append('"Transaction Date" <= ?')
            params.append(end_date.strftime("%Y-%m-%d") + " 23:59:59")

        if account_id:
            conditions.append("account_id = ?")
            params.append(account_id)
        else:
            # Filter to only accounts included in statistics
            from api.services.database import get_included_account_ids

            included_ids = get_included_account_ids()
            if included_ids:
                placeholders = ",".join("?" * len(included_ids))
                conditions.append(f"account_id IN ({placeholders})")
                params.extend(included_ids)

        where_clause = " AND ".join(conditions)

        # Query to get all trades with account info
        query = f"""
            SELECT
                DATE("Transaction Date") as trade_date,
                account_id,
                COALESCE(
                    (SELECT account_name FROM accounts a WHERE a.account_id = bt.account_id),
                    'Account ' || account_id
                ) as account_name,
                COUNT(*) as trade_count
            FROM broker_transactions bt
            WHERE {where_clause}
            GROUP BY DATE("Transaction Date"), account_id
            ORDER BY trade_date, account_id
        """

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, tuple(params))
            rows = cursor.fetchall()

        if not rows:
            empty_account = AccountTradeFrequency(
                account_id=0,
                account_name="All Accounts",
                daily=[],
                monthly=[],
                yearly=[],
                total_trades=0,
                total_trading_days=0,
                avg_trades_per_day=0,
                avg_trades_per_trading_day=0,
                avg_trades_per_month=0,
            )
            return TradeFrequencyResponse(
                by_account=[],
                aggregated=empty_account,
                date_range_days=0,
            )

        # Organize data by account
        account_data: Dict[int, Dict[str, Any]] = defaultdict(
            lambda: {
                "account_name": "",
                "daily": defaultdict(int),
                "monthly": defaultdict(lambda: {"trades": 0, "days": set()}),
                "yearly": defaultdict(
                    lambda: {"trades": 0, "days": set(), "months": set()}
                ),
            }
        )

        # Aggregated data
        agg_daily: Dict[str, int] = defaultdict(int)
        agg_monthly: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {"trades": 0, "days": set()}
        )
        agg_yearly: Dict[int, Dict[str, Any]] = defaultdict(
            lambda: {"trades": 0, "days": set(), "months": set()}
        )

        all_dates: set = set()

        for row in rows:
            trade_date = row[0]
            acc_id = row[1]
            acc_name = row[2]
            trade_count = row[3]

            # Parse date components
            year = int(trade_date[:4])
            month = trade_date[:7]  # YYYY-MM

            # Per-account data
            account_data[acc_id]["account_name"] = acc_name
            account_data[acc_id]["daily"][trade_date] += trade_count
            account_data[acc_id]["monthly"][month]["trades"] += trade_count
            account_data[acc_id]["monthly"][month]["days"].add(trade_date)
            account_data[acc_id]["yearly"][year]["trades"] += trade_count
            account_data[acc_id]["yearly"][year]["days"].add(trade_date)
            account_data[acc_id]["yearly"][year]["months"].add(month)

            # Aggregated data
            agg_daily[trade_date] += trade_count
            agg_monthly[month]["trades"] += trade_count
            agg_monthly[month]["days"].add(trade_date)
            agg_yearly[year]["trades"] += trade_count
            agg_yearly[year]["days"].add(trade_date)
            agg_yearly[year]["months"].add(month)

            all_dates.add(trade_date)

        # Calculate date range
        if all_dates:
            min_date = min(all_dates)
            max_date = max(all_dates)
            from datetime import date as dt_date

            d1 = dt_date.fromisoformat(min_date)
            d2 = dt_date.fromisoformat(max_date)
            date_range_days = (d2 - d1).days + 1
        else:
            date_range_days = 0

        # Build per-account responses
        by_account: List[AccountTradeFrequency] = []

        for acc_id, data in sorted(account_data.items()):
            daily_list = [
                DailyTradeCount(date=d, trades=t)
                for d, t in sorted(data["daily"].items())
            ]
            monthly_list = [
                MonthlyTradeCount(
                    month=m, trades=info["trades"], trading_days=len(info["days"])
                )
                for m, info in sorted(data["monthly"].items())
            ]
            yearly_list = [
                YearlyTradeCount(
                    year=y,
                    trades=info["trades"],
                    trading_days=len(info["days"]),
                    trading_months=len(info["months"]),
                )
                for y, info in sorted(data["yearly"].items())
            ]

            total_trades = sum(d.trades for d in daily_list)
            total_trading_days = len(data["daily"])
            total_months = len(data["monthly"])

            avg_trades_per_day = (
                total_trades / date_range_days if date_range_days > 0 else 0
            )
            avg_trades_per_trading_day = (
                total_trades / total_trading_days if total_trading_days > 0 else 0
            )
            avg_trades_per_month = (
                total_trades / total_months if total_months > 0 else 0
            )

            by_account.append(
                AccountTradeFrequency(
                    account_id=acc_id,
                    account_name=data["account_name"],
                    daily=daily_list,
                    monthly=monthly_list,
                    yearly=yearly_list,
                    total_trades=total_trades,
                    total_trading_days=total_trading_days,
                    avg_trades_per_day=round(avg_trades_per_day, 2),
                    avg_trades_per_trading_day=round(avg_trades_per_trading_day, 2),
                    avg_trades_per_month=round(avg_trades_per_month, 2),
                )
            )

        # Build aggregated response
        agg_daily_list = [
            DailyTradeCount(date=d, trades=t) for d, t in sorted(agg_daily.items())
        ]
        agg_monthly_list = [
            MonthlyTradeCount(
                month=m, trades=info["trades"], trading_days=len(info["days"])
            )
            for m, info in sorted(agg_monthly.items())
        ]
        agg_yearly_list = [
            YearlyTradeCount(
                year=y,
                trades=info["trades"],
                trading_days=len(info["days"]),
                trading_months=len(info["months"]),
            )
            for y, info in sorted(agg_yearly.items())
        ]

        agg_total_trades = sum(d.trades for d in agg_daily_list)
        agg_total_trading_days = len(agg_daily)
        agg_total_months = len(agg_monthly)

        agg_avg_trades_per_day = (
            agg_total_trades / date_range_days if date_range_days > 0 else 0
        )
        agg_avg_trades_per_trading_day = (
            agg_total_trades / agg_total_trading_days
            if agg_total_trading_days > 0
            else 0
        )
        agg_avg_trades_per_month = (
            agg_total_trades / agg_total_months if agg_total_months > 0 else 0
        )

        aggregated = AccountTradeFrequency(
            account_id=0,
            account_name="All Accounts",
            daily=agg_daily_list,
            monthly=agg_monthly_list,
            yearly=agg_yearly_list,
            total_trades=agg_total_trades,
            total_trading_days=agg_total_trading_days,
            avg_trades_per_day=round(agg_avg_trades_per_day, 2),
            avg_trades_per_trading_day=round(agg_avg_trades_per_trading_day, 2),
            avg_trades_per_month=round(agg_avg_trades_per_month, 2),
        )

        return TradeFrequencyResponse(
            by_account=by_account,
            aggregated=aggregated,
            date_range_days=date_range_days,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error fetching trade frequency: {str(e)}"
        )
