from __future__ import annotations

from pathlib import Path

from wallpaper_manager.adapters.background_cover_dom import sync_electron_css
from wallpaper_manager.adapters.settings_json import (
    clear_background_cover,
    read_background_cover,
    write_background_cover,
)
from wallpaper_manager.core.models import AppId
from wallpaper_manager.detect.paths import vscode_settings_path


class VsCodeAdapter:
    app_id = AppId.VSCODE

    def __init__(self, settings_path: Path | None = None):
        self._path_override = settings_path

    @property
    def settings_path(self) -> Path:
        return self._path_override if self._path_override is not None else vscode_settings_path()

    def set_path_override(self, path: Path | None) -> None:
        self._path_override = path

    def auto_detected_path(self) -> Path | None:
        return vscode_settings_path()

    def effective_config_path(self) -> Path | None:
        return self.settings_path

    def detect(self) -> bool:
        path = self.settings_path
        return path.is_file() or path.parent.is_dir()

    def read(self) -> tuple[str | None, int]:
        return read_background_cover(self.settings_path)

    def apply(self, image_path: str, opacity_ui: int) -> None:
        write_background_cover(self.settings_path, image_path, opacity_ui)
        sync_electron_css("vscode", image_path, opacity_ui)

    def clear(self) -> None:
        clear_background_cover(self.settings_path)
        sync_electron_css("vscode", None, 0)

    def extension_installed(self) -> bool:
        return any(
            Path.home().joinpath(".vscode", "extensions").glob(
                "manasxx.background-cover*"
            )
        )
