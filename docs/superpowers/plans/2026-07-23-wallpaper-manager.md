# Wallpaper Manager Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python + Flet desktop app that sets per-app wallpapers (path + opacity) for VS Code, Cursor, IntelliJ IDEA, and PyCharm on macOS and Windows.

**Architecture:** Flet UI talks only to a small core service. Adapters read/write each IDE’s real config (`backgroundCover.*` in settings.json; `idea.background.editor` in JetBrains `other.xml`). Local memory lives in `~/.wallpaper-manager/config.json`.

**Tech Stack:** Python 3.11+, Flet, Pillow, pytest, stdlib `json` / `xml.etree` / `pathlib`

## Global Constraints

- Platforms: macOS + Windows only for path resolution
- v1 apps: vscode, cursor, idea, pycharm only
- VS Code/Cursor mechanism: `manasxx.background-cover` keys `backgroundCover.imagePath` + `backgroundCover.opacity` (0–0.8)
- JetBrains mechanism: `idea.background.editor` = `path,opacityInt,scale,center`
- UI opacity: integer 0–100; map per adapter as in the design spec
- Layout: top tabs + large preview; theme Midnight Glass (cyan accents `#22d3ee` / `#38bdf8`)
- No blur, no gallery, no one-click sync-all, no WebStorm in v1
- Package import root: `wallpaper_manager`
- JDK/Java not involved; use system Python 3.11+

## File Structure

```
pyproject.toml
README.md
wallpaper_manager/
  __init__.py
  __main__.py
  core/
    models.py
    opacity.py
    state_store.py
    image_service.py
    service.py
  detect/
    paths.py
  adapters/
    base.py
    settings_json.py
    vscode.py
    cursor.py
    jetbrains.py
  ui/
    theme.py
    app.py
tests/
  test_opacity.py
  test_paths.py
  test_state_store.py
  test_image_service.py
  test_settings_json.py
  test_jetbrains.py
  test_service.py
```

---

### Task 1: Project scaffold

**Files:**
- Create: `pyproject.toml`
- Create: `wallpaper_manager/__init__.py`
- Create: `wallpaper_manager/__main__.py` (stub)
- Create: `README.md`

**Interfaces:**
- Consumes: none
- Produces: installable package `wallpaper_manager`; pytest runnable via `pytest`

- [ ] **Step 1: Create `pyproject.toml`**

```toml
[project]
name = "wallpaper-manager"
version = "0.1.0"
description = "Unified wallpaper manager for VS Code, Cursor, IDEA, PyCharm"
requires-python = ">=3.11"
dependencies = [
  "flet>=0.27.0",
  "pillow>=10.0.0",
]

[project.optional-dependencies]
dev = ["pytest>=8.0.0"]

[project.scripts]
wallpaper-manager = "wallpaper_manager.__main__:main"

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
include = ["wallpaper_manager*"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] **Step 2: Create package stubs**

`wallpaper_manager/__init__.py`:

```python
__version__ = "0.1.0"
```

`wallpaper_manager/__main__.py`:

```python
def main() -> None:
    print("Wallpaper Manager scaffold OK")


if __name__ == "__main__":
    main()
```

`README.md` (short): how to `python -m venv .venv`, install deps, run `python -m wallpaper_manager`, run `pytest`.

- [ ] **Step 3: Create venv and install**

```bash
cd /Users/cuitian/ShayuApp/Wallpaper-Manager
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python -m wallpaper_manager
```

Expected: prints `Wallpaper Manager scaffold OK`

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml README.md wallpaper_manager/__init__.py wallpaper_manager/__main__.py
git commit -m "chore: scaffold wallpaper-manager package"
```

---

### Task 2: Models + opacity mapping

**Files:**
- Create: `wallpaper_manager/core/models.py`
- Create: `wallpaper_manager/core/opacity.py`
- Create: `wallpaper_manager/core/__init__.py`
- Test: `tests/test_opacity.py`

