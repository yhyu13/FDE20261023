"""讲解稿 Markdown → 单文件 HTML 讲解页。

和视频共用同一套场景数据（`pipeline.parse_script`），所以
**网页和视频讲的是同一件事**，不会出现两版内容对不上的情况。

用法：

    python tools/video/make_html.py --Script problems/01-*-讲解稿.md --Out problems/01-*-讲解稿.html
"""

from __future__ import annotations

import argparse
import html as h
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pipeline as P  # noqa: E402

CSS = """
:root{
  --bg:#0e1316; --card:#141b1f; --line:rgba(255,255,255,.10);
  --ink:#eae8e1; --ink2:#c3cbc7; --muted:#7f8c87; --accent:#6fbf9d; --warn:#d99a72;
}
*{margin:0;padding:0;box-sizing:border-box}
html{scroll-behavior:smooth}
body{
  background:
    radial-gradient(1100px 620px at 10% -8%, rgba(111,191,157,.13), transparent 62%),
    radial-gradient(900px 560px at 104% 106%, rgba(199,123,63,.11), transparent 58%),
    linear-gradient(165deg,#12181b 0%,#0b0f12 100%);
  color:var(--ink); font-family:"Microsoft YaHei","PingFang SC","Noto Sans SC",sans-serif;
  font-size:15.5px; line-height:1.72; -webkit-font-smoothing:antialiased;
}
.wrap{max-width:1000px;margin:0 auto;padding:0 24px}
@media(min-width:768px){.wrap{padding:0 40px}}
header{padding:64px 0 34px;border-bottom:1px solid var(--line)}
.kicker{font-family:"JetBrains Mono",Consolas,monospace;font-size:12px;letter-spacing:.18em;
  color:var(--accent);text-transform:uppercase;margin-bottom:16px}
h1{font-size:clamp(27px,4.4vw,42px);line-height:1.24;font-weight:700;letter-spacing:-.01em;margin-bottom:14px}
.lede{font-size:16.5px;color:var(--ink2);max-width:62ch}
.meta{display:flex;gap:10px;flex-wrap:wrap;margin-top:22px}
.chip{font-family:"JetBrains Mono",Consolas,monospace;font-size:11.5px;color:var(--muted);
  border:1px solid var(--line);border-radius:999px;padding:4px 11px}
nav{position:sticky;top:0;z-index:10;background:rgba(14,19,22,.9);backdrop-filter:blur(10px);
  border-bottom:1px solid var(--line);margin-bottom:12px}
.navin{max-width:1000px;margin:0 auto;padding:10px 24px;display:flex;gap:6px;flex-wrap:wrap}
@media(min-width:768px){.navin{padding:10px 40px}}
nav a{font-family:"JetBrains Mono",Consolas,monospace;font-size:12px;color:var(--muted);
  text-decoration:none;padding:4px 9px;border-radius:6px;border:1px solid transparent;transition:all .18s}
nav a:hover{color:var(--accent);border-color:rgba(111,191,157,.3);background:rgba(111,191,157,.08)}
section.scene{padding:40px 0;border-bottom:1px solid var(--line)}
.scene-h{display:flex;align-items:baseline;gap:14px;margin-bottom:16px}
.no{font-family:"JetBrains Mono",Consolas,monospace;font-size:13px;color:var(--accent);
  border:1px solid rgba(111,191,157,.3);border-radius:6px;padding:2px 9px;flex:none}
h2{font-size:25px;line-height:1.32;font-weight:700}
ul{list-style:none;display:flex;flex-direction:column;gap:10px;margin-bottom:20px}
li{position:relative;padding-left:20px;font-size:15px;color:var(--ink2)}
li::before{content:"";position:absolute;left:0;top:9px;width:6px;height:6px;border-radius:50%;
  background:var(--accent);opacity:.6}
.narr{background:var(--card);border:1px solid var(--line);border-left:2px solid var(--accent);
  border-radius:0 12px 12px 0;padding:16px 20px;font-size:15.5px;color:var(--ink2)}
.narr b{color:var(--ink);font-weight:600}
.check{padding:40px 0 60px}
.check h2{font-size:21px;margin-bottom:14px}
.check ol{list-style:none;counter-reset:s;display:flex;flex-direction:column;gap:12px}
.check ol li{counter-increment:s;padding-left:38px}
.check ol li::before{content:counter(s);position:absolute;left:0;top:0;width:24px;height:24px;
  border-radius:50%;background:rgba(111,191,157,.14);color:var(--accent);
  font-family:"JetBrains Mono",Consolas,monospace;font-size:12px;
  display:flex;align-items:center;justify-content:center}
footer{padding:26px 0 50px;color:var(--muted);font-size:12.5px;border-top:1px solid var(--line)}
footer .mono{font-family:"JetBrains Mono",Consolas,monospace;font-size:11.5px}
"""


