"""Browser smoke test for dashboard/index.html (optional: needs Playwright and a Chromium-based browser).

    pip install -r requirements-dev.txt
    python tests/smoke_dashboard.py

The page is opened from disk (file://), so nothing needs a server or an Azure connection.
Set DIVVY_URL=https://.../dashboard/ to run the same checks against a deployed copy.
Set DIVVY_BROWSER=/path/to/chromium-or-chrome if Playwright cannot find a browser by itself.
Exit code 0 = every check passed, 1 = a check failed, 2 = Playwright or a browser is not available (skipped).
"""
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGE = os.environ.get("DIVVY_URL") or (ROOT / "dashboard" / "index.html").as_uri()  # set DIVVY_URL to test a deployed copy
DATA = json.loads((ROOT / "dashboard" / "data.json").read_text())
TABS = ["rides", "stations", "flow", "money", "riders", "usage", "quality"]
FILTERS = ["all", "member", "casual"]
VIEWPORTS = {"desktop": (1280, 900), "tablet": (820, 1180), "mobile": (390, 844)}

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("SKIP: playwright is not installed (pip install -r requirements-dev.txt)")
    sys.exit(2)

passed, failed = [], []


def check(name, ok, detail=""):
    (passed if ok else failed).append(name)
    print(("PASS  " if ok else "FAIL  ") + name + ("" if ok or not detail else "  -> " + str(detail)))


def usd_m(n):
    return "$%.2fM" % (n / 1e6) if n >= 1e6 else ("$%.0fk" % (n / 1e3) if n >= 1e3 else "$%.0f" % n)


def expected_kpis(key):
    f = DATA["f"][key]
    return ["{:,}".format(f["rides"]), "%.1f min" % f["avg"], usd_m(f["spend_total"]), "$%.2f" % f["avg_payment"], "{:,}".format(f["riders"])]


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
    return None


def luminance(rgb):
    def ch(c):
        c /= 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = rgb
    return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b)


def contrast(a, b):
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


TEXT_SAMPLES = [".kpi .l", ".kpi .n", ".kpi .v", ".panel h2", ".panel .ins", ".panel .cap", ".chip", '.chip[aria-pressed="true"]', ".tabs button", ".foot span"]


def text_contrast(page):
    """(selector, ratio) for sample text elements: computed colour against the first opaque background above it."""
    return page.evaluate(r"""(sels) => {
      const parse = c => { const m = c.match(/rgba?\(([^)]+)\)/); if (!m) return null; const p = m[1].split(',').map(Number); return {r:p[0], g:p[1], b:p[2], a:p.length>3?p[3]:1}; };
      const bgOf = el => { for (let e = el; e; e = e.parentElement) { const c = parse(getComputedStyle(e).backgroundColor); if (c && c.a > 0.99) return c; } return {r:255,g:255,b:255,a:1}; };
      return sels.map(s => { const el = document.querySelector(s); if (!el) return [s, null]; const fg = parse(getComputedStyle(el).color), bg = bgOf(el); return [s, [fg.r, fg.g, fg.b, bg.r, bg.g, bg.b]]; });
    }""", TEXT_SAMPLES)


def select_tab(page, tab):
    page.click('#tabs [data-t="%s"]' % tab)
    page.wait_for_function("document.querySelector('#tabs [data-t=\"%s\"]').getAttribute('aria-selected')==='true'" % tab)
    page.wait_for_timeout(120)


def select_filter(page, key):
    page.click('#seg [data-f="%s"]' % key)
    page.wait_for_function("document.querySelector('#seg [data-f=\"%s\"]').getAttribute('aria-pressed')==='true'" % key)
    page.wait_for_timeout(120)


def bad_text(page):
    txt = page.inner_text("body")
    return sorted(set(re.findall(r"\b(NaN|undefined|Infinity|null)\b", txt)))


def overflow_offenders(page):
    return page.evaluate("""() => {
      const W = window.innerWidth, bad = [];
      if (document.documentElement.scrollWidth > W + 1) bad.push('page scrolls sideways: ' + document.documentElement.scrollWidth + ' > ' + W);
      document.querySelectorAll('#main *, .head *, .kpis *, .tabs *').forEach(e => {
        if (e.closest('.scroll') || e.closest('svg')) return;
        const r = e.getBoundingClientRect();
        if (r.width > 0 && r.right > W + 2) bad.push(e.tagName + '.' + (e.className && e.className.baseVal === undefined ? e.className : '') + ' right=' + Math.round(r.right));
      });
      return bad.slice(0, 5);
    }""")