**Interfaces:**
- Consumes: none
- Produces:
  - `AppId` enum: `VSCODE|CURSOR|IDEA|PYCHARM`
  - `WallpaperState(app_id, image_path, opacity_ui, installed, last_error)`
  - `ui_to_background_cover(opacity_ui: int) -> float`
  - `background_cover_to_ui(opacity: float) -> int`
  - `clamp_ui(opacity_ui: int) -> int`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_opacity.py
from wallpaper_manager.core.opacity import (
    background_cover_to_ui,
    clamp_ui,
    ui_to_background_cover,
)


def test_ui_to_background_cover_maps_100_to_0_8():
    assert ui_to_background_cover(100) == 0.8


def test_ui_to_background_cover_maps_25():
    assert ui_to_background_cover(25) == 0.2


def test_background_cover_to_ui_roundtrip():
    assert background_cover_to_ui(0.2) == 25
    assert background_cover_to_ui(0.8) == 100


def test_clamp_ui():
    assert clamp_ui(-5) == 0
    assert clamp_ui(140) == 100
    assert clamp_ui(40) == 40
```

- [ ] **Step 2: Run tests — expect fail**

```bash
pytest tests/test_opacity.py -v
```

Expected: FAIL (module not found / import error)

- [ ] **Step 3: Implement**

`wallpaper_manager/core/__init__.py`: empty

`wallpaper_manager/core/models.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class AppId(str, Enum):
    VSCODE = "vscode"
    CURSOR = "cursor"
    IDEA = "idea"
    PYCHARM = "pycharm"


@dataclass
class WallpaperState:
    app_id: AppId
    image_path: str | None
    opacity_ui: int
    installed: bool
    last_error: str | None = None
```

`wallpaper_manager/core/opacity.py`:

```python
def clamp_ui(opacity_ui: int) -> int:
    return max(0, min(100, int(opacity_ui)))


def ui_to_background_cover(opacity_ui: int) -> float:
    return round(clamp_ui(opacity_ui) / 100 * 0.8, 4)


def background_cover_to_ui(opacity: float) -> int:
    if opacity <= 0:
        return 0
    return clamp_ui(round(float(opacity) / 0.8 * 100))
```

- [ ] **Step 4: Run tests — expect pass**

```bash
pytest tests/test_opacity.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add wallpaper_manager/core tests/test_opacity.py
git commit -m "feat: add models and opacity converters"
```

---

### Task 3: OS path detection

**Files:**
- Create: `wallpaper_manager/detect/__init__.py`
- Create: `wallpaper_manager/detect/paths.py`
- Test: `tests/test_paths.py`

**Interfaces:**
- Consumes: `AppId`
- Produces:
  - `vscode_settings_path(home: Path | None = None) -> Path`
  - `cursor_settings_path(home: Path | None = None) -> Path`
  - `jetbrains_support_root(home: Path | None = None) -> Path`
  - `find_jetbrains_other_xml(product_prefix: str, home: Path | None = None) -> Path | None`
    - `product_prefix` is `"IntelliJIdea"` or `"PyCharm"`
    - Returns newest matching `.../<prefix>*/options/other.xml` if any

- [ ] **Step 1: Write failing tests**

```python
# tests/test_paths.py
from pathlib import Path

from wallpaper_manager.detect.paths import (
    cursor_settings_path,
    find_jetbrains_other_xml,
    vscode_settings_path,
)


def test_vscode_settings_path_macos(monkeypatch, tmp_path: Path):
    monkeypatch.setattr("wallpaper_manager.detect.paths.sys.platform", "darwin")
    p = vscode_settings_path(tmp_path)
    assert p == tmp_path / "Library/Application Support/Code/User/settings.json"


def test_cursor_settings_path_windows(monkeypatch, tmp_path: Path):
    monkeypatch.setattr("wallpaper_manager.detect.paths.sys.platform", "win32")
    monkeypatch.setenv("APPDATA", str(tmp_path / "AppData/Roaming"))
    p = cursor_settings_path(tmp_path)
    assert p == tmp_path / "AppData/Roaming/Cursor/User/settings.json"


