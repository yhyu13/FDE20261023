# booth_2 · XX客车全域获客模型 · 展位演示（两项能力）

**全自动循环播放，无任何人工操控。** 双击 `slides.html` 即开（需与 `tts/` 目录同级）。

## 这是什么

一段约 **110 秒**的自动演示，对齐 `presubmit/sunwin.html`（2026-10-25 版）的七步闭环叙事，
内容接自客户调研真源。两项能力 = STEP 02 行业问题库 + STEP 03 找客户模型：

| 页 | 内容 | 口播时长 |
|----|------|---------|
| s1 | 封面 + 七步闭环链路（引擎打头，两项能力高亮）+ 调研结论（12 问 / 8 有事实 / 3 要说清边界 / 1 无依据） | 见 timings |
| s2 | 能力一 · CQ 行业问题库（12 问 × S01–S11 × 三档闸门 + 引擎分级复核 96.4/91.2/94.6% + 客群×渠道覆盖矩阵） | 见 timings |
| s3 | 能力二 · 找客户模型定制（输入含典型客户描述 → 10 条规则 → 4,820 企业池 → 三档匹配 + 渠道分层 + 模型评估） | 见 timings |
| s4 | 收尾（问题库决定说什么 / 找客户模型决定对谁说 / 后续五步 / Day1 待确认） | 见 timings |

演示中的脚本动作（口播驱动，非人工）：CQ04 高风险问题被红色拦截条拦下、目标区域自动加上「非洲」、
规则当场重算、企业池与三档分布条同步更新。播完自动回到封面，无限循环。

## ⚠️ 声音：首次要点一下

Chrome / Edge 的自动播放策略会**静默拦截**无手势的 `audio.play()`——画面照走，但没声音。
已在页面里加首次 `pointerdown / keydown / touchstart` 解锁：

- **展位上点一下页面（通常是点全屏那一下）**，之后全程有声；
- 没解锁前，HUD 显示「🔇 点击一次开启声音」；
- kiosk / 无人值守模式，启动参数加 `--autoplay-policy=no-user-gesture-required` 即可全程自动有声。

## 重建

```powershell
python assets/day1025/booth/booth_2/build.py            # 全量：合成口播 + 出 timings + 渲染 slides/video
python assets/day1025/booth/booth_2/build.py --skip-tts # 复用已有 mp3，只重算时间与产物
```

产物：

| 文件 | 说明 |
|------|------|
| `slides.html` | **交付物**：交互幻灯片，timings 已内联，单文件可发 |
| `slides.src.html` | 幻灯片源（`/*TIMINGS*/null` 占位符） |
| `tts/sN.mp3` | 每页口播（edge-tts `zh-CN-YunjianNeural` 浑厚男声，rate +4%） |
| `tts/timings.json` / `timings.js` | 每页时长、字幕分段、动作提示点（秒，相对本页起点） |
| `tts/words.json` | 词级边界缓存（`--skip-tts` 复用） |
| `video/index.html` | HyperFrames 合成（4 场，总长见 timings） |
| `video/compositions/` | 四个场景文件 |
| `video/assets/*.mp3` | 口播拷贝，供 HyperFrames 混音 |

改口播文案或换音色 → 改 `build.py` 里的 `SLIDES` / `VOICE`，**必须全量重跑**（不能 `--skip-tts`，
words.json 缓存的词边界与 mp3 不同源会让 cue 全部错位）。

## 口径与免责

- 客户问题、事实编号（S01–S11）、审核判定（REV01–05）、传播反馈（FB01–04）、缺口（G1–G8）
  全部来自 `assets/customer_analysis/`，可回链；闭环七步、覆盖矩阵、引擎分级复核（96.4/91.2/94.6%）、
  规则命中量（2,860/1,940/3,120/2,640/2,210/1,860/-1,180/3,260/1,720/960）、4,820 企业池、
  86.2% 精度、94%/88%/61% 评估口径对齐 `assets/day1025/presubmit/sunwin.html`（2026-10-25 版）。
  画面中的企业池、命中量、匹配分布为**演示用模拟数据**。
- 企业事实（智能驾驶能力清单、线路→车型规则、TCO 测算、服务网络现状、RoboBus 阶段）⚠️ 待 Day1 现场确认，页面已标注。
- 未跑 `npx hyperframes check`（本机未装 CLI）；`video/` 为按 format.md 契约手写的工程文件，渲染前请先跑 check。
