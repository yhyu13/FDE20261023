"""Isolated artifact checks. Does not run or modify the product's tests or gates."""
import argparse
import copy
import importlib.util
import json
import math
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import unquote

from PIL import Image, ImageDraw, ImageFont
from playwright.sync_api import sync_playwright

sys.dont_write_bytecode = True
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--with-video", action="store_true")
    args = ap.parse_args()
    root = Path(args.root).resolve()
    out = root / "html-validation"
    out.mkdir(exist_ok=True)
    result = {"scope": "new report artifacts only; not the old product", "checks": [], "screenshots": [], "video": None}

    def check(name, condition, detail=None):
        row = {"name": name, "ok": bool(condition)}
        if detail is not None:
            row["detail"] = detail
        result["checks"].append(row)
        print(("[OK] " if condition else "[FAIL] ") + name, json.dumps(detail, ensure_ascii=False) if detail is not None else "")

    model = json.loads((root / "model-inputs.json").read_text(encoding="utf-8"))
    stored = json.loads((root / "model-results.json").read_text(encoding="utf-8"))
    spec = importlib.util.spec_from_file_location("audit_calculate", root / "calculate.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    fresh = json.loads(json.dumps(module.calculate(model), default=module.output))
    check("Python results equal canonical recomputation", stored == fresh)
    check("85000 total / 73000 external / 4 orders", stored["customer_total_listed_cost"] == 85000 and stored["customer_assumed_external_payments"] == 73000 and stored["break_even_orders"] == 4)
    check("software revenue is not customer spend", stored["vendor_service_revenue"] == 15000 and stored["vendor_direct_cost"] == 12500 and stored["vendor_delivery_contribution"] == 2500)
    invalid = copy.deepcopy(model)
    invalid["customer_costs"][0]["amount"] = -1
    try:
        module.calculate(invalid)
        rejected = False
    except ValueError:
        rejected = True
    check("negative cost rejected by Python", rejected)
    zero = copy.deepcopy(model)
    zero["incremental_share"] = 0
    check("zero incremental share has no finite break even", module.calculate(zero)["break_even_orders"] is None)

    html = (root / "index.html").read_text(encoding="utf-8")
    check("no remote script/style/font resources", re.search(r'<(?:script|link)\b[^>]*(?:src|href)=["\']https?://', html, re.I) is None)
    check("three Mermaid figures compiled with responsive SVG variants", html.count('class="ve-mermaid"') == 3 and html.count('aria-roledescription="flowchart"') >= 3, {"figures": html.count('class="ve-mermaid"'), "svg_variants": html.count('aria-roledescription="flowchart"')})
    images = []
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe", headless=True, args=["--allow-file-access-from-files"])
        context = browser.new_context(viewport={"width": 1440, "height": 1000}, color_scheme="light", reduced_motion="reduce")
        external = []
        context.route(re.compile(r"https?://"), lambda route: (external.append(route.request.url), route.abort()))
        page = context.new_page()
        js_errors = []
        console_errors = []
        page.on("pageerror", lambda exc: js_errors.append(str(exc)))
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
        page.goto((root / "index.html").as_uri(), wait_until="load")
        page.wait_for_function("window.reviewResult && window.reviewResult.valid")
        check("HTML canonical JSON equals model-inputs.json", page.locator("#model-data").evaluate("e => JSON.parse(e.textContent)") == model)
        state = page.evaluate("window.reviewResult")
        check("browser default net -10000 / ROI -11.76% / break-even 4", state["net"] == -10000 and abs(state["roi"] + 10000 / 85000) < 1e-12 and state["breakEven"] == 4, state)
        check("rendered default displayed to user", page.locator("#net-result").inner_text() == "¥-10,000" and page.locator("#roi").inner_text() == "-11.76%")
        for case, net in [("conservative", -60000), ("optimistic", 65000)]:
            page.locator('[data-case="' + case + '"]').click()
            check(case + " button updates economics", page.evaluate("window.reviewResult.net") == net)
        page.locator("#reset").click()
        page.locator("#incremental").fill("50")
        state = page.evaluate("window.reviewResult")
        check("50% incrementality shows loss 47500 and break-even 7", state["net"] == -47500 and state["breakEven"] == 7 and page.locator("#roi").inner_text() == "-55.88%", state)
        page.locator("#incremental").fill("0")
        check("zero incremental share is not Infinity", page.locator("#break-even").inner_text() == "不可回本")
        page.locator("#reset").click()
        page.locator("#orders").fill("0")
        check("zero orders shows full loss", page.evaluate("window.reviewResult.net") == -85000 and page.locator("#roi").inner_text() == "-100.00%")
        page.locator("#orders").fill("1.5")
        check("fractional customer count rejected and stale result cleared", not page.evaluate("window.reviewResult.valid") and page.locator("#net-result").inner_text() == "不可计算")
        page.locator("#reset").click()
        page.locator("#revenue").fill("")
        check("blank revenue is not silently zero", not page.evaluate("window.reviewResult.valid"))
        page.locator("#reset").click()
        for row in model["customer_costs"]:
            page.locator("#cost-" + row["id"]).fill("0")
        check("zero denominator returns not calculable", page.locator("#roi").inner_text() == "不可计算")
        page.locator("#reset").click()
        page.locator("#cost-software").fill("20000")
        check("cost edit propagates without double counting", page.evaluate("window.reviewResult.net") == -15000 and page.evaluate("window.reviewResult.total") == 90000)
        for row in model["customer_costs"]:
            page.locator("#cost-" + row["id"]).fill("0")
        page.locator("#cost-media").fill("14500")
        page.locator("#revenue").fill("100000")
        page.locator("#margin").fill("25")
        page.locator("#incremental").fill("29")
        check("exact decimal break-even boundary is 2 not 3", page.evaluate("window.reviewResult.breakEven") == 2, page.evaluate("window.reviewResult"))
        page.locator("#reset").click()
        check("static scenarios remain explicitly default", page.locator("#scenarios tr").count() == 3 and "¥-10,000" in page.locator("#scenarios").inner_text())
        check("four figures each have caption", page.locator("figure").count() == 4 and page.locator("figure > figcaption").count() == 4)
        check("no JavaScript errors", not js_errors, js_errors)
        check("no external network dependency", not external, external)
        missing_links = []
        for link in page.locator(".download a").all():
            target = root / unquote(link.get_attribute("href"))
            if not target.is_file():
                missing_links.append(str(target))
        check("all report and media download links exist", not missing_links, missing_links)

        page.evaluate("window.scrollTo(0,0)")
        top = out / "desktop-overview.png"
        page.screenshot(path=top, animations="disabled")
        images.append(("Desktop overview", top))
        for selector, filename in [("#model", "desktop-economics.png"), ("#critique", "desktop-critique.png"), ("#skills", "desktop-skills.png")]:
            target = page.locator(selector)
            target.scroll_into_view_if_needed()
            image = out / filename
            target.screenshot(path=image, animations="disabled")
            images.append((filename, image))
        page.set_viewport_size({"width": 390, "height": 844})
        page.evaluate("window.scrollTo(0,0)")
        check("mobile body has no horizontal overflow", page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"), page.evaluate("({width:innerWidth,scroll:document.documentElement.scrollWidth})"))
        mobile = out / "mobile-overview.png"
        page.screenshot(path=mobile, animations="disabled")
        images.append(("Mobile overview", mobile))
        mobile_model = out / "mobile-economics.png"
        page.locator("#model").screenshot(path=mobile_model, animations="disabled")
        images.append(("Mobile economics", mobile_model))

        if args.with_video:
            page.set_viewport_size({"width": 1440, "height": 1000})
            page.reload(wait_until="load")
            page.wait_for_function("document.querySelector('video').readyState >= 2", timeout=60000)
            v = page.locator("video")
            metadata = v.evaluate("v => ({duration:v.duration,width:v.videoWidth,height:v.videoHeight,readyState:v.readyState,error:v.error&&v.error.message})")
            check("browser decodes 1080p video", metadata["width"] == 1920 and metadata["height"] == 1080 and metadata["duration"] > 100 and metadata["error"] is None, metadata)
            samples = []
            for fraction in [0.08, 0.5, 0.92]:
                when = metadata["duration"] * fraction
                v.evaluate("(v,t)=>{v.currentTime=t}", when)
                page.wait_for_function("t => {const v=document.querySelector('video');return Math.abs(v.currentTime-t)<.15&&!v.seeking&&v.readyState>=2}", arg=when, timeout=30000)
                pixel = v.evaluate("v => {const c=document.createElement('canvas');c.width=160;c.height=90;const x=c.getContext('2d');x.drawImage(v,0,0,160,90);const d=x.getImageData(0,0,160,90).data;let sum=0;const colors=new Set();for(let i=0;i<d.length;i+=4){sum+=(d[i]+d[i+1]+d[i+2])/3;colors.add((d[i]>>3)+','+(d[i+1]>>3)+','+(d[i+2]>>3));}return {mean:sum/(d.length/4),colors:colors.size};}")
                samples.append({"time": when, **pixel})
                check("seek renders content at " + str(round(when, 1)), pixel["colors"] > 30 and 5 < pixel["mean"] < 253, pixel)
            result["video"] = {"metadata": metadata, "seek_samples": samples, "delivery": "local file; no public HTTP deployment"}
            playback_start = v.evaluate("v => v.currentTime")
            v.evaluate("v => {v.muted=true; return v.play();}")
            page.wait_for_function("t => {const v=document.querySelector('video');return !v.paused&&v.currentTime>t+.3&&v.readyState>=2}", arg=playback_start, timeout=30000)
            check("video playback actually advances", v.evaluate("v => !v.paused && v.readyState>=2"))
            v.evaluate("v => v.pause()")
            v.scroll_into_view_if_needed()
            video_shot = out / "browser-video.png"
            v.screenshot(path=video_shot)
            images.append(("Video browser decode", video_shot))
            check("final browser console has no resource errors", not console_errors, console_errors)
        else:
            result["provisional_console_notes"] = console_errors
        browser.close()

    font = ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", 20)
    thumb_w, thumb_h = 600, 460
    sheet = Image.new("RGB", (thumb_w * 2, (math.ceil(len(images) / 2)) * (thumb_h + 45)), "#e8e9e5")
    draw = ImageDraw.Draw(sheet)
    for i, (label, path) in enumerate(images):
        image = Image.open(path).convert("RGB")
        image.thumbnail((thumb_w - 20, thumb_h - 10))
        x, y = (i % 2) * thumb_w + 10, (i // 2) * (thumb_h + 45)
        draw.text((x, y + 4), label, fill="#1a2429", font=font)
        sheet.paste(image, (x, y + 36))
    sheet.save(out / "contact-sheet.png")
    result["screenshots"] = [str(path.relative_to(root)) for _, path in images]
    result["all_checks_passed"] = all(row["ok"] for row in result["checks"])
    result["check_count"] = len(result["checks"])
    result["video_included"] = args.with_video
    (out / "results.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("[RESULT]", str(out / "results.json"))
    return 0 if result["all_checks_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
