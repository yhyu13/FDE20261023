"""`seed_spec` 的解析与渲染。

这个模块把 `problems/NN-*.md` 的三层拆解树灌进 spec-kit 的 `spec.md` 结构。
它是 "拆解" 与 "SDD" 之间唯一的桥——所以它的行为必须被钉死。

为什么值得单独测：解析器吃的是人写的 Markdown，格式会漂。
一旦它悄悄多解析出一行、或把护栏 KR 漏掉，spec 就会少一条验收标准，
而这种缺失在评审时**看不出来**（spec 看起来是完整的）。
"""

import pytest

from fde.specseed import find_problem_file, parse_problem, render_spec

SAMPLE = """# 题 01 · 申沃客车 | 现场报修了，为什么还要从头查起？

## 二、三层拆解树

### L1 业务问题

> **现场报修了，为什么还要从头查起？**

### L2 子问题（4 条能力缺口）

| # | L2 子问题（缺口） | 根因 | 为何值得做 |
|---|------------------|------|-----------|
| **L2-1** | **经验只存在于人脑** | 老师傅的排查顺序是口述的隐性知识 | 对应业务目标里的工匠经验复用 |
| **L2-2** | **工单与手册不连通** | 现象、码、部件各自成表 | 跨车型串检是真实事故风险 |

### L3 机制（每个 L2 对应 2–3 条，全部标同族复用）

| 对应 L2 | L3 机制 | 怎么落地 | 同族复用（举一反三） |
|---------|---------|----------|----------------------|
| L2-1 | **经验条目化工作台** | 口述 → AI 代拟 → 老师傅只做确认 | 工艺规程 · 质检判据 |
| L2-2 | **工单本体** | Objects → Links → Actions | 通用对象模型 |

> **L3 数量核对**：L2-1 → 2 条，L2-2 → 1 条。

## 五、OKR

| KR | 指标 | 基线 | 目标 | 怎么量 |
|----|------|------|------|--------|
| **KR1（北极星）** | **首次诊断命中率** | Day1 实测 | **≥ 70%** | 历史工单回测 |
| KR2 | 获取排障信息耗时 | Day1 实测 | **≤ 2 分钟** | 现场计时 |
| **KR7（护栏）** | 二次上门率 | Day1 实测 | **不高于基线** | 闭环数据回看 |
"""


@pytest.fixture
def problem():
    return parse_problem(SAMPLE)


def test_l1_is_the_original_question(problem):
    assert problem.l1 == "现场报修了，为什么还要从头查起？"


def test_l2_are_gaps_not_symptoms(problem):
    assert len(problem.l2) == 2
    assert problem.l2[0].id == "L2-1"
    assert problem.l2[0].title == "经验只存在于人脑"
    assert "口述的隐性知识" in problem.l2[0].root_cause
    assert "工匠经验复用" in problem.l2[0].why


def test_l3_are_grouped_under_their_l2(problem):
    assert len(problem.l3) == 2
    assert problem.l3[0].parent == "L2-1"
    assert problem.l3[0].title == "经验条目化工作台"
    assert problem.l3[0].reuse == "工艺规程 · 质检判据"
    assert problem.l3[1].parent == "L2-2"


def test_okr_keeps_north_star_and_guardrail_apart(problem):
    assert len(problem.okr) == 3
    assert problem.okr[0].is_north_star is True
    assert problem.okr[0].target == "≥ 70%"
    # 护栏 KR 不能被当成普通支撑指标丢掉
    guardrails = [k for k in problem.okr if k.is_guardrail]
    assert len(guardrails) == 1
    assert guardrails[0].id == "KR7"
    assert guardrails[0].target == "不高于基线"


def test_render_emits_all_mandatory_sections(problem):
    out = render_spec(problem, feature_num=1, slug="repair-copilot", title="现场报修协同助手")
    for heading in (
        "## User Scenarios & Testing",
        "## Requirements",
        "### Functional Requirements",
        "### Key Entities",
        "## Success Criteria",
        "### Measurable Outcomes",
        "## Assumptions",
    ):
        assert heading in out, f"缺章节：{heading}"


def test_render_keeps_the_three_layers_visible(problem):
    out = render_spec(problem, feature_num=1, slug="repair-copilot", title="现场报修协同助手")
    assert "L2-1" in out
    assert "经验条目化工作台" in out
    # 同族复用必须进 spec，否则"举一反三"在下游断了
    assert "工艺规程" in out


