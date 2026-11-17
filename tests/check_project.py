"""Lightweight local checks. They do NOT run T-SQL; they only catch obvious mistakes
(missing file, diagram/SQL column mismatch, wrong CREATE statement, mixed run folders).
Run from the project root:  python3 -I tests/check_project.py"""
import os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "diagram"))
from schema_spec import TABLES, RELATIONSHIPS  # noqa: E402

FILES = {
    "fact_trip": "sql/warehouse/04_fact_trip.sql", "fact_payment": "sql/warehouse/05_fact_payment.sql",
    "dim_rider": "sql/warehouse/02_dim_rider.sql", "dim_station": "sql/warehouse/03_dim_station.sql",
    "dim_date": "sql/warehouse/01_dim_date.sql",
}
STAGING = ["sql/staging/staging_%s.sql" % n for n in ("payment", "rider", "trip", "station")]
errors = []

def read(rel):
    path = os.path.join(ROOT, rel)
    if not os.path.exists(path):
        errors.append("missing file: " + rel); return ""
    if rel.endswith(".pdf"):
        return ""
    return open(path, errors="ignore").read()

def code_only(sql):  # drop -- comments so words in comments do not count
    return "\n".join(l.split("--")[0] for l in sql.splitlines())

for rel in ["sql/00_external_objects.sql", "sql/postgres/validate_source.sql", "sql/warehouse/06_validation.sql",
            "sql/warehouse/07_business_queries.sql",             "diagram/star_schema.pdf", "docs/SUBMISSION_README.md", "docs/RUBRIC_CHECKLIST.md", "dashboard/index.html", "sql/postgres/create_tables.sql"]:
    read(rel)

runs = set()
for table, rel in FILES.items():
    code = code_only(read(rel))
    if not re.search(r"CREATE\s+EXTERNAL\s+TABLE\s+dbo\.%s\b" % table, code, re.I):
        errors.append("%s: no CREATE EXTERNAL TABLE dbo.%s" % (rel, table))
    if not re.search(r"\bAS\s*\n?\s*(WITH|SELECT)\b", code, re.I):
        errors.append("%s: no AS SELECT (not a CETAS)" % rel)
    for _, col, _t in TABLES[table]:
        if not re.search(r"\b%s\b" % re.escape(col), code):
            errors.append("%s: column %s from the diagram spec is not in the SQL" % (rel, col))
    runs.update(re.findall(r"run\d+", code))
if len(runs) != 1:
    errors.append("CETAS LOCATIONs use different run folders: %s" % sorted(runs))

for rel in STAGING:
    code = code_only(read(rel))
    if not re.search(r"CREATE\s+EXTERNAL\s+TABLE", code, re.I):
        errors.append(rel + ": not CREATE EXTERNAL TABLE")

for rel in STAGING + list(FILES.values()):
    if re.search(r"CREATE\s+TABLE\b|\bCTAS\b|SELECT\s+INTO", code_only(read(rel)), re.I):
        errors.append(rel + ": contains a regular CREATE TABLE / SELECT INTO (not supported in serverless)")

for fact, fcol, dim, dcol, _ in RELATIONSHIPS:
    cols = {c for _, c, _t in TABLES[fact]}; dcols = {c for k, c, _t in TABLES[dim] if k == "PK"}
    if fcol not in cols or dcol not in dcols:
        errors.append("relationship %s.%s -> %s.%s does not match the spec" % (fact, fcol, dim, dcol))

# secrets
for dirpath, _, names in os.walk(ROOT):
    for n in names:
        if n.endswith((".py", ".sql", ".md")):
            txt = open(os.path.join(dirpath, n), errors="ignore").read()
            if re.search(r"password\s*=\s*[\"'][^<\"']+[\"']", txt, re.I):
                errors.append("possible hardcoded password in " + os.path.join(dirpath, n))

if errors:
    print("FAILED"); [print(" -", e) for e in errors]; sys.exit(1)
print("OK: files exist, 5 CETAS scripts match the diagram spec, 4 staging scripts use CREATE EXTERNAL TABLE, one run folder (%s)." % ", ".join(runs))
