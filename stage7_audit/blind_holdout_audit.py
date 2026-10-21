"""Stage 7 v4: Retrospective Empirical Anchoring (Blind Hold-out Audit).
- Baselines in wt% (datasheet nominals); Mo_eq/Al_eq and density use wt% directly.
- wt->at% conversion used ONLY for: c_solute (Stage-5 ss term) and the Stage-2 Cr cap.
- Full-stack gate: Mo_eq <= 16 AND Al_eq <= 9 AND Cr_at <= 4.0.
- Density bias calibration: single volume-contraction factor from mean bias.
Outputs: data/stage7_audit_report.csv, results_archive/slide_stage7_audit.png
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DATA, ARCH = REPO / "data", REPO / "results_archive"
ARCH.mkdir(parents=True, exist_ok=True)

# ---------------- 1. COMMERCIAL BASELINES (wt% datasheet nominals) ----------------
baselines = [
    {"name": "Ti-6Al-4V (Gr5)", "family": "alpha+beta", "Ti": 90.0, "Al": 6.0, "V": 4.0,
     "E_DS": 114, "rho_DS": 4.43, "YS_DS_lo": 880, "YS_DS_hi": 1100},
    {"name": "Ti-6242", "family": "near-alpha", "Ti": 86.0, "Al": 6.0, "Sn": 2.0, "Zr": 4.0, "Mo": 2.0,
     "E_DS": 120, "rho_DS": 4.54, "YS_DS_lo": 900, "YS_DS_hi": 1000},
    {"name": "Ti-6246", "family": "alpha+beta", "Ti": 82.0, "Al": 6.0, "Sn": 2.0, "Zr": 4.0, "Mo": 6.0,
     "E_DS": 120, "rho_DS": 4.68, "YS_DS_lo": 950, "YS_DS_hi": 1050},
    {"name": "Ti-5553", "family": "metastable-beta", "Ti": 82.0, "Al": 5.0, "V": 5.0, "Mo": 5.0, "Cr": 3.0,
     "E_DS": 110, "rho_DS": 4.65, "YS_DS_lo": 1100, "YS_DS_hi": 1200},
    {"name": "Ti-10-2-3", "family": "metastable-beta", "Ti": 85.0, "Al": 3.0, "V": 10.0, "Fe": 2.0,
     "E_DS": 110, "rho_DS": 4.65, "YS_DS_lo": 1100, "YS_DS_hi": 1200},
    {"name": "Ti-15-3-3-3", "family": "metastable-beta", "Ti": 76.0, "Al": 3.0, "V": 15.0, "Cr": 3.0, "Sn": 3.0,
     "E_DS": 105, "rho_DS": 4.90, "YS_DS_lo": 1000, "YS_DS_hi": 1150},
    {"name": "Beta C", "family": "metastable-beta", "Ti": 75.0, "Al": 3.0, "V": 8.0, "Cr": 6.0, "Mo": 4.0, "Zr": 4.0,
     "E_DS": 110, "rho_DS": 4.95, "YS_DS_lo": 1100, "YS_DS_hi": 1250},
    {"name": "CP-Ti (Gr2)", "family": "cp", "Ti": 100.0,
     "E_DS": 105, "rho_DS": 4.51, "YS_DS_lo": 275, "YS_DS_hi": 345},
]
df = pd.DataFrame(baselines)

M = {"Ti": 47.867, "Al": 26.982, "V": 50.942, "Mo": 95.95,
     "Zr": 91.224, "Sn": 118.71, "Cr": 51.996, "Fe": 55.845}
rho_el = {"Ti": 4.51, "Al": 2.70, "V": 6.11, "Mo": 10.22,
          "Zr": 6.52, "Sn": 7.28, "Cr": 7.19, "Fe": 7.87}

wt_cols = [el for el in M if el in df.columns]
wt = df[wt_cols].fillna(0.0)

# ---------------- 2. wt%-based proxies: Mo_eq / Al_eq / density ----------------
moeq = wt['Mo'] + wt['V']/1.5 + wt['Cr']/1.25 + wt['Fe']/1.25
aleq = wt['Al'] + wt['Sn']/3.0 + wt['Zr']/6.0
df['Mo_eq'] = moeq.round(1)
df['Al_eq'] = aleq.round(1)

inv_rho = sum(wt[el]/100.0 / rho_el[el] for el in wt_cols)
df['rho_calc'] = (1 / inv_rho).round(3)
df['rho_err_pct'] = ((df['rho_calc'] - df['rho_DS']) / df['rho_DS'] * 100).round(2)

# ---------------- 3. wt -> at% (ONLY for Cr cap and c_solute) ----------------
mol = pd.DataFrame({el: wt[el] / M[el] for el in wt_cols})
tot_mol = mol.sum(axis=1)
at = mol.div(tot_mol, axis=0) * 100.0
df['Cr_at'] = at.get('Cr', pd.Series(0.0, index=df.index)).fillna(0.0).round(2)
df['c_solute_at'] = (1.0 - at.get('Ti', pd.Series(100.0, index=df.index)).fillna(100.0)/100.0).round(3)

# ---------------- 4. FULL-STACK GATE (Stage-2 Cr cap + Stage-3 windows) ----------------
df['gate_pass'] = (df['Mo_eq'] <= 16.0) & (df['Al_eq'] <= 9.0) & (df['Cr_at'] <= 4.0)

# ---------------- 5. Density bias calibration (volume contraction) ----------------
bias = df['rho_err_pct'].mean() / 100.0
df['rho_corr'] = (df['rho_calc'] / (1 + bias)).round(3)
df['rho_corr_err_pct'] = ((df['rho_corr'] - df['rho_DS']) / df['rho_DS'] * 100).round(2)

# ---------------- 6. Tier-3 strength scenarios (Stage-5 logic) ----------------
C_REF, K_Y, D_REF_UM, B_SS = 0.10, 0.35, 10.0, 400.0
BASE = {
    ("A_unaged", "alpha+beta"): 800.0,      ("B_aged", "alpha+beta"): 1050.0,
    ("A_unaged", "metastable-beta"): 850.0, ("B_aged", "metastable-beta"): 1200.0,
    ("A_unaged", "near-alpha"): 750.0,      ("B_aged", "near-alpha"): 950.0,
    ("A_unaged", "cp"): 340.0,              ("B_aged", "cp"): 450.0,
}
def d_hp(d_um): return K_Y * ((d_um*1e-6)**-0.5 - (D_REF_UM*1e-6)**-0.5)

ys = []
for _, r in df.iterrows():
    scen = "A_unaged" if r["name"] == "CP-Ti (Gr2)" else "B_aged"
    ys.append(BASE[(scen, r["family"])] + B_SS*(r.c_solute_at - C_REF) + d_hp(10.0))
df['YS_calc'] = np.round(ys, 0)
df['YS_DS_mid'] = (df['YS_DS_lo'] + df['YS_DS_hi']) / 2
df['YS_err_pct'] = ((df['YS_calc'] - df['YS_DS_mid']) / df['YS_DS_mid'] * 100).round(1)

# ---------------- 7. Save + print ----------------
csv = DATA / "stage7_audit_report.csv"
df.to_csv(csv, index=False)
print(f"[Saved] {csv}\n")
print(df[['name', 'family', 'Mo_eq', 'Al_eq', 'Cr_at', 'gate_pass',
          'rho_calc', 'rho_err_pct', 'rho_corr', 'rho_corr_err_pct',
          'YS_calc', 'YS_DS_mid', 'YS_err_pct']].to_string(index=False))

bad = df[~df.gate_pass]
print(f"\nGate failures among viable alloys: {bad.name.tolist() if len(bad) else 'NONE'}")
for _, r in bad.iterrows():
    reasons = []
    if r.Mo_eq > 16: reasons.append(f"Mo_eq {r.Mo_eq}")
    if r.Al_eq > 9:  reasons.append(f"Al_eq {r.Al_eq}")
    if r.Cr_at > 4:  reasons.append(f"Cr_at {r.Cr_at} > 4 (Stage-2 cap)")
    print(f"  - {r['name']}: {', '.join(reasons)}")
print(f"Bias factor (volume contraction): {1+bias:.4f}")
print(f"Mean |density| error  raw: {df.rho_err_pct.abs().mean():.2f}%  "
      f"-> calibrated: {df.rho_corr_err_pct.abs().mean():.2f}%")
print(f"Mean |strength| error: {df.YS_err_pct.abs().mean():.2f}%")

# ---------------- 8. Audit figure ----------------
fig, axs = plt.subplots(1, 2, figsize=(15, 5.8))

axs[0].scatter(df.rho_DS, df.rho_calc, s=90, facecolors='none', edgecolors='#1f77b4',
               label='raw proxy', zorder=3)
axs[0].scatter(df.rho_DS, df.rho_corr, s=90, c='#1f77b4', edgecolors='k',
               label='calibrated proxy', zorder=4)
for _, r in df.iterrows():
    axs[0].annotate(r["name"], (r.rho_DS, r.rho_corr), fontsize=8,
                    xytext=(5, 5), textcoords="offset points")
lims = [4.3, 5.1]
axs[0].plot(lims, lims, 'k--', alpha=.5, label='Perfect parity')
axs[0].set_xlabel("Datasheet density (g/cm³)")
axs[0].set_ylabel("Proxy density (g/cm³)")
axs[0].set_title(f"Density audit: raw MAE {df.rho_err_pct.abs().mean():.2f}% -> "
                 f"calibrated MAE {df.rho_corr_err_pct.abs().mean():.2f}%")
axs[0].legend(fontsize=8); axs[0].grid(ls='--', alpha=.5)

axs[1].scatter(df.YS_DS_mid, df.YS_calc, s=100, c='#d62728', edgecolors='k', zorder=3)
for _, r in df.iterrows():
    axs[1].annotate(r["name"], (r.YS_DS_mid, r.YS_calc), fontsize=8,
                    xytext=(5, 5), textcoords="offset points")
    axs[1].errorbar(r.YS_DS_mid, r.YS_calc, xerr=(r.YS_DS_hi - r.YS_DS_lo)/2,
                    fmt='none', ecolor='gray', alpha=.6)
lims2 = [200, 1350]
axs[1].plot(lims2, lims2, 'k--', alpha=.5, label='Perfect parity')
axs[1].set_xlabel("Datasheet YS (mid, MPa)")
axs[1].set_ylabel("Tier-3 predicted YS (MPa)")
axs[1].set_title(f"Strength audit (MAE {df.YS_err_pct.abs().mean():.2f}%)")
axs[1].legend(fontsize=8); axs[1].grid(ls='--', alpha=.5)

plt.tight_layout()
png = ARCH / "slide_stage7_audit.png"
plt.savefig(png, dpi=300, bbox_inches='tight')
print(f"[Saved] {png}")