def test_render_numbers_requirements_and_criteria(problem):
    out = render_spec(problem, feature_num=1, slug="repair-copilot", title="现场报修协同助手")
    assert "FR-001" in out
    assert "FR-002" in out
    assert "SC-001" in out
    assert "SC-003" in out


def test_render_marks_the_guardrail_criterion(problem):
    out = render_spec(problem, feature_num=1, slug="repair-copilot", title="现场报修协同助手")
    assert "护栏" in out
    assert "不高于基线" in out


def test_render_records_the_feature_branch(problem):
    out = render_spec(problem, feature_num=1, slug="repair-copilot", title="现场报修协同助手")
    assert "001-repair-copilot" in out


def test_table_separator_row_is_not_an_entity():
    """表格分隔行（全是横线）不能被当成实体——它会变成一个叫 `---------` 的假实体。"""
    md = """## 四、专项技术点（三层技术栈）

| L1 技术域 | L2 组件 | L3 实现要点 |
|-----------|---------|-----------|
| **数据接入** | 素材接入层 | 说明 |
| | 检索索引 | 说明 |
"""
    p = parse_problem(md)
    assert "---------" not in p.components
    assert "素材接入层" in p.components


def test_render_has_no_pseudo_entity():
    md = """## 四、专项技术点（三层技术栈）

| L1 技术域 | L2 组件 | L3 实现要点 |
|-----------|---------|-----------|
| **数据接入** | 素材接入层 | 说明 |
"""
    p = parse_problem(md)
    out = render_spec(p, feature_num=1, slug="x", title="t")
    assert "**---------**" not in out


def test_okr_section_survives_a_subheading():
    """`## 五、OKR` 下面还有 `### O` 小节——小节不能把表格截断掉。

    这条曾经真炸过：章节提取把 `### O` 当成章节结束，
    于是整张 OKR 表被截成两个字符，**Success Criteria 一条都没进 spec**，
    而 spec 看起来是完整的。
    """
    md = """## 五、OKR

### O

> 目标

| KR | 指标 | 基线 | 目标 | 怎么量 |
|----|------|------|------|--------|
| **KR1（北极星）** | 命中率 | Day1 实测 | **≥ 70%** | 回测 |
| **KR2（护栏）** | 二次上门率 | Day1 实测 | **不高于基线** | 闭环回看 |
"""
    p = parse_problem(md)
    assert len(p.okr) == 2
    assert p.okr[0].is_north_star is True
    assert p.okr[1].is_guardrail is True


def test_cross_cutting_mechanism_is_not_dropped():
    """「横贯」那一行是跨 L2 的机制，丢了它就少一条验收标准。"""
    md = """### L3 机制（每个 L2 对应 2–3 条）

| 对应 L2 | L3 机制 | 怎么落地 | 同族复用（举一反三） |
|---------|---------|----------|----------------------|
| L2-1 | **经验条目化工作台** | 口述 → 确认 | 工艺规程 |
| 横贯 | **确认闭环 + 闭环即评测** | 回写即评测 | 合同审核 |
"""
    p = parse_problem(md)
    assert len(p.l3) == 2
    assert p.l3[1].parent == "横贯"
    assert p.l3[1].title == "确认闭环 + 闭环即评测"

    out = render_spec(p, feature_num=1, slug="repair-copilot", title="x")
    assert "确认闭环 + 闭环即评测" in out
    assert "合同审核" in out


def test_problem_file_lookup_ignores_the_script_file(tmp_path):
    """讲解稿和题解同题号，`-讲解稿` 在字典序里排在 `.md` 前面。

    取错文件的后果很隐蔽：讲解稿里没有 L1 业务问题，`seed_spec` 直接报错退出，
    spec 停在旧版本；而人只看"spec 存在"，看不出它已经过期。
    """
    script = tmp_path / "02-某某企业-某某场景-讲解稿.md"
    problem_file = tmp_path / "02-某某企业-某某场景.md"
    script.write_text("# 讲解稿", encoding="utf-8")
    problem_file.write_text("# 题解", encoding="utf-8")

    assert find_problem_file(tmp_path, 2) == problem_file
