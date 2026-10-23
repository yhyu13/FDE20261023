"""把 `problems/NN-*.md` 的三层拆解树灌进 spec-kit 的 `spec.md` 结构。

这是 "拆解" 与 "SDD" 之间唯一的桥。拆解已经在 `problems/` 里做完并冻结，
spec 不重新发明它——**只做搬运 + 补齐 spec-kit 要求而拆解里没有的三段**
（用户故事 / 验收场景 / Success Criteria 的可测化）。

设计约束：

* 吃的是**人写的 Markdown**，格式会漂。解析必须容错，但**不许静默丢内容**——
  丢一条 L3 就等于丢一条验收标准，而这种缺失在评审时看不出来。
* 护栏 KR 必须能被识别出来（`is_guardrail`），因为它在 spec 里要单独标注：
  只报好看的那条不算达标。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

__all__ = [
    "L2",
    "L3",
    "KR",
    "Problem",
    "parse_problem",
    "render_spec",
    "find_problem_file",
]

# ---------------------------------------------------------------- 数据结构


@dataclass(frozen=True)
class L2:
    """一条能力缺口。"""

    id: str
    title: str
    root_cause: str
    why: str


@dataclass(frozen=True)
class L3:
    """一条可复用机制。"""

    parent: str
    title: str
    how: str
    reuse: str


@dataclass(frozen=True)
class KR:
    """一条关键结果。"""

    id: str
    metric: str
    baseline: str
    target: str
    how_measure: str
    is_north_star: bool = False
    is_guardrail: bool = False


@dataclass
class Problem:
    """一道题的拆解结果。"""

    title: str = ""
    l1: str = ""
    l2: list[L2] = field(default_factory=list)
    l3: list[L3] = field(default_factory=list)
    okr: list[KR] = field(default_factory=list)
    count_note: str = ""
    components: list[str] = field(default_factory=list)
    source: str = ""


# ---------------------------------------------------------------- 解析


_CLEAN_RE = re.compile(r"\*\*(.+?)\*\*", re.S)
_INLINE_CODE_RE = re.compile(r"`([^`]+)`")
_L2_ROW_RE = re.compile(r"^\|\s*\*\*L2-(\d+)\*\*\s*\|")
_L3_ROW_RE = re.compile(r"^\|\s*(L2-\d+|横贯)\s*\|")
_KR_ROW_RE = re.compile(r"^\|\s*\*?\*?(KR\d+)")
_KR_ID_RE = re.compile(r"^(KR\d+)")


def _clean(cell: str) -> str:
    """去掉 markdown 强调/反引号，保留文字本身。"""
    text = cell.strip()
    text = _INLINE_CODE_RE.sub(r"\1", text)
    text = _CLEAN_RE.sub(r"\1", text)
    return text.strip().strip("|").strip()


def _cells(line: str) -> list[str]:
    body = line.strip()
    body = body[1:] if body.startswith("|") else body
    body = body[:-1] if body.endswith("|") else body
    return [_clean(c) for c in body.split("|")]


def _section(text: str, heading_re: str, level: int = 2) -> str:
    """截出一个章节的正文。

    `level` 是这个章节自身的级别：**只在遇到同级或更高级的标题时才截断**。
    小节（`###`）不截断——`## 五、OKR` 下面还有 `### O`，
    早先的版本把 `### O` 当成章节结束，整张 OKR 表被截成两个字符，
    Success Criteria 一条都没进 spec，而 spec 看起来是完整的。
    """
    pattern = re.compile(heading_re, re.M)
    match = pattern.search(text)
    if not match:
        return ""
    rest = text[match.end() :]
    nxt = re.search(rf"^#{{1,{level}}}\s", rest, re.M)
    return rest[: nxt.start()] if nxt else rest


def _l1_of(text: str) -> str:
    section = _section(text, r"^###\s*L1\s*业务问题.*$")
    for line in section.splitlines():
        line = line.strip()
        if line.startswith(">"):
            candidate = _clean(line.lstrip(">").strip())
            if candidate:
                return candidate
    return ""


def _l2_of(text: str) -> list[L2]:
    section = _section(text, r"^###\s*L2\s*子问题.*$", level=3)
    found: list[L2] = []
    for line in section.splitlines():
        if not _L2_ROW_RE.match(line.strip()):
            continue
        cells = _cells(line)
        if len(cells) < 4:
            continue
        found.append(
            L2(
                id=f"L2-{_L2_ROW_RE.match(line.strip()).group(1)}",
                title=cells[1],
                root_cause=cells[2],
                why=cells[3],
            )
        )
    return found


def _l3_of(text: str) -> list[L3]:
    section = _section(text, r"^###\s*L3\s*机制.*$", level=3)
    found: list[L3] = []
    for line in section.splitlines():
        if not _L3_ROW_RE.match(line.strip()):
            continue
        cells = _cells(line)
        if len(cells) < 4:
            continue
        found.append(
            L3(
                parent=cells[0],
                title=cells[1],
                how=cells[2],
                reuse=cells[3],
            )
        )
    return found


def _okr_of(text: str) -> list[KR]:
    section = _section(text, r"^##\s*五、OKR.*$", level=2)
    found: list[KR] = []
    for line in section.splitlines():
        if not _KR_ROW_RE.match(line.strip()):
            continue
        cells = _cells(line)
        if len(cells) < 5:
            continue
        raw_id = cells[0]
        id_match = _KR_ID_RE.match(raw_id)
        if not id_match:
            continue
        found.append(
            KR(
                id=id_match.group(1),
                metric=cells[1],
                baseline=cells[2],
                target=cells[3],
                how_measure=cells[4],
                is_north_star="北极星" in raw_id,
                is_guardrail="护栏" in raw_id,
            )
        )
    return found


def _count_note_of(text: str) -> str:
    for line in text.splitlines():
        if "L3 数量核对" in line:
            note = _clean(line)
            note = note.replace("L3 数量核对：", "").replace("L3 数量核对:", "")
            return note.strip("：: ")
    return ""


def _components_of(text: str) -> list[str]:
    """从「专项技术点」三层技术栈表的 L2 组件列抽候选实体。"""
    section = _section(text, r"^##\s*四、专项技术点.*$", level=2)
    seen: list[str] = []
    for line in section.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = _cells(stripped)
        if len(cells) < 3:
            continue
        domain, component = cells[0], cells[1]
        if domain in {"L1 技术域", "技术域"} or component in {"L2 组件", "组件", ""}:
            continue
        # 表格分隔行（全是横线）不是实体
        if set(component) <= set("-: "):
            continue
        if component not in seen:
            seen.append(component)
    return seen


def _title_of(text: str) -> str:
    for line in text.splitlines():
        if line.startswith("# "):
            head = line[2:].strip()
            if "|" in head:
                return head.split("|")[-1].strip()
            return head
    return ""


def parse_problem(text: str, source: str = "") -> Problem:
    """把一篇题解解析成 `Problem`。"""
    return Problem(
        title=_title_of(text),
        l1=_l1_of(text),
        l2=_l2_of(text),
        l3=_l3_of(text),
        okr=_okr_of(text),
        count_note=_count_note_of(text),
        components=_components_of(text),
        source=source,
    )


def find_problem_file(problems_dir: Path, number: int) -> Path:
    """按题号找到题解文件（`NN-xxx.md`）。

    `problems/` 里同题号还有一份 `-讲解稿.md`（讲分镜的稿子，不是拆解树）。
    字典序上 `-讲解稿` 排在 `.md` 前面，不排除掉就会取错文件——
    讲解稿里没有 L1 业务问题，解析出来是空的。
    """
    prefix = f"{number:02d}-"
    matches = sorted(
        p for p in problems_dir.glob("*.md") if p.name.startswith(prefix) and "讲解稿" not in p.stem
    )
    if not matches:
        raise FileNotFoundError(f"在 {problems_dir} 里找不到题号 {number} 的题解")
    return matches[0]


# ---------------------------------------------------------------- 渲染


def _priority(index: int) -> str:
    return f"P{index + 1}"


def render_spec(
    problem: Problem,
    *,
    feature_num: int,
    slug: str,
    title: str = "",
    created: str | None = None,
) -> str:
    """渲染成 spec-kit 的 `spec.md`。

    只搬运已冻结的拆解，**并把三段拆解里没有的东西显式标成待补**：
    用户故事的行为描述、验收场景的 Given/When/Then、实体的业务定义。
    这三段必须由团队在 Day1 现场补——AI 猜出来的验收场景不算验收标准。
    """
    branch = f"{feature_num:03d}-{slug}"
    heading = title or problem.title
    created = created or date.today().isoformat()

    out: list[str] = []
    out.append(f"# Feature Specification: {heading}")
    out.append("")
    out.append(f"**Feature Branch**: `{branch}`")
    out.append("")
    out.append(f"**Created**: {created}")
    out.append("")
    out.append("**Status**: Draft")
    out.append("")
    out.append(f"**Input**: {problem.l1}")
    out.append("")
    if problem.source:
        out.append(f"**Source**: `{problem.source}`（三层拆解树，已冻结；本文件是它的 spec-kit 形态）")
        out.append("")
    out.append("> ⚠️ **本文件由 `tools/seed_spec.py` 从题解生成。**")
    out.append("> 重新生成会**覆盖**下面的手改内容——手改请改题解，或在生成后另存为 `spec.local.md`。")
    out.append("")

    # --- 用户故事 ---
    out.append("## User Scenarios & Testing *(mandatory)*")
    out.append("")
    out.append("> 每条用户故事对应**一个 L2 能力缺口**，按优先级排序；")
    out.append("> 独立实现其中任意一条，都应该能独立演示、独立验收。")
    out.append("")
    for i, gap in enumerate(problem.l2):
        out.append(f"### User Story {i + 1} - {gap.title} (Priority: {_priority(i)})")
        out.append("")
        out.append(f"**业务问题**：{problem.l1}")
        out.append("")
        out.append(f"**根因**：{gap.root_cause}")
        out.append("")
        out.append(f"**为什么值得做**：{gap.why}")
        out.append("")
        out.append("**Independent Test**: ⚠️ 待补——写清「怎么单独验收这一条」，以及「只实现这一条时交付什么」。")
        out.append("")
        out.append("**Acceptance Scenarios**: ⚠️ 待补——Day1 现场按真实业务动作补 Given/When/Then。")
        out.append("")
        out.append("---")
        out.append("")

    # --- 边界情况 ---
    out.append("### Edge Cases")
    out.append("")
    out.append("> ⚠️ 待补。至少覆盖三类：**输入缺失**（数据没到齐怎么办）、")
    out.append("> **低置信**（模型不确定怎么办）、**越权**（不该自动做的动作怎么办）。")
    out.append("")

    # --- 需求 ---
    out.append("## Requirements *(mandatory)*")
    out.append("")
    out.append("### Functional Requirements")
    out.append("")
    out.append("> 每条 FR 来自一条 **L3 机制**，并注明它属于哪个 L2 缺口。")
    out.append("> 凡是**要签字的数字与参数**，FR 必须写明溯源要求；")
    out.append("> 凡是**低置信结果**，FR 必须写明人工确认要求。")
    out.append("")
    fr_no = 0
    for gap in problem.l2:
        mechanisms = [m for m in problem.l3 if m.parent == gap.id]
        for mech in mechanisms:
            fr_no += 1
            out.append(f"- **FR-{fr_no:03d}**: System MUST {mech.how}")
            out.append(f"  - 来源：L2 {gap.id} / L3 {mech.title}")
            # 同族复用必须一起搬过来：它在题解里是「举一反三」的载体，
            # 丢在这里，下游就再也看不到这条机制还能干什么。
            out.append(f"  - 同族复用：{mech.reuse}")
    # 跨 L2 的横贯机制（如「回写闭环 + 闭环即评测」）同样是需求，一并落成 FR。
    for mech in [m for m in problem.l3 if m.parent == "横贯"]:
        fr_no += 1
        out.append(f"- **FR-{fr_no:03d}**: System MUST {mech.how}")
        out.append(f"  - 来源：横贯 / L3 {mech.title}")
        out.append(f"  - 同族复用：{mech.reuse}")
    out.append("")

    # --- 实体 ---
    out.append("### Key Entities")
    out.append("")
    if problem.components:
        out.append("> 候选实体（由「专项技术点」三层技术栈的 L2 组件列抽取）——**Day2 由团队校正**，")
        out.append("> 实体定义必须是业务语言，不是表名。")
        out.append("")
        for comp in problem.components:
            out.append(f"- **{comp}**: ⚠️ 待补业务定义与关键属性（不写实现细节）")
    else:
        out.append("- ⚠️ 待补：先定义业务对象（用业务语言，不是表名），再定字段。")
    out.append("")

    # --- 成功标准 ---
    out.append("## Success Criteria *(mandatory)*")
    out.append("")
    out.append("### Measurable Outcomes")
    out.append("")
    out.append("> 目标值来自题解的 OKR。**基线为 `Day1 实测` 的条目，在实测前不构成承诺。**")
    out.append("> 没有权威测评的指标一律标「我方验收目标（非业界实测）」。")
    out.append("")
    for i, kr in enumerate(problem.okr):
        flags = []
        if kr.is_north_star:
            flags.append("**北极星**")
        if kr.is_guardrail:
            flags.append("**护栏**")
        tag = ("　" + "·".join(flags)) if flags else ""
        out.append(
            f"- **SC-{i + 1:03d}**: {kr.metric} → 目标 {kr.target}"
            f"（基线：{kr.baseline}；怎么量：{kr.how_measure}）{tag}"
        )
    out.append("")
    if problem.count_note:
        out.append(f"> 拆解计数核对：{problem.count_note}")
        out.append("")

    # --- 假设 ---
    out.append("## Assumptions")
    out.append("")
    out.append("> 以下是拆解阶段明确**尚未确认**的部分，必须在 Day1 现场逐条落实；")
    out.append("> 未落实前，不得按它们写代码。")
    out.append("")
    out.append("- ⚠️ 客户侧数据规模、频次与口径：**Day1 实测确认**")
    out.append("- ⚠️ 现有系统与数据能否互通：**Day1 现场确认**")
    out.append("- ⚠️ 合规红线与验收标准由谁签字：**Day1 现场确认**")
    out.append("- ⚠️ 内网/离线部署条件与可用推理资源：**Day1 现场确认**")
    out.append("")

    return "\n".join(out) + "\n"
