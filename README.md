# Wallpaper Manager

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Windows-lightgrey.svg)](#supported-apps--platforms)

本地桌面应用：为 **VS Code / Cursor / IntelliJ IDEA / PyCharm / Ghostty** 分别设置壁纸图片与透明度。

A local desktop app that manages per-app wallpaper image + opacity for popular editors and Ghostty — on **macOS** and **Windows**.

> Author: [@shayuaidoudou](https://github.com/shayuaidoudou)

---

## Features

- **按应用独立配置**：每个 IDE / 终端单独选图、调透明度，互不影响
- **实时预览**：选择图片后即时预览，透明度所见即所得
- **原生配置写入**：直接改各应用配置文件，无需中间代理层
- **路径可覆盖**：自动检测失败时，可在设置页手动指定配置文件路径
- **Violet Noir UI**：深色玻璃质感界面，带 macOS 风格切换动效

## Supported apps & platforms

| App | Config target | macOS | Windows |
|-----|---------------|-------|---------|
| VS Code | `settings.json` (`backgroundCover.*`) | ✓ | ✓ |
| Cursor | `settings.json` + Background Cover CSS sync | ✓ | ✓ |
| IntelliJ IDEA | `options/other.xml` | ✓ | ✓ |
| PyCharm | `options/other.xml` | ✓ | ✓ |
| Ghostty | `config` / `config.ghostty` | ✓ | ✓ |

## Requirements

- **Python 3.11+**（macOS 自带 `python3` 常为 3.9，请使用 `python3.11` 或更新版本）
- **VS Code / Cursor**：需安装 [Background Cover](https://marketplace.visualstudio.com/items?itemName=manasxx.background-cover)（`manasxx.background-cover`）扩展才能真正显示壁纸；本工具仍可写入设置并提示安装
- **JetBrains**：应用后如未立即生效，请重启 IDE
- **Ghostty**：多数外观项可自动重载；若未生效请完全退出后重开

## Install

```bash
git clone https://github.com/shayuaidoudou/Wallpaper-Manager.git
cd Wallpaper-Manager

python3.11 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

## Run

```bash
python -m wallpaper_manager
# 或
wallpaper-manager
```

使用方式：

1. 顶部 Tab 选择目标应用
2. 浏览或粘贴图片路径，拖动透明度
3. 点击 **应用到 …**
4. 需要时点右上角齿轮进入 **路径配置**，手动指定各应用配置文件

本地状态保存在 `~/.wallpaper-manager/config.json`（含壁纸草稿与路径覆盖）。

## Project layout

```text
wallpaper_manager/
  adapters/     # VS Code / Cursor / JetBrains / Ghostty writers
  core/         # models, opacity, state store, service
  detect/       # OS path resolution
  ui/           # Flet UI (theme, motion, settings)
tests/          # pytest suite
docs/           # design notes
```

## Tests

```bash
pytest -v
# 或
.venv/bin/pytest -v
```

## Configuration notes

| App | Typical config path (macOS) |
|-----|-----------------------------|
| VS Code | `~/Library/Application Support/Code/User/settings.json` |
| Cursor | `~/Library/Application Support/Cursor/User/settings.json` |
| IDEA | `~/Library/Application Support/JetBrains/IntelliJIdea*/options/other.xml` |
| PyCharm | `~/Library/Application Support/JetBrains/PyCharm*/options/other.xml` |
| Ghostty | `~/Library/Application Support/com.mitchellh.ghostty/config.ghostty` |

路径检测失败时，用 UI 里的路径配置页覆盖即可。

## Contributing

欢迎 Issue / PR。请先阅读 [CONTRIBUTING.md](CONTRIBUTING.md)。

## License

[MIT](LICENSE) © shayuaidoudou
