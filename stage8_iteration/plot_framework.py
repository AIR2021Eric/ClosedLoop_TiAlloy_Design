"""Flowchart of one Stage 8 iteration (Loop A).

Reads no archives. Draws the control flow in run_iteration.py and
loop_A_optimizer.py. Boxes are named by what they do. A stage badge
marks a step that reuses a frozen model. Writes a PNG and an SVG.
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Polygon

REPO = Path(__file__).resolve().parents[1]
ARCH = REPO / "results_archive"

INK = "#243140"
MUTED = "#5c6b7a"
RULE = "#c5ced6"


def rounded(ax, cx, cy, w, h, fc, ec=INK, lw=1.05):
    ax.add_patch(FancyBboxPatch(
        (cx - w / 2, cy - h / 2), w, h,
        boxstyle="round,pad=0.02,rounding_size=0.45",
        facecolor=fc, edgecolor=ec, linewidth=lw, zorder=2,
    ))


def text(ax, cx, cy, s, size=8.0, color=INK, weight="regular", ha="center"):
    ax.text(cx, cy, s, ha=ha, va="center", fontsize=size, color=color,
            fontweight=weight, linespacing=1.28, zorder=3)


def arrow(ax, x1, y1, x2, y2, color=INK):
    ax.annotate(
        "", xy=(x2, y2), xytext=(x1, y1),
        arrowprops=dict(arrowstyle="-|>", color=color, lw=1.15,
                        mutation_scale=11, shrinkA=0, shrinkB=0),
        zorder=1,
    )


def down(ax, cx, top_box, bot_box, gap_pad=0.15):
    """Arrow from the bottom of top_box=(cy,h) to the top of bot_box."""
    y1 = top_box[0] - top_box[1] / 2 - gap_pad
    y2 = bot_box[0] + bot_box[1] / 2 + gap_pad
    arrow(ax, cx, y1, cx, y2)


def pill(ax, cx, cy, s, fc="#e7eef6"):
    w = 0.92 * len(s) + 2.4
    h = 2.55
    rounded(ax, cx, cy, w, h, fc, ec="#9eb0c2", lw=0.7)
    text(ax, cx, cy, s, size=6.15, weight="bold", color="#1f4e79")
    return w, h


def card(ax, cx, cy, w, h, title, body, fc, title_color=INK):
    rounded(ax, cx, cy, w, h, fc)
    text(ax, cx, cy + h / 2 - 1.7, title, size=7.6, weight="bold", color=title_color)
    text(ax, cx, cy - 1.15, body, size=6.25)


def main():
    fig, ax = plt.subplots(figsize=(8.6, 13.8))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 236)
    ax.axis("off")
    fig.patch.set_facecolor("white")

    cx = 58.0
    w = 74.0

    gap = 3.15
    y = 228.0

    def take(h):
        nonlocal y
        cy = y - h / 2
        y -= h + gap
        return cy, h

    propose = take(24.0)
    legal = take(15.2)
    dedup = take(8.4)
    choose = take(13.6)
    y -= 6.2  # room for the arrow into Tier S and the Stage 4 badge
    tier_h, tier_w = 16.4, 22.2
    tier_y = y - tier_h / 2
    y -= tier_h + gap
    born = take(6.6)
    y -= 0.4
    file_h = 17.6
    file_y = y - file_h / 2
    y -= file_h + 2.3
    front = take(8.8)
    datasheet = take(11.2)
    stop_rule = take(12.4)

    py = propose[0]
    rounded(ax, cx, py, w, propose[1], "#f4f7fb")
    text(ax, cx, py + 8.4, "Propose", size=9.2, weight="bold")
    text(ax, cx, py + 5.7,
         r"Search compositions that raise both Ashby indices.", size=7.35)
    text(ax, cx, py + 2.9,
         r"Strength  $\sigma_{y,\mathrm{aged}}^{2/3}\,/\,\rho$"
         r"      stiffness  $E_{\mathrm{proxy}}^{1/2}\,/\,\rho$",
         size=7.15)
    text(ax, cx - 6.0, py - 1.15,
         "Yield is the B_aged scenario at a 10 µm grain.", size=7.15)
    pill(ax, cx + 26.5, py - 1.15, "Stage 5")
    text(ax, cx, py - 4.35,
         "Population 200, 40 generations. Warm-started from the archive.",
         size=6.7, color=MUTED)
    text(ax, cx, py - 6.85,
         "E_proxy is the rule-of-mixtures modulus.",
         size=6.7, color=MUTED)

    down(ax, cx, propose, legal)

    rounded(ax, cx, legal[0], w, legal[1], "#ffffff")
    text(ax, cx, legal[0] + 4.55, "Make it legal", size=9.2, weight="bold")
    pill(ax, cx + w / 2 - 8.2, legal[0] + 4.55, "Stage 3")
    text(ax, cx, legal[0] + 1.15,
         "Integer at% on Ti–Al–V–Mo–Zr–Sn–Cr–Fe–Nb, summing to 100, inside the caps.",
         size=7.15)
    text(ax, cx, legal[0] - 1.35,
         "Mo-eq ≤ 16 wt%      Al-eq ≤ 9 wt%      density 3.8–4.8 g/cm³",
         size=7.15)
    text(ax, cx, legal[0] - 3.85,
         "Phase field from Mo-eq:  near-α < 2,   α+β < 10,   else metastable-β.",
         size=7.15)

    down(ax, cx, legal, dedup)

    rounded(ax, cx, dedup[0], w, dedup[1], "#ffffff")
    text(ax, cx, dedup[0] + 1.45, "Drop known alloys", size=9.2, weight="bold")
    text(ax, cx, dedup[0] - 1.55,
         "Skip a formula already in the certified or provisional archive.",
         size=7.2)

    down(ax, cx, dedup, choose)

    rounded(ax, cx, choose[0], w, choose[1], "#ffffff")
    text(ax, cx, choose[0] + 4.05, "Choose the CHGNet queue", size=9.2, weight="bold")
    text(ax, cx, choose[0] + 1.15,
         "A Gaussian process predicts C44 and ranks candidates by μ + 2σ.",
         size=7.15)
    text(ax, cx, choose[0] - 1.25,
         "Descriptors: Mo-eq, Al-eq, solute fraction, size misfit, shear modulus.",
         size=7.15)
    text(ax, cx, choose[0] - 3.7,
         "The training-set size is written to the ledger. The stop rule is below.",
         size=6.7, color=MUTED)

    # Enter Tier S on the left, then S → F → U.
    s_cx, f_cx, u_cx = cx - 24.6, cx, cx + 24.6
    s_top = tier_y + tier_h / 2
    elbow_y = choose[0] - choose[1] / 2 - 2.15
    ax.plot([cx, cx, s_cx], [choose[0] - choose[1] / 2 - 0.12, elbow_y, elbow_y],
            color=INK, lw=1.15, zorder=1)
    arrow(ax, s_cx, elbow_y, s_cx, s_top + 0.12)
    pill(ax, u_cx, (elbow_y + s_top) / 2, "Stage 4")

    tier_body = [
        (s_cx, "Tier S   screen", "Up to 50 formulas\n1 run, seed 42\nAdvance if C44 > 0"),
        (f_cx, "Tier F   floor", "Up to 10 formulas\n3 seeds\nAdvance if viol ≤ 0.50"),
        (u_cx, "Tier U   certify", "4 formulas, 9 runs each\n2 promotions + 2 by score\n3 seeds × 3 strains"),
    ]
    for x, title, body in tier_body:
        rounded(ax, x, tier_y, tier_w, tier_h, "#e7f0f8")
        text(ax, x, tier_y + 4.7, title, size=7.7, weight="bold")
        text(ax, x, tier_y - 1.35, body, size=6.7)
    arrow(ax, s_cx + tier_w / 2 + 0.25, tier_y, f_cx - tier_w / 2 - 0.25, tier_y)
    arrow(ax, f_cx + tier_w / 2 + 0.25, tier_y, u_cx - tier_w / 2 - 0.25, tier_y)

    u_bot = tier_y - tier_h / 2
    arrow(ax, u_cx, u_bot - 0.12, u_cx, born[0] + born[1] / 2 + 0.12)

    rounded(ax, cx, born[0], w, born[1], "#f7f5f2", ec=RULE)
    text(ax, cx, born[0],
         "One CHGNet 0.3 run: 54-atom cell, then C11, C12, C44.  "
         "It fails when C44 ≤ 0 or C11 − C12 ≤ 0.",
         size=6.7, color=MUTED)

    file_title_y = file_y + file_h / 2 - 1.35
    arrow(ax, cx, born[0] - born[1] / 2 - 0.12, cx, file_title_y + 1.7)
    text(ax, cx, file_title_y, "File the result", size=9.0, weight="bold")
    outcomes = [
        ("Certified", "≥ 9 runs\nviol < 0.20\ngates pass", "#e5f3e8", "#1d6b32"),
        ("Provisional", "≥ 3 runs\nviol < 0.50\npromotable later", "#fdecd9", "#9a5410"),
        ("Screened", "Fewer than 3 runs\n\nCan be proposed again", "#f3f5f7", "#3d4d5c"),
        ("Vetoed", "viol ≥ 0.50\nor a known Pugh\nor hull value fails", "#f8e8e6", "#8c3a32"),
    ]
    ow, ogap = 16.6, 1.7
    row_w = 4 * ow + 3 * ogap
    ox0 = cx - row_w / 2 + ow / 2
    oy = file_y - 0.85
    oh = 11.6
    for i, (title, body, fc, tc) in enumerate(outcomes):
        card(ax, ox0 + i * (ow + ogap), oy, ow, oh, title, body, fc, tc)
    text(ax, cx, file_y - file_h / 2 + 0.85,
         "Certifying an alloy removes its provisional row.",
         size=6.5, color=MUTED)

    arrow(ax, cx, file_y - file_h / 2 - 0.15, cx, front[0] + front[1] / 2 + 0.12)

    rounded(ax, cx, front[0], w, front[1], "#f7f5f2")
    text(ax, cx - 6, front[0] + 1.35, "Update the Ashby front", size=9.0, weight="bold")
    pill(ax, cx + w / 2 - 8.2, front[0] + 1.35, "Stage 6")
    text(ax, cx, front[0] - 1.7,
         "Non-dominated certified and provisional alloys. The stop rule uses the certified front.",
         size=6.9)

    down(ax, cx, front, datasheet)

    rounded(ax, cx, datasheet[0], w, datasheet[1], "#ffffff")
    text(ax, cx - 8, datasheet[0] + 2.55, "Datasheet lock", size=9.2, weight="bold")
    pill(ax, cx + w / 2 - 8.2, datasheet[0] + 2.55, "Stage 7")
    text(ax, cx, datasheet[0] - 0.35,
         "Locked errors: raw density 1.87, calibrated density 1.00, yield 7.20.",
         size=7.15)
    text(ax, cx, datasheet[0] - 2.85,
         "A failure aborts the iteration. Nothing is committed.",
         size=7.15)

    down(ax, cx, datasheet, stop_rule)

    rounded(ax, cx, stop_rule[0], w, stop_rule[1], "#ffffff")
    text(ax, cx, stop_rule[0] + 3.55, "Stop or continue", size=9.2, weight="bold")
    text(ax, cx, stop_rule[0] + 0.35,
         "Stop after two iterations that certify nothing and gain under 1% hypervolume,",
         size=7.05)
    text(ax, cx, stop_rule[0] - 2.05,
         "or when 10 real iterations are reached. Reference (21.0, 2.25).",
         size=7.05)
    text(ax, cx, stop_rule[0] - 4.35, "Pre-registered rule. Either condition ends the search.",
         size=6.7, color=MUTED)

    dcx, dcy, dw, dh = cx, stop_rule[0] - stop_rule[1] / 2 - 7.6, 14.0, 8.0
    ax.add_patch(Polygon(
        [(dcx, dcy + dh / 2), (dcx + dw / 2, dcy),
         (dcx, dcy - dh / 2), (dcx - dw / 2, dcy)],
        closed=True, facecolor="#fff8e8", edgecolor=INK, linewidth=1.15, zorder=2,
    ))
    text(ax, dcx, dcy + 0.2, "Stop?", size=8.2, weight="bold")
    arrow(ax, cx, stop_rule[0] - stop_rule[1] / 2 - 0.12, dcx, dcy + dh / 2 + 0.12)

    stop_w, stop_h = 26.5, 8.2
    stop_x = dcx + dw / 2 + 3.6 + stop_w / 2
    rounded(ax, stop_x, dcy, stop_w, stop_h, "#1f4e79", ec="#1f4e79")
    text(ax, stop_x, dcy + 1.35, "STOP", size=8.4, weight="bold", color="white")
    text(ax, stop_x, dcy - 1.45, "tag v2.0-loop-closed\nexit code 10", size=6.7, color="white")
    arrow(ax, dcx + dw / 2 + 0.15, dcy, stop_x - stop_w / 2 - 0.12, dcy)
    text(ax, dcx + dw / 2 + 2.15, dcy + 1.55, "yes", size=7.0, color=MUTED)

    rail = 8.0
    y_join = propose[0]
    ax.plot([dcx - dw / 2, rail, rail], [dcy, dcy, y_join],
            color=INK, lw=1.15, solid_capstyle="round", zorder=1)
    arrow(ax, rail, y_join, cx - w / 2 - 0.08, y_join)
    text(ax, rail + 1.15, (dcy + y_join) / 2,
         "CONTINUE\nnext iteration,\nwarm-started\nfrom the updated\narchive",
         size=6.5, color=MUTED, ha="left")
    text(ax, dcx - dw / 2 - 2.5, dcy + 2.1, "no", size=7.0, color=MUTED)

    content_top = propose[0] + propose[1] / 2
    content_bot = dcy - dh / 2
    pad_top, pad_bot = 0.8, 1.0
    ax.set_ylim(content_bot - pad_bot, content_top + pad_top)
    span = (content_top + pad_top) - (content_bot - pad_bot)
    ipu = 0.0530
    top_in, bot_in = 0.50, 0.28
    fig_h = span * ipu + top_in + bot_in
    fig.set_size_inches(8.6, fig_h, forward=True)
    fig.subplots_adjust(left=0.012, right=0.988,
                        bottom=bot_in / fig_h, top=1 - top_in / fig_h)
    fig.text(0.50, 1 - 0.05 / fig_h, "One iteration of the closed loop",
             ha="center", va="top", fontsize=13, color=INK, fontweight="bold")
    fig.text(0.50, 1 - 0.30 / fig_h,
             "This is the inside of Stage 8.  A stage badge marks a step that reuses a frozen model.",
             ha="center", va="top", fontsize=7.6, color=MUTED)
    fig.text(0.50, 0.06 / fig_h,
             "Pugh and hull are applied when that formula already has a value.",
             ha="center", va="bottom", fontsize=6.8, color=MUTED)
    ARCH.mkdir(parents=True, exist_ok=True)
    png = ARCH / "flowchart_loopA.png"
    svg = ARCH / "flowchart_loopA.svg"
    fig.savefig(png, dpi=200, bbox_inches="tight", pad_inches=0.04, facecolor="white")
    fig.savefig(svg, bbox_inches="tight", pad_inches=0.04, facecolor="white")
    plt.close(fig)
    print(f"[Saved] {png}")
    print(f"[Saved] {svg}")


if __name__ == "__main__":
    main()
