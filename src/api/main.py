"""
Trading Analyzer API

FastAPI backend for the Trading Analyzer frontend.
Provides endpoints for dashboard data, trades, KPIs, and analytics.
"""

import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.routers import analytics, currency, dashboard, imports, instruments, trades

# Determine paths
API_DIR = Path(__file__).parent
SRC_DIR = API_DIR.parent
ROOT_DIR = SRC_DIR.parent
FRONTEND_OUT_DIR = ROOT_DIR / "frontend" / "out"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup and shutdown events."""
    # Startup
    print("Starting Trading Analyzer API...")
    yield
    # Shutdown
    print("Shutting down Trading Analyzer API...")


# Create FastAPI application
app = FastAPI(
    title="Trading Analyzer API",
    description="Backend API for the Trading Analyzer dashboard",
    version="1.0.0",
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
        "version": "1.0.0",
    }


@app.get("/api", tags=["Root"])
async def root():
    """API root endpoint."""
    return {
        "message": "Trading Analyzer API",
        "version": "1.0.0",
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

        # Try to serve the exact file
        file_path = FRONTEND_OUT_DIR / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)

        # Try with .html extension (Next.js static export)
        html_path = FRONTEND_OUT_DIR / f"{full_path}.html"
        if html_path.exists():
            return FileResponse(html_path)

        # Fallback to index.html for client-side routing
        index_path = FRONTEND_OUT_DIR / "index.html"
        if index_path.exists():
            return FileResponse(index_path)

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
