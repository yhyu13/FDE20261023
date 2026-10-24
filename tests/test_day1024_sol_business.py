"""FR-012–019：先收集标注，再识别传播关系；不以角色审批替代业务能力。"""

from __future__ import annotations

import pytest

from test_day1024_sol_roles import DEMO, cmd, login, released, snapshot, topic

pytest_plugins = ("test_day1024_sol_roles",)
pytestmark = pytest.mark.skipif(not DEMO.parent.is_dir(), reason="未附带演示资产，SKIP 不等于验收通过")

RAW = "示例公交项目车辆已交付。该批车辆配置盲区监测和驾驶辅助系统。仅适用于该批车辆，不代表无人驾驶。"


def collect(page, suffix=""):
    login(page, "content")
    result = cmd(
        page, "addSource", title="新增公交项目公开资料" + suffix,
        publisher="演示资料发布方（模拟）", date="2026-10-20", url="",
        location="本地脱敏样例 / 资料第1段" + suffix, rawText=RAW + suffix, kind="case",
    )
    assert result["ok"], result
    return snapshot(page)["sources"][-1]["id"]


def annotate(page, source_id):
    login(page, "content")
    assert cmd(page, "analyzeSource", sourceId=source_id)["ok"]
    return cmd(page, "annotateSource", sourceId=source_id, annotation={
        "productStatus": "资料披露车型", "capabilityType": "辅助驾驶", "evidenceStage": "交付有据",
        "audiences": ["公交运营商"], "capabilityIds": ["ADAS", "BLINDSPOT"],
        "fact": "该批车辆配置盲区监测和驾驶辅助系统。", "allowedClaim": "仅该批车辆具备报道披露的驾驶辅助配置。",
        "boundary": "仅该批次；不等于无人驾驶。", "caseName": "模拟公交交付项目",
    })


def source(page, source_id):
    return next(s for s in snapshot(page)["sources"] if s["id"] == source_id)


def confirm_source(page, source_id):
    assert annotate(page, source_id)["ok"]
    for role in ["tech", "project", "brand"]:
        login(page, role)
        assert cmd(page, "reviewSource", sourceId=source_id, decision="approve", reason="核对本版本职责范围")["ok"]


def test_fr_012_collection_validation_and_deduplication(page):
    source_id = collect(page)
    assert source(page, source_id)["status"] == "inbox"
    count = len(snapshot(page)["sources"])
    login(page, "content")
    assert not cmd(page, "addSource", title="重复资料", publisher="测试", date="未标日期", url="", location="重复出处", rawText=RAW, kind="case")["ok"]
    assert len(snapshot(page)["sources"]) == count
    assert not cmd(page, "addSource", title="不可信链接", publisher="测试", date="未标日期", url="javascript:alert(1)", location="", rawText=RAW, kind="case")["ok"]
    page.get_by_role("button", name="资料收集与标注", exact=True).click()
    assert page.get_by_role("button", name="收集新资料", exact=True).is_visible()
    assert "未自动抓取" in page.locator("main").inner_text()


def test_fr_013_suggestions_have_exact_original_locations_and_need_confirmation(page):
    source_id = collect(page)
    login(page, "content")
    assert cmd(page, "analyzeSource", sourceId=source_id)["ok"]
    s = source(page, source_id)
    assert s["proposal"]["facts"]
    for fact in s["proposal"]["facts"]:
        assert s["rawText"][fact["start"]:fact["end"]] == fact["text"]
        assert fact["location"]
    assert s["status"] != "confirmed"
    assert annotate(page, source_id)["ok"]
    s = source(page, source_id)
    assert s["status"] == "review"
    assert s["productStatus"] == "资料披露车型"
    assert s["capabilityType"] == "辅助驾驶"
    assert s["evidenceStage"] == "交付有据"


def test_fr_014_source_approval_is_role_and_version_bound(page):
    source_id = collect(page)
    assert annotate(page, source_id)["ok"]
    login(page, "dri")
    assert not cmd(page, "reviewSource", sourceId=source_id, decision="approve")["ok"]
    login(page, "tech")
    assert cmd(page, "reviewSource", sourceId=source_id, decision="approve")["ok"]
    assert source(page, source_id)["status"] != "confirmed"
    assert not cmd(page, "reviewSource", sourceId=source_id, decision="approve")["ok"]
    login(page, "project")
    assert cmd(page, "reviewSource", sourceId=source_id, decision="approve")["ok"]
    login(page, "brand")
    assert cmd(page, "reviewSource", sourceId=source_id, decision="approve")["ok"]
    assert source(page, source_id)["status"] == "confirmed"


def test_fr_015_source_update_invalidates_dependent_signatures(page):
    released(page)
    login(page, "content")
    before = source(page, "S06")["version"]
    assert cmd(page, "updateSource", sourceId="S06", rawText="新的资料原文：仅对应批次配置驾驶辅助，范围有更新。")["ok"]
    assert source(page, "S06")["version"] == before + 1
    assert source(page, "S06")["status"] == "inbox"
    assert topic(page)["stage"] == "draft"
    assert topic(page)["approvals"] == {}
    assert topic(page)["releasedVersion"] is None
    assert not cmd(page, "submit", topicId="T01")["ok"]


