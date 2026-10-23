"""开一张本地 issue。

用法：

    python tools/new_issue.py --Kind feature --Title "报价归集管线" --Slug quote-pipeline
    python tools/new_issue.py --Kind bug --Title "台账合计与分项和对不上" --Slug sum-mismatch
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fde.localflow import next_number, render_issue  # noqa: E402

ISSUE_DIR = ROOT / "issues"


def _slugify(text: str) -> str:
    parts = re.findall(r"[A-Za-z0-9]+", text.lower())
    return "-".join(parts)[:40] or "issue"


def main() -> int:
    parser = argparse.ArgumentParser(description="开一张本地 issue")
    parser.add_argument("--Kind", choices=["feature", "bug"], required=True)
    parser.add_argument("--Title", required=True)
    parser.add_argument("--Slug", default="")
    parser.add_argument("--Number", type=int, default=0)
    args = parser.parse_args()

    slug = args.Slug or _slugify(args.Title)
    number = args.Number or next_number(ISSUE_DIR, args.Kind)

    ISSUE_DIR.mkdir(parents=True, exist_ok=True)
    path = ISSUE_DIR / f"{args.Kind}-{number:03d}-{slug}.md"
    if path.exists():
        print(f"[ERR] {path.relative_to(ROOT)} 已存在", file=sys.stderr)
        return 2

    path.write_text(
        render_issue(kind=args.Kind, number=number, slug=slug, title=args.Title),
        encoding="utf-8",
    )

    print(f"[OK ] issue：{path.relative_to(ROOT)}")
    print("     填完 ⚠️ 待补 的段落；这张 issue 会成为 spec 的输入。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
