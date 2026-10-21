"""Live Ashby front against the eight Stage-7 commercial baselines.

Reads the frozen archives and data/stage7_audit_report.csv. Does not run the
loop and does not import stopping_check.py. Writes the comparison figure,
a CSV of the numbers, and a markdown table.
"""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from framework import composition as comp
from framework import config as C
from framework import pareto


def e_proxy(at):
    """Same rule-of-mixtures modulus as loop_A_optimizer.descriptors."""
    k_rm = sum(at[el] / 100.0 * C.EL_K[el] for el in C.PALETTE if at[el] > 0)
    g_rm = sum(at[el] / 100.0 * C.EL_G[el] for el in C.PALETTE if at[el] > 0)
    return round(9.0 * k_rm * g_rm / (3.0 * k_rm + g_rm), 1)

DATA, ARCH = REPO / "data", REPO / "results_archive"
# The v1 audit set named in results_archive/stages_1_to_8.md. beta-21S is an
# extra anchor and is not in data/stage7_audit_report.csv.
V1_NAMES = [
    "Ti-6Al-4V (Gr5)", "Ti-6242", "Ti-6246", "Ti-5553",
    "Ti-10-2-3", "Ti-15-3-3-3", "Beta C", "CP-Ti (Gr2)",
]
# Labels on the figure. CP-Ti sits far below the frame-alloy window.
SHORT = {
    "Ti-6Al-4V (Gr5)": "Ti-6Al-4V",
    "Ti-6242": "Ti-6242",
    "Ti-6246": "Ti-6246",
    "Ti-5553": "Ti-5553",
    "Ti-10-2-3": "Ti-10-2-3",
    "Ti-15-3-3-3": "Ti-15-3-3-3",
    "Beta C": "Beta C",
    "CP-Ti (Gr2)": "CP-Ti Gr2",
}
FRONT_EXPECTED = [
    "Ti69Al15V16", "Ti70Al15V14Cr1", "Ti70Al15V13Cr2", "Ti72Al15V9Cr4",
    "Ti72Al15V7Cr4Fe2", "Ti74Al14V6Cr4Fe2", "Ti74Al14V5Cr4Fe3",
    "Ti83Al14V3", "Ti81Al15Cr2Fe2", "Ti83Al14Cr3", "Ti79Al15Cr4Fe2",
]
CERT_C = "#2ca02c"
PROV_C = "#ff7f0e"
BASE_C = "#1f4e79"


def ashby_strength(sigma, rho):
    return float(np.maximum(sigma, 1.0) ** (2.0 / 3.0) / rho)


def ashby_stiffness(E, rho):
    return float(np.sqrt(np.maximum(E, 1.0)) / rho)


def spec_strength(sigma, rho):
    return float(sigma) / float(rho)


def load_front():
    cert = pd.read_csv(DATA / "archive_certified.csv")
    prov = pd.read_csv(DATA / "archive_provisional.csv")
    live = pd.concat([cert, prov], ignore_index=True).drop_duplicates("formula")
    F = np.column_stack([live.ashby_strength.values, live.ashby_stiffness.values])
    front = live[pareto.nondominated_mask(F)].sort_values(
        ["ashby_strength", "ashby_stiffness"], ascending=[False, True]
    )
    got = front.formula.tolist()
    if got != FRONT_EXPECTED:
        raise SystemExit(f"live front drifted from the iteration-10 labels:\n{got}")
    return front.reset_index(drop=True)


