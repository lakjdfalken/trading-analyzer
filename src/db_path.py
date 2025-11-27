"""
Centralized database path utility.

Stores the database in a platform-specific user data directory
so that user data persists across application updates.

Locations:
- macOS: ~/Library/Application Support/TradingAnalyzer/trading.db
- Windows: %LOCALAPPDATA%/TradingAnalyzer/trading.db
- Linux: ~/.local/share/TradingAnalyzer/trading.db
"""

import os
import platform
import shutil
from pathlib import Path

APP_NAME = "TradingAnalyzer"
DB_FILENAME = "trading.db"


def get_user_data_dir() -> Path:
    """Get the platform-specific user data directory."""
    system = platform.system()

    if system == "Darwin":  # macOS
        base = Path.home() / "Library" / "Application Support"
    elif system == "Windows":
        # Use LOCALAPPDATA for app-specific data
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            base = Path(local_app_data)
        else:
            base = Path.home() / "AppData" / "Local"
    else:  # Linux and others
        xdg_data_home = os.environ.get("XDG_DATA_HOME")
        if xdg_data_home:
            base = Path(xdg_data_home)
        else:
            base = Path.home() / ".local" / "share"

    return base / APP_NAME


def get_database_path() -> str:
    """
    Get the path to the database file.

    Creates the user data directory if it doesn't exist.
    If an old database exists in the application directory,
    it will be migrated to the new location.

    Returns:
        str: Full path to the database file.
    """
    user_data_dir = get_user_data_dir()
    db_path = user_data_dir / DB_FILENAME

    # Ensure the directory exists
    user_data_dir.mkdir(parents=True, exist_ok=True)

    # Check for legacy database location and migrate if needed
    legacy_db_path = _get_legacy_database_path()
    if legacy_db_path and legacy_db_path.exists() and not db_path.exists():
        _migrate_database(legacy_db_path, db_path)

    return str(db_path)


def _get_legacy_database_path() -> Path | None:
    """
    Get the path to the legacy database location (in the app directory).

    Returns:
        Path or None: Path to the legacy database, or None if not determinable.
    """
    try:
        # The legacy location was in the project/app root
        # This file is at src/db_path.py, so go up two levels
        legacy_path = Path(__file__).parent.parent / DB_FILENAME
        return legacy_path
    except Exception:
        return None


def _migrate_database(source: Path, destination: Path) -> bool:
    """
    Migrate the database from the old location to the new location.

    Args:
        source: Path to the existing database.
        destination: Path to the new database location.

    Returns:
        bool: True if migration was successful, False otherwise.
    """
    try:
        # Copy instead of move to be safe - user can delete the old one manually
        shutil.copy2(source, destination)
        print(f"Database migrated from {source} to {destination}")
        return True
    except Exception as e:
        print(f"Warning: Failed to migrate database: {e}")
        return False


def get_database_dir() -> str:
    """
    Get the directory containing the database.

    Returns:
        str: Full path to the database directory.
    """
    return str(get_user_data_dir())


# Provide the path as a module-level constant for convenience
DATABASE_PATH = get_database_path()
