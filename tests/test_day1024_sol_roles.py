"""FR-001–011：分角色营销 mock 的行为验收，不宣称生产鉴权。"""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "assets/day1024_sol_v1_v2/index.html"
pytestmark = pytest.mark.skipif(
    not DEMO.parent.is_dir(), reason="未附带 assets 演示材料；SKIP 不等于验收通过"
)


@pytest.fixture
def page():
    assert DEMO.is_file(), "FR 成品尚未实现：缺少单文件 index.html"
    api = pytest.importorskip("playwright.sync_api", reason="需要 Playwright 才能做浏览器验收")
    with api.sync_playwright() as driver:
        browser = driver.chromium.launch()
        context = browser.new_context(offline=True, viewport={"width": 1440, "height": 1000})
        tab = context.new_page()
        errors, requests = [], []
        tab.on("pageerror", lambda error: errors.append(str(error)))
        tab.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
        tab.on("request", lambda req: requests.append(req.url) if req.url.startswith("http") else None)
        tab.goto(DEMO.as_uri())
        tab.wait_for_function("window.Demo && window.Demo.ready")
        yield tab
        assert not errors, errors
        assert not requests, requests
        context.close()
        browser.close()


def login(page, role):
    page.evaluate("role => Demo.login(role)", role)


def cmd(page, action, **payload):
    return page.evaluate("p => Demo.command(p.action, p.payload)", {"action": action, "payload": payload})


def snapshot(page):
    return page.evaluate("Demo.snapshot()")


def topic(page, topic_id="T01"):
    return next(t for t in snapshot(page)["topics"] if t["id"] == topic_id)


def reviewed(page):
    login(page, "content")
    assert cmd(page, "submit", topicId="T01")["ok"]
    for role in ["tech", "project"]:
        login(page, role)
        assert cmd(page, "approve", topicId="T01", decision="approve", reason="核对当前版本")["ok"]


def released(page):
    reviewed(page)
    login(page, "brand")
    assert cmd(page, "approve", topicId="T01", decision="approve", reason="口径确认")["ok"]
    login(page, "dri")
    assert cmd(page, "release", topicId="T01")["ok"]


def test_fr_001_role_specific_workspaces(page):
    assert page.get_by_test_id("identity-picker").is_visible()
    titles = {
        "dri": "项目驾驶舱", "sales": "客户问题台", "content": "内容制作台",
        "tech": "技术审核台", "project": "项目核验台", "brand": "品牌确认台",
    }
    for role, title in titles.items():
        login(page, role)
        assert page.get_by_role("heading", name=title, exact=True).is_visible()
        assert page.locator("#side-nav button").count() <= 4
        assert page.get_by_test_id("simulation-notice").is_visible()
    assert not page.evaluate("Demo.login('admin').ok")


def test_fr_002_unauthorized_commands_do_not_mutate_business(page):
    for role, action, payload in [
        ("sales", "release", {"topicId": "T01"}),
        ("dri", "approve", {"topicId": "T01", "decision": "approve"}),
        ("tech", "saveDraft", {"topicId": "T01", "body": "越权编辑"}),
        ("content", "planQuestion", {"questionId": "CQ04", "week": "W1"}),
    ]:
        login(page, role)
        before = snapshot(page)
        assert not cmd(page, action, **payload)["ok"]
        after = snapshot(page)
        assert before["topics"] == after["topics"]
        assert before["claims"] == after["claims"]


def test_fr_003_question_to_dri_planning_is_idempotent(page):
    login(page, "sales")
    page.get_by_role("button", name="录入客户问题", exact=True).click()
    page.get_by_label("客户原话").fill("海外客户想了解城间车型适用场景")
    page.get_by_label("所属客群").select_option("海外客户")
    page.get_by_role("button", name="保存问题", exact=True).click()
    q = snapshot(page)["questions"][-1]
    login(page, "dri")
    assert cmd(page, "planQuestion", questionId=q["id"], week="W2")["ok"]
    before = len(snapshot(page)["topics"])
    assert not cmd(page, "planQuestion", questionId=q["id"], week="W2")["ok"]
    assert len(snapshot(page)["topics"]) == before
    assert topic(page, snapshot(page)["topics"][-1]["id"])["owner"] == "content"
    assert not cmd(page, "planQuestion", questionId="missing", week="W2")["ok"]


