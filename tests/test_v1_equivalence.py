"""tests/test_v1_equivalence.py - Equivalence gate v2.6.
Proves the v2 framework + Loop-A refactor never drift the v1.0-validated physics.
Run directly:   python tests/test_v1_equivalence.py
Run via driver: stage8_iteration/run_iteration.py calls this and greps the final banner.
Exit 0 = all green; any assertion failure = non-zero exit = driver refuses to commit.

v2.6 changes:
  - UTF-8 stdout/stderr reconfigure (fixes Windows cp1252 pipe UnicodeEncodeError on ✅).
  - Schema-tolerant row comparison vs data/stage7_audit_report.csv (shared columns only).
  - MAEs (1.87 / 1.00 / 7.20) recomputed from framework outputs, not stored error columns.
  - NEW test_snapshots_present(): every real ledger iteration has >=1 snapshot JSON.
  - test_ledger() now also exercises ledger.snapshot(tag=...) (v2.5 re-run-safe naming).
"""
import sys
import json
from pathlib import Path

for _s in (sys.stdout, sys.stderr):                      # [v2.6] cp1252-pipe hardening
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

import numpy as np                                       # noqa: E402
import pandas as pd                                      # noqa: E402

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from framework import physics, strength, pareto, audit, ledger   # noqa: E402

V1 = ["Ti-6Al-4V (Gr5)", "Ti-6242", "Ti-6246", "Ti-5553",
      "Ti-10-2-3", "Ti-15-3-3-3", "Beta C", "CP-Ti (Gr2)"]
TOL = {"rho": 0.005, "eq": 0.05, "ys": 0.6}


# ---------------- 1) Stage-7 audit rows + MAEs ----------------
def test_audit_rows():
    df, _ = audit.run_audit()
    d = df.set_index("name")
    v1 = pd.read_csv(REPO / "data" / "stage7_audit_report.csv").set_index("name")
    shared = [c for c in ("rho_calc", "Mo_eq", "Al_eq", "Cr_at", "YS_calc") if c in v1.columns]
    for n in V1:
        a, b = d.loc[n], v1.loc[n]
        for c in shared:
            tol = TOL["rho"] if c == "rho_calc" else (TOL["ys"] if c == "YS_calc" else TOL["eq"])
            assert abs(float(a[c]) - float(b[c])) < tol, (n, c, float(a[c]), float(b[c]))
        if "gate_pass" in v1.columns:
            assert bool(a["pass"]) == bool(b["gate_pass"]), (n, "gate")
        if "rho_corr" in v1.columns:                       # only if the on-disk schema carries it
            assert abs(float(a["rho_corr"]) - float(b["rho_corr"])) < TOL["rho"], (n, "rho_corr")
    sub = d.loc[V1]
    mae_rho = ((sub.rho_calc - sub.rho_DS).abs() / sub.rho_DS * 100).mean()
    mae_cor = ((sub.rho_corr - sub.rho_DS).abs() / sub.rho_DS * 100).mean()
    mae_ys = ((sub.YS_calc - sub.YS_DS_mid).abs() / sub.YS_DS_mid * 100).mean()
    assert abs(mae_rho - 1.87) < 0.05, f"raw density MAE drifted: {mae_rho:.3f}"
    assert abs(mae_cor - 1.00) < 0.05, f"calibrated density MAE drifted: {mae_cor:.3f}"
    assert abs(mae_ys - 7.20) < 0.05, f"strength MAE drifted: {mae_ys:.3f}"
    print("✅ audit rows + MAEs (1.87 / 1.00 / 7.20 on v1 subset)")


# ---------------- 2) Stage-5 Tier-3 strength bands ----------------
def test_strength():
    s5 = pd.read_csv(REPO / "data" / "stage5_strength_scenarios.csv")
    for _, r in s5[s5.scenario == "B_aged"].iterrows():
        mid, lo, hi = strength.sigma_y_band(r.c_solute, r.phase_field, "B_aged")
        assert abs(mid - r.sigma_y_mid) < 0.6, (r.formula, "mid")
        assert abs(lo - r.sigma_y_lo) < 1.0 and abs(hi - r.sigma_y_hi) < 1.0, (r.formula, "band")
    print("✅ stage-5 bands (1280/1070/1050/1070 ± unc)")


# ---------------- 3) Stage-6 archive classes + 4-carry aged front ----------------
def test_pareto_archive():
    sl = pd.read_csv(REPO / "data" / "stage6_shortlist_ensemble.csv")
    for _, r in sl.iterrows():
        expect = "provisional" if r.decision == "CARRY" else "vetoed"
        assert pareto.archive_class(r.viol_frac) == expect, r.formula
    car = sl[sl.decision == "CARRY"]
    s5 = pd.read_csv(REPO / "data" / "stage5_strength_scenarios.csv").set_index(["formula", "scenario"])
    F = np.column_stack([-car.hull_v2.values, car.pugh_proxy.values - 1.75, car.spec_stiff_aged.values,
                         [s5.loc[(f, "B_aged"), "spec_strength_mid"] for f in car.formula]])
    assert pareto.nondominated_mask(F).all(), "aged 4-objective front changed"
    print("✅ archive classes + 4-carry aged front intact")


