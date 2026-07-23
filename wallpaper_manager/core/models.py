from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class AppId(str, Enum):
    VSCODE = "vscode"
    CURSOR = "cursor"
    IDEA = "idea"
    PYCHARM = "pycharm"


@dataclass
class WallpaperState:
    app_id: AppId
    image_path: str | None
    opacity_ui: int
    installed: bool
    last_error: str | None = None
