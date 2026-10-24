"""FR-001–010：day1024_prd_v1 单文件产品原型的行为验收。"""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "assets/day1024_prd_v1/index.html"


@pytest.fixture
def page():
    assert DEMO.is_file(), "FR 成品尚未实现：缺少 assets/day1024_prd_v1/index.html"
    api = pytest.importorskip("playwright.sync_api", reason="需要 Playwright；SKIP 不等于通过")
    with api.sync_playwright() as driver:
        browser = driver.chromium.launch()
        context = browser.new_context(offline=True, viewport={"width": 1440, "height": 1000})
        tab = context.new_page()
        errors, requests = [], []
        tab.on("pageerror", lambda error: errors.append(str(error)))
        tab.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
        tab.on("request", lambda req: requests.append(req.url) if req.url.startswith("http") else None)
        tab.goto(DEMO.as_uri())
        tab.wait_for_function("window.PRD && window.PRD.ready")
        yield tab
        assert not errors, errors
        assert not requests, requests
        context.close()
        browser.close()


def state(page):
    return page.evaluate("PRD.state()")


def command(page, action, **payload):
    return page.evaluate(
        "p => PRD.command(p.action, p.payload)", {"action": action, "payload": payload}
    )


def login(page, role):
    assert command(page, "login", role=role)["ok"]


def topic(page, topic_id="T01"):
    return next(t for t in state(page)["topics"] if t["id"] == topic_id)


def release_t01(page):
    login(page, "content")
    assert command(page, "submit", topicId="T01")["ok"]
    for role in ("tech", "project", "brand"):
        login(page, role)
        assert command(page, "approve", topicId="T01", decision="approve", reason="核对当前版本")["ok"]
    login(page, "dri")
    assert command(page, "release", topicId="T01")["ok"]


def test_fr_001_overview_counts_come_from_source_package(page):
    data = state(page)
    assert len(data["sources"]) == 11
    assert len(data["questions"]) == 12
    assert len(data["reviews"]) == 5
    assert {t["week"] for t in data["topics"]} == {"W1", "W2", "W3", "W4"}
    assert page.get_by_role("heading", name="11 月内容作战图", exact=True).is_visible()


def test_fr_002_explained_match_and_missing_cost_evidence(page):
    assert command(page, "match", questionId="CQ01")["ok"]
    relation = next(r for r in state(page)["relations"] if r["questionId"] == "CQ01")
    assert relation["scenario"] == "盲区与驾驶辅助"
    assert relation["sourceIds"] == ["S06"]
    assert relation["caseStage"] == "特定项目交付"
    assert relation["theme"] and relation["boundary"]
    assert command(page, "match", questionId="CQ04")["ok"]
    gap = next(r for r in state(page)["relations"] if r["questionId"] == "CQ04")
    assert not gap["sourceIds"] and gap["gaps"]
    assert not command(page, "createTopic", questionId="CQ04", week="W4")["ok"]


def test_fr_003_four_channels_and_picture_rights_gate(page):
    login(page, "content")
    for channel in ("公众号", "官网", "展会", "销售推介"):
        assert command(page, "generate", topicId="T01", channel=channel)["ok"]
        draft = topic(page)
        assert draft["channel"] == channel
        assert "S06" in draft["body"]
        assert "https://www.sunwinbus.com/cn/news/details/509" in draft["body"]
        assert "2025-11-26" in draft["body"] and "2026-10-23" in draft["body"]
        assert "内部备注" not in draft["body"]
    assert command(page, "selectPicture", topicId="T01", pictureId="PIC04")["ok"]
    denied = command(page, "submit", topicId="T01")
    assert not denied["ok"] and "授权" in denied["message"]
    assert command(page, "selectPicture", topicId="T01", pictureId=None)["ok"]
    assert command(page, "generate", topicId="T01", channel="短视频")["ok"] is False


