---
name: html-slides
description: 在本仓做 HTML 幻灯片/讲解页/汇报片/图解时调用——单文件 HTML deck、PPTX 转网页、把讲解稿 md 变成可讲的页面、或要画流程图与机制图。决定用 frontend-slides（页面）还是 visual-explainer（图解），以及 visual-explainer 的 MCP server 怎么接进 Kilo。若只是改现有 problems/*.html 的文字，不要用这个 skill。
---

# html-slides · 本仓的 HTML 页面与图解路线

## 何时调

- 要把讲解稿 md、方案、清单变成**能讲的页面**（单文件 HTML，双击即开）
- 要画**流程图 / 机制图 / 对照图**并嵌进页面或文档
- 要把别人给的 PPT/PPTX 转成网页
- 要接 `visual-explainer` 的 MCP server

## 零、先记住本仓库的物理事实

| 事实 | 位置 | 影响 |
|---|---|---|
| 已有 6 篇单页讲解版 HTML | `problems/*-讲解稿.html` | 这是基线，新页面要对齐"双击即开、无外链" |
| 讲解稿 md 是唯一真源 | `problems/*-讲解稿.md` | 页面从 md 生成，不要在页面里另写一套内容 |
| 资产红线 | `AGENTS.md` §13.1 | 纯文本、可 diff；图片要入库并相对引用 |
| 两条已装的 skill | `.kilo/skills/frontend-slides/`、`.kilo/skills/visual-explainer/` | 页面归前者，图解归后者 |
| 调研笔记 | `mock/学习笔记/03-幻灯片-HTML.md` | 25 个候选里为什么装这两个、为什么不装其他 |

## 一、两条路，先选一条

| 要做的东西 | 用什么 | 关键动作 |
|---|---|---|
| 一套**页面**（封面、章节、内容页、结尾） | `frontend-slides` | 先出 3 个预览让眼睛选，再全量生成；每份都要嵌完整 `viewport-base.css` |
| 一张**图解**（流程、架构、对照、机制） | `visual-explainer` | 先 `visual-explainer_prepare` 拿流程建议，再 `visual-explainer_render_html` 出图 |
| PPTX → 网页 | `frontend-slides`（`html-template.md`；其 `scripts/extract-pptx.py` 未随本仓安装） | 抽取现场用 python-pptx 或从上游补装；`deploy.sh`/`export-pdf.sh` 是 bash 且同样未随装 |
| 要**可编辑 PPTX** 交付 | 先别做 | 要装 `alchaincyf/huashu-design`（仓库 229,769 KB），单独评估 |

## 二、本仓要改的上游默认

- **不要远端热链：** 字体、图片、图标一律入库相对引用；演示要能断网双击打开。
- **不要发明数字：** 页面上的每个数字来自讲解稿 md 或任务书，否则标 `模拟数据` 或 `⚠️ 待 Day1 现场确认`。
- **不要 AI 味模板：** 不许"居中大字 + 渐变背景 + 全部淡入"；一个强调色；正文 13–15px 以上，标题才上大字。
- **动画克制：** 动效只为讲清因果服务，每页最多一个主动画。
- **导出脚本是 bash：** `export-pdf.sh`、`deploy.sh` 在 Windows 上用 `bash`（WSL/Git Bash），别假设有 sh。

## 三、MCP（已装，已注册）

`visual-explainer` 自带 stdio-only 的本地 MCP server，暴露 `visual_explainer_prepare`、`visual_explainer_render_html` 两个工具，9 个命令模板作为 prompt，20 个只读资源。

**注册在 `.kilo/kilo.json`：**

```json
{
  "mcp": {
    "visual-explainer": {
      "type": "local",
      "command": [
        "node",
        "D:\\GitRepo-AI\\FDE20261023\\tools\\vendor\\visual-explainer\\node_modules\\visual-explainer\\plugins\\visual-explainer\\mcp\\server.mjs"
      ],
      "enabled": true,
      "timeout": 30000
    }
  }
}
```

- **运行时在上游原版里：** `tools/vendor/visual-explainer/` 用 `npm install --no-package-lock` 装了未改动的 `visual-explainer@0.14.0`。`.kilo/skills/visual-explainer/` 里的那份是 skill 文档、kit、references 与源码副本，**不直接运行**。
- **为什么运行时不在 `.kilo/` 里：** server.mjs 启动时读的是自己往上两级的 `package.json`（取 version），在 `.kilo/` 下那个路径是 `.kilo/package.json`——**Kilo 把 `.kilo/` 下任何 package.json 当配置校验并判为无效**，所以放不了。
- **写盘目录：** 默认 `~/.agent/diagrams/`，可用 `VISUAL_EXPLAINER_OUTPUT_DIR` 改。**本仓要显式指到项目内的目录**，别让它往用户主目录写。
- **安全边界（上游自己写的）：** 路径必须是 basename，拒绝目录穿越、控制字符、symlink 目标；`render` 默认 `open: false`。
- **不接也行：** 直接用 `SKILL.md` 和 `commands/` 里的模板，功能不缺。

## 四、验收的最小门槛

- [ ] **单文件、双击即开、无外链**（字体/图片本地化或内联）
- [ ] **内容与讲解稿 md 一致**，页面里没有另一套说法
- [ ] **数字有出处或标模拟**，企业事实标 `⚠️ 待 Day1 现场确认`
- [ ] **没有占位交付**：不许灰块、不许 lorem、不许死按钮
- [ ] **动画每页最多一个**，且不与口播打架
- [ ] **看过放大版截图**：文字没压边、没溢出、对比度够
- [ ] **交付说明写清**：哪些是模拟数据、哪些待现场确认、没做什么

## 五、什么时候**不**用

- 只是改 `problems/*-讲解稿.md` 的文字 → 直接改 md，页面由 `tools/video/make_html.py` 重新生成
- 要的是**视频** → 走 `hyperframes-video`，不是这个
- 要的是**平台界面假象**（像真软件的 dashboard）→ 走 `mock-devops-platform` + `ui-mockups`
- 要的是正式对外 PPTX → 走 Office 工具链，不是 HTML

## 六、来源

- `frontend-slides`（MIT，31,152★）、`visual-explainer`（MIT，10,608★），安装清单与 commit 见 `mock/学习笔记/03-幻灯片-HTML.md`
- 策展列表：`ToseaAI/awesome-html-slide-skills`（CC BY 4.0）
- 本仓纪律：`AGENTS.md` §13 硬性红线、§8 真源只有一份
