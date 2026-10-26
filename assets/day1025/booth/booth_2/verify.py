"""booth_2 交付前静态校验：不依赖浏览器。

校验项：
 1. slides.html 的 <script> 语法可解析（node --check 由外部做，这里做结构校验）
 2. timings 已内联，4 页时长与 ffprobe 实测一致
 3. 每页 data-cue 与 timings.cues 双向齐全（不错配、不缺失）
 4. CQ 客群×渠道矩阵：slides 动态算法 vs s2 composition 静态表，数字一致
 5. video/compositions/*.html 无未填占位符
 6. slides.html 无人工操控入口（onclick / data-goto / 键盘翻页），仅留音频解锁监听
 7. 口播文案里的 cue 关键词都能在正文找到（build.py 已查，这里复核注入值）
"""
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TTS = HERE / "tts"
fails: list[str] = []


def check(cond: bool, msg: str) -> None:
    print(("  [ok] " if cond else "  [FAIL] ") + msg)
    if not cond:
        fails.append(msg)


def ffprobe(p: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)],
        capture_output=True, text=True, check=True).stdout.strip()
    return round(float(out), 3)


slides = (HERE / "slides.html").read_text(encoding="utf-8")
timings = json.loads((TTS / "timings.json").read_text(encoding="utf-8"))

print("== 1. timings 注入与时长 ==")
m = re.search(r"const T = (\{.*?\});\n", slides, re.S)
check(bool(m), "slides.html 内联 timings（const T = {...}）")
if m:
    t_inline = json.loads(m.group(1))
    check(len(t_inline["slides"]) == 4, "4 页")
    for s in t_inline["slides"]:
        real = ffprobe(TTS / f"{s['id']}.mp3")
        check(abs(real - s["duration"]) < 0.05, f"{s['id']} 时长 {s['duration']}s == ffprobe {real}s")

print("== 2. cue 双向对齐 ==")
# 动作类 cue：只触发 action()（改选中行 / 改输入文本 / 重算），不挂 data-cue 元素
ACTION_CUES = {"s2": {"open"}, "s3": {"edit", "rerun"}}
pages = re.findall(r'<section class="pg" data-id="(s\d)">(.*?)</section>', slides, re.S)
check(len(pages) == 4, "4 个 .pg section")
by_id = {s["id"]: s for s in timings["slides"]}
action_src = re.search(r"function action\(k\)\{(.*?)\n\}", slides, re.S)
check(bool(action_src), "slides.html 含 action() 函数")
for pid, body in pages:
    dom_cues = set(re.findall(r'data-cue="([^"]+)"', body))
    t_cues = set(by_id[pid]["cues"])
    expect_cues = dom_cues | ACTION_CUES.get(pid, set())
    check(expect_cues == t_cues, f"{pid} timings.cues == data-cue ∪ 动作 cue {sorted(expect_cues)}")
    for k in ACTION_CUES.get(pid, set()):
        check(f"k==='{k}'" in action_src.group(1), f"action() 处理 {pid}/{k}")

print("== 3. 客群×渠道矩阵一致性 ==")
cq_m = re.search(r"const CQ = \[(.*?)\n\];", slides, re.S)
check(bool(cq_m), "slides.html 含 CQ 数据")
cq_text = cq_m.group(1)
entries = re.findall(
    r"\{id:'(CQ\d+)',seg:'([^']+)',q:'[^']*',ch:\[([^\]]*)\],ev:'([^']+)'", cq_text)
check(len(entries) == 12, f"CQ 12 条（解析到 {len(entries)}）")
segs = ["公交运营商", "海外客户", "行业伙伴"]
chs = ["官网", "公众号", "销售推介", "展会"]
expect = {s: {c: 0 for c in chs} for s in segs}
count = {s: 0 for s in segs}
for _cid, seg, ch_raw, _ev in entries:
    count[seg] += 1
    for ch in re.findall(r"'([^']+)'", ch_raw):
        expect[seg][ch] += 1