def test_fr_004_sources_and_embedded_pictures_are_traceable(page):
    login(page, "content")
    page.get_by_role("button", name="来源与素材", exact=True).click()
    page.get_by_label("搜索资料").fill("RoboBus")
    assert page.get_by_test_id("source-card").count() >= 1
    page.get_by_label("搜索资料").fill("完全不存在的资料")
    assert page.get_by_test_id("source-card").count() == 0
    page.get_by_label("搜索资料").fill("")
    sources = page.evaluate("Demo.sources")
    assert 10 <= len(sources) <= 15
    for source in sources:
        for field in ["id", "title", "publisher", "date", "maturity", "audience", "fact", "boundary", "location"]:
            assert source[field], (source["id"], field)
    assert page.locator('img[src^="data:image/"]').count() >= 3
    assert page.evaluate("Array.from(document.images).every(i => i.complete && i.naturalWidth > 0)")


def test_fr_005_channel_templates_and_evidence_gate(page):
    login(page, "content")
    for channel in ["公众号", "官网", "展会", "销售推介"]:
        assert cmd(page, "generate", topicId="T01", channel=channel)["ok"]
        draft = topic(page)
        assert draft["channel"] == channel
        assert "S06" in draft["body"]
        assert "内部备注" not in draft["body"]
    assert not cmd(page, "submit", topicId="T03")["ok"]
    assert topic(page, "T03")["stage"] == "draft"
    assert not cmd(page, "generate", topicId="T01", channel="任意渠道")["ok"]


def test_fr_006_parallel_reviews_return_and_version_bound_signatures(page):
    login(page, "content")
    assert cmd(page, "submit", topicId="T01")["ok"]
    login(page, "tech")
    assert not cmd(page, "approve", topicId="T01", decision="return", reason="")["ok"]
    assert cmd(page, "approve", topicId="T01", decision="return", reason="请明确仅适用报道批次")["ok"]
    assert topic(page)["stage"] == "changes"
    login(page, "content")
    assert not cmd(page, "submit", topicId="T01")["ok"], "退回的原版本不能直接重新提交"
    assert cmd(
        page, "saveDraft", topicId="T01",
        body=topic(page)["body"] + "\n再次明确：仅报道对应批次，配置不外推。", notes="按退回意见修订",
    )["ok"]
    assert cmd(page, "submit", topicId="T01")["ok"]
    login(page, "project")
    assert cmd(page, "approve", topicId="T01", decision="approve", reason="项目范围核对")["ok"]
    assert topic(page)["stage"] == "review"
    assert not cmd(page, "approve", topicId="T01", decision="approve")["ok"]
    login(page, "tech")
    assert cmd(page, "approve", topicId="T01", decision="approve")["ok"]
    assert topic(page)["stage"] == "brand"
    assert set(topic(page)["approvals"]) == {"tech", "project"}


def test_fr_007_edit_invalidates_all_current_approvals(page):
    released(page)
    previous = topic(page)
    assert snapshot(page)["claims"]
    login(page, "content")
    assert cmd(page, "saveDraft", topicId="T01", body=previous["body"] + "\n补充场景说明。", notes="新版本")["ok"]
    changed = topic(page)
    assert changed["version"] == previous["version"] + 1
    assert changed["stage"] == "draft"
    assert changed["approvals"] == {}
    assert changed["releasedVersion"] is None
    assert snapshot(page)["claims"][0]["version"] == previous["version"]
    login(page, "dri")
    assert not cmd(page, "release", topicId="T01")["ok"]
    login(page, "content")
    assert cmd(page, "restoreVersion", topicId="T01", version=previous["version"], reason="恢复已核对的旧正文")["ok"]
    assert topic(page)["version"] == previous["version"] + 2
    assert topic(page)["approvals"] == {}
    assert topic(page)["stage"] == "draft"


