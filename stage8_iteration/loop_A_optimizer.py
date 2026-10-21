"""Stage 8 - Loop A v2.5: closed-loop adaptive generation.
NSGA-II proposer (Ashby objectives) + GP-UCB query policy + tiered CHGNet (50/10/4)
+ dual archive + append-only ledger provenance.
[v2.5] (a) purge stale provisional rows superseded by certification;
       (b) re-run-safe snapshots via ledger tag (timestamp suffix).
Tier semantics: S(1 run)=screen only; F(3 runs)=provisional floor; U(9 runs)=certification.
"""
import sys, argparse, datetime
from pathlib import Path
import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from framework import config as C
from framework import composition as comp, physics, strength, pareto, generator, ledger, sqs_mlip

from pymoo.core.problem import Problem
from pymoo.core.repair import Repair
from pymoo.core.sampling import Sampling
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.operators.crossover.sbx import SBX
from pymoo.operators.mutation.pm import PM
from pymoo.optimize import minimize
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, WhiteKernel, ConstantKernel
from sklearn.preprocessing import StandardScaler

# ---------------- [v2.2] formula sanitizer ----------------
def _clean_formula(x):
    if x is None:
        return None
    if isinstance(x, float) and np.isnan(x):
        return None
    s = str(x).strip()
    if not s or s.lower() == "nan":
        return None
    try:
        vec = comp.at_vector(s)
        if vec.sum() <= 0:
            return None
        return comp.to_formula(vec)
    except Exception:
        return None

# ---------------- composition-only descriptor / fitness core ----------------
XL = np.zeros(len(C.PALETTE))
XU = np.array([100.0 if el == "Ti" else C.CAPS_AT.get(el, 100.0) for el in C.PALETTE])

def descriptors(vec):
    at = {el: float(v) for el, v in zip(C.PALETTE, vec)}
    wt = comp.at_to_wt(at)
    g = physics.gate_report(wt)
    rho = physics.density(wt)
    c_solute = 1.0 - at["Ti"] / 100.0
    K_rm = sum(at[el] / 100.0 * C.EL_K[el] for el in C.PALETTE if at[el] > 0)
    G_rm = sum(at[el] / 100.0 * C.EL_G[el] for el in C.PALETTE if at[el] > 0)
    E_proxy = 9.0 * K_rm * G_rm / (3.0 * K_rm + G_rm)
    r0 = C.EL_R["Ti"]
    misfit = sum(at[el] / 100.0 * ((C.EL_R[el] - r0) / r0) ** 2 for el in C.PALETTE if el != "Ti")
    sy = strength.sigma_y(c_solute, g["phase_field"], C.FITNESS_SCENARIO, 10.0)
    return {"formula": comp.to_formula(vec), "phase_field": g["phase_field"],
            "Mo_eq": g["Mo_eq"], "Al_eq": g["Al_eq"], "Cr_at": g["Cr_at"],
            "gate_inline_pass": g["pass"], "gate_reasons": ";".join(g["reasons"]),
            "rho": round(rho, 3), "c_solute": round(c_solute, 3),
            "E_proxy": round(E_proxy, 1), "G_rm": round(G_rm, 1),
            "misfit_delta": round(misfit, 4), "sigma_y_aged": round(sy, 0),
            "ashby_strength": round(sy ** C.ASHBY["strength_exp"] / rho, 2),
            "ashby_stiffness": round(np.sqrt(E_proxy) / rho, 3)}

def inline_constraints(d):
    lo, hi = C.HARD_GATES["rho_window"]
    return np.array([lo - d["rho"], d["rho"] - hi,
                     d["Mo_eq"] - C.MOEQ_MAX, d["Al_eq"] - C.ALEQ_MAX])

class TiRepair(Repair):
    def _do(self, problem, X, **kwargs):
        return np.array([generator.repair(x) for x in X])

class FrameProblem(Problem):
    def __init__(self):
        super().__init__(n_var=len(C.PALETTE), n_obj=2, n_ieq_constr=4, xl=XL, xu=XU)
    def _evaluate(self, X, out, *args, **kwargs):
        F, G = [], []
        for x in X:
            d = descriptors(generator.repair(x))
            F.append([-d["ashby_strength"], -d["ashby_stiffness"]])
            G.append(inline_constraints(d))
        out["F"] = np.array(F); out["G"] = np.array(G)

