# Reliability + Multi-App Sync + Backup (v0.3.0)

## Goal

Ship a focused reliability and power-user release, then rebuild the macOS app, drop obsolete local release artifacts, and push to GitHub.

## Scope (locked)

In:

1. **Precheck** before apply (image, config path, extension tip, detect).
2. **Read-back verify** after successful apply.
3. **Diagnostics** summary for settings (per-app path/exists/extension).
4. **Multi-app sync** — apply the same image+opacity to selected installed apps.
5. **Config backup/restore** — snapshot target config file before write; restore last backup.
6. Docs touch-up (SECURITY version line), version **0.3.0**, pack macOS app, delete older `release/*.zip`, push.

Out:

- Full `app.py` split refactor.
- Local folder gallery watcher, import/export profiles, scheduled rotation, Windows packaging.

## Architecture

All new behavior lives in `WallpaperService` (+ small helpers). Adapters unchanged except using existing `effective_config_path` / `read` / `apply`.

```
UI  →  WallpaperService.precheck / apply / apply_many / diagnose / backup / restore
            │
            ├─ adapters (write configs)
            ├─ StateStore (app state, history)
            └─ ConfigBackupStore (~/.wallpaper-manager/backups/)
```

### Precheck

`precheck(app_id, image_path) -> PrecheckResult`:

- image path valid (reuse `validate_image_path`)
- adapter present; `detect()`; effective path parent usable
- optional `extension_tip` for VS Code / Cursor (warning, not hard fail)

Hard fail blocks apply. Warnings surface in toast / diagnostics.

### Apply + verify

`apply(...)` keeps current signature. Internally:

1. precheck (hard errors → `WallpaperState.last_error`)
2. backup effective config file if it exists
3. `adapter.apply`
4. `store.save_app` + history
5. `adapter.read` compare path + opacity → soft warning on mismatch via optional `verify_note` on state or separate field

Add optional `WallpaperState.verify_warning: str | None = None` (default None) so UI can append “已写入，但回读不一致…”.

### Multi-app

`apply_many(app_ids, image_path, opacity_ui, history_entry=None) -> dict[AppId, WallpaperState]`

- sequential apply (safe, simple)
- each app independent backup + history
- UI: “同步到其他已安装应用” checkbox; apply uses active draft targets = active ∪ others if checked (only `detect()` true)

### Backup / restore

`ConfigBackupStore` under `~/.wallpaper-manager/backups/{app_id}/`:

- files: `{timestamp}_{filename}` copy of config
- keep last **5** per app
- `restore_latest(app_id)` copies latest backup over effective path; does not re-run adapter clear/apply semantics beyond file restore + bootstrap refresh

Expose on service: `backup_config`, `list_backups`, `restore_latest_backup`.

### Diagnostics

`diagnose() -> list[AppDiagnostic]`:

- app_id, label, installed, path, exists, extension_ok (or N/A), last stored image

Settings panel: read-only block listing these lines + “恢复最近备份” per app that has backups.

## UI (minimal)

- Main: checkbox under apply row — “同步到其他已安装应用”
- Settings: Diagnostics section + restore buttons
- Toast: include verify warning / multi-app summary (“3 成功 / 1 失败”)

No theme redesign.

## Testing

- unit: precheck fail paths, backup rotate, apply verifies read-back, apply_many partial failure
- existing FakeAdapter extended with optional path for backup tests (temp files)

## Release

1. `pyproject.toml` → `0.3.0`
2. `pytest -v`
3. `./scripts/pack_macos.sh 0.3.0`
4. Remove older `release/Wallpaper-Manager-0.*.zip` (+ `.sha256`) keep only `0.3.0`
5. Commit on current branch, `git push` to `origin`

## Success criteria

- [ ] Precheck blocks bad image / missing adapter path with clear Chinese error
- [ ] Apply creates a backup when config file exists
- [ ] Multi-app checkbox applies to other detected apps
- [ ] Settings shows diagnostics + restore latest
- [ ] Tests green; `release/Wallpaper-Manager-0.3.0-macos-arm64.zip` exists; old zips gone; remote updated
