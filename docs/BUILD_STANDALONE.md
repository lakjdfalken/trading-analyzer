# Building Trading Analyzer as a Standalone Desktop App

This guide explains how to build Trading Analyzer as a standalone desktop application for macOS and Windows.

## Overview

The standalone app bundles:
- Python backend (FastAPI) with all dependencies
- Next.js frontend (pre-built static files)
- SQLite database (created on first run)
- Native window using pywebview

## Prerequisites

### All Platforms

1. **Python 3.9+**
   ```bash
   python --version  # Should be 3.9 or higher
   ```

2. **Node.js 18+**
   ```bash
   node --version  # Should be 18 or higher
   ```

3. **Python Dependencies**
   ```bash
   pip install pyinstaller pywebview
   ```

### macOS Additional Requirements

- Xcode Command Line Tools:
  ```bash
  xcode-select --install
  ```

### Windows Additional Requirements

- Visual C++ Build Tools (for some Python packages)
- Download from: https://visualstudio.microsoft.com/visual-cpp-build-tools/

## Quick Build

### Using the Build Script (Recommended)

```bash
# From the project root directory
python scripts/build_standalone.py
```

Options:
```bash
# Skip frontend rebuild (use existing)
python scripts/build_standalone.py --skip-frontend

# Create installer (DMG on macOS)
python scripts/build_standalone.py --create-installer
```

### Manual Build Steps

#### Step 1: Install Python Dependencies

```bash
cd trading-analyzer
pip install -r requirements.txt
pip install pyinstaller pywebview
```

#### Step 2: Build the Frontend

```bash
cd frontend
npm install
npm run build
cd ..
```

This creates static files in `frontend/out/`.

#### Step 3: Build the Executable

```bash
pyinstaller trading_analyzer.spec
```

## Build Output

### macOS
- **App Bundle**: `dist/Trading Analyzer.app`
- **Run**: Double-click the app or `open "dist/Trading Analyzer.app"`

### Windows
- **Executable**: `dist/Trading Analyzer/Trading Analyzer.exe`
- **Run**: Double-click the executable

## Distribution

### macOS

#### Creating a DMG

```bash
# After building the app
hdiutil create -volname "Trading Analyzer" \
    -srcfolder "dist/Trading Analyzer.app" \
    -ov -format UDZO \
    "dist/Trading Analyzer.dmg"
```

#### Code Signing (Optional but Recommended)

To distribute outside the App Store, sign the app:

```bash
# List available signing identities
security find-identity -v -p codesigning

# Sign the app
codesign --force --deep --sign "Developer ID Application: Your Name (TEAMID)" \
    "dist/Trading Analyzer.app"

# Verify
codesign --verify --deep --strict "dist/Trading Analyzer.app"
```

#### Notarization (Required for macOS 10.15+)

```bash
# Create a ZIP for notarization
ditto -c -k --keepParent "dist/Trading Analyzer.app" "dist/Trading Analyzer.zip"

# Submit for notarization
xcrun notarytool submit "dist/Trading Analyzer.zip" \
    --apple-id "your@email.com" \
    --team-id "TEAMID" \
    --password "app-specific-password" \
    --wait

# Staple the ticket
xcrun stapler staple "dist/Trading Analyzer.app"
```

### Windows

#### Creating an Installer with NSIS

1. Install NSIS from https://nsis.sourceforge.io
2. Create an installer script or use Inno Setup

#### Creating a ZIP Distribution

```powershell
Compress-Archive -Path "dist\Trading Analyzer" -DestinationPath "dist\TradingAnalyzer-Windows.zip"
```

## Troubleshooting

### "App is damaged and can't be opened" (macOS)

This happens with unsigned apps. Users can bypass by:
```bash
xattr -cr "/Applications/Trading Analyzer.app"
```

Or right-click → Open → Open anyway.

### Missing DLLs on Windows

Ensure Visual C++ Redistributable is installed:
https://aka.ms/vs/17/release/vc_redist.x64.exe

### Webview Not Displaying

Check if pywebview dependencies are installed:

**macOS**: Should work out of the box (uses WebKit)

**Windows**: Requires Edge WebView2 Runtime
- Usually pre-installed on Windows 10/11
- Download: https://developer.microsoft.com/en-us/microsoft-edge/webview2/

**Linux**: Requires GTK and WebKit2
```bash
# Ubuntu/Debian
sudo apt install python3-gi gir1.2-webkit2-4.0

# Fedora
sudo dnf install python3-gobject webkit2gtk3
```

### Large App Size

The bundled app includes Python runtime and all dependencies. To reduce size:

1. Use `--onefile` mode (slower startup but single file):
   ```python
   # In spec file, change COLLECT to single file EXE
   ```

2. Use UPX compression (already enabled in spec file)

3. Exclude unnecessary packages in the spec file

### Database Location

The SQLite database (`trading.db`) is created in:
- **Development**: Project root directory
- **Standalone App**: Same directory as the executable

To use a fixed location (e.g., user's home directory), modify `src/api/services/database.py`.

## Development Mode

For development, run the frontend and backend separately:

**Terminal 1 - Backend:**
```bash
cd src
uvicorn api.main:app --reload --port 8000
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

Access at http://localhost:3000

## Architecture

```
┌─────────────────────────────────────────┐
│           Trading Analyzer App          │
├─────────────────────────────────────────┤
│  ┌─────────────────────────────────┐    │
│  │     pywebview (Native Window)   │    │
│  │  ┌───────────────────────────┐  │    │
│  │  │   Next.js Frontend (HTML) │  │    │
│  │  └───────────────────────────┘  │    │
│  └─────────────────────────────────┘    │
│                   │                      │
│                   ▼                      │
│  ┌─────────────────────────────────┐    │
│  │   FastAPI Backend (localhost)   │    │
│  │  ┌───────────────────────────┐  │    │
│  │  │   SQLite Database         │  │    │
│  │  └───────────────────────────┘  │    │
│  └─────────────────────────────────┘    │
└─────────────────────────────────────────┘
```

## CI/CD Integration

For automated builds, see `.github/workflows/build.yml` (if available) or create one:

```yaml
name: Build Desktop App

on:
  release:
    types: [created]

jobs:
  build-macos:
    runs-on: macos-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - uses: actions/setup-node@v3
        with:
          node-version: '18'
      - run: pip install -r requirements.txt pyinstaller pywebview
      - run: cd frontend && npm ci && npm run build
      - run: pyinstaller trading_analyzer.spec
      - uses: actions/upload-artifact@v3
        with:
          name: macos-app
          path: dist/Trading Analyzer.app

  build-windows:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - uses: actions/setup-node@v3
        with:
          node-version: '18'
      - run: pip install -r requirements.txt pyinstaller pywebview
      - run: cd frontend && npm ci && npm run build
      - run: pyinstaller trading_analyzer.spec
      - uses: actions/upload-artifact@v3
        with:
          name: windows-app
          path: dist/Trading Analyzer/
```

## Support

If you encounter issues:
1. Check the troubleshooting section above
2. Review the build logs for errors
3. Open an issue on GitHub with:
   - Your OS version
   - Python version
   - Complete error message
   - Steps to reproduce