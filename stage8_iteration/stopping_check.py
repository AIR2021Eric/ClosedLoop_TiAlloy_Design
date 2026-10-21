"""Stage 8 - pre-registered stopping rule (declare BEFORE further runs; do not tune after).
PRIMARY  STOP : K=2 consecutive real iterations with (new_certified==0 AND certified-front
                hypervolume gain < 1%).
SAFETY   STOP : iter_id > MAX_ITER (10 real iterations).
DIAGNOSTIC    : GP-label growth + Tier-S kill-rate printed as exhaustion indicators (never gate).
Sources: data/iteration_log.csv (immutable index) + results_archive/iterations/iter_XXX.json
         (end-of-iteration archive state). Keys/values whitespace-stripped (CSV/JSON round-trips).
"""
import json, re
import numpy as np, pandas as pd
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DATA, ARCH = REPO / "data", REPO / "results_archive"
K, HV_EPS, MAX_ITER = 2, 0.01, 10
REF = np.array([21.0, 2.25])          # declared Ashby reference point (dominated by all members)

def _strip(o):
    if isinstance(o, dict):  return {k.strip(): _strip(v) for k, v in o.items()}
    if isinstance(o, list):  return [_strip(x) for x in o]
    if isinstance(o, str):   return o.strip()
    return o

def hv2d(pts, ref):
    """Exact 2-D hypervolume (maximize both objectives)."""
    if len(pts) == 0: return 0.0
    p = np.asarray(pts, float)
    p = p[(p[:, 0] > ref[0]) & (p[:, 1] > ref[1])]
    if len(p) == 0: return 0.0
    p = p[np.argsort(-p[:, 0])]
    vol, prev_y = 0.0, ref[1]
    for x, y in p:
        if y > prev_y:
            vol += (x - ref[0]) * (y - prev_y); prev_y = y
    return vol

def certified_front_hv(iter_id):
    cands = sorted((ARCH / "iterations").glob(f"iter_{iter_id:03d}*.json"))   # [v2.5] tagged snapshots
    if not cands:
        return 0.0
    p = max(cands, key=lambda q: q.stat().st_mtime)                          # newest = final state
    d = _strip(json.loads(p.read_text()))
    pts = [(c["ashby_strength"], c["ashby_stiffness"]) for c in d.get("archive_certified", [])]
    if not pts: return 0.0
    a = np.array(pts); keep = []
    for i in range(len(a)):
        dom = np.all(a >= a[i], axis=1) & np.any(a > a[i], axis=1)
        if not dom.any(): keep.append(tuple(a[i]))
    return hv2d(keep, REF)

log = pd.read_csv(DATA / "iteration_log.csv")
real = log[log.run_ids != "dry"].drop_duplicates("iter_id", keep="last").sort_values("iter_id")
rows, prev, streak = [], None, 0
for _, r in real.iterrows():
    hv = certified_front_hv(int(r.iter_id))
    gain = 0.0 if prev in (None, 0.0) else (hv - prev) / prev
    s1 = (int(r.new_certified) == 0)
    s2 = (prev is not None and gain < HV_EPS)
    streak = streak + 1 if (s1 and s2) else 0
    gp = re.search(r"gp_train=([\d.]+)", str(r.notes))
    rows.append(dict(iter=int(r.iter_id), new_cert=int(r.new_certified), hv=round(hv, 4),
                     hv_gain_pct=round(gain * 100, 2), stagnant=bool(s1 and s2), streak=streak,
                     gp_labels=float(gp.group(1)) if gp else np.nan,
                     S_kill_rate=round(int(r.new_vetoed) / max(int(r.n_tierS), 1), 2)))
    prev = hv
out = pd.DataFrame(rows)
print(out.to_string(index=False))
stop = bool(len(out) and out.streak.iloc[-1] >= K)
cap = int(real.iter_id.max()) >= MAX_ITER
print(f"\nPRIMARY stagnation (K={K}, HV eps={HV_EPS:.0%}): {'FIRED' if stop else 'not fired'} | "
      f"SAFETY cap ({MAX_ITER} real iters): {'HIT' if cap else 'ok'}  =>  "
      f"{'STOP - close the loop, write the paper' if (stop or cap) else 'CONTINUE - loop still learning'}")