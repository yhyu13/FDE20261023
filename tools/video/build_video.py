"""讲解稿 → 讲解视频。

用法：

    python tools/video/build_video.py --Script problems/01-*-讲解稿.md --OutDir build/01

流程与判定标准见 `tools/video/pipeline.py` 顶部说明。
成片会被自动校验两轮：帧级画面（时长对齐 / 画面命中 / 抖动量化）+
字幕三轴对齐（时间轴 / 音频轴 / 帧轴）。任何一轮不过，退出码非 0。
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pipeline as P  # noqa: E402

# 子进程的输出是直连的，父进程自己的 print 若不按行刷新会排在后面，看着像乱序
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

VOICE_DEFAULT = "zh-CN-YunxiNeural"


def main() -> int:
    ap = argparse.ArgumentParser(description="讲解稿 → 讲解视频")
    ap.add_argument("--Script", required=True, help="讲解稿 Markdown")
    ap.add_argument("--OutDir", default=None, help="产物目录，默认 build/<题号>")
    ap.add_argument("--Voice", default=VOICE_DEFAULT)
    ap.add_argument("--Rate", default="+6%", help="语速，如 +10%%")
    ap.add_argument("--Fps", type=int, default=P.FPS)
    ap.add_argument("--SkipVideo", action="store_true", help="只出音频与字幕，不渲染画面")
    args = ap.parse_args()

    script = Path(args.Script)
    if not script.is_absolute():
        script = ROOT / args.Script
    if not script.exists():
        print(f"[ERR] 找不到讲解稿：{script}")
        return 2

    out_dir = Path(args.OutDir) if args.OutDir else ROOT / "build" / script.stem[:2]
    if not out_dir.is_absolute():
        out_dir = ROOT / out_dir
    audio_dir = out_dir / "audio"
    frames_dir = out_dir / "frames"
    html_dir = out_dir / "html"

    print(f"[1/9] 解析讲解稿：{script.name}")
    title, scenes = P.parse_script(P.read_text(script))
    if not title:
        title = script.stem
    for sc in scenes:
        if not sc.narration:
            print(f"[ERR] 场景 {sc.id} 没有旁白")
            return 2
    print(f"      标题：{title}")
    print(f"      场景 {len(scenes)} 个，旁白合计 {sum(len(s.narration) for s in scenes)} 字")

    print("[2/9] Edge TTS 配音")
    P.synthesize(scenes, audio_dir, args.Voice, args.Rate)

    print("[3/9] 解码为 PCM 并精确拼接")
    wavs = []
    cursor = 0.0
    for sc in scenes:
        mp3 = audio_dir / sc.audio
        wav = audio_dir / f"scene_{sc.id:02d}.wav"
        P.decode_to_wav(mp3, wav)
        wavs.append(wav)
        dur = P.probe_duration(wav) or 0.0
        sc.start = cursor
        sc.end = cursor + dur
        cursor = sc.end
    narration = audio_dir / "narration_full.wav"
    P.concat_wavs(wavs, narration)
    narr_len = P.probe_duration(narration)
    print(f"      旁白总长 {narr_len:.2f}s")

    print("[4/9] 生成字幕（时间取自 TTS 句子边界，再吸附到帧格）")
    subs = P.build_subtitles(scenes, fps=args.Fps)
    ass_path = out_dir / "subs.ass"
    out_dir.mkdir(parents=True, exist_ok=True)
    ass_path.write_text(P.build_ass(subs, title), encoding="utf-8")
    print(f"      字幕 {len(subs)} 行 → {ass_path.name}")

    if args.SkipVideo:
        print("[SKIP] --SkipVideo：只出音频与字幕")
        return 0

    print("[5/9] 出画面（HTML → 无头 Edge 截图）")
    names = P.render_slides(scenes, title, frames_dir, html_dir)

    print("[6/9] 生成配乐并混音")
    music = P.make_music(narr_len)
    mixed = audio_dir / "mixed.wav"
    P.mix_audio(narration, music, mixed)
    print(f"      混音 {P.probe_duration(mixed):.2f}s")

    print("[7/9] 时间轴规划（时长以音频实测为准）")
    manifest = {
        "fps": args.Fps,
        "scenes": [
            {"id": sc.id, "audio": f"scene_{sc.id:02d}.wav",
             "files": [names[i]], "weights": [1]}
            for i, sc in enumerate(scenes)
        ],
    }
    mpath = out_dir / "steps.json"
    mpath.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    timeline_path = out_dir / "timeline.json"
    P.run([sys.executable, str(P.VENDOR / "plan_timeline.py"),
           "--manifest", str(mpath), "--frames-dir", str(frames_dir),
           "--audio-dir", str(audio_dir), "--out", str(timeline_path)], cwd=ROOT)

    print("[8/9] 逐帧渲染 + 编码")
    nosub = out_dir / "video_nosub.mp4"
    P.run([sys.executable, str(P.VENDOR / "render_pipe.py"),
           "--timeline", str(timeline_path), "--out", str(nosub),
           "--audio", str(mixed), "--crf", "21"], cwd=ROOT)

    print("[9/9] 烧字幕 + 校验")
    final = out_dir / "讲解视频.mp4"
    # fontsdir 用**相对路径**：绝对路径带盘符冒号，过滤器解析器会在冒号处断开
    # （报 "No option name near ..."）。相对路径没有冒号，稳。
    import os

    fontsdir = os.path.relpath(r"C:\Windows\Fonts", out_dir).replace("\\", "/")
    P.run([P.FFMPEG, "-y", "-hide_banner", "-loglevel", "error",
           "-i", str(nosub), "-vf", f"ass=subs.ass:fontsdir={fontsdir}",
           "-c:v", "libx264", "-preset", "medium", "-crf", "21",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
           "-movflags", "+faststart", str(final)], cwd=out_dir)

    print("\n--- 校验一：画面（时长对齐 / 画面命中 / 抖动量化）---")
    r1 = subprocess.run([sys.executable, str(P.VENDOR / "verify_video.py"),
                         "--video", str(nosub), "--timeline", str(timeline_path),
                         "--audio", str(mixed), "--tmp-dir", str(out_dir / "temp")],
                        cwd=ROOT, text=True, encoding="utf-8", errors="replace")

    print("\n--- 校验二：字幕三轴对齐 ---")
    r2 = subprocess.run([sys.executable, str(Path(__file__).parent / "check_subs.py"),
                         "--ass", str(ass_path), "--timeline", str(timeline_path),
                         "--video", str(final), "--video-nosub", str(nosub),
                         "--fps", str(args.Fps)], cwd=ROOT, text=True,
                        encoding="utf-8", errors="replace")

    if r1.returncode != 0 or r2.returncode != 0:
        print("\n[FAIL] 有校验没过，先修再交付")
        return 1

    size = final.stat().st_size / 1024 / 1024
    print(f"\n[OK ] {final}")
    print(f"      {size:.1f} MB · {P.probe_duration(final):.2f}s · {args.Fps}fps · 1920x1080")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
