"""Stage 3 (Tier-2 interim): Mo-eq / Al-eq phase-field gates.
Labels: TIER-2 until pycalphad+TDB (Tier-3a) coverage exists."""
import pandas as pd
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
M = {"Ti":47.867,"Al":26.982,"V":50.942,"Mo":95.95,"Zr":91.224,"Sn":118.71,"Cr":51.996,"Fe":55.845}

df = pd.read_csv(REPO / "data" / "stage2_gated_all.csv")
print(f"Stage-2 gated survivors in: {len(df)}")

# at% -> wt%
mass = pd.DataFrame({el: df[f"{el}_at"] * M[el] for el in M if f"{el}_at" in df.columns})
tot = mass.sum(axis=1)
wt = mass.div(tot, axis=0) * 100.0

# wt% equivalents (standard Ti-alloy formulas; O/C/N assumed negligible)
moeq = (wt.get('Mo', 0) + wt.get('V', 0)/1.5 + wt.get('Cr', 0)/1.25 + wt.get('Fe', 0)/1.25)
aleq = (wt.get('Al', 0) + wt.get('Sn', 0)/3.0 + wt.get('Zr', 0)/6.0)

def field(m):
    if m < 2:  return "near-alpha"
    if m < 10: return "alpha+beta"
    return "metastable-beta"

out = df.copy()
out["Mo_eq_wt"] = moeq.round(2); out["Al_eq_wt"] = aleq.round(2)
out["phase_field"] = moeq.map(field)
flags = []
for a, m in zip(aleq, moeq):
    f = []
    if a > 9.0:  f.append("AL2_RISK")
    if m > 16.0: f.append("MOEQ_EXCESS")
    flags.append(";".join(f) if f else "OK")
out["tier2_flag"] = flags
out["tier2_pass"] = out.tier2_flag.eq("OK")

out.to_csv(REPO / "data" / "stage3_tier2_phase_gates.csv", index=False)
keep = out[out.tier2_pass]
keep.head(100).to_csv(REPO / "data" / "stage3_survivors.csv", index=False)
print(f"Tier-2 pass: {len(keep)} / {len(out)}  -> data/stage3_survivors.csv (Top-100)")
print("\nPhase-field mix of survivors:")
print(keep.phase_field.value_counts().to_string())

# Deep dive: where do the 8 Pareto members land?
fr = pd.read_csv(REPO / "data" / "pareto_front_current.csv")
chk = out[out.formula.isin(fr.formula)][["formula","Mo_eq_wt","Al_eq_wt","phase_field","tier2_flag"]]
print("\nPareto front vs Tier-2 phase gates:")
print(chk.to_string(index=False))