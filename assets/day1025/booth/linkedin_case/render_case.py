from playwright.sync_api import sync_playwright
from PIL import Image
import pathlib

base = pathlib.Path(r"D:\GitRepo-AI\FDE20261023\assets\day1025\booth")
src = base / "linkedin_case" / "linkedin_case.html"

with sync_playwright() as p:
    b = p.chromium.launch()
    page = b.new_page(viewport={"width": 2560, "height": 1440}, device_scale_factor=2)
    page.goto(src.as_uri(), wait_until="load")
    page.evaluate("document.fonts.ready")
    page.wait_for_timeout(1200)
    page.screenshot(path=str(base / "linkedin_case" / "_case_render_5120.png"))
    b.close()

im = Image.open(base / "linkedin_case" / "_case_render_5120.png")
print("raw", im.size)
im.resize((3840, 2160), Image.LANCZOS).save(base / "sunwin_linkedin_case_3840x2160.png", optimize=True)
im.resize((2560, 1440), Image.LANCZOS).save(base / "linkedin_case" / "_case_preview_2560.png", optimize=True)
im.resize((1280, 720), Image.LANCZOS).convert("RGB").save(base / "linkedin_case" / "_case_check_1280.jpg", quality=82, optimize=True)
print("done")
