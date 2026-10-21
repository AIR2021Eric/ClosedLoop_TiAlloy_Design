"""Stage 4 UQ v4-tier: seed x strain-step ensemble -> uncertainty-aware stability classes.
Tier-aware engine for the closed loop (Stage 8):
  --tier S|F|U    override SEEDS/DELTAS from framework.config.TIERS
  --run-id X      isolate outputs to stage4_uq_{raw,bands}_X.csv (v1 archive untouched)
  --input-csv P   evaluate formulas in P (columns: formula[,phase_field])
Default run (no args) == v3 behavior on the Pareto 8 (resume-safe, aggregation-only now).
Classes: viol_frac > 0.5 UNSTABLE_0K | > 0.2 MARGINAL | else STABLE_SOFT.
NOTE: tier S/F classes are PROVISIONAL (1 or 3 runs); only tier U certifies archive class.
"""
import re, zlib, argparse
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
from ase.build import bulk
from ase.neighborlist import neighbor_list
from ase.optimize import BFGS
from chgnet.model.dynamics import CHGNetCalculator

REPO = Path(__file__).resolve().parents[1]
DATA, ARCH = REPO / "data", REPO / "results_archive"

_ap = argparse.ArgumentParser(description="Stage-4 ensemble UQ (tier-aware)")
_ap.add_argument("--input-csv", default=None)
_ap.add_argument("--tier", default=None, choices=["S", "F", "U"])
_ap.add_argument("--run-id", default="manual")
_args, _ = _ap.parse_known_args()

if _args.run_id != "manual":
    RAW = DATA / f"stage4_uq_raw_{_args.run_id}.csv"
    OUT = DATA / f"stage4_uq_bands_{_args.run_id}.csv"
else:
    RAW, OUT = DATA / "stage4_uq_raw.csv", DATA / "stage4_uq_bands.csv"

SEEDS  = [42, 7, 123]
DELTAS = [0.010, 0.015, 0.020]
if _args.tier:
    import sys as _sys
    _sys.path.insert(0, str(REPO))
    from framework import config as _C
    SEEDS  = list(_C.TIERS[_args.tier]["seeds"])
    DELTAS = list(_C.TIERS[_args.tier]["deltas"])

N_CELL = 54
EV_A3_TO_GPA = 160.21766208
VIOL_UNSTABLE, VIOL_MARGINAL = 0.5, 0.2

COLS = ["formula", "phase_field", "seed", "delta", "sro", "e_atom",
        "C11", "C12", "C44", "K", "G", "E", "max_disp_A", "n_disp_gt_0p3"]

# ---------------- structure + elasticity helpers ----------------
def build_supercell(counts, phase_field, rng):
    if phase_field in ("alpha+beta", "near-alpha"):
        base = bulk('Ti', 'hcp', a=2.95, c=4.68).repeat((3, 3, 3))
    else:
        base = bulk('Ti', 'bcc', a=3.30, cubic=True).repeat((3, 3, 3))
    syms = [el for el, n in counts.items() for _ in range(n)]
    rng.shuffle(syms)
    atoms = base.copy(); atoms.set_chemical_symbols(syms)
    return atoms

def sro_objective(atoms, conc, cutoff=3.5):
    i, j = neighbor_list('ij', atoms, cutoff)
    s = np.array(atoms.get_chemical_symbols()); val = 0.0
    for a in conc:
        ma = s[i] == a; n_a = ma.sum()
        if n_a == 0: continue
        for b in conc:
            p_ab = ((s[j] == b) & ma).sum() / n_a
            val += conc[a] * conc[b] * (1.0 - p_ab / conc[b]) ** 2
    return val

def mc_sqs(atoms, counts, rng, steps=4000):
    conc = {k: v / sum(counts.values()) for k, v in counts.items()}
    syms = np.array(atoms.get_chemical_symbols()); cur = sro_objective(atoms, conc)
    for _ in range(steps):
        p, q = rng.choice(len(syms), 2, replace=False)
        if syms[p] == syms[q]: continue
        syms[[p, q]] = syms[[q, p]]; atoms.set_chemical_symbols(syms.tolist())
        new = sro_objective(atoms, conc)
        if new <= cur: cur = new
        else: syms[[p, q]] = syms[[q, p]]; atoms.set_chemical_symbols(syms.tolist())
    return atoms, cur