def _md_inline(text: str) -> str:
    """极简行内 Markdown：**粗体**、`代码`、[链接](url)。"""
    out = h.escape(text)
    out = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", out)
    out = re.sub(r"`([^`]+)`", r"<code>\1</code>", out)
    out = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2" target="_blank">\1</a>', out)
    return out


def _md_block(text: str) -> str:
    """段落 + 列表 + 粗体。讲解稿正文结构简单，不需要完整 Markdown 引擎。"""
    chunks: list[str] = []
    for para in [p.strip() for p in text.split("\n\n") if p.strip()]:
        lines = [ln.rstrip() for ln in para.split("\n")]
        if all(ln.lstrip().startswith(("-", "*")) for ln in lines if ln.strip()):
            items = "".join(f"<li>{_md_inline(ln.lstrip().lstrip('-*').strip())}</li>" for ln in lines if ln.strip())
            chunks.append(f"<ul>{items}</ul>")
        else:
            chunks.append(f"<p>{_md_inline(' '.join(ln for ln in lines if ln.strip()))}</p>")
    return "\n".join(chunks)


def build_html(title: str, scenes, lede: str, check_md: str) -> str:
    nav = "".join(f'<a href="#s{i}">{i:02d}</a>' for i in range(1, len(scenes) + 1))
    nav += '<a href="#check">怎么看</a>'

    blocks = []
    for sc in scenes:
        points = "".join(f"<li>{_md_inline(p)}</li>" for p in sc.points)
        narr = f'<p class="narr"><b>旁白</b>　{_md_inline(sc.narration)}</p>'
        blocks.append(
            f'<section class="scene" id="s{sc.id}">'
            f'<div class="scene-h"><span class="no">{sc.id:02d}</span><h2>{_md_inline(sc.title)}</h2></div>'
            f"{('<ul>' + points + '</ul>') if points else ''}"
            f"{narr}</section>"
        )

    check = ""
    if check_md.strip():
        check = f'<section class="check" id="check"><h2>怎么看</h2>{_md_block(check_md)}</section>'

    return f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{_md_inline(title)}</title>
<style>{CSS}</style></head><body>
<header><div class="wrap">
  <div class="kicker">FDE 训练营 · 讲解稿</div>
  <h1>{_md_inline(title)}</h1>
  <p class="lede">{_md_inline(lede)}</p>
  <div class="meta">
    <span class="chip">{len(scenes)} 个场景</span>
    <span class="chip">旁白 {sum(len(s.narration) for s in scenes)} 字</span>
    <span class="chip">1920x1080 同源画面</span>
  </div>
</div></header>
<nav><div class="navin">{nav}</div></nav>
<div class="wrap">
{"".join(blocks)}
{check}
</div>
<footer><div class="wrap">
  <div class="mono">FDE 训练营 · 六道真题拆解 · 配套讲解视频与本页同源</div>
  <div style="margin-top:6px">这一页和讲解视频用的是同一份场景数据（`tools/video/pipeline.py` 的解析结果），改稿子要重跑一次视频。</div>
</div></footer>
</body></html>"""


def main() -> int:
    ap = argparse.ArgumentParser(description="讲解稿 Markdown → 单文件 HTML")
    ap.add_argument("--Script", required=True)
    ap.add_argument("--Out", default=None)
    args = ap.parse_args()

    script = Path(args.Script)
    if not script.is_absolute():
        script = ROOT / args.Script
    text = P.read_text(script)
    title, scenes = P.parse_script(text)

    lede = ""
    m = re.search(r"^>\s*(.+?)\s*$", text, re.M)
    if m:
        lede = m.group(1)
    if lede.startswith("一句话"):
        lede = lede.replace("一句话", "").lstrip("：:").strip()

    check_md = ""
    cm = re.search(r"^##\s*怎么看\s*$(.*?)(?=^##\s|\Z)", text, re.M | re.S)
    if cm:
        check_md = cm.group(1).strip()

    out = Path(args.Out) if args.Out else script.with_suffix(".html")
    if not out.is_absolute():
        out = ROOT / out
    out.write_text(build_html(title, scenes, lede, check_md), encoding="utf-8")
    print(f"[OK ] {out.relative_to(ROOT) if out.is_relative_to(ROOT) else out}"
          f"  ({len(scenes)} 场景, 怎么看 {len(check_md)} 字)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
