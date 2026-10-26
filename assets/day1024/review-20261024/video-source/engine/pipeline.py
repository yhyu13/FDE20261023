"""讲解视频管线：从讲解稿 Markdown 到成片。

流程（每一步都有单一事实来源，不靠手填秒数）：

    讲解稿.md
      → parse_script()      场景 / 标题 / 要点 / 旁白
      → synthesize()        Edge TTS，逐场出 mp3，并拿到 SentenceBoundary
      → build_subtitles()   字幕行（时间取自 TTS 的真实语音时间，再对齐到帧格）
      → render_slides()     每场一张 1920x1080 画面（HTML → 无头 Edge 截图）
      → make_music()        numpy 生成的配乐床
      → mix_audio()         旁白 + 配乐（按旁白能量闪避）
      → plan_timeline.py    时长以**音频实测**为准
      → render_pipe.py      逐帧亚像素渲染 + 编码
      → burn_subtitles()    libass 把字幕烧进画面
      → verify_video.py     时长对齐 / 画面命中 / 抖动量化
      → check_subs.py       字幕与时间轴、音频轴、帧轴的三轴对齐

为什么时长以音频实测为准：分镜估算和真实语音时长对不上时，
按估算切帧会让后半段音画全错。这里 duration 只是备胎。
"""

from __future__ import annotations

import asyncio
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

VENDOR = Path(__file__).resolve().parent / "vendor"
if str(VENDOR) not in sys.path:
    sys.path.insert(0, str(VENDOR))

# probe_duration 是**再导出**：build_video.py 走 `P.probe_duration(...)` 调用它。
# 写成 `as probe_duration` 是 ruff 认的显式再导出写法——不写会被当成"没用过的 import"报 F401，
# 但删掉会真的把调用链打断。
from ffmedia import probe_duration as probe_duration  # noqa: E402

FFMPEG = shutil.which("ffmpeg")
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
SR = 48000
FPS = 24
WIDTH, HEIGHT = 1920, 1080


def read_text(path: Path) -> str:
    """读文本。用 utf-8-sig 兜住 BOM——PowerShell 5.1 的 Set-Content -Encoding UTF8 会写 BOM，
    带 BOM 的第一行会让 `^#` 匹配不到，标题直接解析成空。"""
    return Path(path).read_text(encoding="utf-8-sig")


# ---------------------------------------------------------------- 数据结构


@dataclass
class Scene:
    id: int
    title: str
    points: list[str] = field(default_factory=list)
    narration: str = ""
    audio: str = ""
    boundaries: list[dict] = field(default_factory=list)
    start: float = 0.0
    end: float = 0.0


@dataclass
class Subtitle:
    text: str
    start: float          # 秒（已对齐帧格）
    end: float
    scene: int


# ---------------------------------------------------------------- 1. 解析讲解稿

_SCENE_RE = re.compile(r"^###\s+场景\s*(\d+)\s*[·:：]?\s*(.+?)\s*$")
_POINT_RE = re.compile(r"^\s*[-*]\s+(.+?)\s*$")
_NARR_RE = re.compile(r"^\*\*旁白\*\*[：:]\s*(.+?)\s*$")
_H1_RE = re.compile(r"^#\s+(.+?)\s*$")
_QUOTE_RE = re.compile(r"^>\s*(.+?)\s*$")


