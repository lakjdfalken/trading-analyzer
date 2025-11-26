"""
API Routers package.

Contains FastAPI router definitions for different API endpoints.
"""

from . import analytics, dashboard, instruments, trades

__all__ = [
    "dashboard",
    "trades",
    "instruments",
    "analytics",
]
