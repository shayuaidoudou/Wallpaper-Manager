"""Per-app config file snapshots under ~/.wallpaper-manager/backups/."""

from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

from wallpaper_manager.core.models import AppId

DEFAULT_BACKUP_ROOT = Path.home() / ".wallpaper-manager" / "backups"
KEEP_PER_APP = 5


class ConfigBackupStore:
    def __init__(self, root: Path | None = None) -> None:
        self._root = root if root is not None else DEFAULT_BACKUP_ROOT

    def backup_file(self, app_id: AppId, source: Path) -> Path | None:
        """Copy ``source`` into the app backup folder. Returns backup path or None."""
        if not source.is_file():
            return None
        app_dir = self._root / app_id.value
        app_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        dest = app_dir / f"{stamp}_{source.name}"
        # Same-second collisions: append a counter.
        if dest.exists():
            n = 1
            while True:
                candidate = app_dir / f"{stamp}_{n}_{source.name}"
                if not candidate.exists():
                    dest = candidate
                    break
                n += 1
        shutil.copy2(source, dest)
        self._prune(app_dir)
        return dest

    def list_backups(self, app_id: AppId) -> list[Path]:
        app_dir = self._root / app_id.value
        if not app_dir.is_dir():
            return []
        files = [p for p in app_dir.iterdir() if p.is_file()]
        files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        return files

    def latest(self, app_id: AppId) -> Path | None:
        items = self.list_backups(app_id)
        return items[0] if items else None

    def restore_to(self, app_id: AppId, target: Path) -> Path:
        """Restore the latest backup over ``target``. Raises if no backup."""
        latest = self.latest(app_id)
        if latest is None:
            raise FileNotFoundError(f"没有可用的备份: {app_id.value}")
        target = target.expanduser()
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(latest, target)
        return latest

    def _prune(self, app_dir: Path) -> None:
        files = [p for p in app_dir.iterdir() if p.is_file()]
        files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        for stale in files[KEEP_PER_APP:]:
            try:
                stale.unlink()
            except OSError:
                pass
