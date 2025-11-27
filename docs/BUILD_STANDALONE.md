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

---

## Quick Build (Local)

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

#### Step 1: Clean Previous Builds

```bash
rm -rf dist build .venv
rm -rf frontend/.next frontend/node_modules/.cache
rm -rf src/__pycache__ src/**/__pycache__
```

#### Step 2: Create Fresh Virtual Environment

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

#### Step 3: Build the Frontend

```bash
cd frontend
npm ci  # Clean install (recommended for releases)
npm run build
cd ..
```

This creates static files in `frontend/out/`.

#### Step 4: Build the Executable

```bash
pyinstaller trading_analyzer.spec
```

## Build Output

### macOS
- **App Bundle**: `dist/Trading Analyzer.app`
- **Run**: `xattr -cr "dist/Trading Analyzer.app"` then double-click or `open "dist/Trading Analyzer.app"`

### Windows
- **Executable**: `dist/Trading Analyzer/Trading Analyzer.exe`
- **Run**: Double-click the executable

---

## Automated Releases with GitHub Actions

The repository includes a GitHub Actions workflow that automatically builds releases for both Windows and macOS.

### How It Works

The workflow (`.github/workflows/build-release.yml`) is triggered when you:
1. **Push a version tag** (e.g., `v1.0.0`, `v2.1.3`)
2. **Manually trigger** the workflow from GitHub Actions tab

### Creating a Release (Recommended Method)

#### Step 1: Commit Your Changes

```bash
git add .
git commit -m "Release v1.0.0 - Description of changes"
```

#### Step 2: Create and Push a Version Tag

```bash
# Create a tag
git tag v1.0.0

# Push the tag to GitHub
git push origin v1.0.0

# Also push your commits if not already pushed
git push origin main
```

#### Step 3: Wait for Build

GitHub Actions will automatically:
1. Build the Windows executable (.exe in a zip)
2. Build the macOS app (.dmg)
3. Create a GitHub Release with both files attached

#### Step 4: Download Artifacts

Once complete, find your release at:
`https://github.com/YOUR_USERNAME/trading-analyzer/releases`

### Version Tag Format

Use semantic versioning: `vMAJOR.MINOR.PATCH`

Examples:
- `v1.0.0` - Initial release
- `v1.1.0` - New features added
- `v1.1.1` - Bug fixes
- `v2.0.0` - Major changes/breaking changes

### Manual Workflow Trigger

You can also trigger a build without creating a release:

1. Go to **Actions** tab in your GitHub repository
2. Select **Build Release** workflow
3. Click **Run workflow**
4. Optionally enter a version name
5. Click **Run workflow**

Build artifacts will be available for download from the workflow run (not as a release).

### What Gets Built

| Platform | Output File | Contents |
|----------|-------------|----------|
| Windows | `TradingAnalyzer-Windows-x64.zip` | Folder with .exe and dependencies |
| macOS | `TradingAnalyzer-macOS.dmg` | Disk image with .app bundle |

---

## Distribution

### macOS

#### Creating a DMG (Manual)

```bash
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

#### Creating a ZIP Distribution (Manual)

```powershell
Compress-Archive -Path "dist\Trading Analyzer" -DestinationPath "dist\TradingAnalyzer-Windows.zip"
```

#### Creating an Installer with NSIS

1. Install NSIS from https://nsis.sourceforge.io
2. Create an installer script or use Inno Setup

---

## Pre-Release Checklist

Before creating a release tag:

- [ ] All features tested and working
- [ ] No console errors in browser dev tools
- [ ] Import/export functionality works
- [ ] Charts display correctly (including expanded views)
- [ ] Update version number if hardcoded anywhere
- [ ] Commit all changes
- [ ] Update CHANGELOG.md (if maintained)

---

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

1. Use UPX compression (already enabled in spec file)
2. Exclude unnecessary packages in the spec file

### Database Location

The SQLite database (`trading.db`) is created in:
- **Development**: Project root directory
- **Standalone App**: Same directory as the executable

### GitHub Actions Build Fails

Common issues:
1. **npm ci fails**: Ensure `package-lock.json` is committed
2. **PyInstaller fails**: Check that all imports in the code are in `requirements.txt`
3. **Missing frontend/out**: The frontend build step must complete before PyInstaller

---

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

---

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

---

## Support

If you encounter issues:
1. Check the troubleshooting section above
2. Review the build logs for errors
3. Open an issue on GitHub with:
   - Your OS version
   - Python version
   - Complete error message
   - Steps to reproduce