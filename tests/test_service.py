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
