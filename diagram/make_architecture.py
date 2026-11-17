"""Builds the end-to-end architecture diagram from one specification.

    python diagram/make_architecture.py

Writes (paths relative to the repository root):
    docs/architecture.drawio          editable in diagrams.net (draw.io)
    docs/images/architecture.svg      what the README embeds
    docs/images/architecture.png      optional raster copy (needs Playwright and a Chromium-based browser)

Table names come from diagram/schema_spec.py and the row counts from dashboard/data.json, so the
picture follows the project files. tests/check_project.py checks the names against the SQL.
"""
import html
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
from schema_spec import TABLES  # noqa: E402

meta = json.loads((ROOT / "dashboard" / "data.json").read_text())["meta"]
data_kb = round((ROOT / "dashboard" / "data.json").stat().st_size / 1024)
dims = [t for t in TABLES if t.startswith("dim_")]
facts = [t for t in TABLES if t.startswith("fact_")]
n = lambda v: "{:,}".format(v)

# ---- palette ---------------------------------------------------------------------------------
INK, MUTED = "#0D1B2B", "#566779"
LANE1, LANE1_LINE = "#F1F7FC", "#C9DCEC"
LANE2, LANE2_LINE = "#FBF5EA", "#E7D5B3"
STYLES = {  # fill, stroke, title colour, text colour
    "source": ("#FFFFFF", "#566779", INK, INK),
    "azure": ("#FFFFFF", "#1783BC", "#0F3A5F", INK),
    "warehouse": ("#0F3A5F", "#0F3A5F", "#FFFFFF", "#E6F2FA"),
    "python": ("#FFFFFF", "#B7791F", "#7A4F0E", INK),
    "web": ("#FFFFFF", "#1B8A5A", "#115C3B", INK),
}

# ---- nodes: id, lane, column x, width, style, title lines, body lines ----------------------------
W, GAP, X0 = 200, 70, 30
col = lambda i: X0 + i * (W + GAP)
NODES = [
    # lane 1: Azure warehouse
    dict(id="n1", lane=1, x=col(0), w=W, st="source", title=["Source CSV files"],
         body=["riders.csv  (%s)" % n(meta["riders"]), "trips.csv  (%s)" % n(meta["trips_total"]), "payments.csv  (%s)" % n(meta["payments"]),
               "stations.csv  (%s)" % n(meta["stations"]), "", "Real Divvy trips plus", "synthetic rider, account", "and payment data"]),
    dict(id="n2", lane=1, x=col(1), w=W, st="azure", title=["Azure Database", "for PostgreSQL"],
         body=["OLTP source system", "", "tables: rider, trip,", "payment, station", "", "loaded with a Python", "script (COPY)"]),
    dict(id="n3", lane=1, x=col(2), w=W, st="azure", title=["Azure Synapse", "Ingest"],
         body=["copy data tool", "one-time pipeline run", "", "4 copy activities", "PostgreSQL to data lake"]),
    dict(id="n4", lane=1, x=col(3), w=W, st="azure", title=["Azure Data Lake", "Storage Gen2"],
         body=["raw: 4 delimited text files", "public.rider.txt", "public.trip.txt", "public.payment.txt", "public.station.txt", "", "warehouse/: Parquet output", "written by the CETAS step"]),
    dict(id="n5", lane=1, x=col(4), w=W, st="azure", title=["Synapse serverless", "SQL pool (built-in)"],
         body=["database: divvy_dw", "", "4 external staging tables:", "staging_rider", "staging_trip", "staging_payment", "staging_station"]),
    dict(id="n6", lane=1, x=col(5), w=330, st="warehouse", title=["5 CETAS transformations"],
         body=["CREATE EXTERNAL TABLE ... AS SELECT", "", "Dimensions", "   " + "  ·  ".join(dims), "Facts", "   " + "  ·  ".join(facts), "",
               "Parquet files in warehouse/<table>/run01/", "a new run folder for every re-run"]),
    # lane 2: dashboard
    dict(id="m1", lane=2, x=col(0), w=W, st="source", title=["Source CSV files"],
         body=["the same four files,", "read locally", "", "not stored in the", "repository"]),
    dict(id="m2", lane=2, x=col(1), w=W, st="python", title=["Python aggregation"],
         body=["dashboard/build_data.py", "pandas + NumPy", "", "same business rules as", "the warehouse SQL"]),
    dict(id="m3", lane=2, x=col(2), w=W, st="python", title=["data.json"],
         body=["aggregates only", "about %d KB" % data_kb, "no rider-level rows", "split by rider type"]),
    dict(id="m4", lane=2, x=col(3), w=W, st="python", title=["Static page build"],
         body=["make_dashboard.py +", "template.html", "makes dashboard/index.html", "data embedded"]),
    dict(id="m5", lane=2, x=col(4), w=W, st="web", title=["GitHub Pages"],
         body=["static hosting from", "the main branch", "", "no database,", "no backend"]),
    dict(id="m6", lane=2, x=col(5), w=330, st="web", title=["Divvy Ride Atlas"],
         body=["runs in the visitor's browser:", "rider-type filter, 7 tabs,", "heatmap, station map, routes,", "rebalancing, payments, accounts"]),
]
ANALYTICS = dict(id="n7", lane=1, st="azure", title=["T-SQL analytics and validation (serverless SQL)"],
                 body=["07_business_queries.sql: ride duration, stations, routes, spend, usage vs spend",
                       "06_validation_summary.sql: 26 checks, all passing in the Synapse run"])

