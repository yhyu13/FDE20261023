"""工作树助手。

并行开发的基础设施。出错时症状极难查——分支被换掉而不知道、
HEAD 被抽走、两个会话互相踩文件。所以**命名规则和路径推导必须被钉死**，
钉在测试里，不靠记性。

约定：

* 工作树目录 = 仓库名的兄弟目录 `<repo>-wt-<slug>`（与用户既有的
  `pbl-wt-ugc-moderation` 命名一致）
* 分支 = spec-kit 的约定 `NNN-slug`，因为 `check-prerequisites.ps1`
  **按分支名解析 `specs/NNN-slug/`**——两边对不上，工具就找不到 spec。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

__all__ = ["WorktreePlan", "plan_worktree", "render_commands", "slugify"]


@dataclass(frozen=True)
class WorktreePlan:
    path: Path
    branch: str
    slug: str
    feature_num: int
    spec_dir: Path
    base: str = "main"


def slugify(text: str) -> str:
    """把中文/长描述压成 spec-kit 认的 kebab-case 短名。"""
    cleaned = [c if (c.isascii() and (c.isalnum() or c in "-_")) else " " for c in text]
    parts = [p for p in "".join(cleaned).lower().split() if p]
    return "-".join(parts) or "feature"


def plan_worktree(
    repo_root: Path,
    *,
    feature_num: int,
    slug: str,
    base: str = "main",
) -> WorktreePlan:
    """算出一棵工作树该长在哪、叫什么分支。"""
    repo_root = Path(repo_root).resolve()
    branch = f"{feature_num:03d}-{slug}"
    path = repo_root.parent / f"{repo_root.name}-wt-{slug}"
    spec_dir = repo_root / "specs" / branch
    return WorktreePlan(
        path=path,
        branch=branch,
        slug=slug,
        feature_num=feature_num,
        spec_dir=spec_dir,
        base=base,
    )


def render_commands(plan: WorktreePlan) -> list[str]:
    """给出可以直接粘进终端的命令。"""
    return [
        f'git worktree add "{plan.path}" -b {plan.branch} {plan.base}',
        f'cd "{plan.path}"',
        (
            "powershell -ExecutionPolicy Bypass -File tools/seed_spec.py "
            f"-Number {plan.feature_num} -ShortName {plan.slug}"
        ),
        'git worktree list',
    ]
