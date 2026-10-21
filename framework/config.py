"""framework/config.py - SINGLE SOURCE OF TRUTH for the closed-loop framework (v2).
All stages and the Loop import policy from here; never hard-code constants in stage code.
v1.0-validated values frozen by git tag v1.0-validated; [v2] = Stage-8 additions.
"""
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DATA = REPO / "data"
ARCH = REPO / "results_archive"

# ---------------- palette & element tables ----------------
PALETTE = ["Ti", "Al", "V", "Mo", "Zr", "Sn", "Cr", "Fe", "Nb"]      # [v2] +Nb (Ta/Si deferred)
M = {"Ti": 47.867, "Al": 26.982, "V": 50.942, "Mo": 95.95, "Zr": 91.224,
     "Sn": 118.71, "Cr": 51.996, "Fe": 55.845, "Nb": 92.906, "Si": 28.085}
RHO_EL = {"Ti": 4.51, "Al": 2.70, "V": 6.11, "Mo": 10.22, "Zr": 6.52,
          "Sn": 7.28, "Cr": 7.19, "Fe": 7.87, "Nb": 8.57, "Si": 2.33}
# [v2] elemental shear moduli (GPa) and metallic radii (pm) for misfit / G_rm descriptors
EL_G = {"Ti": 44.0, "Al": 26.0, "V": 47.0, "Mo": 94.0, "Zr": 33.0,
        "Sn": 18.0, "Cr": 94.0, "Fe": 82.0, "Nb": 38.0}
EL_R = {"Ti": 147.0, "Al": 143.0, "V": 135.0, "Mo": 139.0, "Zr": 160.0,
        "Sn": 140.0, "Cr": 128.0, "Fe": 126.0, "Nb": 146.0}
# [v2] elemental bulk moduli (GPa) -> composition-only E_proxy = 9 K_rm G_rm /(3 K_rm + G_rm)
EL_K = {"Ti": 110.0, "Al": 76.0, "V": 160.0, "Mo": 177.0, "Zr": 95.0,
        "Sn": 58.0, "Cr": 184.0, "Fe": 165.0, "Nb": 170.0}

# ---------------- composition caps (at%) ----------------
# [v2] added explicit caps on the strong stabilizers so NSGA-II cannot propose absurd cells
CAPS_AT = {"Ti_min": 50.0, "Al": 15.0, "V": 25.0, "Mo": 25.0,
           "Zr": 10.0, "Sn": 6.0, "Cr": 4.0, "Fe": 5.0, "Nb": 20.0}

# ---------------- Stage-3 equivalents (wt%) ----------------
MOEQ_COEF = {"Mo": 1.0, "Nb": 1/3.4, "V": 1/1.5, "Cr": 1/1.25, "Fe": 1/1.25,
             "Ta": 1/1.4, "W": 1/2.5, "Mn": 1/1.6}                    # [v2] +Nb
ALEQ_COEF = {"Al": 1.0, "Sn": 1/3.0, "Zr": 1/6.0}
MOEQ_MAX, ALEQ_MAX = 16.0, 9.0

# ---------------- Stage-4 tiers & CHGNet budget [v2] ----------------
TIERS = {"S": {"seeds": [42],         "deltas": [0.015],                  "mace": False},
         "F": {"seeds": [42, 7, 123], "deltas": [0.015],                  "mace": True},
         "U": {"seeds": [42, 7, 123], "deltas": [0.010, 0.015, 0.020],    "mace": False}}
BUDGET = {"S": 50, "F": 10, "U": 4}
VIOL_UNSTABLE, VIOL_MARGINAL = 0.5, 0.2
ARCHIVE_CERTIFIED_MAX, ARCHIVE_PROVISIONAL_MAX = 0.20, 0.50          # [v2] dual archive

# ---------------- Stage-5 Tier-3 declared constants (v1 values) ----------------
C_REF, K_Y, D_REF_UM, B_SS, SS_EDGE = 0.10, 0.35, 10.0, 400.0, 0.20
GRAIN_UM = [1.0, 10.0, 50.0]
BASE = {("A_unaged", "alpha+beta"): 800.0,      ("B_aged", "alpha+beta"): 1050.0,
        ("A_unaged", "metastable-beta"): 850.0, ("B_aged", "metastable-beta"): 1200.0,
        ("A_unaged", "near-alpha"): 750.0,      ("B_aged", "near-alpha"): 950.0,
        ("A_unaged", "cp"): 340.0,              ("B_aged", "cp"): 450.0}
BASE_UNC = {("A_unaged", "alpha+beta"): 100.0,  ("B_aged", "alpha+beta"): 150.0,
            ("A_unaged", "metastable-beta"): 100.0, ("B_aged", "metastable-beta"): 150.0,
            ("A_unaged", "near-alpha"): 80.0,   ("B_aged", "near-alpha"): 100.0,
            ("A_unaged", "cp"): 40.0,           ("B_aged", "cp"): 60.0}
FITNESS_SCENARIO = "B_aged"                                           # frames serve aged

# ---------------- Stage-6 objectives [v2: weight-free Ashby] ----------------
ASHBY = {"strength_exp": 2/3, "stiffness_exp": 1/2}                   # sigma_y^(2/3)/rho, E^(1/2)/rho
HARD_GATES = {"pugh_min": 1.75, "hull_max": 0.05, "rho_window": (3.8, 4.8)}

# ---------------- Stage-7 audit ----------------
RHO_CALIB_FACTOR = 1.0191                                             # v1: 1/0.9813 volume contraction
AUDIT_EXTRA = [   # [v2] Nb-bearing aerospace anchor (entered without trace Si; declared)
    {"name": "beta-21S*", "family": "metastable-beta",
     "Ti": 82.0, "Mo": 15.0, "Nb": 3.0, "Al": 3.0,
     "E_DS": 106, "rho_DS": 4.90, "YS_DS_lo": 1000, "YS_DS_hi": 1150},
]   # Ti-13Nb-13Zr removed: biomedical alloy, out of aerospace-frame scope

# ---------------- GP surrogate & Loop policy [v2] ----------------
GP_DESCRIPTORS = ["Mo_eq", "Al_eq", "c_solute", "misfit_delta", "G_rm"]
GP_TARGET = "C44_med"             # GP steers queries by predicted C44 (+uncertainty)
ACQ_UCB_BETA = 2.0                # exploration/exploitation balance in the query policy
LOOP = {"pop_size": 200, "n_gen": 40, "n_proposed": 1000, "mut_sigma": 2.0}