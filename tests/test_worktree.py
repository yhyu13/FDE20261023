"""工作树助手的行为。

工作树是并行开发的基础设施，出错时症状非常难查
（分支被换掉、HEAD 被抽走、两个会话互相踩文件）。
所以命名规则和路径推导必须被钉死。
"""

from pathlib import Path

from fde.worktree import plan_worktree, render_commands


def test_worktree_sits_beside_the_repo(tmp_path: Path):
    repo = tmp_path / "FDE训练营"
    repo.mkdir()
    plan = plan_worktree(repo, feature_num=1, slug="repair-copilot")
    assert plan.path.parent == repo.parent
    assert plan.path.name == "FDE训练营-wt-repair-copilot"


def test_branch_follows_the_spec_kit_convention(tmp_path: Path):
    repo = tmp_path / "FDE训练营"
    repo.mkdir()
    plan = plan_worktree(repo, feature_num=1, slug="repair-copilot")
    # spec-kit 按分支名解析 specs/NNN-slug/，两边必须对得上
    assert plan.branch == "001-repair-copilot"
    assert plan.spec_dir.parts[-2:] == ("specs", "001-repair-copilot")


def test_feature_numbers_are_zero_padded(tmp_path: Path):
    repo = tmp_path / "FDE训练营"
    repo.mkdir()
    plan = plan_worktree(repo, feature_num=12, slug="quotes")
    assert plan.branch == "012-quotes"
    assert plan.path.name == "FDE训练营-wt-quotes"


def test_rendered_commands_are_copy_pasteable(tmp_path: Path):
    repo = tmp_path / "FDE训练营"
    repo.mkdir()
    plan = plan_worktree(repo, feature_num=1, slug="repair-copilot")
    commands = render_commands(plan)
    assert any("git worktree add" in c for c in commands)
    assert any("-b 001-repair-copilot" in c for c in commands)
    assert any(str(plan.path) in c for c in commands)
