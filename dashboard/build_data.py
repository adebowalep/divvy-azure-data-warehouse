"""Builds data.json for the dashboard from the four source CSVs (same rules as the warehouse SQL).
Run:  python3 build_data.py <folder with riders/payments/stations/trips CSVs>
Rules mirrored from the SQL: valid ride = 0 < duration <= 24 h; age = completed years; 
member flag = rider's CURRENT is_member."""
import sys, json, numpy as np, pandas as pd
D = sys.argv[1].rstrip("/") + "/"
r = pd.read_csv(D+"riders.csv", header=None, names="rider_id first last address birthday start end is_member".split())
p = pd.read_csv(D+"payments.csv", header=None, names="payment_id date amount rider_id".split())
s = pd.read_csv(D+"stations.csv", header=None, names="station_id name lat lon".split(), dtype={"station_id": str})
t = pd.read_csv(D+"trips.csv", header=None, names="trip_id type start end s_id e_id rider_id".split(), dtype={"s_id": str, "e_id": str})
r["member"] = r.is_member.astype(str).str.lower().eq("true")
r["bd"] = pd.to_datetime(r.birthday); r["as"] = pd.to_datetime(r.start)
def age(b, d): return d.dt.year-b.dt.year-(((d.dt.month<b.dt.month)|((d.dt.month==b.dt.month)&(d.dt.day<b.dt.day))).astype(int))

t["s"] = pd.to_datetime(t.start); t["e"] = pd.to_datetime(t.end)
t["sec"] = (t.e-t.s).dt.total_seconds()
issues = {"ok": int(((t.sec>0)&(t.sec<=86400)).sum()), "negative": int((t.sec<0).sum()), "zero": int((t.sec==0).sum()), "over_24h": int((t.sec>86400).sum())}
v = t[(t.sec>0)&(t.sec<=86400)].copy()
v["min"] = (v.sec/60).round(4)
v = v.merge(r[["rider_id","bd","member"]], on="rider_id", how="left")
v["age"] = age(v.bd, v.s)
v["dow"] = v.s.dt.dayofweek; v["hour"] = v.s.dt.hour; v["ym"] = v.start.str[:7]
AB = [(-1,17,"Under 18"),(18,24,"18-24"),(25,34,"25-34"),(35,44,"35-44"),(45,54,"45-54"),(55,64,"55-64"),(65,999,"65+")]
def band(x):
    for lo,hi,l in AB:
        if lo<=x<=hi: return l
v["band"] = v.age.map(band)
labels = [l for _,_,l in AB]

p["year"] = p.date.str[:4].astype(int); p["ym"] = p.date.str[:7]
p = p.merge(r[["rider_id","member","bd","as"]], on="rider_id", how="left")
rs = p.groupby("rider_id").amount.sum().rename("tot").reset_index().merge(r[["rider_id","member","bd","as"]], on="rider_id")
rs["band"] = age(rs.bd, rs["as"]).map(band)

def r3(x, n=3): return None if pd.isna(x) else round(float(x), n)
out = {"meta": {"labels": labels, "issues": issues, "trips_total": int(len(t)), "riders": int(len(r)), "stations": int(len(s)), "payments": int(len(p)),
                "first_trip": t.start.min()[:10], "last_trip": t.start.max()[:10]}, "f": {}}
