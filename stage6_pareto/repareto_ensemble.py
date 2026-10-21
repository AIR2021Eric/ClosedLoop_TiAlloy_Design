"""Stage 6 re-rank (ensemble-aware).
- VETO candidates whose Stage-4 ensemble violates Born criteria in >50% of runs (UNSTABLE_0K).
- CARRY the rest; report stiffness as TWO declared scenarios:
    * spec_stiff_0K   = ensemble-median E of the UNAGED 0K single-phase solid solution (Tier-1, banded)
    * spec_stiff_aged = zero-parameter composite/aged proxy E_proxy (Tier-2, datasheet-consistent)
- Selection front computed on (stability margin, ductility margin, aged specific stiffness).
- 0K bands are checked for overlap: if bands overlap, 0K stiffness CANNOT discriminate the pair
  (stiffness_0K_resolved = False) and must not be used as a selector.
Outputs: data/stage6_shortlist_ensemble.csv, results_archive/slide_stage6_shortlist_ensemble.png
"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DATA, ARCH = REPO / "data", REPO / "results_archive"
ARCH.mkdir(parents=True, exist_ok=True)

# Datasheet anchor for the aged scenario (Ti-6Al-4V: E ~ 114 GPa, rho ~ 4.43 g/cm3)
TI64_SPEC_STIFF = 114.0 / 4.43

# ---------------- inputs ----------------
front = pd.read_csv(DATA / "pareto_front_current.csv")
bands = pd.read_csv(DATA / "stage4_uq_bands.csv")
s2 = pd.read_csv(DATA / "stage2_gated_all.csv").set_index("formula")
s3 = pd.read_csv(DATA / "stage3_tier2_phase_gates.csv").set_index("formula")

df = front.merge(bands, on="formula", how="left", suffixes=("", "_uq"))
if "cls" not in df.columns:                      # tolerate older bands files
    df["cls"] = df["stability_class"]
df["E_proxy"]  = df.formula.map(s2["E_proxy"])
df["rho"]      = df.formula.map(s2["rho_proxy"])
df["Mo_eq_wt"] = df.formula.map(s3["Mo_eq_wt"])
df["Al_eq_wt"] = df.formula.map(s3["Al_eq_wt"])

# ---------------- ensemble veto ----------------
df["decision"] = np.where(df.cls.eq("UNSTABLE_0K"), "VETOED", "CARRY")

# ---------------- stiffness scenarios ----------------
df["spec_stiff_0K"]      = df["spec_stiff_med"]            # E_med / rho (unaged, banded)
df["spec_stiff_0K_iqr"]  = df["spec_stiff_iqr"]
df["spec_stiff_aged"]    = (df["E_proxy"] / df["rho"]).round(2)   # aged/composite proxy

# ---------------- Pareto among carries (aged scenario) ----------------
def non_dominated_mask(F):
    keep = np.ones(len(F), dtype=bool)
    for i in range(len(F)):
        if not keep[i]:
            continue
        dominated = np.all(F[i] >= F, axis=1) & np.any(F[i] > F, axis=1)
        keep[dominated] = False
    return keep

carry = df[df.decision.eq("CARRY")].copy()
F = np.column_stack([
    -carry.hull_v2.values,                 # maximize stability margin
    carry.pugh_proxy.values - 1.75,        # maximize ductility margin
    carry.spec_stiff_aged.values,          # maximize aged specific stiffness
])
carry["on_pareto_aged"] = non_dominated_mask(F)

# ---------------- can the 0K bands discriminate? (IQR band overlap) ----------------
lo = (carry.E_med - carry.E_iqr / 2).values
hi = (carry.E_med + carry.E_iqr / 2).values
resolved = [not any(j != i and lo[j] <= hi[i] and lo[i] <= hi[j] for j in range(len(carry)))
            for i in range(len(carry))]
carry["stiffness_0K_resolved"] = resolved

df = df.merge(carry[["formula", "on_pareto_aged", "stiffness_0K_resolved"]],
              on="formula", how="left")
df[["on_pareto_aged", "stiffness_0K_resolved"]] = df[
    ["on_pareto_aged", "stiffness_0K_resolved"]].fillna(False)

# ---------------- sort, save, print ----------------
df["_ord"] = df.decision.map({"CARRY": 0, "VETOED": 1})
df = df.sort_values(["_ord", "viol_frac"]).drop(columns="_ord")

cols = ["formula", "phase_field", "Mo_eq_wt", "Al_eq_wt", "decision", "viol_frac", "cls",
        "C44_med", "C44_iqr", "C11mC12_med", "E_med", "E_iqr",
        "spec_stiff_0K", "spec_stiff_0K_iqr", "E_proxy", "spec_stiff_aged",
        "hull_v2", "pugh_proxy", "rho", "on_pareto_aged", "stiffness_0K_resolved"]
out_csv = DATA / "stage6_shortlist_ensemble.csv"
df[cols].to_csv(out_csv, index=False)
print(f"[Saved] {out_csv}\n")
print(df[cols].to_string(index=False))

vet = df[df.decision.eq("VETOED")].formula.tolist()
car = df[df.decision.eq("CARRY")].formula.tolist()
frt = carry[carry.on_pareto_aged].formula.tolist()
print(f"\nVETOED ({len(vet)}): {', '.join(vet)}")
print(f"CARRY  ({len(car)}): {', '.join(car)}")
print(f"On aged-scenario Pareto front: {', '.join(frt)}")
if not carry.stiffness_0K_resolved.any():
    print("NOTE: 0K unaged stiffness bands overlap for ALL carries -> 0K E cannot discriminate; "
          "selection rests on hull/Pugh margins + aged scenario.")

# ---------------- decision figure ----------------
fig, axs = plt.subplots(1, 2, figsize=(15.5, 6.0))

for dec, mk, c in [("CARRY", "o", "#2ca02c"), ("VETOED", "X", "#d62728")]:
    s = df[df.decision.eq(dec)]
    axs[0].scatter(s.hull_v2, s.pugh_proxy, s=130, marker=mk, c=c, edgecolors="k", label=dec)
for _, r in df.iterrows():
    axs[0].annotate(r.formula, (r.hull_v2, r.pugh_proxy), fontsize=8,
                    xytext=(5, 4), textcoords="offset points")
axs[0].set_xlabel("hull_v2 (eV/atom, lower = more stable)")
axs[0].set_ylabel("Pugh ratio (ductility margin)")
axs[0].set_title("Stage-6 ensemble-aware shortlist\n(ensemble Born-veto applied)")
axs[0].legend(); axs[0].grid(ls="--", alpha=.5)

xc = np.arange(len(carry))
axs[1].bar(xc - 0.19, carry.spec_stiff_0K, 0.38, yerr=carry.spec_stiff_0K_iqr / 2,
           capsize=4, color="#ff7f0e", label="0K unaged single-phase (MLIP median ± IQR/2)")
axs[1].bar(xc + 0.19, carry.spec_stiff_aged, 0.38, color="#1f77b4",
           label="aged/composite proxy (E_proxy)")
axs[1].axhline(TI64_SPEC_STIFF, color="k", ls="--", lw=1)
axs[1].text(len(carry) - 0.5, TI64_SPEC_STIFF + 0.6,
            f"Ti-6Al-4V datasheet E/rho ≈ {TI64_SPEC_STIFF:.1f}", fontsize=9, ha="right")
axs[1].set_xticks(xc); axs[1].set_xticklabels(carry.formula, rotation=30, ha="right", fontsize=9)
axs[1].set_ylabel("specific stiffness E/rho (GPa·cm³/g)")
axs[1].set_title("Stiffness is scenario-dependent:\nunaged 0K solid solution vs aged composite")
axs[1].legend(fontsize=9); axs[1].grid(ls="--", alpha=.5, axis="y")

plt.tight_layout()
png = ARCH / "slide_stage6_shortlist_ensemble.png"
plt.savefig(png, dpi=300, bbox_inches="tight")
print(f"[Saved] {png}")