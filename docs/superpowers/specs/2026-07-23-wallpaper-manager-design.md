# Wallpaper Manager — Design Spec

**Date:** 2026-07-23  
**Status:** Draft for review  
**Stack:** Python + Flet (desktop)

## 1. Goal

A local desktop app that manages editor/IDE wallpapers in one place. Each supported app has its own image and opacity; the user picks a file or pastes a path, previews it, then applies.

**v1 targets**
- Platforms: macOS + Windows
- Apps: VS Code, Cursor, IntelliJ IDEA, PyCharm
- Controls: image path (browse + paste), opacity, live preview, apply/clear
- UI: top IDE tabs + large preview; “Midnight Glass” visual theme

**Out of scope for v1**
- Blur / brightness
- Random folder rotation / online galleries
- Syncing one image to all apps in one click
- WebStorm (easy follow-up; same JetBrains adapter)
- Cloud sync / accounts

## 2. User experience

### 2.1 Layout (Layout C)

1. Title bar: app name + detected-app count  
2. Top tabs: VS Code | Cursor | IDEA | PyCharm  
3. Large preview of the selected image with opacity overlay  
4. Path field + “Browse…”  
5. Opacity slider (UI: 0–100%)  
6. Actions: Clear | Apply to current app

### 2.2 Interaction rules

- Switching tabs changes the editing target only; it does **not** write IDE config until Apply  
- Path change (browse or paste + confirm/load) refreshes preview immediately  
- Opacity drag updates the preview overlay in real time  
- Apply writes only the active app’s config  
- Clear removes this app’s wallpaper setting in the IDE config (VS Code/Cursor: clear `backgroundCover.imagePath` / related opacity; JetBrains: remove `idea.background.editor`) and clears local remembered state for that app

### 2.3 Visual theme — Midnight Glass

- Deep space background with subtle radial cool highlight  
- Semi-transparent panels / glass-like surfaces  
- Accent: cyan–sky (`#22d3ee` / `#38bdf8`)  
- Motion: tab cross-fade, preview fade-in, apply success micro-feedback  
- Avoid purple-glow “AI default” styling; keep effects restrained

## 3. Architecture

```
ui/ (Flet)
  └── pages + theme + animations
core/
  ├── models.py          # AppId, WallpaperState
  ├── state_store.py     # ~/.wallpaper-manager/config.json
  ├── image_service.py   # validate path, load preview bytes
  └── opacity.py         # UI% ↔ target formats
adapters/
  ├── base.py            # detect / read / apply / clear
  ├── vscode.py          # VS Code + shared Electron settings helper
  ├── cursor.py          # Cursor (same background-cover keys)
  └── jetbrains.py       # IDEA / PyCharm via other.xml
detect/
  └── paths.py           # OS-specific config path resolution
```

UI never touches IDE files directly. All writes go through adapters.

## 4. Domain model

```python
class AppId(str, Enum):
    VSCODE = "vscode"
    CURSOR = "cursor"
    IDEA = "idea"
    PYCHARM = "pycharm"

@dataclass
class WallpaperState:
    app_id: AppId
    image_path: str | None
    opacity_ui: int          # 0–100
    installed: bool
    last_error: str | None
```

App-owned persistence (`~/.wallpaper-manager/config.json`):

```json
{
  "version": 1,
  "apps": {
    "vscode": { "image_path": "...", "opacity_ui": 35 },
    "cursor": { "image_path": "...", "opacity_ui": 35 },
    "idea": { "image_path": "...", "opacity_ui": 25 },
    "pycharm": { "image_path": "...", "opacity_ui": 35 }
  }
}
```

On launch: detect installs → read each adapter’s current wallpaper when possible → merge with local store (adapter values win if present).

## 5. Adapters (based on local scan 2026-07-23)

### 5.1 VS Code / Cursor — extension `background-cover` (`manasxx.background-cover`)

**Config files**
- macOS VS Code: `~/Library/Application Support/Code/User/settings.json`
- macOS Cursor: `~/Library/Application Support/Cursor/User/settings.json`
- Windows VS Code: `%APPDATA%\Code\User\settings.json`
- Windows Cursor: `%APPDATA%\Cursor\User\settings.json`

**Keys written**
| Key | Meaning |
|-----|---------|
| `backgroundCover.imagePath` | Absolute image path |
| `backgroundCover.opacity` | Float **0–0.8** |

**Opacity mapping**
- UI `opacity_ui` (0–100) → `backgroundCover.opacity = clamp(opacity_ui / 100 * 0.8, 0, 0.8)`
- Read back → `opacity_ui = round(opacity / 0.8 * 100)`

