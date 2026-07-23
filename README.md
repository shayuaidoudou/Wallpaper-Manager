# Wallpaper Manager

Unified desktop wallpaper manager for **VS Code**, **Cursor**, **IntelliJ IDEA**, and **PyCharm** on **macOS** and **Windows**.

Pick an image, adjust opacity, and apply per app. Settings are written to each IDE’s native config; local state is stored in `~/.wallpaper-manager/config.json`.

## Supported apps & platforms

| App | macOS | Windows |
|-----|-------|---------|
| VS Code | ✓ | ✓ |
| Cursor | ✓ | ✓ |
| IntelliJ IDEA | ✓ | ✓ |
| PyCharm | ✓ | ✓ |

## Requirements

- **Python 3.11+** (system `python3` on macOS is often 3.9 — use `python3.11` or newer)
- **VS Code / Cursor:** the [Background Cover](https://marketplace.visualstudio.com/items?itemName=manasxx.background-cover) extension (`manasxx.background-cover`) must be installed for wallpapers to render. Wallpaper Manager can still write settings without it, but you will see a tip to install the extension.
- **JetBrains (IDEA / PyCharm):** after applying, you may need to **restart the IDE** for the background to appear.

## Install

```bash
python3.11 -m venv .venv   # any Python 3.11+ interpreter works
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

## Run

```bash
python -m wallpaper_manager
```

This opens the Flet desktop UI. Choose an app tab, browse or paste an image path, set opacity, then **Apply**. Use **Clear** to remove the wallpaper for the selected app.

## Tests

```bash
pytest -v
```

Or with the project venv:

```bash
.venv/bin/pytest -v        # Windows: .venv\Scripts\pytest -v
```