for key, vm, pm, rm in [("all", v, p, rs), ("member", v[v.member==True], p[p.member==True], rs[rs.member==True]), ("casual", v[v.member==False], p[p.member==False], rs[rs.member==False])]:
    heat = [[[0,0.0] for _ in range(24)] for _ in range(7)]
    for (d,h),g in vm.groupby(["dow","hour"])["min"]: heat[d][h] = [int(g.size), r3(g.mean())]
    month = {k: [int(g.size), r3(g.mean())] for k,g in vm.groupby("ym")["min"]}
    ages = [[int(g.size), r3(g.mean())] for l,g in ((l, vm[vm.band==l]["min"]) for l in labels)]
    types = {k: [int(g.size), r3(g.mean())] for k,g in vm.groupby("type")["min"]}
    st = {}
    for role, col in (("start","s_id"),("end","e_id")):
        g = vm.groupby(col)["min"].agg(["size","mean"]).reset_index().rename(columns={col:"station_id"}).merge(s, on="station_id")
        g = g[g["size"]>=20]
        st[role] = [[x.station_id, x["name"], round(x.lat,5), round(x.lon,5), int(x["size"]), r3(x["mean"],2)] for _,x in g.iterrows()]
    yr = {int(k): [int(g.size), r3(g.sum(),2)] for k,g in pm.groupby("year").amount}
    pmo = {k: r3(g.sum(),2) for k,g in pm.groupby("ym").amount}
    ap = {l: [int(g.size), r3(g.tot.sum(),2), r3(g.tot.mean(),2)] for l,g in rs_ if False} if False else {}
    ap = {l: [int(len(g)), r3(g.tot.sum(),2), r3(g.tot.mean(),2)] for l,g in rm.groupby("band")}
    out["f"][key] = {"rides": int(len(vm)), "avg": r3(vm["min"].mean()), "heat": heat, "month": month, "ages": ages, "types": types,
                     "stations": st, "spend_year": yr, "spend_month": pmo, "spend_age": ap,
                     "payments": int(len(pm)), "spend_total": r3(pm.amount.sum(),2), "avg_payment": r3(pm.amount.mean(),2),
                     "riders": {"all": int(len(r)), "member": int(r.member.sum()), "casual": int((~r.member).sum())}[key]}
    # --- extra views ---
    EDGES = [0,2,4,6,8,10,12,15,20,25,30,45,60,120,1440]
    hist, _ = np.histogram(vm["min"], bins=EDGES)
    out["f"][key]["dur_hist"] = {"edges": EDGES, "counts": [int(x) for x in hist]}
    tm = {}
    for (ym, ty), g in vm.groupby(["ym", "type"]).size().items(): tm.setdefault(ym, {})[ty] = int(g)
    out["f"][key]["type_month"] = tm
    names = dict(zip(s.station_id, s.name))
    rt = vm.groupby(["s_id", "e_id"])["min"].agg(["size", "mean"]).reset_index().sort_values("size", ascending=False)
    pack = lambda d: [[names.get(x.s_id, x.s_id), names.get(x.e_id, x.e_id), int(x["size"]), r3(x["mean"], 1)] for _, x in d.head(15).iterrows()]
    out["f"][key]["routes"] = {"p2p": pack(rt[rt.s_id != rt.e_id]), "round": pack(rt[rt.s_id == rt.e_id]),
                               "round_share": r3((rt[rt.s_id == rt.e_id]["size"].sum()) / rt["size"].sum(), 4)}
    rr = {"all": r, "member": r[r.member], "casual": r[~r.member]}[key].copy()
    rr["sd"] = pd.to_datetime(rr.start); rr["ed"] = pd.to_datetime(rr.end)
    valid_end = rr.ed.notna() & (rr.ed >= rr.sd)
    out["f"][key]["opened"] = {int(k): int(n) for k, n in rr.sd.dt.year.value_counts().sort_index().items()}
    out["f"][key]["closed"] = {int(k): int(n) for k, n in rr[valid_end].ed.dt.year.value_counts().sort_index().items()}
    act = {}
    for per in pd.period_range("2013-01", "2022-02", freq="M"):
        a, b = per.start_time, per.end_time
        act[str(per)] = int(((rr.sd <= b) & ((~valid_end) | (rr.ed >= a))).sum())
    out["f"][key]["active"] = act
    out["f"][key]["invalid_accounts"] = int((rr.ed.notna() & (rr.ed < rr.sd)).sum())
json.dump(out, open("data.json","w"), separators=(",",":"))
print("wrote data.json", round(len(json.dumps(out,separators=(',',':')))/1024), "KB")
print({k:(out["f"][k]["rides"], out["f"][k]["avg"], out["f"][k]["spend_total"], out["f"][k]["avg_payment"]) for k in out["f"]})
print("station lat range", s.lat.min(), s.lat.max(), "lon", s.lon.min(), s.lon.max())
