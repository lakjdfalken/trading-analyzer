#!/usr/bin/env python3
"""
Sync version from VERSION file to all project files.

Updates:
- frontend/package.json
"""

import json
import sys
from pathlib import Path


def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent


def read_version() -> str:
    """Read version from VERSION file."""
    version_file = get_project_root() / "VERSION"
    if not version_file.exists():
        print(f"Error: VERSION file not found at {version_file}", file=sys.stderr)
        sys.exit(1)
    return version_file.read_text().strip()


def update_package_json(version: str) -> None:
    """Update frontend/package.json version."""
    package_json_path = get_project_root() / "frontend" / "package.json"
    if not package_json_path.exists():
        print(
            f"Warning: package.json not found at {package_json_path}", file=sys.stderr
        )
        return

    with open(package_json_path, "r") as f:
        data = json.load(f)

    old_version = data.get("version", "unknown")
    data["version"] = version

    with open(package_json_path, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")

    print(f"Updated frontend/package.json: {old_version} -> {version}")


def main():
    """Main entry point."""
    version = read_version()
    print(f"Version from VERSION file: {version}")

    update_package_json(version)

    print("Version sync complete!")


if __name__ == "__main__":
    main()
