from __future__ import annotations

import json
from pathlib import Path

from wallpaper_manager.core.models import AppId

DEFAULT_CONFIG_PATH = Path.home() / ".wallpaper-manager" / "config.json"


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
            return {"version": 1, "apps": {}}
        return json.loads(self._path.read_text(encoding="utf-8"))

    def _write_raw(self, data: dict) -> None:
        data.setdefault("version", 1)
        data.setdefault("apps", {})
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps(data, indent=2) + "\n",
            encoding="utf-8",
        )
