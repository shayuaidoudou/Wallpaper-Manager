# Final Review Fix Report

Date: 2026-07-23
Branch: `feature/wallpaper-manager-v1`

## Fix notes

1. JSONC settings support
   - Added a string-aware JSONC preprocessor for `//` comments, `/* ... */`
     comments, and trailing commas.
   - Comment-like text inside JSON strings is preserved.
   - Existing settings keys remain in the parsed dictionary and survive writes.
   - As accepted for v1, writing a file originally containing JSONC normalizes it
     to pretty-printed standard JSON and removes comments.

2. JetBrains detection without `other.xml`
   - Product directories now participate in discovery even before
     `options/other.xml` exists.
   - Discovery returns the prospective `options/other.xml` path for the newest
     matching product.
   - Version ordering is numeric, so `2025.10` sorts after `2025.9`.
   - Adapter detection treats an existing product directory as installed.
   - Apply and clear create `options/` and a minimal `PropertyService` document
     when `other.xml` is absent.

3. Bootstrap store fallback
   - An installed adapter still wins when it reports a wallpaper path.
   - If it reports no path, bootstrap uses a stored path and stored opacity when
     available while retaining `installed=True`.

## Targeted test output

Command:

```text
.venv/bin/pytest -v tests/test_settings_json.py tests/test_paths.py tests/test_jetbrains.py tests/test_service.py
```

Output:

```text
============================= test session starts ==============================
platform darwin -- Python 3.11.15, pytest-9.1.1, pluggy-1.6.0 -- /Users/cuitian/ShayuApp/Wallpaper-Manager/.venv/bin/python3
cachedir: .pytest_cache
rootdir: /Users/cuitian/ShayuApp/Wallpaper-Manager
configfile: pyproject.toml
plugins: anyio-4.14.2, flet-0.86.2
collecting ... collected 23 items

tests/test_settings_json.py::test_write_preserves_other_keys PASSED      [  4%]
tests/test_settings_json.py::test_commented_jsonc_reads_writes_and_preserves_other_keys PASSED [  8%]
tests/test_settings_json.py::test_read_and_clear PASSED                  [ 13%]
tests/test_settings_json.py::test_vscode_detect PASSED                   [ 17%]
tests/test_paths.py::test_vscode_settings_path_macos PASSED              [ 21%]
tests/test_paths.py::test_cursor_settings_path_windows PASSED            [ 26%]
tests/test_paths.py::test_find_jetbrains_prefers_newest PASSED           [ 30%]
tests/test_paths.py::test_find_jetbrains_returns_prospective_path_when_other_xml_missing PASSED [ 34%]
tests/test_jetbrains.py::test_encode_decode PASSED                       [ 39%]
tests/test_jetbrains.py::test_decode_malformed_value_returns_empty_state PASSED [ 43%]
tests/test_jetbrains.py::test_apply_read_and_clear_preserve_json_and_xml_components PASSED [ 47%]
tests/test_jetbrains.py::test_detect_and_apply_when_product_exists_without_other_xml PASSED [ 52%]
tests/test_jetbrains.py::test_clear_creates_minimal_other_xml_for_existing_product PASSED [ 56%]
tests/test_jetbrains.py::test_product_factories_use_expected_ids PASSED  [ 60%]
tests/test_service.py::test_apply_and_bootstrap_reads_adapter_state PASSED [ 65%]
tests/test_service.py::test_bootstrap_uses_store_when_adapter_is_not_detected PASSED [ 69%]
tests/test_service.py::test_bootstrap_preserves_store_opacity_zero_from_store_fallback PASSED [ 73%]
tests/test_service.py::test_bootstrap_adapter_state_wins_over_store PASSED [ 78%]
tests/test_service.py::test_bootstrap_uses_store_when_installed_adapter_has_no_wallpaper PASSED [ 82%]
tests/test_service.py::test_apply_failure_returns_error_without_saving PASSED [ 86%]
tests/test_service.py::test_clear_clears_adapter_and_store PASSED        [ 91%]
tests/test_service.py::test_extension_tip_only_reports_missing_editor_extensions PASSED [ 95%]
tests/test_service.py::test_build_default_service_wires_all_real_adapters PASSED [100%]

============================== 23 passed in 0.12s ==============================
```

