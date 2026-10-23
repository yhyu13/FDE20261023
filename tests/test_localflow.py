"""本地 issue / PR 的行为。

远程没建的时候，issue 和 PR 就落在仓内目录里（`issues/`、`pr/`）。
**纪律一点不减**：PR 描述必须填全、必须能过闸、合并必须留痕。
只是载体从 GitHub 换成了仓库目录——将来建了远程，`gh issue create` /
`gh pr create` 直接接上，目录结构可平滑迁移。

最要紧的一条是 `check_pr_complete`：**PR 描述里的占位符没填完，就不许合。**
这是本地流程唯一能挡住"看起来很行、其实没验证"的地方。
"""

import pytest

from fde.localflow import check_pr_complete, next_number, render_pr

COMPLETE_PR = """# PR · 报价归集管线

**分支**：`004-quote-compare` → `main`

## 动了什么

把报价单解析成统一行结构，保留源定位。

## 对应哪条 AC / FR

- FR-001

## 测试证据

失败时：

```
E   assert 0 == 1
```

转绿后：

```
1 passed
```

## 闸结果

```
test  OK
lint  OK
```

## 没做什么

- 没做扫描件 OCR
"""


def test_complete_pr_passes():
    assert check_pr_complete(COMPLETE_PR) == []


def test_missing_section_is_reported():
    text = COMPLETE_PR.replace("## 没做什么\n\n- 没做扫描件 OCR\n", "")
    problems = check_pr_complete(text)
    assert any("没做什么" in p for p in problems)


def test_unfilled_placeholder_is_reported():
    """还留着「⚠️ 待补」就说明没写——这是最常见的一种假装写完了。"""
    text = COMPLETE_PR.replace("- FR-001", "- ⚠️ 待补：还没定")
    problems = check_pr_complete(text)
    assert problems


def test_empty_section_is_reported():
    text = COMPLETE_PR.replace("## 动了什么\n\n把报价单解析成统一行结构，保留源定位。\n", "## 动了什么\n\n\n")
    problems = check_pr_complete(text)
    assert any("动了什么" in p for p in problems)


def test_missing_ac_reference_is_reported():
    text = COMPLETE_PR.replace("- FR-001", "- 还没定")
    problems = check_pr_complete(text)
    assert any("AC" in p or "FR" in p for p in problems)


def test_missing_test_evidence_is_reported():
    text = COMPLETE_PR.replace("失败时：\n\n```\nE   assert 0 == 1\n```", "失败时：\n\n（贴失败输出）")
    problems = check_pr_complete(text)
    assert any("测试证据" in p for p in problems)


def test_next_number_is_monotonic(tmp_path):
    assert next_number(tmp_path, "pr") == 1
    (tmp_path / "pr-001-thing.md").write_text("x", encoding="utf-8")
    assert next_number(tmp_path, "pr") == 2


def test_render_pr_contains_the_required_sections():
    text = render_pr(number=4, slug="quote-compare", branch="004-quote-compare", base="main")
    for heading in ("## 动了什么", "## 对应哪条 AC / FR", "## 测试证据", "## 闸结果", "## 没做什么"):
        assert heading in text


def test_rendered_pr_does_not_pass_completeness():
    """刚生成的模板**必须**过不了检查——否则闸形同虚设。"""
    text = render_pr(number=1, slug="x", branch="001-x", base="main")
    assert check_pr_complete(text) != []


def test_html_comment_is_treated_as_placeholder():
    text = COMPLETE_PR.replace("把报价单解析成统一行结构，保留源定位。", "<!-- 写清楚 -->")
    problems = check_pr_complete(text)
    assert problems


@pytest.mark.parametrize("marker", ["⚠️", "（贴", "______"])
def test_known_placeholders_are_caught(marker):
    text = COMPLETE_PR.replace("把报价单解析成统一行结构，保留源定位。", marker)
    assert check_pr_complete(text)
