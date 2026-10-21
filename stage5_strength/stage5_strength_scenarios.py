"""Stage 5: Tier-3 semi-empirical strength scenarios for CARRY candidates.
sigma_y = BASE(scenario, family) + B_ss*(c - c_ref) + k_y*(d^-1/2 - d_ref^-1/2)
ALL assumptions are declared constants below; edit them to run sensitivity.
Outputs: data/stage5_strength_scenarios.csv, results_archive/slide_stage5_strength.png
"""
import re
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DATA, ARCH = REPO / "data", REPO / "results_archive"
ARCH.mkdir(parents=True, exist_ok=True)

# ---------------- DECLARED ASSUMPTIONS (Tier-3) ----------------
C_REF      = 0.10      # at-fraction solute of calibration reference (Ti-6Al-4V)
D_REF_UM   = 10.0      # reference grain size (um)
K_Y        = 0.35      # MPa*m^0.5, Hall-Petch slope (mid-range Ti alloys)
B_SS       = 400.0     # MPa per at-fraction solute above C_REF (local linear)
SS_EDGE    = 0.20      # validity radius of the local-linear ss term
GRAIN_UM   = [1.0, 10.0, 50.0]
BASE = {   # (scenario, family): (baseline YS MPa, uncertainty MPa) - datasheet families
    ("A_unaged", "alpha+beta"):      (800.0, 100.0),
    ("A_unaged", "metastable-beta"): (850.0, 100.0),
    ("B_aged",   "alpha+beta"):      (1050.0, 150.0),
    ("B_aged",   "metastable-beta"): (1200.0, 150.0),
}
TI64_ANNEALED_YS, TI64_STA_YS, TI64_RHO = 880.0, 1100.0, 4.43
TI64_STA_SPEC = TI64_STA_YS / TI64_RHO

def d_hp(d_um):        # MPa, relative to d_ref
    return K_Y * ((d_um * 1e-6) ** -0.5 - (D_REF_UM * 1e-6) ** -0.5)

# ---------------- inputs ----------------
sl = pd.read_csv(DATA / "stage6_shortlist_ensemble.csv")
car = sl[sl.decision.eq("CARRY")].copy()

def solute_at(formula):
    comp = {el: float(n) for el, n in re.findall(r'([A-Z][a-z]?)([\d\.]+)', formula)}
    return 1.0 - comp.get("Ti", 100.0) / 100.0

rows = []
for _, r in car.iterrows():
    c = solute_at(r.formula)
    dc = c - C_REF
    flag = "SS_LINEAR_EDGE" if abs(dc) >= SS_EDGE else "OK"
    for scen in ["A_unaged", "B_aged"]:
        base, unc = BASE[(scen, r.phase_field)]
        ss = B_SS * dc
        ys = {d: base + ss + d_hp(d) for d in GRAIN_UM}
        mid = ys[D_REF_UM]
        lo, hi = base - unc + ss + d_hp(max(GRAIN_UM)), base + unc + ss + d_hp(min(GRAIN_UM))
        rows.append({
            "formula": r.formula, "phase_field": r.phase_field, "scenario": scen,
            "c_solute": round(c, 3), "ss_adj_MPa": round(ss, 1),
            "base_MPa": base, "base_unc_MPa": unc,
            "sigma_y_d1": round(ys[1.0], 0), "sigma_y_d10": round(ys[10.0], 0),
            "sigma_y_d50": round(ys[50.0], 0),
            "sigma_y_mid": round(mid, 0), "sigma_y_lo": round(lo, 0), "sigma_y_hi": round(hi, 0),
            "rho": r.rho,
            "spec_strength_mid": round(mid / r.rho, 1),
            "spec_strength_lo": round(lo / r.rho, 1),
            "spec_strength_hi": round(hi / r.rho, 1),
            "ratio_vs_ti64_sta": round((mid / r.rho) / TI64_STA_SPEC, 2),
            "validity_flag": flag, "tier": "TIER-3",
        })
out = pd.DataFrame(rows)

# ---------------- 4-objective final front (aged scenario) ----------------
aged = out[out.scenario.eq("B_aged")].set_index("formula")
m = car.merge(aged[["spec_strength_mid"]], left_on="formula", right_index=True)
F = np.column_stack([-m.hull_v2.values, m.pugh_proxy.values - 1.75,
                     m.spec_stiff_aged.values, m.spec_strength_mid.values])
keep = np.ones(len(F), dtype=bool)
for i in range(len(F)):
    if not keep[i]: continue
    dom = np.all(F[i] >= F, axis=1) & np.any(F[i] > F, axis=1)
    keep[dom] = False
m["on_final_front"] = keep
out = out.merge(m[["formula", "on_final_front"]], on="formula", how="left")

csv = DATA / "stage5_strength_scenarios.csv"
out.to_csv(csv, index=False)
print(f"[Saved] {csv}\n")
print(out[out.scenario.eq("B_aged")][
    ["formula", "phase_field", "c_solute", "sigma_y_mid", "sigma_y_lo", "sigma_y_hi",
     "spec_strength_mid", "ratio_vs_ti64_sta", "validity_flag", "on_final_front"]
].to_string(index=False))
print("\nAged-scenario specific strength vs Ti-6Al-4V STA anchor "
      f"({TI64_STA_SPEC:.1f} GPa*cm3/g):")
for _, r in out[out.scenario.eq("B_aged")].iterrows():
    print(f"  {r.formula:16s} {r.spec_strength_mid:6.1f}  ({r.ratio_vs_ti64_sta:+.2f}x anchor)")

# ---------------- figure ----------------
fig, axs = plt.subplots(1, 2, figsize=(15, 5.8))
xc = np.arange(len(car))
for ax, scen, ttl in [(axs[0], "A_unaged", "Scenario A: unaged / solution-treated"),
                      (axs[1], "B_aged", "Scenario B: aged two-phase (STA)")]:
    s = out[out.scenario.eq(scen)].set_index("formula").loc[car.formula]
    ax.bar(xc, s.sigma_y_mid, yerr=(s.sigma_y_mid - (s.base_MPa - s.base_unc_MPa + s.ss_adj_MPa)),
           capsize=4, color="#ff7f0e" if scen == "A_unaged" else "#1f77b4")
    ax.axhline(TI64_ANNEALED_YS, color='k', ls=':', lw=1)
    ax.axhline(TI64_STA_YS, color='k', ls='--', lw=1)
    ax.text(len(car) - 0.4, TI64_ANNEALED_YS + 25, "Ti-6-4V annealed 880", fontsize=8, ha='right')
    ax.text(len(car) - 0.4, TI64_STA_YS + 25, "Ti-6-4V STA 1100", fontsize=8, ha='right')
    ax.set_xticks(xc); ax.set_xticklabels(car.formula, rotation=30, ha='right', fontsize=9)
    ax.set_ylabel("Yield strength (MPa), d = 10 um ± base unc."); ax.set_title(ttl)
    ax.grid(ls='--', alpha=.5, axis='y')
fig.suptitle("Stage-5 Tier-3 strength scenarios (declared assumptions; recalibrate at Stage 7/8)",
             fontweight='bold')
plt.tight_layout()
png = ARCH / "slide_stage5_strength.png"
plt.savefig(png, dpi=300, bbox_inches='tight')
print(f"[Saved] {png}")