def basin_diag(ideal, relaxed):
    d = relaxed.get_scaled_positions() - ideal.get_scaled_positions()
    d -= np.round(d)
    cart = d @ np.array(relaxed.cell)
    norms = np.linalg.norm(cart, axis=1)
    return float(norms.max()), int((norms > 0.3).sum())

def voigt_strain(g):
    return np.array([[g[0], g[5]/2, g[4]/2],
                     [g[5]/2, g[1], g[3]/2],
                     [g[4]/2, g[3]/2, g[2]]])

def strain_energy(atoms0, calc, g, fmax=0.01):
    a = atoms0.copy(); a.calc = calc
    a.set_cell(np.dot(a.cell, (np.eye(3) + voigt_strain(g)).T), scale_atoms=True)
    BFGS(a, logfile=None).run(fmax=fmax, steps=300)
    return a.get_potential_energy()

def elastic_constants(atoms0, calc, delta):
    V = atoms0.get_volume()
    E0 = strain_energy(atoms0, calc, np.zeros(6))
    def u(g): return (strain_energy(atoms0, calc, g) + strain_energy(atoms0, calc, -g) - 2*E0) / 2.0
    U = {i: u(np.eye(6)[i] * delta) for i in range(6)}
    C = np.zeros((6, 6))
    for i in range(6): C[i, i] = 2 * U[i] / (V * delta**2)
    for i, j in [(0, 1), (0, 2), (1, 2)]:
        g = np.eye(6)[i] * delta + np.eye(6)[j] * delta
        C[i, j] = C[j, i] = (u(g) - U[i] - U[j]) / (V * delta**2)
    return C * EV_A3_TO_GPA

def vrh(C):
    KV = (C[0,0]+C[1,1]+C[2,2] + 2*(C[0,1]+C[0,2]+C[1,2])) / 9
    GV = (C[0,0]+C[1,1]+C[2,2] - (C[0,1]+C[0,2]+C[1,2]) + 3*(C[3,3]+C[4,4]+C[5,5])) / 15
    try:
        S = np.linalg.inv(C)
        KR = 1.0 / (S[0,0]+S[1,1]+S[2,2] + 2*(S[0,1]+S[0,2]+S[1,2]))
        GR = 15.0 / (4*(S[0,0]+S[1,1]+S[2,2]) - 4*(S[0,1]+S[0,2]+S[1,2]) + 3*(S[3,3]+S[4,4]+S[5,5]))
        K, G = (KV+KR)/2, (GV+GR)/2
    except np.linalg.LinAlgError:
        # [v4.1] Degenerate finite-difference stiffness (collapsed / pathological relaxation):
        # Reuss compliance undefined -> Voigt-only fallback so screening survives.
        # Such runs almost always also carry C44<0 or C11-C12<0 and are vetoed by the Born gate.
        K, G = KV, GV
    denom = 3*K + G
    E = 9*K*G/denom if denom != 0 else np.nan
    return K, G, E

# ---------------- inputs + resume ----------------
rho = pd.read_csv(DATA / "stage2_gated_all.csv").set_index("formula")["rho_proxy"]
if _args.input_csv:
    df = pd.read_csv(_args.input_csv)
    if "phase_field" not in df.columns:
        pf = pd.read_csv(DATA / "stage3_tier2_phase_gates.csv")[["formula", "phase_field"]].set_index("formula")
        df = df.join(pf, on="formula")
    df = df.dropna(subset=["phase_field"]).reset_index(drop=True)
else:
    df_p = pd.read_csv(DATA / "pareto_front_current.csv")
    pf = pd.read_csv(DATA / "stage3_tier2_phase_gates.csv")[["formula", "phase_field"]].set_index("formula")
    df = df_p.join(pf, on="formula").dropna(subset=["phase_field"])

buf = pd.read_csv(RAW) if RAW.exists() else pd.DataFrame(columns=COLS)
for c in ["max_disp_A", "n_disp_gt_0p3"]:
    if c not in buf.columns: buf[c] = np.nan
done = {(r.formula, int(r.seed), float(r.delta)) for r in buf.itertuples()}
todo = [(r.formula, s, d) for _, r in df.iterrows() for s in SEEDS for d in DELTAS
        if (r.formula, s, d) not in done]
