#!/usr/bin/env python3
"""
Trading Analyzer - Standalone Desktop Application

Launches the Trading Analyzer as a standalone desktop app with:
- Embedded FastAPI backend server
- Auto-opens in user's default browser

Works on macOS, Windows, and Linux.
"""

import logging
import signal
import socket
import sys
import threading
import time
import webbrowser
from contextlib import closing
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("TradingAnalyzer")

# Add src directory to path
ROOT_DIR = Path(__file__).parent
SRC_DIR = ROOT_DIR / "src"
sys.path.insert(0, str(SRC_DIR))

# Global references
api_server = None


def find_free_port(start_port: int = 8000, max_attempts: int = 100) -> int:
    """Find an available port starting from start_port."""
    for port in range(start_port, start_port + max_attempts):
        with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
            try:
                sock.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise RuntimeError(
        f"Could not find free port in range {start_port}-{start_port + max_attempts}"
    )


def wait_for_server(host: str, port: int, timeout: float = 30.0) -> bool:
    """Wait for the server to become available."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
                sock.settimeout(1.0)
                result = sock.connect_ex((host, port))
                if result == 0:
                    return True
        except Exception:
            pass
        time.sleep(0.1)
    return False


class APIServer:
    """Manages the FastAPI backend server in a separate thread."""

    def __init__(self, host: str = "127.0.0.1", port: int = 8000):
        self.host = host
        self.port = port
        self.server = None
        self.thread = None
        self._shutdown_event = threading.Event()

    def start(self):
        """Start the API server in a background thread."""
        self.thread = threading.Thread(target=self._run_server, daemon=True)
        self.thread.start()

        # Wait for server to be ready
        logger.info(f"Waiting for API server at {self.host}:{self.port}...")
        if wait_for_server(self.host, self.port):
            logger.info("API server is ready")
            return True
        else:
            logger.error("API server failed to start")
            return False

    def _run_server(self):
        """Run the uvicorn server."""
        try:
            import uvicorn

            from api.main import app

            config = uvicorn.Config(
                app,
                host=self.host,
                port=self.port,
                log_level="warning",
                access_log=False,
            )
            self.server = uvicorn.Server(config)
            self.server.run()
        except Exception as e:
            logger.error(f"API server error: {e}")

    def stop(self):
        """Stop the API server."""
        if self.server:
            self.server.should_exit = True
            self._shutdown_event.set()
            logger.info("API server stopped")


def get_frontend_url(api_port: int) -> str:
    """
    Get the frontend URL.

    In development: Points to Next.js dev server
    In production: Points to static files served by FastAPI
    """
    # Check if Next.js dev server is running
    if wait_for_server("127.0.0.1", 3000, timeout=0.5):
        logger.info("Using Next.js development server")
        return "http://127.0.0.1:3000"

    # Check if we have static frontend build
    static_dir = ROOT_DIR / "frontend" / "out"
    if static_dir.exists():
        logger.info("Using static frontend build")
        return f"http://127.0.0.1:{api_port}"

    # Fallback: show API docs
    logger.warning("No frontend available, showing API documentation")
    return f"http://127.0.0.1:{api_port}/api/docs"


def setup_static_serving(app, static_dir: Path):
    """Configure FastAPI to serve static frontend files."""
    from fastapi.responses import FileResponse
    from fastapi.staticfiles import StaticFiles

    if static_dir.exists():
        # Serve static files
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

        # Serve index.html for all non-API routes
        @app.get("/{full_path:path}")
        async def serve_frontend(full_path: str):
            # Don't serve frontend for API routes
            if full_path.startswith("api/"):
                return None

            file_path = static_dir / full_path
            if file_path.exists() and file_path.is_file():
                return FileResponse(file_path)

            # Fallback to index.html for SPA routing
            index_path = static_dir / "index.html"
            if index_path.exists():
                return FileResponse(index_path)

            return FileResponse(static_dir / "404.html")


def ensure_database():
    """Ensure the database exists and has the correct schema."""
    try:
        from create_database import create_db_schema

        create_db_schema()
        logger.info("Database schema verified")
    except Exception as e:
        logger.error(f"Failed to create database schema: {e}")
        raise


def run_app():
    """Main entry point for the standalone app."""
    global api_server

    logger.info("Starting Trading Analyzer...")

    # Ensure database exists
    try:
        ensure_database()
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        sys.exit(1)

    # Find available port
    api_port = find_free_port(8000)
    logger.info(f"Using port {api_port} for API server")

    # Start API server
    api_server = APIServer(host="127.0.0.1", port=api_port)
    if not api_server.start():
        logger.error("Failed to start API server")
        sys.exit(1)

    # Configure static file serving if available
    static_dir = ROOT_DIR / "frontend" / "out"
    if static_dir.exists():
        from api.main import app

        setup_static_serving(app, static_dir)

    # Get frontend URL
    frontend_url = get_frontend_url(api_port)
    logger.info(f"Opening frontend at {frontend_url}")

    # Open in default browser
    webbrowser.open(frontend_url)

    print(f"\n{'=' * 50}")
    print(f"Trading Analyzer is running!")
    print(f"Open in browser: {frontend_url}")
    print(f"Press Ctrl+C to stop")
    print(f"{'=' * 50}\n")

    # Keep running until interrupted
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        if api_server:
            api_server.stop()


def main():
    """Entry point with signal handling."""

    # Handle Ctrl+C gracefully
    def signal_handler(sig, frame):
        logger.info("Received shutdown signal")
        if api_server:
            api_server.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    run_app()


if __name__ == "__main__":
    main()
