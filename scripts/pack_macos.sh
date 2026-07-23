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
ICON_ARG=()
if [[ -f assets/icon.icns ]]; then
  ICON_ARG=(-i assets/icon.icns)
elif [[ -f assets/icon.png ]]; then
  ICON_ARG=(-i assets/icon.png)
fi

flet pack main.py \
  -n "${APP_NAME}" \
  --product-name "${APP_NAME}" \
  --product-version "${VERSION}" \
  --copyright "Copyright (c) 2026 shayuaidoudou" \
  --bundle-id "store.shayuaidoudou.wallpaper-manager" \
  --distpath dist \
  "${ICON_ARG[@]}" \
  --hidden-import PIL \
  --hidden-import httpx \
  --hidden-import wallpaper_manager \
  --hidden-import wallpaper_manager.ui.app \
  --hidden-import wallpaper_manager.ui.gallery_panel \
  --hidden-import wallpaper_manager.gallery \
  --hidden-import wallpaper_manager.adapters.vscode \
  --hidden-import wallpaper_manager.adapters.cursor \
  --hidden-import wallpaper_manager.adapters.jetbrains \
  --hidden-import wallpaper_manager.adapters.ghostty \
  -y

mkdir -p release
rm -f "release/${ZIP_NAME}"
ditto -c -k --sequesterRsrc --keepParent "dist/${APP_NAME}.app" "release/${ZIP_NAME}"
shasum -a 256 "release/${ZIP_NAME}" | tee "release/${ZIP_NAME}.sha256"
echo "Built: release/${ZIP_NAME}"
