"""
Stage 6 - Pareto front extraction (exact non-dominated sorting) + 2D/3D visuals.
Objectives (all MAXIMIZED): spec_stiff_cons | -hull_v2 | pugh_proxy - 1.75
3-D view: hull axis inverted so the front is the visible outer envelope.
"""
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

# --- 3-D camera controls (tweak these to adjust the saved views) ---
ELEV,  AZIM  = 18.0, -60.0     # main saved view
ELEV2, AZIM2 = 12.0, -125.0    # alternate saved view

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA = REPO_ROOT / "data"
ARCH = REPO_ROOT / "results_archive"
ARCH.mkdir(parents=True, exist_ok=True)

SRC = DATA / "stage2_survivors.csv"
if not SRC.exists():
    sys.exit(f"ERROR: {SRC} not found. Run stage2_export/export_survivors.py (Block 2) first.")

df = pd.read_csv(SRC)
print(f"Input survivors: {len(df)} rows from {SRC.name}")

REQUIRED = ['formula', 'spec_stiff_cons', 'hull_v2', 'pugh_proxy']
missing = [c for c in REQUIRED if c not in df.columns]
if missing:
    sys.exit(f"ERROR: missing columns {missing}. Available: {list(df.columns)}")

F = np.column_stack([
    df['spec_stiff_cons'].to_numpy(float),
    -df['hull_v2'].to_numpy(float),
    df['pugh_proxy'].to_numpy(float) - 1.75,
])

def non_dominated_mask(F):
    """Exact Pareto membership: keep points dominated by nobody."""
    keep = np.ones(len(F), dtype=bool)
    for i in range(len(F)):
        if not keep[i]:
            continue   # dominated points add no new dominance (transitivity)
        dominated = np.all(F[i] >= F, axis=1) & np.any(F[i] > F, axis=1)
        keep[dominated] = False
    return keep

keep = non_dominated_mask(F)
pareto = df[keep].copy().sort_values('spec_stiff_cons', ascending=False).reset_index(drop=True)

out_csv = DATA / "pareto_front_current.csv"
pareto.to_csv(out_csv, index=False)
print(f"Pareto front size: {len(pareto)} / {len(df)} ({100*len(pareto)/len(df):.1f}%)")
print(f"[Saved] {out_csv}")

print("\nExtreme members of the front:")
for label, col, asc in [("max specific stiffness", 'spec_stiff_cons', False),
                        ("most stable (min hull)", 'hull_v2', True),
                        ("most ductile (max Pugh)", 'pugh_proxy', False)]:
    r = pareto.sort_values(col, ascending=asc).iloc[0]
    print(f"  - {label:26s}: {r['formula']:16s} E/rho={r['spec_stiff_cons']:.2f}, "
          f"hull={r['hull_v2']:.3f}, Pugh={r['pugh_proxy']:.2f}")

s = pareto.sort_values('spec_stiff_cons')
rate = (s['hull_v2'].diff() / s['spec_stiff_cons'].diff().replace(0, np.nan)).dropna()
if len(rate):
    print(f"\nMean trade-off rate along front: {rate.mean():.4f} eV/atom per unit E/rho")

print("\nTop-10 by specific stiffness on the front:")
print(pareto.head(10)[['formula', 'spec_stiff_cons', 'hull_v2', 'pugh_proxy']].to_string(index=False))

# ---------- 2-D pairwise panels ----------
fig, axs = plt.subplots(1, 3, figsize=(16, 4.6))
pairs = [('spec_stiff_cons', 'hull_v2',    'Specific stiffness vs hull energy'),
         ('spec_stiff_cons', 'pugh_proxy', 'Specific stiffness vs Pugh ratio'),
         ('hull_v2',         'pugh_proxy', 'Hull energy vs Pugh ratio')]
for ax, (xa, ya, t) in zip(axs, pairs):
    ax.scatter(df[xa], df[ya], s=12, c='lightgray', edgecolors='none', label='gated survivors')
    ax.scatter(pareto[xa], pareto[ya], s=45, c='#d62728', edgecolors='k', label='Pareto front')
    ax.set_xlabel(xa); ax.set_ylabel(ya); ax.set_title(t)
    ax.legend(fontsize=8); ax.grid(ls='--', alpha=.5)
fig.suptitle(f"Stage 6 Pareto front ({len(pareto)} non-dominated of {len(df)} gated survivors)",
             fontweight='bold')
plt.tight_layout()
out_png = ARCH / "slide_pareto_current.png"
plt.savefig(out_png, dpi=300, bbox_inches='tight')
print(f"[Saved] {out_png}")
plt.close(fig)

# ---------- 3-D views (hull inverted: up/right/front = better on every axis) ----------
def draw_3d(elev, azim, tag):
    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection='3d')
    ax.scatter(df.spec_stiff_cons, df.hull_v2, df.pugh_proxy,
               s=12, c='lightgray', edgecolors='none', depthshade=False,
               label='gated survivors')
    ax.scatter(pareto.spec_stiff_cons, pareto.hull_v2, pareto.pugh_proxy,
               s=70, c='#d62728', edgecolors='k', depthshade=False,
               label='Pareto front')
    ax.invert_yaxis()                      # low hull plots UP -> front = outer skin
    ax.set_xlabel('Specific stiffness E/rho')
    ax.set_ylabel('Hull energy (inverted: up = stable)')
    ax.set_zlabel('Pugh ratio')
    ax.view_init(elev=elev, azim=azim)     # <-- the camera adjustment
    ax.set_title(f"3-D Pareto front (elev={elev:.0f}, azim={azim:.0f})\n"
                 f"red points form the outer envelope in 3-D")
    for _, r in pareto.head(3).iterrows(): # label the top-3 stiffness knees
        ax.text(r.spec_stiff_cons, r.hull_v2, r.pugh_proxy, f"  {r.formula}", fontsize=8)
    ax.legend(loc='upper left', fontsize=9)
    plt.tight_layout()
    p = ARCH / f"slide_pareto_3d{tag}.png"
    plt.savefig(p, dpi=300, bbox_inches='tight')
    print(f"[Saved] {p}")
    return fig

draw_3d(ELEV,  AZIM,  "")
draw_3d(ELEV2, AZIM2, "_alt")

print("\nInteractive window: drag to rotate / scroll to zoom, then close to finish.")
plt.show()