def test_find_jetbrains_prefers_newest(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("wallpaper_manager.detect.paths.sys.platform", "darwin")
    root = tmp_path / "Library/Application Support/JetBrains"
    older = root / "IntelliJIdea2024.3/options"
    newer = root / "IntelliJIdea2025.2/options"
    older.mkdir(parents=True)
    newer.mkdir(parents=True)
    (older / "other.xml").write_text("<app/>", encoding="utf-8")
    (newer / "other.xml").write_text("<app/>", encoding="utf-8")
    found = find_jetbrains_other_xml("IntelliJIdea", tmp_path)
    assert found == newer / "other.xml"
```

- [ ] **Step 2: Run — expect fail**

```bash
pytest tests/test_paths.py -v
```

- [ ] **Step 3: Implement `paths.py`**

```python
from __future__ import annotations

import os
import sys
from pathlib import Path


def _home(home: Path | None) -> Path:
    return home if home is not None else Path.home()


def vscode_settings_path(home: Path | None = None) -> Path:
    h = _home(home)
    if sys.platform == "darwin":
        return h / "Library/Application Support/Code/User/settings.json"
    if sys.platform == "win32":
        appdata = Path(os.environ.get("APPDATA", str(h / "AppData/Roaming")))
        return appdata / "Code/User/settings.json"
    raise RuntimeError(f"Unsupported platform: {sys.platform}")


def cursor_settings_path(home: Path | None = None) -> Path:
    h = _home(home)
    if sys.platform == "darwin":
        return h / "Library/Application Support/Cursor/User/settings.json"
    if sys.platform == "win32":
        appdata = Path(os.environ.get("APPDATA", str(h / "AppData/Roaming")))
        return appdata / "Cursor/User/settings.json"
    raise RuntimeError(f"Unsupported platform: {sys.platform}")


def jetbrains_support_root(home: Path | None = None) -> Path:
    h = _home(home)
    if sys.platform == "darwin":
        return h / "Library/Application Support/JetBrains"
    if sys.platform == "win32":
        appdata = Path(os.environ.get("APPDATA", str(h / "AppData/Roaming")))
        return appdata / "JetBrains"
    raise RuntimeError(f"Unsupported platform: {sys.platform}")


def find_jetbrains_other_xml(product_prefix: str, home: Path | None = None) -> Path | None:
    root = jetbrains_support_root(home)
    if not root.is_dir():
        return None
    candidates: list[Path] = []
    for child in root.iterdir():
        if child.is_dir() and child.name.startswith(product_prefix):
            other = child / "options" / "other.xml"
            if other.is_file():
                candidates.append(other)
    if not candidates:
        return None
    candidates.sort(key=lambda p: p.parent.parent.name, reverse=True)
    return candidates[0]
```

- [ ] **Step 4: Run — expect pass**

```bash
pytest tests/test_paths.py -v
```

- [ ] **Step 5: Commit**

```bash
git add wallpaper_manager/detect tests/test_paths.py
git commit -m "feat: add OS config path detection"
```

---

### Task 4: Local state store

**Files:**
- Create: `wallpaper_manager/core/state_store.py`
- Test: `tests/test_state_store.py`

**Interfaces:**
- Consumes: `AppId`
- Produces:
  - `StateStore(path: Path)`
  - `load() -> dict[AppId, dict]` mapping to `{image_path, opacity_ui}`
  - `save_app(app_id, image_path, opacity_ui) -> None`
  - `clear_app(app_id) -> None`
  - Default path: `Path.home() / ".wallpaper-manager" / "config.json"`

- [ ] **Step 1: Write failing tests**

```python
from pathlib import Path

from wallpaper_manager.core.models import AppId
from wallpaper_manager.core.state_store import StateStore


def test_roundtrip(tmp_path: Path):
    store = StateStore(tmp_path / "config.json")
    store.save_app(AppId.VSCODE, "/tmp/a.png", 35)
    data = store.load()
    assert data[AppId.VSCODE]["image_path"] == "/tmp/a.png"
    assert data[AppId.VSCODE]["opacity_ui"] == 35


def test_clear_app(tmp_path: Path):
    store = StateStore(tmp_path / "config.json")
    store.save_app(AppId.CURSOR, "/tmp/b.png", 20)
    store.clear_app(AppId.CURSOR)
    assert AppId.CURSOR not in store.load() or store.load()[AppId.CURSOR]["image_path"] is None
```

- [ ] **Step 2: Run — expect fail**

```bash
pytest tests/test_state_store.py -v
```

- [ ] **Step 3: Implement `state_store.py`**

Persist JSON shape from the design spec (`version: 1`, `apps: {...}`). Create parent dirs on save. Missing file → empty apps dict. `clear_app` sets that app entry to `{"image_path": null, "opacity_ui": 20}` or removes the key; pick **remove the key** and make the test assert `AppId.CURSOR not in store.load()`.

- [ ] **Step 4: Run — expect pass**

```bash
pytest tests/test_state_store.py -v
```

- [ ] **Step 5: Commit**

```bash
git add wallpaper_manager/core/state_store.py tests/test_state_store.py
git commit -m "feat: add local config state store"
```

---

### Task 5: Image validation service

**Files:**
- Create: `wallpaper_manager/core/image_service.py`
- Test: `tests/test_image_service.py`

**Interfaces:**
- Consumes: none
- Produces:
  - `IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}`
  - `validate_image_path(path: str) -> tuple[bool, str | None]` → `(ok, error_message)`
  - `is_supported_image(path: Path) -> bool`

- [ ] **Step 1: Write failing tests**

```python
from pathlib import Path

