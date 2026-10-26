"""Isolated, reproducible nine-scene review video. Never writes to the input tree."""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import html
import importlib.util
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
from decimal import Decimal

sys.dont_write_bytecode = True
OUT = Path(__file__).resolve().parent
ALLOWED = Path(r"C:\Users\24717\AppData\Local\Temp\kilo\day1024-review-video")
assert OUT == ALLOWED, "Output location is intentionally fixed for isolation"
ROOT = Path(r"D:\GitRepo-AI\FDE20261023")
VOICE, RATE, PITCH = "zh-CN-YunjianNeural", "-5%", "-5Hz"
FPS = 24
DISCLAIMER = "免责声明：本输出由 AI 辅助生成，仅用于信息整理与研究参考，不构成专业意见或决策依据。"
FFMPEG = shutil.which("ffmpeg")
FFPROBE = shutil.which("ffprobe")
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"


def local(path: Path) -> Path:
    path = path.resolve()
    assert path == OUT or OUT in path.parents, f"Outside isolated output: {path}"
    return path


def save(path: Path, content: str) -> None:
    local(path).parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def save_json(path: Path, value) -> None:
    save(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def env() -> dict:
    work = local(OUT / "tmp")
    work.mkdir(parents=True, exist_ok=True)
    return {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONUTF8": "1",
            "TEMP": str(work), "TMP": str(work)}


def run(cmd: list, label: str, cwd: Path = OUT) -> subprocess.CompletedProcess:
    print(f"[{label}]", flush=True)
    result = subprocess.run([str(x) for x in cmd], cwd=local(cwd), env=env(),
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, encoding="utf-8", errors="replace")
    save(OUT / "logs" / f"{label}.log", result.stdout)
    if result.stdout.strip():
        print(result.stdout, flush=True)
    if result.returncode:
        raise RuntimeError(f"{label}: exit {result.returncode}")
    return result


def probe(path: Path) -> dict:
    result = subprocess.run([FFPROBE, "-v", "error", "-show_format", "-show_streams",
                             "-of", "json", str(path)], env=env(), cwd=OUT,
                            check=True, capture_output=True, text=True, encoding="utf-8")
    return json.loads(result.stdout)


def money(value) -> str:
    return format(Decimal(str(value)) / Decimal(10000), ".4f").rstrip("0").rstrip(".")


def yen(value) -> str:
    return format(Decimal(str(value)), ",.0f")


def esc(value) -> str:
    return html.escape(str(value))


CSS = """
*{box-sizing:border-box}html,body{margin:0;width:1920px;height:1080px;overflow:hidden}
body{font-family:'Microsoft YaHei','Noto Sans CJK SC',sans-serif;background:#f3f3ed;color:#142c42}
.paper{position:relative;width:1920px;height:1080px;padding:62px 104px 0;background:linear-gradient(110deg,#f7f7f0,#ecefe9)}
.paper:before{content:'';position:absolute;left:0;top:0;bottom:0;width:22px;background:#18374b}
.meta{display:flex;align-items:center;justify-content:space-between;height:42px;font-size:22px;letter-spacing:2px;color:#426073}
.stamp{letter-spacing:0;font-size:24px;font-weight:700;padding:10px 19px;border:1px solid #bc7957;background:#f7ece0;color:#8d482c;border-radius:4px}
.stamp.audit{border-color:#78909b;background:#e5eceb;color:#355468}
.title{font-size:59px;line-height:1.32;margin:42px 0 0;font-weight:700;letter-spacing:-1px}
.deck{font-size:28px;color:#5d6c76;line-height:1.5;margin:17px 0 0}
.visual{position:absolute;left:104px;right:104px;top:320px;height:450px}
.row{display:flex;gap:24px;align-items:stretch}.col{flex:1;min-width:0}
.card{padding:28px 32px;background:#fffef9;border:1px solid #d7dfd9;border-radius:5px}
.card.navy{background:#18374b;color:#fafaf1;border-color:#18374b}.card.red{background:#f5e7df;border-color:#d7ac94;color:#8a3b26}
.eyebrow{font-size:24px;color:#627986;letter-spacing:1px}.navy .eyebrow{color:#b5c9cf}
.label{font-size:32px;font-weight:700;line-height:1.4}.detail{font-size:26px;color:#586a74;line-height:1.6}.navy .detail{color:#c0d2d5}
.number{font-size:86px;line-height:1.25;font-weight:700;letter-spacing:-2px;font-family:'Microsoft YaHei',sans-serif;font-variant-numeric:tabular-nums}
.unit{font-size:29px;margin-left:10px;font-weight:400;letter-spacing:0}.arrow{font-size:44px;color:#80948f;align-self:center;flex:none}
.rule{height:1px;background:#ced9d5;margin:24px 0}.pill{display:inline-block;border:1px solid #c0d0cd;padding:8px 16px;font-size:25px;background:#e9efea;border-radius:3px}
.note{font-size:26px;color:#5b6e78;line-height:1.6}.bottomnote{position:absolute;top:718px;left:104px;right:104px;font-size:26px;color:#576c77;line-height:1.5}
.caption-safe{position:absolute;left:82px;right:82px;top:814px;height:144px;border-top:1px solid #d2ddd6;background:#e8ede7}
.footer{position:absolute;left:104px;right:104px;top:1004px;font-size:20px;display:flex;justify-content:space-between;color:#687d85}
.tiny{font-size:23px;color:#5e747c;line-height:1.5}.strong{font-weight:700;color:#18374b}.thin{font-weight:400}
.step{font-family:Georgia,serif;font-size:69px;line-height:1;color:#7c9b9b;margin-bottom:26px}
.ledger{display:grid;grid-template-columns:72px 320px 1fr;gap:22px;align-items:center;padding:22px 25px;border-bottom:1px solid #d4dfd7;background:#fffdf7}
.ledger .index{font-family:Georgia,serif;font-size:42px;color:#6d9695}.ledger .what{font-size:29px;font-weight:700}.ledger .where{font-size:26px;color:#5c717c}
.segments{height:45px;display:flex;border-radius:3px;overflow:hidden;gap:3px;margin:30px 0}.segments span{height:100%}
.cost-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:18px}.cost-item{border-top:3px solid var(--color);padding:15px 5px 10px}.cost-item b{display:block;font-size:28px;margin-bottom:8px}.cost-item em{font-size:35px;font-style:normal}
.flow{display:flex;align-items:center;gap:16px}.flow .node{flex:1;text-align:center;border:1px solid #c6d2ce;padding:25px 10px;background:#fffdf7;font-size:30px;font-weight:700;border-radius:3px}.flow .arrow{font-size:30px}
.costline{display:grid;grid-template-columns:170px 1fr 95px;gap:18px;align-items:center;font-size:24px;margin:16px 0}.track{height:13px;background:#e0e8df}.track span{display:block;height:100%;background:#557e83}
.disclaimer{margin-top:28px;padding:22px 27px;border:1px solid #c6b29d;background:#f3e9dc;font-size:26px;line-height:1.75;color:#724b32}
"""


def visual(sid: int, inputs: dict, results: dict) -> tuple[str, str, str]:
    base = next(s for s in results["scenarios"] if s["id"] == "base")
    costs = inputs["customer_costs"]
    total = results["customer_total_listed_cost"]
    vendor_cost = results["vendor_direct_cost"]
    if sid == 1:
        cards = [("01", "一个市场", "先找谁，凭什么买"), ("02", "一线出初稿", "先做哪一件事"),
                 ("03", "负责人校正", "预算、责任与验证方法")]
        body = '<div class="row">' + ''.join(
            f'<div class="card col {"navy" if i == 2 else ""}"><div class="step">{n}</div><div class="label">{t}</div><div class="detail" style="margin-top:22px">{d}</div></div>'
            for i, (n, t, d) in enumerate(cards)) + '</div>'
        return "先把下一步讲清，菜单数量排在后面。", body, "每个动作都要说清：花多少、谁负责、怎么验证。"
    if sid == 2:
        body = '<div class="row" style="align-items:center">'
        for i, (name, desc) in enumerate([("商机", "可能有生意"), ("收入", "确认了业务收入"), ("回款", "钱真正到账")]):
            if i:
                body += '<div class="arrow" style="font-size:64px;color:#a66042">≠</div>'
            body += f'<div class="card col" style="height:263px"><div class="eyebrow">不是同一口径</div><div class="number" style="font-size:68px;margin:24px 0 12px">{name}</div><div class="detail">{desc}</div></div>'
        body += '</div><div class="pill" style="margin-top:30px">随机上涨的曲线 ≠ 营销有效的证据</div>'
        return "界面能演示，不等于经营效果已获证实。", body, "真实花费、成交与回款记录：目前均未核实。"
    if sid == 3:
        rows = [("01", "客户营销支出", "客户 → 媒体、达人、制作方"),
                ("02", "软件自有收入", "客户 → 软件与试点服务费"),
                ("03", "代收代付", "经手金额不能全算自己的收入"),
                ("04", "软件交付成本", "实施、审核、模型与支持，另外扣除")]
        body = ''.join(f'<div class="ledger"><span class="index">{n}</span><span class="what">{a}</span><span class="where">{b}</span></div>' for n, a, b in rows)
        return "四本账分开看，才能知道谁花钱、谁挣到钱。", body, "此处未假设平台代收代付；如发生，经手款须单独核算。"
    if sid == 4:
        colors = ["#24465b", "#426579", "#628591", "#86a3a5", "#b28a61", "#c5aa88", "#a7b79e"]
        labels = ["媒体", "达人", "制作", "活动", "软件", "直接数据", "归属人工"]
        segments = ''.join(f'<span style="width:{float(Decimal(str(c["amount"])) / Decimal(str(total)) * 100):.5f}%;background:{color}"></span>' for c, color in zip(costs, colors))
        lines = ''.join(f'<div class="cost-item" style="--color:{color}"><b>{label}</b><em>{money(c["amount"])}<span class="unit">万</span></em></div>' for c, label, color in zip(costs, labels, colors))
        body = f'<div class="row"><div class="card navy" style="width:390px;flex:none"><div class="eyebrow">{inputs["horizon_days"]}天 · 单一市场</div><div class="number" style="margin-top:26px">{money(total)}<span class="unit">万元</span></div><div class="rule"></div><div class="detail">假设外付 {money(results["customer_assumed_external_payments"])} 万<br>归属人工为分摊成本</div></div><div class="col" style="padding:0 12px"><div class="segments">{segments}</div><div class="cost-grid">{lines}</div></div></div>'
        return "费用结构按已列项目相加，不是已批准预算。", body, "7.3万元是假设外付项合计，不是实际付款，也不等于可以省掉的钱。"
    if sid == 5:
        body = f'<div class="row"><div class="card col"><div class="eyebrow">{base["new_customers"]} 笔 × 每笔 {money(inputs["net_revenue_per_order"])} 万</div><div class="number">{money(base["net_revenue"])}<span class="unit">万</span></div><div class="label">净收入</div></div><div class="arrow">→</div><div class="card col navy"><div class="eyebrow">履约后，营销前 · 贡献率 {Decimal(str(inputs["pre_marketing_contribution_rate"])) * 100:.0f}%</div><div class="number">{money(base["incremental_pre_marketing_contribution"])}<span class="unit">万</span></div><div class="label">可抵营销的贡献</div></div><div class="arrow">−</div><div class="card col"><div class="eyebrow">已列营销投入</div><div class="number">{money(total)}<span class="unit">万</span></div><div class="label">还要再扣一次</div></div></div><div class="row" style="margin-top:22px"><div class="card red" style="flex:1;padding:17px 28px;display:flex;justify-content:space-between;align-items:center"><span class="label">营销后贡献</span><span class="number" style="font-size:58px">{money(base["net_contribution_after_marketing"])}<span class="unit">万元</span></span></div><div class="card" style="flex:1;padding:22px 28px"><span class="label">同条件下，至少 {results["break_even_orders"]} 笔才回本</span></div></div>'
        return "卖出去多少，与最后留下多少，不是一回事。", body, "教学假设：成交100%由试点新增；现实必须验证，且净收入不是回款。"
    if sid == 6:
        lines = ''.join(f'<div class="costline"><span>{esc(c["label"].replace("工时", ""))}</span><div class="track"><span style="width:{float(Decimal(str(c["amount"])) / Decimal(str(vendor_cost)) * 100):.4f}%"></span></div><span style="text-align:right">{yen(c["amount"])}</span></div>' for c in inputs["vendor_direct_costs"])
        body = f'<div class="row"><div style="flex:1.25"><div class="row" style="gap:15px"><div class="card col"><div class="eyebrow">自有服务收入</div><div class="number" style="font-size:66px">{money(results["vendor_service_revenue"])}</div><div class="detail">万元</div></div><div class="card col"><div class="eyebrow">直接交付成本</div><div class="number" style="font-size:66px">{money(vendor_cost)}</div><div class="detail">万元</div></div><div class="card col navy"><div class="eyebrow">交付贡献</div><div class="number" style="font-size:66px">{yen(results["vendor_delivery_contribution"])}</div><div class="detail">元</div></div></div><div class="pill" style="margin-top:24px">尚未扣：获客、研发、管理等费用</div></div><div class="card" style="flex:1;padding:20px 28px"><div class="eyebrow">直接交付成本分解 / 元</div>{lines}</div></div>'
        return "服务费不是净利润，人工交付成本不能漏。", body, "软件方自购数据与客户直接数据，教学情景假设为不同合同；实际采购须去重。"
    if sid == 7:
        def flow(names):
            return '<div class="flow">' + '<span class="arrow">→</span>'.join(f'<div class="node">{n}</div>' for n in names) + '</div>'
        body = '<div class="eyebrow" style="margin-bottom:15px">支出凭证链</div>' + flow(["预算项", "合同", "验收", "实付"])
        body += '<div class="tiny" style="text-align:center;margin:24px 0">活动编号关联上下两条链，保留依据与版本</div>'
        body += '<div class="eyebrow" style="margin-bottom:15px">业务结果链</div>' + flow(["内容与渠道", "去重线索", "成交", "回款"])
        return "每一笔钱，都能沿着凭证找到后续结果。", body, "负责人决定预算上限与停止线；系统负责保留证据，不代替经营判断。"
    if sid == 8:
        body = '<div class="row"><div class="card navy col"><div class="eyebrow">Agent可以帮忙</div><div class="label" style="margin:26px 0">整理证据<br>比较方案<br>改渠道文案</div><div class="detail">Skill写清输入、输出、工具与拒绝条件</div></div><div class="card col"><div class="eyebrow">确定性机制</div><div class="label" style="margin:26px 0">算术 → 代码</div><div class="rule"></div><div class="label">事实变了<br>旧审批失效</div></div><div class="card col"><div class="eyebrow">三道授权，不能混用</div><div class="label" style="margin-top:25px">内容人审</div><div class="rule"></div><div class="label">预算审批</div><div class="rule"></div><div class="label">付款授权</div></div></div>'
        return "岗位名字不是机制，内容通过也不代表付款获准。", body, "Agent查证、代码计算、负责人授权：三者边界分清。"
    if sid == 9:
        body = '<div class="row"><div class="card col"><div class="step">01</div><div class="label">确认试点边界</div><div class="detail" style="margin-top:18px">卖什么 · 哪个市场 · 谁负责</div></div><div class="card col"><div class="step">02</div><div class="label">拿历史记录</div><div class="detail" style="margin-top:18px">账单 · 成交 · 回款</div></div><div class="card col"><div class="step">03</div><div class="label">核对可取消支出</div><div class="detail" style="margin-top:18px">有凭证，再谈能省多少</div></div></div>'
        body += f'<div class="disclaimer">{DISCLAIMER}</div>'
        return "当前金额全是教学假设，不是客户预算或已经赚到的钱。", body, ""
    raise ValueError(sid)


def make_slide(sc, inputs: dict, results: dict) -> str:
    deck, body, note = visual(sc.id, inputs, results)
    monetary = sc.id in (3, 4, 5, 6)
    stamp = "教学情景 非客户预算/报价/预测" if monetary else "静态材料审计 未验证真实营销效果"
    kind = "stamp" if monetary else "stamp audit"
    footer = "所有金额均为教学假设，不是客户实绩" if monetary else "静态材料审计 / 不代表真实营销成效"
    return f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><link rel="icon" href="data:,"><title>{esc(sc.title)}</title><style>{CSS}</style></head><body><main class="paper"><header class="meta"><span>经营复盘 / 2026.10.24 / {sc.id:02d}</span><span class="{kind}">{stamp}</span></header><h1 class="title">{esc(sc.title)}</h1><p class="deck">{deck}</p><section class="visual">{body}</section><div class="bottomnote">{note}</div><div class="caption-safe" aria-label="字幕安全区"></div><footer class="footer"><span>{footer}</span><span>先把钱算清，再谈营销平台 · {sc.id:02d} / 09</span></footer></main></body></html>'''


def copy_inputs(input_dir: Path, engine_dir: Path):
    for name in ("04-视频讲解稿.md", "model-inputs.json", "model-results.json", "calculate.py"):
        src = input_dir / name
        if not src.exists():
            continue
        dst = local(OUT / "inputs" / name)
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.resolve() != dst:
            shutil.copyfile(src, dst)
    for name in ("pipeline.py", "check_subs.py", "contact_sheet.py", "vendor/ffmedia.py",
                 "vendor/plan_timeline.py", "vendor/render_pipe.py", "vendor/verify_video.py"):
        src = engine_dir / name
        dst = local(OUT / "engine" / name)
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.resolve() != dst:
            shutil.copyfile(src, dst)


def load():
    sys.path.insert(0, str(OUT / "engine"))
    import pipeline as P
    title, scenes = P.parse_script(P.read_text(OUT / "inputs" / "04-视频讲解稿.md"))
    assert [s.id for s in scenes] == list(range(1, 10))
    assert all(s.narration and s.title and s.points for s in scenes)
    inputs = json.loads((OUT / "inputs" / "model-inputs.json").read_text(encoding="utf-8"))
    spec = importlib.util.spec_from_file_location("review_calculation", OUT / "inputs" / "calculate.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    computed = json.loads(json.dumps(mod.calculate(inputs), default=mod.output))
    existing = OUT / "inputs" / "model-results.json"
    if existing.exists():
        assert computed == json.loads(existing.read_text(encoding="utf-8")), "Stale model results"
    results = computed
    assert results["customer_total_listed_cost"] == 85000
    assert results["vendor_direct_cost"] == 12500
    assert results["vendor_delivery_contribution"] == 2500
    save_json(OUT / "model-results.used.json", results)
    return P, title, scenes, inputs, results


async def synthesize(scenes) -> None:
    import edge_tts
    semaphore = asyncio.Semaphore(2)

    async def one(sc):
        name = f"scene_{sc.id:02d}"
        mp3, boundary = OUT / "audio" / f"{name}.mp3", OUT / "boundaries" / f"{name}.json"
        key = hashlib.sha256(json.dumps([sc.narration, VOICE, RATE, PITCH], ensure_ascii=False).encode()).hexdigest()
        if mp3.exists() and boundary.exists():
            old = json.loads(boundary.read_text(encoding="utf-8"))
            if old.get("request_sha256") == key and old.get("audio_sha256") == digest(mp3):
                sc.boundaries = old["boundaries"]
                print(f"[tts cached] {name}", flush=True)
                return
        async with semaphore:
            for attempt in range(3):
                try:
                    comm = edge_tts.Communicate(sc.narration, VOICE, rate=RATE, pitch=PITCH,
                                               boundary="SentenceBoundary")
                    audio, bounds = bytearray(), []
                    async for chunk in comm.stream():
                        if chunk["type"] == "audio":
                            audio.extend(chunk["data"])
                        elif chunk["type"] == "SentenceBoundary":
                            bounds.append({k: chunk[k] for k in ("offset", "duration", "text")})
                    assert audio and bounds, f"Empty audio/boundaries: {name}"
                    local(mp3).parent.mkdir(parents=True, exist_ok=True)
                    mp3.write_bytes(audio)
                    sc.boundaries = bounds
                    save_json(boundary, {"scene": sc.id, "voice": VOICE, "rate": RATE, "pitch": PITCH,
                                         "text": sc.narration, "request_sha256": key,
                                         "audio_sha256": digest(mp3), "offset_unit": "100ns",
                                         "boundaries": bounds})
                    print(f"[tts ready] {name}: {len(audio)} bytes, {len(bounds)} sentences", flush=True)
                    return
                except Exception:
                    if attempt == 2:
                        raise
                    await asyncio.sleep(2 * (attempt + 1))
    await asyncio.gather(*(one(sc) for sc in scenes))


def subtitle_files(P, scenes):
    subs = P.build_subtitles(scenes, fps=FPS)
    assert subs, "No subtitles"
    # The approved narration is not rewritten. Only line breaks are added.
    def wrap(text: str) -> str:
        if len(text) <= 28:
            return text
        candidates = [i + 1 for i, ch in enumerate(text[:-1]) if ch in "，。；：？！、"
                      and max(i + 1, len(text) - i - 1) <= 28]
        cut = min(candidates, key=lambda i: abs(i - len(text) / 2)) if candidates else len(text) // 2
        assert max(cut, len(text) - cut) <= 28, f"Caption too long: {text}"
        return text[:cut] + "\n" + text[cut:]
    for i, sub in enumerate(subs):
        sub.text = wrap(sub.text)
        if i + 1 < len(subs):
            # Boundary durations can overlap the next event by one or two frames.
            sub.end = min(sub.end, subs[i + 1].start)
        assert sub.end > sub.start
    for scene in scenes:
        rendered = "".join(s.text for s in subs if s.scene == scene.id)
        assert "".join(rendered.split()) == "".join(scene.narration.split()), f"Caption/source mismatch: {scene.id}"
    ass = P.build_ass(subs, "先把钱算清，再谈营销平台")
    ass = ass.replace("52,&H00F2F2EC,&H00F2F2EC,&H00101010,&HA0000000", "46,&H00F7F6F2,&H00F7F6F2,&H003C2819,&H003C2819")
    ass = ass.replace(",100,100,0,0,1,3,1,2,90,90,170,1", ",100,100,0,0,3,14,0,2,125,125,140,1")
    save(OUT / "subs.ass", ass)
    def stamp(t, sep):
        ms = round(t * 1000)
        h, rem = divmod(ms, 3600000)
        m, rem = divmod(rem, 60000)
        s, ms = divmod(rem, 1000)
        return f"{h:02}:{m:02}:{s:02}{sep}{ms:03}"
    srt = "\n\n".join(f"{i}\n{stamp(s.start, ',')} --> {stamp(s.end, ',')}\n{s.text}" for i, s in enumerate(subs, 1))
    vtt = "WEBVTT\n\n" + "\n\n".join(f"{stamp(s.start, '.')} --> {stamp(s.end, '.')}\n{s.text}" for s in subs)
    save(OUT / "subs.srt", srt + "\n")
    save(OUT / "subs.vtt", vtt + "\n")
    save_json(OUT / "subtitles.json", [vars(s) for s in subs])
    return subs


def screenshots(scenes, inputs, results):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            str(local(OUT / "browser-profile")), executable_path=EDGE, headless=True,
            viewport={"width": 1920, "height": 1080}, device_scale_factor=1,
            locale="zh-CN", reduced_motion="reduce", downloads_path=str(OUT / "downloads"),
            args=["--disable-gpu", "--disable-breakpad", "--disable-crash-reporter", "--no-first-run"],
            env=env())
        try:
            page = context.new_page()
            page.route("http://**/*", lambda route: route.abort())
            page.route("https://**/*", lambda route: route.abort())
            errors, layouts = [], []
            page.on("pageerror", lambda err: errors.append(str(err)))
            for sc in scenes:
                target = OUT / "html" / f"scene_{sc.id:02d}.html"
                save(target, make_slide(sc, inputs, results))
                page.goto(target.as_uri(), wait_until="load")
                page.evaluate("() => document.fonts.ready")
                info = page.evaluate("""() => {
                  const r = e => {const b=e.getBoundingClientRect();return {top:b.top,bottom:b.bottom,left:b.left,right:b.right}};
                  return {body:{width:document.body.scrollWidth,height:document.body.scrollHeight},
                    font:document.fonts.check('32px "Microsoft YaHei"'),
                    title:r(document.querySelector('.title')),
                    cards:[...document.querySelectorAll('.visual .card,.visual .ledger,.visual .disclaimer')].map(r),
                    disclaimer:document.querySelector('.disclaimer')?.textContent || null};
                }""")
                assert info["body"] == {"width": 1920, "height": 1080}
                assert info["font"]
                assert info["title"]["right"] <= 1816
                assert all(b["bottom"] < 805 for b in info["cards"]), info
                if sc.id == 9:
                    assert info["disclaimer"] == DISCLAIMER
                local(OUT / "frames").mkdir(exist_ok=True)
                page.screenshot(path=str(OUT / "frames" / f"scene_{sc.id:02d}.png"),
                                full_page=False, animations="disabled", caret="hide")
                layouts.append({"scene": sc.id, **info})
            assert not errors, errors
            save_json(OUT / "layout-check.json", {"errors": errors, "layouts": layouts})
        finally:
            context.close()


def prepare(args):
    assert FFMPEG and FFPROBE and Path(EDGE).exists()
    copy_inputs(Path(args.input_dir), Path(args.engine_dir))
    P, title, scenes, inputs, results = load()
    print(f"[source] {len(scenes)} scenes / {sum(len(s.narration) for s in scenes)} narration chars", flush=True)
    asyncio.run(synthesize(scenes))
    cursor, wavs = 0.0, []
    for sc in scenes:
        wav = OUT / "audio" / f"scene_{sc.id:02d}.wav"
        run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-i", OUT / "audio" / f"scene_{sc.id:02d}.mp3",
             "-ac", "1", "-ar", "48000", "-c:a", "pcm_s16le", wav], f"decode-{sc.id:02d}")
        duration = float(probe(wav)["format"]["duration"])
        sc.audio, sc.start, sc.end = wav.name, cursor, cursor + duration
        cursor = sc.end
        wavs.append(wav)
    cmd = [FFMPEG, "-y", "-hide_banner", "-loglevel", "error"]
    for wav in wavs:
        cmd += ["-i", wav]
    graph = "".join(f"[{i}:a]" for i in range(len(wavs))) + f"concat=n={len(wavs)}:v=0:a=1[outa]"
    cmd += ["-filter_complex", graph, "-map", "[outa]", "-ac", "1", "-ar", "48000", "-c:a", "pcm_s16le", OUT / "audio" / "narration_full.wav"]
    run(cmd, "concat-pcm")
    subs = subtitle_files(P, scenes)
    save_json(OUT / "scenes.json", [vars(s) for s in scenes])
    screenshots(scenes, inputs, results)
    manifest = {"fps": FPS, "scenes": [{"id": s.id, "audio": s.audio,
                 "files": [f"scene_{s.id:02d}.png"], "weights": [1]} for s in scenes]}
    save_json(OUT / "steps.json", manifest)
    run([sys.executable, "-B", OUT / "engine/vendor/plan_timeline.py", "--manifest", OUT / "steps.json",
         "--frames-dir", OUT / "frames", "--audio-dir", OUT / "audio", "--out", OUT / "timeline.json"], "plan-timeline")
    save_json(OUT / "source-manifest.json", {"voice": VOICE, "rate": RATE, "pitch": PITCH,
              "narration_chars": sum(len(s.narration) for s in scenes), "subtitle_events": len(subs),
              "audio_duration_seconds": float(probe(OUT / "audio/narration_full.wav")["format"]["duration"]),
              "sources": {p.name: digest(p) for p in (OUT / "inputs").iterdir() if p.is_file()},
              "motion": "Pillow floating-point crop; 1.04x maximum; no zoompan",
              "privacy": "Only approved scene narration sent to Edge TTS; local slides block HTTP(S).",
              "disclaimer": DISCLAIMER})
    print(f"[prepared] audio {cursor:.3f}s / subtitles {len(subs)}", flush=True)


def render():
    run([sys.executable, "-B", OUT / "engine/vendor/render_pipe.py", "--timeline", OUT / "timeline.json",
         "--audio", OUT / "audio/narration_full.wav", "--out", OUT / "video_nosub.mp4", "--crf", "20"], "render-subpixel")
    run([FFMPEG, "-y", "-hide_banner", "-loglevel", "info", "-i", OUT / "video_nosub.mp4",
         "-vf", "ass=filename=subs.ass", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
         "-pix_fmt", "yuv420p", "-c:a", "copy", "-movflags", "+faststart", OUT / "final.mp4"], "burn-subtitles")


def contact_sheet():
    from PIL import Image, ImageDraw, ImageFont
    timeline = json.loads((OUT / "timeline.json").read_text(encoding="utf-8"))
    tiles, cursor, entries = [], 0.0, []
    font = ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", 22)
    for seg in timeline["segments"]:
        t = cursor + seg["duration"] / 2
        cursor += seg["duration"]
        path = OUT / "midpoints" / f"scene_{seg['scene']:02d}.png"
        local(path).parent.mkdir(parents=True, exist_ok=True)
        run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-ss", str(t), "-i", OUT / "final.mp4",
             "-frames:v", "1", path], f"midpoint-{seg['scene']:02d}")
        tile = Image.new("RGB", (640, 398), "#142c42")
        tile.paste(Image.open(path).convert("RGB").resize((640, 360), Image.Resampling.LANCZOS), (0, 0))
        ImageDraw.Draw(tile).text((14, 365), f"{seg['scene']:02d}  /  {t:.2f}s", font=font, fill="#f2f1e8")
        tiles.append(tile)
        entries.append({"scene": seg["scene"], "time": t, "file": str(path)})
    sheet = Image.new("RGB", (1944, 1218), "#c8d3ce")
    for i, tile in enumerate(tiles):
        sheet.paste(tile, (6 + i % 3 * 646, 6 + i // 3 * 404))
    sheet.save(local(OUT / "contact-sheet.png"))
    save_json(OUT / "midpoints.json", entries)


def verify():
    vendor = OUT / "engine/vendor/verify_video.py"
    run([sys.executable, "-B", vendor, "--video", OUT / "video_nosub.mp4", "--timeline", OUT / "timeline.json",
         "--audio", OUT / "audio/narration_full.wav", "--tmp-dir", OUT / "verify"], "verify-picture")
    # Check every scene's continuous motion, not only the vendor script's first eligible scene.
    for sid in range(2, 10):
        run([sys.executable, "-B", vendor, "--video", OUT / "video_nosub.mp4", "--timeline", OUT / "timeline.json",
             "--jitter-only", "--jitter-scene", sid, "--tmp-dir", OUT / "verify" / f"scene_{sid:02d}"], f"verify-jitter-{sid:02d}")
    run([sys.executable, "-B", OUT / "engine/check_subs.py", "--ass", OUT / "subs.ass", "--timeline", OUT / "timeline.json",
         "--video", OUT / "final.mp4", "--video-nosub", OUT / "video_nosub.mp4", "--fps", FPS,
         "--tmp-dir", OUT / "subs-check"], "verify-subtitles")
    info, audio = probe(OUT / "final.mp4"), probe(OUT / "audio/narration_full.wav")
    video_stream = next(s for s in info["streams"] if s["codec_type"] == "video")
    audio_stream = next(s for s in info["streams"] if s["codec_type"] == "audio")
    assert (video_stream["codec_name"], video_stream["width"], video_stream["height"], video_stream["pix_fmt"], video_stream["avg_frame_rate"]) == ("h264", 1920, 1080, "yuv420p", "24/1")
    assert audio_stream["codec_name"] == "aac"
    delta = abs(float(info["format"]["duration"]) - float(audio["format"]["duration"]))
    assert delta <= 0.5
    atoms, pos = [], 0
    with (OUT / "final.mp4").open("rb") as f:
        size_total = (OUT / "final.mp4").stat().st_size
        while pos + 8 <= size_total:
            f.seek(pos)
            size, kind = struct.unpack(">I4s", f.read(8))
            if size == 1:
                size = struct.unpack(">Q", f.read(8))[0]
            atoms.append(kind.decode("ascii"))
            if size == 0:
                break
            pos += size
    assert atoms.index("moov") < atoms.index("mdat")
    run([FFMPEG, "-hide_banner", "-v", "error", "-i", OUT / "final.mp4", "-f", "null", "-"], "decode-entire-final")
    contact_sheet()
    save_json(OUT / "ffprobe-final.json", info)
    save_json(OUT / "verification.json", {"duration_difference_seconds": delta, "atoms": atoms,
              "video": {k: video_stream[k] for k in ("codec_name", "width", "height", "pix_fmt", "avg_frame_rate")},
              "audio_codec": audio_stream["codec_name"], "picture_all_nine": "passed",
              "jitter_all_nine": "passed", "subtitle_three_axes_and_burn_sample": "passed",
              "whole_file_decode": "passed", "http_range": "not tested; no server started",
              "voice_subjective_quality": "not guaranteed by metadata; no human listening sign-off"})
    print("[verified] ffprobe, faststart, duration, all-scene midpoint match, all-scene jitter, captions, full decode", flush=True)


def playback():
    from playwright.sync_api import sync_playwright
    timeline = json.loads((OUT / "timeline.json").read_text(encoding="utf-8"))
    page_html = '<!doctype html><meta charset="utf-8"><link rel="icon" href="data:,"><title>Local video verification</title><style>body{background:#142c42;color:#fff;font-family:sans-serif}video{width:min(96vw,1280px);display:block;margin:20px auto}</style><video id="v" controls preload="auto" src="final.mp4"><track kind="subtitles" src="subs.vtt" srclang="zh" label="Chinese"></video>'
    save(OUT / "player.html", page_html)
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(str(OUT / "playback-profile"), executable_path=EDGE,
                    headless=True, viewport={"width": 1440, "height": 950}, env=env(),
                    args=["--disable-gpu", "--disable-breakpad", "--allow-file-access-from-files"])
        try:
            page = context.new_page()
            errors = []
            page.on("pageerror", lambda err: errors.append(str(err)))
            page.goto((OUT / "player.html").as_uri(), wait_until="load")
            page.wait_for_function("() => v.readyState >= 2 && v.videoWidth === 1920")
            start, checks = 0.0, []
            for seg in timeline["segments"]:
                t = start + seg["duration"] / 2
                start += seg["duration"]
                result = page.evaluate("""async t => {
                    const v=document.getElementById('v');
                    await new Promise((resolve,reject)=>{v.addEventListener('seeked',resolve,{once:true});v.addEventListener('error',()=>reject(new Error('video error')),{once:true});v.currentTime=t;});
                    const c=document.createElement('canvas');c.width=192;c.height=108;
                    const x=c.getContext('2d');x.drawImage(v,0,0,192,108);
                    const d=x.getImageData(0,0,192,108).data;let sum=0;const colors=new Set();
                    for(let i=0;i<d.length;i+=4){sum+=(d[i]+d[i+1]+d[i+2])/3;colors.add(`${d[i]>>3},${d[i+1]>>3},${d[i+2]>>3}`)}
                    return {time:v.currentTime,mean_luma:sum/(d.length/4),distinct_colors:colors.size,ready_state:v.readyState};
                }""", t)
                assert 5 < result["mean_luma"] < 252 and result["distinct_colors"] > 30, result
                checks.append({"scene": seg["scene"], **result})
            played = page.evaluate("""async () => {v.muted=true;await v.play();return {paused:v.paused,currentTime:v.currentTime,videoWidth:v.videoWidth,videoHeight:v.videoHeight}}""")
            assert not played["paused"]
            page.screenshot(path=str(OUT / "playback.png"))
            assert not errors, errors
            save_json(OUT / "browser-playback.json", {"local_file_seek_all_scenes": checks,
                       "play_started": played, "page_errors": errors, "audio_listening": "not human-audited",
                       "http_range": "not applicable to file URL; server delivery not tested"})
        finally:
            context.close()
    print("[playback] local Edge play and nine seek/decode probes passed", flush=True)


def supplement():
    import numpy as np
    from PIL import Image
    subtitles = json.loads((OUT / "subtitles.json").read_text(encoding="utf-8"))
    scenes = json.loads((OUT / "scenes.json").read_text(encoding="utf-8"))
    by_id = {s["id"]: s for s in scenes}
    for sid, scene in by_id.items():
        text = "".join(s["text"] for s in subtitles if s["scene"] == sid)
        assert "".join(text.split()) == "".join(scene["narration"].split())
    for i, sub in enumerate(subtitles):
        scene = by_id[sub["scene"]]
        assert scene["start"] - 1 / FPS <= sub["start"] < sub["end"] <= scene["end"] + 1 / FPS
        if i:
            assert sub["start"] >= subtitles[i - 1]["end"]
    target = local(OUT / "caption-probes")
    target.mkdir(exist_ok=True)

    def difference(t: float, name: str):
        paths = []
        for suffix, video in (("sub", "final.mp4"), ("clean", "video_nosub.mp4")):
            path = target / f"{name}-{suffix}.png"
            run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-ss", f"{t:.6f}",
                 "-i", OUT / video, "-frames:v", "1", path], f"caption-probe-{name}-{suffix}")
            paths.append(path)
        images = [np.asarray(Image.open(p).convert("RGB"), dtype="float32") for p in paths]
        delta = np.max(np.abs(images[0] - images[1]), axis=2)
        mae = float(np.abs(images[0][790:990] - images[1][790:990]).mean())
        active = np.flatnonzero((delta[790:990] > 30).sum(axis=1) > 20)
        bounds = [int(active[0] + 790), int(active[-1] + 790)] if len(active) else None
        return {"time": t, "band_mae": mae, "caption_y_bounds": bounds}

    present = []
    for i, sub in enumerate(subtitles):
        result = difference((sub["start"] + sub["end"]) / 2, f"event-{i + 1:02d}")
        assert result["band_mae"] > 1 and result["caption_y_bounds"], result
        assert 805 <= result["caption_y_bounds"][0] <= result["caption_y_bounds"][1] <= 970, result
        present.append({"event": i + 1, "scene": sub["scene"], **result})
    empty_times = [0.0]
    for left, right in zip(subtitles, subtitles[1:]):
        if right["start"] - left["end"] >= 0.10:
            empty_times.append((right["start"] + left["end"]) / 2)
        if len(empty_times) == 3:
            break
    assert len(empty_times) == 3
    absent = [difference(t, f"empty-{i}") for i, t in enumerate(empty_times)]
    assert max(p["band_mae"] for p in absent) < 1, absent
    assert min(p["band_mae"] for p in present) > 2 * max(p["band_mae"] for p in absent)
    save_json(OUT / "caption-verification.json", {
        "source_text_exact_ignoring_whitespace": True, "event_count": len(subtitles),
        "event_overlap_count": 0, "scene_identity_check": "passed",
        "all_event_midpoint_burn_and_safety": present, "empty_gap_counterexamples": absent,
        "note": "Supplements check_subs.py's warning: gaps under 0.6s exist and were sampled explicitly."})
    run([FFMPEG, "-hide_banner", "-i", OUT / "audio/narration_full.wav", "-af", "volumedetect",
         "-f", "null", "-"], "audio-levels")
    final_probe = json.loads((OUT / "ffprobe-final.json").read_text(encoding="utf-8"))
    final = OUT / "final.mp4"
    delivery = {
        "directory": str(OUT), "final_video": str(final), "bytes": final.stat().st_size,
        "sha256": digest(final), "duration_seconds": float(final_probe["format"]["duration"]),
        "voice": {"name": VOICE, "rate": RATE, "pitch": PITCH, "boundary": "SentenceBoundary"},
        "subtitles": len(subtitles), "scenes": len(scenes),
        "verification_files": ["verification.json", "caption-verification.json", "browser-playback.json",
                               "ffprobe-final.json", "layout-check.json", "source-manifest.json"],
        "publish_files": ["final.mp4", "subs.ass", "subs.srt", "subs.vtt", "audio/narration_full.wav",
                          "contact-sheet.png", "frames/", "html/", "midpoints/", "boundaries/", "timeline.json",
                          "steps.json", "scenes.json", "subtitles.json", "produce.py", "reproduce.ps1", "engine/", "inputs/"],
        "do_not_publish": ["browser-profile/", "playback-profile/", "tmp/", "downloads/"],
        "limitations": ["No human listening approval; low-pitch male voice is a selected synthetic voice, not a biological claim.",
                        "SentenceBoundary timing; within-sentence split timing is proportional, not forced phoneme alignment.",
                        "Local file playback and seek verified; HTTP Range was not tested and no server was started.",
                        "Teaching scenarios only; no real marketing effectiveness, budget, supplier quote, or prediction validated."]}
    save_json(OUT / "delivery.json", delivery)
    print(json.dumps({k: delivery[k] for k in ("duration_seconds", "bytes", "sha256", "subtitles", "scenes")}), flush=True)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=("prepare", "render", "verify", "playback", "supplement", "all"), default="all")
    parser.add_argument("--input-dir", default=str(ROOT / "assets/day1024/review-20261024"))
    parser.add_argument("--engine-dir", default=str(ROOT / "tools/video"))
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    os.environ.update({k: v for k, v in env().items() if k in ("TEMP", "TMP", "PYTHONDONTWRITEBYTECODE", "PYTHONUTF8")})
    if args.stage in ("prepare", "all"):
        prepare(args)
    if args.stage in ("render", "all"):
        render()
    if args.stage in ("verify", "all"):
        verify()
    if args.stage in ("playback", "all"):
        playback()
    if args.stage in ("supplement", "all"):
        supplement()


if __name__ == "__main__":
    main()
