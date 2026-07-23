# Wallpaper Manager

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Windows-lightgrey.svg)](#支持的应用)

**统一管理多个 IDE / 终端背景的本地小工具。**

在一个界面里，为 VS Code、Cursor、IntelliJ IDEA、PyCharm、Ghostty 分别选图、调透明度并一键写入各自配置——不用再翻各个应用的设置文件。

> Author: [shayuaidoudou](https://github.com/shayuaidoudou) · 个人小站：[鲨鱼爱兜兜的小站](https://blog.shayuaidoudou.store/)

## 下载体验（macOS）

无需装 Python，直接下载 [最新 Release](https://github.com/shayuaidoudou/Wallpaper-Manager/releases/latest) 里的：

**`Wallpaper-Manager-*-macos-arm64.zip`**（Apple Silicon / M 系列）

1. 解压得到 `Wallpaper Manager.app`
2. 拖到「应用程序」，或直接双击打开  
3. 若提示「无法验证开发者」：在 App 上 **右键 → 打开**，或在终端执行：

```bash
xattr -cr "/Applications/Wallpaper Manager.app"
```

> 当前预编译包仅含 **macOS arm64**。Intel Mac / Windows 请用下方源码方式运行。

---

## 它解决什么

日常同时用好几个编辑器时，换壁纸往往要：

1. 找到每个应用的配置目录  
2. 记住不同格式（`settings.json` / `other.xml` / Ghostty config）  
3. 再分别改透明度  

Wallpaper Manager 把这些收成一套：**选应用 → 选图 → 调透明度 → 应用**。每个应用独立配置，互不影响。

## 功能一览

- **多应用统一入口**：编辑器 + Ghostty 在同一窗口切换管理
- **按应用独立配置**：图片与透明度互不覆盖
- **实时预览**：选图与透明度所见即所得
- **原生写入配置**：直接改各应用自己的配置文件
- **路径可覆盖**：自动检测失败时，在设置页选择数据目录，自动定位配置文件

## 支持的应用

| 应用 | 写入目标 | macOS | Windows |
|------|----------|-------|---------|
| VS Code | `settings.json`（Background Cover） | ✓ | ✓ |
| Cursor | `settings.json` + CSS 同步 | ✓ | ✓ |
| IntelliJ IDEA | `options/other.xml` | ✓ | ✓ |
| PyCharm | `options/other.xml` | ✓ | ✓ |
| Ghostty | `config` / `config.ghostty` | ✓ | ✓ |

## 快速开始

需要 **Python 3.11+**（macOS 自带 `python3` 常为 3.9，请用 `python3.11` 或更新版本）。

```bash
git clone https://github.com/shayuaidoudou/Wallpaper-Manager.git
cd Wallpaper-Manager

python3.11 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[dev]"

python -m wallpaper_manager
```

使用步骤：

1. 顶部 Tab 选择目标应用  
2. 浏览或粘贴图片路径，拖动透明度  
3. 点击 **应用到 …**  
4. 路径不对时，点右上角齿轮进入 **路径配置**

本地状态保存在 `~/.wallpaper-manager/config.json`。

### 使用前注意

- **VS Code / Cursor**：需安装 [Background Cover](https://marketplace.visualstudio.com/items?itemName=manasxx.background-cover)（`manasxx.background-cover`）扩展才能真正显示壁纸  
- **JetBrains**：应用后如未立即生效，请重启 IDE  
- **Ghostty**：多数外观项可自动重载；未生效时可完全退出后重开  

## 路径说明（偏 macOS）

默认按 **macOS** 常见位置自动检测。设置页提示与示例也以 mac 为主。

| 应用 | 建议选择的数据目录（macOS） |
|------|-----------------------------|
| VS Code | `~/Library/Application Support/Code` |
| Cursor | `~/Library/Application Support/Cursor` |
| IDEA | `~/Library/Application Support/JetBrains/IntelliJIdea*` |
| PyCharm | `~/Library/Application Support/JetBrains/PyCharm*` |
| Ghostty | `~/Library/Application Support/com.mitchellh.ghostty` |

请选 **数据目录**（Application Support），不要选 `.app` 安装包本身。选好后程序会自动找到配置文件。

**Windows**：功能可用，但路径因安装方式差异较大，自动检测可能不准。若检测失败，请在路径配置里手动选择 `%APPDATA%` 下对应数据目录（不要选 `Program Files`），例如 `%APPDATA%\Cursor`、`%APPDATA%\JetBrains\IntelliJIdea*`。

## 项目结构

```text
wallpaper_manager/
  adapters/     # 各应用写入适配
  core/         # 模型、状态、服务
  detect/       # 路径检测
  ui/           # Flet 界面
tests/
docs/
```

```bash
pytest -v
```

## 打包（维护者）

在 Apple Silicon Mac 上：

```bash
chmod +x scripts/pack_macos.sh
./scripts/pack_macos.sh          # 产出 release/Wallpaper-Manager-<version>-macos-arm64.zip
```

## Contributing

欢迎 Issue / PR，请先阅读 [CONTRIBUTING.md](CONTRIBUTING.md)。

## License

[MIT](LICENSE) © shayuaidoudou
