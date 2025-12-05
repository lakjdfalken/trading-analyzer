"""
Trading Analyzer API package.

FastAPI backend for the Trading Analyzer frontend.
Provides endpoints for dashboard data, trades, KPIs, and analytics.
"""

from pathlib import Path


def _get_version() -> str:
    """Read version from VERSION file."""
    import sys

    # Try multiple possible locations for VERSION file
    possible_paths = [
        Path(__file__).parent.parent.parent / "VERSION",  # src/api -> src -> root
        Path(__file__).parent.parent.parent.parent
        / "VERSION",  # In case of different structure
        Path.cwd() / "VERSION",  # Current working directory
    ]

    # Add PyInstaller bundle path (for packaged app)
    if getattr(sys, "frozen", False):
        # Running as compiled executable
        bundle_dir = Path(sys._MEIPASS)
        possible_paths.insert(0, bundle_dir / "VERSION")

    for version_path in possible_paths:
        if version_path.exists():
            return version_path.read_text().strip()

    return "0.0.0"  # Fallback version


__version__ = _get_version()