# ---- geometry ------------------------------------------------------------------------------------
TITLE_LH, BODY_LH = 19, 17
def node_h(nd): return 20 + TITLE_LH * len(nd["title"]) + 12 + BODY_LH * len(nd["body"]) + 14
row_h = {1: max(node_h(x) for x in NODES if x["lane"] == 1), 2: max(node_h(x) for x in NODES if x["lane"] == 2)}
LANE1_Y, LANE2_TOP_GAP = 60, 40
ROW1_Y = LANE1_Y + 56
for nd in NODES:
    nd["h"] = row_h[nd["lane"]]
ANALYTICS.update(x=col(4), w=W * 1 + GAP + 330, y=ROW1_Y + row_h[1] + 46, h=20 + TITLE_LH + 12 + BODY_LH * 2 + 14)
LANE1_H = (ANALYTICS["y"] + ANALYTICS["h"] + 24) - LANE1_Y
LANE2_Y = LANE1_Y + LANE1_H + LANE2_TOP_GAP
ROW2_Y = LANE2_Y + 80
for nd in NODES:
    nd["y"] = ROW1_Y if nd["lane"] == 1 else ROW2_Y
LANE2_H = ROW2_Y + row_h[2] + 24 - LANE2_Y
CANVAS_W = col(5) + 330 + 30
LEGEND_Y = LANE2_Y + LANE2_H + 24
CANVAS_H = LEGEND_Y + 44
byid = {x["id"]: x for x in NODES}; byid["n7"] = ANALYTICS

# text must fit its box (rough Helvetica estimate)
for nd in NODES + [ANALYTICS]:
    for t in nd["title"]:
        assert len(t) * 8.8 <= nd["w"] - 24, ("title too wide", t)
    for t in nd["body"]:
        assert len(t) * 6.4 <= nd["w"] - 24, ("line too wide", t, len(t) * 6.4, nd["w"])

EDGES = [  # source, target, side, dashed, badge
    ("n1", "n2", "h", False, "1"), ("n2", "n3", "h", False, "2"), ("n3", "n4", "h", False, "3"),
    ("n4", "n5", "h", False, "4"), ("n5", "n6", "h", False, "5"), ("n6", "n7", "v", False, "6"),
    ("n1", "m1", "v", True, ""), ("m1", "m2", "h", False, "A"), ("m2", "m3", "h", False, "B"),
    ("m3", "m4", "h", False, "C"), ("m4", "m5", "h", False, "D"), ("m5", "m6", "h", False, "E"),
]
def anchors(e):
    a, b, side = byid[e[0]], byid[e[1]], e[2]
    if side == "h":
        return (a["x"] + a["w"], a["y"] + a["h"] / 2), (b["x"], b["y"] + b["h"] / 2)
    # vertical: bottom centre of a to top centre of b
    if e[0] == "n6":  # n7 is narrower than n6; drop from the x where they overlap
        x = ANALYTICS["x"] + ANALYTICS["w"] - 165
        return (x, a["y"] + a["h"]), (x, b["y"])
    x = a["x"] + a["w"] / 2
    return (x, a["y"] + a["h"]), (x, b["y"])