print(f"[run-id={_args.run_id} tier={_args.tier or 'manual'}] "
      f"Completed combos: {len(done)} | remaining: {len(todo)} "
      f"({'aggregation only - no GPU needed' if not todo else f'~{len(todo)*19} strained relaxations'})")

# ---------------- GPU sweep (skipped when all combos exist) ----------------
if todo:
    try:    calc = CHGNetCalculator(use_device='cuda')
    except Exception: calc = CHGNetCalculator(use_device='cpu')
    for _, r in df.iterrows():
        formula, phase = r.formula, r.phase_field
        comp = {el: float(n) for el, n in re.findall(r'([A-Z][a-z]?)([\d\.]+)', formula)}
        tot = sum(comp.values())
        counts = {el: max(1, int(round(n / tot * N_CELL))) for el, n in comp.items()}
        counts[max(counts, key=counts.get)] += N_CELL - sum(counts.values())
        for seed in SEEDS:
            if all((formula, seed, d) in done for d in DELTAS): continue
            rng = np.random.default_rng([seed, zlib.crc32(formula.encode())])
            atoms, sro = mc_sqs(build_supercell(counts, phase, rng), counts, rng)
            ideal = atoms.copy()
            atoms.calc = calc
            BFGS(atoms, logfile=None).run(fmax=0.05, steps=300)
            e_atom = atoms.get_potential_energy() / len(atoms)
            mx, nd = basin_diag(ideal, atoms)
            for delta in DELTAS:
                if (formula, seed, delta) in done: continue
                C = elastic_constants(atoms, calc, delta)
                K, G, E = vrh(C)
                buf = pd.concat([buf, pd.DataFrame([{
                    "formula": formula, "phase_field": phase, "seed": seed, "delta": delta,
                    "sro": round(sro, 6), "e_atom": round(e_atom, 4),
                    "C11": round(C[0,0], 1), "C12": round(C[0,1], 1), "C44": round(C[3,3], 1),
                    "K": round(K, 1), "G": round(G, 1), "E": round(E, 1),
                    "max_disp_A": round(mx, 3), "n_disp_gt_0p3": nd}])], ignore_index=True)
                buf.to_csv(RAW, index=False)
                print(f"  {formula} seed={seed} d={delta:.3f}: C44={C[3,3]:7.1f} "
                      f"C11-C12={C[0,0]-C[0,1]:7.1f} E={E:8.1f} maxdisp={mx:.2f}A")

# ---------------- ensemble aggregation ----------------
raw = buf.copy(); raw["C11mC12"] = raw.C11 - raw.C12
rows = []
for formula, g in raw.groupby("formula"):
    viol = float(((g.C44 < 0) | (g.C11mC12 < 0)).mean())
    cls = ("UNSTABLE_0K" if viol > VIOL_UNSTABLE
           else "MARGINAL" if viol > VIOL_MARGINAL else "STABLE_SOFT")
    if formula in rho.index:
        rh = float(rho[formula])
    else:                                   # novel loop composition: compute rho from chemistry
        import sys as _s; _s.path.insert(0, str(REPO))
        from framework import composition as _cc, physics as _ph
        rh = round(_ph.density(_cc.at_to_wt(_cc.parse_formula(formula))), 3)
    rows.append({
        "formula": formula, "phase_field": g.phase_field.iloc[0], "n_runs": len(g),
        "viol_frac": round(viol, 2), "stability_class": cls, "cls": cls,
        "C44_med": round(g.C44.median(), 1),
        "C44_iqr": round(g.C44.quantile(.75) - g.C44.quantile(.25), 1),
        "C44_mean": round(g.C44.mean(), 1), "C44_sd": round(g.C44.std(), 1),
        "C44_lo95": round(g.C44.mean() - 2*g.C44.std(), 1),
        "C44_hi95": round(g.C44.mean() + 2*g.C44.std(), 1),
        "C11mC12_med": round(g.C11mC12.median(), 1),
        "C11mC12_iqr": round(g.C11mC12.quantile(.75) - g.C11mC12.quantile(.25), 1),
        "C11mC12_mean": round(g.C11mC12.mean(), 1), "C11mC12_sd": round(g.C11mC12.std(), 1),
        "E_med": round(g.E.median(), 1),
        "E_iqr": round(g.E.quantile(.75) - g.E.quantile(.25), 1),
        "E_mean": round(g.E.mean(), 1), "E_sd": round(g.E.std(), 1),
        "K_med": round(g.K.median(), 1), "G_med": round(g.G.median(), 1),
        "rho": rh,
        "spec_stiff_med": round(g.E.median() / rh, 2) if rh == rh else np.nan,
        "spec_stiff_iqr": round((g.E.quantile(.75) - g.E.quantile(.25)) / rh, 2) if rh == rh else np.nan,
        "seed_sd_C44": round(float(g.groupby("seed").C44.mean().std()), 1),
        "delta_sd_C44": round(float(g.groupby("delta").C44.mean().std()), 1),
        "max_disp_med": round(g.max_disp_A.median(), 2) if g.max_disp_A.notna().any() else np.nan,
    })