def load_baselines():
    raw = pd.read_csv(DATA / "stage7_audit_report.csv")
    missing = [n for n in V1_NAMES if n not in set(raw["name"])]
    if missing:
        raise SystemExit(f"stage7 audit is missing {missing}")
    raw = raw.set_index("name").loc[V1_NAMES].reset_index()
    rows = []
    for _, r in raw.iterrows():
        wt = {el: float(r[el]) for el in C.PALETTE
              if el in r and pd.notna(r[el]) and float(r[el]) > 0}
        at = comp.wt_to_at(wt)
        e_rm = e_proxy(at)
        rho_ds, e_ds = float(r.rho_DS), float(r.E_DS)
        ys_lo, ys_hi = float(r.YS_DS_lo), float(r.YS_DS_hi)
        rho_m, ys_m = float(r.rho_calc), float(r.YS_calc)
        rows.append({
            "name": r["name"],
            "short": SHORT[r["name"]],
            "family": r["family"],
            "E_DS": e_ds,
            "rho_DS": rho_ds,
            "YS_lo": ys_lo,
            "YS_hi": ys_hi,
            "strength_ds_lo": ashby_strength(ys_lo, rho_ds),
            "strength_ds_hi": ashby_strength(ys_hi, rho_ds),
            "stiffness_ds": ashby_stiffness(e_ds, rho_ds),
            "spec_ds_lo": spec_strength(ys_lo, rho_ds),
            "spec_ds_hi": spec_strength(ys_hi, rho_ds),
            "E_proxy": e_rm,
            "rho_model": rho_m,
            "YS_model": ys_m,
            "strength_model": ashby_strength(ys_m, rho_m),
            "stiffness_model": ashby_stiffness(e_rm, rho_m),
            "spec_model": spec_strength(ys_m, rho_m),
            "in_frame_window": r["name"] != "CP-Ti (Gr2)",
        })
    return pd.DataFrame(rows)


def _pct(value, ref):
    return 100.0 * (value / ref - 1.0)


def comparison_table(front, base):
    frame = base[base.in_frame_window]
    best_s_ds = frame.loc[frame.strength_ds_hi.idxmax()]
    best_k_ds = frame.loc[frame.stiffness_ds.idxmax()]
    best_s_m = frame.loc[frame.strength_model.idxmax()]
    best_k_m = frame.loc[frame.stiffness_model.idxmax()]
    ti64 = base[base.name == "Ti-6Al-4V (Gr5)"].iloc[0]
    rows = []
    for _, r in front.iterrows():
        s, k = float(r.ashby_strength), float(r.ashby_stiffness)
        spec = spec_strength(r.sigma_y_aged, r.rho)
        n_dom_ds = int(((s >= frame.strength_ds_hi) & (k >= frame.stiffness_ds)
                        & ((s > frame.strength_ds_hi) | (k > frame.stiffness_ds))).sum())
        n_dom_m = int(((s >= frame.strength_model) & (k >= frame.stiffness_model)
                       & ((s > frame.strength_model) | (k > frame.stiffness_model))).sum())
        rows.append({
            "formula": r.formula,
            "class": r.archive_class,
            "runs": int(r.evidence_runs),
            "viol_frac": float(r.viol_frac),
            "strength": s,
            "stiffness": k,
            "spec": spec,
            "d_strength_vs_best_ds_pct": _pct(s, best_s_ds.strength_ds_hi),
            "best_strength_ds": best_s_ds.short,
            "d_stiffness_vs_best_ds_pct": _pct(k, best_k_ds.stiffness_ds),
            "best_stiffness_ds": best_k_ds.short,
            "d_spec_vs_ti64_hi_pct": _pct(spec, ti64.spec_ds_hi),
            "d_strength_vs_best_model_pct": _pct(s, best_s_m.strength_model),
            "best_strength_model": best_s_m.short,
            "d_stiffness_vs_best_model_pct": _pct(k, best_k_m.stiffness_model),
            "best_stiffness_model": best_k_m.short,
            "d_spec_vs_ti64_model_pct": _pct(spec, ti64.spec_model),
            "n_frame_dominated_datasheet_upper": n_dom_ds,
            "n_frame_dominated_model": n_dom_m,
            "n_frame": int(len(frame)),
        })
    return pd.DataFrame(rows), {
        "best_s_ds": best_s_ds, "best_k_ds": best_k_ds,
        "best_s_m": best_s_m, "best_k_m": best_k_m, "ti64": ti64,
    }