with sync_playwright() as p:
    browser = launch(p)
    if browser is None:
        print("SKIP: no Chromium-based browser found (set DIVVY_BROWSER)")
        sys.exit(2)

    ctx = browser.new_context(viewport={"width": 1280, "height": 900})
    page = ctx.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append("pageerror: %s" % e))
    page.on("console", lambda m: errors.append("console.error: %s" % m.text) if m.type == "error" and "fonts.g" not in m.text and "ERR_" not in m.text else None)
    page.goto(PAGE)
    page.wait_for_selector(".kpi .v")

    # 1. document structure
    check("document has a doctype, lang and title", page.evaluate("document.doctype && document.doctype.name==='html' && document.documentElement.lang==='en' && document.title==='Divvy Ride Atlas'"))
    check("no external script or data requests (only fonts)", page.evaluate("[...document.querySelectorAll('script[src],link[rel=stylesheet]')].every(e => /fonts\\.googleapis\\.com/.test(e.href||''))"))

    # 2. KPIs for each filter
    for key in FILTERS:
        select_filter(page, key)
        want = expected_kpis(key)
        try:
            page.wait_for_function("(w) => JSON.stringify([...document.querySelectorAll('.kpi .v')].map(e => e.textContent)) === JSON.stringify(w)", arg=want, timeout=4000)
            check("KPI cards match data.json for filter '%s'" % key, True)
        except Exception:
            check("KPI cards match data.json for filter '%s'" % key, False, page.eval_on_selector_all(".kpi .v", "els => els.map(e=>e.textContent)"))
    select_filter(page, "all")
    f = DATA["f"]
    check("members + casual reconcile to all riders (rides, payments, riders)",
          f["member"]["rides"] + f["casual"]["rides"] == f["all"]["rides"] and f["member"]["payments"] + f["casual"]["payments"] == f["all"]["payments"]
          and f["member"]["riders"] + f["casual"]["riders"] == f["all"]["riders"])
    iss = DATA["meta"]["issues"]
    check("valid + invalid durations equal total trips; valid equals dashboard rides", sum(iss.values()) == DATA["meta"]["trips_total"] and iss["ok"] == f["all"]["rides"])

    # 3. every tab under every filter renders without bad values
    for key in FILTERS:
        select_filter(page, key)
        for tab in TABS:
            select_tab(page, tab)
            panels = page.locator("#main .panel").count()
            ins = page.locator("#main .ins").count()
            check("tab '%s' renders under '%s' (%d panels, %d insights, no NaN/undefined)" % (tab, key, panels, ins), panels >= 2 and ins >= 1 and not bad_text(page), bad_text(page))
            check("URL hash follows tab '%s'" % tab, page.evaluate("location.hash") == "#" + tab) if key == "all" else None
    select_filter(page, "all")

    # 4. filters change the content, not just the KPIs
    select_tab(page, "rides")
    a = page.inner_text("#main .ins")
    select_filter(page, "casual"); b = page.inner_text("#main .ins"); select_filter(page, "all")
    check("rider-type filter changes the chart insight text", a != b)

    # 5. direct links, back / forward
    p2 = ctx.new_page(); p2.goto(PAGE + "#money"); p2.wait_for_selector(".kpi .v")
    check("direct link #money opens the Money tab", p2.get_attribute('#tabs [data-t="money"]', "aria-selected") == "true")
    p2.goto(PAGE + "#nonsense"); p2.wait_for_selector(".kpi .v")
    check("unknown hash falls back to the first tab", p2.get_attribute('#tabs [data-t="rides"]', "aria-selected") == "true")
    p2.goto(PAGE + "#rides"); p2.wait_for_selector(".kpi .v")
    p2.click('#tabs [data-t="stations"]'); p2.click('#tabs [data-t="money"]')
    p2.go_back(); p2.wait_for_timeout(200)
    check("browser Back returns to the previous tab", p2.get_attribute('#tabs [data-t="stations"]', "aria-selected") == "true")
    p2.go_forward(); p2.wait_for_timeout(200)
    check("browser Forward returns to the next tab", p2.get_attribute('#tabs [data-t="money"]', "aria-selected") == "true")
    p2.close()

    # 6. keyboard navigation
    page.goto(PAGE + "#rides"); page.wait_for_selector(".kpi .v")
    page.focus('#tabs [data-t="rides"]'); page.keyboard.press("ArrowRight"); page.wait_for_timeout(150)
    check("ArrowRight moves to the next tab and keeps focus there", page.get_attribute('#tabs [data-t="stations"]', "aria-selected") == "true" and page.evaluate("document.activeElement.dataset.t") == "stations")
    page.keyboard.press("End"); page.wait_for_timeout(150)
    check("End jumps to the last tab", page.get_attribute('#tabs [data-t="quality"]', "aria-selected") == "true")
    page.keyboard.press("Home"); page.wait_for_timeout(150)
    check("Home jumps to the first tab", page.get_attribute('#tabs [data-t="rides"]', "aria-selected") == "true")
    check("only the selected tab is in the tab order", page.evaluate("[...document.querySelectorAll('#tabs button')].filter(b => b.tabIndex===0).length") == 1)
    check("tab panel is labelled by the selected tab", page.get_attribute("#main", "aria-labelledby") == "tab-rides")

    # 7. tooltips
    select_tab(page, "rides")
    page.hover("#main svg rect >> nth=30"); page.wait_for_timeout(150)
    check("heatmap cell shows a tooltip with ride counts", page.evaluate("getComputedStyle(document.querySelector('#tip')).opacity") == "1" and "rides" in page.inner_text("#tip"), page.inner_text("#tip"))
    page.mouse.move(5, 5)
    select_tab(page, "stations")
    page.hover("#main svg circle >> nth=40", force=True); page.wait_for_timeout(150)
    check("station dot shows a tooltip with the station name", page.evaluate("getComputedStyle(document.querySelector('#tip')).opacity") == "1" and "min average" in page.inner_text("#tip"), page.inner_text("#tip"))
    page.mouse.move(5, 5)

    # 8. controls: chips and sliders
    select_tab(page, "rides"); before = page.inner_text("#main .ins")
    page.click("#main .chip >> text=Number of rides"); page.wait_for_timeout(150)
    check("heatmap metric toggle updates the insight", page.inner_text("#main .ins") != before)
    select_tab(page, "stations")
    first0 = page.inner_text(".li >> nth=0")
    page.evaluate("const r=document.querySelector('#mr'); r.value=1000; r.dispatchEvent(new Event('input',{bubbles:true}))"); page.wait_for_timeout(150)
    rides = [int(x.replace(",", "")) for x in re.findall(r"([\d,]+) rides", " ".join(page.locator(".li small").all_inner_texts()))]
    check("stations minimum-rides slider only lists stations above the minimum (%d items, smallest %s rides)" % (len(rides), min(rides) if rides else "n/a"),
          len(rides) > 0 and min(rides) >= 1000 and page.inner_text(".li >> nth=0") != first0)
    page.evaluate("state.minRides = 100000; render()"); page.wait_for_timeout(150)
    check("stations tab explains an empty ranking", "No station has that many rides" in page.inner_text("#main") and not bad_text(page))
    page.evaluate("state.minRides = 100; render()")
    page.click("#main .chip >> text=Rides ending here"); page.wait_for_timeout(150)
    check("station role toggle (start/end) keeps a populated map", page.locator("#main svg circle").count() > 500)
    select_tab(page, "flow")
    page.click("#main .chip >> text=Filling up"); page.wait_for_timeout(150)
    check("flow watch-list toggle renders", page.locator("#main .bar").count() >= 5 and not bad_text(page))
    page.click("#main .chip >> text=Round trips"); page.wait_for_timeout(150)
    check("round-trip route view renders", page.locator("#main .rt").count() >= 5 and not bad_text(page))
    page.evaluate("const r=document.querySelector('#fr'); r.value=5000; r.dispatchEvent(new Event('input',{bubbles:true})); r.dispatchEvent(new Event('change',{bubbles:true}))"); page.wait_for_timeout(250)
    check("flow slider at its maximum still renders sensibly", not bad_text(page) and page.locator("#main svg circle").count() >= 1)
    page.evaluate("state.flowMin = 999999; render()"); page.wait_for_timeout(250)
    check("flow tab explains an empty watch list", "No stations match" in page.inner_text("#main") and not bad_text(page))
    page.evaluate("state.flowMin = 500; render()")
    select_filter(page, "all")

    # 9. dark theme
    select_tab(page, "rides")
    light_bg = page.evaluate("getComputedStyle(document.body).backgroundColor")
    page.emulate_media(color_scheme="dark"); page.wait_for_timeout(300)
    dark_bg = page.evaluate("getComputedStyle(document.body).backgroundColor")
    check("dark colour scheme changes the page background", light_bg != dark_bg, (light_bg, dark_bg))
    check("dark scheme still renders every chart without errors", page.locator("#main svg").count() >= 4 and not bad_text(page))
    for scheme in ("light", "dark"):
        page.emulate_media(color_scheme=scheme); page.wait_for_timeout(250)
        weak = []
        for sel, v in text_contrast(page):
            if v is None:
                continue
            ratio = contrast(tuple(v[:3]), tuple(v[3:]))
            if ratio < 4.5:
                weak.append("%s %.2f" % (sel, ratio))
        check("text contrast is at least 4.5:1 in the %s scheme (WCAG AA)" % scheme, not weak, weak)
    page.emulate_media(color_scheme="light")

    check("no JavaScript or console errors during the session", not errors, errors[:3])
    ctx.close()

    # 10. responsive layouts (fresh page per viewport)
    for name, (w, h) in VIEWPORTS.items():
        c = browser.new_context(viewport={"width": w, "height": h}, has_touch=(name == "mobile"), is_mobile=(name == "mobile"))
        pg = c.new_page(); errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(PAGE); pg.wait_for_selector(".kpi .v")
        for tab in TABS:
            select_tab(pg, tab)
            off = overflow_offenders(pg)
            check("%s %dx%d: tab '%s' has no sideways overflow" % (name, w, h, tab), not off, off)
        check("%s: no JavaScript errors" % name, not errs, errs[:2])
        c.close()
    browser.close()

print("\n%d passed, %d failed" % (len(passed), len(failed)))
sys.exit(1 if failed else 0)
