# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Trading Analyzer standalone application.

Build commands:
    # macOS/Linux:
    pyinstaller trading_analyzer.spec

    # Windows:
    pyinstaller trading_analyzer.spec

Output:
    - macOS: dist/Trading Analyzer.app
    - Windows: dist/Trading Analyzer.exe
    - Linux: dist/Trading Analyzer
"""

import sys
from pathlib import Path

block_cipher = None

# Determine platform
is_macos = sys.platform == "darwin"
is_windows = sys.platform == "win32"
is_linux = sys.platform.startswith("linux")

# Root directory
ROOT_DIR = Path(SPECPATH)

# Data files to include
datas = [
    # Include frontend build output
    (str(ROOT_DIR / "frontend" / "out"), "frontend/out"),
]

# Filter out non-existent paths
datas = [(src, dst) for src, dst in datas if Path(src).exists()]

# Hidden imports for FastAPI and dependencies
hiddenimports = [
    "uvicorn",
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.auto",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
    "fastapi",
    "pydantic",
    "starlette",
    "anyio",
    "anyio._backends",
    "anyio._backends._asyncio",
    "webview",
    "webview.platforms",
    "sqlite3",
    "pandas",
    "numpy",
    # API modules
    "api",
    "api.main",
    "api.routers",
    "api.routers.dashboard",
    "api.routers.trades",
    "api.routers.instruments",
    "api.routers.analytics",
    "api.routers.currency",
    "api.routers.imports",
    "api.models",
    "api.models.schemas",
    "api.services",
    "api.services.database",
    "api.services.currency",
    # Source modules
    "create_database",
    "db_path",
    "file_handler",
    "import_data",
    "logger",
    "settings",
]

# Platform-specific hidden imports
if is_macos:
    hiddenimports.extend([
        "webview.platforms.cocoa",
        "Foundation",
        "AppKit",
        "WebKit",
    ])
elif is_windows:
    hiddenimports.extend([
        "webview.platforms.winforms",
        "webview.platforms.edgechromium",
        "clr",
        "pythonnet",
    ])
elif is_linux:
    hiddenimports.extend([
        "webview.platforms.gtk",
        "gi",
        "gi.repository",
    ])

# Binary exclusions (reduce size)
excludes = [
    "tkinter",
    "test",
    "unittest",
    "PyQt5",
    "PyQt6",
    "PyQt6.QtWidgets",
    "PyQt6.QtCore",
    "PyQt6.QtGui",
    "matplotlib",
    "plotly",
    "seaborn",
    "PIL",
    "IPython",
    "jupyter",
]

a = Analysis(
    ["app.py"],
    pathex=[str(ROOT_DIR / "src")],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Trading Analyzer",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # No console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="docs/icon.icns" if is_macos else ("docs/icon.ico" if is_windows else None),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="Trading Analyzer",
)

# macOS-specific: Create .app bundle
if is_macos:
    app = BUNDLE(
        coll,
        name="Trading Analyzer.app",
        icon="docs/icon.icns" if Path("docs/icon.icns").exists() else None,
        bundle_identifier="com.tradinganalyzer.app",
        info_plist={
            "CFBundleName": "Trading Analyzer",
            "CFBundleDisplayName": "Trading Analyzer",
            "CFBundleGetInfoString": "Trading Analyzer - Portfolio Analysis Tool",
            "CFBundleIdentifier": "com.tradinganalyzer.app",
            "CFBundleVersion": "2.0.0",
            "CFBundleShortVersionString": "2.0.0",
            "NSHighResolutionCapable": True,
            "NSRequiresAquaSystemAppearance": False,  # Support dark mode
            "LSMinimumSystemVersion": "10.13.0",
        },
    )
