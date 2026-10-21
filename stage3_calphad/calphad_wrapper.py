"""Stage 3 (Tier-3a): pycalphad equilibrium phase fractions.
Gracefully exits until TDB files are dropped into stage3_calphad/tdb/."""
import sys, pandas as pd
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]
TDB_DIR = REPO / "stage3_calphad" / "tdb"
tdbs = sorted(TDB_DIR.glob("*.tdb"))
if not tdbs:
    sys.exit("No TDB yet: Tier-2 gates hold the Stage-3 gate (labelled TIER-2). "
             "Drop SGTE unary + Ti-binary TDBs into stage3_calphad/tdb/ and re-run.")

from pycalphad import Database, equilibrium, variables as v
merged = "\n".join(p.read_text(encoding="utf-8", errors="ignore") for p in tdbs)
dbf = Database(merged, fmt="tdb")
print(f"Merged {len(tdbs)} TDBs | elements: {sorted(dbf.elements)} | phases: {len(dbf.phases)}")

df = pd.read_csv(REPO / "data" / "stage3_survivors.csv")
EL = {"Ti":"TI","Al":"AL","V":"V","Mo":"MO","Zr":"ZR","Sn":"SN","Cr":"CR","Fe":"FE"}
rows = []
for _, r in df.iterrows():
    present = {EL[k]: float(r[f"{k}_at"]) for k in EL if f"{k}_at" in r.columns and r[f"{k}_at"] > 0}
    comps = [c for c in present if c in dbf.elements] + ["VA"]
    missing = [c for c in present if c not in dbf.elements]
    if missing or len(comps) < 3:
        rows.append({"formula": r.formula, "gap": f"tdb_missing:{missing or 'too_few'}"}); continue
    tot = sum(present.values()); conds = {v.T: 900.0, v.P: 101325.0}
    dep = max(comps[:-1], key=lambda c: present[c])
    for c in comps[:-1]:
        if c != dep: conds[v.X(c)] = present[c] / tot
    try:
        res = equilibrium(dbf, comps, list(dbf.phases.keys()), conds)
        fr = {}
        for ph, f_ in zip(res.Phase.values.ravel(), res.NP.values.ravel()):
            if ph != "" and f_ > 1e-6: fr[ph] = fr.get(ph, 0.0) + float(f_)
        rows.append({"formula": r.formula, "gap": "",
                     **{f"frac_{k}": round(val, 4) for k, val in sorted(fr.items())}})
    except Exception as e:
        rows.append({"formula": r.formula, "gap": f"equilibrium_failed:{type(e).__name__}"})

o = pd.DataFrame(rows)
o.to_csv(REPO / "data" / "stage3_phase_fractions.csv", index=False)
print(o["gap"].value_counts().to_string())
print(f"[Saved] data/stage3_phase_fractions.csv")