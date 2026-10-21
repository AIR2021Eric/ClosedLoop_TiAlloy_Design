"""Stage-5 Tier-3 strength: declared constants live in config; closed-form, loop-safe."""
from . import config as C

def d_hp(d_um):
    return C.K_Y * ((d_um * 1e-6) ** -0.5 - (C.D_REF_UM * 1e-6) ** -0.5)

def sigma_y(c_solute, family, scenario=None, d_um=10.0):
    scen = scenario or C.FITNESS_SCENARIO
    base = C.BASE[(scen, family)]
    return base + C.B_SS * (c_solute - C.C_REF) + d_hp(d_um)

def sigma_y_band(c_solute, family, scenario=None):
    scen = scenario or C.FITNESS_SCENARIO
    mid = sigma_y(c_solute, family, scen, 10.0)
    unc = C.BASE_UNC[(scen, family)]
    lo = C.BASE[(scen, family)] - unc + C.B_SS * (c_solute - C.C_REF) + d_hp(max(C.GRAIN_UM))
    hi = C.BASE[(scen, family)] + unc + C.B_SS * (c_solute - C.C_REF) + d_hp(min(C.GRAIN_UM))
    return mid, lo, hi

def ss_edge_flag(c_solute):
    return "SS_LINEAR_EDGE" if abs(c_solute - C.C_REF) >= C.SS_EDGE else "OK"