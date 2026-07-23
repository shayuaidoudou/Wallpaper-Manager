from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import quote

from wallpaper_manager.core.opacity import ui_to_background_cover

_OPACITY_RE = re.compile(r"(opacity\s*:\s*)([0-9]*\.?[0-9]+)(\s*;)", re.IGNORECASE)
_IMAGE_RE = re.compile(
    r"(background-image\s*:\s*url\(['\"]?)([^'\")]+)(['\"]?\s*\))",
    re.IGNORECASE,
)


def css_paths_for_app(app: str) -> list[Path]:
    """Return possible css-background-cover.css paths for vscode|cursor."""
    paths: list[Path] = []
    if sys.platform == "darwin":
        if app == "cursor":
            paths.append(
                Path(
                    "/Applications/Cursor.app/Contents/Resources/app/out/vs/workbench/"
                    "css-background-cover.css"
                )
            )
        elif app == "vscode":
            paths.append(
                Path(
                    "/Applications/Visual Studio Code.app/Contents/Resources/app/"
                    "out/vs/workbench/css-background-cover.css"
                )
            )
    elif sys.platform == "win32":
        local = Path.home() / "AppData" / "Local" / "Programs"
        if app == "cursor":
            paths.append(
                local
                / "cursor"
                / "resources"
                / "app"
                / "out"
                / "vs"
                / "workbench"
                / "css-background-cover.css"
            )
        elif app == "vscode":
            paths.append(
                local
                / "Microsoft VS Code"
                / "resources"
                / "app"
                / "out"
                / "vs"
                / "workbench"
                / "css-background-cover.css"
            )
    return paths


def to_vscode_file_url(image_path: str) -> str:
    absolute = Path(image_path).expanduser().resolve()
    encoded = quote(absolute.as_posix(), safe="/:")
    return f"vscode-file://vscode-app{encoded}"


def patch_background_cover_css(
    css_path: Path, image_path: str, opacity_ui: int
) -> bool:
    """Update installed extension CSS. Returns True if a file was patched."""
    if not css_path.is_file():
        return False
    opacity = ui_to_background_cover(opacity_ui)
    css_url = to_vscode_file_url(image_path)
    text = css_path.read_text(encoding="utf-8")
    if not _OPACITY_RE.search(text):
        return False
    text = _OPACITY_RE.sub(rf"\g<1>{opacity}\g<3>", text, count=1)
    if _IMAGE_RE.search(text):
        text = _IMAGE_RE.sub(rf"\g<1>{css_url}\g<3>", text, count=1)
    css_path.write_text(text, encoding="utf-8")
    return True


def clear_background_cover_css(css_path: Path) -> bool:
    if not css_path.is_file():
        return False
    text = css_path.read_text(encoding="utf-8")
    changed = False
    if _OPACITY_RE.search(text):
        text = _OPACITY_RE.sub(r"\g<1>0\g<3>", text, count=1)
        changed = True
    if _IMAGE_RE.search(text):
        text = _IMAGE_RE.sub(r"\g<1>\g<3>", text, count=1)
        changed = True
    if changed:
        css_path.write_text(text, encoding="utf-8")
    return changed


def sync_electron_css(app: str, image_path: str | None, opacity_ui: int) -> int:
    """Patch all known CSS targets for an electron editor. Returns patched count."""
    count = 0
    for css_path in css_paths_for_app(app):
        if image_path:
            if patch_background_cover_css(css_path, image_path, opacity_ui):
                count += 1
        elif clear_background_cover_css(css_path):
            count += 1
    return count
