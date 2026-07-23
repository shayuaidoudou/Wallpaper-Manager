# Contributing to Wallpaper Manager

感谢你愿意一起完善这个项目。

## Development setup

```bash
python3.11 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pytest -v
```

运行应用：

```bash
python -m wallpaper_manager
```

## Guidelines

1. **保持适配器隔离**：每个应用的读写逻辑放在 `wallpaper_manager/adapters/`，不要把 IDE 特有细节泄漏进 UI。
2. **透明度约定**：UI 统一使用 `0–100`；写入各应用前在 `core/opacity.py` 做映射。
3. **路径可注入**：适配器构造函数应支持注入配置路径，便于测试与「路径覆盖」。
4. **半透明颜色**：Flet/Flutter 使用 `#AARRGGBB`。请优先用 `ft.Colors.with_opacity(alpha, "#RRGGBB")`，不要手写容易写反的 8 位 hex。
5. **测试**：新增适配器或路径逻辑时补 pytest；提交前跑通 `pytest -v`。

## Pull requests

- 说清楚动机（修复 / 功能 / 文档）
- 尽量小而专注
- 若改 UI，附一张截图或简短操作说明
- 不要提交 `.venv/`、`.idea/`、本机绝对路径配置、密钥

## Reporting issues

请尽量包含：

- 操作系统与版本（macOS / Windows）
- Python 版本
- 目标应用（VS Code / Cursor / IDEA / PyCharm / Ghostty）
- 复现步骤与期望行为
- 相关报错或截图

## License

贡献内容将按仓库 [MIT License](LICENSE) 授权。
