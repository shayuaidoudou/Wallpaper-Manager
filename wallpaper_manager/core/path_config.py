"""Per-app config path hints and user-folder resolution."""

from __future__ import annotations

import sys
from pathlib import Path

from wallpaper_manager.core.models import AppId
from wallpaper_manager.detect.paths import (
    cursor_settings_path,
    find_ghostty_config,
    find_jetbrains_other_xml,
    vscode_settings_path,
)

# Exact file we ultimately write.
CONFIG_FILE_LABELS = {
    AppId.VSCODE: "settings.json",
    AppId.CURSOR: "settings.json",
    AppId.IDEA: "other.xml",
    AppId.PYCHARM: "other.xml",
    AppId.GHOSTTY: "config / config.ghostty",
}

_DIR_HINTS_DARWIN = {
    AppId.VSCODE: "~/Library/Application Support/Code （或其中的 User 目录）",
    AppId.CURSOR: "~/Library/Application Support/Cursor （或其中的 User 目录）",
    AppId.IDEA: "~/Library/Application Support/JetBrains/IntelliJIdea* 版本目录",
    AppId.PYCHARM: "~/Library/Application Support/JetBrains/PyCharm* 版本目录",
    AppId.GHOSTTY: "~/Library/Application Support/com.mitchellh.ghostty",
}

_DIR_HINTS_WIN32 = {
    AppId.VSCODE: r"%APPDATA%\Code （或其中的 User 目录）",
    AppId.CURSOR: r"%APPDATA%\Cursor （或其中的 User 目录）",
    AppId.IDEA: r"%APPDATA%\JetBrains\IntelliJIdea* 版本目录",
    AppId.PYCHARM: r"%APPDATA%\JetBrains\PyCharm* 版本目录",
    AppId.GHOSTTY: r"%APPDATA%\ghostty",
}

_PATH_HINTS_DARWIN = {
    AppId.VSCODE: "~/Library/Application Support/Code/User/settings.json",
    AppId.CURSOR: "~/Library/Application Support/Cursor/User/settings.json",
    AppId.IDEA: "~/Library/Application Support/JetBrains/IntelliJIdea*/options/other.xml",
    AppId.PYCHARM: "~/Library/Application Support/JetBrains/PyCharm*/options/other.xml",
    AppId.GHOSTTY: "~/Library/Application Support/com.mitchellh.ghostty/config.ghostty",
}

_PATH_HINTS_WIN32 = {
    AppId.VSCODE: r"%APPDATA%\Code\User\settings.json",
    AppId.CURSOR: r"%APPDATA%\Cursor\User\settings.json",
    AppId.IDEA: r"%APPDATA%\JetBrains\IntelliJIdea*\options\other.xml",
    AppId.PYCHARM: r"%APPDATA%\JetBrains\PyCharm*\options\other.xml",
    AppId.GHOSTTY: r"%APPDATA%\ghostty\config",
}

_INSTALL_NAME_HINTS = {
    AppId.VSCODE: ("visual studio code.app", "code.app", "code.exe"),
    AppId.CURSOR: ("cursor.app", "cursor.exe"),
    AppId.IDEA: ("intellij idea.app", "idea.app", "idea64.exe"),
    AppId.PYCHARM: ("pycharm.app", "pycharm64.exe"),
    AppId.GHOSTTY: ("ghostty.app", "ghostty.exe"),
}

# Folder name tokens only matched inside Program Files / Local\Programs trees.
_INSTALL_DIR_TOKENS = {
    AppId.VSCODE: ("code", "vscode", "microsoft vs code"),
    AppId.CURSOR: ("cursor",),
    AppId.IDEA: ("intellij", "idea"),
    AppId.PYCHARM: ("pycharm",),
    AppId.GHOSTTY: ("ghostty",),
}


def config_dir_hint(app_id: AppId) -> str:
    """OS-specific folder users should pick in Settings."""
    table = _DIR_HINTS_WIN32 if sys.platform == "win32" else _DIR_HINTS_DARWIN
    return table[app_id]


def config_path_hint(app_id: AppId) -> str:
    """OS-specific final config file path for docs/status."""
    table = _PATH_HINTS_WIN32 if sys.platform == "win32" else _PATH_HINTS_DARWIN
    return table[app_id]


# Backward-compatible aliases (resolved at import time for the current OS).
CONFIG_DIR_HINTS = {app_id: config_dir_hint(app_id) for app_id in AppId}
CONFIG_PATH_HINTS = {app_id: config_path_hint(app_id) for app_id in AppId}


