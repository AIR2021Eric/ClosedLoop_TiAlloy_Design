"""Stage-2/3 fast physics: Mo_eq / Al_eq / density / phase field / full-stack gates."""
from . import config as C
from . import composition as comp

def moeq_aleq(wt):
    mo = sum(wt.get(el, 0.0) * k for el, k in C.MOEQ_COEF.items())
    al = sum(wt.get(el, 0.0) * k for el, k in C.ALEQ_COEF.items())
    return mo, al

def phase_field(mo_eq):
    if mo_eq < 2:  return "near-alpha"
    if mo_eq < 10: return "alpha+beta"
    return "metastable-beta"

def density(wt):
    inv = sum(wt[el] / 100.0 / C.RHO_EL[el] for el in wt if wt[el] > 0)
    return 1.0 / inv

def density_calibrated(wt):
    return density(wt) * C.RHO_CALIB_FACTOR

def gate_report(wt):
    """Full Stage-2/3 gate stack on a wt% dict -> dict usable by loop and audit."""
    mo, al = moeq_aleq(wt)
    at = comp.wt_to_at(wt)
    ok, why = comp.caps_ok(at)
    reasons = [] if ok else [f"cap_{why}"]
    if mo > C.MOEQ_MAX: reasons.append("Mo_eq")
    if al > C.ALEQ_MAX: reasons.append("Al_eq")
    return {"Mo_eq": round(mo, 2), "Al_eq": round(al, 2), "Cr_at": round(at["Cr"], 2),
            "pass": not reasons, "reasons": reasons, "phase_field": phase_field(mo)}