def parse_script(md_text: str) -> tuple[str, list[Scene]]:
    """把讲解稿解析成 (标题, 场景列表)。

    约定格式见各 `*-讲解稿.md`：
        ### 场景 N · 标题
        - **要点**：
            - 要点
        **旁白**：台词
    """
    title = ""
    scenes: list[Scene] = []
    current: Scene | None = None
    in_points = False

    for raw in md_text.splitlines():
        line = raw.rstrip()

        if not current:
            h1 = _H1_RE.match(line)
            if h1 and not title:
                title = h1.group(1).strip()
                continue

            m = _SCENE_RE.match(line)
            if m:
                current = Scene(id=int(m.group(1)), title=m.group(2).strip())
                scenes.append(current)
                in_points = False
            continue

        # 场景内部
        if _SCENE_RE.match(line):
            current = Scene(id=int(_SCENE_RE.match(line).group(1)), title=_SCENE_RE.match(line).group(2).strip())
            scenes.append(current)
            in_points = False
            continue

        if line.strip() == "":
            in_points = False
            continue

        if line.strip().startswith("- **要点**"):
            in_points = True
            continue

        narr = _NARR_RE.match(line.strip())
        if narr:
            current.narration = (current.narration + narr.group(1)).strip()
            in_points = False
            continue

        if in_points:
            pt = _POINT_RE.match(line)
            if pt:
                text = pt.group(1).strip()
                text = re.sub(r"^\*\*|\*\*$", "", text).strip()
                if text:
                    current.points.append(text)
                continue

        q = _QUOTE_RE.match(line.strip())
        if q and not q.group(1).startswith("一句话"):
            continue

    if not scenes:
        raise SystemExit("[ERR] 讲解稿里没解析到场景（### 场景 N · 标题）")
    return title, scenes


# ---------------------------------------------------------------- 2. Edge TTS


async def _synth_one(text: str, voice: str, out_mp3: Path, rate: str) -> list[dict]:
    import edge_tts

    comm = edge_tts.Communicate(text, voice, rate=rate, boundary="SentenceBoundary")
    audio = bytearray()
    bounds: list[dict] = []
    async for chunk in comm.stream():
        if chunk["type"] == "audio":
            audio.extend(chunk["data"])
        elif chunk["type"] in ("SentenceBoundary", "WordBoundary"):
            bounds.append(
                {
                    "offset": chunk["offset"],      # 100 纳秒
                    "duration": chunk["duration"],
                    "text": chunk.get("text", ""),
                }
            )
    if not audio:
        raise SystemExit(f"[ERR] TTS 没拿到音频：{out_mp3.name}")
    out_mp3.write_bytes(bytes(audio))
    return bounds


def synthesize(scenes: list[Scene], audio_dir: Path, voice: str, rate: str = "+8%") -> None:
    """逐场合成，产出 scene_XX.mp3 与该场的句子边界。"""
    audio_dir.mkdir(parents=True, exist_ok=True)

    async def run() -> None:
        for sc in scenes:
            name = f"scene_{sc.id:02d}.mp3"
            out = audio_dir / name
            sc.audio = name
            print(f"  TTS 场景 {sc.id}: {sc.title}")
            sc.boundaries = await _synth_one(sc.narration, voice, out, rate)

    asyncio.run(run())


# ---------------------------------------------------------------- 3. 字幕


def _split_long(text: str, limit: int = 24) -> list[str]:
    """把过长的句子再切一刀，切点优先落在标点后。"""
    if len(text) <= limit:
        return [text]
    parts: list[str] = []
    buf = ""
    for ch in text:
        buf += ch
        if len(buf) >= limit and ch in "，。；：？！、":
            parts.append(buf.strip())
            buf = ""
    if buf.strip():
        parts.append(buf.strip())
    return [p for p in parts if p]