def _front_artists(ax, front):
    order = front.sort_values("ashby_stiffness")
    ax.plot(order.ashby_stiffness, order.ashby_strength, color="#444444",
            lw=1.0, zorder=2)
    for cls, color in (("certified", CERT_C), ("provisional", PROV_C)):
        g = front[front.archive_class == cls]
        ax.scatter(g.ashby_stiffness, g.ashby_strength, s=64, c=color,
                   edgecolors="k", linewidths=0.6, zorder=3)
    strength = front[front.ashby_strength >= 26].sort_values("ashby_stiffness")
    stiff = front[front.ashby_strength < 26].sort_values("ashby_stiffness")
    # Open region above the commercial cloud, left of the strength arm.
    for i, (_, r) in enumerate(strength.iterrows()):
        color = CERT_C if r.archive_class == "certified" else "#b85c00"
        ax.annotate(
            r.formula, (r.ashby_stiffness, r.ashby_strength),
            xytext=(2.045, 27.42 - i * 0.24),
            fontsize=6.4, color=color, va="center", ha="left",
            arrowprops=dict(arrowstyle="-", color="#9a9a9a", lw=0.45),
            zorder=5,
        )
    # Gutter to the right of the stiffness arm.
    for i, (_, r) in enumerate(stiff.iterrows()):
        color = CERT_C if r.archive_class == "certified" else "#b85c00"
        ax.annotate(
            r.formula, (r.ashby_stiffness, r.ashby_strength),
            xytext=(2.58, 24.85 - i * 0.42),
            fontsize=6.4, color=color, va="center", ha="left",
            arrowprops=dict(arrowstyle="-", color="#9a9a9a", lw=0.45),
            zorder=5,
        )


def _style(ax, xlabel):
    ax.set_xlabel(xlabel)
    ax.set_xlim(2.02, 2.96)
    ax.set_ylim(19.2, 27.7)
    ax.grid(ls="--", alpha=0.45)


