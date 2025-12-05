"""
Analytics API router.

Provides endpoints for advanced analytics and performance metrics.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from api.models import (
    DailyPnLDataPoint,
    DrawdownPeriod,
    HourlyPerformance,
    RiskRewardData,
    StreakData,
    TradeDurationStats,
    WeekdayPerformance,
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
            key=lambda x: x.get("entry_time", "") or "",
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
            entry_time = trade.get("entry_time")
            exit_time = trade.get("exit_time")
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


class FundingDataPoint(BaseModel):
    """Funding data point for deposits/withdrawals chart."""

    date: str
    deposits: float
    withdrawals: float
    net: float
    cumulative: float


@router.get("/funding", response_model=List[FundingDataPoint])
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

        conditions = ["(\"Action\" = 'Fund receivable' OR \"Action\" = 'Fund payable')"]
        params: List[Any] = []

        if start_date:
            conditions.append('"Transaction Date" >= ?')
            params.append(start_date.strftime("%Y-%m-%d"))
        if end_date:
            conditions.append('"Transaction Date" <= ?')
            params.append(end_date.strftime("%Y-%m-%d"))
        if account_id:
            conditions.append("bt.account_id = ?")
            params.append(account_id)

        where_clause = " AND ".join(conditions)

        # Get account currencies for conversion
        query = f"""
            SELECT
                DATE(bt."Transaction Date") as date,
                SUM(CASE WHEN bt."Action" = 'Fund receivable' THEN COALESCE(bt."P/L", 0) ELSE 0 END) as deposits,
                SUM(CASE WHEN bt."Action" = 'Fund payable' THEN ABS(COALESCE(bt."P/L", 0)) ELSE 0 END) as withdrawals,
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
            account_currency = row[3] or currency

            # Convert to target currency if needed
            if account_currency != currency:
                rate = CurrencyService.get_exchange_rate(account_currency, currency)
                if rate:
                    deposits *= rate
                    withdrawals *= rate

            if date_str not in date_data:
                date_data[date_str] = {"deposits": 0, "withdrawals": 0}
            date_data[date_str]["deposits"] += deposits
            date_data[date_str]["withdrawals"] += withdrawals

        result = []
        cumulative = 0.0

        for date_str in sorted(date_data.keys()):
            data = date_data[date_str]
            deposits = data["deposits"]
            withdrawals = data["withdrawals"]
            net = deposits - withdrawals
            cumulative += net

            result.append(
                FundingDataPoint(
                    date=date_str,
                    deposits=round(deposits, 2),
                    withdrawals=round(withdrawals, 2),
                    net=round(net, 2),
                    cumulative=round(cumulative, 2),
                )
            )

        return result
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error fetching funding data: {str(e)}"
        )