def build_subtitles(scenes: list[Scene], fps: int = FPS) -> list[Subtitle]:
    """字幕行。

    时间轴来自 TTS 的 SentenceBoundary（真实语音时间，音频轴）；
    再把每行的起止**吸附到帧格**（帧轴），所以同一行在视频里
    出现的帧号是确定的，不会出现半帧错位。

    ASS 的时间格式只到**厘秒**（0.01s），而 24fps 的帧格是 1/24≈0.0417s，
    所以写进 ASS 的时间与帧格之间最多差 0.005s = 0.12 帧。这个量化误差
    是格式本身的上限，不是错位。
    """
    subs: list[Subtitle] = []
    for sc in scenes:
        if not sc.boundaries:
            continue
        for b in sc.boundaries:
            text = (b.get("text") or "").strip()
            if not text:
                continue
            # TTS 的边界偏移是**本场音频内**的相对时间，要加上本场的全局起点
            start = sc.start + b["offset"] / 1e7
            end = sc.start + (b["offset"] + b["duration"]) / 1e7
            parts = _split_long(text)
            total_len = sum(len(p) for p in parts) or 1
            cursor = start
            span = end - start
            for part in parts:
                # 顺序铺开：每段接上一段，不许都从句首开始（那样会互相覆盖）
                p_start = cursor
                p_end = cursor + span * (len(part) / total_len)
                cursor = p_end
                # 钳进本场音频区间：边界事件可能比解码后的 PCM 长几十毫秒
                if sc.end > sc.start:
                    p_start = min(max(p_start, sc.start), sc.end - 0.05)
                    p_end = min(max(p_end, p_start + 0.04), sc.end)
                f0 = round(p_start * fps)
                f1 = max(round(p_end * fps), f0 + 1)
                subs.append(Subtitle(text=part, start=f0 / fps, end=f1 / fps, scene=sc.id))
    return subs


def build_ass(subs: list[Subtitle], title: str, width: int = WIDTH, height: int = HEIGHT) -> str:
    """把字幕行写成 ASS。

    时间已经对齐帧格，这里只做格式化；样式里显式指定中文字体，
    字体找不到时 libass 会回退，落到哪个字体不确定，所以字体名给微软雅黑。
    """
    def ts(t: float) -> str:
        total = int(round(t * 100))
        h, rem = divmod(total, 360000)
        m, rem = divmod(rem, 6000)
        s, cs = divmod(rem, 100)
        return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Microsoft YaHei,52,&H00F2F2EC,&H00F2F2EC,&H00101010,&HA0000000,0,0,0,0,100,100,0,0,1,3,1,2,90,90,170,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = [head]
    for s in subs:
        text = s.text.replace("{", "(").replace("}", ")").replace("\n", "\\N")
        lines.append(f"Dialogue: 0,{ts(s.start)},{ts(s.end)},Default,,0,0,0,,{text}")
    return "\n".join(lines)


# ---------------------------------------------------------------- 4. 画面


