from __future__ import annotations

from wallpaper_manager.adapters.base import WallpaperAdapter
from wallpaper_manager.adapters.cursor import CursorAdapter
from wallpaper_manager.adapters.jetbrains import IdeaAdapter, PyCharmAdapter
from wallpaper_manager.adapters.vscode import VsCodeAdapter
from wallpaper_manager.core.image_service import validate_image_path
from wallpaper_manager.core.models import AppId, WallpaperState
from wallpaper_manager.core.state_store import StateStore

DEFAULT_OPACITY_UI = 20


class WallpaperService:
    def __init__(
        self,
        adapters: list[WallpaperAdapter],
        store: StateStore | None = None,
    ) -> None:
        self.adapters = adapters
        self.store = store or StateStore()
        self._adapters = {adapter.app_id: adapter for adapter in adapters}

    def bootstrap(self) -> dict[AppId, WallpaperState]:
        stored = self.store.load()
        states: dict[AppId, WallpaperState] = {}

        for app_id, adapter in self._adapters.items():
            try:
                installed = adapter.detect()
                if installed:
                    image_path, opacity_ui = adapter.read()
                else:
                    entry = stored.get(app_id, {})
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

    @staticmethod
    def _detect(adapter: WallpaperAdapter) -> bool:
        try:
            return adapter.detect()
        except Exception:
            return False


def build_default_service() -> WallpaperService:
    return WallpaperService(
        [VsCodeAdapter(), CursorAdapter(), IdeaAdapter(), PyCharmAdapter()]
    )
