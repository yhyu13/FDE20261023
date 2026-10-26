"""booth_2 构建脚本：Edge TTS 口播 → 词级时间戳 → 动作提示点 / 字幕 → 交互幻灯片 + HyperFrames 视频工程。

用法（在仓库根目录）：
    python assets/day1025/booth/booth_2/build.py            # 全量：合成口播 + 出 timings + 渲染 slides/video
    python assets/day1025/booth/booth_2/build.py --skip-tts # 复用已有 mp3/words.json，只重算时间与产物

产物：
    tts/sN.mp3            每页一段口播（edge-tts，zh-CN-YunxiNeural 轻柔男声，rate +4%）
    tts/words.json        词级边界缓存（--skip-tts 时复用）
    tts/timings.json      每页时长、字幕分段、动作提示点（秒，相对本页起点）
    tts/timings.js        同上，挂 window.BOOTH_TIMINGS，供外部页面在 file:// 下读
    slides.html           由 slides.src.html 注入 timings 生成的交互幻灯片（双击即开）
    video/index.html      由 video/index.src.html 填时间的 HyperFrames 合成
    video/assets/*.mp3    口播拷贝，供 HyperFrames 混音

时长一律 ffprobe 实测，不估算。
"""
from __future__ import annotations

import argparse
import asyncio
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TTS = HERE / "tts"
VIDEO = HERE / "video"
VOICE = "zh-CN-YunxiNeural"    # 轻柔男声（云希）
RATE = "+4%"
LEAD_IN = 0.6   # 口播前气口
TAIL = 1.0      # 口播后收尾

# ---------------------------------------------------------------------------
# 分镜：四页 = 封面 / 能力一 / 能力二 / 收尾
# cue 的 key 会出现在 slides.src.html 的 data-cue 与 video/index.src.html 的时间表里
# ---------------------------------------------------------------------------
SLIDES = [
    {
        "id": "s1",
        "title": "封面 · 七步闭环与调研结论",
        "text": "北美十四校二组，为一家客车制造企业搭建的全域获客模型。"
                "闭环七步，内容资产引擎打头，问题库和找客户模型紧随其后。"
                "客户调研的结论先放这儿：十二个提问，八个有可用事实，"
                "三个要说清还没到哪一步，一个没有依据。"
                "这一分钟，只看最前面的两项能力："
                "先弄清客户在问什么，再据此把客户找出来。",
        "cues": {"pipe": "闭环七步", "survey": "十二个提问", "cards": "两项能力"},
    },
    {
        "id": "s2",
        "title": "能力一 · CQ 行业问题库",
        "text": "第一项，行业问题库。"
                "公交运营商、海外客户、行业伙伴，三类客群的十二个真实提问，"
                "覆盖官网、公众号、销售推介、展会四类渠道。"
                "每条都带可用事实和必须守住的边界。"
                "看覆盖矩阵，海外客户在公众号上是空白，这就是要补的缺口。"
                "分级不靠人工拍板，引擎抽样复核三百二十条，准确率九成一以上。"
                "再看这一条：有没有数据证明运营成本下降百分之三十？"
                "审核已判待补依据，证据未核实之前，禁止它进入任何对外内容。",
        "cues": {
            "seg1": "公交运营商",
            "seg2": "海外客户",
            "seg3": "行业伙伴",
            "chans": "四类渠道",
            "ev": "必须守住的边界",
            "matrix": "覆盖矩阵",
            "recheck": "抽样复核三百二十条",
            "open": "再看这一条",
            "block": "禁止",
        },
    },
    {
        "id": "s3",
        "title": "能力二 · 找客户模型定制",
        "text": "第二项，找客户模型定制。"
                "输入产品品类、典型客户描述、应用场景、目标区域和排除对象，"
                "系统生成十条筛选规则，命中量逐条列清楚。"
                "渠道分两层：关系层看商机推进，算法层看完播与单线索成本。"
                "模型评估四项，两项达标，海外决策人覆盖和成本口径还要补。"
                "现在改一个输入，目标区域加上非洲，规则当场重算，"
                "预计目标企业数和三档匹配分布同步更新。",
        "cues": {
            "inputs": "输入产品品类",
            "rules": "十条筛选规则",
            "layers": "渠道分两层",
            "eval": "模型评估四项",
            "edit": "目标区域加上非洲",
            "rerun": "规则当场重算",
            "pool": "预计目标企业数",
            "bars": "三档匹配",
        },
    },
    {
        "id": "s4",
        "title": "收尾",
        "text": "问题库决定说什么，找客户模型决定对谁说。"
                "客户考核的不是内容火不火，是我能不能信你。"
                "后面五步，客户画像、营销内容、全渠道获客、自动化，加上持续学习，都从这两步接出去。"
                "完整七步闭环和十块面板，欢迎到交互版亲手点一遍。"
                "画面数据均为演示用模拟数据。",
        "cues": {"c1": "问题库", "c2": "找客户模型", "trust": "信你",
                 "rest": "后面五步", "cta": "交互版", "note": "模拟数据"},
    },
]
CAPTION_MAX = 26  # 字幕单行字数上限


