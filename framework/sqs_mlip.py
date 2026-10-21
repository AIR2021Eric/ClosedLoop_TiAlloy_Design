"""Stage-4 (v2): tiered CHGNet query router.
Spawns the frozen tier-aware engine with isolated raw/bands outputs per run-id,
so v1 archives are never touched. Budgets enforced from config.BUDGET."""
import subprocess, sys
import pandas as pd
from . import config as C
from . import composition as comp, physics, pareto

ENGINE = C.REPO / "stage4_mlip" / "stage4_uq_bands.py"

def phase_fields(formulas):
    out = []
    for f in formulas:
        wt = comp.at_to_wt(comp.parse_formula(f))
        out.append(physics.gate_report(wt)["phase_field"])
    return out

def query_tier(formulas, tier, run_id):
    """Evaluate formulas at tier S/F/U; returns the run's bands DataFrame."""
    formulas = list(formulas)
    assert tier in C.TIERS, f"unknown tier {tier}"
    assert len(formulas) <= C.BUDGET[tier], f"tier {tier} budget {C.BUDGET[tier]} exceeded"
    inp = C.DATA / f"tier_{tier}_{run_id}_input.csv"
    pd.DataFrame({"formula": formulas, "phase_field": phase_fields(formulas)}).to_csv(inp, index=False)
    cmd = [sys.executable, str(ENGINE), "--tier", tier, "--run-id", run_id, "--input-csv", str(inp)]
    subprocess.run(cmd, check=True, cwd=str(C.REPO))
    bands = pd.read_csv(C.DATA / f"stage4_uq_bands_{run_id}.csv")
    bands["archive_class"] = bands.viol_frac.map(pareto.archive_class)
    return bands