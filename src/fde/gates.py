"""闸。机械拦截，不靠记性。

三条规矩，都是从真实事故里学来的：

1. **SKIP 不是 OK。** 没跑的东西不许报绿（否则新工作树在装依赖前会一直红，
   一条常红的闸等于没有闸）。
2. **空跑不允许报绿。** 闸如果查了 0 个文件却说"已审"，它比没有闸更糟——
   因为它会在报告里写下"已审"，而它一个字节都没查。
3. **退出码是唯一判据。** 输出文本是给人看的。
"""

from __future__ import annotations

import re
from dataclasses import dataclass

__all__ = [
    "GateResult",
    "OK",
    "FAIL",
    "SKIP",
    "fr_trace_gate",
    "no_empty_scan",
    "overall_exit_code",
]

OK = "OK"
FAIL = "FAIL"
SKIP = "SKIP"

_FR_RE = re.compile(r"\*\*(FR-\d{3})\*\*")


@dataclass(frozen=True)
class GateResult:
    """一条闸的结果。

    `checked` 是它**实际检查过的对象数**——用来识别"空跑"。
    """

    name: str
    status: str
    detail: str = ""
    checked: int = 0


def fr_trace_gate(spec_text: str, test_sources: dict[str, str]) -> GateResult:
    """每条 FR 必须有一条同名测试。

    同名规则：测试函数名以 `test_fr_001` 开头。
    对不上号的两边都要改，**不许留悬空的**。
    """
    frs = _FR_RE.findall(spec_text or "")
    if not frs:
        return GateResult("fr-trace", SKIP, "spec 里还没有 FR 条目，无从对账", 0)

    missing: list[str] = []
    for fr in frs:
        stem = "test_" + fr.lower().replace("-", "_")
        if not any(stem in src for src in test_sources.values()):
            missing.append(fr)

    if missing:
        return GateResult(
            "fr-trace",
            FAIL,
            f"{len(missing)}/{len(frs)} 条 FR 没有同名测试：{', '.join(missing)}",
            len(frs),
        )
    return GateResult("fr-trace", OK, f"{len(frs)} 条 FR 都有同名测试", len(frs))


def no_empty_scan(result: GateResult) -> GateResult:
    """自称 OK 但什么都没查的闸，转红。"""
    if result.status == OK and result.checked == 0:
        return GateResult(
            result.name,
            FAIL,
            f"{result.detail}（但它检查了 0 个文件——空跑不算通过）",
            0,
        )
    return result


def overall_exit_code(results: list[GateResult]) -> int:
    """只要有一条 FAIL 就非零。SKIP 不影响退出码，但结论行会写明。"""
    return 1 if any(r.status == FAIL for r in results) else 0
