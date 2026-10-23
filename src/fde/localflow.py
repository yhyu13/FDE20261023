"""本地 issue / PR。

远程没建的时候，issue 和 PR 落在仓内目录里（`issues/`、`pr/`）。
**纪律一点不减**：PR 描述必须填全、必须能过闸、合并必须留痕。
只是载体从 GitHub 换成了仓库目录——将来建了远程，`gh issue create` /
`gh pr create` 直接接上，目录结构可平滑迁移。

最要紧的一条是 `check_pr_complete`：**PR 描述里的占位符没填完，就不许合。**
这是本地流程唯一能挡住"看起来很行、其实没验证"的地方。

**为什么值得单独写一个模块并给它写测试**：合并的判定逻辑如果散在脚本里，
它迟早会被改成一个"看起来差不多就放行"的判断。而这一条是整个流程的闸门。
"""

from __future__ import annotations

import re
from datetime import date

__all__ = [
    "PLACEHOLDERS",
    "REQUIRED_SECTIONS",
    "check_pr_complete",
    "next_number",
    "render_issue",
    "render_pr",
]

#: PR 描述里出现这些，就说明那段还是占位符，没真写。
PLACEHOLDERS = ("⚠️", "（贴", "______", "<!--", "TODO", "TBD", "待补")

#: (段标题前缀, 是否必须含 AC/FR 编号)
REQUIRED_SECTIONS: list[tuple[str, str | None]] = [
    ("动了什么", None),
    ("对应哪条 AC / FR", r"(?:AC|FR)-\d+"),
    ("测试证据", None),
    ("闸结果", None),
    ("没做什么", None),
]

_SECTION_RE = re.compile(r"^##\s+(.*)$", re.M)


def _sections(text: str) -> dict[str, str]:
    """把 `## 标题` 切成 {标题: 正文}。"""
    matches = list(_SECTION_RE.finditer(text or ""))
    out: dict[str, str] = {}
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        out[m.group(1).strip()] = text[m.end() : end]
    return out


def check_pr_complete(text: str) -> list[str]:
    """检查 PR 描述是否填全。返回问题列表；**空列表 = 通过**。"""
    sections = _sections(text)
    problems: list[str] = []

    for name, need_id in REQUIRED_SECTIONS:
        key = next((k for k in sections if k.startswith(name)), None)
        if key is None:
            problems.append(f"{name}：这一段没了")
            continue

        body = sections[key]

        if need_id and not re.search(need_id, body):
            problems.append(f"{name}：没有列出任何 AC-xxx / FR-xxx 编号")
            continue

        hit = next((ph for ph in PLACEHOLDERS if ph in body), None)
        if hit is not None:
            problems.append(f"{name}：还留着占位符「{hit}」")
            continue

        if not body.strip():
            problems.append(f"{name}：这一段是空的")

    return problems


def next_number(directory, prefix: str) -> int:
    """目录里下一个可用编号（从 1 起）。"""
    from pathlib import Path

    directory = Path(directory)
    if not directory.is_dir():
        return 1
    highest = 0
    pattern = re.compile(rf"^{re.escape(prefix)}-(\d{{3}})-")
    for path in directory.glob(f"{prefix}-*.md"):
        m = pattern.match(path.name)
        if m:
            highest = max(highest, int(m.group(1)))
    return highest + 1


def render_pr(*, number: int, slug: str, branch: str, base: str = "main") -> str:
    """生成 PR 描述模板。**刚生成的模板一定过不了 `check_pr_complete`**——否则闸形同虚设。"""
    return f"""# PR · {slug}

**编号**：{number:03d}
**分支**：`{branch}` → `{base}`
**创建**：{date.today().isoformat()}

> 本文件是**本地 PR**。填完之后跑：
> `uv run --group dev python tools/merge_pr.py --Pr pr/{number:03d}-{slug}.md`
> 它会先查 PR 描述填没填全、再跑全套闸，**两道都过才允许合并**。

## 动了什么

⚠️ 待补——一句话说清**为什么**要改，不写改了什么（diff 自己会说）。

## 对应哪条 AC / FR

⚠️ 待补——列出 AC-xxx / FR-xxx 编号。**没有编号的 PR 不许合。**

- FR-xxx

## 测试证据

⚠️ 待补——贴「哪条测试先红后绿」，不是「测试都过了」。

失败时（原因必须是「功能还没实现」，不是打错字）：

```
（贴失败输出）
```

转绿后：

```
（贴通过输出）
```

## 闸结果

```
（贴 python tools/run_all_gates.py 的输出）
```

有 SKIP 时请写明：**SKIP 不等于通过**。

## 举一反三

⚠️ 待补——这次复用了哪条 L3 机制？它还能一并解决什么？

- 复用的 L3 机制：
- 同族复用（还能解决）：

## 没做什么

⚠️ 待补——划范围是 FDE 的核心动作，「没做什么」比「做了什么」更能防扯皮。

- 

## 风险与兜底

⚠️ 待补——出错会怎样？兜底是什么？

- 

## 需要人点头的事

- [ ] 本 PR 涉及改验收标准 / 部署公网 / 打 tag / 删数据 / 合并共享分支，**已单独取得确认**
"""


def render_issue(*, kind: str, number: int, slug: str, title: str) -> str:
    """生成 issue 模板。"""
    kind_title = "功能 / 需求" if kind == "feature" else "缺陷"
    return f"""# [{kind_title}] {title}

**编号**：{number:03d}
**类型**：{kind}
**创建**：{date.today().isoformat()}

> 本文件是**本地 issue**。将来建了 GitHub 远程，可用 `gh issue create` 承接同样的内容。

## L2 能力缺口

⚠️ 待补——这次补的是哪条缺口？例：`L2-2 工单与手册不连通`

## L3 机制

⚠️ 待补——用哪条机制实现？例：`工单本体（Ontology 三步法）`

## 业务问题

⚠️ 待补——用业务语言说清「谁的什么问题」，附现场证据（照片 / 工单号 / 日志）。

## 范围

- 做什么：
- **不做什么**：

## 验收标准（AC）

⚠️ 待补——每条 AC 必须可判定，且有一条同名测试（名字以 `FR-xxx` 开头）。

- FR-xxx：

## 同族复用

⚠️ 待补——这个机制还能一并解决什么问题？

## 风险与兜底

⚠️ 待补——出错会怎样？怎么兜？

## 纪律确认

- [ ] 低置信度结果要走人工确认台，不会自动进主表
- [ ] 要签字的数字可溯源，LLM 不做算术
- [ ] 本单不涉及打 tag / 部署公网 / 删数据 / 改验收标准（涉及请另开单并先问）
"""