# ---------------- warm-start from live archive (+ orphan recovery) ----------------
_BASE_CARRIES = ["Ti70Al11V15Cr4", "Ti85Al1V14", "Ti90V10", "Ti85Al4V11"]

def _bands_files():
    return [C.DATA / "stage4_uq_bands.csv"] + sorted(C.DATA.glob("stage4_uq_bands_*.csv"))

def _evidence_certified():
    frames = []
    for p in _bands_files():
        if p.exists():
            b = pd.read_csv(p)
            if {"n_runs", "viol_frac"} <= set(b.columns):
                frames.append(b)
    if not frames:
        return set()
    b = pd.concat(frames, ignore_index=True)
    b = b[(b.n_runs >= 9) & (b.viol_frac < C.ARCHIVE_CERTIFIED_MAX)]
    return {_clean_formula(f) for f in b.formula} - {None}

def _warm_bases():
    cert, prov = load_archive("certified"), load_archive("provisional")
    live = pd.concat([c for c in (cert, prov) if len(c)], ignore_index=True) \
        if (len(cert) or len(prov)) else pd.DataFrame()
    formulas = list(live.formula) if len(live) else []
    formulas += [f for f in _evidence_certified() if f not in set(formulas)]
    formulas = [f for f in (_clean_formula(x) for x in formulas) if f is not None]
    formulas = list(dict.fromkeys(formulas))
    if formulas:
        scored = sorted(formulas, key=lambda f: -descriptors(comp.at_vector(f))["ashby_strength"])
        return [comp.at_vector(f) for f in scored[:8]]
    return [comp.at_vector(f) for f in _BASE_CARRIES]

class WarmStartSampling(Sampling):
    def __init__(self, rng):
        super().__init__()
        self.rng = rng
    def _do(self, problem, n_samples, **kwargs):
        return warm_start(self.rng, n_samples)

def warm_start(rng, n):
    lo, hi = C.HARD_GATES["rho_window"]
    bases = _warm_bases()
    out = [b.astype(float) for b in bases]
    tries = 0
    while len(out) < n and tries < n * 200:
        tries += 1
        b = bases[rng.integers(len(bases))]
        cand = generator.repair(b + rng.normal(0.0, C.LOOP["mut_sigma"], len(b)))
        d = descriptors(cand)
        if d["gate_inline_pass"] and lo <= d["rho"] <= hi:
            out.append(cand.astype(float))
    while len(out) < n:
        out.append(bases[len(out) % len(bases)].astype(float))
    return np.array(out[:n], dtype=float)

# ---------------- pymoo 0.6.x-safe final-population extractor ----------------
def _final_X(res):
    pop = getattr(res, "pop", None)
    if pop is not None:
        try:
            X = pop.get("X")
        except Exception:
            X = getattr(pop, "X", None)
        if X is not None and len(X) > 0:
            return np.asarray(X)
    X = getattr(res, "X", None)
    if X is not None and len(X) > 0:
        return np.asarray(X)
    raise RuntimeError("NSGA-II returned no final population; check pop_size/n_gen/feasibility.")

# ---------------- CrabNet lookup (soft gates only) ----------------
def load_crabnet_lookup():
    p = C.DATA / "stage2_gated_all.csv"
    if not p.exists():
        return {}
    s = pd.read_csv(p)
    cols = {c for c in ("hull_v2", "pugh_proxy") if c in s.columns}
    return {r.formula: {c: float(getattr(r, c)) for c in cols} for r in s.itertuples()}

def apply_soft_gates(d, crab, chgnet=None):
    info = {"hull": np.nan, "hull_src": "pending", "pugh": np.nan, "pugh_src": "pending",
            "soft_pass": True, "soft_note": []}
    if chgnet is not None and not pd.isna(chgnet.get("K_med")) and not pd.isna(chgnet.get("G_med")) \
       and chgnet.get("G_med", 0) > 0:
        info["pugh"] = round(chgnet["K_med"] / chgnet["G_med"], 3); info["pugh_src"] = "chgnet"
    elif d["formula"] in crab and "pugh_proxy" in crab[d["formula"]]:
        info["pugh"] = round(crab[d["formula"]]["pugh_proxy"], 3); info["pugh_src"] = "crabnet"
    if d["formula"] in crab and "hull_v2" in crab[d["formula"]]:
        info["hull"] = round(crab[d["formula"]]["hull_v2"], 4); info["hull_src"] = "crabnet"
    if info["pugh_src"] != "pending" and info["pugh"] < C.HARD_GATES["pugh_min"]:
        info["soft_pass"] = False; info["soft_note"].append("pugh<1.75")
    if info["hull_src"] != "pending" and info["hull"] > C.HARD_GATES["hull_max"]:
        info["soft_pass"] = False; info["soft_note"].append("hull>0.05")
    return info