LANES = [
    dict(id="lane1", x=12, y=LANE1_Y, w=CANVAS_W - 24, h=LANE1_H, fill=LANE1, stroke=LANE1_LINE,
         title="Azure data warehouse: built and validated in Azure Synapse",
         sub="Temporary Udacity cloud-lab resources, since deleted. Evidence is in evidence/."),
    dict(id="lane2", x=12, y=LANE2_Y, w=CANVAS_W - 24, h=LANE2_H, fill=LANE2, stroke=LANE2_LINE, tx=col(1),  # heading starts right of the dashed arrow
         title="Interactive dashboard: a separate presentation branch with no live Azure connection",
         sub="Uses the same business rules as the SQL; headline figures were cross-checked against Synapse results."),
]
LEGEND = [("source", "Source files"), ("azure", "Azure service"), ("warehouse", "Warehouse tables"), ("python", "Python / local build"), ("web", "Static hosting")]

# ---- SVG -----------------------------------------------------------------------------------------
esc = html.escape
def svg_text(x, y, s, size=12, weight="400", fill=INK, anchor="start", extra=""):
    return '<text x="%s" y="%s" font-size="%s" font-weight="%s" fill="%s" text-anchor="%s"%s>%s</text>' % (x, y, size, weight, fill, anchor, extra, esc(s))

out = ['<?xml version="1.0" encoding="UTF-8"?>',
       '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d" font-family="Helvetica, Arial, sans-serif" role="img" aria-labelledby="t d">' % (CANVAS_W, CANVAS_H, CANVAS_W, CANVAS_H),
       '<title id="t">Divvy Azure data warehouse: solution architecture</title>',
       '<desc id="d">Four CSV files are loaded into Azure PostgreSQL, copied by Synapse Ingest to Azure Data Lake Storage, exposed as four external staging tables in the serverless SQL pool and transformed by five CETAS statements into three dimensions and two fact tables stored as Parquet, then queried and validated with T-SQL. A separate branch aggregates the same CSV files with Python into a static dashboard hosted on GitHub Pages and has no live Azure connection.</desc>',
       '<defs><marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="%s"/></marker></defs>' % MUTED,
       '<rect width="%d" height="%d" fill="#FFFFFF"/>' % (CANVAS_W, CANVAS_H),
       svg_text(30, 36, "Divvy Bike Share: solution architecture", 22, "700", INK)]
for ln in LANES:
    out.append('<rect x="%d" y="%d" width="%d" height="%d" rx="10" fill="%s" stroke="%s"/>' % (ln["x"], ln["y"], ln["w"], ln["h"], ln["fill"], ln["stroke"]))
    tx = ln.get("tx", ln["x"] + 18)
    out.append(svg_text(tx, ln["y"] + 28, ln["title"], 15, "700", INK))
    out.append(svg_text(tx, ln["y"] + 48, ln["sub"], 12, "400", MUTED))
for e in EDGES:
    (x1, y1), (x2, y2) = anchors(e)
    dash = ' stroke-dasharray="6 5"' if e[3] else ""
    out.append('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="2"%s marker-end="url(#arr)"/>' % (x1, y1, x2 - (0 if e[2] == "v" else 1), y2 - (1 if e[2] == "v" else 0), MUTED, dash))
    if e[4]:
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        out.append('<circle cx="%s" cy="%s" r="11" fill="#FFFFFF" stroke="%s" stroke-width="1.5"/>' % (mx, my, MUTED))
        out.append(svg_text(mx, my + 4, e[4], 11, "700", INK, "middle"))
    elif e[3]:
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        out.append('<rect x="%s" y="%s" width="104" height="22" rx="4" fill="#FFFFFF"/>' % (mx - 52, my - 11))
        out.append(svg_text(mx, my + 4, "same files", 11, "400", MUTED, "middle"))
