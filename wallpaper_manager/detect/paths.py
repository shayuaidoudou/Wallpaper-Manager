from __future__ import annotations

import os
import re
import sys
from pathlib import Path


def _home(home: Path | None) -> Path:
    return home if home is not None else Path.home()


def _xdg_config_home(home: Path) -> Path:
    return Path(os.environ.get("XDG_CONFIG_HOME", str(home / ".config")))


def vscode_settings_path(home: Path | None = None) -> Path:
    h = _home(home)
    if sys.platform == "darwin":
        return h / "Library/Application Support/Code/User/settings.json"
    if sys.platform == "win32":
        appdata = Path(os.environ.get("APPDATA", str(h / "AppData/Roaming")))
        return appdata / "Code/User/settings.json"
    # Linux / other: XDG layout used by official VS Code packages.
    return _xdg_config_home(h) / "Code/User/settings.json"


def cursor_settings_path(home: Path | None = None) -> Path:
    h = _home(home)
    if sys.platform == "darwin":
        return h / "Library/Application Support/Cursor/User/settings.json"
    if sys.platform == "win32":
        appdata = Path(os.environ.get("APPDATA", str(h / "AppData/Roaming")))
        return appdata / "Cursor/User/settings.json"
    return _xdg_config_home(h) / "Cursor/User/settings.json"


def jetbrains_support_root(home: Path | None = None) -> Path:
    h = _home(home)
    if sys.platform == "darwin":
        return h / "Library/Application Support/JetBrains"
    if sys.platform == "win32":
        appdata = Path(os.environ.get("APPDATA", str(h / "AppData/Roaming")))
        return appdata / "JetBrains"
    return _xdg_config_home(h) / "JetBrains"


def find_jetbrains_other_xml(product_prefix: str, home: Path | None = None) -> Path | None:
    root = jetbrains_support_root(home)
    if not root.is_dir():
        return None
    candidates: list[Path] = []
    for child in root.iterdir():
        if child.is_dir() and child.name.startswith(product_prefix):
            candidates.append(child)
    if not candidates:
        return None
    candidates.sort(
        key=lambda path: tuple(
            int(part) for part in re.findall(r"\d+", path.name[len(product_prefix) :])
        ),
        reverse=True,
    )
    return candidates[0] / "options" / "other.xml"


def ghostty_config_candidates(home: Path | None = None) -> list[Path]:
    """Ghostty search order: platform app support first, then XDG."""
    h = _home(home)
    xdg = _xdg_config_home(h) / "ghostty"
    if sys.platform == "darwin":
        support = h / "Library/Application Support/com.mitchellh.ghostty"
        return [
            support / "config.ghostty",
            support / "config",
            xdg / "config.ghostty",
            xdg / "config",
        ]
    if sys.platform == "win32":
        appdata = Path(os.environ.get("APPDATA", str(h / "AppData/Roaming")))
        return [
            appdata / "ghostty" / "config.ghostty",
            appdata / "ghostty" / "config",
            xdg / "config.ghostty",
            xdg / "config",
        ]
    # Linux and other Unix: XDG only.
    return [
        xdg / "config.ghostty",
        xdg / "config",
    ]


def find_ghostty_config(home: Path | None = None) -> Path:
    """Return first existing Ghostty config, else the preferred default path."""
    candidates = ghostty_config_candidates(home)
    for path in candidates:
        if path.is_file():
            return path
    return candidates[0]
