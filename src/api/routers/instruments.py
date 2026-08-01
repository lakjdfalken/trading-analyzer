"""
Instruments API router.

Provides endpoints for accessing available trading instruments.
"""

from typing import List

from fastapi import APIRouter, HTTPException

from api.models import Instrument
from api.services.database import db

router = APIRouter()

# Name patterns used to bucket an instrument into a display category.
INSTRUMENT_TYPE_PATTERNS = [
    (
        "index",
        [
            "us30",
            "wall street",
            "dow",
            "nasdaq",
            "s&p",
            "spx",
            "dax",
            "ftse",
            "uk 100",
            "germany",
        ],
    ),
    ("forex", ["eur/", "gbp/", "usd/", "jpy", "aud/", "nzd/", "cad/", "chf/"]),
    ("commodity", ["gold", "silver", "oil", "xau", "xag", "wti", "brent"]),
    ("crypto", ["btc", "eth", "bitcoin", "ethereum", "crypto"]),
]


def classify_instrument(name: str) -> str:
    """Classify an instrument name into a display category."""
    lowered = (name or "").lower()
    for instrument_type, patterns in INSTRUMENT_TYPE_PATTERNS:
        if any(p in lowered for p in patterns):
            return instrument_type
    return "stock"


def to_instrument_option(name: str) -> dict:
    """Build the option shape the frontend expects from an instrument name.

    db.get_available_instruments() returns plain names (List[str]); the API
    exposes them as {value, label, type} to match the Instrument model.
    """
    return {"value": name, "label": name, "type": classify_instrument(name)}


@router.get("", response_model=List[Instrument])
async def get_all_instruments():
    """
    Get all available trading instruments.

    Returns a list of instruments that have been traded,
    including their symbols and labels for display.

    Returns:
        List of available instruments
    """
    try:
        instruments = db.get_available_instruments()
        return [to_instrument_option(name) for name in instruments]
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error fetching instruments: {str(e)}"
        )


@router.get("/types")
async def get_instrument_types():
    """
    Get all available instrument types.

    Returns a list of instrument type categories.

    Returns:
        List of instrument types with counts
    """
    try:
        instruments = db.get_available_instruments()

        # Count instruments by type
        type_counts = {
            "index": 0,
            "forex": 0,
            "commodity": 0,
            "crypto": 0,
            "stock": 0,
        }

        for name in instruments:
            type_counts[classify_instrument(name)] += 1

        return [
            {"type": "index", "label": "Indices", "count": type_counts["index"]},
            {"type": "forex", "label": "Forex", "count": type_counts["forex"]},
            {
                "type": "commodity",
                "label": "Commodities",
                "count": type_counts["commodity"],
            },
            {"type": "crypto", "label": "Crypto", "count": type_counts["crypto"]},
            {"type": "stock", "label": "Stocks", "count": type_counts["stock"]},
        ]
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error fetching instrument types: {str(e)}"
        )


@router.get("/search")
async def search_instruments(q: str = ""):
    """
    Search for instruments by name.

    Args:
        q: Search query string

    Returns:
        List of matching instruments
    """
    try:
        if not q or len(q) < 2:
            return []

        instruments = db.get_available_instruments()

        # Filter instruments by search query
        query_lower = q.lower()
        matching = [name for name in instruments if query_lower in (name or "").lower()]

        return [to_instrument_option(name) for name in matching[:20]]
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error searching instruments: {str(e)}"
        )
