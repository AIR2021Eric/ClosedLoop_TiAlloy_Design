"""Stage-7 (v2): blind hold-out audit as importable, config-driven functions.
Row schema is a superset of the v4 CSV (adds gate_pass alias + per-row error-% cols),
so the equivalence test can subset the 8 v1 baselines and reproduce 1.87/1.00/7.20 MAEs.
"""
import numpy as np
import pandas as pd
from . import config as C
from . import composition as comp, physics, strength

BASELINES = [
    {"name": "Ti-6Al-4V (Gr5)", "family": "alpha+beta", "Ti": 90.0, "Al": 6.0, "V": 4.0,
     "rho_DS": 4.43, "YS_DS_lo": 880, "YS_DS_hi": 1100},
    {"name": "Ti-6242", "family": "near-alpha", "Ti": 86.0, "Al": 6.0, "Sn": 2.0, "Zr": 4.0, "Mo": 2.0,
     "rho_DS": 4.54, "YS_DS_lo": 900, "YS_DS_hi": 1000},
    {"name": "Ti-6246", "family": "alpha+beta", "Ti": 82.0, "Al": 6.0, "Sn": 2.0, "Zr": 4.0, "Mo": 6.0,
     "rho_DS": 4.68, "YS_DS_lo": 950, "YS_DS_hi": 1050},
    {"name": "Ti-5553", "family": "metastable-beta", "Ti": 82.0, "Al": 5.0, "V": 5.0, "Mo": 5.0, "Cr": 3.0,
     "rho_DS": 4.65, "YS_DS_lo": 1100, "YS_DS_hi": 1200},
    {"name": "Ti-10-2-3", "family": "metastable-beta", "Ti": 85.0, "Al": 3.0, "V": 10.0, "Fe": 2.0,
     "rho_DS": 4.65, "YS_DS_lo": 1100, "YS_DS_hi": 1200},
    {"name": "Ti-15-3-3-3", "family": "metastable-beta", "Ti": 76.0, "Al": 3.0, "V": 15.0, "Cr": 3.0, "Sn": 3.0,
     "rho_DS": 4.90, "YS_DS_lo": 1000, "YS_DS_hi": 1150},
    {"name": "Beta C", "family": "metastable-beta", "Ti": 75.0, "Al": 3.0, "V": 8.0, "Cr": 6.0, "Mo": 4.0, "Zr": 4.0,
     "rho_DS": 4.95, "YS_DS_lo": 1100, "YS_DS_hi": 1250},
    {"name": "CP-Ti (Gr2)", "family": "cp", "Ti": 100.0,
     "rho_DS": 4.51, "YS_DS_lo": 275, "YS_DS_hi": 345},
] + C.AUDIT_EXTRA   # [v2] Nb-bearing aerospace anchors from config


def run_audit():
    """Returns (rows_df, summary_mae_dict). summary keys: rho_raw, rho_corr, ys (all rows)."""
    df = pd.DataFrame(BASELINES)
    rows, mae = [], {"rho_raw": [], "rho_corr": [], "ys": []}
    for _, r in df.iterrows():
        wt = {el: float(r[el]) for el in C.PALETTE if el in r and pd.notna(r[el])}
        g = physics.gate_report(wt)
        at = comp.wt_to_at(wt)
        c = 1.0 - at["Ti"] / 100.0
        rho_raw = physics.density(wt)
        rho_cor = physics.density_calibrated(wt)
        scen = "A_unaged" if r["family"] == "cp" else C.FITNESS_SCENARIO
        ys = strength.sigma_y(c, r["family"], scen, 10.0)
        ymid = (r.YS_DS_lo + r.YS_DS_hi) / 2.0
        re_raw = (rho_raw - r.rho_DS) / r.rho_DS * 100.0
        re_cor = (rho_cor - r.rho_DS) / r.rho_DS * 100.0
        ye = (ys - ymid) / ymid * 100.0
        mae["rho_raw"].append(abs(re_raw))
        mae["rho_corr"].append(abs(re_cor))
        mae["ys"].append(abs(ye))
        rows.append({**r.to_dict(), **g, "gate_pass": g["pass"],
                     "c_solute_at": round(c, 3),
                     "rho_calc": round(rho_raw, 3), "rho_err_pct": round(re_raw, 2),
                     "rho_corr": round(rho_cor, 3), "rho_corr_err_pct": round(re_cor, 2),
                     "YS_calc": round(ys, 0), "YS_DS_mid": ymid, "YS_err_pct": round(ye, 1)})
    out = pd.DataFrame(rows)
    summary = {k: round(float(np.mean(v)), 2) for k, v in mae.items()}
    return out, summary