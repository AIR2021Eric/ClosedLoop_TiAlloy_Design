"""Stage-1 (v2): proposal utilities for the closed loop.
Gen-0 seed = archived Tier-2 survivors + provisional carries.
mutate/crossover/repair keep every proposal inside caps and sum-to-100 at%."""
import numpy as np
import pandas as pd
from . import config as C
from . import composition as comp

def seed_population(survivors_csv=None, shortlist_csv=None):
    surv = pd.read_csv(survivors_csv or (C.DATA / "stage3_survivors.csv"))
    car = pd.read_csv(shortlist_csv or (C.DATA / "stage6_shortlist_ensemble.csv"))
    formulas = list(dict.fromkeys(list(surv.formula) + list(car[car.decision == "CARRY"].formula)))
    return [comp.at_vector(f) for f in formulas], formulas

def repair(vec):
    """Integer at%, element caps, Ti floor, exact sum = 100."""
    v = np.clip(np.round(np.asarray(vec, dtype=float)), 0, 100).astype(int)
    ti = C.PALETTE.index("Ti")
    others = [i for i in range(len(C.PALETTE)) if i != ti]
    for i in others:
        v[i] = min(v[i], int(C.CAPS_AT.get(C.PALETTE[i], 100)))
    max_others = 100 - int(C.CAPS_AT["Ti_min"])
    s = v[others].sum()
    if s > max_others:
        v[others] = np.floor(v[others] * (max_others / s)).astype(int)
    v[ti] = 100 - v[others].sum()
    return v

def mutate(vec, sigma=2.0, rng=None):
    rng = rng or np.random.default_rng()
    return repair(vec.astype(float) + rng.normal(0.0, sigma, len(vec)))

def crossover(a, b, rng=None):
    rng = rng or np.random.default_rng()
    mask = rng.random(len(a)) < 0.5
    return repair(np.where(mask, a, b).astype(float))