from wallpaper_manager.core.image_service import validate_image_path


def test_missing_file():
    ok, err = validate_image_path("/no/such/file.png")
    assert ok is False
    assert err


def test_valid_png(tmp_path: Path):
    # minimal PNG via Pillow in test setup
    from PIL import Image

    p = tmp_path / "a.png"
    Image.new("RGB", (8, 8), color=(10, 20, 30)).save(p)
    ok, err = validate_image_path(str(p))
    assert ok is True
    assert err is None


def test_reject_txt(tmp_path: Path):
    p = tmp_path / "a.txt"
    p.write_text("hi", encoding="utf-8")
    ok, err = validate_image_path(str(p))
    assert ok is False
```

- [ ] **Step 2: Run — expect fail**

```bash
pytest tests/test_image_service.py -v
```

- [ ] **Step 3: Implement**

Expand user/`~`, resolve path, require file exists, require suffix in `IMAGE_EXTENSIONS`, optionally open with Pillow to confirm decodable. Return Chinese error strings suitable for UI (`文件不存在`, `不支持的图片格式`, `无法读取图片`).

- [ ] **Step 4: Run — expect pass**

```bash
pytest tests/test_image_service.py -v
```

- [ ] **Step 5: Commit**

```bash
git add wallpaper_manager/core/image_service.py tests/test_image_service.py
git commit -m "feat: add image path validation"
```

---

### Task 6: settings.json helper + VS Code / Cursor adapters

**Files:**
- Create: `wallpaper_manager/adapters/__init__.py`
- Create: `wallpaper_manager/adapters/base.py`
- Create: `wallpaper_manager/adapters/settings_json.py`
- Create: `wallpaper_manager/adapters/vscode.py`
- Create: `wallpaper_manager/adapters/cursor.py`
- Test: `tests/test_settings_json.py`

**Interfaces:**
- Consumes: `AppId`, opacity converters, path helpers
- Produces:
  - `WallpaperAdapter` Protocol with `app_id`, `detect()`, `read() -> tuple[str | None, int]`, `apply(image_path, opacity_ui)`, `clear()`, and `extension_installed() -> bool` (optional helper on electron adapters)
  - `read_background_cover(settings_path: Path) -> tuple[str | None, int]`
  - `write_background_cover(settings_path: Path, image_path: str, opacity_ui: int) -> None`
  - `clear_background_cover(settings_path: Path) -> None`
  - `VsCodeAdapter(settings_path: Path | None = None)`
  - `CursorAdapter(settings_path: Path | None = None)`

- [ ] **Step 1: Write failing tests**

```python
import json
from pathlib import Path