for nd in NODES + [ANALYTICS]:
    fill, stroke, tcol, bcol = STYLES[nd["st"]]
    out.append('<rect x="%s" y="%s" width="%s" height="%s" rx="8" fill="%s" stroke="%s" stroke-width="2"/>' % (nd["x"], nd["y"], nd["w"], nd["h"], fill, stroke))
    y = nd["y"] + 26
    for t in nd["title"]:
        out.append(svg_text(nd["x"] + 14, y, t, 15, "700", tcol)); y += TITLE_LH
    y += 4
    for t in nd["body"]:
        if t:
            out.append(svg_text(nd["x"] + 14, y + 4, t, 12, "400", bcol, extra=' xml:space="preserve"'))
        y += BODY_LH
lx = 30
for k, label in LEGEND:
    fill, stroke, _, _ = STYLES[k]
    out.append('<rect x="%d" y="%d" width="22" height="14" rx="3" fill="%s" stroke="%s" stroke-width="2"/>' % (lx, LEGEND_Y, fill, stroke))
    out.append(svg_text(lx + 30, LEGEND_Y + 12, label, 12, "400", MUTED)); lx += 40 + len(label) * 7 + 22
out.append(svg_text(lx + 10, LEGEND_Y + 12, "Numbers 1-6: warehouse steps in order.  Letters A-E: dashboard steps in order.", 12, "400", MUTED))
out.append("</svg>")
svg_path = ROOT / "docs" / "images" / "architecture.svg"
svg_path.parent.mkdir(parents=True, exist_ok=True)
svg_path.write_text("\n".join(out) + "\n", encoding="utf-8")

# ---- draw.io -------------------------------------------------------------------------------------
cells, cid = [], [1]
def cell(**kw):
    cid[0] += 1
    return cid[0]
def vtx(idn, value, x, y, w, h, style):
    return '<mxCell id="%s" value="%s" style="%s" vertex="1" parent="1"><mxGeometry x="%s" y="%s" width="%s" height="%s" as="geometry"/></mxCell>' % (idn, esc(value, quote=True), style, x, y, w, h)
cells.append(vtx("title", "<b style='font-size:22px'>Divvy Bike Share: solution architecture</b>", 30, 8, 700, 40, "text;html=1;align=left;verticalAlign=middle;strokeColor=none;fillColor=none;"))
for ln in LANES:
    value = "<b style='font-size:15px'>%s</b><br><span style='color:%s'>%s</span>" % (esc(ln["title"]), MUTED, esc(ln["sub"]))
    cells.append(vtx(ln["id"], value, ln["x"], ln["y"], ln["w"], ln["h"],
                     "rounded=1;arcSize=3;html=1;whiteSpace=wrap;align=left;verticalAlign=top;spacingLeft=%d;spacingTop=8;fontSize=12;fillColor=%s;strokeColor=%s;" % (ln.get("tx", ln["x"] + 18) - ln["x"] - 4, ln["fill"], ln["stroke"])))
for nd in NODES + [ANALYTICS]:
    fill, stroke, tcol, bcol = STYLES[nd["st"]]
    body = "<br>".join(esc(t).replace("   ", "&nbsp;&nbsp;&nbsp;") if t else "&nbsp;" for t in nd["body"])
    value = "<b style='font-size:15px;color:%s'>%s</b><br><div style='line-height:6px'>&nbsp;</div>%s" % (tcol, "<br>".join(esc(t) for t in nd["title"]), body)
    cells.append(vtx(nd["id"], value, nd["x"], nd["y"], nd["w"], nd["h"],
                     "rounded=1;arcSize=6;html=1;whiteSpace=wrap;align=left;verticalAlign=top;spacingLeft=10;spacingTop=6;spacingRight=6;fontSize=12;fontColor=%s;fillColor=%s;strokeColor=%s;strokeWidth=2;" % (bcol, fill, stroke)))
