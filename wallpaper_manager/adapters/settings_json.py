from __future__ import annotations

import json
from pathlib import Path

from wallpaper_manager.core.opacity import (
    background_cover_to_ui,
    ui_to_background_cover,
)

IMAGE_PATH_KEY = "backgroundCover.imagePath"
OPACITY_KEY = "backgroundCover.opacity"


def _strip_jsonc(text: str) -> str:
    stripped: list[str] = []
    index = 0
    in_string = False
    escaped = False
    while index < len(text):
        char = text[index]
        next_char = text[index + 1] if index + 1 < len(text) else ""
        if in_string:
            stripped.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            index += 1
            continue
        if char == '"':
            in_string = True
            stripped.append(char)
            index += 1
            continue
        if char == "/" and next_char == "/":
            index += 2
            while index < len(text) and text[index] not in "\r\n":
                index += 1
            continue
        if char == "/" and next_char == "*":
            index += 2
            while index + 1 < len(text) and text[index : index + 2] != "*/":
                index += 1
            index = min(index + 2, len(text))
            continue
        stripped.append(char)
        index += 1

    without_comments = "".join(stripped)
    result: list[str] = []
    index = 0
    in_string = False
    escaped = False
    while index < len(without_comments):
        char = without_comments[index]
        if in_string:
            result.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
        elif char == '"':
            in_string = True
            result.append(char)
        elif char == ",":
            lookahead = index + 1
            while (
                lookahead < len(without_comments)
                and without_comments[lookahead].isspace()
            ):
                lookahead += 1
            if (
                lookahead < len(without_comments)
                and without_comments[lookahead] in "}]"
            ):
                index += 1
                continue
            result.append(char)
        else:
            result.append(char)
        index += 1
    return "".join(result)


def _load_settings(settings_path: Path) -> dict:
    if not settings_path.is_file():
        return {}
    return json.loads(_strip_jsonc(settings_path.read_text(encoding="utf-8")))


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