def test_fr_004_revision_history_and_approved_claims(page):
    login(page, "content")
    assert command(page, "reviseDraft")["ok"]
    assert state(page)["draftVersion"] == "0.2"
    assert "已经实现量产" in state(page)["draftHistory"][0]["body"]
    claims = {c["id"]: c for c in state(page)["claims"]}
    assert set(claims) == {"P01", "P02", "P03"}
    assert claims["P01"]["version"] == "1.0"
    assert "不足以证明" not in claims["P01"]["text"]
    assert "现有资料未提供量产或商业运营的证据" in claims["P01"]["text"]


def test_fr_005_role_and_sequence_guards_do_not_mutate(page):
    login(page, "sales")
    before = topic(page)
    assert not command(page, "release", topicId="T01")["ok"]
    assert topic(page) == before
    login(page, "brand")
    assert not command(page, "approve", topicId="T01", decision="approve")["ok"]
    login(page, "content")
    assert command(page, "submit", topicId="T01")["ok"]
    login(page, "tech")
    assert not command(page, "approve", topicId="T01", decision="return", reason="")["ok"]
    assert command(page, "approve", topicId="T01", decision="return", reason="补充批次边界")["ok"]
    assert topic(page)["stage"] == "changes"
    release_t01(page)
    assert topic(page)["stage"] == "released"


def test_fr_006_edit_invalidates_current_version_approvals(page):
    release_t01(page)
    previous = topic(page)
    login(page, "content")
    assert command(page, "saveDraft", topicId="T01", body=previous["body"] + "\n补充适用范围。", notes="修订")["ok"]
    changed = topic(page)
    assert changed["version"] == previous["version"] + 1
    assert changed["approvals"] == {}
    assert changed["releasedVersion"] is None
    assert changed["stage"] == "draft"
    old = next(v for v in changed["history"] if v["version"] == previous["version"])
    assert old["body"] == previous["body"]
    assert old["releasedVersion"] == previous["version"]
    assert old["approvals"]["brand"]["version"] == previous["version"]
    assert old["body"] in page.evaluate("PRD.exportText()")
    login(page, "sales")
    assert not command(page, "channel", topicId="T01", channel="官网")["ok"]
    login(page, "content")
    assert command(page, "channel", topicId="T01", channel="官网")["ok"]
    channeled = topic(page)
    assert channeled["version"] == changed["version"] + 1
    assert channeled["approvals"] == {} and channeled["releasedVersion"] is None
    login(page, "dri")
    assert not command(page, "release", topicId="T01")["ok"]


def test_fr_007_feedback_adoption_is_gated_and_idempotent(page):
    login(page, "sales")
    assert not command(page, "addFeedback", topicId="T01", signal="追问", question="未放行")["ok"]
    release_t01(page)
    login(page, "sales")
    assert command(page, "addFeedback", topicId="T01", signal="客户追问", question="请给出维保出处")["ok"]
    created = state(page)["feedback"][-1]
    login(page, "dri")
    assert command(page, "adoptFeedback", feedbackId=created["id"])["ok"]
    assert next(x for x in state(page)["nextItems"] if x["feedbackId"] == created["id"])["kind"] == "资料需求"
    assert command(page, "adoptFeedback", feedbackId="FB04")["ok"]
    count = len(state(page)["nextItems"])
    assert not command(page, "adoptFeedback", feedbackId="FB04")["ok"]
    assert len(state(page)["nextItems"]) == count
    assert next(x for x in state(page)["nextItems"] if x["feedbackId"] == "FB04")["kind"] == "资料需求"