def plot(front, base, path):
    fig, axs = plt.subplots(1, 2, figsize=(13.6, 6.6), sharey=True)
    frame = base[base.in_frame_window]

    ax = axs[0]
    _front_artists(ax, front)
    ax.errorbar(
        frame.stiffness_ds, frame.strength_ds_hi,
        yerr=np.vstack([
            frame.strength_ds_hi - frame.strength_ds_lo,
            np.zeros(len(frame)),
        ]),
        fmt="s", color=BASE_C, ecolor=BASE_C, elinewidth=1.2, capsize=3,
        ms=6, zorder=4,
    )
    offsets = {
        "Ti-6Al-4V": (-72, -6), "Ti-6242": (10, 2), "Ti-6246": (-6, 10),
        "Ti-5553": (8, 2), "Ti-10-2-3": (8, -12), "Ti-15-3-3-3": (8, 2),
        "Beta C": (8, -12),
    }
    for _, r in frame.iterrows():
        dx, dy = offsets[r.short]
        ax.annotate(r.short, (r.stiffness_ds, r.strength_ds_hi),
                    textcoords="offset points", xytext=(dx, dy),
                    fontsize=7, color=BASE_C)
    _style(ax, r"Ashby buckling index  $E^{1/2}/\rho$   (GPa$^{0.5}$ cm$^3$/g)")
    ax.set_ylabel(r"Ashby bending-strength index  $\sigma_y^{2/3}/\rho$   (MPa$^{2/3}$ cm$^3$/g)")
    ax.set_title("A   Datasheet E, density, and yield band")

    ax = axs[1]
    _front_artists(ax, front)
    ax.scatter(frame.stiffness_model, frame.strength_model, s=46, marker="s",
               c=BASE_C, zorder=4)
    offsets_m = {
        "Ti-6Al-4V": (-58, -14), "Ti-6242": (8, -4), "Ti-6246": (8, 6),
        "Ti-5553": (8, 6), "Ti-10-2-3": (8, -12), "Ti-15-3-3-3": (-78, 4),
        "Beta C": (8, -12),
    }
    for _, r in frame.iterrows():
        dx, dy = offsets_m[r.short]
        ax.annotate(r.short, (r.stiffness_model, r.strength_model),
                    textcoords="offset points", xytext=(dx, dy),
                    fontsize=7, color=BASE_C)
    _style(ax, r"Ashby buckling index  $E_{\mathrm{proxy}}^{1/2}/\rho$   (GPa$^{0.5}$ cm$^3$/g)")
    ax.set_title("B   B_aged yield, model density, and $E_{proxy}$")

    fig.suptitle(
        "Loop A live front (iteration 10) and eight commercial titanium alloys",
        fontsize=12, y=1.01,
    )
    handles = [
        plt.Line2D([0], [0], marker="o", color="none", markerfacecolor=CERT_C,
                   markeredgecolor="k", markersize=7, label="certified on the live front"),
        plt.Line2D([0], [0], marker="o", color="none", markerfacecolor=PROV_C,
                   markeredgecolor="k", markersize=7, label="provisional on the live front"),
        plt.Line2D([0], [0], marker="s", color=BASE_C, markersize=6,
                   label="A  datasheet (square = upper yield; bar = yield band)"),
        plt.Line2D([0], [0], marker="s", color=BASE_C, markerfacecolor=BASE_C,
                   markersize=6, linestyle="none",
                   label="B  same model as the search"),
    ]
    fig.legend(handles=handles, loc="lower center", ncol=2, fontsize=8,
               frameon=False, bbox_to_anchor=(0.5, -0.04))
    fig.text(
        0.5, -0.08,
        "Green and orange names are the live front. Ti-5553 and Ti-10-2-3 share one datasheet point. "
        "CP-Ti Grade 2 (bending index about 11) lies below this window. "
        "Discovered yields are the B_aged calculation, not measured tensile strengths.",
        ha="center", va="top", fontsize=8, color="#333333",
    )
    fig.tight_layout()
    fig.savefig(path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def _fmt_pct(v):
    return f"{v:+.1f}%"


def _tied_names(frame, column, best_value):
    hit = frame[np.isclose(frame[column], best_value)]
    return " and ".join(hit.short.tolist())


def write_markdown(front_cmp, base, refs, path):
    ti64 = refs["ti64"]
    bs, bk = refs["best_s_ds"], refs["best_k_ds"]
    ms, mk = refs["best_s_m"], refs["best_k_m"]
    frame = base[base.in_frame_window]
    best_s_ds_name = _tied_names(frame, "strength_ds_hi", bs.strength_ds_hi)
    best_k_ds_name = _tied_names(frame, "stiffness_ds", bk.stiffness_ds)
    lines = [
        "# Live front against commercial baselines",
        "",
        "The eleven labelled alloys are the live Ashby front at iteration 10: "
        "certified and provisional alloys that no other archived alloy dominates. "
        "The eight comparison alloys are the Stage 7 datasheet set in "
        "`data/stage7_audit_report.csv`.",
        "",
        "Two scorings are kept apart. Panel A and the datasheet columns use measured "
        "modulus, density, and the published yield band. Panel B and the model columns "
        "score those same alloys with the search's own recipe: B_aged yield at the "
        "declared datasheet family (`YS_calc`), inverse rule-of-mixtures density "
        "(`rho_calc`), and the rule-of-mixtures modulus `E_proxy`. "
        "Discovered yields remain the B_aged calculation. They are not measured tensile strengths.",
        "",
        f"On the datasheet scoring, the highest bending-strength index is "
        f"**{best_s_ds_name}** at {bs.strength_ds_hi:.2f} "
        f"(upper yield {bs.YS_hi:.0f} MPa, ρ = {bs.rho_DS:.2f} g/cm³). "
        f"The highest buckling index is **{best_k_ds_name}** at {bk.stiffness_ds:.3f}. "
        f"Ti-6Al-4V's upper specific strength is {ti64.spec_ds_hi:.1f} MPa·cm³/g.",
        "",
        f"On the model scoring, the highest bending-strength index is **{ms.short}** "
        f"at {ms.strength_model:.2f}, and the highest buckling index is **{mk.short}** "
        f"at {mk.stiffness_model:.3f}.",
        "",
        "A labelled alloy can lead one index and still sit behind a commercial alloy "
        "on the other. CP-Ti Grade 2 is in the tables and below the plotted window.",
        "",
        "## Where the labelled front is higher",
        "",
    ]
    hi_s = front_cmp.iloc[0]
    lo_s = front_cmp.iloc[-1]
    both = front_cmp[front_cmp.n_frame_dominated_datasheet_upper == front_cmp.n_frame]
    short_of = front_cmp[front_cmp.d_stiffness_vs_best_ds_pct < 0]
    stiff_arm = front_cmp[front_cmp.strength < 26]
    lines += [
        f"- Bending index against the datasheet upper bounds: all eleven are above "
        f"{best_s_ds_name} ({bs.strength_ds_hi:.2f}). "
        f"{hi_s.formula} is {_fmt_pct(hi_s.d_strength_vs_best_ds_pct)}. "
        f"{lo_s.formula} is {_fmt_pct(lo_s.d_strength_vs_best_ds_pct)}.",
        f"- Buckling index against the datasheets: {', '.join(short_of.formula)} "
        f"are below {best_k_ds_name} ({bk.stiffness_ds:.3f}), by "
        f"{_fmt_pct(short_of.d_stiffness_vs_best_ds_pct.min())} to "
        f"{_fmt_pct(short_of.d_stiffness_vs_best_ds_pct.max())}. "
        f"From {both.iloc[0].formula} to the right, the front is above every commercial "
        f"buckling index. The largest gain is {lo_s.formula} at "
        f"{_fmt_pct(lo_s.d_stiffness_vs_best_ds_pct)}.",
        f"- Both indices at once, using each frame alloy's upper datasheet yield: "
        f"{both.iloc[0].formula} and the alloys to its right beat all "
        f"{int(both.iloc[0].n_frame)} frame alloys. The three strength-arm leaders do not, "
        f"because Ti-6Al-4V and Ti-6242 remain slightly stiffer.",
        f"- Same model: the strength arm stays above {ms.short}'s bending index "
        f"({ms.strength_model:.2f}), by {_fmt_pct(front_cmp[front_cmp.strength >= 26].d_strength_vs_best_model_pct.min())} "
        f"to {_fmt_pct(hi_s.d_strength_vs_best_model_pct)}. "
        f"The stiffness arm falls short of that model bending index, by "
        f"{_fmt_pct(stiff_arm.d_strength_vs_best_model_pct.max())} to "
        f"{_fmt_pct(stiff_arm.d_strength_vs_best_model_pct.min())}, and stays ahead on buckling.",
        f"- Specific strength against Ti-6Al-4V's upper datasheet value "
        f"({ti64.spec_ds_hi:.1f} MPa·cm³/g): {_fmt_pct(hi_s.d_spec_vs_ti64_hi_pct)} at "
        f"{hi_s.formula}, down to {_fmt_pct(front_cmp.d_spec_vs_ti64_hi_pct.min())} at "
        f"{front_cmp.loc[front_cmp.d_spec_vs_ti64_hi_pct.idxmin(), 'formula']}.",
        "",
        "",
        "## Datasheet positions",
        "",
        "| alloy | family | E (GPa) | ρ (g/cm³) | YS band (MPa) | bending index | buckling index | specific strength (MPa·cm³/g) |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for _, r in base.iterrows():
        lines.append(
            f"| {r.short} | {r.family} | {r.E_DS:.0f} | {r.rho_DS:.2f} | "
            f"{r.YS_lo:.0f}–{r.YS_hi:.0f} | {r.strength_ds_lo:.2f}–{r.strength_ds_hi:.2f} | "
            f"{r.stiffness_ds:.3f} | {r.spec_ds_lo:.1f}–{r.spec_ds_hi:.1f} |"
        )
    lines += [
        "",
        "## Same-model positions",
        "",
        "Yield uses the datasheet family, as in the Stage 7 audit. "
        "Density is the uncalibrated inverse rule of mixtures. Modulus is `E_proxy`.",
        "",
        "| alloy | family | E_proxy (GPa) | ρ_model | σ_Baged (MPa) | bending index | buckling index | specific strength |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for _, r in base.iterrows():
        lines.append(
            f"| {r.short} | {r.family} | {r.E_proxy:.1f} | {r.rho_model:.3f} | "
            f"{r.YS_model:.0f} | {r.strength_model:.2f} | {r.stiffness_model:.3f} | "
            f"{r.spec_model:.1f} |"
        )
    lines += [
        "",
        "## Labelled front versus the best commercial alloy",
        "",
        "Bending and buckling deltas use the best frame alloy in that column "
        f"(datasheet bending: {best_s_ds_name}; datasheet buckling: {best_k_ds_name}; "
        f"model bending: {ms.short}; model buckling: {mk.short}). "
        "Specific-strength deltas use Ti-6Al-4V. "
        "“Dominates” counts how many of the seven frame alloys the row beats on both indices at once. "
        "The datasheet count uses each alloy's upper yield. CP-Ti is excluded from that count.",
        "",
        "| formula | class | runs | viol | bending | vs best datasheet | vs best model | buckling | vs best datasheet | vs best model | σ/ρ | vs Ti-64 upper | vs Ti-64 model | dominates (datasheet) | dominates (model) |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for _, r in front_cmp.iterrows():
        lines.append(
            f"| {r.formula} | {r['class']} | {r.runs} | {r.viol_frac:.2f} | "
            f"{r.strength:.2f} | {_fmt_pct(r.d_strength_vs_best_ds_pct)} | "
            f"{_fmt_pct(r.d_strength_vs_best_model_pct)} | "
            f"{r.stiffness:.3f} | {_fmt_pct(r.d_stiffness_vs_best_ds_pct)} | "
            f"{_fmt_pct(r.d_stiffness_vs_best_model_pct)} | "
            f"{r.spec:.1f} | {_fmt_pct(r.d_spec_vs_ti64_hi_pct)} | "
            f"{_fmt_pct(r.d_spec_vs_ti64_model_pct)} | "
            f"{r.n_frame_dominated_datasheet_upper}/{r.n_frame} | "
            f"{r.n_frame_dominated_model}/{r.n_frame} |"
        )
    lines += [
        "",
        "Positive means the labelled alloy is higher than that reference. "
        "Ti69Al15V16 carries `SS_LINEAR_EDGE`: its solute fraction is far from the "
        "0.10 calibration point of the solid-solution term.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    front = load_front()
    base = load_baselines()
    front_cmp, refs = comparison_table(front, base)
    ARCH.mkdir(parents=True, exist_ok=True)
    png = ARCH / "slide_loopA_vs_baselines.png"
    csv = ARCH / "baseline_comparison.csv"
    md = ARCH / "baseline_comparison.md"
    plot(front, base, png)
    front_cmp.to_csv(csv, index=False)
    write_markdown(front_cmp, base, refs, md)
    print(f"[Saved] {png}")
    print(f"[Saved] {csv}")
    print(f"[Saved] {md}")
    cols = ["short", "strength_ds_lo", "strength_ds_hi", "stiffness_ds",
            "strength_model", "stiffness_model", "spec_ds_hi", "spec_model"]
    print(base[cols].to_string(index=False))
    print(front_cmp[["formula", "d_strength_vs_best_ds_pct", "d_stiffness_vs_best_ds_pct",
                     "d_spec_vs_ti64_hi_pct", "n_frame_dominated_datasheet_upper",
                     "n_frame_dominated_model"]].to_string(index=False))


if __name__ == "__main__":
    main()
