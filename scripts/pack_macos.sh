#!/usr/bin/env bash
# Build a double-clickable macOS .app (Apple Silicon) and zip it for GitHub Releases.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ $# -ge 1 ]]; then
  VERSION="$1"
else
  VERSION="$(python3 -c 'import tomllib; print(tomllib.load(open("pyproject.toml","rb"))["project"]["version"])')"
fi

APP_NAME="Wallpaper Manager"
ZIP_NAME="Wallpaper-Manager-${VERSION}-macos-arm64.zip"

if [[ ! -d .venv ]]; then
  python3.11 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -e ".[dev]" pyinstaller >/dev/null

rm -rf dist "build/${APP_NAME}" "${APP_NAME}.spec"

# Onedir build (via our driver script): onefile .app bundles break macOS TCC —
# folder-access permission is re-asked on every launch.
python scripts/pack_macos_onedir.py "${VERSION}"

# Re-sign with entitlements so the macOS file/folder picker works
# (file_selector_macos requires the user-selected read-write entitlement,
#  otherwise it throws PlatformException(ENTITLEMENT_NOT_FOUND)).
if [[ -f assets/entitlements.plist ]]; then
  codesign --force --deep --sign - \
    --options runtime \
    --entitlements assets/entitlements.plist \
    "dist/${APP_NAME}.app"
  codesign -d --entitlements - --xml "dist/${APP_NAME}.app" >/dev/null 2>&1 \
    && echo "Re-signed with entitlements."
fi

mkdir -p release
rm -f "release/${ZIP_NAME}"
ditto -c -k --sequesterRsrc --keepParent "dist/${APP_NAME}.app" "release/${ZIP_NAME}"
shasum -a 256 "release/${ZIP_NAME}" | tee "release/${ZIP_NAME}.sha256"
echo "Built: release/${ZIP_NAME}"
