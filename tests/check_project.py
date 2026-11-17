"""Local consistency checks. Standard library only; no Azure access and no source CSV files needed.

    python3 tests/check_project.py

These checks do NOT run T-SQL. They catch the mistakes that are easy to make in a SQL-and-docs project:
missing files, SQL that disagrees with the schema spec or the diagrams, a stale generated dashboard,
dashboard totals that do not reconcile, broken Markdown links, and secrets or data files in the repo.
For the browser tests see tests/smoke_dashboard.py.
"""
import json
import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "diagram"))
from schema_spec import TABLES, RELATIONSHIPS  # noqa: E402

passed, failed = [], []


def check(name, ok, detail=""):
    (passed if ok else failed).append(name)
    if not ok:
        print("FAIL  %s%s" % (name, ("  -> " + str(detail)) if detail else ""))


def text(rel):
    p = ROOT / rel
    return p.read_text(encoding="utf-8", errors="ignore") if p.is_file() else ""


def code_only(sql):  # drop -- comments so words in comments do not count
    return "\n".join(line.split("--")[0] for line in sql.splitlines())


# ---- 1. required files ------------------------------------------------------------------------------
REQUIRED = [
    "README.md", "LICENSE", ".gitignore", "requirements.txt", "requirements-dev.txt", "index.html", ".nojekyll",
    "dashboard/index.html", "dashboard/template.html", "dashboard/data.json", "dashboard/build_data.py", "dashboard/make_dashboard.py",
    "diagram/star_schema.pdf", "diagram/star_schema.png", "diagram/schema_spec.py", "diagram/make_star_schema_pdf.py", "diagram/make_architecture.py",
    "docs/architecture.drawio", "docs/images/architecture.svg", "docs/images/dashboard-overview.png", "docs/images/dashboard-stations.png",
    "docs/images/dashboard-routes.png", "docs/images/dashboard-money.png", "docs/implementation-notes.md", "docs/validation.md",
    "docs/reproduction.md", "docs/portfolio-summary.md", "sql/00_external_objects.sql", "sql/postgres/create_tables.sql",
    "sql/postgres/validate_source.sql", "sql/warehouse/06_validation.sql", "sql/warehouse/06_validation_summary.sql",
    "sql/warehouse/07_business_queries.sql", "starter/README.md", "tests/smoke_dashboard.py",
]
for rel in REQUIRED:
    check("file exists: " + rel, (ROOT / rel).is_file())

# ---- 2. SQL against the schema spec ---------------------------------------------------------------------
FILES = {
    "dim_date": "sql/warehouse/01_dim_date.sql", "dim_rider": "sql/warehouse/02_dim_rider.sql", "dim_station": "sql/warehouse/03_dim_station.sql",
    "fact_trip": "sql/warehouse/04_fact_trip.sql", "fact_payment": "sql/warehouse/05_fact_payment.sql",
}
STAGING = {n: "sql/staging/staging_%s.sql" % n for n in ("payment", "rider", "trip", "station")}
runs = set()
for table, rel in FILES.items():
    code = code_only(text(rel))
    check("%s: CREATE EXTERNAL TABLE dbo.%s ... AS SELECT (a CETAS)" % (rel, table),
          bool(re.search(r"CREATE\s+EXTERNAL\s+TABLE\s+dbo\.%s\b" % table, code, re.I)) and bool(re.search(r"\bAS\s*\n?\s*(WITH|SELECT)\b", code, re.I)))
    missing = [c for _, c, _t in TABLES[table] if not re.search(r"\b%s\b" % re.escape(c), code)]
    check("%s: every column of the diagram spec is in the SQL" % rel, not missing, missing)
    loc = re.search(r"LOCATION\s*=\s*'([^']+)'", code)
    check("%s: output folder is warehouse/%s/runNN/" % (rel, table), bool(loc) and re.fullmatch(r"warehouse/%s/run\d+/" % table, loc.group(1)) is not None, loc and loc.group(1))
    runs.update(re.findall(r"run\d+", code))
    check("%s: no regular CREATE TABLE, CTAS or SELECT INTO (not supported in serverless)" % rel, not re.search(r"CREATE\s+TABLE\b|\bCTAS\b|SELECT\s+INTO", code, re.I))
check("all five CETAS scripts write to the same run folder (%s)" % ", ".join(sorted(runs)), len(runs) == 1, sorted(runs))
for name, rel in STAGING.items():
    code = code_only(text(rel))
    check("%s: CREATE EXTERNAL TABLE dbo.staging_%s reading public.%s.txt" % (rel, name, name),
          bool(re.search(r"CREATE\s+EXTERNAL\s+TABLE\s+dbo\.staging_%s\b" % name, code, re.I)) and ("'public.%s.txt'" % name) in code and "[divvy_storage]" in code)