def test_fr_016_new_question_gets_explained_scenario_capability_case_theme(page):
    login(page, "sales")
    assert cmd(page, "addQuestion", ask="公交线路运营中，驾驶员关心盲区监测与环视辅助。", audience="公交运营商")["ok"]
    qid = snapshot(page)["questions"][-1]["id"]
    login(page, "content")
    assert cmd(page, "suggestRelations", questionId=qid)["ok"]
    relation = snapshot(page)["relations"][-1]
    assert relation["scenarioId"] == "blindspot"
    assert relation["matchedTerms"] and relation["capabilityIds"]
    assert relation["theme"] and relation["boundaries"]
    evidence = next(e for e in relation["evidence"] if e["sourceId"] == "S06")
    assert evidence["version"] == source(page, "S06")["version"]
    assert evidence["quote"] and evidence["location"] and evidence["reason"]
    assert evidence["caseName"] and evidence["caseStage"]
    assert relation["status"] == "suggested"


def test_fr_017_unknown_and_cost_questions_cannot_become_supported_claims(page):
    login(page, "content")
    assert cmd(page, "suggestRelations", questionId="CQ04")["ok"]
    r = snapshot(page)["relations"][-1]
    assert not r["evidence"]
    assert r["gaps"]
    assert not cmd(page, "confirmRelation", relationId=r["id"], theme="降本宣传", sourceIds=[], reason="希望推广")["ok"]
    login(page, "sales")
    assert cmd(page, "addQuestion", ask="客户询问完全未知的海底采矿装备", audience="行业伙伴")["ok"]
    qid = snapshot(page)["questions"][-1]["id"]
    login(page, "content")
    assert cmd(page, "suggestRelations", questionId=qid)["ok"]
    r = snapshot(page)["relations"][-1]
    assert r["scenarioId"] is None and not r["evidence"]
    sid = collect(page, "待审")
    assert cmd(page, "suggestRelations", questionId="CQ01")["ok"]
    assert sid not in [e["sourceId"] for e in snapshot(page)["relations"][-1]["evidence"]]


def test_fr_018_human_confirmation_then_dri_handoff(page):
    login(page, "sales")
    assert cmd(page, "addQuestion", ask="城间客户想区分 iEV12LE 与城市车型的适用范围", audience="海外客户")["ok"]
    qid = snapshot(page)["questions"][-1]["id"]
    login(page, "content")
    assert cmd(page, "suggestRelations", questionId=qid)["ok"]
    r = snapshot(page)["relations"][-1]
    login(page, "dri")
    assert not cmd(page, "planRelation", relationId=r["id"], week="W2")["ok"]
    login(page, "content")
    assert cmd(page, "confirmRelation", relationId=r["id"], theme="城市与城间的车型定位说明", sourceIds=["S10"], reason="保留展会发布边界，不宣称交付")["ok"]
    assert not cmd(page, "confirmRelation", relationId=r["id"], theme="重复确认", sourceIds=["S10"], reason="重复")["ok"]
    login(page, "dri")
    assert cmd(page, "planRelation", relationId=r["id"], week="W2")["ok"]
    assert not cmd(page, "planRelation", relationId=r["id"], week="W2")["ok"]
    t = snapshot(page)["topics"][-1]
    assert t["relationId"] == r["id"] and t["sourceIds"] == ["S10"]
    assert t["title"] == "城市与城间的车型定位说明"


def test_fr_019_relation_evidence_versions_persist_and_become_stale(page):
    sid = collect(page)
    confirm_source(page, sid)
    login(page, "sales")
    assert cmd(page, "addQuestion", ask="公交客户希望说明新批次的盲区辅助配置", audience="公交运营商")["ok"]
    qid = snapshot(page)["questions"][-1]["id"]
    login(page, "content")
    assert cmd(page, "suggestRelations", questionId=qid)["ok"]
    r = snapshot(page)["relations"][-1]
    assert sid in [e["sourceId"] for e in r["evidence"]]
    assert cmd(page, "confirmRelation", relationId=r["id"], theme="新批次驾驶辅助配置说明", sourceIds=[sid], reason="只用该资料已确认的范围")["ok"]
    login(page, "dri")
    assert cmd(page, "planRelation", relationId=r["id"], week="W3")["ok"]
    t = snapshot(page)["topics"][-1]
    assert t["relationId"] == r["id"]
    assert t["sourceVersions"][sid] == source(page, sid)["version"]
    assert t["sourceIds"] == [sid]
    assert t["scenarioId"] == "blindspot"
    page.reload()
    page.wait_for_function("window.Demo && Demo.ready")
    assert any(x["id"] == r["id"] for x in snapshot(page)["relations"])
    login(page, "content")
    assert cmd(page, "updateSource", sourceId=sid, rawText=RAW + "\n补充新资料说明。")["ok"]
    assert next(x for x in snapshot(page)["relations"] if x["id"] == r["id"])["status"] == "stale"
    login(page, "dri")
    assert not cmd(page, "planRelation", relationId=r["id"], week="W3")["ok"]
    assert r["id"] in page.evaluate("Demo.exportText()")


