from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from wallpaper_manager.adapters.base import WallpaperAdapter
from wallpaper_manager.adapters.cursor import CursorAdapter
from wallpaper_manager.adapters.ghostty import GhosttyAdapter
from wallpaper_manager.adapters.jetbrains import IdeaAdapter, PyCharmAdapter
from wallpaper_manager.adapters.vscode import VsCodeAdapter
from wallpaper_manager.core.config_backup import ConfigBackupStore
from wallpaper_manager.core.image_service import validate_image_path
from wallpaper_manager.core.models import (
    AppDiagnostic,
    AppId,
    PrecheckResult,
    WallpaperState,
)
from wallpaper_manager.core.path_config import (
    config_dir_hint,
    CONFIG_FILE_LABELS,
    auto_config_path,
    normalize_config_path,
    resolve_config_from_user_selection,
)
from wallpaper_manager.core.state_store import StateStore
from wallpaper_manager.gallery.models import GalleryItem
from wallpaper_manager.gallery.nuanxin_client import (
    NuanxinGalleryClient,
    build_cdn_url,
    friendly_network_error,
)

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
        backups: ConfigBackupStore | None = None,
    ) -> None:
        self.adapters = adapters
        self.store = store or StateStore()
        self.backups = backups or ConfigBackupStore()
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

    def precheck(self, app_id: AppId, image_path: str) -> PrecheckResult:
        adapter = self._adapters.get(app_id)
        if adapter is None:
            return PrecheckResult(ok=False, error=f"未找到适配器: {app_id.value}")

        valid, error = validate_image_path(image_path)
        if not valid:
            return PrecheckResult(ok=False, error=error or "图片路径无效")

        installed = self._detect(adapter)
        has_path_api = callable(getattr(adapter, "effective_config_path", None))
        config_path = self._effective_path(adapter) if has_path_api else None
        config_exists = bool(config_path and Path(config_path).expanduser().exists())

        if not installed:
            return PrecheckResult(
                ok=False,
                error="未检测到该应用的配置目录，请先在「路径配置」中指定",
                installed=False,
                config_path=str(config_path) if config_path else None,
                config_exists=config_exists,
            )

        # Real adapters expose effective_config_path; test doubles may omit it.
        if has_path_api:
            if config_path is None:
                return PrecheckResult(
                    ok=False,
                    error="无法解析配置文件路径，请在「路径配置」中手动选择",
                    installed=True,
                    config_path=None,
                    config_exists=False,
                )
            parent = Path(config_path).expanduser().parent
            if not parent.exists():
                return PrecheckResult(
                    ok=False,
                    error=f"配置目录不存在：{parent}",
                    installed=True,
                    config_path=str(config_path),
                    config_exists=False,
                )

        warning = self.extension_tip(app_id)
        return PrecheckResult(
            ok=True,
            warning=warning,
            installed=True,
            config_path=str(config_path) if config_path else None,
            config_exists=config_exists,
        )

    def apply(
        self,
        app_id: AppId,
        image_path: str,
        opacity_ui: int,
        *,
        history_entry: dict | None = None,
        skip_precheck: bool = False,
    ) -> WallpaperState:
        adapter = self._adapters.get(app_id)
        if adapter is None:
            return WallpaperState(
                app_id, image_path, opacity_ui, False, f"未找到适配器: {app_id.value}"
            )

        if not skip_precheck:
            check = self.precheck(app_id, image_path)
            if not check.ok:
                return WallpaperState(
                    app_id,
                    image_path,
                    opacity_ui,
                    check.installed,
                    check.error,
                )
            pre_warning = check.warning
        else:
            valid, error = validate_image_path(image_path)
            if not valid:
                return WallpaperState(
                    app_id, image_path, opacity_ui, self._detect(adapter), error
                )
            pre_warning = self.extension_tip(app_id)

        try:
            self._backup_adapter_config(app_id, adapter)
            adapter.apply(image_path, opacity_ui)
            self.store.save_app(app_id, image_path, opacity_ui)
        except Exception as exc:
            return WallpaperState(
                app_id, image_path, opacity_ui, self._detect(adapter), str(exc)
            )

        self._record_history(app_id, image_path, opacity_ui, history_entry)
        verify_warning = self._verify_readback(adapter, image_path, opacity_ui)
        # Prefer verify note; keep extension tip only when verify is clean.
        warning = verify_warning or pre_warning
        return WallpaperState(
            app_id,
            image_path,
            opacity_ui,
            self._detect(adapter),
            None,
            verify_warning=warning,
        )

    def apply_many(
        self,
        app_ids: list[AppId],
        image_path: str,
        opacity_ui: int,
        *,
        history_entry: dict | None = None,
    ) -> dict[AppId, WallpaperState]:
        results: dict[AppId, WallpaperState] = {}
        for app_id in app_ids:
            results[app_id] = self.apply(
                app_id,
                image_path,
                opacity_ui,
                history_entry=history_entry,
            )
        return results

    def diagnose(self) -> list[AppDiagnostic]:
        stored = self.store.load()
        rows: list[AppDiagnostic] = []
        for app_id, adapter in self._adapters.items():
            installed = self._detect(adapter)
            path = self._effective_path(adapter)
            exists = bool(path and Path(path).expanduser().exists())
            if app_id in (AppId.VSCODE, AppId.CURSOR):
                try:
                    extension_ok = adapter.extension_installed()
                except Exception:
                    extension_ok = False
            else:
                extension_ok = None
            entry = stored.get(app_id, {})
            rows.append(
                AppDiagnostic(
                    app_id=app_id,
                    label=CONFIG_FILE_LABELS.get(app_id, app_id.value),
                    installed=installed,
                    config_path=str(path) if path else None,
                    config_exists=exists,
                    extension_ok=extension_ok,
                    stored_image=entry.get("image_path"),
                    backup_count=len(self.backups.list_backups(app_id)),
                )
            )
        return rows

    def restore_latest_backup(self, app_id: AppId) -> str:
        adapter = self._adapters.get(app_id)
        if adapter is None:
            raise KeyError(app_id)
        path = self._effective_path(adapter)
        if path is None:
            raise FileNotFoundError("无法解析配置路径，请先完成路径配置")
        restored = self.backups.restore_to(app_id, Path(path))
        return str(restored)

    def list_backups(self, app_id: AppId) -> list[Path]:
        return self.backups.list_backups(app_id)

    def _backup_adapter_config(
        self, app_id: AppId, adapter: WallpaperAdapter
    ) -> Path | None:
        path = self._effective_path(adapter)
        if path is None:
            return None
        try:
            return self.backups.backup_file(app_id, Path(path).expanduser())
        except OSError:
            return None

    def _verify_readback(
        self,
        adapter: WallpaperAdapter,
        image_path: str,
        opacity_ui: int,
    ) -> str | None:
        try:
            read_path, read_opacity = adapter.read()
        except Exception as exc:
            return f"已写入，但回读失败：{exc}"
        expected = str(Path(image_path).expanduser())
        actual = str(Path(read_path).expanduser()) if read_path else None
        if actual is None:
            return "已写入，但回读未看到壁纸路径（部分应用需重启后生效）"
        if Path(actual).resolve() != Path(expected).resolve():
            return "已写入，但回读路径不一致，配置可能被 IDE 覆盖"
        if int(read_opacity) != int(opacity_ui):
            return "已写入，但透明度回读不一致"
        return None

    def _record_history(
        self,
        app_id: AppId,
        image_path: str,
        opacity_ui: int,
        base: dict | None,
    ) -> None:
        entry = dict(base) if base else {
            "source": "local",
            "title": Path(image_path).name,
            "thumb": image_path,
            "gallery": None,
        }
        entry.update(
            {
                "image_path": image_path,
                "app": app_id.value,
                "opacity_ui": opacity_ui,
                "applied_at": datetime.now().isoformat(timespec="seconds"),
            }
        )
        try:
            self.store.add_history(entry)
        except Exception:
            # The wallpaper is already applied — a bookkeeping failure must not
            # surface as an apply error.
            pass

    def history(self) -> list[dict]:
        return self.store.load_history()

    def favorites(self) -> list[dict]:
        return self.store.load_favorites()

    def toggle_favorite(self, entry: dict) -> bool:
        return self.store.toggle_favorite(entry)

    def favorite_keys(self) -> set[str]:
        return self.store.favorite_keys()

    def clear(self, app_id: AppId) -> WallpaperState:
        adapter = self._adapters.get(app_id)
        if adapter is None:
            return WallpaperState(
                app_id, None, DEFAULT_OPACITY_UI, False, f"未找到适配器: {app_id.value}"
            )

        try:
            self._backup_adapter_config(app_id, adapter)
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

    def gallery_download_dir(self) -> Path:
        return self.store.load_gallery_download_dir()

    def set_gallery_download_dir(self, download_dir: str | None) -> Path:
        if download_dir and download_dir.strip():
            path = Path(download_dir.strip()).expanduser().resolve()
            path.mkdir(parents=True, exist_ok=True)
            return self.store.save_gallery_download_dir(path)
        return self.store.save_gallery_download_dir(None)

    async def apply_gallery_item(
        self,
        app_id: AppId,
        item: GalleryItem,
        opacity_ui: int,
        *,
        client: NuanxinGalleryClient | None = None,
    ) -> WallpaperState:
        """Download full image then apply to the target app."""
        owns = client is None
        gallery = client or NuanxinGalleryClient()
        try:
            local = await gallery.download_full(item, self.gallery_download_dir())
        except Exception as exc:
            if owns:
                await gallery.aclose()
            adapter = self._adapters.get(app_id)
            return WallpaperState(
                app_id,
                None,
                opacity_ui,
                self._detect(adapter) if adapter else False,
                f"下载失败：{friendly_network_error(exc)}",
            )
        if owns:
            await gallery.aclose()
        try:
            thumb = build_cdn_url(item, kind="thumbnail")
        except ValueError:
            thumb = str(local)
        entry = {
            "source": "gallery",
            "title": item.display_title,
            "thumb": thumb,
            "gallery": item.to_dict(),
        }
        return self.apply(app_id, str(local), opacity_ui, history_entry=entry)

    @staticmethod
    def _detect(adapter: WallpaperAdapter) -> bool:
        try:
            return adapter.detect()
        except Exception:
            return False

    @staticmethod
    def _effective_path(adapter: WallpaperAdapter) -> Path | None:
        getter = getattr(adapter, "effective_config_path", None)
        if not callable(getter):
            return None
        try:
            return getter()
        except Exception:
            return None


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
