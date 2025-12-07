"""
Currency API router.

Provides endpoints for:
- Getting supported currencies
- Getting/updating exchange rates
- Managing user currency preferences
- Currency conversion
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from api.services.currency import CurrencyService

router = APIRouter()


# Request/Response Models
class CurrencyInfo(BaseModel):
    """Currency information."""

    code: str
    symbol: str
    name: str


class ExchangeRateUpdate(BaseModel):
    """Exchange rate update request."""

    from_currency: str = Field(alias="fromCurrency")
    to_currency: str = Field(alias="toCurrency")
    rate: float

    class Config:
        populate_by_name = True


class BulkRatesUpdate(BaseModel):
    """Bulk exchange rates update request."""

    base_currency: str = Field(default="SEK", alias="baseCurrency")
    rates: Dict[str, float]

    class Config:
        populate_by_name = True


class CurrencyPreferences(BaseModel):
    """User currency preferences."""

    default_currency: Optional[str] = Field(default=None, alias="defaultCurrency")
    show_converted: bool = Field(default=True, alias="showConverted")

    class Config:
        populate_by_name = True


class ConversionRequest(BaseModel):
    """Currency conversion request."""

    amount: float
    from_currency: str = Field(alias="fromCurrency")
    to_currency: str = Field(alias="toCurrency")

    class Config:
        populate_by_name = True


class ConversionResult(BaseModel):
    """Currency conversion result."""

    original_amount: float = Field(alias="originalAmount")
    original_currency: str = Field(alias="originalCurrency")
    converted_amount: float = Field(alias="convertedAmount")
    target_currency: str = Field(alias="targetCurrency")
    rate: float
    formatted_original: str = Field(alias="formattedOriginal")
    formatted_converted: str = Field(alias="formattedConverted")

    class Config:
        populate_by_name = True


class BrokerCurrencies(BaseModel):
    """Broker with associated currencies."""

    broker: str
    currencies: List[str]


class AccountCurrency(BaseModel):
    """Account currency information."""

    account_id: int = Field(alias="accountId")
    account_name: str = Field(alias="accountName")
    broker: str
    currency: str

    class Config:
        populate_by_name = True


# Endpoints
@router.get("/supported", response_model=List[CurrencyInfo])
async def get_supported_currencies():
    """Get list of all supported currencies."""
    return CurrencyService.get_supported_currencies()


@router.get("/in-use", response_model=List[str])
async def get_currencies_in_use():
    """Get list of currencies actually used in trading data."""
    return CurrencyService.get_currencies_in_use()


@router.get("/rates")
async def get_exchange_rates(
    base: str = Query(default="SEK", description="Base currency for rates"),
):
    """Get all exchange rates relative to a base currency."""
    rates = CurrencyService.get_all_exchange_rates(base)
    return {
        "baseCurrency": base,
        "rates": rates,
        "updatedAt": None,  # Could add timestamp tracking
    }


@router.get("/rates/{from_currency}/{to_currency}")
async def get_exchange_rate(from_currency: str, to_currency: str):
    """Get exchange rate between two specific currencies."""
    rate = CurrencyService.get_exchange_rate(from_currency, to_currency)
    if rate is None:
        raise HTTPException(
            status_code=404,
            detail=f"Exchange rate not found for {from_currency} to {to_currency}",
        )
    return {
        "fromCurrency": from_currency,
        "toCurrency": to_currency,
        "rate": rate,
    }


@router.put("/rates")
async def update_exchange_rate(update: ExchangeRateUpdate):
    """Update a single exchange rate."""
    success = CurrencyService.update_exchange_rate(
        update.from_currency, update.to_currency, update.rate, source="api"
    )
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update exchange rate")
    return {
        "success": True,
        "message": f"Updated rate: {update.from_currency} -> {update.to_currency} = {update.rate}",
    }


@router.put("/rates/bulk")
async def bulk_update_rates(update: BulkRatesUpdate):
    """Bulk update exchange rates relative to a base currency."""
    success = CurrencyService.bulk_update_rates(
        update.rates, update.base_currency, source="api"
    )
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update exchange rates")
    return {
        "success": True,
        "message": f"Updated {len(update.rates)} exchange rates",
        "baseCurrency": update.base_currency,
    }


@router.post("/convert", response_model=ConversionResult)
async def convert_currency(request: ConversionRequest):
    """Convert an amount between currencies."""
    rate = CurrencyService.get_exchange_rate(request.from_currency, request.to_currency)
    if rate is None:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot convert from {request.from_currency} to {request.to_currency}",
        )

    converted = request.amount * rate

    return ConversionResult(
        originalAmount=request.amount,
        originalCurrency=request.from_currency,
        convertedAmount=converted,
        targetCurrency=request.to_currency,
        rate=rate,
        formattedOriginal=CurrencyService.format_currency(
            request.amount, request.from_currency
        ),
        formattedConverted=CurrencyService.format_currency(
            converted, request.to_currency
        ),
    )


@router.get("/convert")
async def convert_currency_get(
    amount: float = Query(..., description="Amount to convert"),
    from_currency: str = Query(..., alias="from", description="Source currency"),
    to_currency: str = Query(..., alias="to", description="Target currency"),
):
    """Convert an amount between currencies (GET version)."""
    rate = CurrencyService.get_exchange_rate(from_currency, to_currency)
    if rate is None:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot convert from {from_currency} to {to_currency}",
        )

    converted = amount * rate

    return {
        "originalAmount": amount,
        "originalCurrency": from_currency,
        "convertedAmount": converted,
        "targetCurrency": to_currency,
        "rate": rate,
        "formattedOriginal": CurrencyService.format_currency(amount, from_currency),
        "formattedConverted": CurrencyService.format_currency(converted, to_currency),
    }


@router.get("/preferences", response_model=CurrencyPreferences)
async def get_currency_preferences():
    """Get user currency preferences."""
    return CurrencyPreferences(
        defaultCurrency=CurrencyService.get_default_currency(),
        showConverted=CurrencyService.get_show_converted(),
    )


@router.put("/preferences")
async def update_currency_preferences(prefs: CurrencyPreferences):
    """Update user currency preferences."""
    success_currency = CurrencyService.set_default_currency(prefs.default_currency)
    success_converted = CurrencyService.set_show_converted(prefs.show_converted)

    if not success_currency:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid currency: {prefs.default_currency}",
        )

    return {
        "success": True,
        "preferences": {
            "defaultCurrency": prefs.default_currency,
            "showConverted": prefs.show_converted,
        },
    }


@router.get("/preferences/default")
async def get_default_currency():
    """Get the default display currency."""
    return {
        "defaultCurrency": CurrencyService.get_default_currency(),
    }


@router.put("/preferences/default")
async def set_default_currency(currency: str = Query(..., description="Currency code")):
    """Set the default display currency."""
    success = CurrencyService.set_default_currency(currency)
    if not success:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid or unsupported currency: {currency}",
        )
    return {
        "success": True,
        "defaultCurrency": currency,
    }


@router.get("/brokers", response_model=List[BrokerCurrencies])
async def get_brokers_with_currencies():
    """Get list of brokers with their associated currencies."""
    return CurrencyService.get_brokers_with_currencies()


@router.get("/accounts", response_model=List[AccountCurrency])
async def get_account_currencies():
    """Get currencies associated with each account."""
    accounts = CurrencyService.get_account_currencies()
    return [
        AccountCurrency(
            accountId=acc["account_id"],
            accountName=acc["account_name"],
            broker=acc["broker"],
            currency=acc["currency"],
        )
        for acc in accounts
    ]


@router.get("/format")
async def format_currency(
    amount: float = Query(..., description="Amount to format"),
    currency: str = Query(..., description="Currency code"),
    include_symbol: bool = Query(True, alias="includeSymbol"),
    decimal_places: int = Query(2, alias="decimalPlaces"),
):
    """Format a currency amount."""
    return {
        "amount": amount,
        "currency": currency,
        "formatted": CurrencyService.format_currency(
            amount, currency, include_symbol, decimal_places
        ),
    }


@router.get("/format-with-conversion")
async def format_with_conversion(
    amount: float = Query(..., description="Amount to format"),
    original_currency: str = Query(..., alias="originalCurrency"),
    target_currency: str = Query(
        ..., alias="targetCurrency", description="Target currency (required)"
    ),
):
    """Format amount with optional conversion display."""

    result = CurrencyService.format_with_conversion(
        amount, original_currency, target_currency
    )
    return result
