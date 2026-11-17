"""Builds dashboard/index.html from template.html + data.json.

Usage (works from any directory):
    python3 dashboard/make_dashboard.py
    python3 dashboard/make_dashboard.py --data other.json --out other.html

index.html is a single, self-contained static page: the data is embedded, so it needs no server and
no Azure connection. It loads three web fonts from Google Fonts and falls back to system fonts offline.
"""
import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ap = argparse.ArgumentParser(description="Embed data.json into template.html and write index.html")
ap.add_argument("--template", type=Path, default=HERE / "template.html")
ap.add_argument("--data", type=Path, default=HERE / "data.json")
ap.add_argument("--out", type=Path, default=HERE / "index.html")
a = ap.parse_args()

for label, p in (("template", a.template), ("data", a.data)):
    if not p.is_file():
        sys.exit("error: %s file not found: %s" % (label, p))
template = a.template.read_text(encoding="utf-8")
raw = a.data.read_text(encoding="utf-8")
json.loads(raw)  # fail early if data.json is not valid JSON
if template.count("__DATA__") != 1:
    sys.exit("error: template must contain the __DATA__ marker exactly once")
html = template.replace("__DATA__", raw, 1)

# structural sanity checks on the generated document
problems = []
for needle in ("<!doctype html>", '<html lang="en">', "<head>", "</head>", "<body>", "</body>", "</html>", "<title>", 'name="viewport"', 'charset="utf-8"'):
    if needle not in html:
        problems.append("missing " + needle)
if re.search(r"__[A-Z_]+__", html.replace(raw, "")):
    problems.append("unresolved template marker")
if problems:
    sys.exit("error: generated HTML is not valid: " + "; ".join(problems))

a.out.parent.mkdir(parents=True, exist_ok=True)
a.out.write_text(html, encoding="utf-8")
print("wrote", a.out.resolve(), round(len(html.encode("utf-8")) / 1024), "KB")
