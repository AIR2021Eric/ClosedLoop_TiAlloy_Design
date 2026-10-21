"""Convergence figure and certified-leader cards from the frozen Loop A ledger.

Reads data/iteration_log.csv and results_archive/iterations/iter_XXX_*.json.
Hypervolume uses the same reference point and 2-D formula as stopping_check.py.
This script does not import that module: importing it would re-run the rule.
It writes only the figure, the series table, and the leader cards.
"""
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from framework import pareto, strength

DATA, ARCH = REPO / "data", REPO / "results_archive"
# Declared in stopping_check.py. Do not retune here.
REF = np.array([21.0, 2.25])
# Ti-6Al-4V (Gr5) datasheet anchor in data/stage7_audit_report.csv.
TI64_RHO = 4.43
TI64_YS_HI = 1100.0


def hv2d(pts, ref):
    """Exact 2-D hypervolume (maximize both objectives). Matches stopping_check.hv2d."""
    if len(pts) == 0:
        return 0.0
    p = np.asarray(pts, float)
    p = p[(p[:, 0] > ref[0]) & (p[:, 1] > ref[1])]
    if len(p) == 0:
        return 0.0
    p = p[np.argsort(-p[:, 0])]
    vol, prev_y = 0.0, ref[1]
    for x, y in p:
        if y > prev_y:
            vol += (x - ref[0]) * (y - prev_y)
            prev_y = y
    return vol


def latest_snapshot(iter_id):
    cands = sorted((ARCH / "iterations").glob(f"iter_{iter_id:03d}*.json"))
    if not cands:
        raise FileNotFoundError(f"no snapshot for iter {iter_id}")
    return max(cands, key=lambda q: q.stat().st_mtime)


def load_snapshot(iter_id):
    return json.loads(latest_snapshot(iter_id).read_text(encoding="utf-8"))


def certified_front(rows):
    if not rows:
        return []
    F = np.array([(r["ashby_strength"], r["ashby_stiffness"]) for r in rows], float)
    mask = pareto.nondominated_mask(F)
    return sorted((r for r, k in zip(rows, mask) if k), key=lambda r: -r["ashby_strength"])


def series_from_ledger():
    log = pd.read_csv(DATA / "iteration_log.csv")
    real = (log[log.run_ids != "dry"]
            .drop_duplicates("iter_id", keep="last")
            .sort_values("iter_id"))
    rows = []
    for _, r in real.iterrows():
        snap = load_snapshot(int(r.iter_id))
        cert = snap.get("archive_certified", [])
        front = certified_front(cert)
        pts = [(c["ashby_strength"], c["ashby_stiffness"]) for c in front]
        gp = re.search(r"gp_train=([\d.]+)", str(r.notes))
        rows.append({
            "iter": int(r.iter_id),
            "hv": hv2d(pts, REF),
            "n_certified": len(cert),
            "n_provisional": len(snap.get("archive_provisional", [])),
            "n_front_live": len(snap.get("ashby_front", [])),
            "n_front_certified": len(front),
            "new_certified": int(r.new_certified),
            "gp_labels": float(gp.group(1)) if gp else np.nan,
        })
    return pd.DataFrame(rows)


