#!/usr/bin/env python3
"""
Build script for Trading Analyzer standalone desktop application.

This script builds standalone executables for macOS and Windows.

Usage:
    python scripts/build_standalone.py [--platform macos|windows|all]

Requirements:
    pip install pyinstaller pywebview

Output:
    - macOS: dist/Trading Analyzer.app
    - Windows: dist/Trading Analyzer/Trading Analyzer.exe
"""

import argparse
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

# Root directory
ROOT_DIR = Path(__file__).parent.parent
SRC_DIR = ROOT_DIR / "src"
FRONTEND_DIR = ROOT_DIR / "frontend"
DIST_DIR = ROOT_DIR / "dist"


def run_command(
    cmd: list, cwd: Path = None, check: bool = True
) -> subprocess.CompletedProcess:
    """Run a command and return the result."""
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd, capture_output=False)
    if check and result.returncode != 0:
        print(f"Command failed with exit code {result.returncode}")
        sys.exit(1)
    return result


def check_requirements():
    """Check that required tools are installed."""
    print("Checking requirements...")

    # Check Python version
    if sys.version_info < (3, 9):
        print("Error: Python 3.9 or higher is required")
        sys.exit(1)

    # Check PyInstaller
    try:
        import PyInstaller

        print(f"  PyInstaller: {PyInstaller.__version__}")
    except ImportError:
        print("Error: PyInstaller is not installed. Run: pip install pyinstaller")
        sys.exit(1)

    # Check pywebview
    try:
        import webview

        print(f"  pywebview: {webview.__version__}")
    except ImportError:
        print("Error: pywebview is not installed. Run: pip install pywebview")
        sys.exit(1)

    # Check Node.js (for frontend build)
    try:
        result = subprocess.run(["node", "--version"], capture_output=True, text=True)
        print(f"  Node.js: {result.stdout.strip()}")
    except FileNotFoundError:
        print("Error: Node.js is not installed. Install from https://nodejs.org")
        sys.exit(1)

    print("All requirements satisfied.\n")


def build_frontend():
    """Build the Next.js frontend as static files."""
    print("Building frontend...")

    # Check if node_modules exists
    if not (FRONTEND_DIR / "node_modules").exists():
        print("  Installing npm dependencies...")
        run_command(["npm", "install"], cwd=FRONTEND_DIR)

    # Build frontend
    print("  Building Next.js static export...")
    run_command(["npm", "run", "build"], cwd=FRONTEND_DIR)

    # Verify output
    out_dir = FRONTEND_DIR / "out"
    if not out_dir.exists():
        print("Error: Frontend build failed - 'out' directory not found")
        sys.exit(1)

    print(f"  Frontend built successfully: {out_dir}\n")


def build_pyinstaller(target_platform: str = None):
    """Build the standalone executable using PyInstaller."""
    current_platform = platform.system().lower()

    if target_platform is None:
        target_platform = "macos" if current_platform == "darwin" else "windows"

    print(f"Building standalone app for {target_platform}...")

    # Clean previous builds
    if DIST_DIR.exists():
        print("  Cleaning previous build...")
        shutil.rmtree(DIST_DIR)

    build_dir = ROOT_DIR / "build"
    if build_dir.exists():
        shutil.rmtree(build_dir)

    # Run PyInstaller
    print("  Running PyInstaller...")
    run_command(["pyinstaller", "--clean", "trading_analyzer.spec"], cwd=ROOT_DIR)

    # Verify output
    if current_platform == "darwin":
        app_path = DIST_DIR / "Trading Analyzer.app"
        if app_path.exists():
            print(f"\n✅ macOS app built successfully: {app_path}")
            print(f"   To run: open '{app_path}'")
        else:
            exe_path = DIST_DIR / "Trading Analyzer" / "Trading Analyzer"
            if exe_path.exists():
                print(f"\n✅ Executable built: {exe_path}")
    else:
        exe_path = DIST_DIR / "Trading Analyzer" / "Trading Analyzer.exe"
        if exe_path.exists():
            print(f"\n✅ Windows app built successfully: {exe_path}")
        else:
            print(
                "\n⚠️  Build completed but executable location unclear. Check dist/ directory."
            )


def create_dmg():
    """Create a DMG installer for macOS."""
    if platform.system() != "Darwin":
        print("DMG creation is only available on macOS")
        return

    print("Creating DMG installer...")

    app_path = DIST_DIR / "Trading Analyzer.app"
    if not app_path.exists():
        print("Error: App bundle not found. Run build first.")
        return

    dmg_path = DIST_DIR / "Trading Analyzer.dmg"

    # Use hdiutil to create DMG
    run_command(
        [
            "hdiutil",
            "create",
            "-volname",
            "Trading Analyzer",
            "-srcfolder",
            str(app_path),
            "-ov",
            "-format",
            "UDZO",
            str(dmg_path),
        ]
    )

    print(f"✅ DMG created: {dmg_path}")


def create_windows_installer():
    """Create a Windows installer using NSIS (if available)."""
    if platform.system() != "Windows":
        print("Windows installer creation is only available on Windows")
        return

    # Check if NSIS is available
    try:
        subprocess.run(["makensis", "/VERSION"], capture_output=True, check=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        print("NSIS not found. Skipping installer creation.")
        print("To create an installer, install NSIS from https://nsis.sourceforge.io")
        return

    print("Creating Windows installer with NSIS...")
    # TODO: Add NSIS script generation
    print("Windows installer creation not yet implemented")


def main():
    parser = argparse.ArgumentParser(
        description="Build Trading Analyzer standalone desktop application"
    )
    parser.add_argument(
        "--platform",
        choices=["macos", "windows", "current"],
        default="current",
        help="Target platform (default: current)",
    )
    parser.add_argument(
        "--skip-frontend",
        action="store_true",
        help="Skip frontend build (use existing build)",
    )
    parser.add_argument(
        "--create-installer",
        action="store_true",
        help="Create platform-specific installer (DMG for macOS)",
    )

    args = parser.parse_args()

    print("=" * 60)
    print("Trading Analyzer - Standalone App Builder")
    print("=" * 60 + "\n")

    # Check requirements
    check_requirements()

    # Build frontend
    if not args.skip_frontend:
        build_frontend()
    else:
        print("Skipping frontend build (using existing)\n")

    # Build executable
    target = None if args.platform == "current" else args.platform
    build_pyinstaller(target)

    # Create installer if requested
    if args.create_installer:
        if platform.system() == "Darwin":
            create_dmg()
        elif platform.system() == "Windows":
            create_windows_installer()

    print("\n" + "=" * 60)
    print("Build complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
