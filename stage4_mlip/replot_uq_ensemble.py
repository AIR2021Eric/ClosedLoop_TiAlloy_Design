"""stage4_mlip/replot_uq_ensemble.py - ensemble-aware stats (median + Born-violation fraction)."""
import numpy as np, pandas as pd, matplotlib.pyplot as plt
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]
raw = pd.read_csv(REPO / "data" / "stage4_uq_raw.csv")
raw["C11mC12"] = raw.C11 - raw.C12

rows = []
for f, g in raw.groupby("formula"):
    viol = ((g.C44 < 0) | (g.C11mC12 < 0)).mean()
    cls = "UNSTABLE_0K" if viol > 0.5 else ("MARGINAL" if viol > 0.2 else "STABLE_SOFT")
    rows.append(dict(formula=f, viol_frac=round(viol, 2), C44_med=round(g.C44.median(), 1),
                     C11mC12_med=round(g.C11mC12.median(), 1), E_med=round(g.E.median(), 1),
                     E_iqr=round(g.E.quantile(.75) - g.E.quantile(.25), 1), cls=cls))
out = pd.DataFrame(rows).sort_values("viol_frac")
out.to_csv(REPO / "data" / "stage4_uq_ensemble.csv", index=False)
print(out.to_string(index=False))

cols = {"STABLE_SOFT": "#98df8a", "MARGINAL": "#ff7f0e", "UNSTABLE_0K": "#d62728"}
fig, axs = plt.subplots(1, 2, figsize=(15, 5.5))
x = np.arange(len(out))
axs[0].bar(x, out.viol_frac, color=[cols[c] for c in out.cls])
axs[0].axhline(0.5, color='k', ls='--'); axs[0].axhline(0.2, color='k', ls=':')
axs[0].set_ylabel("fraction of 9 runs violating Born criteria")
axs[1].boxplot([raw[raw.formula == f].C44.values for f in out.formula], showfliers=False)
axs[1].axhline(0, color='k', lw=1); axs[1].set_ylabel("C44 (GPa)")
for ax, t in zip(axs, ["Ensemble Born-violation fraction", "C44 distribution per alloy (IQR boxes)"]):
    ax.set_title(t); ax.set_xticks(x); ax.set_xticklabels(out.formula, rotation=45, ha='right')
plt.tight_layout(); plt.savefig(REPO / "results_archive" / "slide_stage4_uq_ensemble.png", dpi=300, bbox_inches='tight')
print("[Saved] results_archive/slide_stage4_uq_ensemble.png")