def data_root_guidance() -> str:
    if sys.platform == "win32":
        return "请选择各应用的数据目录（%APPDATA%），不要选 Program Files 安装目录。"
    return (
        "请选择各应用的数据目录（Application Support），"
        "我们会自动定位配置文件。不建议选 .app 安装包本身。"
    )


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


def _in_windows_install_tree(path: Path) -> bool:
    parts = [p.lower() for p in path.parts]
    if "program files" in parts or "program files (x86)" in parts:
        return True
    # Typical Electron installs: %LOCALAPPDATA%\Programs\Cursor
    lower = str(path).lower().replace("/", "\\")
    return "\\appdata\\local\\programs\\" in lower


def _looks_like_install_root(app_id: AppId, path: Path) -> bool:
    name = path.name.lower()
    for hint in _INSTALL_NAME_HINTS.get(app_id, ()):
        if name == hint or name.endswith(hint):
            return True
    if _in_windows_install_tree(path):
        return any(token in name for token in _INSTALL_DIR_TOKENS.get(app_id, ()))
    return False


def _settings_json_candidates(root: Path) -> list[Path]:
    return [
        root / "settings.json",
        root / "User" / "settings.json",
        root / "Code" / "User" / "settings.json",
        root / "Cursor" / "User" / "settings.json",
    ]


def _jetbrains_candidates(root: Path, prefixes: tuple[str, ...]) -> list[Path]:
    out = [
        root / "other.xml",
        root / "options" / "other.xml",
    ]
    if root.is_dir():
        for child in sorted(root.iterdir(), reverse=True):
            if child.is_dir() and any(child.name.startswith(p) for p in prefixes):
                out.append(child / "options" / "other.xml")
    return out


def _ghostty_candidates(root: Path) -> list[Path]:
    return [
        root / "config.ghostty",
        root / "config",
        root / "ghostty" / "config.ghostty",
        root / "ghostty" / "config",
        root / "com.mitchellh.ghostty" / "config.ghostty",
        root / "com.mitchellh.ghostty" / "config",
    ]


def _candidate_files(app_id: AppId, root: Path) -> list[Path]:
    if app_id in (AppId.VSCODE, AppId.CURSOR):
        return _settings_json_candidates(root)
    if app_id is AppId.IDEA:
        return _jetbrains_candidates(root, ("IntelliJIdea", "IdeaIC"))
    if app_id is AppId.PYCHARM:
        return _jetbrains_candidates(root, ("PyCharm",))
    if app_id is AppId.GHOSTTY:
        return _ghostty_candidates(root)
    return []


def _is_plausible_target(app_id: AppId, candidate: Path) -> bool:
    """Allow prospective paths only when the parent folder clearly matches."""
    parent = candidate.parent
    if not parent.is_dir():
        return False
    if app_id in (AppId.VSCODE, AppId.CURSOR):
        return candidate.name == "settings.json" and parent.name == "User"
    if app_id in (AppId.IDEA, AppId.PYCHARM):
        return candidate.name == "other.xml" and parent.name == "options"
    if app_id is AppId.GHOSTTY:
        return candidate.name in {"config", "config.ghostty"}
    return False


def resolve_config_from_user_selection(
    app_id: AppId, selected: str | Path
) -> tuple[Path | None, str | None]:
    """Resolve a user-picked folder/file/.app into the real config file.

    Returns (resolved_path, error_message).
    """
    raw = Path(str(selected)).expanduser()
    try:
        path = raw.resolve()
    except OSError:
        path = raw

    if path.is_file():
        return path, None

    if not path.exists():
        if path.suffix:
            return path, None
        return None, "路径不存在，请选择应用的数据目录或版本目录"

    if _looks_like_install_root(app_id, path):
        auto = auto_config_path(app_id)
        if auto is not None:
            return auto, None
        data_hint = "%APPDATA%" if sys.platform == "win32" else "Application Support"
        return (
            None,
            f"选中的是安装目录，但未能映射到默认配置位置，请改选 {data_hint} 下的数据目录",
        )

    for candidate in _candidate_files(app_id, path):
        if candidate.is_file():
            return candidate, None

    for candidate in _candidate_files(app_id, path):
        if _is_plausible_target(app_id, candidate):
            return candidate, None

    return None, (
        f"在所选目录中未找到 {CONFIG_FILE_LABELS[app_id]}。"
        f"请选择类似：{config_dir_hint(app_id)}"
    )
