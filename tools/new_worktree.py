"""开一棵工作树。

**一棵树，一个会话。** 要并行就用工作树把两边分开——共享 `.git`，
文件目录各自独立，提交互不覆盖。

命名约定：

* 目录 = 仓库名的兄弟 `<repo>-wt-<slug>`
* 分支 = spec-kit 的 `NNN-slug`（因为 `check-prerequisites.ps1`
  **按分支名解析 `specs/NNN-slug/`**，两边对不上工具就找不到 spec）

用法：

    python tools/new_worktree.py -Feature 1 -ShortName repair-copilot
    python tools/new_worktree.py -Feature 1 -ShortName repair-copilot --DryRun
    python tools/new_worktree.py --List
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fde.worktree import plan_worktree, render_commands  # noqa: E402


def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)


def list_worktrees() -> int:
    proc = _run(["git", "worktree", "list"])
    print(proc.stdout.strip() or "(没有工作树)")
    count = len([ln for ln in proc.stdout.splitlines() if ln.strip()])
    print(f"\n共 {count} 棵。**一棵树，同一时间只允许一个会话在写。**")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="开一棵工作树")
    parser.add_argument("-Feature", type=int, help="题号（1-6）")
    parser.add_argument("-ShortName", help="spec-kit 短名，如 repair-copilot")
    parser.add_argument("--Base", default="main", help="基线分支（默认 main）")
    parser.add_argument("--DryRun", action="store_true", help="只打印命令，不执行")
    parser.add_argument("--List", action="store_true", help="列出当前工作树")
    args = parser.parse_args()

    if args.List:
        return list_worktrees()

    if not args.Feature or not args.ShortName:
        parser.error("需要 -Feature 与 -ShortName（或用 --List）")

    plan = plan_worktree(ROOT, feature_num=args.Feature, slug=args.ShortName, base=args.Base)
    commands = render_commands(plan)

    if args.DryRun:
        print("将要执行：")
        for cmd in commands:
            print(f"  {cmd}")
        return 0

    if plan.path.exists():
        print(f"[ERR] {plan.path} 已存在", file=sys.stderr)
        return 2

    proc = _run(["git", "worktree", "add", str(plan.path), "-b", plan.branch, args.Base])
    if proc.returncode != 0:
        print(f"[ERR] git worktree add 失败：\n{proc.stderr.strip()}", file=sys.stderr)
        return proc.returncode

    print(f"[OK ] 工作树：{plan.path}")
    print(f"     分支  ：{plan.branch}")
    print(f"     spec  ：{plan.spec_dir.relative_to(ROOT)}")
    print()
    print("接着执行：")
    for cmd in commands[1:]:
        print(f"  {cmd}")
    print()
    print("提醒：动手前先看三眼——")
    print("  git branch --show-current   # 我在哪个分支？")
    print("  git reflog -6               # 最近这些 commit 是我做的吗？")
    print("  git status --short          # 有没有别人的未跟踪文件？")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
