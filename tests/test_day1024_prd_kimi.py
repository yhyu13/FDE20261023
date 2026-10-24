"""FR-001–008：两策略、四 Campaign、三屏部门会签原型验收。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "assets/day1024_prd_kimi/index.html"


@pytest.fixture
def page():
    assert DEMO.is_file(), "缺少 assets/day1024_prd_kimi/index.html"
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


def campaign(page, campaign_id="C01"):
    return next(item for item in state(page)["campaigns"] if item["id"] == campaign_id)


def approve(page, role, campaign_id="C01", comment=None):
    login(page, role)
    return command(
        page,
        "reviewCampaign",
        campaignId=campaign_id,
        decision="approve",
        comment=comment or f"{role} 已核对当前版本",
    )


def store_state(page, value):
    page.evaluate(
        "p => localStorage.setItem('growthpilot.kimi.v1', p)",
        json.dumps(value, ensure_ascii=False),
    )


def reload_ready(page):
    page.reload()
    page.wait_for_function("window.PRD && window.PRD.ready")


def test_fr_001_only_two_growth_levers_and_four_campaigns(page):
    data = state(page)
    assert set(data["levers"]) == {"精准投流", "提高复购率"}
    assert len(data["enterprise"]) == 7
    assert len(data["campaigns"]) == 4
    for lever in data["levers"]:
        assert sum(c["lever"] == lever for c in data["campaigns"]) == 2
    assert page.get_by_text("把产品卖爆，先只打两场仗", exact=True).is_visible()
    assert page.get_by_test_id("simulation-notice").is_visible()


def test_fr_002_every_analysis_links_to_canonical_enterprise_data(page):
    data = state(page)
    evidence_ids = {row["id"] for row in data["enterprise"]}
    assert evidence_ids == {f"D0{i}" for i in range(1, 8)}
    for item in data["campaigns"]:
        assert len(item["evidenceIds"]) >= 2
        assert set(item["evidenceIds"]) <= evidence_ids
        assert item["dataDisclosure"] == "合成演示数据"
    stored = page.evaluate("localStorage.getItem('growthpilot.kimi.v1')")
    assert "DEMO-C03" not in stored and "30 天复购率 21%" not in stored


def test_fr_003_campaign_plans_and_assets_are_complete_not_placeholders(page):
    for item in state(page)["campaigns"]:
        for key in ("title", "insight", "audience", "channel", "flight", "budget", "goal", "headline", "body"):
            assert item[key], (item["id"], key)
        assert len(item["assets"]) >= 3
        assert all(asset["label"] and asset["text"] for asset in item["assets"])
        assert item["required"] in (["marketing", "sales", "finance"], ["marketing", "crm", "finance"])
        combined = item["headline"] + item["body"] + "".join(a["text"] for a in item["assets"])
        assert "此处生成" not in combined and "待定文案" not in combined


def test_fr_004_department_guards_and_ready_gate(page):
    assert campaign(page)["status"] == "in_review"
    login(page, "crm")
    assert not command(
        page, "reviewCampaign", campaignId="C01", decision="approve", comment="越权"
    )["ok"]
    assert approve(page, "sales")["ok"]
    assert campaign(page)["status"] == "in_review"
    assert not approve(page, "sales")["ok"], "同一部门不能重复审同一版本"
    assert approve(page, "finance")["ok"]
    assert campaign(page)["status"] == "ready"
    assert not approve(page, "marketing")["ok"], "待执行后不能继续改写审核"


def test_fr_005_return_revise_and_reapprove_new_version(page):
    assert approve(page, "sales")["ok"]
    login(page, "finance")
    assert command(
        page, "reviewCampaign", campaignId="C01", decision="changes", comment="体验装权益需核对"
    )["ok"]
    assert campaign(page)["status"] == "changes"
    login(page, "marketing")
    assert command(
        page,
        "reviseCampaign",
        campaignId="C01",
        headline="下午三点，给自己一条清爽冷萃",
        body="加水或牛奶，0 蔗糖。新客体验装权益以财务确认页为准。",
    )["ok"]
    revised = campaign(page)
    assert revised["version"] == 2 and revised["status"] == "in_review"
    assert len(revised["versions"]) == 2
    assert not [r for r in revised["reviews"] if r["version"] == 2]
    assert approve(page, "marketing")["ok"]
    assert approve(page, "sales")["ok"]
    assert campaign(page)["status"] == "in_review"
    assert approve(page, "finance")["ok"]
    assert campaign(page)["status"] == "ready"


def test_fr_006_persistence_export_full_content_and_safe_markdown(page):
    payload = '新标题\n# 伪造待执行章节\n<script>window.__xss=1</script>'
    login(page, "finance")
    assert command(
        page, "reviewCampaign", campaignId="C01", decision="changes", comment=payload
    )["ok"]
    login(page, "marketing")
    assert command(
        page,
        "reviseCampaign",
        campaignId="C01",
        headline=payload,
        body="修订正文\n- 伪造审核记录",
    )["ok"]
    reload_ready(page)
    assert campaign(page)["version"] == 2
    exported = page.evaluate("PRD.exportText()")
    assert "assets/real_request.md" in exported
    assert "短视频" in exported and "体验装权益需核对" not in exported
    assert "伪造待执行章节" in exported
    assert "\n# 伪造待执行章节" not in exported
    assert "<script>" not in exported and "\n- 伪造审核记录" not in exported
    command(page, "navigate", view="review")
    assert page.locator("script").count() == 1
    assert page.evaluate("window.__xss") is None


def test_fr_007_valid_json_with_forged_ready_or_bad_ids_is_rejected(page):
    stored = page.evaluate("JSON.parse(localStorage.getItem('growthpilot.kimi.v1'))")
    stored["records"]["C01"]["status"] = "ready"
    store_state(page, stored)
    reload_ready(page)
    assert campaign(page)["status"] == "in_review"
    assert page.get_by_test_id("storage-warning").is_visible()
    stored = page.evaluate("JSON.parse(localStorage.getItem('growthpilot.kimi.v1'))")
    stored["records"]["C01"]["reviews"][0]["id"] = '<img src=x onerror="window.__xss=1">'
    store_state(page, stored)
    reload_ready(page)
    assert page.get_by_test_id("storage-warning").is_visible()
    assert page.locator("img[src='x']").count() == 0
    assert page.evaluate("window.__xss") is None
    page.evaluate("localStorage.setItem('growthpilot.kimi.v1', '{bad json')")
    reload_ready(page)
    assert state(page)["schema"] == 1
    assert page.get_by_test_id("storage-warning").is_visible()


def test_fr_008_real_ui_review_three_views_and_mobile(page):
    for view in ("overview", "campaigns", "review"):
        assert command(page, "navigate", view=view)["ok"]
        assert page.get_by_test_id(f"view-{view}").is_visible()
    page.locator("#role-select").select_option("sales")
    page.locator("#review-comment").fill("销售已核对线索承接与体验装入口")
    page.locator("[data-action='reviewCampaign'][data-decision='approve']").click()
    page.locator("#role-select").select_option("finance")
    page.locator("#review-comment").fill("财务已核对演示预算与权益")
    page.locator("[data-action='reviewCampaign'][data-decision='approve']").click()
    assert campaign(page)["status"] == "ready"
    assert page.get_by_text("待执行", exact=True).first.is_visible()
    for view in ("overview", "campaigns", "review"):
        command(page, "navigate", view=view)
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    page.set_viewport_size({"width": 390, "height": 844})
    command(page, "navigate", view="overview")
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    assert page.get_by_role("button", name="导出 Campaign 方案").is_visible()
