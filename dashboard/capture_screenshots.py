"""Takes the README screenshots from the real, rendered dashboard (optional tool).

    pip install -r requirements-dev.txt
    python dashboard/capture_screenshots.py                # writes docs/images/dashboard-*.png
    python dashboard/capture_screenshots.py --out some/dir

It opens dashboard/index.html in a headless Chromium-based browser at a fixed width, waits for the
fonts and for the KPI count-up animation to finish, and saves one image per view. Nothing is drawn or
edited by hand. Set DIVVY_BROWSER=/path/to/chromium if Playwright cannot find a browser.
"""
import argparse
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sys.exit("playwright is not installed: pip install -r requirements-dev.txt")

ap = argparse.ArgumentParser(description="Capture dashboard screenshots")
ap.add_argument("--out", type=Path, default=ROOT / "docs" / "images")
ap.add_argument("--width", type=int, default=1200)
args = ap.parse_args()
args.out.mkdir(parents=True, exist_ok=True)
PAGE = (HERE / "index.html").as_uri()

try:  # optional: shrink the PNGs (flat UI colours compress very well with a 256-colour palette)
    from PIL import Image
except ImportError:
    Image = None


def save(path_png):
    if Image is None:
        return
    im = Image.open(path_png).convert("RGB")
    im.quantize(colors=256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE).save(path_png, optimize=True)


def launch(p):
    attempts = [{}]
    if os.environ.get("DIVVY_BROWSER"):
        attempts.insert(0, {"executable_path": os.environ["DIVVY_BROWSER"]})
    attempts += [{"channel": "chrome"}, {"channel": "msedge"}]
    for kw in attempts:
        try:
            return p.chromium.launch(**kw)
        except Exception:
            continue
    sys.exit("no Chromium-based browser found (set DIVVY_BROWSER)")


def settle(page):
    page.wait_for_selector(".kpi .v")
    page.evaluate("document.fonts.ready")
    page.wait_for_function("document.querySelectorAll('.kpi .v')[0].textContent.replace(/[^0-9]/g, '').length >= 7", timeout=10000)
    page.wait_for_timeout(900)  # let the 450 ms count-up finish


def shoot(page, name, upto_panel=None):
    """Full page, or only down to the bottom of panel number `upto_panel` (0-based)."""
    height = page.evaluate("document.documentElement.scrollHeight")
    if upto_panel is not None:
        height = int(page.evaluate("(i) => document.querySelectorAll('#main .panel')[i].getBoundingClientRect().bottom + window.scrollY", upto_panel)) + 10
    target = args.out / name
    page.screenshot(path=str(target), full_page=True, clip={"x": 0, "y": 0, "width": args.width, "height": height})
    save(target)
    print("wrote", target, "%d x %d, %d KB" % (args.width, height, target.stat().st_size / 1024))


with sync_playwright() as p:
    browser = launch(p)
    page = browser.new_context(viewport={"width": args.width, "height": 900}, device_scale_factor=1).new_page()
    for tab, name, upto in (("rides", "dashboard-overview.png", 2), ("stations", "dashboard-stations.png", None),
                            ("flow", "dashboard-routes.png", None), ("money", "dashboard-money.png", None)):
        page.goto(PAGE + "#" + tab)
        settle(page)
        shoot(page, name, upto)
    browser.close()
