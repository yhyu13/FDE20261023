"""从 `problems/` 的三层拆解树，生成 spec-kit 的 `spec.md`。

这是「拆解」与「SDD」之间唯一的桥。**拆解已经做完并冻结，spec 不重新发明它**，
只做搬运 + 补齐 spec-kit 要求而拆解里没有的三段（用户故事的行为描述 /
验收场景 / 实体的业务定义）——这三段必须由团队在 Day1 现场补，
AI 猜出来的验收场景不算验收标准。

用法：

    python tools/seed_spec.py -Number 1 -ShortName repair-copilot
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description="把题解的三层拆解灌进 spec-kit 的 spec.md")
    parser.add_argument("-Number", type=int, required=True, help="题号（1-6）")
    parser.add_argument("-ShortName", required=True, help="spec-kit 短名，如 repair-copilot")
    parser.add_argument("--NoBranch", action="store_true", help="不建分支，只写 spec.md")
    parser.add_argument("--Force", action="store_true", help="覆盖已存在的 spec.md")
    args = parser.parse_args()

    sys.path.insert(0, str(ROOT / "src"))
    from fde.specseed import find_problem_file, parse_problem, render_spec  # noqa: PLC0415

    problems_dir = ROOT / "problems"
    try:
        problem_file = find_problem_file(problems_dir, args.Number)
    except FileNotFoundError as exc:
        print(f"[ERR] {exc}", file=sys.stderr)
        return 2

    text = problem_file.read_text(encoding="utf-8")
    problem = parse_problem(text, source=f"problems/{problem_file.name}")

    if not problem.l1:
        print(f"[ERR] {problem_file.name} 里没解析到 L1 业务问题，题解格式可能变了", file=sys.stderr)
        return 2
    if not problem.l2:
        print(f"[ERR] {problem_file.name} 里没解析到 L2 子问题", file=sys.stderr)
        return 2

    branch = f"{args.Number:03d}-{args.ShortName}"
    spec_dir = ROOT / "specs" / branch
    spec_path = spec_dir / "spec.md"

    if spec_path.exists() and not args.Force:
        print(f"[ERR] {spec_path.relative_to(ROOT)} 已存在。要覆盖请加 --Force", file=sys.stderr)
        return 2

    spec_dir.mkdir(parents=True, exist_ok=True)
    spec_path.write_text(
        render_spec(problem, feature_num=args.Number, slug=args.ShortName),
        encoding="utf-8",
    )

    print(f"[OK ] spec: {spec_path.relative_to(ROOT)}")
    print(f"     来源: problems/{problem_file.name}")
    print(
        f"     解析: L2 {len(problem.l2)} 条 / L3 {len(problem.l3)} 条 / KR {len(problem.okr)} 条"
    )
    if problem.okr:
        guards = [k.id for k in problem.okr if k.is_guardrail]
        if guards:
            print(f"     护栏 KR: {', '.join(guards)}（已单独标注）")

    if not args.NoBranch:
        result = subprocess.run(
            ["git", "checkout", "-b", branch], cwd=ROOT, capture_output=True, text=True
        )
        if result.returncode == 0:
            print(f"[OK ] 分支: {branch}（已切换）")
        else:
            print(f"[WARN] 分支 {branch} 未创建：{result.stderr.strip()}")
            print("       手动执行：git checkout -b " + branch)
    else:
        print(f"     分支（未创建）: {branch}")

    print()
    print("下一步：")
    print("  1. 补 spec.md 里标 ⚠️ 的三段：用户故事行为、验收场景(Given/When/Then)、实体定义")
    print(f"  2. /speckit.plan  →  specs/{branch}/plan.md")
    print(f"  3. /speckit.tasks →  specs/{branch}/tasks.md")
    print("  4. /speckit.implement（每个任务走 TDD 红→绿→重构）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
