"""为图片生成「伴随文字文档」(.md)，让不支持多模态的 Agent 也能读到图上内容。

用法：
    python tools/ocr_companion.py                 # 处理默认清单（assets 下信息承载类图片）
    python tools/ocr_companion.py -f <图片路径>   # 只处理指定图片
    python tools/ocr_companion.py -a              # 处理 assets 下全部图片
    python tools/ocr_companion.py -o index.md     # 额外生成总索引

输出：每个图片同目录下 <同名>.md，包含
    1) 文件元信息（尺寸/体积/时间/哈希）
    2) OCR 原文（按版面行序，带置信度，低分标 ⚠）
    3) 结构化摘要区（机器填不到的部分留空，标注未核实）
    4) 下游 Agent 使用说明

依赖：pip install pillow rapidocr-onnxruntime opencv-python-headless
"""
from __future__ import annotations

import argparse
import hashlib
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"

# 默认清单：只处理承载信息的照片/截图/讲义翻拍；
# AI 生成的配图、产品实拍照、视频抽帧默认跳过（文字信息量低，OCR 无意义）。
DEFAULT_SET = [
    "day1025/lecture/*.jpg",
    "day1024/submit/sunwin-prototype*.png",
    "real_request.png",
    "problem-original-photo.jpg",
    "survey-detail-photo-05.jpg",
    "training-camp-site-photo.jpg",
    "overview-preview.png",
    "day1023/交付物说明.png",
    "day1023/六道题-寻找问题.jpg",
    "day1023/微信图片_*.jpg",
]

MAX_SIDE = 1600          # OCR 前把最长边缩到此值，提速且基本不掉字
LOW_CONF = 0.80          # 低于此置信度的行标记 ⚠ 未核实


def ocr_engine():
    from rapidocr_onnxruntime import RapidOCR
    return RapidOCR()


def sha256_short(p: Path, n: int = 12) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:n]


def run_ocr(engine, img_path: Path):
    """返回 [(text, score), ...]，按版面从上到下、行内从左到右。"""
    import numpy as np
    from PIL import Image

    img = Image.open(img_path)
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    w, h = img.size
    scale = min(1.0, MAX_SIDE / max(w, h))
    if scale < 1.0:
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
    arr = np.array(img.convert("RGB"))

    result, _ = engine(arr)
    lines = []
    for item in result or []:
        box, text, score = item[0], item[1], item[2]
        ys = [pt[1] for pt in box]
        xs = [pt[0] for pt in box]
        lines.append((sum(ys) / len(ys), sum(xs) / len(xs), text, float(score)))

    # 按 y 分行（同一行 y 差 < 14px 视为同版行），行内按 x 排序
    lines.sort(key=lambda t: (t[0], t[1]))
    rows, cur = [], []
    for y, x, text, score in lines:
        if cur and abs(y - cur[-1][0]) > 14:
            rows.append(cur)
            cur = []
        cur.append((y, x, text, score))
    if cur:
        rows.append(cur)

    out = []
    for row in rows:
        row.sort(key=lambda t: t[1])
        seg_text = "  ".join(t[2].strip() for t in row)
        avg_score = sum(t[3] for t in row) / len(row)
        out.append((seg_text, avg_score))
    return out


def build_md(img: Path, rows, size_kb: int, dims, sha: str, mtime: str) -> str:
    low = [t for t, s in rows if s < LOW_CONF]
    body_lines = []
    for text, score in rows:
        flag = " ⚠" if score < LOW_CONF else ""
        body_lines.append(f"- {text}`[{score:.2f}]`{flag}")
    ocr_block = "\n".join(body_lines) if body_lines else "_（OCR 未识别出文字：可能是纯图片/图表，需多模态模型补录）_"

    low_block = (
        "\n".join(f"- {t}" for t in low)
        if low
        else "无"
    )

    return f"""# 图片伴随文档 · {img.name}

> 自动生成 `{datetime.now().strftime('%Y-%m-%d %H:%M')}` ｜ 工具：`tools/ocr_companion.py`
> 用途：给不支持多模态的 Agent 提供这张图的文字内容与元信息

## 1. 元信息

| 项 | 值 |
|----|-----|
| 路径 | `{img.relative_to(ROOT).as_posix()}` |
| 尺寸 | {dims[0]} × {dims[1]} px |
| 体积 | {size_kb} KB |
| 修改时间 | {mtime} |
| SHA256 前 {len(sha)} 位 | `{sha}` |

## 2. OCR 原文（按版面行序）

每条行尾 `[数字]` 为该行平均置信度，`⚠` 表示置信度 < {LOW_CONF}，**不得直接引用**。

{ocr_block}

## 3. 低置信度行（需人工/多模态复核）

{low_block}

## 4. 结构化摘要

> ⚠️ 本区需要**人工或多模态模型补录**。OCR 只给文字，不给理解；
> 任何未在此处写明的内容，下游 Agent 不得当作事实使用。

- 图面类型：（讲义照片 / 截图 / 表单 / 白板 / 其他）
- 核心主张：
- 关键数据：
- 与其它文件的关联：

## 5. 下游 Agent 怎么用

1. 只读「第 2 节」的文字，把它当作**线索**而非结论。
2. `⚠` 行、以及第 3 节的任何内容，引用前必须回到原图确认。
3. 需要理解图表/版式/图像含义时，请让多模态模型或人工读原图 `{img.name}`。
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-f", "--file", action="append", default=[], help="指定图片路径")
    ap.add_argument("-a", "--all", action="store_true", help="处理 assets 下全部图片")
    ap.add_argument("-o", "--index", help="生成总索引文件路径")
    args = ap.parse_args()

    targets: list[Path] = []
    if args.file:
        targets = [Path(x) if Path(x).is_absolute() else ASSETS / x for x in args.file]
    elif args.all:
        for ext in ("*.png", "*.jpg", "*.jpeg"):
            targets += sorted(ASSETS.rglob(ext))
    else:
        for pat in DEFAULT_SET:
            targets += sorted(ASSETS.glob(pat))

    targets = sorted({p.resolve() for p in targets if p.exists()})
    if not targets:
        print("没有匹配的图片")
        return 1

    print(f"待处理 {len(targets)} 张，加载 OCR 引擎…", flush=True)
    engine = ocr_engine()

    done = []
    for i, img in enumerate(targets, 1):
        print(f"[{i}/{len(targets)}] {img.name}", flush=True)
        try:
            rows = run_ocr(engine, img)
            size_kb = img.stat().st_size // 1024
            from PIL import Image
            dims = Image.open(img).size
            md = build_md(
                img, rows, size_kb, dims,
                sha256_short(img),
                datetime.fromtimestamp(img.stat().st_mtime).strftime("%Y-%m-%d %H:%M"),
            )
            out = img.with_suffix(".md")
            out.write_text(md, encoding="utf-8")
            done.append((img, out, len(rows)))
        except Exception as e:  # noqa: BLE001
            print(f"  !! 失败：{e}", file=sys.stderr)

    print(f"\n完成 {len(done)}/{len(targets)}")

    if args.index:
        idx = Path(args.index)
        lines = ["# 图片伴随文档索引", "", f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}", "",
                 "| 原图 | 伴随文档 | OCR 行数 |", "|------|----------|---------|"]
        for img, out, n in done:
            lines.append(f"| `{img.relative_to(ROOT).as_posix()}` | `{out.relative_to(ROOT).as_posix()}` | {n} |")
        lines += ["", "规则：任何图片 → 同目录同名 `.md`；`⚠` 行不可直接引用。"]
        idx.write_text("\n".join(lines), encoding="utf-8")
        print(f"总索引：{idx}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