def plot(df, path):
    it = df["iter"].to_numpy()
    fig, axes = plt.subplots(1, 3, figsize=(11.2, 3.6), sharex=True)

    ax = axes[0]
    ax.plot(it, df["hv"], "-o", color="#1f4e79", ms=5, lw=1.6)
    ax.set_ylabel("Hypervolume")
    ax.set_title("Certified front")
    ax.annotate(f"{df.hv.iloc[-1]:.4f}",
                xy=(it[-1], df.hv.iloc[-1]),
                xytext=(-28, 8), textcoords="offset points", fontsize=8, color="#1f4e79")

    ax = axes[1]
    ax.plot(it, df["n_certified"], "-o", color="#2ca02c", ms=5, lw=1.6, label="in archive", zorder=3)
    ax.set_ylabel("Certified in archive")
    ax.set_title("Certified alloys")
    ax2 = ax.twinx()
    ax2.bar(it, df["new_certified"], width=0.55, color="#c5ddd0", label="new_certified", zorder=2)
    ax2.set_ylabel("new_certified (ledger)")
    ax2.set_ylim(0, max(6, int(df.new_certified.max()) + 1))
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, fontsize=7, frameon=False, loc="upper left")

    ax = axes[2]
    ax.plot(it, df["gp_labels"], "-o", color="#4c4c4c", ms=5, lw=1.6)
    ax.set_ylabel("Unique C44 labels")
    ax.set_title("GP training set")

    for a in axes:
        a.set_xlabel("Real iteration")
        a.set_xticks(list(it))
        a.axvline(it[-1], color="#888888", ls=":", lw=0.8, zorder=0)
        a.grid(ls="--", alpha=0.4)
        a.set_xlim(it[0] - 0.4, it[-1] + 0.4)

    fig.suptitle("Loop A convergence  ·  closed on the 10-iteration cap", fontsize=12)
    fig.tight_layout()
    fig.savefig(path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def _spec(row):
    return float(row["sigma_y_aged"]) / float(row["rho"])


def _edge(row):
    return strength.ss_edge_flag(float(row["c_solute"]))


def _card(row, ti64_spec):
    spec = _spec(row)
    pct = 100.0 * (spec / ti64_spec - 1.0)
    return "\n".join([
        f"## {row['formula']}",
        "",
        f"- Phase field: {row['phase_field']}. Certified at iteration {int(row['iter_id'])}.",
        f"- Evidence: {int(row['evidence_runs'])} runs, viol_frac {float(row['viol_frac']):.2f}, "
        f"C44_med {float(row['C44_med']):.1f} GPa, Pugh {float(row['pugh']):.2f}.",
        f"- Ashby indices: strength {float(row['ashby_strength']):.2f}, "
        f"stiffness {float(row['ashby_stiffness']):.3f}.",
        f"- B_aged yield {float(row['sigma_y_aged']):.0f} MPa, density {float(row['rho']):.3f} g/cm³, "
        f"specific strength {spec:.1f} MPa·cm³/g ({pct:+.1f}% vs the Ti-6Al-4V upper datasheet value).",
        f"- Solute fraction {float(row['c_solute']):.2f}. Solid-solution flag: {_edge(row)}.",
        "",
    ])


def write_cards(df, path):
    final = load_snapshot(int(df.iter.iloc[-1]))
    cert = final["archive_certified"]
    by_f = {r["formula"]: r for r in cert + final["archive_provisional"]}
    front = certified_front(cert)
    ti64 = TI64_YS_HI / TI64_RHO
    late = [r for r in cert if int(r["iter_id"]) >= 9]
    late = sorted(late, key=lambda r: (int(r["iter_id"]), -float(r["ashby_strength"])))
    on_front = {r["formula"] for r in front}
    lines = [
        "# Certified-leader cards",
        "",
        "Loop A closed at iteration 10 on the pre-registered safety cap "
        f"(tag `v2.0-loop-closed`). Certified archive: {int(df.n_certified.iloc[-1])}. "
        f"Certified-only front: {len(front)}. "
        f"Live front (certified and provisional): {len(final['ashby_front'])}. "
        f"Certified-front hypervolume: {df.hv.iloc[-1]:.4f}, unchanged from iteration 8.",
        "",
        "The datasheet anchor is Ti-6Al-4V (Gr5) in `data/stage7_audit_report.csv`: "
        f"ρ = {TI64_RHO:.2f} g/cm³, yield-strength band 880–{TI64_YS_HI:.0f} MPa. "
        f"The upper specific strength is {ti64:.1f} MPa·cm³/g. "
        "Yield strengths below are the declared B_aged scenario at the 10 µm reference grain size, "
        "where the Hall–Petch increment relative to that reference is zero.",
        "",
        "# Certified-only front",
        "",
        "These eight points are the set whose hypervolume the stopping rule tracks "
        f"(reference [{REF[0]:.1f}, {REF[1]:.2f}]).",
        "",
    ]
    for r in front:
        lines.append(_card(r, ti64))
    lines += [
        "# Certifications in iterations 9 and 10",
        "",
        "These entered the certified archive after the front had already flattened. "
        "A row is interior when a certified neighbor dominates it in Ashby space.",
        "",
    ]
    for r in late:
        place = "on the certified front" if r["formula"] in on_front else "interior to the certified front"
        lines.append(_card(r, ti64).replace(
            f"## {r['formula']}\n",
            f"## {r['formula']}\n\n- Place: {place}.\n",
            1,
        ))
    lines += [
        "# Live Ashby front",
        "",
        "| formula | class | phase | runs | viol | strength | stiffness | σ_y,aged (MPa) | ρ |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for name in final["ashby_front"]:
        r = by_f[name]
        lines.append(
            f"| {r['formula']} | {r['archive_class']} | {r['phase_field']} | "
            f"{int(r['evidence_runs'])} | {float(r['viol_frac']):.2f} | "
            f"{float(r['ashby_strength']):.2f} | {float(r['ashby_stiffness']):.3f} | "
            f"{float(r['sigma_y_aged']):.0f} | {float(r['rho']):.3f} |"
        )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    df = series_from_ledger()
    # Locked to the iteration-10 stopping table. A mismatch means this figure
    # and stopping_check.py no longer share a hypervolume.
    expect_hv = [0.7075, 0.7075, 1.0169, 1.0654, 1.0654, 1.0689, 1.0721, 1.0740, 1.0740, 1.0740]
    got = [round(v, 4) for v in df.hv.tolist()]
    if got != expect_hv:
        raise SystemExit(f"hypervolume drifted from the stopping table:\n{got}")
    ARCH.mkdir(parents=True, exist_ok=True)
    csv_path = ARCH / "loopA_convergence_series.csv"
    png_path = ARCH / "slide_loopA_convergence.png"
    card_path = ARCH / "certified_leader_cards.md"
    out = df.copy()
    out["hv"] = out["hv"].round(4)
    out.to_csv(csv_path, index=False)
    plot(df, png_path)
    write_cards(df, card_path)
    print(f"[Saved] {png_path}")
    print(f"[Saved] {csv_path}")
    print(f"[Saved] {card_path}")
    print(out.to_string(index=False))


if __name__ == "__main__":
    main()
