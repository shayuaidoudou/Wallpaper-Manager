from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class AppId(str, Enum):
    DESKTOP = "desktop"
    VSCODE = "vscode"
    CURSOR = "cursor"
    IDEA = "idea"
    PYCHARM = "pycharm"
    WEBSTORM = "webstorm"
    PHPSTORM = "phpstorm"
    GOLAND = "goland"
    CLION = "clion"
    RIDER = "rider"
    DATAGRIP = "datagrip"
    GHOSTTY = "ghostty"


# JetBrains 全家桶共用同一套 other.xml 机制，仅产品目录前缀不同。
JETBRAINS_PRODUCT_PREFIXES: dict[AppId, str] = {
    AppId.IDEA: "IntelliJIdea",
    AppId.PYCHARM: "PyCharm",
    AppId.WEBSTORM: "WebStorm",
    AppId.PHPSTORM: "PhpStorm",
    AppId.GOLAND: "GoLand",
    AppId.CLION: "CLion",
    AppId.RIDER: "Rider",
    AppId.DATAGRIP: "DataGrip",
}
JETBRAINS_APP_IDS: tuple[AppId, ...] = tuple(JETBRAINS_PRODUCT_PREFIXES)


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
