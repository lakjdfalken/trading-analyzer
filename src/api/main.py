"""
Trading Analyzer API

FastAPI backend for the Trading Analyzer frontend.
Provides endpoints for dashboard data, trades, KPIs, and analytics.
"""

import os
import sys
from contextlib import asynccontextmanager
from contextvars import ContextVar
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from api import __version__

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sqlite3

from api.routers import analytics, currency, dashboard, imports, instruments, trades
from db_path import DATABASE_PATH

# Determine paths
API_DIR = Path(__file__).parent
SRC_DIR = API_DIR.parent
ROOT_DIR = SRC_DIR.parent
FRONTEND_OUT_DIR = ROOT_DIR / "frontend" / "out"

# Context variable for request-scoped caching of included account IDs
_included_account_ids_cache: ContextVar[Optional[List[int]]] = ContextVar(
    "included_account_ids_cache", default=None
)


def get_cached_included_account_ids() -> Optional[List[int]]:
    """Get cached included account IDs for current request."""
    return _included_account_ids_cache.get()


def set_cached_included_account_ids(ids: List[int]) -> None:
    """Cache included account IDs for current request."""
    _included_account_ids_cache.set(ids)


def clear_included_account_ids_cache() -> None:
    """Clear the cached included account IDs."""
    _included_account_ids_cache.set(None)


class NoCacheMiddleware(BaseHTTPMiddleware):
    """Middleware to add cache-control headers to static files."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        path = request.url.path

        # Add no-cache headers for HTML files and static assets
        if path.endswith(".html") or path == "/" or "." not in path.split("/")[-1]:
            # HTML pages - never cache
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        elif "/_next/" in path:
            # Next.js assets - short cache with revalidation
            response.headers["Cache-Control"] = "no-cache, must-revalidate"

        return response


class RequestScopedCacheMiddleware(BaseHTTPMiddleware):
    """Middleware to clear request-scoped caches after each request."""

    async def dispatch(self, request: Request, call_next):
        # Clear cache at start of request
        clear_included_account_ids_cache()
        try:
            response = await call_next(request)
            return response
        finally:
            # Clear cache after request completes
            clear_included_account_ids_cache()


def run_migrations():
    """Run database migrations."""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        # Check if include_in_stats column exists
        cursor.execute("PRAGMA table_info(accounts)")
        columns = [col[1] for col in cursor.fetchall()]

        if "include_in_stats" not in columns:
            print("Adding include_in_stats column to accounts table...")
            cursor.execute(
                "ALTER TABLE accounts ADD COLUMN include_in_stats INTEGER DEFAULT 1"
            )
            conn.commit()
            print("Migration complete: include_in_stats column added")

        conn.close()
    except Exception as e:
        print(f"Migration warning: {e}")


def create_indexes():
    """Create database indexes for performance optimization."""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        # Check existing indexes
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
        existing_indexes = {row[0] for row in cursor.fetchall()}

        indexes_to_create = [
            ("idx_bt_transaction_date", 'broker_transactions("Transaction Date")'),
            ("idx_bt_account_id", "broker_transactions(account_id)"),
            (
                "idx_bt_account_date",
                'broker_transactions(account_id, "Transaction Date")',
            ),
            ("idx_bt_description", 'broker_transactions("Description")'),
            ("idx_bt_action", 'broker_transactions("Action")'),
            ("idx_accounts_include_stats", "accounts(include_in_stats)"),
        ]

        created = []
        for index_name, index_def in indexes_to_create:
            if index_name not in existing_indexes:
                try:
                    cursor.execute(
                        f"CREATE INDEX IF NOT EXISTS {index_name} ON {index_def}"
                    )
                    created.append(index_name)
                except Exception as e:
                    print(f"Could not create index {index_name}: {e}")

        if created:
            conn.commit()
            print(f"Created database indexes: {', '.join(created)}")

        conn.close()
    except Exception as e:
        print(f"Index creation warning: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup and shutdown events."""
    # Startup
    print("Starting Trading Analyzer API...")
    run_migrations()
    create_indexes()
    yield
    # Shutdown
    print("Shutting down Trading Analyzer API...")


# Create FastAPI application
app = FastAPI(
    title="Trading Analyzer API",
    description="Backend API for the Trading Analyzer dashboard",
    version=__version__,
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Next.js dev server
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add request-scoped cache middleware (must be before other middleware)
app.add_middleware(RequestScopedCacheMiddleware)

# Add no-cache middleware to prevent browser caching issues
app.add_middleware(NoCacheMiddleware)

# Include routers
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])
app.include_router(trades.router, prefix="/api/trades", tags=["Trades"])
app.include_router(instruments.router, prefix="/api/instruments", tags=["Instruments"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["Analytics"])
app.include_router(currency.router, prefix="/api/currency", tags=["Currency"])
app.include_router(imports.router, prefix="/api/import", tags=["Import"])


@app.get("/api/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": __version__,
    }


@app.get("/api", tags=["Root"])
async def root():
    """API root endpoint."""
    return {
        "message": "Trading Analyzer API",
        "version": __version__,
        "docs": "/api/docs",
    }


# Serve static frontend files if available (for standalone app)
if FRONTEND_OUT_DIR.exists():
    # Mount static assets
    static_assets = FRONTEND_OUT_DIR / "_next"
    if static_assets.exists():
        app.mount(
            "/_next", StaticFiles(directory=str(static_assets)), name="next_static"
        )

    @app.get("/", tags=["Frontend"])
    async def serve_index():
        """Serve the frontend index page."""
        index_path = FRONTEND_OUT_DIR / "index.html"
        if index_path.exists():
            return FileResponse(index_path)
        return {
            "message": "Frontend not built. Run 'npm run build' in frontend directory."
        }

    @app.get("/{full_path:path}", tags=["Frontend"])
    async def serve_frontend(full_path: str):
        """Serve frontend static files."""
        # Skip API routes
        if full_path.startswith("api"):
            return None

        # Remove trailing slash for path resolution
        clean_path = full_path.rstrip("/")

        # Try to serve the exact file
        file_path = FRONTEND_OUT_DIR / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)

        # Try as directory with index.html (Next.js trailingSlash: true)
        dir_index_path = FRONTEND_OUT_DIR / clean_path / "index.html"
        if dir_index_path.exists():
            return FileResponse(dir_index_path)

        # Try with .html extension (Next.js static export)
        html_path = FRONTEND_OUT_DIR / f"{clean_path}.html"
        if html_path.exists():
            return FileResponse(html_path)

        # 404 page
        not_found_path = FRONTEND_OUT_DIR / "404.html"
        if not_found_path.exists():
            return FileResponse(not_found_path, status_code=404)

        return {"error": "Not found"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
