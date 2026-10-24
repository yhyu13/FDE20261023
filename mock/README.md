# mock/ · HTML 原型、视频、幻灯片三条线的调研与落地

这个目录放"用 skill 做 HTML 页面 / 视频 / 幻灯片"这件事的调研与学习笔记。**不是成品目录**——平台 mock 成品在 `assets/day1024/`（任务书指定）。

| 文件 | 内容 |
|---|---|
| [`学习笔记/01-模拟平台原型.md`](./学习笔记/01-模拟平台原型.md) | 把平台画成"像真软件"的三个 skill，厂商对内容平台的模块划分 |
| [`学习笔记/02-视频-HyperFrames.md`](./学习笔记/02-视频-HyperFrames.md) | HyperFrames 引擎与 7 个上游 skill、本机环境实测、MCP 现状、知乎与博客的流程经验 |
| [`学习笔记/03-幻灯片-HTML.md`](./学习笔记/03-幻灯片-HTML.md) | 25 个 HTML 幻灯片 skill 的策展清单、装哪两个、visual-explainer 的 MCP server 怎么接 |
| [`调研总结.md`](./调研总结.md) | 第一轮（平台 mock）的带来源分级版本：结论、引用、可信度分级 |

---

## 已安装的 skill（本仓项目级）

装在 `.kilo/skills/`（Kilo CLI 项目级 skill 发现路径）。**新会话才生效**，本会话不会自动加载。

### 入口（本仓自研，先加载这三个）

| skill | 干什么 |
|---|---|
| `mock-devops-platform` | 平台 mock：选 ui-mockups / web-prototype / html-artifacts 哪一个，以及哪些上游默认在本仓要改 |
| `hyperframes-video` | 视频：HyperFrames 命令阶梯、本机环境现状、要不要接 MCP、跟现有 `tools/video/pipeline.py` 怎么分工 |
| `html-slides` | 幻灯片与图解：frontend-slides 管页面、visual-explainer 管图解，含 MCP 注册写法 |

### 第三方 skill

