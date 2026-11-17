"""Draws the star schema to star_schema.pdf (vector). Run: python3 make_star_schema_pdf.py"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyBboxPatch
from schema_spec import TABLES, RELATIONSHIPS, GRAIN

HERE = os.path.dirname(os.path.abspath(__file__))
ROW_H, HEAD_H, GRAIN_H = 0.30, 0.42, 0.28
FACT_C, DIM_C = "#c8553d", "#2f6f8f"
W = {"fact_trip": 5.0, "fact_payment": 4.4, "dim_rider": 4.4, "dim_station": 3.8, "dim_date": 4.0}
# x, y of the box's top-left corner (canvas 24 x 12.5 inches, y up)
POS = {
    "dim_station": (0.5, 8.6),
    "fact_trip": (6.4, 10.8),
    "dim_rider": (13.0, 11.6),
    "dim_date": (13.2, 5.6),
    "fact_payment": (19.2, 10.2),
}

fig = plt.figure(figsize=(24, 12.5))
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 24); ax.set_ylim(0, 12.5); ax.axis("off")
ax.text(0.5, 12.05, "Divvy Bike Share - Star Schema (Azure Synapse serverless, CETAS external tables)",
        fontsize=19, fontweight="bold", color="#222")
ax.text(0.5, 11.68, "Two fact tables share dim_rider and dim_date. dim_station plays two roles (start / end). "
        "PK = primary key (natural key from the source), FK = foreign key (not enforced in serverless; validated in 06_validation.sql).",
        fontsize=10.5, color="#444")

anchors = {}  # (table, column) -> (x_left, x_right, y)
def draw(name):
    x, y = POS[name]; w = W[name]; cols = TABLES[name]
    color = FACT_C if name.startswith("fact") else DIM_C
    h = HEAD_H + GRAIN_H + ROW_H * len(cols)
    ax.add_patch(FancyBboxPatch((x, y - h), w, h, boxstyle="round,pad=0,rounding_size=0.08",
                                fc="white", ec=color, lw=2, zorder=2))
    ax.add_patch(Rectangle((x, y - HEAD_H), w, HEAD_H, fc=color, ec=color, zorder=3))
    ax.text(x + w / 2, y - HEAD_H / 2, name, ha="center", va="center", color="white",
            fontsize=13, fontweight="bold", zorder=4)
    ax.text(x + 0.12, y - HEAD_H - GRAIN_H / 2, GRAIN[name], ha="left", va="center",
            fontsize=9, style="italic", color="#555", zorder=4)
    for i, (k, c, t) in enumerate(cols):
        ry = y - HEAD_H - GRAIN_H - ROW_H * (i + 0.5)
        if i % 2 == 0:
            ax.add_patch(Rectangle((x + 0.01, ry - ROW_H / 2), w - 0.02, ROW_H, fc="#f4f4f4", ec="none", zorder=2.5))
        ax.text(x + 0.12, ry, k, ha="left", va="center", fontsize=9, fontweight="bold",
                color=color, zorder=4)
        ax.text(x + 0.55, ry, c, ha="left", va="center", fontsize=10.5,
                fontweight="bold" if k == "PK" else "normal", color="#111", zorder=4)
        ax.text(x + w - 0.12, ry, t, ha="right", va="center", fontsize=9, color="#555", zorder=4)
        anchors[(name, c)] = (x, x + w, ry)

for n in POS:
    draw(n)

def link(rel, rad):
    fact, fcol, dim, dcol, label = rel
    fl, fr, fy = anchors[(fact, fcol)]; dl, dr, dy = anchors[(dim, dcol)]
    # leave the fact on the side that faces the dimension
    if dr <= fl:   p0, p1 = (fl, fy), (dr, dy)
    elif dl >= fr: p0, p1 = (fr, fy), (dl, dy)
    else:          p0, p1 = (fr, fy), (dl, dy)
    ax.annotate("", xy=p1, xytext=p0, zorder=1,
                arrowprops=dict(arrowstyle="-|>", color="#555", lw=1.4,
                                connectionstyle="arc3,rad=%s" % rad))
    ax.text(p0[0] + (0.1 if p0[0] > p1[0] else -0.1) * -1, p0[1] + 0.12, "*", fontsize=11, color="#555")
    ax.text(p1[0] + (0.1 if p1[0] > p0[0] else -0.1) * -1, p1[1] + 0.12, "1", fontsize=11, color="#555")
    if label:
        mx, my = (p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2
        my += 0.17 if label.startswith('start') else (-0.17 if label.startswith('end') else 0)
        ax.text(mx, my, label, fontsize=9.5, color="#222", ha="center",
                bbox=dict(fc="white", ec="#bbb", boxstyle="round,pad=0.2"), zorder=5)

for rel in RELATIONSHIPS:
    link(rel, 0.0)

# legend / notes
notes = [
    "Fact rows are measured events, joined to dimensions by keys. Dimensions hold descriptions only, no measures.",
    "Trip measures: ride_duration_minutes (fractional minutes), rider_age_at_trip (whole years on the ride date).",
    "Payment measure: amount. Age at account start comes from dim_rider.age_at_account_start.",
    "There is NO link between a payment and a trip in the source. Never join the two facts row by row.",
    "dim_rider.is_member is the CURRENT flag only; membership history is not in the source.",
]
for i, t in enumerate(notes):
    ax.text(0.5, 3.2 - i * 0.38, "- " + t, fontsize=10.5, color="#333")
ax.add_patch(Rectangle((0.5, 0.45), 0.35, 0.22, fc=FACT_C)); ax.text(0.95, 0.56, "fact table", va="center", fontsize=10)
ax.add_patch(Rectangle((2.6, 0.45), 0.35, 0.22, fc=DIM_C)); ax.text(3.05, 0.56, "dimension table", va="center", fontsize=10)
ax.text(5.4, 0.56, "Arrow: FK in fact  ->  PK in dimension   (* = many, 1 = one)", va="center", fontsize=10)

fig.savefig(os.path.join(HERE, "star_schema.pdf"))
fig.savefig(os.path.join(HERE, "star_schema.png"), dpi=70)
print("wrote star_schema.pdf and star_schema.png")
