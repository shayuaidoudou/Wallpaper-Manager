from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from wallpaper_manager.adapters.base import WallpaperAdapter
from wallpaper_manager.adapters.cursor import CursorAdapter
from wallpaper_manager.adapters.ghostty import GhosttyAdapter
from wallpaper_manager.adapters.jetbrains import IdeaAdapter, PyCharmAdapter
from wallpaper_manager.adapters.vscode import VsCodeAdapter
from wallpaper_manager.core.image_service import validate_image_path
from wallpaper_manager.core.models import AppId, WallpaperState
from wallpaper_manager.core.path_config import (
    config_dir_hint,
    CONFIG_FILE_LABELS,
    auto_config_path,
    normalize_config_path,
    resolve_config_from_user_selection,
)
from wallpaper_manager.core.state_store import StateStore

DEFAULT_OPACITY_UI = 20


@dataclass
class AppPathInfo:
    app_id: AppId
    label: str
    hint: str
    auto_path: str | None
    override_path: str | None
    effective_path: str | None
    exists: bool
    using_override: bool


class WallpaperService:
    def __init__(
        self,
        adapters: list[WallpaperAdapter],
        store: StateStore | None = None,
    ) -> None:
        self.adapters = adapters
        self.store = store or StateStore()
        self._adapters = {adapter.app_id: adapter for adapter in adapters}
        self.apply_stored_path_overrides()

    def bootstrap(self) -> dict[AppId, WallpaperState]:
        stored = self.store.load()
        states: dict[AppId, WallpaperState] = {}

        for app_id, adapter in self._adapters.items():
            try:
                entry = stored.get(app_id, {})
                installed = adapter.detect()
                if installed:
                    image_path, opacity_ui = adapter.read()
                    if image_path is None and entry.get("image_path") is not None:
                        image_path = entry["image_path"]
                        stored_opacity = entry.get("opacity_ui")
                        if stored_opacity is not None:
                            opacity_ui = stored_opacity
                else:
                    image_path = entry.get("image_path")
                    opacity_ui = entry.get("opacity_ui")
                    if opacity_ui is None:
                        opacity_ui = DEFAULT_OPACITY_UI
                states[app_id] = WallpaperState(
                    app_id=app_id,
                    image_path=image_path,
                    opacity_ui=opacity_ui,
                    installed=installed,
                )
            except Exception as exc:
                entry = stored.get(app_id, {})
                stored_opacity = entry.get("opacity_ui")
                opacity_ui = (
                    DEFAULT_OPACITY_UI if stored_opacity is None else stored_opacity
                )
                states[app_id] = WallpaperState(
                    app_id=app_id,
                    image_path=entry.get("image_path"),
                    opacity_ui=opacity_ui,
                    installed=False,
                    last_error=str(exc),
                )

        return states

    def apply(
        self,
        app_id: AppId,
        image_path: str,
        opacity_ui: int,
    ) -> WallpaperState:
        adapter = self._adapters.get(app_id)
        if adapter is None:
            return WallpaperState(
                app_id, image_path, opacity_ui, False, f"未找到适配器: {app_id.value}"
            )

        valid, error = validate_image_path(image_path)
        if not valid:
            return WallpaperState(
                app_id, image_path, opacity_ui, self._detect(adapter), error
            )

        try:
            adapter.apply(image_path, opacity_ui)
            self.store.save_app(app_id, image_path, opacity_ui)
        except Exception as exc:
            return WallpaperState(
                app_id, image_path, opacity_ui, self._detect(adapter), str(exc)
            )

        return WallpaperState(
            app_id, image_path, opacity_ui, self._detect(adapter), None
        )

    def clear(self, app_id: AppId) -> WallpaperState:
        adapter = self._adapters.get(app_id)
        if adapter is None:
            return WallpaperState(
                app_id, None, DEFAULT_OPACITY_UI, False, f"未找到适配器: {app_id.value}"
            )

        try:
            adapter.clear()
            self.store.clear_app(app_id)
        except Exception as exc:
            return WallpaperState(
                app_id, None, DEFAULT_OPACITY_UI, self._detect(adapter), str(exc)
            )

        return WallpaperState(
            app_id, None, DEFAULT_OPACITY_UI, self._detect(adapter), None
        )

    def extension_tip(self, app_id: AppId) -> str | None:
        if app_id not in (AppId.VSCODE, AppId.CURSOR):
            return None
        adapter = self._adapters.get(app_id)
        if adapter is None or adapter.extension_installed():
            return None
        return f"请为 {app_id.value} 安装 Background Cover 扩展"

    def apply_stored_path_overrides(self) -> None:
        overrides = self.store.load_path_overrides()
        for app_id, adapter in self._adapters.items():
            setter = getattr(adapter, "set_path_override", None)
            if not callable(setter):
                continue
            raw = overrides.get(app_id)
            setter(Path(raw).expanduser() if raw else None)

    def path_info(self, app_id: AppId) -> AppPathInfo:
        adapter = self._adapters[app_id]
        overrides = self.store.load_path_overrides()
        override = overrides.get(app_id)
        auto = getattr(adapter, "auto_detected_path", lambda: auto_config_path(app_id))()
        effective = getattr(adapter, "effective_config_path", lambda: auto)()
        auto_str = str(auto) if auto is not None else None
        effective_str = str(effective) if effective is not None else None
        exists = bool(effective and Path(effective).expanduser().exists())
        return AppPathInfo(
            app_id=app_id,
            label=CONFIG_FILE_LABELS[app_id],
            hint=config_dir_hint(app_id),
            auto_path=auto_str,
            override_path=override,
            effective_path=effective_str,
            exists=exists,
            using_override=bool(override),
        )

    def set_path_override(self, app_id: AppId, config_path: str | None) -> AppPathInfo:
        adapter = self._adapters.get(app_id)
        if adapter is None:
            raise KeyError(app_id)
        cleaned: str | None = None
        if config_path and config_path.strip():
            resolved, error = resolve_config_from_user_selection(app_id, config_path)
            if error or resolved is None:
                raise ValueError(error or "无法解析配置路径")
            cleaned = normalize_config_path(str(resolved))
        self.store.save_path_override(app_id, cleaned)
        setter = getattr(adapter, "set_path_override", None)
        if callable(setter):
            setter(Path(cleaned) if cleaned else None)
        return self.path_info(app_id)

    @staticmethod
    def _detect(adapter: WallpaperAdapter) -> bool:
        try:
            return adapter.detect()
        except Exception:
            return False


def build_default_service() -> WallpaperService:
    return WallpaperService(
        [
            VsCodeAdapter(),
            CursorAdapter(),
            IdeaAdapter(),
            PyCharmAdapter(),
            GhosttyAdapter(),
        ]
    )
