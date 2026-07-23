# Wallpaper Manager

Unified wallpaper manager for VS Code, Cursor, IDEA, and PyCharm.

## Setup

Requires **Python 3.11+** (system `python3` on macOS is often 3.9).

```bash
python3.11 -m venv .venv   # any Python 3.11+ interpreter works
source .venv/bin/activate
pip install -e ".[dev]"
```

## Run

```bash
python -m wallpaper_manager
```

Expected output: `Wallpaper Manager scaffold OK`

## Tests

```bash
pytest
```
