"""报告构建：把模型输入嵌入HTML快照，渲染Mermaid，去除外部字体依赖。

只生成本报告目录内文件，不修改源演示、产品规格或项目配置。
"""
import json
from pathlib import Path
import re
import subprocess
import sys


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    here = Path(__file__).resolve().parent
    root = here.parents[2]
    model = json.loads((here / "model-inputs.json").read_text(encoding="utf-8"))
    source = (here / "index.src.html").read_text(encoding="utf-8")
    data = json.dumps(model, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    source, count = re.subn(
        r'(<script id="model-data" type="application/json">).*?(</script>)',
        lambda match: match[1] + data + match[2], source, flags=re.S,
    )
    if count != 1:
        raise ValueError("HTML必须有且仅有一个模型数据区")
    intermediate = here / "index.render.src.html"
    intermediate.write_text(source, encoding="utf-8")
    renderer = root / ".kilo/skills/visual-explainer/kit/render.mjs"
    subprocess.run(["node", str(renderer), str(intermediate)], check=True, cwd=root)
    rendered = (here / "index.render.html").read_text(encoding="utf-8")
    rendered = re.sub(r'<link\b[^>]*https://fonts\.(?:googleapis|gstatic)\.com[^>]*>\s*', "", rendered)
    if re.search(r'<(?:script|link)\b[^>]*(?:src|href)=["\']https?://', rendered, re.I):
        raise ValueError("成品仍包含远程脚本或样式依赖")
    (here / "index.html").write_text(rendered, encoding="utf-8")
    print("[OK] index.html：模型输入已同步，3幅Mermaid内联SVG，无远程字体/脚本/样式依赖")
    print("[NOTE] 配套视频及报告用相对路径，不嵌入单文件；需保留整个交付目录。")