| skill | 干什么 | 上游 | commit | 许可 |
|---|---|---|---|---|
| `ui-mockups` | 把平台画成"看起来像真软件"的假界面：发丝线、10–13px 界面字、密度即真实、禁止灰占位块 | [kgoedecke/ui-mockup-skill](https://github.com/kgoedecke/ui-mockup-skill) | `9f5f93e` | MIT |
| `web-prototype` | 单文件 HTML 种子模板 + 8 套 section 骨架 + P0/P1/P2 自检清单 | [nexu-io/open-design](https://github.com/nexu-io/open-design) `design-templates/web-prototype` | `e03d5c2` | Apache-2.0 |
| `html-artifacts` | 单文件交互 HTML 的质量标杆库：20 个完整范例 + 管线流程图/看板/编辑器参考 | [liush2yuxjtu/html-artifacts](https://github.com/liush2yuxjtu/html-artifacts) | `7767f60` | Apache-2.0 |
| `hyperframes` | HyperFrames 渲染契约、12 条硬规则、按视频类型分流 | [heygen-com/hyperframes](https://github.com/heygen-com/hyperframes) | `8a102f6` | Apache-2.0 |
| `hyperframes-cli` | CLI 命令手册 + 失败恢复表 | 同上 | `8a102f6` | Apache-2.0 |
| `hyperframes-registry` | 50+ block/component 目录与检索 | 同上 | `8a102f6` | Apache-2.0 |
| `remotion-to-hyperframes` | Remotion / Motion Canvas / Lottie / Three.js / Manim / AE / Blender → HyperFrames，含逐帧 SSIM 比对与 4 档测试语料 | 同上 | `8a102f6` | Apache-2.0 |
| `slideshow` | deck 式视频 | 同上 | `8a102f6` | Apache-2.0 |
| `frontend-slides` | 零依赖 HTML 幻灯片：先出 3 个预览再全量生成，含 14 张风格卡 | [zarazhangrui/frontend-slides](https://github.com/zarazhangrui/frontend-slides) | — | MIT |
| `visual-explainer` | 图解与讲解页生成器，自带 stdio MCP server（`visual_explainer_prepare` / `visual_explainer_render_html`） | [nicobailon/visual-explainer](https://github.com/nicobailon/visual-explainer) | — | MIT |

各 skill 的 `LICENSE`（`html-artifacts` 另有 `NOTICE`）已随目录保留。`html-artifacts` 的 `reference/*.html` 为 ThariqS/html-effectiveness 逐字原样文件（© Anthropic PBC，Apache-2.0）。

### 装了但跳过的部分

- `hyperframes/assets/frame-presets`：13 套 deck 外观约 990 KB，含二进制字体；上游 `references/look.md:27` 说它只用于幻灯片 deck、不做兜底。
- `hyperframes` 的 `media-use` / `figma`：前者 116 文件 1.9 MB 含 mp3 音效与 LUT 二进制，且与本仓 Edge TTS + numpy 配乐重叠；后者需要 Figma MCP 与设计资产。
- `frontend-slides` 的 14 套 `design.md`：每份 40 KB 以上，全套约 3.5 MB；按需再从上游取。
- `visual-explainer` 的 `banner.png`（1,187,907 字节）与 `replay.gif`（367,945 字节）：二进制不入库。

---

## 本机环境现状

- **HyperFrames：** Node v22.14.0 ✅ · ffmpeg 9.0.2 ✅ · ffprobe 9.0.2 ✅ · **浏览器 = Microsoft Edge 156.0.4314.42** ✅（用户级环境变量 `HYPERFRAMES_BROWSER_PATH`）。常规浏览器没有 `beginFrame`，引擎退到截图采集路径，慢一些但结果一样确定；走这条路不支持 `--resolution` 放大到 4K。实测 8 秒片子渲了 15 秒。详见 `mock/学习笔记/02-视频-HyperFrames.md` §11。
- **HyperFrames 在本仓的落点：** `tools/video/hyperframes/`——`template/`（两场景模板，GSAP 本地化在 `assets/gsap.min.js`）、`render.ps1`（check → render → ffprobe 核对一条命令）、`README.md`。
- **visual-explainer MCP：** 已装已注册（`.kilo/kilo.json`），运行时在 `tools/vendor/visual-explainer/`（上游原版 0.14.0，未改动）。
- **视觉工具：** 本仓已有 `tools/video/pipeline.py` 全链路（Edge TTS → 词级字幕 → 音频实测定时 → 逐帧 → libass 烧字幕 → 校验）。HyperFrames 接管的是**出帧与编码**这一段，稿子/TTS/字幕/混音仍在 Python 侧；现有 6 支讲解片不动。

---

## 怎么用

1. **先加载入口 skill**：`mock-devops-platform` / `hyperframes-video` / `html-slides`，它们各自写清了该调哪个上游、哪些上游默认要改。
2. **动手前读笔记**：对应的 `mock/学习笔记/*.md` 里有每个参考的取舍理由和本仓要改的点。
3. **本仓要改掉的上游默认**：远端图标/字体热链 → 内联或入库；`~/.claude/artifacts/` → `assets/day1024/`；bash 脚本 → WSL 或 `Start-Process`；`npx` → `npx.cmd`。

---

## 给 Claude Code 用户

本仓 skill 装在 `.kilo/skills/`（Kilo 读这个目录）。Claude Code 读 `.claude/skills/`，需要镜像一份：

```powershell
New-Item -ItemType Directory -Force -Path ".claude\skills" | Out-Null
Copy-Item -Recurse -Force ".kilo\skills\*" ".claude\skills\"
```

镜像后两边内容相同，改动请改 `.kilo/skills/` 再重新同步，避免两份漂移。
