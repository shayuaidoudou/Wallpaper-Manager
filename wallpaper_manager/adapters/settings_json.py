from __future__ import annotations

import json
from pathlib import Path

from wallpaper_manager.core.opacity import (
    background_cover_to_ui,
    ui_to_background_cover,
)

IMAGE_PATH_KEY = "backgroundCover.imagePath"
OPACITY_KEY = "backgroundCover.opacity"


def _load_settings(settings_path: Path) -> dict:
    if not settings_path.is_file():
        return {}
    return json.loads(settings_path.read_text(encoding="utf-8"))


def read_background_cover(settings_path: Path) -> tuple[str | None, int]:
    settings = _load_settings(settings_path)
    image_path = settings.get(IMAGE_PATH_KEY)
    opacity = settings.get(OPACITY_KEY, 0)
    return image_path, background_cover_to_ui(opacity)


def write_background_cover(
    settings_path: Path, image_path: str, opacity_ui: int
) -> None:
    settings = _load_settings(settings_path)
    settings[IMAGE_PATH_KEY] = image_path
    settings[OPACITY_KEY] = ui_to_background_cover(opacity_ui)
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text(
        json.dumps(settings, ensure_ascii=False, indent=4) + "\n",
        encoding="utf-8",
    )


def clear_background_cover(settings_path: Path) -> None:
    if not settings_path.is_file():
        return
    settings = _load_settings(settings_path)
    settings.pop(IMAGE_PATH_KEY, None)
    settings.pop(OPACITY_KEY, None)
    settings_path.write_text(
        json.dumps(settings, ensure_ascii=False, indent=4) + "\n",
        encoding="utf-8",
    )
