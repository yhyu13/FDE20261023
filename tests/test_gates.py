"""闸的行为。闸决定代码能不能合，所以它的行为必须被钉死。

两条从真实事故里学来的硬规矩，在这里被固化成测试：

1. **SKIP 不是 OK。** 没跑的东西不许报绿。
2. **空跑不允许报绿。** 一个闸如果查了 0 个文件却说"已审"，
   它比没有这条闸更糟——因为它会在报告里写下"已审"。
"""

import pytest

from fde.gates import GateResult, fr_trace_gate, no_empty_scan


def test_missing_fr_test_is_a_failure():
    spec = "### Functional Requirements\n\n- **FR-001**: System MUST do a thing\n"
    tests = {"tests/test_x.py": "def test_something_else():\n    pass\n"}
    result = fr_trace_gate(spec, tests)
    assert result.status == "FAIL"
    assert "FR-001" in result.detail


def test_matching_fr_test_passes():
    spec = "### Functional Requirements\n\n- **FR-001**: System MUST do a thing\n"
    tests = {"tests/test_x.py": "def test_fr_001_does_a_thing():\n    pass\n"}
    result = fr_trace_gate(spec, tests)
    assert result.status == "OK"
    assert result.checked == 1


def test_spec_without_requirements_is_skipped_not_ok():
    """spec 还没写完时是 SKIP，不是 OK——否则空 spec 会把闸变绿。"""
    result = fr_trace_gate("# Feature Specification: x\n\n还没写需求。\n", {})
    assert result.status == "SKIP"
    assert result.checked == 0


def test_empty_scan_is_turned_red():
    """一个自称 OK 但什么都没查的闸，必须转红。"""
    self_reporting = GateResult(name="lint", status="OK", detail="全部通过", checked=0)
    fixed = no_empty_scan(self_reporting)
    assert fixed.status == "FAIL"
    assert "0" in fixed.detail


def test_non_empty_ok_stays_ok():
    result = GateResult(name="lint", status="OK", detail="全部通过", checked=3)
    assert no_empty_scan(result).status == "OK"


def test_skip_is_never_rewritten_to_ok():
    result = GateResult(name="test", status="SKIP", detail="没有测试", checked=0)
    assert no_empty_scan(result).status == "SKIP"


@pytest.mark.parametrize(
    ("status", "expected_exit"),
    [("OK", 0), ("FAIL", 1), ("SKIP", 0)],
)
def test_exit_code_only_fails_on_fail(status, expected_exit):
    from fde.gates import overall_exit_code

    results = [
        GateResult(name="a", status="OK", detail="", checked=1),
        GateResult(name="b", status=status, detail="", checked=1),
    ]
    assert overall_exit_code(results) == expected_exit
