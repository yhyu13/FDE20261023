"""成片缩略拼版：一次看完一个视频的所有场景。

为什么必须做：HTTP 200、脚本无报错、退出码 0，都不能说明版面是对的。
自动判据全绿也可能是错的版面（实测踩过：两栏内容被竖着堆起来，
所有信号都绿）。所以要**看图**。

用法：

    python tools/video/contact_sheet.py --Video build/04/讲解视频.mp4 --Out build/04/拼版.png
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

VENDOR = Path(__file__).resolve().parent / "vendor"
if str(VENDOR) not in sys.path:
    sys.path.insert(0, str(VENDOR))

from ffmedia import probe_duration  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="成片缩略拼版")
    ap.add_argument("--Video", required=True)
    ap.add_argument("--Out", required=True)
    ap.add_argument("--Cols", type=int, default=4, dest="cols")
    ap.add_argument("--Rows", type=int, default=4, dest="rows")
    ap.add_argument("--Width", type=int, default=480, dest="width", help="单格宽")
    args = ap.parse_args()

    from PIL import Image

    video = Path(args.Video)
    out = Path(args.Out)
    dur = probe_duration(video)
    n = args.cols * args.rows

    times = [dur * (i + 0.5) / n for i in range(n)]
    tmp = out.parent / "_sheet"
    tmp.mkdir(parents=True, exist_ok=True)

    tiles = []
    for i, t in enumerate(times):
        p = tmp / f"s{i:02d}.png"
        subprocess.run(
            ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
             "-ss", f"{t:.3f}", "-i", str(video), "-frames:v", "1", str(p)],
            check=True,
        )
        if not p.exists():
            raise SystemExit(f"[ERR] 抽帧失败：t={t:.2f}s")
        tiles.append(Image.open(p).convert("RGB").resize(
            (args.width, int(args.width * 1080 / 1920)), Image.LANCZOS))

    tw, th = tiles[0].size
    pad = 6
    sheet = Image.new("RGB", (args.cols * tw + (args.cols + 1) * pad,
                              args.rows * th + (args.rows + 1) * pad), (18, 18, 20))
    for i, tile in enumerate(tiles):
        r, c = divmod(i, args.cols)
        sheet.paste(tile, (pad + c * (tw + pad), pad + r * (th + pad)))
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)

    print(f"[OK ] 拼版 {out}  {sheet.size[0]}x{sheet.size[1]}  {n} 格 / {dur:.1f}s")
    print(f"     抽帧时刻：{', '.join(f'{t:.0f}s' for t in times)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
