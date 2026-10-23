"""合并前的最后一道关。

**两道都过才允许合并**：

1. PR 描述填全了（没有空段、没有占位符、列了 AC/FR 编号）
2. 全套闸没有 FAIL

用法：

    python tools/merge_pr.py --Pr pr/004-quote-compare.md          # 只检查
    python tools/merge_pr.py --Pr pr/004-quote-compare.md --Yes    # 检查通过就合并
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fde.localflow import check_pr_complete  # noqa: E402

PR_DIR = ROOT / "pr"


def _git(*args: str) -> subprocess.CompletedProcess[str]:
    # 显式指定 utf-8：Windows 默认按 GBK 解码子进程输出，
    # 而闸的输出里有中文 → UnicodeDecodeError 直接把把关流程炸掉。
    return subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace"
    )


def _current_branch() -> str:
    return _git("branch", "--show-current").stdout.strip()


def main() -> int:
    parser = argparse.ArgumentParser(description="合并前的最后一道关")
    parser.add_argument("--Pr", required=True, help="PR 描述文件路径")
    parser.add_argument("--Base", default="main", help="合并目标分支（默认 main）")
    parser.add_argument("--Yes", action="store_true", help="检查通过就真的合并")
    args = parser.parse_args()

    pr_path = (ROOT / args.Pr) if not Path(args.Pr).is_absolute() else Path(args.Pr)
    if not pr_path.is_file():
        print(f"[ERR] 找不到 PR 描述：{pr_path}", file=sys.stderr)
        return 2

    text = pr_path.read_text(encoding="utf-8")

    # ---- 关 1：PR 描述填全了没有 ----
    problems = check_pr_complete(text)
    print()
    print("关 1 · PR 描述完整性")
    if problems:
        for p in problems:
            print(f"  [缺] {p}")
        print(f"  → {len(problems)} 处没填完，**不许合**。")
    else:
        print("  [OK] 五段都填了，没有占位符，AC/FR 编号齐。")

    # ---- 关 2：全套闸 ----
    print()
    print("关 2 · 全套闸")
    gates = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "run_all_gates.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env={**__import__("os").environ, "PYTHONIOENCODING": "utf-8"},
    )
    print(gates.stdout.rstrip() or gates.stderr.rstrip())
    gate_ok = gates.returncode == 0

    if problems or not gate_ok:
        print()
        print("[FAIL] 有东西没过，**不许合**。")
        return 1

    # ---- 合并 ----
    branch = _current_branch()
    print()
    print(f"[OK ] 两道关都过。当前分支：{branch} → 合并目标：{args.Base}")
    if not args.Yes:
        print("     （这是演练。加 --Yes 才真的合并。）")
        return 0

    if branch != args.Base:
        print(f"[ERR] 合并要在 {args.Base} 上做，当前在 {branch}。", file=sys.stderr)
        return 2

    merge = _git("merge", "--no-ff", "-m", f"merge: {pr_path.stem}", args.Base)
    if merge.returncode != 0:
        print(f"[ERR] 合并失败：\n{merge.stderr.strip()}", file=sys.stderr)
        return merge.returncode

    archived = PR_DIR / "merged"
    archived.mkdir(exist_ok=True)
    pr_path.rename(archived / pr_path.name)
    print(f"[OK ] 已合并，PR 描述归档到 {archived.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