# s2 composition 静态矩阵
comp2 = (HERE / "video" / "compositions" / "s2.html").read_text(encoding="utf-8")
mx_rows = re.findall(r'<td class="rh">([^<]+)</td>((?:<td[^>]*>[^<]*</td>){4})<td>(\d+)</td>', comp2)
mx_rows = [r for r in mx_rows if r[0] in segs]
check(len(mx_rows) == 3, f"composition 矩阵 3 行（解析到 {len(mx_rows)}）")
for seg, cells, sub in mx_rows:
    nums = [int(re.sub(r"<[^>]+>", "", c).replace("—", "0") or 0) for c in re.findall(r"<td[^>]*>([^<]*)</td>", cells)]
    ok = nums == [expect[seg][c] for c in chs] and int(sub) == count[seg]
    check(ok, f"{seg} 矩阵 {nums} == 动态计算 {[expect[seg][c] for c in chs]}（小计 {sub} vs {count[seg]} 条）")
col_tot = [sum(expect[s][c] for s in segs) for c in chs]
sum_row = re.search(r'<td class="rh">合计</td>((?:<td[^>]*>[^<]*</td>){4})<td>(\d+)</td>', comp2)
sum_nums = [int(x) for x in re.findall(r"<td[^>]*>(\d+)</td>", sum_row.group(1))] if sum_row else []
check(sum_nums == col_tot and int(sum_row.group(2)) == 12,
      f"合计行 {sum_nums}/{sum_row.group(2) if sum_row else '?'} == 动态 {col_tot}/12")

print("== 4. compositions 占位符 ==")
for f in sorted((HERE / "video" / "compositions").glob("s*.html")):
    left = re.findall(r"\{\{[A-Z0-9_]+\}\}", f.read_text(encoding="utf-8"))
    check(not left, f"{f.name} 无未填占位符" + (f"（残留 {left[:3]}）" if left else ""))
idx = (HERE / "video" / "index.html").read_text(encoding="utf-8")
check(not re.findall(r"\{\{[A-Z0-9_]+\}\}", idx), "video/index.html 无未填占位符")

print("== 5. 零人工操控 ==")
bad = {
    "onclick": len(re.findall(r"\.onclick\s*=", slides)),
    "addEventListener(click/mouse)": len(re.findall(r"addEventListener\('(?:click|mouse)[^']*'", slides)),
    "data-goto": len(re.findall(r"data-goto", slides)),
    "btn-": len(re.findall(r"id=\"btn-", slides)),
    "cursor:pointer": len(re.findall(r"cursor:\s*pointer", slides)),
    "<button": len(re.findall(r"<button", slides)),
}
for k, v in bad.items():
    check(v == 0, f"无 {k}（{v} 处）")
unlock = re.findall(r"addEventListener\('(?:pointerdown|keydown|touchstart)',\s*unlockAudio\)", slides)
check(len(unlock) == 3, f"仅保留 3 个音频解锁监听（{len(unlock)} 个）")
check("addEventListener('keydown'" in slides and len(re.findall(r"addEventListener\('keydown'", slides)) == 1,
      "keydown 仅用于音频解锁（无键盘翻页）")

print("== 6. 关键数字口径 ==")
for token, why in [
    ("4,820", "默认企业池"), ("86.2%", "精度"), ("96.4%", "分级复核"), ("320", "抽样量"),
    ("2,860", "行业分类命中"), ("3,260", "决策链命中"), ("800+exc.length*95", "排除命中公式"),
]:
    check(token in slides, f"slides 含 {token}（{why}）")
comp3 = (HERE / "video" / "compositions" / "s3.html").read_text(encoding="utf-8")
check("- 1,180" in comp3, "s3 composition 排除命中 - 1,180")
check("1,860" in comp3, "s3 composition 区域过滤 1,860")
check("5,060" in comp3, "s3 composition 加非洲后企业池 5,060（与 slides 公式一致）")

print()
if fails:
    print(f"共 {len(fails)} 项不通过：")
    for f_ in fails:
        print(" -", f_)
    sys.exit(1)
print("全部通过 ✅")