## Full-suite test output

Command:

```text
.venv/bin/pytest -v
```

Output:

```text
============================= test session starts ==============================
platform darwin -- Python 3.11.15, pytest-9.1.1, pluggy-1.6.0 -- /Users/cuitian/ShayuApp/Wallpaper-Manager/.venv/bin/python3
cachedir: .pytest_cache
rootdir: /Users/cuitian/ShayuApp/Wallpaper-Manager
configfile: pyproject.toml
testpaths: tests
plugins: anyio-4.14.2, flet-0.86.2
collecting ... collected 37 items

tests/test_image_service.py::test_missing_file PASSED                    [  2%]
tests/test_image_service.py::test_valid_png PASSED                       [  5%]
tests/test_image_service.py::test_reject_txt PASSED                      [  8%]
tests/test_image_service.py::test_reject_corrupt_png PASSED              [ 10%]
tests/test_jetbrains.py::test_encode_decode PASSED                       [ 13%]
tests/test_jetbrains.py::test_decode_malformed_value_returns_empty_state PASSED [ 16%]
tests/test_jetbrains.py::test_apply_read_and_clear_preserve_json_and_xml_components PASSED [ 18%]
tests/test_jetbrains.py::test_detect_and_apply_when_product_exists_without_other_xml PASSED [ 21%]
tests/test_jetbrains.py::test_clear_creates_minimal_other_xml_for_existing_product PASSED [ 24%]
tests/test_jetbrains.py::test_product_factories_use_expected_ids PASSED  [ 27%]
tests/test_opacity.py::test_ui_to_background_cover_maps_100_to_0_8 PASSED [ 29%]
tests/test_opacity.py::test_ui_to_background_cover_maps_25 PASSED        [ 32%]
tests/test_opacity.py::test_background_cover_to_ui_roundtrip PASSED      [ 35%]
tests/test_opacity.py::test_clamp_ui PASSED                              [ 37%]
tests/test_paths.py::test_vscode_settings_path_macos PASSED              [ 40%]
tests/test_paths.py::test_cursor_settings_path_windows PASSED            [ 43%]
tests/test_paths.py::test_find_jetbrains_prefers_newest PASSED           [ 45%]
tests/test_paths.py::test_find_jetbrains_returns_prospective_path_when_other_xml_missing PASSED [ 48%]
tests/test_service.py::test_apply_and_bootstrap_reads_adapter_state PASSED [ 51%]
tests/test_service.py::test_bootstrap_uses_store_when_adapter_is_not_detected PASSED [ 54%]
tests/test_service.py::test_bootstrap_preserves_store_opacity_zero_from_store_fallback PASSED [ 56%]
tests/test_service.py::test_bootstrap_adapter_state_wins_over_store PASSED [ 59%]
tests/test_service.py::test_bootstrap_uses_store_when_installed_adapter_has_no_wallpaper PASSED [ 62%]
tests/test_service.py::test_apply_failure_returns_error_without_saving PASSED [ 64%]
tests/test_service.py::test_clear_clears_adapter_and_store PASSED        [ 67%]
tests/test_service.py::test_extension_tip_only_reports_missing_editor_extensions PASSED [ 70%]
tests/test_service.py::test_build_default_service_wires_all_real_adapters PASSED [ 72%]
tests/test_settings_json.py::test_write_preserves_other_keys PASSED      [ 75%]
tests/test_settings_json.py::test_commented_jsonc_reads_writes_and_preserves_other_keys PASSED [ 78%]
tests/test_settings_json.py::test_read_and_clear PASSED                  [ 81%]
tests/test_settings_json.py::test_vscode_detect PASSED                   [ 83%]
tests/test_state_store.py::test_roundtrip PASSED                         [ 86%]
tests/test_state_store.py::test_clear_app PASSED                         [ 89%]
tests/test_ui.py::test_midnight_glass_theme_constants PASSED             [ 91%]
tests/test_ui.py::test_apply_requires_installed_app_and_valid_image PASSED [ 94%]
tests/test_ui.py::test_success_message_has_target_specific_reload_hint PASSED [ 97%]
tests/test_ui.py::test_normalize_image_path_returns_resolved_absolute_path PASSED [100%]

============================== 37 passed in 0.36s ==============================
```