# ---------------- GP query policy ----------------
def collect_chgnet_training():
    frames = []
    for p in _bands_files():
        if p.exists():
            b = pd.read_csv(p)
            if "C44_med" in b.columns:
                frames.append(b)
    if not frames:
        return None
    b = pd.concat(frames, ignore_index=True).dropna(subset=["C44_med"])
    b["_f"] = b.formula.map(_clean_formula)
    b = b[b._f.notna()]
    b = b.sort_values("n_runs").drop_duplicates("_f", keep="last")
    rows = []
    for f, c44 in zip(b._f, b.C44_med):
        d = descriptors(comp.at_vector(f))
        rows.append([d[k] for k in C.GP_DESCRIPTORS] + [c44, f])
    return pd.DataFrame(rows, columns=C.GP_DESCRIPTORS + ["C44", "formula"])

def fit_gp(train):
    X = train[C.GP_DESCRIPTORS].values.astype(float)
    y = train["C44"].values.astype(float)
    scaler = StandardScaler().fit(X)
    kern = ConstantKernel(1.0) * RBF(length_scale=1.0) + WhiteKernel(noise_level=0.1)
    gp = GaussianProcessRegressor(kernel=kern, normalize_y=True, alpha=1e-6,
                                  n_restarts_optimizer=3, random_state=0).fit(scaler.transform(X), y)
    return gp, scaler

def ucb_select(pool_df, gp, scaler, n):
    if gp is None or len(pool_df) == 0 or n <= 0:
        return pool_df.sort_values("ashby_strength", ascending=False).head(max(n, 0))
    Z = scaler.transform(pool_df[C.GP_DESCRIPTORS].values.astype(float))
    mu, sd = gp.predict(Z, return_std=True)
    pool_df = pool_df.copy()
    pool_df["gp_C44_mu"] = np.round(mu, 1)
    pool_df["gp_C44_sd"] = np.round(sd, 1)
    pool_df["ucb"] = mu + C.ACQ_UCB_BETA * sd
    return pool_df.sort_values("ucb", ascending=False).head(n)

# ---------------- archive (dual) ----------------
ARC_COLS = ["formula", "phase_field", "iter_id", "evidence_runs", "viol_frac", "archive_class",
            "cls", "C44_med", "E_med", "sigma_y_aged", "E_proxy", "rho",
            "ashby_strength", "ashby_stiffness", "hull", "hull_src", "pugh", "pugh_src",
            "soft_pass", "Mo_eq", "Al_eq", "c_solute", "gate_inline_pass"]

def _arc_path(cls):
    return C.DATA / f"archive_{cls}.csv"

def load_archive(cls):
    p = _arc_path(cls)
    if not p.exists():
        return pd.DataFrame(columns=ARC_COLS)
    df = pd.read_csv(p)
    if "formula" in df.columns:
        df = df.copy()
        df["_cf"] = df.formula.map(_clean_formula)
        bad = int(df._cf.isna().sum())
        if bad:
            print(f"[warn] dropped {bad} unparseable formula rows from archive_{cls}.csv")
        df = df[df._cf.notna()]
        df["formula"] = df["_cf"]; df.drop(columns="_cf", inplace=True)
    return df.reset_index(drop=True)

def merge_archive(rows, cls):
    cur = load_archive(cls)
    new = pd.DataFrame(rows)
    if len(new):
        new = new.sort_values("evidence_runs").drop_duplicates("formula", keep="last")
        cur = pd.concat([cur, new], ignore_index=True)
        cur = cur.sort_values("evidence_runs").drop_duplicates("formula", keep="last")
    cur.to_csv(_arc_path(cls), index=False)
    return cur

