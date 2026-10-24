"""成品验证测试：单文件 HTML 演示（Day1024 GLM）

对应 `assets/day1024_glm/spec.md` 的 FR-001…FR-015 与 SC-001…SC-008。

这不是"给生产代码写单测"——成品是演示资产，没有生产逻辑。
这里是**交付物验收层**：把"评审人当场能点出来的东西"变成机械可判定的断言。

判定口径：
* 编号一律不虚造：FR-xxx ↔ test_demo_fr_xxx 一一对应，不许悬空。
* 数字要么来自数据层，要么显式标「模拟数据」；成品里不许出现未标注的效果宣称。
* 联网条目必须带真实 URL 与发布日期；材料包条目必须逐字存在于数据层。
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DEMO_DIR = ROOT / "assets" / "day1024_glm"
HTML_PATH = DEMO_DIR / "sunwin-ai-marketing-ops-demo.html"
DATA_PATH = DEMO_DIR / "_data.json"
SPEC_PATH = DEMO_DIR / "spec.md"
TESTS_PATH = Path(__file__)

# 演示资产目录 assets/ 不在版本控制内（见 .gitignore），所以这份验收测试
# 在没带资产的检出（CI、别人的 clone）里没有可验对象。
# 缺对象时整份跳过，而不是报错——"没跑"不等于"通过"，闸的结论行会写明这一点。
pytestmark = pytest.mark.skipif(
    not DEMO_DIR.is_dir(),
    reason="演示资产 assets/day1024_glm/ 未入库，成品验收测试无对象可验",
)


def _load_data() -> dict:
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


def _load_html() -> str:
    return HTML_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def data() -> dict:
    return _load_data()


@pytest.fixture(scope="module")
def html() -> str:
    return _load_html()


# --------------------------------------------------------------------------
# FR-001 / FR-002 / FR-003：资料中台
# --------------------------------------------------------------------------
def test_demo_fr001_material_and_net_entries_complete(data):
    """材料包 11 条 + 联网 20 条，字段齐全。"""
    sources = data["sources"]
    material = [s for s in sources if s["kind"] == "material"]
    net = [s for s in sources if s["kind"] == "net"]
    assert [s["id"] for s in material] == [f"S{i:02d}" for i in range(1, 12)]
    assert [s["id"] for s in net] == [f"N{i:02d}" for i in range(1, 21)]
    required = [
        "id", "title", "type", "publisher", "date", "checked", "url", "stage",
        "level", "audiences", "fact", "boundary", "missing", "usage", "kind",
    ]
    for s in sources:
        for field in required:
            assert field in s, f"{s['id']} 缺字段 {field}"
            assert s[field] not in (None, ""), f"{s['id']} 字段 {field} 为空"
        assert s["url"].startswith("http"), f"{s['id']} 的 URL 不是真实链接"
        assert re.search(r"20\d\d", s["checked"]), f"{s['id']} 缺检索核对日期"
        if s["kind"] == "net":
            assert re.search(r"20\d\d", s["date"]), f"{s['id']} 联网条目缺发布日期"
        assert 1 <= s["level"] <= 4


def test_demo_fr002_net_entries_flagged_as_reference_only(html):
    """联网条目带真实 URL + 日期 + 「仅供参考」标注，与材料包视觉区分。"""
    assert "联网核实 · 仅供参考" in html
    assert "kind === 'net'" in html
    assert "联网" in html
    # 材料包与联网两条目必须在成品里都能被检索到
    assert "S01" in html and "N01" in html and "N20" in html


def test_demo_fr003_missing_params_rendered_as_todo_not_blank(data, html):
    """缺参数不补值，显示为「待补」；成品里不出现 undefined / NaN 泄漏到界面。"""
    with_missing = [s for s in data["sources"] if s["missing"]]
    assert len(with_missing) >= 10, "缺参数条目太少，演示不出『待补』这一态"
    assert "缺参数" in html and "待补" in html
    # 只查会渲染到界面上的形态：>undefined< / >NaN<（base64 里可能凑巧出现 NaN 字样，不算）
    assert ">undefined<" not in html, "界面里出现 undefined，说明有字段没接上"
    assert ">NaN<" not in html
    assert "undefined" not in json.dumps(data, ensure_ascii=False)


# --------------------------------------------------------------------------
# FR-004：场景匹配
# --------------------------------------------------------------------------
def test_demo_fr004_all_twelve_questions_have_evidence_or_explicit_gap(data):
    """12 条客户问题，每条要么有资料，要么显式写明缺什么。"""
    qs = data["questions"]
    assert len(qs) == 12
    assert [q["id"] for q in qs] == [f"CQ{i:02d}" for i in range(1, 13)]
    for q in qs:
        assert q["state"] in {"有依据", "部分依据", "无资料"}
        assert q["ask"] and q["theme"] and q["boundary"]
        if q["state"] == "无资料":
            assert q["sources"] == [], f"{q['id']} 标了无资料却挂了资料"
            assert q["gap"], f"{q['id']} 无资料但没写缺口"
        else:
            assert q["sources"], f"{q['id']} 标了有依据却没挂资料"


def test_demo_fr004_cost_question_cannot_generate_copy(data):
    """CQ04（成本降 30%）只能转资料征集；任何交付物里都不许出现 30% 断言。"""
    cq04 = next(q for q in data["questions"] if q["id"] == "CQ04")
    assert cq04["sources"] == []
    assert "30" in cq04["ask"] or "30%" in cq04["ask"]
    for draft in data["channelDrafts"]:
        blob = json.dumps(draft, ensure_ascii=False)
        assert "30%" not in blob, f"渠道稿 {draft['id']} 出现无来源的 30%"
    for t in data["topics"]:
        assert "30%" not in json.dumps(t, ensure_ascii=False)
    # 唯一允许出现 30% 的地方：旧稿原文、审核意见原表达、检测器错例
    assert "30%" in data["draft"]["text"]
    assert any("30%" in r["raw"] for r in data["reviews"])
    assert any("30%" in c["text"] and c["over"] for c in data["detector"])


# --------------------------------------------------------------------------
# FR-005 / FR-006：选题与渠道
# --------------------------------------------------------------------------
def test_demo_fr005_every_topic_has_cq_and_source_or_is_flagged(data, html):
    """每条选题至少 1 个 CQ；缺来源的必须在界面上被标为不合规。"""
    topics = data["topics"]
    assert len(topics) >= 6
    for t in topics:
        assert t["cqs"], f"{t['id']} 没挂客户问题"
        assert t["audience"] in {"公交运营商", "海外客户", "行业伙伴"}
        assert t["week"] and t["channels"] and t["theme"]
    t08 = next(t for t in topics if t["id"] == "T08")
    assert t08["sources"] == [], "T08 应保持无资料（转资料征集）"
    assert "资料征集" in t08["theme"]
    assert "不合规" in html, "选题缺来源时界面必须标不合规"


def test_demo_fr006_channel_drafts_have_refs_and_pending(data, html):
    """四类渠道稿齐备；每个事实块都挂编号；待核实内容单独成块。"""
    drafts = data["channelDrafts"]
    assert [d["id"] for d in drafts] == ["公众号提纲", "官网文案", "展会介绍", "销售推介"]
    for d in drafts:
        assert d["blocks"], f"{d['id']} 没有内容块"
        assert d["pending"], f"{d['id']} 没有待核实块"
        for b in d["blocks"]:
            assert b["refs"], f"{d['id']} 的内容块没有挂来源编号"
        for p in d["pending"]:
            assert p["refs"], f"{d['id']} 的待核实项没有挂来源编号"
    assert "待核实" in html


# --------------------------------------------------------------------------
# FR-007 / FR-008 / FR-009：审核、口径、复用
# --------------------------------------------------------------------------
def test_demo_fr007_v02_contains_no_violation_phrases(data):
    """改稿 v0.2 里不得残留任何越界表述。"""
    blob = json.dumps(data["revisedDraft"], ensure_ascii=False)
    forbidden = [
        "量产和大规模商业运营",
        "所有申沃车型",
        "海外项目正式落地",
        "30%",
        "iEV12LE 面向城市公交",
    ]
    for bad in forbidden:
        assert bad not in blob, f"v0.2 仍含越界表述：{bad}"
    assert len(data["revisedDraft"]["sentences"]) == 5
    # 五处越界必须有对应审核结论
    assert {r["sentence"] for r in data["reviews"]} == {
        s["id"] for s in data["draft"]["sentences"]
    }
    assert len(data["reviews"]) == 5
    for r in data["reviews"]:
        assert r["result"] in {"不通过", "修改", "待补依据"}
        assert r["role"] in {"技术审核员", "品牌审核员", "项目审核员"}
        assert r["fix"] and r["basis"] and r["require"]


def test_demo_fr008_phrases_have_source_version_scope_and_reuse_flag(data, html):
    """P01–P03 必须有来源、版本、状态、审核依据、适用范围，并显示复用免重审。"""
    phrases = data["phrases"]
    assert [p["id"] for p in phrases] == ["P01", "P02", "P03"]
    for p in phrases:
        for f in ("text", "source", "stage", "version", "status", "basis", "scope", "approval"):
            assert p[f], f"{p['id']} 缺 {f}"
        assert p["status"] == "已确认"
    assert "免重审" in html
    assert "复用" in html


def test_demo_fr009_feedback_maps_to_topic_updates_and_requests(data):
    """FB01–04 → 选题调整 → 待补资料，三段必须连得上。"""
    fbs = {f["id"] for f in data["feedback"]}
    assert fbs == {"FB01", "FB02", "FB03", "FB04"}
    topic_ids = {t["id"] for t in data["topics"]}
    for u in data["topicUpdates"]:
        assert u["topic"] in topic_ids
        assert u["fb"] in fbs
        assert u["change"] and u["reason"]
    assert len(data["topicUpdates"]) == len(data["topics"])
    for r in data["todoRequests"]:
        assert r["owner"] and r["refs"] and r["state"] and r["due"]
        assert r["id"].startswith("REQ")


# --------------------------------------------------------------------------
# FR-010 / FR-011 / FR-014：成熟度与边界
# --------------------------------------------------------------------------
def test_demo_fr010_four_levels_have_sourced_items_and_platform_boundary(data, html):
    """四级阶梯每级都有可点来源；享道平台事实与申沃合作事实必须分开。"""
    levels = data["levels"]
    assert [lv["id"] for lv in levels] == ["L1", "L2", "L3", "L4"]
    known = {s["id"] for s in data["sources"]} | {p["id"] for p in data["phrases"]} | {
        r["id"] for r in data["reviews"]
    }
    for lv in levels:
        assert lv["items"], f"{lv['id']} 没有条目"
        assert lv["say"] and lv["cannot"]
        for it in lv["items"]:
            assert it["ref"] in known, f"{lv['id']} 引用了不存在的编号 {it['ref']}"
    # 享道运营数据必须标成平台事实
    n06 = next(s for s in data["sources"] if s["id"] == "N06")
    assert "享道" in n06["fact"] and "申沃" in n06["boundary"]
    assert "平台" in n06["boundary"]
    assert "享道" in html and "S11" in html


def test_demo_fr011_detector_has_seven_cases_with_answers(data, html):
    """7 句示例全部有级别、是否越级、理由、正确说法、依据。"""
    cases = data["detector"]
    assert len(cases) == 7
    over = [c for c in cases if c["over"]]
    good = [c for c in cases if not c["over"]]
    assert len(over) == 5 and len(good) == 2
    known = {s["id"] for s in data["sources"]} | {p["id"] for p in data["phrases"]} | {
        r["id"] for r in data["reviews"]
    } | {f["id"] for f in data["feedback"]} | {q["id"] for q in data["questions"]}
    for c in cases:
        assert c["actual"] and c["reason"] and c["correct"] and c["basis"]
        for b in c["basis"]:
            assert b in known, f"{c['id']} 依据编号 {b} 不存在"


def test_demo_fr014_boundary_rules_present(data, html):
    """阶段边界规则 B1–B6 必须出现在成品里。"""
    rules = data["boundaryRules"]
    assert len(rules) == 6
    for r in rules:
        assert r["text"] and r["refs"]
    for r in rules:
        assert r["id"] in html, f"边界规则 {r['id']} 没有出现在成品里"


# --------------------------------------------------------------------------
# FR-012 / FR-013 / FR-015：全局、冲突、流水线
# --------------------------------------------------------------------------
def test_demo_fr012_overview_maps_five_tasks_and_labels_mock(data, html):
    """总览必须把企业 5 项任务映射到模块，并标「演示数据 · 非实测」。"""
    assert "演示数据" in html and "非实测" in html
    for token in ("任务 1", "任务 2", "任务 3", "任务 4", "任务 5"):
        assert token in html, f"总览缺少 {token} 的映射"
    assert data["meta"]["notice"] == "演示数据 · 非实测"
    assert "未做" in html, "总览必须列出未做事项"


def test_demo_fr013_conflicts_shown_not_resolved(data, html):
    """口径冲突必须显式挂起（已核实的除外），同时给出两个口径与处置动作。"""
    conflicts = data["conflicts"]
    assert len(conflicts) == 4
    for c in conflicts:
        assert c["a"] and c["b"] and c["action"] and c["refs"]
        assert c["a"] != c["b"]
        if c.get("resolved"):
            assert c.get("resolvedBy"), f"{c['id']} 标了已核实却没写核实依据"
    unresolved = [c for c in conflicts if not c.get("resolved")]
    assert len(unresolved) >= 3, "挂起的口径冲突太少，等于把问题藏起来"
    assert "口径冲突" in html
    assert "CF-01" in html and "CF-04" in html
    assert "已核实" in html, "已核实的冲突项必须在界面上标出来"


def test_demo_fr015_pipeline_and_gates_present(data, html):
    """7 段流水线 + 6 条护栏 + 8 项发布前检查 + 导出出口。"""
    stages = data["pipeline"]
    assert [s["stage"] for s in stages] == ["归集", "打标", "匹配", "起草", "审核", "发布闸", "回流"]
    for s in stages:
        assert s["owner"] and s["output"] and s["gate"]
    guards = data["guardrails"]
    assert len(guards) == 6
    for g in guards:
        assert g["name"] and g["desc"] and isinstance(g["value"], int)
        assert isinstance(g["target"], int)
    assert len(data["releaseChecks"]) == 8
    assert "导出" in html
    assert "createObjectURL" in html, "导出必须能真的把决定带走"


# --------------------------------------------------------------------------
# 交付形态：单文件 / 离线 / 无占位 / 无未验证宣称
# --------------------------------------------------------------------------
def test_demo_single_file_offline_no_remote_resources(html):
    """单文件、离线可开：无远端脚本/样式/图片/字体。"""
    assert "<script src=" not in html
    assert "<link " not in html or "rel=\"stylesheet\"" not in html
    assert re.search(r'<img[^>]+src="https?://', html) is None
    assert "fonts.googleapis.com" not in html
    assert "cdn." not in html
    assert "http" in html  # 只允许作为「原文链接」出现，不作为资源依赖


def test_demo_images_embedded_as_data_uri(html):
    """5 张产品图必须内联进单文件，不引用外部路径。"""
    assert html.count("data:image/jpeg;base64,") == 5
    for pic in ("PIC01", "PIC02", "PIC03", "PIC04", "PIC05"):
        assert pic in html


def test_demo_no_filler_or_placeholder(html):
    """不许出现占位式交付（AGENTS.md §13.5）。"""
    for bad in ("Lorem ipsum", "Feature One", "占位块", "XXXX", "示例文本", "待填"):
        assert bad not in html, f"成品出现占位内容：{bad}"


def test_demo_no_unverified_claims(html):
    """不宣称未验证的效果（AGENTS.md §13.3）。"""
    for bad in ("准确率 9", "业界领先", "行业第一", "全球第一", "效果显著", "降本增效 3"):
        assert bad not in html, f"成品出现未验证宣称：{bad}"


def test_demo_fr016_two_write_entry_points_with_live_compliance_check(html):
    """FR-016：系统必须有两个「写」的入口，且新录入内容一律先判无据/不合规。

    企业最硬的批评：整份 Demo 没有「录入」动词，销售"把客户问题带回来"无处落地。
    """
    # ① 录客户问题
    assert "记一条客户问题" in html, "M2 缺少「＋ 记一条客户问题」入口"
    assert "口头来源" in html, "录入表单缺少「口头来源」字段"
    assert "本轮新记" in html, "新录入的客户问题必须标出是本轮新记"
    assert "可查方向" in html, "新问题必须给出「可查方向（未核实）」而不是直接当成有依据"
    # ② 录选题
    assert "新增选题" in html, "M3 缺少「＋ 新增选题」入口"
    assert "缺引用资料" in html and "缺客户问题" in html, "新增选题必须写明缺哪一项"
    assert "不合规" in html, "缺依据的新增选题必须标不合规"


def test_demo_fr017_phrase_library_has_copy_and_recent_use(html):
    """FR-017：口径复用要有独立出口——一键复制 + 最近使用 + 已入库计数。"""
    assert "一键复制" in html, "口径库缺少一键复制"
    assert "最近使用" in html, "口径库缺少最近使用"
    assert "已入库" in html, "口径库必须显示已入库计数"
    assert "能说到哪" in html, "口径库必须给出「本句能说到哪为止」"
    assert "id=\"panel-m8\"" in html, "口径库必须是独立模块（导航置顶）"


def test_demo_fr018_data_provenance_is_graded_not_flattened(html):
    """FR-018：公开资料与脱敏情境必须分级标注，不许用一句「全是 mock」一起打折。"""
    assert "公开" in html and "可回链" in html, "缺少「公开 · 可回链」口径徽标"
    assert "脱敏情境" in html, "缺少「材料包 · 脱敏情境」口径徽标"
    for bad in ("数据全部由 mock 数据层产出", "全部是 mock", "均为模拟数据，请勿当真"):
        assert bad not in html, f"界面出现了笼统贬低口径的措辞：{bad}"


def test_demo_module_contract_complete(html):
    """8 个模块齐备，render/bind 成对存在，可导航。"""
    for i in range(1, 8):
        assert f"function renderM{i}(" in html, f"缺 renderM{i}"
        assert f"function bindM{i}(" in html, f"缺 bindM{i}"
    assert "function renderM8(" in html, "缺 renderM8"
    assert "function bindM8(" in html, "缺 bindM8"
    assert "function renderOverview(" in html
    for panel in ("overview", "m8", "m1", "m2", "m3", "m4", "m5", "m6", "m7"):
        assert f'id="panel-{panel}"' in html
    assert "数据-nav" in html or "data-nav" in html


def test_demo_no_silent_facts_in_channel_drafts(data):
    """渠道稿里每条事实句都要挂可解析的编号；待核实内容不得混进事实块。"""
    known = {s["id"] for s in data["sources"]} | {p["id"] for p in data["phrases"]} | {
        r["id"] for r in data["reviews"]
    } | {f["id"] for f in data["feedback"]} | {q["id"] for q in data["questions"]}
    for d in data["channelDrafts"]:
        for b in d["blocks"]:
            assert b["refs"], f"{d['id']} 的事实块没有挂来源编号"
            for ref in b["refs"]:
                assert ref in known, f"{d['id']} 的事实块引用了不存在的编号 {ref}"
        for p in d["pending"]:
            assert p["text"], "待核实项必须有文字说明"
            for ref in p["refs"]:
                assert ref in known, f"{d['id']} 的待核实项引用了不存在的编号 {ref}"
            assert "%" not in p["text"], f"{d['id']} 的待核实项里出现了未经证实的数字"


def test_demo_spec_fr_test_traceability():
    """spec 里的每条 FR 都有一条同名测试（不许悬空）。

    命名约定：FR-001 → test_demo_fr001_*（与 002 spec 的 test_fr_001_* 刻意错开，
    避免 fr-trace 闸把本演示的测试误判成 002 spec 的覆盖）。
    """
    spec = SPEC_PATH.read_text(encoding="utf-8")
    frs = sorted(set(re.findall(r"FR-\d{3}", spec)))
    assert frs, "spec 里没有 FR 条目"
    test_src = TESTS_PATH.read_text(encoding="utf-8")
    missing = [fr for fr in frs if f"test_demo_{fr.lower().replace('-', '')}" not in test_src]
    assert not missing, f"这些 FR 没有同名测试：{missing}"