from wallpaper_manager.adapters.settings_json import (
    clear_background_cover,
    read_background_cover,
    write_background_cover,
)
from wallpaper_manager.adapters.vscode import VsCodeAdapter


def test_write_preserves_other_keys(tmp_path: Path):
    settings = tmp_path / "settings.json"
    settings.write_text(json.dumps({"editor.fontSize": 20}), encoding="utf-8")
    write_background_cover(settings, "/tmp/w.png", 25)
    data = json.loads(settings.read_text(encoding="utf-8"))
    assert data["editor.fontSize"] == 20
    assert data["backgroundCover.imagePath"] == "/tmp/w.png"
    assert data["backgroundCover.opacity"] == 0.2


def test_read_and_clear(tmp_path: Path):
    settings = tmp_path / "settings.json"
    write_background_cover(settings, "/tmp/w.png", 50)
    path, ui = read_background_cover(settings)
    assert path == "/tmp/w.png"
    assert ui == 50
    clear_background_cover(settings)
    path2, ui2 = read_background_cover(settings)
    assert path2 is None


def test_vscode_detect(tmp_path: Path):
    settings = tmp_path / "User" / "settings.json"
    settings.parent.mkdir(parents=True)
    settings.write_text("{}", encoding="utf-8")
    adapter = VsCodeAdapter(settings_path=settings)
    assert adapter.detect() is True
```

- [ ] **Step 2: Run — expect fail**

```bash
pytest tests/test_settings_json.py -v
```

- [ ] **Step 3: Implement**

`base.py` — Protocol only.

`settings_json.py` — load/dump UTF-8 JSON; create file if missing on write; set/remove the two keys; use opacity converters.

`vscode.py` / `cursor.py` — thin wrappers around path defaults + `settings_json` helpers. `detect()` = settings path exists (file or parent User dir with ability to create — **spec:** settings path exists; for detect use `settings_path.is_file()` OR parent exists). Prefer: `detect()` true if `settings_path.parent.is_dir()` (User folder present). `extension_installed()` glob `manasxx.background-cover*` under `~/.vscode/extensions` or `~/.cursor/extensions`.

- [ ] **Step 4: Run — expect pass**

```bash
pytest tests/test_settings_json.py -v
```

- [ ] **Step 5: Commit**

```bash
git add wallpaper_manager/adapters tests/test_settings_json.py
git commit -m "feat: add background-cover settings adapters"
```

---

### Task 7: JetBrains adapter

**Files:**
- Create: `wallpaper_manager/adapters/jetbrains.py`
- Test: `tests/test_jetbrains.py`

**Interfaces:**
- Consumes: `find_jetbrains_other_xml`, `AppId`, `clamp_ui`
- Produces:
  - `encode_background_value(path: str, opacity_ui: int) -> str` → `path,{opacity},scale,center`
  - `decode_background_value(value: str) -> tuple[str | None, int]`
  - `JetBrainsAdapter(app_id: AppId, other_xml: Path | None = None, product_prefix: str | None = None)`
  - For IDEA: prefix `IntelliJIdea`; PyCharm: `PyCharm`
  - `read`/`apply`/`clear` mutate property `idea.background.editor` inside `other.xml` component `PropertiesComponent` (match real file structure on machine)

**Real file shape note (from local scan):** JetBrains stores keys in `options/other.xml` under a map/properties structure. Before implementing, open one real `other.xml` on the machine and mirror its element structure in the writer. If the file uses:

```xml
<application>
  <component name="PropertiesComponent">
    <property name="idea.background.editor" value="..." />
  </component>
