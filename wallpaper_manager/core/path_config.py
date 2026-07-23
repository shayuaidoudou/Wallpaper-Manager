"""Per-app config-file path hints and auto resolution."""

from __future__ import annotations

from pathlib import Path

from wallpaper_manager.core.models import AppId
from wallpaper_manager.detect.paths import (
    cursor_settings_path,
    find_ghostty_config,
    find_jetbrains_other_xml,
    vscode_settings_path,
)

# What the user should point at (config file, not the .app binary).
CONFIG_FILE_LABELS = {
    AppId.VSCODE: "settings.json",
    AppId.CURSOR: "settings.json",
    AppId.IDEA: "other.xml",
    AppId.PYCHARM: "other.xml",
    AppId.GHOSTTY: "config / config.ghostty",
}

CONFIG_PATH_HINTS = {
    AppId.VSCODE: "~/Library/Application Support/Code/User/settings.json",
    AppId.CURSOR: "~/Library/Application Support/Cursor/User/settings.json",
    AppId.IDEA: "~/Library/Application Support/JetBrains/IntelliJIdea*/options/other.xml",
    AppId.PYCHARM: "~/Library/Application Support/JetBrains/PyCharm*/options/other.xml",
    AppId.GHOSTTY: "~/Library/Application Support/com.mitchellh.ghostty/config.ghostty",
}


def auto_config_path(app_id: AppId) -> Path | None:
    if app_id is AppId.VSCODE:
        return vscode_settings_path()
    if app_id is AppId.CURSOR:
        return cursor_settings_path()
    if app_id is AppId.IDEA:
        return find_jetbrains_other_xml("IntelliJIdea")
    if app_id is AppId.PYCHARM:
        return find_jetbrains_other_xml("PyCharm")
    if app_id is AppId.GHOSTTY:
        return find_ghostty_config()
    return None


def normalize_config_path(raw: str) -> str:
    return str(Path(raw).expanduser().resolve())
