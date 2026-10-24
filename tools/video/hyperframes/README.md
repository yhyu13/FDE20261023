# HyperFrames 在本仓的用法

**本仓的视频渲染层用 HyperFrames（HeyGen 开源，Apache-2.0）。浏览器用本机的 Microsoft Edge，不另外下 Chrome。模板在 `template/`，渲染走 `render.ps1`。**

## 0. 先确认机器状态

- **浏览器：** `C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe`（版本 156.0.4314.42）。已写进用户级环境变量 `HYPERFRAMES_BROWSER_PATH`，新终端自动生效。
- **ffmpeg / ffprobe：** 9.0.2（WinGet Gyan 包），已在 PATH。
- **Node：** v22.14.0，满足 `hyperframes` 的 `engines.node >= 22`。

**为什么用 Edge 不用 Chrome：** 常规浏览器构建没有 `HeadlessExperimental.beginFrame`，引擎会退到截图采集路径，慢一些但结果一样确定。实测 8 秒片子在 Edge 上渲了 15 秒（240 帧，4 worker）。要回到 beginFrame 快速路径才需要 `npx hyperframes browser ensure` 拉 chrome-headless-shell。

**代价：** 走截图路径时不支持 `--resolution` 放大到 4K，要 4K 就得另装 headless shell。

## 1. 起一个片子

```powershell
# 复制模板，别直接改模板本身
Copy-Item -Recurse tools\video\hyperframes\template work\hyperframes\片名
# 改 index.html 里的 data-composition-variables（主标题、副标题、要点）
# 每个场景一个文件，放在 compositions\ 里
```

模板长这样：

| 文件 | 作用 |
|---|---|
| `index.html` | 根 composition：声明片长、宽高，挂载各个场景，根自己也要注册一条时间轴 |
| `compositions/scene-*.html` | 一个场景一个文件，样式、标记、脚本全部写在 `<template>` 里 |
| `hyperframes.json` | 注册表与素材目录配置 |
| `assets/gsap.min.js` | 本地 GSAP 3.14.2（72,779 字节），不走 CDN，离线可渲 |

## 2. 渲染

```powershell
powershell -ExecutionPolicy Bypass -File tools\video\hyperframes\render.ps1 `
    -ProjectDir work\hyperframes\片名 -Output renders\片名.mp4
```

这个脚本按顺序做四件事，任何一步不过就停：

1. 确认 Edge 与 ffprobe 在位，把 `HYPERFRAMES_BROWSER_PATH` 设上。
2. 跑 `hyperframes check --json`，error 不清零就停，报告落在项目目录的 `.check.json`。
3. 跑 `hyperframes render --quality looks`（可选 `draft` 迭代、`delivery` 终版）。
4. 用 ffprobe 核对成片时长、分辨率、帧数；时长与根节点 `data-duration` 差超过 0.05 秒就报错。

**手工等价命令**（Windows 上 `npx` 被执行策略挡，必须写 `npx.cmd`）：

```powershell
npx.cmd -y hyperframes@latest check --json
npx.cmd -y hyperframes@latest render --quality looks --output renders\out.mp4
```

## 3. 写 composition 必须守的规矩

这些是 `hyperframes check` 会拦的，踩过两次：

- **根 composition 也要注册时间轴：** `window.__timelines["main"] = tl`。只给场景注册、根不注册，check 直接报 `Missing window.__timelines registration`。
- **host id、场景的 `data-composition-id`、时间轴 key 三者一致。** 不一致的话每个场景会等 45 秒再显示静帧。
- **每个 clip 自己定位：** 引擎会把 clip 移出普通流，写成 flex 居中会全部叠在一起（本仓第一次渲染就是这样，标题和副标题压成一团）。给 `.clip` 写 `position: absolute`，坐标自己定。
- **场景根用 `inset: 0`**，不要写死像素；画布尺寸是 `data-width` × `data-height`。
- **场景里用 `fromTo`，不要用 `from`。** host 每次显示场景都会重新 seek，`from` 只记录一次起始态，来回 seek 会漂。
- **id 在整页唯一**，场景内加前缀（`#scene-title-title`）。场景的时间轴够不到别的文件里的元素。
- **禁止不确定：** 不写 `Date.now()`、不用没种子的 `Math.random()`、不依赖网络请求。

## 4. 和现有管线的关系

- **现有：** `tools/video/pipeline.py` 负责稿子解析、Edge TTS、词级字幕、混音、时长校验；`render_slides` + `render_pipe` 负责出帧与编码。
- **HyperFrames 接管的：** 出帧与编码这一段——HTML 当源码，时间轴是 `data-start` / `data-duration` 数据，GSAP 编排，引擎逐帧抓、FFmpeg 编码。
- **还没迁的：** 稿子解析、TTS、字幕、混音仍在 Python 侧。**现有 6 支讲解片不动**，先拿新片试点。
- **迁移时的验收口径不变：** 时长对齐、字幕对齐、画面命中这三条检查继续用 `tools/video/verify_video.py` 与 `check_subs.py`。

## 5. 边界

- **不做：** 部署到公网、把渲染产物当交付物直接提交、动现有 6 支讲解片。
- **产物目录：** `renders/` 与项目里的 `.check.json` 都不入库（已在 `.gitignore`）。
- **第三方：** GSAP 3.14.2 随模板入库（`assets/gsap.min.js`），HyperFrames 本身通过 npx 拉取，不入库。