</application>
```

or a JSON blob inside — **match whatever is actually present**. Tests should use a minimal fixture copied from the real schema.

- [ ] **Step 1: Inspect real schema once, then write fixture + failing tests**

```bash
# inspect (do not commit secrets/paths unnecessarily)
python3 - <<'PY'
from pathlib import Path
p = Path.home()/"Library/Application Support/JetBrains/PyCharm2025.2/options/other.xml"
print(p.read_text(encoding="utf-8")[:1500])
PY
```

Then write `tests/test_jetbrains.py` with encode/decode unit tests and apply/read/clear against a temp `other.xml` fixture matching that schema.

```python
from wallpaper_manager.adapters.jetbrains import (
    decode_background_value,
    encode_background_value,
)


def test_encode_decode():
    raw = encode_background_value("/tmp/a.png", 35)
    assert raw == "/tmp/a.png,35,scale,center"
    path, ui = decode_background_value(raw)
    assert path == "/tmp/a.png"
    assert ui == 35
```

Plus adapter apply/read/clear tests on tmp fixture.

- [ ] **Step 2: Run — expect fail**

```bash
pytest tests/test_jetbrains.py -v
```

- [ ] **Step 3: Implement `jetbrains.py`**

- Preserve unrelated properties
- `clear()` removes `idea.background.editor` only
- `detect()` true when resolved `other.xml` exists
- Factory helpers: `IdeaAdapter()`, `PyCharmAdapter()` as thin constructors if useful

- [ ] **Step 4: Run — expect pass**

```bash
pytest tests/test_jetbrains.py -v
```

- [ ] **Step 5: Commit**

```bash
git add wallpaper_manager/adapters/jetbrains.py tests/test_jetbrains.py
git commit -m "feat: add JetBrains wallpaper adapter"
```

---

### Task 8: WallpaperService orchestration

**Files:**
- Create: `wallpaper_manager/core/service.py`
- Test: `tests/test_service.py`

**Interfaces:**
- Consumes: all adapters, `StateStore`, `validate_image_path`
- Produces:
  - `WallpaperService(adapters: list[WallpaperAdapter], store: StateStore | None = None)`
  - `bootstrap() -> dict[AppId, WallpaperState]` — detect, read adapter (wins), else store
  - `apply(app_id, image_path, opacity_ui) -> WallpaperState` — validate, adapter.apply, store.save_app; on failure set `last_error`
  - `clear(app_id) -> WallpaperState`
  - `extension_tip(app_id) -> str | None` — for vscode/cursor if extension missing

- [ ] **Step 1: Write failing tests with fake adapters**

```python
from wallpaper_manager.core.models import AppId, WallpaperState
from wallpaper_manager.core.service import WallpaperService
from wallpaper_manager.core.state_store import StateStore


class FakeAdapter:
    def __init__(self, app_id: AppId, installed: bool = True):
        self.app_id = app_id
        self._installed = installed
        self.path = None
        self.opacity = 20
        self.applied = []

    def detect(self) -> bool:
        return self._installed

    def read(self):
        return self.path, self.opacity

    def apply(self, image_path: str, opacity_ui: int) -> None:
        self.path = image_path
        self.opacity = opacity_ui
        self.applied.append((image_path, opacity_ui))

    def clear(self) -> None:
        self.path = None


def test_apply_and_bootstrap(tmp_path):
    fake = FakeAdapter(AppId.VSCODE)
    svc = WallpaperService([fake], store=StateStore(tmp_path / "c.json"))
    # create tiny png
    from PIL import Image

    img = tmp_path / "w.png"
    Image.new("RGB", (4, 4)).save(img)
    state = svc.apply(AppId.VSCODE, str(img), 40)
    assert state.last_error is None
    assert fake.applied[-1] == (str(img), 40)
    states = svc.bootstrap()
    assert states[AppId.VSCODE].image_path == str(img)