def test_fr_008_brand_and_dri_cannot_skip_gates(page):
    login(page, "brand")
    assert not cmd(page, "approve", topicId="T01", decision="approve")["ok"]
    login(page, "dri")
    assert not cmd(page, "release", topicId="T01")["ok"]
    released(page)
    draft = topic(page)
    assert draft["stage"] == "released"
    assert draft["releasedVersion"] == draft["version"]
    assert not cmd(page, "release", topicId="T01")["ok"]
    log = snapshot(page)["audit"]
    assert {"content", "tech", "project", "brand", "dri"} <= {x["role"] for x in log}
    login(page, "content")
    claim = snapshot(page)["claims"][0]
    assert cmd(page, "reuseClaim", claimId=claim["id"], topicId="T02")["ok"]
    assert topic(page, "T02")["stage"] == "draft"
    assert topic(page, "T02")["approvals"] == {}


def test_fr_009_feedback_to_next_round_without_duplicates(page):
    login(page, "sales")
    assert not cmd(page, "addFeedback", topicId="T01", signal="追问适用范围", question="尚未发布")["ok"]
    released(page)
    login(page, "sales")
    assert cmd(page, "addFeedback", topicId="T01", signal="追问适用范围", question="下一轮请说明适用线路")["ok"]
    feedback = snapshot(page)["feedback"][-1]
    login(page, "dri")
    assert cmd(page, "adoptFeedback", feedbackId=feedback["id"])["ok"]
    count = len(snapshot(page)["questions"])
    assert not cmd(page, "adoptFeedback", feedbackId=feedback["id"])["ok"]
    assert len(snapshot(page)["questions"]) == count
    assert snapshot(page)["questions"][-1]["feedbackId"] == feedback["id"]


def test_fr_010_persistence_download_and_corrupt_storage(page, tmp_path):
    released(page)
    page.reload()
    page.wait_for_function("window.Demo && Demo.ready")
    assert topic(page)["stage"] == "released"
    login(page, "dri")
    with page.expect_download() as download:
        page.get_by_role("button", name="导出项目记录", exact=True).click()
    target = tmp_path / "project.md"
    download.value.save_as(target)
    text = target.read_text(encoding="utf-8")
    for required in ["模拟数据", "S06", "T01", "版本", "导出时间", "辅助驾驶", "https://"]:
        assert required in text
    page.evaluate("localStorage.setItem('sunwin.role-demo.v1', '{bad')")
    page.reload()
    page.wait_for_function("window.Demo && Demo.ready")
    assert page.get_by_test_id("storage-notice").is_visible()
    assert topic(page)["stage"] == "draft"


def test_fr_011_offline_mobile_and_explicit_mock_boundary(page):
    html = DEMO.read_text(encoding="utf-8")
    assert 'src="http' not in html and '<link rel="stylesheet"' not in html
    for size in [{"width": 1440, "height": 1000}, {"width": 390, "height": 844}]:
        page.set_viewport_size(size)
        for role in ["dri", "sales", "content", "tech", "project", "brand"]:
            login(page, role)
            assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
            assert page.get_by_test_id("simulation-notice").is_visible()
    assert "不是真实登录鉴权" in page.locator("body").inner_text()
    assert "未接模型" in page.locator("body").inner_text()


def test_fr_005_picture_rights_are_not_implicitly_approved(page):
    login(page, "content")
    assert cmd(page, "selectPicture", topicId="T01", pictureId="PIC04")["ok"]
    result = cmd(page, "submit", topicId="T01")
    assert not result["ok"] and "授权" in result["message"]
    assert cmd(page, "selectPicture", topicId="T01", pictureId=None)["ok"]
    assert cmd(page, "submit", topicId="T01")["ok"]


def test_fr_010_unavailable_storage_is_visible(page):
    page.add_init_script("Object.defineProperty(window, 'localStorage', {get(){throw new Error('denied')}})")
    page.reload()
    page.wait_for_function("window.Demo && Demo.ready")
    assert page.get_by_test_id("storage-notice").is_visible()
    login(page, "sales")
    assert cmd(page, "addQuestion", ask="离线存储被拒绝时仍可继续演示", audience="行业伙伴")["ok"]
    assert "会话模式" in page.get_by_test_id("storage-notice").inner_text()