**Detect**
- Settings path exists  
- Prefer also checking that the extension folder exists (`~/.vscode/extensions` / `~/.cursor/extensions` matching `manasxx.background-cover*`). If settings exist but extension missing, still allow write but surface a non-blocking tip to install Background Cover.

**Apply notes**
- Preserve other keys in `settings.json`  
- Handle JSONC lightly if needed (user files observed as plain JSON)  
- After write, user may need to reload window / use extension command for CSS inject; show short hint in success toast

### 5.2 IntelliJ IDEA / PyCharm — built-in background image

**Config files (versioned product dirs)**
- macOS IDEA example: `~/Library/Application Support/JetBrains/IntelliJIdea2025.2/options/other.xml`
- macOS PyCharm example: `~/Library/Application Support/JetBrains/PyCharm2025.2/options/other.xml`
- Windows: `%APPDATA%\JetBrains\<ProductYYYY.N>\options\other.xml`

**Detection rule**
- Scan `JetBrains` support root for directories matching:
  - IDEA: `IntelliJIdea*`
  - PyCharm: `PyCharm*`
- Prefer the newest version directory that contains `options/other.xml` (or create `other.xml` structure if missing but product dir exists)

**Property**
- Key: `idea.background.editor`
- Value format observed locally:

```text
<absolute-path>,<opacity-int>,scale,center
```

Examples from this machine:
- IDEA: `…/日落时分的城市列车之旅.png,25,scale,center`
- PyCharm: `…/上班快乐_TomJerry.png,35,scale,center`

**Opacity mapping**
- UI 0–100 → integer in the CSV (same number)  
- Fill mode fixed to `scale`, position fixed to `center` in v1

**Apply notes**
- Parse/update the property inside `other.xml` without destroying unrelated properties  
- IDE may need restart or reopen for background refresh; mention in success tip  
- Also update `BackgroundImageDialog#recent` list is optional (skip in v1)

### 5.3 Adapter interface

```python
class WallpaperAdapter(Protocol):
    app_id: AppId
    def detect(self) -> bool: ...
    def read(self) -> tuple[str | None, int]: ...  # path, opacity_ui
    def apply(self, image_path: str, opacity_ui: int) -> None: ...
    def clear(self) -> None: ...
```

## 6. Image input & preview

- Browse: native file picker; filter common image types (`png`, `jpg`, `jpeg`, `webp`, `gif`, `bmp`)  
- Paste path: text field; on change/blur/Enter, validate and load  
- Validation failures (missing file, not an image): show message in preview area; disable Apply  
- Preview: decode with Pillow (or Flet image src for local file); overlay a dimming layer driven by opacity so the preview matches perceived strength as closely as practical  
- No network fetches in v1

## 7. Error handling

| Case | Behavior |
|------|----------|
| App not installed | Tab shows “未安装”; Apply disabled |
| Invalid path | Preview error; Apply disabled |
| Write permission / parse failure | Banner/toast with reason; form state kept |
| background-cover missing | Apply still writes settings; tip to install extension |
| JetBrains version dir ambiguous | Use newest matching product dir; log choice |

No silent failures: every Apply returns success or a readable error.

## 8. Packaging & run

- Dev: `python -m wallpaper_manager` (or `flet run`)  
- Deps: `flet`, `pillow`; stdlib for JSON/XML/pathlib  
- Later: `flet pack` / platform installers (not required to finish v1 logic)

## 9. Testing strategy

- Unit: opacity converters; JetBrains value encode/decode; settings.json merge  
- Adapter fixtures: temp dirs mimicking macOS/Windows layout  
- Manual: apply to each installed app on this Mac; verify reload/restart behavior

## 10. Future (explicitly later)

- WebStorm / other JetBrains products via same adapter  
- Optional blur for background-cover  
- Gallery folder browser  
- One-click “apply current image to selected apps”

## 11. Decisions locked

| Topic | Decision |
|-------|----------|
| Language / UI | Python + Flet |
| Per-app wallpapers | Yes (no forced global sync) |
| Platforms | macOS + Windows |
| v1 apps | VS Code, Cursor, IDEA, PyCharm |
| VS Code/Cursor mechanism | `background-cover` settings keys |
| JetBrains mechanism | `idea.background.editor` in `other.xml` |
| Layout | Top tabs + large preview |
| Theme | Midnight Glass |
| Opacity UI | 0–100%, mapped per adapter |
