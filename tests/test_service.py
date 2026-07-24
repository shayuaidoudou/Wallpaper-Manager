from pathlib import Path

from PIL import Image

from wallpaper_manager.adapters.cursor import CursorAdapter
from wallpaper_manager.adapters.ghostty import GhosttyAdapter
from wallpaper_manager.adapters.jetbrains import JetBrainsAdapter
from wallpaper_manager.adapters.vscode import VsCodeAdapter
from wallpaper_manager.core.models import AppId
from wallpaper_manager.core.service import WallpaperService, build_default_service
from wallpaper_manager.core.state_store import StateStore


class FakeAdapter:
    def __init__(
        self,
        app_id: AppId,
        installed: bool = True,
        extension_installed: bool = True,
    ):
        self.app_id = app_id
        self._installed = installed
        self._extension_installed = extension_installed
        self.path = None
        self.opacity = 20
        self.applied = []
        self.cleared = 0
        self.fail_apply = None

    def detect(self) -> bool:
        return self._installed

    def read(self) -> tuple[str | None, int]:
        return self.path, self.opacity

    def apply(self, image_path: str, opacity_ui: int) -> None:
        if self.fail_apply is not None:
            raise self.fail_apply
        self.path = image_path
        self.opacity = opacity_ui
        self.applied.append((image_path, opacity_ui))

    def clear(self) -> None:
        self.cleared += 1
        self.path = None

    def extension_installed(self) -> bool:
        return self._extension_installed


def make_image(tmp_path: Path) -> Path:
    image = tmp_path / "wallpaper.png"
    Image.new("RGB", (4, 4)).save(image)
    return image


def test_apply_and_bootstrap_reads_adapter_state(tmp_path: Path):
    fake = FakeAdapter(AppId.VSCODE)
    service = WallpaperService([fake], store=StateStore(tmp_path / "config.json"))
    image = make_image(tmp_path)

    state = service.apply(AppId.VSCODE, str(image), 40)

    assert state.last_error is None
    assert fake.applied == [(str(image), 40)]
    assert service.bootstrap()[AppId.VSCODE].image_path == str(image)


def test_bootstrap_uses_store_when_adapter_is_not_detected(tmp_path: Path):
    store = StateStore(tmp_path / "config.json")
    store.save_app(AppId.VSCODE, "/stored/wallpaper.png", 35)
    service = WallpaperService(
        [FakeAdapter(AppId.VSCODE, installed=False)], store=store
    )

    state = service.bootstrap()[AppId.VSCODE]

    assert state.installed is False
    assert state.image_path == "/stored/wallpaper.png"
    assert state.opacity_ui == 35


def test_bootstrap_preserves_store_opacity_zero_from_store_fallback(tmp_path: Path):
    store = StateStore(tmp_path / "config.json")

    store.save_app(AppId.VSCODE, "/stored/wallpaper.png", 0)
    not_detected = FakeAdapter(AppId.VSCODE, installed=False)
    service = WallpaperService([not_detected], store=store)
    state = service.bootstrap()[AppId.VSCODE]
    assert state.installed is False
    assert state.image_path == "/stored/wallpaper.png"
    assert state.opacity_ui == 0

    store_path = tmp_path / "config-no-path.json"
    store_path.write_text(
        '{"version": 1, "apps": {"vscode": {"image_path": null, "opacity_ui": 0}}}\n',
        encoding="utf-8",
    )
    store_no_path = StateStore(store_path)
    service = WallpaperService(
        [FakeAdapter(AppId.VSCODE, installed=False)], store=store_no_path
    )
    state = service.bootstrap()[AppId.VSCODE]
    assert state.image_path is None
    assert state.opacity_ui == 0


def test_bootstrap_adapter_state_wins_over_store(tmp_path: Path):
    store = StateStore(tmp_path / "config.json")
    store.save_app(AppId.VSCODE, "/stored/wallpaper.png", 35)
    fake = FakeAdapter(AppId.VSCODE)
    fake.path = "/detected/wallpaper.png"
    fake.opacity = 60
    service = WallpaperService([fake], store=store)

    state = service.bootstrap()[AppId.VSCODE]

    assert state.image_path == "/detected/wallpaper.png"
    assert state.opacity_ui == 60


def test_bootstrap_uses_store_when_installed_adapter_has_no_wallpaper(
    tmp_path: Path,
):
    store = StateStore(tmp_path / "config.json")
    store.save_app(AppId.VSCODE, "/stored/wallpaper.png", 35)
    service = WallpaperService([FakeAdapter(AppId.VSCODE)], store=store)

    state = service.bootstrap()[AppId.VSCODE]

    assert state.installed is True
    assert state.image_path == "/stored/wallpaper.png"
    assert state.opacity_ui == 35


