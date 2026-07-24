from __future__ import annotations

import json
from pathlib import Path

from wallpaper_manager.core.models import AppId

DEFAULT_CONFIG_PATH = Path.home() / ".wallpaper-manager" / "config.json"
DEFAULT_GALLERY_DOWNLOAD_DIR = Path.home() / "Pictures" / "WallpaperManager"
HISTORY_LIMIT = 60


def library_entry_key(entry: dict) -> str:
    """Identity for dedupe: gallery items key by remote path, locals by file path."""
    gallery = entry.get("gallery")
    if isinstance(gallery, dict) and gallery.get("path"):
        return f"g:{gallery['path']}"
    return f"l:{entry.get('image_path') or ''}"


class StateStore:
    def __init__(self, path: Path | None = None) -> None:
        self._path = path if path is not None else DEFAULT_CONFIG_PATH

    def load(self) -> dict[AppId, dict]:
        if not self._path.exists():
            return {}

        raw = json.loads(self._path.read_text(encoding="utf-8"))
        apps = raw.get("apps", {})
        result: dict[AppId, dict] = {}
        for app_id in AppId:
            entry = apps.get(app_id.value)
            if entry is not None:
                result[app_id] = {
                    "image_path": entry.get("image_path"),
                    "opacity_ui": entry.get("opacity_ui"),
                }
        return result

    def load_path_overrides(self) -> dict[AppId, str]:
        """Return only apps with a non-empty custom config-file path."""
        raw = self._read_raw()
        paths = raw.get("paths", {})
        result: dict[AppId, str] = {}
        if not isinstance(paths, dict):
            return result
        for app_id in AppId:
            value = paths.get(app_id.value)
            if isinstance(value, str) and value.strip():
                result[app_id] = value.strip()
        return result

    def save_path_override(self, app_id: AppId, config_path: str | None) -> None:
        data = self._read_raw()
        paths = data.setdefault("paths", {})
        if config_path and config_path.strip():
            paths[app_id.value] = config_path.strip()
        else:
            paths.pop(app_id.value, None)
        data["paths"] = paths
        self._write_raw(data)

    def load_gallery_download_dir(self) -> Path:
        raw = self._read_raw()
        gallery = raw.get("gallery")
        if isinstance(gallery, dict):
            value = gallery.get("download_dir")
            if isinstance(value, str) and value.strip():
                return Path(value.strip()).expanduser()
        return DEFAULT_GALLERY_DOWNLOAD_DIR

    def save_gallery_download_dir(self, download_dir: str | Path | None) -> Path:
        data = self._read_raw()
        gallery = data.setdefault("gallery", {})
        if download_dir is None or not str(download_dir).strip():
            gallery.pop("download_dir", None)
            data["gallery"] = gallery
            self._write_raw(data)
            return DEFAULT_GALLERY_DOWNLOAD_DIR
        path = Path(str(download_dir).strip()).expanduser()
        gallery["download_dir"] = str(path)
        data["gallery"] = gallery
        self._write_raw(data)
        return path

    def load_history(self) -> list[dict]:
        return self._load_library_list("history")

    def add_history(self, entry: dict) -> None:
        data = self._read_raw()
        library = data.setdefault("library", {})
        history = [e for e in library.get("history", []) if isinstance(e, dict)]
        key = library_entry_key(entry)
        history = [e for e in history if library_entry_key(e) != key]
        history.insert(0, entry)
        library["history"] = history[:HISTORY_LIMIT]
        self._write_raw(data)

    def load_favorites(self) -> list[dict]:
        return self._load_library_list("favorites")

    def toggle_favorite(self, entry: dict) -> bool:
        """Add or remove a favorite; returns True when now favorited."""
        data = self._read_raw()
        library = data.setdefault("library", {})
        favorites = [e for e in library.get("favorites", []) if isinstance(e, dict)]
        key = library_entry_key(entry)
        remaining = [e for e in favorites if library_entry_key(e) != key]
        now_favorite = len(remaining) == len(favorites)
        if now_favorite:
            remaining.insert(0, entry)
        library["favorites"] = remaining
        self._write_raw(data)
        return now_favorite

    def favorite_keys(self) -> set[str]:
        return {library_entry_key(e) for e in self.load_favorites()}

    def _load_library_list(self, name: str) -> list[dict]:
        library = self._read_raw().get("library")
        if not isinstance(library, dict):
            return []
        items = library.get(name)
        if not isinstance(items, list):
            return []
        return [e for e in items if isinstance(e, dict)]

    def save_app(self, app_id: AppId, image_path: str, opacity_ui: int) -> None:
        data = self._read_raw()
        data.setdefault("apps", {})[app_id.value] = {
            "image_path": image_path,
            "opacity_ui": opacity_ui,
        }
        self._write_raw(data)

    def clear_app(self, app_id: AppId) -> None:
        data = self._read_raw()
        apps = data.get("apps", {})
        apps.pop(app_id.value, None)
        data["apps"] = apps
        self._write_raw(data)

    def _read_raw(self) -> dict:
        if not self._path.exists():
            return {
                "version": 1,
                "apps": {},
                "paths": {},
                "gallery": {},
                "library": {},
            }
        raw = json.loads(self._path.read_text(encoding="utf-8"))
        raw.setdefault("version", 1)
        raw.setdefault("apps", {})
        raw.setdefault("paths", {})
        raw.setdefault("gallery", {})
        raw.setdefault("library", {})
        return raw

    def _write_raw(self, data: dict) -> None:
        data.setdefault("version", 1)
        data.setdefault("apps", {})
        data.setdefault("paths", {})
        data.setdefault("gallery", {})
        data.setdefault("library", {})
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
