from __future__ import annotations

from pathlib import Path

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
        self.settings_path = settings_path or vscode_settings_path()

    def detect(self) -> bool:
        return self.settings_path.is_file() or self.settings_path.parent.is_dir()

    def read(self) -> tuple[str | None, int]:
        return read_background_cover(self.settings_path)

    def apply(self, image_path: str, opacity_ui: int) -> None:
        write_background_cover(self.settings_path, image_path, opacity_ui)

    def clear(self) -> None:
        clear_background_cover(self.settings_path)

    def extension_installed(self) -> bool:
        return any(
            Path.home().joinpath(".vscode", "extensions").glob(
                "manasxx.background-cover*"
            )
        )
