from pathlib import Path

from wallpaper_manager.core.config_backup import ConfigBackupStore, KEEP_PER_APP
from wallpaper_manager.core.models import AppId


def test_backup_and_restore_roundtrip(tmp_path: Path):
    store = ConfigBackupStore(tmp_path / "backups")
    source = tmp_path / "settings.json"
    source.write_text('{"a": 1}\n', encoding="utf-8")

    backup = store.backup_file(AppId.VSCODE, source)
    assert backup is not None
    assert backup.is_file()

    source.write_text('{"a": 2}\n', encoding="utf-8")
    restored = store.restore_to(AppId.VSCODE, source)
    assert restored == backup
    assert source.read_text(encoding="utf-8") == '{"a": 1}\n'


def test_backup_skips_missing_source(tmp_path: Path):
    store = ConfigBackupStore(tmp_path / "backups")
    assert store.backup_file(AppId.VSCODE, tmp_path / "missing.json") is None


def test_backup_prunes_to_keep_limit(tmp_path: Path):
    store = ConfigBackupStore(tmp_path / "backups")
    source = tmp_path / "other.xml"
    for i in range(KEEP_PER_APP + 3):
        source.write_text(f"v{i}\n", encoding="utf-8")
        # Distinct mtime via content change + explicit touch sequence
        store.backup_file(AppId.IDEA, source)

    backups = store.list_backups(AppId.IDEA)
    assert len(backups) == KEEP_PER_APP


def test_restore_without_backup_raises(tmp_path: Path):
    store = ConfigBackupStore(tmp_path / "backups")
    try:
        store.restore_to(AppId.GHOSTTY, tmp_path / "config")
        raised = False
    except FileNotFoundError:
        raised = True
    assert raised