def test_fr_007_feedback_html_is_inert_and_new_questions_become_source_requests(page):
    release_t01(page)
    login(page, "sales")
    payload = '<img id="prd-xss" src=x onerror="window.__prdXss=1">'
    assert command(page, "addFeedback", topicId="T01", signal="客户追问", question=payload)["ok"]
    created = state(page)["feedback"][-1]
    login(page, "dri")
    assert command(page, "adoptFeedback", feedbackId=created["id"])["ok"]
    assert next(x for x in state(page)["nextItems"] if x["feedbackId"] == created["id"])["kind"] == "资料需求"
    assert command(page, "navigate", view="feedback")["ok"]
    page.evaluate("PRD.render()")
    assert page.locator("#prd-xss").count() == 0
    assert page.evaluate("window.__prdXss") is None
    assert page.locator("main").inner_text().count(payload) >= 1


def test_fr_008_persistence_export_and_corrupt_storage(page):
    release_t01(page)
    page.reload()
    page.wait_for_function("window.PRD && window.PRD.ready")
    assert topic(page)["stage"] == "released"
    text = page.evaluate("PRD.exportText()")
    for required in ("模拟数据", "S06", "T01", "版本", "导出时间", "未接模型", "https://"):
        assert required in text
    page.evaluate("localStorage.setItem('sunwin.prd.v1', '{bad')")
    page.reload()
    page.wait_for_function("window.PRD && window.PRD.ready")
    assert topic(page)["stage"] == "draft"
    assert page.get_by_test_id("storage-notice").is_visible()
    for mutation in ("view", "sourceReference"):
        page.evaluate("""mutation => {
            const value = PRD.state();
            if (mutation === 'view') value.view = 'not-a-view';
            else value.topics[0].sourceIds = ['NO-SUCH-SOURCE'];
            localStorage.setItem('sunwin.prd.v1', JSON.stringify(value));
        }""", mutation)
        page.reload()
        page.wait_for_function("window.PRD && window.PRD.ready")
        assert page.locator("body").get_attribute("data-view") == "overview"
        assert topic(page)["sourceIds"] == ["S06"]
        assert page.get_by_test_id("storage-notice").is_visible()


def test_fr_009_sources_and_pictures_expose_traceability_and_rights(page):
    for source in state(page)["sources"]:
        for field in ("id", "title", "publisher", "date", "stage", "fact", "boundary", "url"):
            assert source[field], (source["id"], field)
    pictures = state(page)["pictures"]
    assert len(pictures) == 5
    assert all(p["rights"] == "供内部选材；对外使用须确认" for p in pictures)
    assert all("自动驾驶运营实证" in p["boundary"] for p in pictures)
    assert all(p["filename"] and p["sourcePage"].startswith("https://") for p in pictures)
    assert all(p["originalUrl"].startswith("https://") for p in pictures)
    assert page.locator('img[src^="data:image/"]').count() >= 2
    assert page.evaluate("Array.from(document.images).every(i => i.complete && i.naturalWidth > 0)")


def test_fr_010_offline_mobile_and_explicit_simulation_boundary(page):
    html = DEMO.read_text(encoding="utf-8")
    assert 'src="http' not in html and "<link rel=\"stylesheet\"" not in html
    for width, height in ((1440, 1000), (390, 844)):
        page.set_viewport_size({"width": width, "height": height})
        for view in ("overview", "questions", "calendar", "review", "feedback", "sources"):
            assert command(page, "navigate", view=view)["ok"]
            page.evaluate("PRD.render()")
            assert page.locator("body").get_attribute("data-view") == view
            assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    body = page.locator("body").inner_text()
    assert "规则/模板模拟" in body and "未接模型" in body and "不真实发布" in body


def test_fr_010_render_preserves_action_focus_and_navigation_focuses_heading(page):
    command(page, "navigate", view="questions")
    page.evaluate("PRD.render()")
    assert page.evaluate("document.activeElement.tagName") == "H1"
    match = page.locator('[data-action="match"][data-id="CQ01"]')
    match.focus()
    page.keyboard.press("Enter")
    assert page.evaluate("document.activeElement.dataset.action") == "match"
    assert page.evaluate("document.activeElement.dataset.id") == "CQ01"
