"""Iteration-10 archive against the eight Stage-7 commercial alloys.

Reads the frozen archives and data/stage7_audit_report.csv. Does not run the
loop and does not import stopping_check.py. One axes: the archive uses the
Ashby indices already stored on it, and the commercial alloys are scored with
that same recipe (B_aged yield, model density, E_proxy).

The live-front tables remain in plot_baseline_comparison.py.

Run from the repo root:

    py -3.11 stage8_iteration/plot_final_iteration.py
"""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "stage8_iteration"))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

import plot_baseline_comparison as basefig

DATA, ARCH = REPO / "data", REPO / "results_archive"
CERT_C = basefig.CERT_C
PROV_C = basefig.PROV_C
BASE_C = basefig.BASE_C
INTERIOR = {"certified": "#8fbf8f", "provisional": "#f3c48a"}


def load_archive():
    cert = pd.read_csv(DATA / "archive_certified.csv")
    prov = pd.read_csv(DATA / "archive_provisional.csv")
    if len(cert) != 25 or len(prov) != 55:
        raise SystemExit(
            f"archive size drifted from the closed loop: "
            f"certified={len(cert)} provisional={len(prov)}"
        )
    overlap = set(cert.formula) & set(prov.formula)
    if overlap:
        raise SystemExit(f"formula in both archives: {sorted(overlap)}")
    return pd.concat([cert, prov], ignore_index=True)


def plot(archive, front, baselines, png_path, pdf_path):
    plt.rcParams.update({
        "font.size": 10,
        "axes.labelsize": 10,
        "axes.titlesize": 12,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    })
    frame = baselines[baselines.in_frame_window]
    front_names = set(front.formula)
    n_cert = int((archive.archive_class == "certified").sum())
    n_prov = int((archive.archive_class == "provisional").sum())
    n_front_c = int((front.archive_class == "certified").sum())
    n_front_p = int((front.archive_class == "provisional").sum())

    fig, ax = plt.subplots(figsize=(11.4, 7.6))
    for cls, color in (("certified", CERT_C), ("provisional", PROV_C)):
        g = archive[archive.archive_class == cls]
        interior = g[~g.formula.isin(front_names)]
        on_front = g[g.formula.isin(front_names)]
        ax.scatter(
            interior.ashby_stiffness, interior.ashby_strength,
            s=28, c=INTERIOR[cls], edgecolors="none", zorder=2,
        )
        ax.scatter(
            on_front.ashby_stiffness, on_front.ashby_strength,
            s=70, c=color, edgecolors="k", linewidths=0.6, zorder=4,
        )
    order = front.sort_values("ashby_stiffness")
    ax.plot(order.ashby_stiffness, order.ashby_strength, color="#444444", lw=1.05, zorder=3)
    ax.scatter(
        frame.stiffness_model, frame.strength_model,
        s=52, marker="s", c=BASE_C, zorder=5,
    )

    strength = front[front.ashby_strength >= 26].sort_values("ashby_stiffness")
    for i, (_, r) in enumerate(strength.iterrows()):
        color = CERT_C if r.archive_class == "certified" else "#b85c00"
        ax.annotate(
            r.formula, (r.ashby_stiffness, r.ashby_strength),
            xytext=(2.291, 26.95 - i * 0.15),
            fontsize=7, color=color, va="center", ha="left",
            arrowprops=dict(arrowstyle="-", color="#b5b5b5", lw=0.4),
            zorder=6,
        )
    stiff = front[front.ashby_strength < 26].sort_values("ashby_stiffness")
    for i, (_, r) in enumerate(stiff.iterrows()):
        color = CERT_C if r.archive_class == "certified" else "#b85c00"
        ax.annotate(
            r.formula, (r.ashby_stiffness, r.ashby_strength),
            xytext=(2.505, 24.70 - i * 0.32),
            fontsize=7, color=color, va="center", ha="left",
            arrowprops=dict(arrowstyle="-", color="#b5b5b5", lw=0.4),
            zorder=6,
        )
    model_offsets = {
        "Ti-6Al-4V": (6, -12),
        "Ti-6242": (6, -8),
        "Ti-6246": (-6, -12),
        "Ti-5553": (-8, 9),
        "Ti-10-2-3": (-58, -11),
        "Ti-15-3-3-3": (6, 5),
        "Beta C": (6, -11),
    }
    for _, r in frame.iterrows():
        ax.annotate(
            r.short, (r.stiffness_model, r.strength_model),
            textcoords="offset points", xytext=model_offsets[r.short],
            fontsize=8, color=BASE_C, zorder=6,
        )

    ax.set_xlim(2.285, 2.585)
    ax.set_ylim(21.55, 27.15)
    ax.grid(ls="--", alpha=0.4)
    ax.set_xlabel(
        r"Ashby buckling index  $E_{\mathrm{proxy}}^{1/2}/\rho$   (GPa$^{0.5}$ cm$^3$/g)",
        labelpad=8,
    )
    ax.set_ylabel(
        r"Ashby bending-strength index  $\sigma_y^{2/3}/\rho$   (MPa$^{2/3}$ cm$^3$/g)"
    )
    ax.set_title("Iteration 10 archive and commercial titanium alloys")

    handles = [
        plt.Line2D([0], [0], marker="o", color="none", markerfacecolor=CERT_C,
                   markeredgecolor="k", markersize=8, label="certified on the live front"),
        plt.Line2D([0], [0], marker="o", color="none", markerfacecolor=PROV_C,
                   markeredgecolor="k", markersize=8, label="provisional on the live front"),
        plt.Line2D([0], [0], marker="o", color="none", markerfacecolor=INTERIOR["certified"],
                   markersize=6, label=f"other certified (n={n_cert - n_front_c})"),
        plt.Line2D([0], [0], marker="o", color="none", markerfacecolor=INTERIOR["provisional"],
                   markersize=6, label=f"other provisional (n={n_prov - n_front_p})"),
        plt.Line2D([0], [0], marker="s", color=BASE_C, markerfacecolor=BASE_C,
                   markersize=7, linestyle="none",
                   label="commercial alloy, same model as the search"),
    ]
    fig.legend(
        handles=handles, loc="upper center", ncol=3, fontsize=8,
        frameon=False, bbox_to_anchor=(0.55, 0.145),
    )
    fig.text(
        0.55, 0.015,
        "Named circles are the live Ashby front. Squares use B_aged yield, model density, and "
        r"$E_{\mathrm{proxy}}$, the same recipe as the archive."
        "\nCP-Ti Grade 2 lies below this window. "
        "Discovered yields are the B_aged calculation, not measured tensile strengths.",
        ha="center", va="bottom", fontsize=8, color="#333333", linespacing=1.35,
    )
    fig.subplots_adjust(left=0.10, right=0.98, top=0.92, bottom=0.28)
    fig.savefig(png_path, dpi=200)
    fig.savefig(pdf_path)
    plt.close(fig)


def main():
    archive = load_archive()
    front = basefig.load_front()
    baselines = basefig.load_baselines()
    ARCH.mkdir(parents=True, exist_ok=True)
    png = ARCH / "fig_iter10_vs_commercial.png"
    pdf = ARCH / "fig_iter10_vs_commercial.pdf"
    plot(archive, front, baselines, png, pdf)
    print(f"[Saved] {png}")
    print(f"[Saved] {pdf}")
    print(
        f"archive certified={(archive.archive_class == 'certified').sum()} "
        f"provisional={(archive.archive_class == 'provisional').sum()} "
        f"live front={len(front)}"
    )


if __name__ == "__main__":
    main()