```

- [ ] **Step 2: Run — expect fail**

```bash
pytest tests/test_service.py -v
```

- [ ] **Step 3: Implement `service.py`**

Wire real adapter list in a `build_default_service()` helper used by UI later.

- [ ] **Step 4: Run full unit suite**

```bash
pytest -v
```

Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add wallpaper_manager/core/service.py tests/test_service.py
git commit -m "feat: add wallpaper orchestration service"
```

---

### Task 9: Flet UI — Midnight Glass shell + wiring

**Files:**
- Create: `wallpaper_manager/ui/__init__.py`
- Create: `wallpaper_manager/ui/theme.py`
- Create: `wallpaper_manager/ui/app.py`
- Modify: `wallpaper_manager/__main__.py`

**Interfaces:**
- Consumes: `WallpaperService`, `AppId`, `validate_image_path`
- Produces: `main()` launches Flet desktop window

**UI requirements (implement exactly):**
- Title: `Wallpaper Manager` + subtitle with detected count (`检测到 N 个软件`)
- Tabs for four apps; uninstalled tabs show `未安装` and disable Apply
- Large preview (`ft.Image` or container background) + dark overlay opacity tied to slider
- Path `TextField` + Browse (`ft.FilePicker`)
- Opacity `Slider` 0–100 with live label
- Buttons: `清除`, `应用到 {name}`
- Success snack: mention reload/restart hint (VS Code/Cursor vs JetBrains)
- Theme colors from Midnight Glass; accent `#38bdf8`
- Tab switch does not apply; only button does

- [ ] **Step 1: Implement `theme.py` constants**

```python
BG = "#0b0d12"
PANEL = "#141a22"
ACCENT = "#38bdf8"
ACCENT_2 = "#22d3ee"
TEXT = "#eef2f7"
MUTED = "#8b95a8"
```

- [ ] **Step 2: Implement `app.py`**

Build page layout; keep per-tab draft state in a `dict[AppId, ...]` while editing; on tab change load that draft into controls; on path/slider change update preview; Apply/Clear call service and show snackbar.

Keep file focused: if `app.py` grows past ~300 lines, split `components.py` for preview/path row — only if needed.

- [ ] **Step 3: Wire `__main__.py`**

```python
def main() -> None:
    from wallpaper_manager.ui.app import run_app

    run_app()
```

- [ ] **Step 4: Manual smoke run**

```bash
source .venv/bin/activate
python -m wallpaper_manager
```

Expected: window opens with 4 tabs, preview updates when picking a local image, Apply writes real configs on this Mac.

Manual checks:
1. VS Code / Cursor `settings.json` get `backgroundCover.imagePath` + `opacity`
2. IDEA / PyCharm `other.xml` `idea.background.editor` updates
3. Invalid path disables Apply and shows error in preview area
4. Uninstall simulation not required if all four detected

- [ ] **Step 5: Commit**

```bash
git add wallpaper_manager/ui wallpaper_manager/__main__.py
git commit -m "feat: add Midnight Glass Flet UI"
```

---

### Task 10: README polish + final verification

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Document**

- Install / run / test commands  
- Note about Background Cover extension  
- Note JetBrains may need restart  
- Supported apps and platforms  

- [ ] **Step 2: Run full tests**

```bash
pytest -v
```

Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: finalize README for v1"
```

---

## Spec coverage checklist

| Spec item | Task |
|-----------|------|
| Per-app path + opacity | 8, 9 |
| Browse + paste + preview | 5, 9 |
| VS Code/Cursor background-cover | 6 |
| JetBrains other.xml | 7 |
| macOS + Windows paths | 3 |
| Local config.json | 4 |
| Opacity mapping | 2 |
| Midnight Glass + Layout C | 9 |
| Error handling / tips | 8, 9 |
| Out-of-scope excluded | Global Constraints |

## Self-review notes

- No TBD placeholders left in tasks  
- Adapter Protocol signatures consistent across Tasks 6–8  
- Opacity helpers named `ui_to_background_cover` / `background_cover_to_ui` everywhere  
- JetBrains task requires one live schema inspect before coding writer (explicit step)
