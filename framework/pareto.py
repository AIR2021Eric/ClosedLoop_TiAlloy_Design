"""Stage-6: exact non-dominated sort, Ashby objectives, hard gates, dual archive."""
import numpy as np
from . import config as C

def nondominated_mask(F):
    keep = np.ones(len(F), dtype=bool)
    for i in range(len(F)):
        if not keep[i]:
            continue
        dom = np.all(F[i] >= F, axis=1) & np.any(F[i] > F, axis=1)
        keep[dom] = False
    return keep

def ashby_objectives(sigma_y_aged, E_used, rho):
    """Weight-free frame indices: bending-strength and buckling mass minimizers.
    E_used = proxy/GP value for screening, CHGNet median once queried."""
    return np.column_stack([(np.maximum(sigma_y_aged, 1.0) ** (2.0/3.0)) / rho,
                            np.sqrt(np.maximum(E_used, 1.0)) / rho])

def hard_gates_ok(pugh, hull, rho):
    g = C.HARD_GATES
    return (pugh >= g["pugh_min"]) and (hull <= g["hull_max"]) \
        and (g["rho_window"][0] <= rho <= g["rho_window"][1])

def archive_class(viol_frac):
    if viol_frac < C.ARCHIVE_CERTIFIED_MAX:  return "certified"
    if viol_frac < C.ARCHIVE_PROVISIONAL_MAX: return "provisional"
    return "vetoed"

def split_archive(df):
    return {k: df[df["archive_class"] == k].copy()
            for k in ("certified", "provisional", "vetoed")}