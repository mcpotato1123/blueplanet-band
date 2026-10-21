# 素材版权说明（NOTICE）

本工程的 **代码** 以 MIT 协议发布（见 `LICENSE`）。
**以下内容不在 MIT 范围内**，版权归《海蓝星之梦》原作者/PygmaGame 所有；收录它们只是为了让工程能直接构建出可运行的包。

## 不在 MIT 范围内的内容

| 路径 | 内容 | 来源 |
|---|---|---|
| `src/common/story/*.txt` | 全部剧本文字（10,070 句） | PC 版 `.rpyc` 解包后编译 |
| `src/common/img/b/` | 实际使用的 80 张背景 | PC 版 `images/background/`、`DLC/DLC_images/` |
| `src/common/img/s/` | 立绘 base、表情差分（21 个标签 / 218 张） | PC 版 `images/role/` |
| `src/common/img/w/`、`src/common/img/t/` | 17 张 CG 与缩略图 | PC 版 `images/CG/`、`DLC/DLC_images/` |
| `src/common/img/ui/`、`src/common/icon.png` | 首页背景、标题、图标 | PC 版 `gui/game_menu.png`、`gui/main_menu.png`、`gui/window_icon.png` |
| `preview/*.png` | 用上述素材合成的界面预览 | —— |

## 可以自由使用的部分（MIT）

- `src/pages/**/*.ux`：7 个页面
- `src/common/reader.js`、`vm.js`、`assets.js`（生成文件）、`theme.js`
- `src/app.ux`、`src/manifest.json`
- `tools/**`：剧本编译、出图、构建脚本
- `sim/**`：浏览器模拟器
- 文档（`README.md`、`NOTICE.md`、`LICENSE`）

## 使用建议

- 拿这套代码做**自己的** VN 移植没问题：替换 `src/common/img/` 和 `src/common/story/`，改 `manifest.json` 的包名即可。
- **不要**把这批素材用于商业用途，也不要单独再分发素材。
- 如果版权方有异议，删除上表列出的目录即可；代码本身不依赖具体内容。