def _slide_html(scene: Scene, title: str, index: int, total: int) -> str:
    points = "".join(
        f'<li><span class="tick"></span><span class="t">{p}</span></li>' for p in scene.points
    )
    return f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  html, body {{ width:{WIDTH}px; height:{HEIGHT}px; overflow:hidden; }}
  body {{
    background:
      radial-gradient(1200px 700px at 12% -10%, rgba(78,168,138,.16), transparent 65%),
      radial-gradient(900px 600px at 105% 110%, rgba(199,123,63,.12), transparent 60%),
      linear-gradient(160deg, #12181b 0%, #0c1114 100%);
    color:#e9e7df;
    font-family:"Microsoft YaHei","PingFang SC","Noto Sans SC",sans-serif;
    padding:96px 120px 200px 120px;
    display:flex; flex-direction:column;
  }}
  .kicker {{ font-family:"JetBrains Mono",Consolas,monospace; font-size:24px; letter-spacing:.18em;
    color:#6fbf9d; text-transform:uppercase; margin-bottom:34px; }}
  h1 {{ font-size:74px; line-height:1.22; font-weight:700; letter-spacing:-.01em; margin-bottom:44px; }}
  ul {{ list-style:none; display:flex; flex-direction:column; gap:26px; }}
  li {{ display:flex; align-items:flex-start; gap:20px; font-size:38px; line-height:1.45; color:#cfd6d2; }}
  .tick {{ flex:none; width:14px; height:14px; border-radius:50%; background:#6fbf9d; margin-top:18px; }}
  .foot {{ position:absolute; left:120px; right:120px; bottom:86px; display:flex;
    justify-content:space-between; align-items:center; border-top:1px solid rgba(255,255,255,.12); padding-top:26px; }}
  .foot .t {{ font-size:26px; color:#8e9a95; }}
  .foot .n {{ font-family:"JetBrains Mono",Consolas,monospace; font-size:24px; color:#6fbf9d; }}
</style></head><body>
  <div class="kicker">场景 {scene.id:02d} / {total:02d}</div>
  <h1>{scene.title}</h1>
  <ul>{points}</ul>
  <div class="foot"><div class="t">{title}</div><div class="n">FDE 训练营 · {index:02d}/{total:02d}</div></div>
</body></html>"""


def render_slides(scenes: list[Scene], title: str, frames_dir: Path, html_dir: Path,
                  edge: str = EDGE) -> list[str]:
    """每场一张 1920x1080 画面。走浏览器路线：字体与符号由浏览器负责回退。"""
    if not edge or not Path(edge).exists():
        raise SystemExit("[ERR] 找不到 Edge，无法出画面")
    frames_dir.mkdir(parents=True, exist_ok=True)
    html_dir.mkdir(parents=True, exist_ok=True)

    names: list[str] = []
    profile = html_dir / "_edge_profile"
    for sc in scenes:
        html = html_dir / f"scene_{sc.id:02d}.html"
        html.write_text(_slide_html(sc, title, sc.id, len(scenes)), encoding="utf-8")
        png = frames_dir / f"scene_{sc.id:02d}.png"
        url = html.resolve().as_uri()
        cmd = [
            edge, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run",
            f"--user-data-dir={profile}", f"--window-size={WIDTH},{HEIGHT}",
            f"--screenshot={png.resolve()}", url,
        ]
        subprocess.run(cmd, capture_output=True, timeout=90)
        if not png.exists():
            raise SystemExit(f"[ERR] 截图失败：{png.name}")
        names.append(png.name)
        print(f"  画面 {sc.id:02d}: {png.name} ({png.stat().st_size // 1024} KB)")
    return names


# ---------------------------------------------------------------- 5. 配乐


def make_music(duration: float, sr: int = SR, path: Path | None = None,
               bpm: int = 62) -> np.ndarray:  # noqa: F821
    """numpy 生成的配乐床：慢垫音 + 稀疏琶音，音量压得很低，只做底。

    不用采样库，也不用下载素材——现场评审时断网也不影响出片。
    """
    import numpy as np

    n = int(duration * sr)
    t = np.arange(n, dtype=np.float64) / sr
    rng = np.random.default_rng(20261023)

    # D 小调五声（A2 根音），音程用半音数表示
    scale = [0, 3, 5, 7, 10, 12, 15]
    root = 146.83  # D3

    def note(semi: float) -> float:
        return root * (2 ** (semi / 12))

    # 垫音：三个泛音的慢速叠加 + 轻微失谐
    pad = np.zeros(n)
    for semi, amp in ((0, 0.55), (7, 0.30), (12, 0.18)):
        f = note(semi)
        pad += amp * np.sin(2 * np.pi * f * t + rng.uniform(0, 0.4))
        pad += amp * 0.5 * np.sin(2 * np.pi * f * 1.004 * t)
    pad *= 0.5 + 0.5 * np.sin(2 * np.pi * (1 / 8.0) * t) ** 2

    # 琶音：每两拍一个音，落在五声上
    beat = 60.0 / bpm
    arp = np.zeros(n)
    idx = 0
    pos = 0.0
    while pos < duration:
        semi = scale[idx % len(scale)] + (12 if idx % 7 == 6 else 0)
        dur = beat * 1.6
        i0 = int(pos * sr)
        i1 = min(n, int((pos + dur) * sr))
        if i1 > i0:
            seg = np.arange(i1 - i0) / sr
            env = np.exp(-seg * 3.2) * (1 - np.exp(-seg * 60))
            f = note(semi)
            arp[i0:i1] += 0.30 * env * (
                np.sin(2 * np.pi * f * seg) + 0.35 * np.sin(2 * np.pi * f * 2 * seg)
            )
        pos += beat * 2
        idx += 1

    music = pad * 0.22 + arp * 0.30
    music += 1e-4 * rng.standard_normal(n)
    music = np.tanh(music * 1.1) * 0.7
    peak = float(np.max(np.abs(music))) or 1.0
    music = music / peak * 0.5
    if path:
        _write_wav(path, music.astype(np.float32), sr)
    return music.astype(np.float32)


def _write_wav(path: Path, data, sr: int) -> None:
    import soundfile as sf

    path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(path), data, sr, subtype="PCM_16")


def _read_wav(path: Path) -> tuple[np.ndarray, int]:  # noqa: F821
    import soundfile as sf

    data, sr = sf.read(str(path), dtype="float32", always_2d=False)
    if data.ndim > 1:
        data = data.mean(axis=1)
    return data, sr


# ---------------------------------------------------------------- 6. 混音


def mix_audio(narration_path: Path, music, out_path: Path, sr: int = SR,
              duck: float = 0.86) -> float:
    """旁白 + 配乐。配乐按旁白能量闪避，人说话时压下去。"""
    import numpy as np

    narr, nsr = _read_wav(narration_path)
    if nsr != sr:
        raise SystemExit(f"[ERR] 采样率不一致：旁白 {nsr}，期望 {sr}")

    music = np.asarray(music, dtype=np.float32)
    if len(music) < len(narr):
        music = np.pad(music, (0, len(narr) - len(music)))
    music = music[: len(narr)]

    # 逐 50ms 窗口算旁白 RMS，做闪避曲线（再插值回逐样本）
    win = int(sr * 0.05)
    n_win = max(len(narr) // win, 1)
    rms = np.array([
        float(np.sqrt(np.mean(narr[i * win:(i + 1) * win] ** 2))) if (i + 1) * win <= len(narr)
        else 0.0
        for i in range(n_win)
    ])
    ref = float(np.percentile(rms, 95)) or 1.0
    level = np.clip(rms / ref, 0, 1)
    gain_win = 1.0 - duck * level
    gain = np.interp(np.arange(len(narr)) / win, np.arange(n_win), gain_win)
    gain = np.clip(gain, 1.0 - duck, 1.0)

    mixed = narr + music * gain * 0.22
    peak = float(np.max(np.abs(mixed))) or 1.0
    if peak > 0.97:
        mixed = mixed / peak * 0.97
    _write_wav(out_path, mixed.astype(np.float32), sr)
    return len(narr) / sr


# ---------------------------------------------------------------- 7. 辅助


def run(cmd: list[str], cwd: Path | None = None) -> None:
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    out = (r.stdout or "") + (r.stderr or "")
    if r.returncode != 0:
        print(out[-3000:])
        raise SystemExit(f"[ERR] 命令失败（{r.returncode}）：{' '.join(cmd[:4])}")
    if out.strip():
        print(out.rstrip())


def decode_to_wav(src: Path, dst: Path, sr: int = SR) -> None:
    run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error",
         "-i", str(src), "-ac", "1", "-ar", str(sr), str(dst)])


def concat_wavs(parts: list[Path], out_path: Path, sr: int = SR) -> None:
    """按 PCM 精确拼接，保证「各场之和 = 全片」在样本级成立。"""
    import numpy as np

    chunks = []
    for p in parts:
        data, psr = _read_wav(p)
        if psr != sr:
            raise SystemExit(f"[ERR] 采样率不一致：{p.name} 是 {psr}")
        chunks.append(data)
    _write_wav(out_path, np.concatenate(chunks).astype(np.float32), sr)
