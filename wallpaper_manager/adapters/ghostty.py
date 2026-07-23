"""Ghostty config adapter — mutate wallpaper keys, preserve everything else."""

from __future__ import annotations

import re
from pathlib import Path

from wallpaper_manager.core.models import AppId
from wallpaper_manager.core.opacity import ghostty_to_ui, ui_to_ghostty
from wallpaper_manager.detect.paths import find_ghostty_config, ghostty_config_candidates

MANAGED_KEYS = (
    "background-image",
    "background-image-opacity",
    "background-image-position",
    "background-image-fit",
)

DEFAULT_POSITION = "center"
DEFAULT_FIT = "cover"

_LINE_RE = re.compile(
    r"^(?P<prefix>\s*)(?P<key>[\w-]+)(?P<sep>\s*=\s*)(?P<value>.*?)(?P<suffix>\s*)$"
)


def _strip_value(raw: str) -> str:
    value = raw.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def read_ghostty_wallpaper(config_path: Path) -> tuple[str | None, int]:
    if not config_path.is_file():
        return None, 20
    image_path: str | None = None
    opacity_ui = 20
    for line in config_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        match = _LINE_RE.match(line)
        if not match:
            continue
        key = match.group("key")
        value = _strip_value(match.group("value"))
        if key == "background-image":
            image_path = value or None
        elif key == "background-image-opacity":
            try:
                opacity_ui = ghostty_to_ui(float(value))
            except ValueError:
                pass
    return image_path, opacity_ui


def write_ghostty_wallpaper(
    config_path: Path,
    image_path: str,
    opacity_ui: int,
) -> None:
    config_path.parent.mkdir(parents=True, exist_ok=True)
    desired = {
        "background-image": image_path,
        "background-image-opacity": f"{ui_to_ghostty(opacity_ui):g}",
        "background-image-position": DEFAULT_POSITION,
        "background-image-fit": DEFAULT_FIT,
    }
    raw_lines = (
        config_path.read_text(encoding="utf-8").splitlines()
        if config_path.is_file()
        else []
    )
    seen: set[str] = set()
    out: list[str] = []
    for line in raw_lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            match = _LINE_RE.match(line)
            if match and match.group("key") in desired:
                key = match.group("key")
                if key in seen:
                    continue
                seen.add(key)
                out.append(
                    f"{match.group('prefix')}{key}{match.group('sep')}"
                    f"{desired[key]}{match.group('suffix')}"
                )
                continue
        out.append(line)

    missing = [key for key in MANAGED_KEYS if key not in seen]
    if missing:
        if out and out[-1].strip():
            out.append("")
        if not any("Wallpaper Manager" in line for line in out):
            out.append("# Wallpaper Manager")
        for key in missing:
            out.append(f"{key} = {desired[key]}")

    content = "\n".join(out)
    if content and not content.endswith("\n"):
        content += "\n"
    config_path.write_text(content, encoding="utf-8")


def clear_ghostty_wallpaper(config_path: Path) -> None:
    if not config_path.is_file():
        return
    raw_lines = config_path.read_text(encoding="utf-8").splitlines()
    out: list[str] = []
    for line in raw_lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            match = _LINE_RE.match(line)
            if match and match.group("key") in MANAGED_KEYS:
                continue
        if stripped == "# Wallpaper Manager":
            continue
        out.append(line)

    # Drop trailing blank runs left by removals, keep single trailing newline.
    while out and not out[-1].strip():
        out.pop()
    content = "\n".join(out)
    if content:
        content += "\n"
    config_path.write_text(content, encoding="utf-8")


class GhosttyAdapter:
    app_id = AppId.GHOSTTY

    def __init__(self, config_path: Path | None = None):
        self._path_override = config_path

    @property
    def config_path(self) -> Path:
        return self._path_override if self._path_override is not None else find_ghostty_config()

    def set_path_override(self, path: Path | None) -> None:
        self._path_override = path

    def auto_detected_path(self) -> Path | None:
        return find_ghostty_config()

    def effective_config_path(self) -> Path | None:
        return self.config_path

    def detect(self) -> bool:
        path = self.config_path
        if path.is_file() or path.parent.is_dir():
            return True
        if self._path_override is not None:
            return False
        return any(
            candidate.is_file() or candidate.parent.is_dir()
            for candidate in ghostty_config_candidates()
        )

    def read(self) -> tuple[str | None, int]:
        return read_ghostty_wallpaper(self.config_path)

    def apply(self, image_path: str, opacity_ui: int) -> None:
        write_ghostty_wallpaper(self.config_path, image_path, opacity_ui)

    def clear(self) -> None:
        clear_ghostty_wallpaper(self.config_path)

    def extension_installed(self) -> bool:
        return True