def _best_bands_row(formula):
    best = None
    for p in _bands_files():
        if not p.exists():
            continue
        m = pd.read_csv(p)
        m = m[(m.formula.map(_clean_formula) == formula) & (m.n_runs >= 9)]
        if len(m):
            best = m.iloc[0]
    return best

def seed_archive_from_v1():
    p = _arc_path("provisional")
    if p.exists() and len(pd.read_csv(p)) > 0:
        return 0
    sl = C.DATA / "stage6_shortlist_ensemble.csv"
    bd = C.DATA / "stage4_uq_bands.csv"
    if not sl.exists() or not bd.exists():
        return 0
    s = pd.read_csv(sl); b = pd.read_csv(bd).set_index("formula")
    rows = []
    for _, r in s[s.decision == "CARRY"].iterrows():
        d = descriptors(comp.at_vector(r.formula))
        ev = b.loc[r.formula] if r.formula in b.index else None
        rows.append({**d, "iter_id": 0, "evidence_runs": 9,
                     "viol_frac": float(r.viol_frac),
                     "archive_class": pareto.archive_class(float(r.viol_frac)),
                     "cls": r.cls,
                     "C44_med": float(ev.C44_med) if ev is not None else np.nan,
                     "E_med": float(ev.E_med) if ev is not None else np.nan,
                     "K_med": float(ev.K_med) if ev is not None else np.nan,
                     "G_med": float(ev.G_med) if ev is not None else np.nan,
                     "hull": float(r.hull_v2), "hull_src": "crabnet",
                     "pugh": float(r.pugh_proxy), "pugh_src": "crabnet",
                     "soft_pass": True, "gate_inline_pass": True})
    if rows:
        pd.DataFrame(rows).to_csv(p, index=False)
    return len(rows)

def _rec(df):
    return df.astype(object).where(pd.notna(df), None).to_dict("records")

