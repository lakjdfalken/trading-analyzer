"""
Instruments API router.

Provides endpoints for accessing available trading instruments.
"""

from typing import List

from fastapi import APIRouter, HTTPException

from api.models import Instrument
from api.services.database import db

router = APIRouter()


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

        # Add instrument type classification based on name patterns
        for instrument in instruments:
            name = instrument.get("value", "").lower()

            if any(
                x in name
                for x in [
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
                ]
            ):
                instrument["type"] = "index"
            elif any(
                x in name
                for x in ["eur/", "gbp/", "usd/", "jpy", "aud/", "nzd/", "cad/", "chf/"]
            ):
                instrument["type"] = "forex"
            elif any(
                x in name
                for x in ["gold", "silver", "oil", "xau", "xag", "wti", "brent"]
            ):
                instrument["type"] = "commodity"
            elif any(
                x in name for x in ["btc", "eth", "bitcoin", "ethereum", "crypto"]
            ):
                instrument["type"] = "crypto"
            else:
                instrument["type"] = "stock"

        return instruments
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

        for instrument in instruments:
            name = instrument.get("value", "").lower()

            if any(
                x in name
                for x in [
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
                ]
            ):
                type_counts["index"] += 1
            elif any(
                x in name
                for x in ["eur/", "gbp/", "usd/", "jpy", "aud/", "nzd/", "cad/", "chf/"]
            ):
                type_counts["forex"] += 1
            elif any(
                x in name
                for x in ["gold", "silver", "oil", "xau", "xag", "wti", "brent"]
            ):
                type_counts["commodity"] += 1
            elif any(
                x in name for x in ["btc", "eth", "bitcoin", "ethereum", "crypto"]
            ):
                type_counts["crypto"] += 1
            else:
                type_counts["stock"] += 1

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
        matching = [
            inst
            for inst in instruments
            if query_lower in inst.get("value", "").lower()
            or query_lower in inst.get("label", "").lower()
        ]

        return matching[:20]  # Limit to 20 results
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error searching instruments: {str(e)}"
        )
