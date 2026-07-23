from __future__ import annotations

from pathlib import Path
from typing import Protocol

from wallpaper_manager.core.models import AppId


class WallpaperAdapter(Protocol):
    app_id: AppId

    def detect(self) -> bool:
        ...

    def read(self) -> tuple[str | None, int]:
        ...

    def apply(self, image_path: str, opacity_ui: int) -> None:
        ...

    def clear(self) -> None:
        ...

    def extension_installed(self) -> bool:
        ...