# ---------------------------------------------------------------------------
# 工具
# ---------------------------------------------------------------------------
def ffprobe_duration(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    return round(float(out), 3)


async def synth(slide: dict) -> list[dict]:
    import edge_tts

    comm = edge_tts.Communicate(slide["text"], VOICE, rate=RATE, boundary="WordBoundary")
    mp3 = TTS / f"{slide['id']}.mp3"
    words: list[dict] = []
    with mp3.open("wb") as fh:
        async for chunk in comm.stream():
            if chunk["type"] == "audio":
                fh.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                words.append({"t": round(chunk["offset"] / 1e7, 3),
                              "d": round(chunk["duration"] / 1e7, 3),
                              "w": chunk["text"]})
    if not words:
        raise RuntimeError(f"{slide['id']}: edge-tts 未返回词边界，无法对齐动作点")
    return words


def align(text: str, words: list[dict]) -> list[dict]:
    """把每个词边界对回正文字符位置；对不上的词（数字读法被改写等）不推进游标。"""
    pos = 0
    for w in words:
        idx = text.find(w["w"], pos, pos + 40)
        if idx >= 0:
            w["c"] = idx
            pos = idx + len(w["w"])
        else:
            w["c"] = None
    return [w for w in words if w["c"] is not None]


def time_at_char(words: list[dict], ci: int) -> float:
    best = words[0]["t"]
    for w in words:
        if w["c"] <= ci:
            best = w["t"]
        else:
            break
    return best


def split_captions(text: str) -> list[tuple[int, str]]:
    parts: list[tuple[int, str]] = []
    for m in re.finditer(r"[^。！？；]+[。！？；]?", text):
        seg, start = m.group(0), m.start()
        if len(seg) <= CAPTION_MAX:
            parts.append((start, seg))
            continue
        buf, bstart = "", start
        for sm in re.finditer(r"[^，、]+[，、]?", seg):
            piece = sm.group(0)
            if buf and len(buf) + len(piece) > CAPTION_MAX:
                parts.append((bstart, buf))
                buf, bstart = "", start + sm.start()
            buf += piece
        if buf:
            parts.append((bstart, buf))
    return [(s, t.rstrip("，、；：")) for s, t in parts if t.strip()]


# ---------------------------------------------------------------------------
# timings
# ---------------------------------------------------------------------------
def build_timings(skip_tts: bool) -> dict:
    TTS.mkdir(exist_ok=True)
    cache = TTS / "words.json"
    if skip_tts:
        words_by_slide = json.loads(cache.read_text(encoding="utf-8"))
    else:
        words_by_slide = {}
        for s in SLIDES:
            print(f"[tts] {s['id']} {s['title']} …", flush=True)
            words_by_slide[s["id"]] = asyncio.run(synth(s))
        cache.write_text(json.dumps(words_by_slide, ensure_ascii=False, indent=1), encoding="utf-8")

    out = {"voice": VOICE, "rate": RATE, "slides": []}
    for s in SLIDES:
        words = align(s["text"], [dict(w) for w in words_by_slide[s["id"]]])
        dur = ffprobe_duration(TTS / f"{s['id']}.mp3")
        cues = {}
        for cid, kw in s["cues"].items():
            ci = s["text"].find(kw)
            if ci < 0:
                raise ValueError(f"{s['id']} cue {cid}: 关键词「{kw}」不在正文里")
            cues[cid] = time_at_char(words, ci)
        caps = []
        segs = split_captions(s["text"])
        for i, (ci, seg) in enumerate(segs):
            st = time_at_char(words, ci)
            en = time_at_char(words, segs[i + 1][0]) if i + 1 < len(segs) else dur
            caps.append({"t": st, "e": round(max(en, st + 0.4), 3), "x": seg})
        out["slides"].append({
            "id": s["id"], "title": s["title"], "text": s["text"],
            "audio": f"tts/{s['id']}.mp3", "duration": dur, "cues": cues, "captions": caps,
        })
        print(f"[ok] {s['id']} {dur:6.2f}s  {len(caps)} 条字幕  cues={ {k: round(v, 2) for k, v in cues.items()} }")
    (TTS / "timings.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    (TTS / "timings.js").write_text(
        "window.BOOTH_TIMINGS = " + json.dumps(out, ensure_ascii=False) + ";\n", encoding="utf-8")
    return out


# ---------------------------------------------------------------------------
# 交互幻灯片：slides.src.html → slides.html（timings 注入，单文件可发）
# ---------------------------------------------------------------------------
def build_slides(t: dict) -> None:
    src = (HERE / "slides.src.html").read_text(encoding="utf-8")
    marker = "/*TIMINGS*/null"
    if marker not in src:
        raise ValueError("slides.src.html 缺少占位符 /*TIMINGS*/null")
    src = src.replace(marker, json.dumps(t, ensure_ascii=False))
    if "/*TIMINGS*/" in src:
        raise ValueError("timings 注入后仍残留占位符")
    (HERE / "slides.html").write_text(src, encoding="utf-8")
    print(f"[slides] slides.html 已生成（{len(src)} 字符，timings 已内联）")


# ---------------------------------------------------------------------------
# HyperFrames 视频工程
# ---------------------------------------------------------------------------
def build_video(t: dict) -> None:
    src = (VIDEO / "index.src.html").read_text(encoding="utf-8")
    comp_dir = VIDEO / "compositions"
    assets = VIDEO / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    start, scenes = 0.0, []
    for s in t["slides"]:
        slot = round(LEAD_IN + s["duration"] + TAIL, 3)
        scenes.append({**s, "start": round(start, 3), "slot": slot, "voice_at": round(start + LEAD_IN, 3)})
        shutil.copyfile(TTS / f"{s['id']}.mp3", assets / f"{s['id']}.mp3")
        start += slot
    total = round(start, 3)
    by_id = {s["id"]: s for s in scenes}

    # --- 合成文件：compositions/<id>.src.html → <id>.html ---
    # 场景时钟从 0 起，口播在 LEAD_IN 后开始，故 cue 时刻 = LEAD_IN + timings 里的 cue
    # 占位符：{{CUE_k}} 起始秒；{{CUEEND_k}} 结束秒（本场结束）；/*CAPTIONS*/null → 字幕组
    if comp_dir.exists():
        for f in sorted(comp_dir.glob("*.src.html")):
            sid = f.name.split(".")[0]
            if sid not in by_id:
                raise ValueError(f"{f.name}: 找不到对应分镜 {sid}")
            s = by_id[sid]
            text = f.read_text(encoding="utf-8")
            caps = []
            segs = s["captions"]
            for i, c in enumerate(segs):
                st = round(LEAD_IN + c["t"], 3)
                en = round(LEAD_IN + c["e"], 3)
                caps.append(f'<div class="cap clip" data-start="{st}" data-duration="{round(en - st, 3)}">{c["x"]}</div>')
            text = text.replace("/*CAPTIONS*/null", "\n".join(caps))
            for k, v in s["cues"].items():
                at = round(LEAD_IN + v, 3)
                text = text.replace("{{CUE_" + k + "}}", f"{at}")
                text = text.replace("{{CUEEND_" + k + "}}", f"{round(s['slot'] - at, 3)}")
            if "{{" in text:
                raise ValueError(f"{f.name}: 还有没填的占位符")
            (comp_dir / f"{sid}.html").write_text(text, encoding="utf-8")
        print(f"[video] compositions/ 已渲染 {len(list(comp_dir.glob('s*.html')))} 个场景")

    rep = {"{{TOTAL}}": f"{total}"}
    for sc in scenes:
        k = sc["id"].upper()
        rep[f"{{{{{k}_START}}}}"] = f"{sc['start']}"
        rep[f"{{{{{k}_DUR}}}}"] = f"{sc['slot']}"
        rep[f"{{{{{k}_VOICE}}}}"] = f"{sc['voice_at']}"
        rep[f"{{{{{k}_VDUR}}}}"] = f"{sc['duration']}"
    for a, b in rep.items():
        if a not in src:
            raise ValueError(f"video/index.src.html 缺占位符 {a}")
        src = src.replace(a, b)
    left = re.findall(r"\{\{[A-Z0-9_]+\}\}", src)
    if left:
        raise ValueError(f"还有没填的占位符：{left}")
    (VIDEO / "index.html").write_text(src, encoding="utf-8")
    print(f"[video] video/index.html 已生成，总长 {total}s，{len(scenes)} 场")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-tts", action="store_true", help="复用 tts/ 下已有 mp3 与 words.json")
    args = ap.parse_args()
    t = build_timings(args.skip_tts)
    build_slides(t)
    if (VIDEO / "index.src.html").exists():
        build_video(t)
    return 0


if __name__ == "__main__":
    sys.exit(main())
