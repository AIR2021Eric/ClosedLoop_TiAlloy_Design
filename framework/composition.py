"""Composition codec: formula <-> at% vector over C.PALETTE; wt<->at; caps."""
import re
import numpy as np
from . import config as C

def parse_formula(formula):
    raw = {el: float(n) for el, n in re.findall(r'([A-Z][a-z]?)([\d\.]+)', formula)}
    return {el: raw.get(el, 0.0) for el in C.PALETTE}

def at_vector(formula):
    return np.array([parse_formula(formula)[el] for el in C.PALETTE])

def to_formula(vec):
    return "".join(f"{el}{int(round(v))}" for el, v in zip(C.PALETTE, vec) if round(v) > 0)

def at_to_wt(at):
    mass = {el: at.get(el, 0.0) * C.M[el] for el in C.PALETTE}
    tot = sum(mass.values())
    return {el: 100.0 * mass[el] / tot for el in C.PALETTE}

def wt_to_at(wt):
    mol = {el: wt.get(el, 0.0) / C.M[el] for el in C.PALETTE}
    tot = sum(mol.values())
    return {el: 100.0 * mol[el] / tot for el in C.PALETTE}

def caps_ok(at):
    if at.get("Ti", 0.0) < C.CAPS_AT["Ti_min"]:
        return False, "Ti_min"
    for el, cap in C.CAPS_AT.items():
        if el != "Ti_min" and at.get(el, 0.0) > cap:
            return False, el
    return True, ""