def test_fr_013_cannot_upgrade_delivery_evidence_into_operations(page):
    sid = collect(page)
    assert annotate(page, sid)["ok"]
    original = source(page, sid)
    annotation = {
        "productStatus": "资料披露车型", "capabilityType": "辅助驾驶", "evidenceStage": "运营有据",
        "audiences": ["公交运营商"], "capabilityIds": ["ADAS"],
        "fact": "该批车辆配置盲区监测和驾驶辅助系统。", "allowedClaim": "车辆已商业运营。",
        "boundary": "不能超出范围", "caseName": "伪造运营案例",
    }
    assert not cmd(page, "annotateSource", sourceId=sid, annotation=annotation)["ok"]
    assert source(page, sid)["version"] == original["version"]
    annotation["evidenceStage"] = "交付有据"
    annotation["fact"] = "该批车辆运营成本降低30%。"
    assert not cmd(page, "annotateSource", sourceId=sid, annotation=annotation)["ok"]


def test_fr_016_negated_keyword_is_not_confirmed_customer_interest(page):
    login(page, "sales")
    assert cmd(page, "addQuestion", ask="客户明确不需要盲区监测，本次只问空调能耗测算。", audience="公交运营商")["ok"]
    qid = snapshot(page)["questions"][-1]["id"]
    login(page, "content")
    assert cmd(page, "suggestRelations", questionId=qid)["ok"]
    r = snapshot(page)["relations"][-1]
    assert r["scenarioId"] != "blindspot"
    assert r["status"] != "confirmed"
    assert "规则模拟" in r["method"] and "非 AI 语义理解" in r["method"]
    assert "规则模拟" in page.evaluate("Demo.exportText()")


def test_fr_018_evidence_cannot_support_cost_or_operation_escalation(page):
    login(page, "content")
    assert cmd(page, "suggestRelations", questionId="CQ01")["ok"]
    r = snapshot(page)["relations"][-1]
    assert not cmd(page, "confirmRelation", relationId=r["id"], theme="驾驶辅助使运营成本降低30%", sourceIds=["S06"], reason="有资料编号")["ok"]
    assert cmd(page, "suggestRelations", questionId="CQ10")["ok"]
    r = snapshot(page)["relations"][-1]
    assert not cmd(page, "confirmRelation", relationId=r["id"], theme="RoboBus 已量产并商业运营", sourceIds=["S11"], reason="有合作报道")["ok"]


def test_fr_012_plain_text_import_and_unsupported_pdf_rejection(page):
    login(page, "content")
    page.get_by_role("button", name="资料收集与标注", exact=True).click()
    page.get_by_role("button", name="收集新资料", exact=True).click()
    page.get_by_label("导入 UTF-8 文本（TXT / MD / JSON）").set_input_files({
        "name": "sample.md", "mimeType": "text/markdown", "buffer": RAW.encode("utf-8"),
    })
    page.wait_for_function("document.querySelector('#collect-text').value.length > 10")
    assert page.get_by_label("正文（粘贴或文件导入）").input_value() == RAW
    page.get_by_label("导入 UTF-8 文本（TXT / MD / JSON）").set_input_files({
        "name": "fake.txt", "mimeType": "text/plain", "buffer": b"%PDF-1.7 fake payload",
    })
    page.wait_for_function("document.querySelector('#collect-file').value === ''")
    assert "未导入" in page.get_by_role("status").inner_text()


def test_fr_014_returned_annotation_edit_starts_a_new_version(page):
    sid = collect(page)
    assert annotate(page, sid)["ok"]
    login(page, "project")
    assert cmd(page, "reviewSource", sourceId=sid, decision="return", reason="请核对披露范围")["ok"]
    previous_version = source(page, sid)["version"]
    assert annotate(page, sid)["ok"]
    assert source(page, sid)["version"] == previous_version + 1
    assert source(page, sid)["approvals"] == {}


def test_fr_015_known_date_conflict_cannot_be_bypassed_by_direct_planning(page):
    login(page, "sales")
    assert cmd(page, "addQuestion", ask="海外客户想查看悉尼适配说明但日期有冲突", audience="海外客户", sourceIds=["S08"])["ok"]
    qid = snapshot(page)["questions"][-1]["id"]
    login(page, "dri")
    assert cmd(page, "planQuestion", questionId=qid, week="W3")["ok"]
    tid = snapshot(page)["topics"][-1]["id"]
    login(page, "content")
    assert not cmd(page, "submit", topicId=tid)["ok"]
