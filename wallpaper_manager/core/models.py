from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class AppId(str, Enum):
    VSCODE = "vscode"
    CURSOR = "cursor"
    IDEA = "idea"
    PYCHARM = "pycharm"
    GHOSTTY = "ghostty"


@dataclass
class WallpaperState:
    app_id: AppId
    image_path: str | None
    opacity_ui: int
    installed: bool
    last_error: str | None = None
    verify_warning: str | None = None


@dataclass
class PrecheckResult:
    ok: bool
    error: str | None = None
    warning: str | None = None
    installed: bool = False
    config_path: str | None = None
    config_exists: bool = False


@dataclass
class AppDiagnostic:
    app_id: AppId
    label: str
    installed: bool
    config_path: str | None
    config_exists: bool
    extension_ok: bool | None
    stored_image: str | None
    backup_count: int