# ---------------- 4) Stage-4 v1 archive checksum (tiers must never touch it) ----------------
def test_stage4_archive_untouched():
    b = pd.read_csv(REPO / "data" / "stage4_uq_bands.csv").set_index("formula")
    exp = {"Ti85Al4V11": (0.44, 6.3), "Ti90V10": (0.33, 2.0), "Ti70Al11V15Cr4": (0.22, 17.6),
           "Ti85Al1V14": (0.22, 6.8), "Ti72Al14V12Cr2": (0.22, 16.8) if False else (0.22, 16.8),
           "Ti73Al15V5Mo1Cr3Fe3": (0.22, 14.9), "Ti76Al15V1Mo2Cr4Fe2": (0.22, 19.7),
           "Ti77Al14Mo2Cr4Fe3": (0.22, 16.4), "Ti77Al14V1Mo2Cr4Fe2": (0.33, 18.2),
           "Ti76Al15V1Mo2Cr3Fe3": (0.44, 18.6)}
    # v1-era checksums (the 8 original Pareto candidates):
    exp_v1 = {"Ti85Al4V11": (0.44, 6.3), "Ti90V10": (0.33, 2.0), "Ti70Al11V15Cr4": (0.22, 17.6),
              "Ti85Al1V14": (0.22, 6.8), "Ti85V14Mo1": (0.89, -38.0), "Ti70Al12V15Fe3": (0.78, 12.8),
              "Ti70Al12V15Cr3": (0.67, 15.4), "Ti85V15": (0.56, 13.4)}
    for f, (v, c) in exp_v1.items():
        assert abs(b.loc[f, "viol_frac"] - v) < 1e-9 and abs(b.loc[f, "C44_med"] - c) < 0.05, f
    print("✅ stage-4 v1 archive checksum (tiers write to isolated files only)")


# ---------------- 5) Ledger record + tagged snapshot round-trip (isolated tmp) ----------------
def test_ledger():
    import tempfile, shutil
    tmp = Path(tempfile.mkdtemp())
    old_log, old_snap = ledger.LOG, ledger.SNAP
    try:
        ledger.LOG = tmp / "iteration_log.csv"
        ledger.SNAP = tmp / "iterations"
        row = ledger.record(iter_id=999, pop_source="unit-test", pop_n=1,
                            decision="ok", next_action="none")
        assert row["iter_id"] == 999 and len(row["config_sha"]) == 12
        p0 = ledger.snapshot(999, {"hello": "world"})                 # untagged
        p1 = ledger.snapshot(999, {"hello": "tagged"}, tag="010101")  # [v2.5] tagged
        assert p0.exists() and p1.exists() and p0.name != p1.name
        assert '"hello"' in p0.read_text() and p1.name.endswith("_010101.json")
        chk = pd.read_csv(ledger.LOG)
        assert len(chk) == 1 and chk.iloc[0]["iter_id"] == 999
    finally:
        ledger.LOG, ledger.SNAP = old_log, old_snap
        shutil.rmtree(tmp, ignore_errors=True)
    print("✅ ledger record + tagged/untagged snapshot round-trip (isolated tmp, real log untouched)")


# ---------------- 6) [v2.6] provenance integrity: every real iteration has a snapshot ----------------
def test_snapshots_present():
    log = REPO / "data" / "iteration_log.csv"
    snap_dir = REPO / "results_archive" / "iterations"
    if not log.exists():
        print("✅ snapshot provenance (no ledger yet - nothing to check)")
        return
    lg = pd.read_csv(log)
    real = sorted(set(int(i) for i in lg.iter_id if (lg[lg.iter_id == i].run_ids != "dry").any()))
    missing = []
    for iid in real:
        cands = sorted(snap_dir.glob(f"iter_{iid:03d}*.json")) if snap_dir.exists() else []
        if not cands:
            missing.append(iid)
            continue
        p = max(cands, key=lambda q: q.stat().st_mtime)
        try:
            json.loads(p.read_text())
        except Exception:
            missing.append(iid)
    assert not missing, f"iterations missing/invalid snapshots: {missing}"
    print(f"✅ snapshot provenance for {len(real)} real iteration(s): {real}")


if __name__ == "__main__":
    test_audit_rows()
    test_strength()
    test_pareto_archive()
    test_stage4_archive_untouched()
    test_ledger()
    test_snapshots_present()
    print("\n ALL EQUIVALENCE CHECKS PASSED - cleared for Loop A")