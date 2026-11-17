#!/usr/bin/env bash
# Builds the submission ZIP from this folder. Run from the project root: bash package.sh
# Output name has _INCOMPLETE until real screenshots exist in evidence/.
set -euo pipefail
cd "$(dirname "$0")"
python3 -I tests/check_project.py
python3 diagram/make_star_schema_pdf.py >/dev/null
STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT
cp diagram/star_schema.pdf "$STAGE/star_schema.pdf"
n=1; for t in payment rider trip station; do cp "sql/staging/staging_$t.sql" "$STAGE/Load$n.txt"; n=$((n+1)); done
for f in dim_date:01 dim_rider:02 dim_station:03 fact_trip:04 fact_payment:05; do cp "sql/warehouse/${f#*:}_${f%%:*}.sql" "$STAGE/${f%%:*}.sql"; done
mkdir -p "$STAGE/sql/warehouse" "$STAGE/sql/staging" "$STAGE/sql/postgres" "$STAGE/starter" "$STAGE/evidence"
cp sql/00_external_objects.sql "$STAGE/sql/"; cp sql/staging/*.sql "$STAGE/sql/staging/"
cp sql/warehouse/*.sql "$STAGE/sql/warehouse/"; cp sql/postgres/*.sql "$STAGE/sql/postgres/"
cp starter/ProjectDataToPostgres.py "$STAGE/starter/"
mkdir -p "$STAGE/dashboard" && cp dashboard/index.html "$STAGE/dashboard/index.html"
cp docs/SUBMISSION_README.md "$STAGE/README.md"; cp docs/RUBRIC_CHECKLIST.md "$STAGE/"
SHOTS=$(find evidence -type f \( -name '*.png' -o -name '*.jpg' \) | wc -l | tr -d ' ')
if [ "$SHOTS" -gt 0 ]; then cp evidence/* "$STAGE/evidence/"; fi
if [ "$SHOTS" -ge 5 ]; then OUT=Divvy_Azure_Data_Warehouse_Submission.zip
else OUT=Divvy_Azure_Data_Warehouse_Submission_INCOMPLETE.zip; echo "Only $SHOTS screenshot(s) found: building $OUT"; fi
rm -f "$OUT"; (cd "$STAGE" && zip -qr - .) > "$OUT"
echo "Wrote $OUT"; unzip -l "$OUT" | tail -n +4
