from playwright.sync_api import sync_playwright
from PIL import Image
import pathlib

base = pathlib.Path(r"D:\GitRepo-AI\FDE20261023\assets\day1025\booth")
src = base / "poster" / "poster.html"

with sync_playwright() as p:
    b = p.chromium.launch()
    page = b.new_page(viewport={"width": 2560, "height": 1440}, device_scale_factor=2)
    page.goto(src.as_uri(), wait_until="load")
    page.evaluate("document.fonts.ready")
    page.wait_for_timeout(1200)
    page.screenshot(path=str(base / "poster" / "_render_5120.png"))
    b.close()

im = Image.open(base / "poster" / "_render_5120.png")
print("raw", im.size)
im.resize((3840, 2160), Image.LANCZOS).save(base / "sunwin_poster_3840x2160.png", optimize=True)
im.resize((2560, 1440), Image.LANCZOS).save(base / "poster" / "_preview_2560.png", optimize=True)
print("done")
