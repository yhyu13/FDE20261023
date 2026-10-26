"""字幕三轴对齐校验。

字幕要同时对上三条轴：

* **音频轴** —— 每行字幕的时间来自 TTS 的 SentenceBoundary，是真实语音时间；
* **帧轴** —— 每行的起止都吸附到 1/fps 的整数帧，不出现半帧错位；
* **时间轴** —— 画面分步（timeline 的 segment）与字幕行属于同一场景、
  同一时间区间，不出现"念的是这段、画面放的是那段"。

再加一条**视觉验证**：从成片里抽帧，确认字幕确实烧进了画面，
且在不该出现的时刻确实没出现——这条能挡住"ASS 写了但没烧进去"。

用法：

    python tools/video/check_subs.py --ass subs.ass --timeline timeline.json \
        --video final.mp4 --video-nosub nosub.mp4 --fps 24
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

VENDOR = Path(__file__).resolve().parent / "vendor"
if str(VENDOR) not in sys.path:
    sys.path.insert(0, str(VENDOR))

from ffmedia import run_ffmpeg  # noqa: E402


def parse_ass(path: Path) -> list[tuple[float, float, str]]:
    """解析 ASS 的 Dialogue 行。

    按字段切，不靠正则找最后一列——正则里的 `.*?,` 是非贪婪的，
    会在第一个逗号处停下，把 ",0,0,0,," 这种字段尾巴当成正文。
    """
    out: list[tuple[float, float, str]] = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        s = line.strip()
        if not s.startswith("Dialogue:"):
            continue
        parts = s.split(",", 9)
        if len(parts) < 10:
            continue
        start = _ts(parts[1])
        end = _ts(parts[2])
        text = parts[9].replace("\\N", "").strip()
        if text:
            out.append((start, end, text))
    return out


def _ts(v: str) -> float:
    h, m, s = v.strip().split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)


def band_mae(video: Path, video_nosub: Path, t: float, tmp: Path, label: str) -> float:
    """抽 t 秒这一帧，比较**底部字幕带**与同帧无字幕视频的差异。"""
    import numpy as np
    from PIL import Image

    a = tmp / f"_s_{label}.png"
    b = tmp / f"_n_{label}.png"
    run_ffmpeg(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                "-ss", f"{t:.3f}", "-i", str(video), "-frames:v", "1", str(a)])
    run_ffmpeg(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                "-ss", f"{t:.3f}", "-i", str(video_nosub), "-frames:v", "1", str(b)])
    if not a.exists() or not b.exists():
        return 0.0
    ia = np.asarray(Image.open(a).convert("L"), dtype="float32")
    ib = np.asarray(Image.open(b).convert("L"), dtype="float32")
    h = ia.shape[0]
    # 字幕带取**底部 30%**：MarginV=170、字号 52 时，字幕实际落在 72%~85% 高度，
    # 取底部 20% 会整条漏掉（差值≈0），误判成"字幕没烧进去"。
    band = slice(int(h * 0.70), h)
    return float(np.abs(ia[band] - ib[band]).mean())


def main() -> int:
    ap = argparse.ArgumentParser(description="字幕三轴对齐校验")
    ap.add_argument("--ass", required=True)
    ap.add_argument("--timeline", required=True)
    ap.add_argument("--video", required=True, help="烧过字幕的成片")
    ap.add_argument("--video-nosub", required=True, help="没烧字幕的画面版")
    ap.add_argument("--fps", type=int, default=24)
    ap.add_argument("--tmp-dir", default="temp/subs")
    args = ap.parse_args()

    import json

    ass_path = Path(args.ass)
    timeline = json.loads(Path(args.timeline).read_text(encoding="utf-8"))
    fps = args.fps
    tmp = Path(args.tmp_dir)
    tmp.mkdir(parents=True, exist_ok=True)

    events = parse_ass(ass_path)
    ok = True

    # ---------- 轴 1：帧轴 ----------
    print("=== 轴 1 · 帧轴（起止吸附到整数帧）===")
    # ASS 的时间只到厘秒（0.01s），24fps 的帧格是 1/24≈0.0417s，
    # 所以写进 ASS 的时间与帧格最多差 0.005s = 0.12 帧。这是格式上限，不是错位。
    tol_frames = 0.25
    bad = []
    worst = 0.0
    for start, end, _ in events:
        for t in (start, end):
            dev = abs(t * fps - round(t * fps))
            worst = max(worst, dev)
            if dev > tol_frames:
                bad.append(t)
    if bad:
        ok = False
        print(f"[FAIL] {len(bad)} 个字幕时间点偏离帧格超过 {tol_frames} 帧（fps={fps}）")
        for t in bad[:5]:
            print(f"       {t:.4f}s → {t * fps:.4f} 帧")
    else:
        print(f"[OK] {len(events)} 行字幕起止都在帧格上，最大偏差 {worst:.3f} 帧"
              f"（ASS 厘秒精度上限 0.12 帧）")

    # ---------- 轴 2：音频轴（场景区间） ----------
    print("\n=== 轴 2 · 音频轴（落在所属场景的音频区间内）===")
    scenes: dict[int, tuple[float, float]] = {}
    acc = 0.0
    for seg in timeline["segments"]:
        sid = seg["scene"]
        s, e = scenes.get(sid, (acc, acc))
        scenes[sid] = (min(s, acc), max(e, acc + seg["duration"]))
        acc += seg["duration"]
    outside = []
    for start, end, _text in events:
        hit = [s for s in scenes.values() if start >= s[0] - 0.01 and end <= s[1] + 0.01]
        if not hit:
            near = min(scenes.values(), key=lambda s: min(abs(start - s[0]), abs(start - s[1])))
            outside.append((start, end, near))
    if outside:
        ok = False
        print(f"[FAIL] {len(outside)} 行字幕越出了场景的音频区间")
        for start, end, near in outside[:5]:
            print(f"       {start:.2f}-{end:.2f}s，最近场景 {near[0]:.2f}-{near[1]:.2f}s")
    else:
        print(f"[OK] {len(events)} 行字幕都落在所属场景的音频区间内")

    # ---------- 轴 3：时间轴（覆盖 + 无大段空缺） ----------
    print("\n=== 轴 3 · 时间轴（覆盖与空缺）===")
    total = sum(seg["duration"] for seg in timeline["segments"])
    if not events:
        print("[FAIL] 没有字幕行")
        return 1
    gaps = []
    prev = 0.0
    for start, end, _ in events:
        if start - prev > 2.0:
            gaps.append((prev, start))
        prev = max(prev, end)
    if total - prev > 2.0:
        gaps.append((prev, total))
    if gaps:
        print(f"[WARN] {len(gaps)} 段空缺超过 2 秒")
        for a, b in gaps[:5]:
            print(f"       {a:.2f}s → {b:.2f}s")
    else:
        print(f"[OK] 字幕覆盖到 {prev:.2f}s / 总长 {total:.2f}s，无 2 秒以上空缺")

    # ---------- 视觉验证：字幕确实烧进去了，且时间对 ----------
    print("\n=== 视觉验证（字幕带在成片与无字幕版之间的差异）===")
    # 找几行字幕的中点
    picks = [e for e in events if e[1] - e[0] > 0.8]
    picks = picks[:: max(len(picks) // 3, 1)][:3] if picks else []
    ins = []
    for i, (start, end, text) in enumerate(picks):
        t = (start + end) / 2
        mae = band_mae(Path(args.video), Path(args.video_nosub), t, tmp, f"in{i}")
        ins.append(mae)
        print(f"  字幕中点 t={t:6.2f}s  底部差异 {mae:6.2f}  「{text[:22]}」")

    # 找一处没有字幕的时刻：优先用场景之间的空档，没有就用片头/片尾
    outs = []
    total_dur = sum(seg["duration"] for seg in timeline["segments"])
    candidates = []
    for i in range(len(events) - 1):
        if events[i + 1][0] - events[i][1] > 0.6:
            candidates.append(((events[i][1] + events[i + 1][0]) / 2, "场景间空档"))
    if events[0][0] > 0.3:
        candidates.append((events[0][0] / 2, "片头"))
    if total_dur - events[-1][1] > 0.3:
        candidates.append(((events[-1][1] + total_dur) / 2, "片尾"))
    for i, (t, why) in enumerate(candidates[:2]):
        mae = band_mae(Path(args.video), Path(args.video_nosub), t, tmp, f"out{i}")
        outs.append(mae)
        print(f"  无字幕时刻 t={t:6.2f}s（{why}）  底部差异 {mae:6.2f}")
        if outs:
            break

    if not ins:
        print("[WARN] 没有可采样的长字幕行，跳过视觉验证")
    elif not outs:
        print("[WARN] 没找到空档，无法反证，只看有字幕时差异")
        if min(ins) <= 1.0:
            ok = False
            print("[FAIL] 有字幕时底部几乎没有差异 —— 字幕可能没烧进画面")
        else:
            print(f"[OK] 有字幕时底部差异 {min(ins):.2f}，字幕已烧进画面")
    else:
        if min(ins) > max(outs) * 2 and min(ins) > 1.0:
            print(f"[OK] 有字幕时差异 {min(ins):.2f} 远大于空档时 {max(outs):.2f}，"
                  "字幕烧进去了且时间对得上")
        else:
            ok = False
            print(f"[FAIL] 有字幕 {min(ins):.2f} vs 空档 {max(outs):.2f}，区分度不足，"
                  "字幕可能没烧进去或时间没对齐")

    print()
    if ok:
        print("[OK ] 字幕三轴对齐校验通过")
        return 0
    print("[FAIL] 字幕三轴对齐校验未通过")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