def test_apply_failure_returns_error_without_saving(tmp_path: Path):
    fake = FakeAdapter(AppId.VSCODE)
    fake.fail_apply = RuntimeError("adapter unavailable")
    store = StateStore(tmp_path / "config.json")
    service = WallpaperService([fake], store=store)

    state = service.apply(AppId.VSCODE, str(make_image(tmp_path)), 40)

    assert state.last_error == "adapter unavailable"
    assert store.load() == {}


def test_clear_clears_adapter_and_store(tmp_path: Path):
    fake = FakeAdapter(AppId.VSCODE)
    store = StateStore(tmp_path / "config.json")
    store.save_app(AppId.VSCODE, "/stored/wallpaper.png", 35)
    service = WallpaperService([fake], store=store)

    state = service.clear(AppId.VSCODE)

    assert state.image_path is None
    assert state.last_error is None
    assert fake.cleared == 1
    assert store.load() == {}


def test_extension_tip_only_reports_missing_editor_extensions(tmp_path: Path):
    service = WallpaperService(
        [
            FakeAdapter(AppId.VSCODE, extension_installed=False),
            FakeAdapter(AppId.CURSOR),
            FakeAdapter(AppId.IDEA, extension_installed=False),
        ],
        store=StateStore(tmp_path / "config.json"),
    )

    assert service.extension_tip(AppId.VSCODE)
    assert service.extension_tip(AppId.CURSOR) is None
    assert service.extension_tip(AppId.IDEA) is None


def test_apply_records_history(tmp_path: Path):
    store = StateStore(tmp_path / "config.json")
    service = WallpaperService([FakeAdapter(AppId.VSCODE)], store=store)
    image = make_image(tmp_path)

    service.apply(AppId.VSCODE, str(image), 40)

    history = service.history()
    assert len(history) == 1
    entry = history[0]
    assert entry["image_path"] == str(image)
    assert entry["source"] == "local"
    assert entry["title"] == image.name
    assert entry["app"] == "vscode"
    assert entry["opacity_ui"] == 40
    assert entry["applied_at"]


def test_apply_with_history_entry_preserves_gallery_meta(tmp_path: Path):
    store = StateStore(tmp_path / "config.json")
    service = WallpaperService([FakeAdapter(AppId.VSCODE)], store=store)
    image = make_image(tmp_path)
    base = {
        "source": "gallery",
        "title": "星空",
        "thumb": "https://cdn.example/thumb.webp",
        "gallery": {"path": "/g/star.jpg"},
    }

    service.apply(AppId.VSCODE, str(image), 30, history_entry=base)
    # Re-apply (e.g. from the library panel) must not create a duplicate.
    service.apply(AppId.VSCODE, str(image), 55, history_entry=base)

    history = service.history()
    assert len(history) == 1
    entry = history[0]
    assert entry["source"] == "gallery"
    assert entry["title"] == "星空"
    assert entry["gallery"] == {"path": "/g/star.jpg"}
    assert entry["opacity_ui"] == 55


def test_apply_failure_records_no_history(tmp_path: Path):
    fake = FakeAdapter(AppId.VSCODE)
    fake.fail_apply = RuntimeError("boom")
    service = WallpaperService([fake], store=StateStore(tmp_path / "config.json"))

    service.apply(AppId.VSCODE, str(make_image(tmp_path)), 40)

    assert service.history() == []


def test_toggle_favorite_via_service(tmp_path: Path):
    service = WallpaperService(
        [FakeAdapter(AppId.VSCODE)], store=StateStore(tmp_path / "config.json")
    )
    entry = {
        "source": "gallery",
        "title": "星空",
        "image_path": None,
        "thumb": "https://cdn.example/thumb.webp",
        "gallery": {"path": "/g/star.jpg"},
    }

    assert service.toggle_favorite(entry) is True
    assert service.favorite_keys() == {"g:/g/star.jpg"}
    assert service.toggle_favorite(entry) is False
    assert service.favorites() == []


def test_build_default_service_wires_all_real_adapters():
    service = build_default_service()

    assert [type(adapter) for adapter in service.adapters] == [
        VsCodeAdapter,
        CursorAdapter,
        JetBrainsAdapter,
        JetBrainsAdapter,
        GhosttyAdapter,
    ]
    assert [adapter.app_id for adapter in service.adapters] == list(AppId)