# ---------------- main loop ----------------
def run_iteration(iter_id, dry_run, smoke, seed):
    rng = np.random.default_rng(seed)
    pop_cfg = dict(pop_size=20, n_gen=4, n_proposed=60, mut_sigma=2.0) if smoke else \
               dict(pop_size=C.LOOP["pop_size"], n_gen=C.LOOP["n_gen"],
                    n_proposed=C.LOOP["n_proposed"], mut_sigma=C.LOOP["mut_sigma"])
    bud = dict(S=6, F=3, U=2) if smoke else dict(C.BUDGET)

    print(f"=== Loop A iteration {iter_id} | dry_run={dry_run} smoke={smoke} seed={seed} ===")
    pop, formulas = generator.seed_population()
    print(f"seed population: {len(pop)} alleles (gen-0 = v1 survivors + carries)")
    n_seed = seed_archive_from_v1()
    print(f"v1 incumbent seed -> provisional archive: {n_seed} carries (iter_id=0)")

    prob = FrameProblem()
    algo = NSGA2(pop_size=pop_cfg["pop_size"],
                 sampling=WarmStartSampling(rng),
                 crossover=SBX(prob=0.9, eta=15),
                 mutation=PM(eta=20),
                 repair=TiRepair(),
                 eliminate_duplicates=True)
    res = minimize(prob, algo, ("n_gen", pop_cfg["n_gen"]), seed=seed, verbose=False)
    X = np.array([generator.repair(x) for x in _final_X(res)])
    pool = pd.DataFrame([descriptors(x) for x in X]).drop_duplicates("formula")
    pool = pool[pool.gate_inline_pass].reset_index(drop=True)
    _lo, _hi = C.HARD_GATES["rho_window"]
    pool = pool[(pool.rho >= _lo) & (pool.rho <= _hi)].reset_index(drop=True)
    print(f"NSGA-II -> {len(pool)} inline-feasible unique proposals (after rho window)")

    known = set(load_archive("certified").formula) | set(load_archive("provisional").formula)
    pool = pool[~pool.formula.isin(known)].reset_index(drop=True)
    print(f"after de-dup vs {len(known)} known -> {len(pool)} new proposals for GPU queue")

    train = collect_chgnet_training()
    gp = scaler = None
    if train is not None and len(train) >= 2:
        gp, scaler = fit_gp(train)
        print(f"GP trained on {len(train)} CHGNet labels | descriptors={C.GP_DESCRIPTORS}")
    else:
        print("GP: <2 training labels -> falling back to ashby_strength ordering")

    crab = load_crabnet_lookup()

    s_pool = ucb_select(pool, gp, scaler, bud["S"]); s_formulas = s_pool.formula.tolist()
    bands = {}
    if not dry_run and s_formulas:
        bs = sqs_mlip.query_tier(s_formulas, "S", f"it{iter_id}S")
        for _, r in bs.iterrows(): bands[r.formula] = r.to_dict()
        s_keep = [f for f in s_formulas if bands.get(f, {}).get("C44_med", -1) > 0]
    else:
        s_keep = s_formulas[:]
    print(f"Tier-S: queried {0 if dry_run else len(s_formulas)} (dry) -> {len(s_keep)} advance")

    f_pool_df = pool[pool.formula.isin(s_keep)]
    f_sel = ucb_select(f_pool_df, gp, scaler, bud["F"]); f_formulas = f_sel.formula.tolist()
    if not dry_run and f_formulas:
        bf = sqs_mlip.query_tier(f_formulas, "F", f"it{iter_id}F")
        for _, r in bf.iterrows(): bands.setdefault(r.formula, {}).update(r.to_dict())
        f_keep = [f for f in f_formulas if bands[f].get("viol_frac", 1.0) <= C.VIOL_UNSTABLE]
    else:
        f_keep = f_formulas[:]
    print(f"Tier-F: queried {0 if dry_run else len(f_formulas)} (dry) -> {len(f_keep)} advance")

    prov0 = load_archive("provisional")
    promo = prov0[prov0.evidence_runs < 9] if len(prov0) else prov0.iloc[0:0]
    promo_df = pd.DataFrame([descriptors(comp.at_vector(f)) for f in promo.formula]) \
        if len(promo) else pd.DataFrame(columns=list(descriptors(comp.at_vector(_BASE_CARRIES[0])).keys()))
    if len(promo_df):
        print(f"promotion queue: {len(promo_df)} provisionals with <9 runs eligible for Tier-U")
    u_pool_df = pool[pool.formula.isin(f_keep)]
    n_u = bud["U"]
    promo_first = promo_df.sort_values("ashby_strength", ascending=False).head(max(1, n_u // 2)).formula.tolist() \
        if len(promo_df) else []
    rest = u_pool_df[~u_pool_df.formula.isin(promo_first)]
    fill = ucb_select(rest, gp, scaler, n_u - len(promo_first))
    u_formulas = promo_first + fill.formula.tolist()
    if not dry_run and u_formulas:
        bu = sqs_mlip.query_tier(u_formulas, "U", f"it{iter_id}U")
        for _, r in bu.iterrows(): bands.setdefault(r.formula, {}).update(r.to_dict())
    print(f"Tier-U: queried {0 if dry_run else len(u_formulas)} (dry) -> certification set "
          f"(promo={len(promo_first)}, ucb={len(u_formulas) - len(promo_first)})")

    lookup = pd.concat([pool, promo_df], ignore_index=True).drop_duplicates("formula") \
        if len(promo_df) else pool.copy()

    reached = list(dict.fromkeys(s_formulas + f_formulas + u_formulas))
    cert_rows, prov_rows, vetoed, screened_rows = [], [], [], []
    for f in reached:
        ch = bands.get(f)
        if ch is None:
            continue
        dd = lookup[lookup.formula == f]
        if not len(dd):
            continue
        d = dd.iloc[0].to_dict()
        soft = apply_soft_gates(d, crab, chgnet=ch)
        ev = int(ch.get("n_runs", 0)); viol = float(ch.get("viol_frac", np.nan))
        cls = ch.get("cls")
        if (not soft["soft_pass"]) or (viol >= C.ARCHIVE_PROVISIONAL_MAX):
            acls = "vetoed"
        elif ev >= 9 and viol < C.ARCHIVE_CERTIFIED_MAX and d["gate_inline_pass"]:
            acls = "certified"
        elif ev >= 3 and viol < C.ARCHIVE_PROVISIONAL_MAX:
            acls = "provisional"
        else:
            acls = "screened"
        row = {**{k: d[k] for k in ARC_COLS if k in d},
               "iter_id": iter_id, "evidence_runs": ev, "viol_frac": viol,
               "archive_class": acls, "cls": cls,
               "C44_med": ch.get("C44_med", np.nan), "E_med": ch.get("E_med", np.nan),
               "K_med": ch.get("K_med", np.nan), "G_med": ch.get("G_med", np.nan),
               **{k: soft[k] for k in ("hull", "hull_src", "pugh", "pugh_src", "soft_pass")}}
        (cert_rows if acls == "certified" else
         prov_rows if acls == "provisional" else
         screened_rows if acls == "screened" else vetoed).append(row)

    have = ({r["formula"] for r in cert_rows} | {r["formula"] for r in prov_rows}
            | set(load_archive("certified").formula) | set(load_archive("provisional").formula))
    ingested = []
    for f in sorted(_evidence_certified() - have):
        best = _best_bands_row(f)
        if best is None:
            continue
        d = descriptors(comp.at_vector(f))
        cert_rows.append({**{k: d[k] for k in ARC_COLS if k in d},
                          "iter_id": iter_id, "evidence_runs": int(best.n_runs),
                          "viol_frac": float(best.viol_frac), "archive_class": "certified",
                          "cls": best.get("cls"), "C44_med": best.get("C44_med"),
                          "E_med": best.get("E_med"), "K_med": best.get("K_med"),
                          "G_med": best.get("G_med"), "hull": np.nan, "hull_src": "pending",
                          "pugh": (best.K_med / best.G_med) if best.get("G_med") else np.nan,
                          "pugh_src": "chgnet", "soft_pass": True})
        ingested.append(f)
    if ingested:
        print(f"[ingest] disk-evidence certified added: {', '.join(ingested)}")

    cert_after = merge_archive(cert_rows, "certified")
    prov_after = merge_archive(prov_rows, "provisional")

    # [v2.5a] purge stale provisional rows superseded by certification
    stale = set(cert_after.formula) & set(prov_after.formula)
    if stale:
        prov_after = prov_after[~prov_after.formula.isin(stale)]
        prov_after.to_csv(_arc_path("provisional"), index=False)
        print(f"[purge] {len(stale)} stale provisional row(s) superseded by certification: "
              f"{', '.join(sorted(stale))}")

    # demote stale provisionals vetoed by NEW 9-run evidence
    dem = {r["formula"] for r in vetoed if r["evidence_runs"] >= 9} & set(prov_after.formula)
    if dem:
        prov_after = prov_after[~prov_after.formula.isin(dem)]
        prov_after.to_csv(_arc_path("provisional"), index=False)
        print(f"[demote] provisionals removed on 9-run veto: {', '.join(sorted(dem))}")

    new_cert = [r["formula"] for r in cert_rows]
    new_prov = [r["formula"] for r in prov_rows]

    live = pd.concat([c for c in (cert_after, prov_after) if len(c)], ignore_index=True) \
        if (len(cert_after) or len(prov_after)) else pd.DataFrame(columns=ARC_COLS)
    live = live.drop_duplicates("formula")
    if len(live):
        Fl = np.column_stack([live.ashby_strength.values, live.ashby_stiffness.values])
        live = live.assign(on_front=pareto.nondominated_mask(Fl))
        front = live[live.on_front].sort_values("ashby_strength", ascending=False).formula.tolist()
    else:
        front = []

    best = live.sort_values("ashby_strength", ascending=False).iloc[0] if len(live) else None
    if best is not None and not dry_run:
        decision = f"keep/promote {best.formula} (ashby_s={best.ashby_strength}, viol={best.viol_frac})"
        next_action = f"iter {iter_id+1}: exploit near {best.formula}, mut_sigma={pop_cfg['mut_sigma']}; GP n_train={0 if train is None else len(train)+len(reached)}"
    elif dry_run:
        decision = "DRY-RUN: no CHGNet evidence -> nothing certifiable (expected)"
        next_action = f"iter {iter_id+1}: run WITHOUT --dry-run to spend the 50/10/4 budget"
    else:
        decision = "no improving candidate this iteration"
        next_action = f"iter {iter_id+1}: expand search (raise n_proposed / widen caps)"

    ledger.record(iter_id=iter_id, pop_source="seed_population(v1 survivors+carries)+warm-start",
                  pop_n=len(pop), n_proposed=len(pool),
                  n_tierS=len(s_formulas), n_tierF=len(f_formulas), n_tierU=len(u_formulas),
                  run_ids=f"it{iter_id}S,it{iter_id}F,it{iter_id}U" if not dry_run else "dry",
                  new_certified=len(new_cert), new_provisional=len(new_prov),
                  new_vetoed=len(vetoed), front_members=";".join(front),
                  decision=decision, next_action=next_action,
                  notes=f"dry_run={dry_run};smoke={smoke};beta={C.ACQ_UCB_BETA};"
                        f"gp_train={0 if train is None else len(train)};v1_seed={n_seed};"
                        f"screened={len(screened_rows)};ingested={len(ingested)};"
                        f"purged={len(stale)};demoted={len(dem)}")
    snap = ledger.snapshot(iter_id, {
        "config_sha": ledger._config_sha(), "git": ledger._git(),
        "pop_cfg": pop_cfg, "budget": bud, "inline_feasible_pool": _rec(pool),
        "tierS": s_formulas, "tierF": f_formulas, "tierU": u_formulas,
        "promotion_queue": promo_first, "ingested": ingested,
        "purged": sorted(stale), "demoted": sorted(dem),
        "chgnet_bands": {k: {kk: (None if pd.isna(vv) else vv) for kk, vv in v.items()}
                         for k, v in bands.items()},
        "new_certified": new_cert, "new_provisional": new_prov, "new_vetoed": vetoed,
        "new_screened": [r["formula"] for r in screened_rows],
        "archive_certified": _rec(cert_after), "archive_provisional": _rec(prov_after),
        "ashby_front": front},
        tag=datetime.datetime.utcnow().strftime("%H%M%S"))   # [v2.5b] re-run-safe
    print(f"[ledger] iteration_log.csv row + {snap.name}")

    _plot(live, pool, front, iter_id, dry_run)
    print(f"=== iteration {iter_id} done | certified={len(cert_after)} provisional={len(prov_after)} "
          f"front={len(front)} ===")
    return {"certified": len(cert_after), "provisional": len(prov_after), "front": front}

def _plot(live, pool, front, iter_id, dry_run):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    C.ARCH.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(9, 6.5))
    if pool is not None and len(pool):
        known = set(live.formula) if len(live) else set()
        prop = pool[~pool.formula.isin(known)]
        if len(prop):
            ax.scatter(prop.ashby_stiffness, prop.ashby_strength, marker="x", s=40,
                       c="#9e9e9e", alpha=0.7, label=f"proposed pool (n={len(prop)}, no CHGNet yet)")
    if len(live):
        cmap = {"certified": "#2ca02c", "provisional": "#ff7f0e", "vetoed": "#d62728"}
        for cls, g in live.groupby("archive_class"):
            ax.scatter(g.ashby_stiffness, g.ashby_strength, s=70,
                       c=cmap.get(cls, "#7f7f7f"), edgecolors="k", label=f"{cls} (n={len(g)})")
        for f in front:
            r = live[live.formula == f].iloc[0]
            ax.annotate(r.formula, (r.ashby_stiffness, r.ashby_strength), fontsize=7,
                        xytext=(4, 3), textcoords="offset points")
    ax.set_xlabel("Ashby buckling index  E^(1/2)/rho   (GPa^0.5 cm3/g)")
    ax.set_ylabel("Ashby bending-strength index  sigma_y^(2/3)/rho   (MPa^0.5 cm3/g)")
    ax.set_title(f"Loop A iter {iter_id}{' [DRY-RUN]' if dry_run else ''}: "
                 f"Ashby objectives, dual-archive colour")
    ax.legend(fontsize=8); ax.grid(ls="--", alpha=.5)
    plt.tight_layout()
    p = C.ARCH / f"slide_loopA_iter{iter_id:03d}.png"
    plt.savefig(p, dpi=200, bbox_inches="tight"); plt.close(fig)
    print(f"[Saved] {p}")

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Stage 8 Loop A")
    ap.add_argument("--iter-id", type=int, default=1)
    ap.add_argument("--dry-run", action="store_true", help="no CHGNet GPU calls (plumbing test)")
    ap.add_argument("--smoke", action="store_true", help="tiny pop/gen/budget for fast validation")
    ap.add_argument("--seed", type=int, default=42)
    a = ap.parse_args()
    run_iteration(a.iter_id, a.dry_run, a.smoke, a.seed)