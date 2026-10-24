---
name: mock-devops-platform
description: 在本仓做「AI 平台/系统的单文件 HTML mock demo」时调用——典型触发：day1024 的 AI 营销 DevOps 平台原型、六道题的可点击方案演示、给评审人看的平台界面假象、"做个 mock 页面/原型/demo"。它决定调 ui-mockups / web-prototype / html-artifacts 哪一个，以及哪些上游默认在本仓必须改（远端图标热链、Claude 专属输出路径、bash 脚本）。若目标是生产代码、真接后端或真调模型，不要用这个 skill。
---

# mock-devops-platform · 在本仓把"平台"做成一个能双击打开的单文件 HTML

## 何时调

- 任务书要"单文件 HTML + 模拟数据"的平台原型（当前：`assets/day1024/prompt1.md`）
- 要把已有的文字版方案升级成**界面版**方案（`assets/day1023/result/submit/` 是昨天的文字+HTML版）
- 评审人要"看一眼平台长什么样"，而不是读方案

## 零、先记住本仓库的物理事实

| 事实 | 位置 | 为什么重要 |
|---|---|---|
| 成品目录不是 `mock/`，是 `assets/day1024/` | `assets/day1024/prompt1.md` | `mock/` 放方法与调研，不放成品 |
| 昨天的交付形态：单文件 HTML + README + zip | `assets/day1023/result/submit/` | 已有的质量基线，先读再动手 |
| 业务理解与五步流程 | `assets/day1023/result/上海申沃客车需求分析.md` | mock 的每屏都要能对回这五步 |
| 三个上游 skill 已装 | `.kilo/skills/{ui-mockups,web-prototype,html-artifacts}/` | 新会话才生效 |
| 本仓红线 | `AGENTS.md` §13（纯文本资产 / 自由文本不驱动业务 / 不宣称未验证效果 / 数据不出厂区 / 不做占位式交付） | 改一条就踩一条 |
| 调研与选型依据 | `mock/调研总结.md`、`mock/README.md` | 为什么装这三个、为什么排除其他 |

## 一、三条路径，先选一条

| 你要做的东西 | 调哪个 | 怎么用 |
|---|---|---|
| **平台界面假象**（像真软件的窗口、侧栏、表格、看板） | `ui-mockups` | 读它的 clean-UI 规则集 → 从 `references/components.md` 粘组件 → **自己截图回看** |
| **单文件页面的骨架与排版**（不想从零写 CSS） | `web-prototype` | 读 `assets/template.html` → 从 `references/layouts.md` 挑 section → 跑 `references/checklist.md` 的 P0 |
| **拿不准"该做到多好"** | `html-artifacts` | 读最接近的 `reference/*.html`（管线看 13、看板看 11、可点击流程看 08、编辑器看 18–20），**先读再写** |

三者正交，可叠加。典型组合：`web-prototype` 出骨架 → `ui-mockups` 定密度与质感 → `html-artifacts` 当标尺。

**动手前先说一句**：打算做哪几屏（`web-prototype` Step 2 的做法）——此时改成本最低，写完再改就是重写。

## 二、上游默认里，本仓必须改的三条

1. **远端图标热链 → 内联 SVG**。
   证据：`ui-mockups/references/components.md:32,56,85` 用 `icons.duckduckgo.com`、`api.iconify.design` 取图标。
   本仓要求：demo 要能断网双击打开，且 AGENTS.md §13.1 要求资产是可 diff 的文本。**一律换成内联 SVG**；要用外部图标必须下载进仓并相对引用。
2. **`~/.claude/artifacts/` → `assets/day1024/`**。
   证据：`html-artifacts/SKILL.md` 的输出契约。
   本仓要求：成品跟任务书放一起，评审人才找得到。
3. **`scripts/open-artifact.sh` 是 bash，Windows 跑不了**。
   本仓替代：写完直接 `Start-Process <file>.html`，然后在交付说明里给绝对路径。

## 三、本仓特有的红线（通用 skill 里没有的那几条）

- **模拟数据必须标出来**。页面上每个数字要么来自任务书/已有资料，要么明确标 `模拟数据`。证据：`web-prototype/references/checklist.md` 的 "No invented metrics" + AGENTS.md §13.3。
- **企业事实不许臆造**。车型能力、合作阶段、已投入运营与否，只能用已核实口径；未核实的写 `⚠️ 待 Day1 现场确认` 并**把它做成一等公民状态**（界面上看得见），而不是塞进脚注。
- **四类成熟度不许混用**：辅助驾驶 / 自动驾驶合作与试点 / 量产车型 / 已投入运营——每条素材要带自己那一类。证据：`assets/day1024/prompt1.md` 第 5 条。
- **每个结论可回溯**：素材、问题、案例、主题之间要有对应关系（任务书第 2 条），界面上最好能看到编号（S / CQ / PIC / REV，见 `assets/day1023/result/submit/README.md`）。
- **不做占位式交付**（AGENTS.md §13.5）：宁可交一个真跑通的窄切片，不交五屏都点不动的宽原型。灰占位块、假图表、"Feature One" 一律不许。

## 四、验收的最小门槛

逐条打勾，不过不算交付：

- [ ] **单文件**：一个 `.html`，CSS/JS/字体全内联，**断网双击能开**，无 CDN、无构建步骤
- [ ] **P0 全过**：`web-prototype/references/checklist.md` 的 P0 逐条过
- [ ] **截图自查过**：`ui-mockups` 的 pre-ship checklist 要求"100% 与放大两种都看过"——这一步不能省
- [ ] **每个数字有出处或标模拟**；无出处的企业事实标 `⚠️ 待 Day1 现场确认`
- [ ] **无远端依赖**：图标、字体、图片全部本地化或内联
- [ ] **界面密度对**：界面文字 10–13px、一个强调色、发丝线分隔、无浮夸阴影、无 emoji 图标
- [ ] **故事自洽**：同一套角色/工作区/任务贯穿全屏，标签互相呼应
- [ ] **有出口**：能把人做的决定带走（导出选题清单/口径清单），不是死页面
- [ ] **交付说明**写清：哪些是模拟数据、哪些待现场确认、哪些没做（范围划界）

## 五、什么时候**不**调这个 skill

- 要真接后端、真调模型、真发布 → 那是实现，不是 mock；走 `AGENTS.md` 的 spec-kit + TDD 流程
- 要的是产品文档/方案书（Markdown）→ 用 `content-craft` / `manage-up-core`，不要用 HTML mock 代替文字
- 只是要一张示意图/图 → 用 `anatomy` 或 `taste-imagegen-*`
- 要做的是游戏 → `single-file-html-game` / `game-dev-loop`

## 六、来源

- 三个上游 skill 的 commit 锁定与许可见 `mock/README.md` 溯源表
- 选型理由、被排除的候选、厂商内容中台的模块地图见 `mock/调研总结.md`
- 本仓纪律来源：`AGENTS.md`（§6 闸、§12 必须停下来的事、§13 硬性红线）
