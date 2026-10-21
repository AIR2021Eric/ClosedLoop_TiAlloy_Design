import pandas as pd, numpy as np
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]
df = pd.read_csv(REPO / "data" / "stage2_survivors.csv")
fr = pd.read_csv(REPO / "data" / "pareto_front_current.csv")

F = lambda d: np.column_stack([d.spec_stiff_cons.values, -d.hull_v2.values, d.pugh_proxy.values - 1.75])
A, B = F(df), F(fr)
def dom(q, P):  # does any row of P dominate q?
    return np.any(np.all(P >= q, axis=1) & np.any(P > q, axis=1))

print("Check 1 - no front member dominated by any survivor:",
      all(not dom(q, A) for q in B))
print("Check 2 - every non-front survivor dominated by >=1 front member:",
      all(dom(q, B) for q in A if not any(np.array_equal(q, b) for b in B)))

print("\nWhy front members look 'interior' in 2-D panels:")
for _, r in fr.iterrows():
    q = np.array([r.spec_stiff_cons, -r.hull_v2, r.pugh_proxy - 1.75])
    beat_pair = df[(df.spec_stiff_cons >= r.spec_stiff_cons) & (df.hull_v2 <= r.hull_v2)
                   & ~df.formula.isin(fr.formula)]   # beats it in panel-1 pair
    if len(beat_pair):
        w = beat_pair.loc[beat_pair.pugh_proxy.idxmax()]
        print(f"  {r.formula:16s}: {len(beat_pair)} survivors beat it on (E/rho, hull), "
              f"but their best Pugh is {w.pugh_proxy:.3f} < {r.pugh_proxy:.3f} -> none dominates in 3-D")