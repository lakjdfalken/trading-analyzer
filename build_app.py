#!/usr/bin/env python3
"""
Build script for Trading Analyzer standalone application.

This script builds the complete standalone application:
1. Installs frontend dependencies
2. Builds the Next.js frontend for static export
3. Packages everything with PyInstaller

Usage:
    python build_app.py [--skip-frontend] [--skip-pyinstaller] [--dev]

Options:
    --skip-frontend     Skip building the frontend
    --skip-pyinstaller  Skip PyInstaller packaging (just build frontend)
    --dev               Build in development mode (no minification)
"""

import argparse
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

# Paths
ROOT_DIR = Path(__file__).parent
FRONTEND_DIR = ROOT_DIR / "frontend"
FRONTEND_OUT_DIR = FRONTEND_DIR / "out"
DIST_DIR = ROOT_DIR / "dist"


def run_command(cmd: list, cwd: Path = None, env: dict = None) -> bool:
    """Run a command and return True if successful."""
    print(f"\n>>> Running: {' '.join(cmd)}")
    try:
        merged_env = os.environ.copy()
        if env:
            merged_env.update(env)
        result = subprocess.run(
            cmd,
            cwd=cwd or ROOT_DIR,
            env=merged_env,
            check=True,
            text=True,
        )
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {e}")
        return False
    except FileNotFoundError as e:
        print(f"Command not found: {e}")
        return False


def check_requirements():
    """Check that all required tools are installed."""
    print("Checking requirements...")

    errors = []

    # Check Node.js
    try:
        result = subprocess.run(
            ["node", "--version"],
            capture_output=True,
            text=True,
            check=True,
        )
        print(f"  Node.js: {result.stdout.strip()}")
    except (subprocess.CalledProcessError, FileNotFoundError):
        errors.append("Node.js is not installed. Install from https://nodejs.org/")

    # Check npm
    try:
        result = subprocess.run(
            ["npm", "--version"],
            capture_output=True,
            text=True,
            check=True,
        )
        print(f"  npm: {result.stdout.strip()}")
    except (subprocess.CalledProcessError, FileNotFoundError):
        errors.append("npm is not installed.")

    # Check Python packages
    required_packages = ["pyinstaller", "uvicorn", "fastapi", "webview"]
    for package in required_packages:
        try:
            __import__(package)
            print(f"  {package}: OK")
        except ImportError:
            errors.append(
                f"Python package '{package}' is not installed. Run: pip install {package}"
            )

    if errors:
        print("\nMissing requirements:")
        for error in errors:
            print(f"  - {error}")
        return False

    print("All requirements satisfied.\n")
    return True


def build_frontend(dev: bool = False):
    """Build the Next.js frontend for static export."""
    print("\n" + "=" * 60)
    print("Building frontend...")
    print("=" * 60)

    if not FRONTEND_DIR.exists():
        print(f"Error: Frontend directory not found at {FRONTEND_DIR}")
        return False

    # Install dependencies
    print("\nInstalling frontend dependencies...")
    npm_cmd = "npm.cmd" if platform.system() == "Windows" else "npm"

    if not run_command([npm_cmd, "install"], cwd=FRONTEND_DIR):
        return False

    # Build for production
    print("\nBuilding frontend for production...")

    # Set environment for build
    build_env = {
        "NEXT_PUBLIC_API_URL": "",  # Empty for relative URLs in standalone
        "NEXT_PUBLIC_USE_MOCK_FALLBACK": "false",
    }

    if not run_command([npm_cmd, "run", "build"], cwd=FRONTEND_DIR, env=build_env):
        return False

    # Verify output
    if not FRONTEND_OUT_DIR.exists():
        print(f"Error: Frontend build output not found at {FRONTEND_OUT_DIR}")
        return False

    print(f"\nFrontend built successfully to {FRONTEND_OUT_DIR}")
    return True


def build_pyinstaller():
    """Build the standalone application with PyInstaller."""
    print("\n" + "=" * 60)
    print("Building standalone application with PyInstaller...")
    print("=" * 60)

    spec_file = ROOT_DIR / "trading_analyzer.spec"
    if not spec_file.exists():
        print(f"Error: PyInstaller spec file not found at {spec_file}")
        return False

    # Clean previous build
    build_dir = ROOT_DIR / "build"
    if build_dir.exists():
        print(f"Cleaning {build_dir}...")
        shutil.rmtree(build_dir)

    if DIST_DIR.exists():
        print(f"Cleaning {DIST_DIR}...")
        shutil.rmtree(DIST_DIR)

    # Run PyInstaller
    if not run_command(["pyinstaller", "--clean", str(spec_file)]):
        return False

    # Verify output
    if not DIST_DIR.exists():
        print("Error: PyInstaller did not create dist directory")
        return False

    print(f"\nStandalone application built successfully to {DIST_DIR}")

    # Print output info
    system = platform.system()
    if system == "Darwin":
        app_path = DIST_DIR / "Trading Analyzer.app"
        if app_path.exists():
            print(f"\nmacOS app bundle: {app_path}")
            print(f"To run: open '{app_path}'")
    elif system == "Windows":
        exe_path = DIST_DIR / "Trading Analyzer" / "Trading Analyzer.exe"
        if exe_path.exists():
            print(f"\nWindows executable: {exe_path}")
    else:
        exe_path = DIST_DIR / "Trading Analyzer" / "Trading Analyzer"
        if exe_path.exists():
            print(f"\nLinux executable: {exe_path}")

    return True


def main():
    parser = argparse.ArgumentParser(
        description="Build Trading Analyzer standalone application"
    )
    parser.add_argument(
        "--skip-frontend",
        action="store_true",
        help="Skip building the frontend",
    )
    parser.add_argument(
        "--skip-pyinstaller",
        action="store_true",
        help="Skip PyInstaller packaging",
    )
    parser.add_argument(
        "--dev",
        action="store_true",
        help="Build in development mode",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("Trading Analyzer Build Script")
    print("=" * 60)
    print(f"Platform: {platform.system()} {platform.machine()}")
    print(f"Python: {sys.version}")
    print(f"Root directory: {ROOT_DIR}")

    # Check requirements
    if not check_requirements():
        print("\nPlease install missing requirements and try again.")
        sys.exit(1)

    # Build frontend
    if not args.skip_frontend:
        if not build_frontend(dev=args.dev):
            print("\nFrontend build failed!")
            sys.exit(1)
    else:
        print("\nSkipping frontend build...")

    # Build with PyInstaller
    if not args.skip_pyinstaller:
        if not build_pyinstaller():
            print("\nPyInstaller build failed!")
            sys.exit(1)
    else:
        print("\nSkipping PyInstaller packaging...")

    print("\n" + "=" * 60)
    print("Build completed successfully!")
    print("=" * 60)

    if not args.skip_pyinstaller:
        print("\nTo run the standalone app:")
        system = platform.system()
        if system == "Darwin":
            print(f"  open 'dist/Trading Analyzer.app'")
        elif system == "Windows":
            print(f"  dist\\Trading Analyzer\\Trading Analyzer.exe")
        else:
            print(f"  ./dist/Trading\\ Analyzer/Trading\\ Analyzer")

    print("\nTo run in development mode:")
    print("  python app.py")


if __name__ == "__main__":
    main()