setup = text("sql/00_external_objects.sql")
check("00_external_objects.sql defines the data source and both file formats", all(x in setup for x in ("[divvy_storage]", "[divvy_csv_format]", "[divvy_parquet_format]")))
check("00_external_objects.sql uses placeholders, not a real storage account", "<container>@<storage_account>" in setup and "divvystorage" not in setup)
for fact, fcol, dim, dcol, _ in RELATIONSHIPS:
    cols = {c for _, c, _t in TABLES[fact]}
    pks = {c for k, c, _t in TABLES[dim] if k == "PK"}
    check("relationship %s.%s -> %s.%s exists in the spec" % (fact, fcol, dim, dcol), fcol in cols and dcol in pks)
check("two fact tables, three dimensions", len([t for t in TABLES if t.startswith("fact_")]) == 2 and len([t for t in TABLES if t.startswith("dim_")]) == 3)

# ---- 3. diagrams against the SQL ---------------------------------------------------------------------------
sql_all = "\n".join(text(r) for r in list(FILES.values()) + list(STAGING.values()))
svg = text("docs/images/architecture.svg")
for tag, path in (("architecture.svg", "docs/images/architecture.svg"), ("architecture.drawio", "docs/architecture.drawio")):
    try:
        root = ET.fromstring((ROOT / path).read_bytes())
        check("%s is well-formed XML" % tag, True)
    except Exception as exc:
        check("%s is well-formed XML" % tag, False, exc)
try:
    cells = ET.fromstring((ROOT / "docs/architecture.drawio").read_bytes()).findall(".//mxCell")
    vids = {c.get("id") for c in cells if c.get("vertex")}
    edges = [c for c in cells if c.get("edge")]
    check("architecture.drawio: every connector joins two existing shapes", bool(edges) and all(e.get("source") in vids and e.get("target") in vids for e in edges))
except Exception as exc:
    check("architecture.drawio: every connector joins two existing shapes", False, exc)
names_in_svg = set(re.findall(r"\b(?:dim|fact|staging)_[a-z]+\b", svg))
check("architecture.svg names every star-schema table", all(t in svg for t in TABLES))
check("architecture.svg names every staging table", all(("staging_" + n) in svg for n in STAGING))
check("every table named in architecture.svg exists in the SQL", all(re.search(r"\b%s\b" % n, sql_all) for n in names_in_svg), sorted(names_in_svg))
check("architecture.svg shows the dashboard as a separate branch without a live Azure link", "no live Azure connection" in svg)

# ---- 4. dashboard data ---------------------------------------------------------------------------------------
data = json.loads(text("dashboard/data.json") or "{}")
meta, F = data.get("meta", {}), data.get("f", {})
check("data.json has the three rider-type filters", set(F) == {"all", "member", "casual"})
DOC = dict(trips_total=4584921, payments=1946607, riders=75000, stations=838)
check("data.json totals match the documented figures", all(meta.get(k) == v for k, v in DOC.items()), {k: meta.get(k) for k in DOC})
iss = meta.get("issues", {})
check("duration issues are 4,583,447 valid / 116 negative / 81 zero / 1,277 over 24 h", iss == {"ok": 4583447, "negative": 116, "zero": 81, "over_24h": 1277}, iss)
check("valid + invalid durations add up to all trips", sum(iss.values()) == meta.get("trips_total"))
if F:
    a, m, c = F["all"], F["member"], F["casual"]
    check("dashboard rides for 'all' equal the valid-duration trips", a["rides"] == iss.get("ok"))
    check("total payment amount is $19,457,105.25", round(a["spend_total"], 2) == 19457105.25, a["spend_total"])
    check("members + casual = all riders (rides, payments, riders, spend)", m["rides"] + c["rides"] == a["rides"] and m["payments"] + c["payments"] == a["payments"]
          and m["riders"] + c["riders"] == a["riders"] and round(m["spend_total"] + c["spend_total"], 2) == round(a["spend_total"], 2))
    check("payments by year add up to total payments", all(sum(v[0] for v in f["spend_year"].values()) == f["payments"] for f in F.values()))
    check("age-band rides add up to valid rides", all(sum(x[0] for x in f["ages"]) == f["rides"] for f in F.values()))
    check("heatmap rides add up to valid rides", all(sum(cell[0] for row in f["heat"] for cell in row) == f["rides"] for f in F.values()))
    check("duration histogram adds up to valid rides", all(sum(f["dur_hist"]["counts"]) == f["rides"] for f in F.values()))
    check("monthly rides add up to valid rides", all(sum(v[0] for v in f["month"].values()) == f["rides"] for f in F.values()))
    check("accounts: members + casual = all riders opened", sum(m["opened"].values()) + sum(c["opened"].values()) == sum(a["opened"].values()) == a["riders"])
    val = text("sql/warehouse/06_validation_summary.sql")
    check("06_validation_summary.sql expects the same counts as data.json", all(str(meta[k]) in val for k in ("trips_total", "payments", "riders", "stations")) and "4583447" in val)