for i, e in enumerate(EDGES):
    style = "endArrow=block;endFill=1;html=1;strokeWidth=2;strokeColor=%s;labelBackgroundColor=#FFFFFF;fontSize=11;fontStyle=1;%s" % (MUTED, "dashed=1;" if e[3] else "")
    if e[0] == "n6":
        (x1, y1), (x2, y2) = anchors(e)
        exit_x = (x1 - byid["n6"]["x"]) / byid["n6"]["w"]
        entry_x = (x2 - ANALYTICS["x"]) / ANALYTICS["w"]
        style += "exitX=%.4f;exitY=1;entryX=%.4f;entryY=0;" % (exit_x, entry_x)
    label = e[4] if e[4] else ("same files" if e[3] else "")
    cells.append('<mxCell id="e%d" value="%s" style="%s" edge="1" parent="1" source="%s" target="%s"><mxGeometry relative="1" as="geometry"/></mxCell>' % (i + 1, esc(label), style, e[0], e[1]))
lx = 30
for j, (k, label) in enumerate(LEGEND):
    fill, stroke, _, _ = STYLES[k]
    cells.append(vtx("lg%d" % j, "", lx, LEGEND_Y, 22, 14, "rounded=1;html=1;fillColor=%s;strokeColor=%s;strokeWidth=2;" % (fill, stroke)))
    cells.append(vtx("lt%d" % j, esc(label), lx + 28, LEGEND_Y - 4, len(label) * 7 + 10, 22, "text;html=1;align=left;verticalAlign=middle;fontSize=12;fontColor=%s;strokeColor=none;fillColor=none;" % MUTED))
    lx += 40 + len(label) * 7 + 22
cells.append(vtx("lnote", "Numbers 1-6: warehouse steps in order.  Letters A-E: dashboard steps in order.", lx + 10, LEGEND_Y - 4, 560, 22, "text;html=1;align=left;verticalAlign=middle;fontSize=12;fontColor=%s;strokeColor=none;fillColor=none;" % MUTED))
drawio = ('<mxfile host="app.diagrams.net"><diagram id="architecture" name="Architecture"><mxGraphModel dx="1400" dy="900" grid="0" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="%d" pageHeight="%d" math="0" shadow="0">'
          '<root><mxCell id="0"/><mxCell id="1" parent="0"/>%s</root></mxGraphModel></diagram></mxfile>\n') % (CANVAS_W, CANVAS_H, "".join(cells))
(ROOT / "docs" / "architecture.drawio").write_text(drawio, encoding="utf-8")
print("wrote", svg_path.relative_to(ROOT), "and docs/architecture.drawio  (%d x %d)" % (CANVAS_W, CANVAS_H))

# ---- optional PNG ---------------------------------------------------------------------------------
try:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = None
        for kw in ([{"executable_path": os.environ["DIVVY_BROWSER"]}] if os.environ.get("DIVVY_BROWSER") else []) + [{}, {"channel": "chrome"}, {"channel": "msedge"}]:
            try:
                browser = p.chromium.launch(**kw); break
            except Exception:
                continue
        if browser is None:
            print("png skipped: no browser found")
        else:
            page = browser.new_context(viewport={"width": CANVAS_W, "height": CANVAS_H}, device_scale_factor=1.5).new_page()
            page.goto(svg_path.as_uri())
            png = ROOT / "docs" / "images" / "architecture.png"
            page.screenshot(path=str(png), clip={"x": 0, "y": 0, "width": CANVAS_W, "height": CANVAS_H})
            browser.close()
            try:
                from PIL import Image
                Image.open(png).convert("RGB").quantize(colors=256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE).save(png, optimize=True)
            except ImportError:
                pass
            print("wrote", png.relative_to(ROOT), round(png.stat().st_size / 1024), "KB")
except ImportError:
    print("png skipped: playwright is not installed")