def test_precheck_rejects_invalid_image(tmp_path: Path):
    service = WallpaperService(
        [FakeAdapter(AppId.VSCODE)], store=StateStore(tmp_path / "config.json")
    )
    result = service.precheck(AppId.VSCODE, str(tmp_path / "nope.png"))
    assert result.ok is False
    assert result.error


def test_precheck_rejects_undetected_app(tmp_path: Path):
    service = WallpaperService(
        [FakeAdapter(AppId.VSCODE, installed=False)],
        store=StateStore(tmp_path / "config.json"),
    )
    result = service.precheck(AppId.VSCODE, str(make_image(tmp_path)))
    assert result.ok is False
    assert "路径配置" in (result.error or "")


def test_apply_creates_backup_when_config_exists(tmp_path: Path):
    from wallpaper_manager.core.config_backup import ConfigBackupStore

    config = tmp_path / "settings.json"
    config.write_text("{}\n", encoding="utf-8")

    class PathAwareFake(FakeAdapter):
        def effective_config_path(self):
            return config

    fake = PathAwareFake(AppId.VSCODE)
    backups = ConfigBackupStore(tmp_path / "backups")
    service = WallpaperService(
        [fake], store=StateStore(tmp_path / "config.json"), backups=backups
    )
    image = make_image(tmp_path)

    state = service.apply(AppId.VSCODE, str(image), 40)
    assert state.last_error is None
    assert len(backups.list_backups(AppId.VSCODE)) == 1


def test_apply_verify_warning_on_path_mismatch(tmp_path: Path):
    class MismatchFake(FakeAdapter):
        def apply(self, image_path: str, opacity_ui: int) -> None:
            # Pretend write succeeded but store a different path.
            self.path = "/other/wallpaper.png"
            self.opacity = opacity_ui
            self.applied.append((image_path, opacity_ui))

    service = WallpaperService(
        [MismatchFake(AppId.VSCODE)], store=StateStore(tmp_path / "config.json")
    )
    state = service.apply(AppId.VSCODE, str(make_image(tmp_path)), 40)
    assert state.last_error is None
    assert state.verify_warning
    assert "不一致" in state.verify_warning


def test_apply_many_partial_failure(tmp_path: Path):
    ok = FakeAdapter(AppId.VSCODE)
    bad = FakeAdapter(AppId.CURSOR)
    bad.fail_apply = RuntimeError("cursor locked")
    service = WallpaperService(
        [ok, bad], store=StateStore(tmp_path / "config.json")
    )
    image = str(make_image(tmp_path))
    results = service.apply_many([AppId.VSCODE, AppId.CURSOR], image, 33)

    assert results[AppId.VSCODE].last_error is None
    assert results[AppId.CURSOR].last_error == "cursor locked"
    assert len(ok.applied) == 1
    assert bad.applied == []


def test_diagnose_reports_extension_and_backup_count(tmp_path: Path):
    from wallpaper_manager.core.config_backup import ConfigBackupStore

    config = tmp_path / "settings.json"
    config.write_text("{}\n", encoding="utf-8")

    class PathAwareFake(FakeAdapter):
        def effective_config_path(self):
            return config

    fake = PathAwareFake(AppId.VSCODE, extension_installed=False)
    backups = ConfigBackupStore(tmp_path / "backups")
    backups.backup_file(AppId.VSCODE, config)
    service = WallpaperService(
        [fake], store=StateStore(tmp_path / "config.json"), backups=backups
    )

    rows = service.diagnose()
    assert len(rows) == 1
    assert rows[0].installed is True
    assert rows[0].extension_ok is False
    assert rows[0].backup_count == 1


def test_restore_latest_backup(tmp_path: Path):
    from wallpaper_manager.core.config_backup import ConfigBackupStore

    config = tmp_path / "settings.json"
    config.write_text("original\n", encoding="utf-8")

    class PathAwareFake(FakeAdapter):
        def effective_config_path(self):
            return config

    backups = ConfigBackupStore(tmp_path / "backups")
    service = WallpaperService(
        [PathAwareFake(AppId.VSCODE)],
        store=StateStore(tmp_path / "config.json"),
        backups=backups,
    )
    service.apply(AppId.VSCODE, str(make_image(tmp_path)), 20)
    config.write_text("mutated\n", encoding="utf-8")
    service.restore_latest_backup(AppId.VSCODE)
    assert config.read_text(encoding="utf-8") == "original\n"
