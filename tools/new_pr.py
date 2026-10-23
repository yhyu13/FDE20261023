"""开一张本地 PR。

本地 PR = 仓内 `pr/NNN-slug.md` 一份描述 + 一个分支。
描述必须填全、必须过闸，才允许合并（`tools/merge_pr.py` 把关）。

用法：

    python tools/new_pr.py --Branch 004-quote-compare --Base main
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fde.localflow import next_number, render_pr  # noqa: E402

PR_DIR = ROOT / "pr"


def main() -> int:
    parser = argparse.ArgumentParser(description="开一张本地 PR")
    parser.add_argument("--Branch", required=True, help="源分支名，如 004-quote-compare")
    parser.add_argument("--Base", default="main", help="目标分支（默认 main）")
    parser.add_argument("--Slug", default="", help="PR 短名（默认取分支名）")
    parser.add_argument("--Number", type=int, default=0, help="编号（默认自动）")
    args = parser.parse_args()

    slug = args.Slug or re.sub(r"^\d{3}-", "", args.Branch)
    number = args.Number or next_number(PR_DIR, "pr")

    PR_DIR.mkdir(parents=True, exist_ok=True)
    path = PR_DIR / f"{number:03d}-{slug}.md"
    if path.exists():
        print(f"[ERR] {path.relative_to(ROOT)} 已存在", file=sys.stderr)
        return 2

    path.write_text(
        render_pr(number=number, slug=slug, branch=args.Branch, base=args.Base),
        encoding="utf-8",
    )

    print(f"[OK ] PR 描述：{path.relative_to(ROOT)}")
    print(f"     分支：{args.Branch} → {args.Base}")
    print()
    print("下一步：")
    print("  1. 填 PR 描述（⚠️ 待补的地方必须填完，别留占位符）")
    print(f"  2. python tools/merge_pr.py --Pr {path.relative_to(ROOT)}")
    print()
    print("提醒：合并前会检查两件事——PR 描述填没填全、全套闸过没过。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