bands = pd.DataFrame(rows).sort_values(["stability_class", "viol_frac"], ascending=[True, False])
bands.to_csv(OUT, index=False)
print(f"\n[Saved] {OUT}  (canonical stats for run-id={_args.run_id})")
print(bands[["formula", "phase_field", "viol_frac", "C44_med", "C44_iqr", "C11mC12_med",
             "E_med", "E_iqr", "spec_stiff_med", "seed_sd_C44", "delta_sd_C44",
             "stability_class"]].to_string(index=False))

# ---------------- plots (skip for thin tier runs) ----------------
if raw.groupby("formula").size().min() >= 5:
    cols = {"STABLE_SOFT": "#2ca02c", "MARGINAL": "#ff7f0e", "UNSTABLE_0K": "#d62728"}
    x = np.arange(len(bands)); labs = bands.formula.tolist()
    fig, axs = plt.subplots(1, 3, figsize=(19, 5.6))
    axs[0].bar(x, bands.viol_frac, color=[cols[c] for c in bands.stability_class])
    axs[0].axhline(VIOL_UNSTABLE, color='k', ls='--', lw=1)
    axs[0].axhline(VIOL_MARGINAL, color='k', ls=':', lw=1)
    axs[0].set_ylabel("fraction of runs violating Born criteria"); axs[0].set_ylim(0, 1.05)
    axs[0].set_title("Ensemble Born-violation fraction\n(dashed=0.5 UNSTABLE, dotted=0.2 MARGINAL)")
    data_c44 = [raw[raw.formula == f].C44.values for f in labs]
    bp1 = axs[1].boxplot(data_c44, positions=x, showfliers=True, patch_artist=True, widths=0.6)
    for patch, c in zip(bp1["boxes"], [cols[c] for c in bands.stability_class]): patch.set_facecolor(c)
    axs[1].axhline(0, color='k', lw=1); axs[1].set_ylabel("C44 (GPa)")
    axs[1].set_title("C44 ensemble"); axs[1].set_xlim(-0.7, len(bands) - 0.3)
    data_e = [raw[raw.formula == f].E.values for f in labs]
    bp2 = axs[2].boxplot(data_e, positions=x, showfliers=True, patch_artist=True, widths=0.6)
    for patch, c in zip(bp2["boxes"], [cols[c] for c in bands.stability_class]): patch.set_facecolor(c)
    axs[2].axhline(0, color='k', lw=1); axs[2].set_ylabel("E (GPa)")
    axs[2].set_title("Young's modulus ensemble"); axs[2].set_xlim(-0.7, len(bands) - 0.3)
    for ax in axs:
        ax.set_xticks(x); ax.set_xticklabels(labs, rotation=45, ha='right', fontsize=8)
        ax.grid(ls='--', alpha=.5)
    fig.suptitle(f"Stage-4 UQ (run-id={_args.run_id}, tier={_args.tier or 'manual'}): "
                 f"green=STABLE_SOFT, orange=MARGINAL, red=UNSTABLE_0K", fontweight='bold')
    plt.tight_layout()
    png = ARCH / f"slide_stage4_uq_{_args.run_id}.png"
    plt.savefig(png, dpi=300, bbox_inches='tight')
    print(f"[Saved] {png}")
else:
    print("[figure skipped: tier run with <5 runs per formula]")