# ---- 5. dashboard generation -----------------------------------------------------------------------------------
html = text("dashboard/index.html")
check("index.html is a complete HTML5 document", all(x in html for x in ("<!doctype html>", '<html lang="en">', "</head>", "<body>", "</body>", "</html>", 'name="viewport"', 'charset="utf-8"', "<title>Divvy Ride Atlas</title>")))
check("index.html has no unresolved template marker", "__DATA__" not in html)
check("index.html has no tool-specific metadata", "claude" not in html.lower())
ext = set(re.findall(r'(?:src|href)="(https?://[^"]+)"', html))
check("index.html loads only Google Fonts from outside (no scripts, APIs or trackers)", all(u.startswith(("https://fonts.googleapis.com", "https://fonts.gstatic.com")) for u in ext), sorted(ext))
with tempfile.TemporaryDirectory() as tmp:
    out = Path(tmp) / "index.html"
    r = subprocess.run([sys.executable, str(ROOT / "dashboard" / "make_dashboard.py"), "--out", str(out)], cwd=tmp, capture_output=True, text=True)
    check("make_dashboard.py runs from an unrelated directory", r.returncode == 0, r.stderr.strip()[:200])
    check("committed index.html is up to date with template.html + data.json", out.is_file() and out.read_text(encoding="utf-8") == html)
r = subprocess.run([sys.executable, str(ROOT / "dashboard" / "build_data.py"), str(ROOT / "no-such-folder")], capture_output=True, text=True)
check("build_data.py reports missing source CSVs clearly", r.returncode != 0 and "riders.csv" in (r.stderr + r.stdout))

# ---- 6. Markdown links and images -------------------------------------------------------------------------------
md_files = [ROOT / "README.md"] + sorted((ROOT / "docs").glob("*.md")) + [ROOT / "starter" / "README.md"] + sorted((ROOT / "evidence").glob("*.md"))
broken = []
for md in md_files:
    if not md.is_file():
        continue
    body = md.read_text(encoding="utf-8", errors="ignore")
    targets = re.findall(r"!?\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)", body) + re.findall(r'<img[^>]+src="([^"]+)"', body)
    for t in targets:
        if t.startswith(("http://", "https://", "mailto:", "#")):
            continue
        if not (md.parent / t.split("#")[0]).exists():
            broken.append("%s -> %s" % (md.relative_to(ROOT), t))
check("Markdown links and images point to files that exist", not broken, broken[:6])

# ---- 7. secrets, personal data and files that must not be committed ---------------------------------------------------
def repo_files():
    """Files Git tracks (or would track): `git ls-files` in a clone, otherwise a walk that skips ignored folders."""
    try:
        r = subprocess.run(["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"], cwd=ROOT, capture_output=True, text=True, check=True)
        return [ROOT / f for f in r.stdout.split("\0") if f]
    except Exception:
        return [p for p in ROOT.rglob("*") if p.is_file() and not any(part in (".git", "data", "__pycache__") for part in p.relative_to(ROOT).parts)]


SECRET = re.compile(r"password\s*=\s*[\"'][^<\"'\s]+[\"']|AccountKey=|DefaultEndpointsProtocol|[?&]sig=|BEGIN (RSA |OPENSSH )?PRIVATE KEY|AKIA[0-9A-Z]{16}", re.I)
bad = []
for p in repo_files():
    if not p.is_file():
        continue
    rel = p.relative_to(ROOT)
    if p.suffix in (".csv", ".zip", ".pem") or p.name in (".env", "ProjectDataToPostgres.py"):
        bad.append("file that should not be in the repo: %s" % rel)
    if p.suffix in (".py", ".sql", ".md", ".html", ".json", ".sh", ".txt", ".svg", ".drawio") and str(rel) != "tests/check_project.py":
        if SECRET.search(p.read_text(encoding="utf-8", errors="ignore")):
            bad.append("possible secret in %s" % rel)
check("no secrets, keys, CSV files, archives or the course loader script among the repository files", not bad, bad[:5])
gi = text(".gitignore")
check(".gitignore keeps raw data, archives and the starter script out of Git", all(x in gi for x in ("data/", "*.zip", "starter/ProjectDataToPostgres.py")))

print("%d passed, %d failed" % (len(passed), len(failed)))
sys.exit(1 if failed else 0)
