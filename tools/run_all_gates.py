"""跑全套闸。**判断成败永远看退出码，不看输出文本。**

输出文本是给人看的；机器判断靠 `$LASTEXITCODE`（Windows）或退出码。

状态有三种：

* **OK** —— 跑了，通过
* **FAIL** —— 跑了，不通过 → 拦住
* **SKIP** —— **没跑**（缺依赖、还没有测试）→ 不是 FAIL，也不是 OK

> SKIP 必须在结论行写明「这不等于全部通过」。
> 把「没跑」写成「通过了」，是本项目最贵的病。

用法：

    python tools/run_all_gates.py
    python tools/run_all_gates.py --list
    python tools/run_all_gates.py --only fr-trace,test
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fde.gates import (  # noqa: E402
    FAIL,
    OK,
    SKIP,
    GateResult,
    fr_trace_gate,
    no_empty_scan,
    overall_exit_code,
)

BRANCH_RE = re.compile(r"^(\d{3}-[a-z0-9-]+)$")


def _current_branch() -> str:
    """当前分支名。

    CI 的 PR 检出是 detached HEAD，`git branch --show-current` 拿不到分支名——
    这时退回 `GITHUB_HEAD_REF`（GitHub 提供的 PR 源分支名），
    否则 CI 上 `spec` / `fr-trace` 两条闸会永远 SKIP，等于没有。
    """
    out = subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    branch = out.stdout.strip()
    if branch:
        return branch
    return (os.environ.get("GITHUB_HEAD_REF") or "").strip()


def _test_sources() -> dict[str, str]:
    sources: dict[str, str] = {}
    tests_dir = ROOT / "tests"
    if not tests_dir.is_dir():
        return sources
    for path in sorted(tests_dir.rglob("test_*.py")):
        try:
            sources[str(path.relative_to(ROOT))] = path.read_text(encoding="utf-8")
        except OSError:
            continue
    return sources


def gate_spec() -> GateResult:
    """当前分支是 feature 分支时，spec.md 必须存在。"""
    branch = _current_branch()
    match = BRANCH_RE.match(branch)
    if not match:
        return GateResult("spec", SKIP, f"当前不在 feature 分支（{branch or 'detached'}）", 0)
    spec_path = ROOT / "specs" / match.group(1) / "spec.md"
    if not spec_path.is_file():
        return GateResult("spec", FAIL, f"{spec_path.relative_to(ROOT)} 不存在", 0)
    text = spec_path.read_text(encoding="utf-8")
    if "FR-" not in text:
        return GateResult("spec", FAIL, f"{spec_path.relative_to(ROOT)} 里没有 FR 条目", 1)
    return GateResult("spec", OK, f"{spec_path.relative_to(ROOT)} 存在且有 FR", 1)


def gate_fr_trace() -> GateResult:
    """每条 FR 必须有一条同名测试。"""
    branch = _current_branch()
    match = BRANCH_RE.match(branch)
    spec_text = ""
    if match:
        spec_path = ROOT / "specs" / match.group(1) / "spec.md"
        if spec_path.is_file():
            spec_text = spec_path.read_text(encoding="utf-8")
    return fr_trace_gate(spec_text, _test_sources())


def gate_test() -> GateResult:
    """pytest 必须全绿。没有测试文件 = SKIP，不是 OK。"""
    tests_dir = ROOT / "tests"
    if not tests_dir.is_dir() or not any(tests_dir.rglob("test_*.py")):
        return GateResult("test", SKIP, "还没有测试文件", 0)
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode == 0:
        return GateResult("test", OK, "pytest 全绿", 1)
    tail = (proc.stdout or proc.stderr).strip().splitlines()
    detail = tail[-1] if tail else f"pytest 退出码 {proc.returncode}"
    return GateResult("test", FAIL, detail, 1)


def gate_lint() -> GateResult:
    """ruff 必须干净。"""
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "ruff", "check", "."],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except OSError as exc:  # pragma: no cover
        return GateResult("lint", SKIP, f"ruff 不可用：{exc}", 0)
    if proc.returncode == 0:
        return GateResult("lint", OK, "ruff 干净", 1)
    tail = (proc.stdout or proc.stderr).strip().splitlines()
    detail = tail[-1] if tail else f"ruff 退出码 {proc.returncode}"
    return GateResult("lint", FAIL, detail, 1)


GATES = {
    "spec": gate_spec,
    "fr-trace": gate_fr_trace,
    "test": gate_test,
    "lint": gate_lint,
}


def main() -> int:
    parser = argparse.ArgumentParser(description="跑全套闸")
    parser.add_argument("--list", action="store_true", help="只列不跑")
    parser.add_argument("--only", default="", help="只跑指定闸，逗号分隔")
    args = parser.parse_args()

    if args.list:
        for name in GATES:
            print(f"{name:10s} — {GATES[name].__doc__ or ''}")
        return 0

    selected = [n.strip() for n in args.only.split(",") if n.strip()] or list(GATES)
    unknown = [n for n in selected if n not in GATES]
    if unknown:
        print(f"[ERR] 未知闸：{', '.join(unknown)}", file=sys.stderr)
        return 2

    results: list[GateResult] = []
    for name in selected:
        try:
            result = GATES[name]()
        except Exception as exc:  # noqa: BLE001 - 闸自己崩了也必须留痕，不能静默
            result = GateResult(name, FAIL, f"闸自身抛异常：{exc!r}", 0)
        results.append(no_empty_scan(result))

    width = max(len(r.name) for r in results)
    print()
    print("闸".ljust(width + 2) + "状态    详情")
    print("-" * (width + 40))
    for r in results:
        print(f"{r.name.ljust(width)}  {r.status.ljust(7)} {r.detail}")

    failed = [r for r in results if r.status == FAIL]
    skipped = [r for r in results if r.status == SKIP]
    print()
    if failed:
        print(f"[FAIL] {len(failed)} 条闸不通过：{', '.join(r.name for r in failed)}")
    else:
        print("[OK  ] 没有闸不通过。")
    if skipped:
        print(
            f"[SKIP] {len(skipped)} 条闸没跑：{', '.join(r.name for r in skipped)}"
            "　——**这不等于全部通过**，去把它们跑起来。"
        )
    print()
    return overall_exit_code(results)


if __name__ == "__main__":
    raise SystemExit(main())
