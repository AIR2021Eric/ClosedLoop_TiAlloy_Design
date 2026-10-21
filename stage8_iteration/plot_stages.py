"""Eight-stage map of the closed-loop titanium design framework.

Writes two figures:
  results_archive/flowchart_stages.png        how the stages connect
  results_archive/flowchart_stage_details.png one small flowchart per stage

Stage 6 is drawn twice on the overview. The frozen pipeline ranks the
CrabNet table before CHGNet, then re-ranks after the elastic ensemble.
Stage 8 is the loop; it reuses Stages 3–6 and re-checks Stage 7.
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

REPO = Path(__file__).resolve().parents[1]
ARCH = REPO / "results_archive"
INK = "#243140"
MUTED = "#5c6b7a"
RULE = "#c5ced6"


def rounded(ax, cx, cy, w, h, fc, ec=INK, lw=1.0):
    ax.add_patch(FancyBboxPatch(
        (cx - w / 2, cy - h / 2), w, h,
        boxstyle="round,pad=0.015,rounding_size=0.35",
        facecolor=fc, edgecolor=ec, linewidth=lw,
        transform=ax.transData, zorder=2, clip_on=False,
    ))


def label(ax, x, y, s, size=7.4, color=INK, weight="regular", ha="center", va="center",
          rotation=0):
    ax.text(x, y, s, ha=ha, va=va, fontsize=size, color=color,
            fontweight=weight, linespacing=1.22, rotation=rotation, zorder=3)


def arrow(ax, x1, y1, x2, y2):
    ax.annotate(
        "", xy=(x2, y2), xytext=(x1, y1),
        arrowprops=dict(arrowstyle="-|>", color=INK, lw=1.05,
                        mutation_scale=10, shrinkA=0, shrinkB=0),
        zorder=1,
    )


def box(ax, cx, cy, w, h, title, purpose, rule, fc, badge=None):
    """Name, then the question this stage answers, then the rule."""
    rounded(ax, cx, cy, w, h, fc)
    y = cy + h / 2 - 1.15
    if badge:
        label(ax, cx + w / 2 - 1.2, y, badge, size=6.0, color=MUTED,
              weight="bold", ha="right", va="top")
        y -= 2.15
    label(ax, cx, y, title, size=8.05, weight="bold", va="top")
    y -= 2.15 * (title.count("\n") + 1) + 0.15
    label(ax, cx, y, purpose, size=7.15, va="top")
    y -= 1.95 * (purpose.count("\n") + 1) + 0.45
    label(ax, cx, y, rule, size=6.45, color=MUTED, va="top")


def frame(fig, ax, y0, y1, ipu, width, title, subtitle, footer):
    """Clip the axes to the drawing and sit the title and footer against it."""
    pad_top, pad_bot = 0.8, 1.0
    ax.set_ylim(y0 - pad_bot, y1 + pad_top)
    span = (y1 + pad_top) - (y0 - pad_bot)
    top_in, bot_in = 0.50, 0.28
    fig_h = span * ipu + top_in + bot_in
    fig.set_size_inches(width, fig_h, forward=True)
    fig.subplots_adjust(left=0.012, right=0.988,
                        bottom=bot_in / fig_h, top=1 - top_in / fig_h)
    fig.text(0.50, 1 - 0.05 / fig_h, title, ha="center", va="top",
             fontsize=13, color=INK, fontweight="bold")
    fig.text(0.50, 1 - 0.30 / fig_h, subtitle, ha="center", va="top",
             fontsize=7.5, color=MUTED)
    fig.text(0.50, 0.06 / fig_h, footer, ha="center", va="bottom",
             fontsize=7.2, color=MUTED)


def save(fig, name):
    ARCH.mkdir(parents=True, exist_ok=True)
    png = ARCH / f"{name}.png"
    svg = ARCH / f"{name}.svg"
    fig.savefig(png, dpi=200, bbox_inches="tight", pad_inches=0.04, facecolor="white")
    fig.savefig(svg, bbox_inches="tight", pad_inches=0.04, facecolor="white")
    plt.close(fig)
    print(f"[Saved] {png}")


def _rail(ax, x, y_top, y_bot, caption):
    ax.plot([x, x], [y_bot, y_top], color=RULE, lw=1.35, solid_capstyle="butt", zorder=1)
    ax.plot([x - 1.15, x + 1.15], [y_top, y_top], color=RULE, lw=1.15, zorder=1)
    ax.plot([x - 1.15, x + 1.15], [y_bot, y_bot], color=RULE, lw=1.15, zorder=1)
    label(ax, x - 1.55, (y_top + y_bot) / 2, caption, size=6.5, color=MUTED,
          weight="bold", rotation=90)


def overview():
    fig, ax = plt.subplots(figsize=(8.7, 12.9))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 214)
    ax.axis("off")
    fig.patch.set_facecolor("white")

    cx, full_w = 58.0, 76.0
    left_cx, right_cx, branch_w = 38.2, 77.8, 36.4
    gap = 4.0
    y = 208.0

    def take(h, extra=0.0):
        nonlocal y
        cy = y - h / 2
        y = y - h - gap - extra
        return cy

    s1 = (cx, take(14.2), full_w, 14.2)
    s2 = (cx, take(14.2, extra=2.6), full_w, 14.2)
    branch_y = take(19.6)
    s3 = (left_cx, branch_y, branch_w, 19.6)
    s6a = (right_cx, branch_y, branch_w, 19.6)
    s4 = (right_cx, take(17.2), branch_w, 17.2)
    s6b = (cx, take(15.4), full_w, 15.4)
    s5 = (cx, take(14.6), full_w, 14.6)
    s7 = (cx, take(14.6, extra=1.4), full_w, 14.6)
    s8 = (cx, take(16.8), full_w, 16.8)

    box(ax, *s1, "Stage 1  ·  CrabNet screen",
        "Which compositions look promising?",
        "39,480 compositions. Keep every row that passes the screen.",
        "#eef3f8")
    box(ax, *s2, "Stage 2  ·  Export the survivors",
        "What table do the later stages read?",
        "13,650 rows passed. Sort them by specific stiffness. Keep a top 500.",
        "#ffffff")
    box(ax, *s3, "Stage 3  ·  Phase-field gates",
        "What kind of titanium is this?",
        "Label near-α, α+β, or metastable-β\nfrom the Mo-equivalent.\nReject a high Al-equivalent or Mo-equivalent.",
        "#ffffff")
    box(ax, *s6a, "Rank before elasticity",
        "Who should get a crystal calculation?",
        "On the top 500. Maximize stiffness,\nminimize hull distance,\nreward a Pugh ratio above 1.75.",
        "#f7f5f2", badge="Stage 6")
    box(ax, *s4, "Stage 4  ·  CHGNet elasticity",
        "Is the crystal elastically stable?",
        "54-atom cell. A run fails if\nC44 ≤ 0 or C11 − C12 ≤ 0.",
        "#e7f0f8")
    box(ax, *s6b, "Rank after elasticity",
        "Which alloys survive the stability check?",
        "Drop a formula if more than half of its runs are Born-unstable.",
        "#f7f5f2", badge="Stage 6")
    box(ax, *s5, "Stage 5  ·  Yield scenarios",
        "How strong is this alloy on paper?",
        "Phase-field base plus a solid-solution term.\nThe loop uses B_aged at a 10 µm grain.",
        "#ffffff")
    box(ax, *s7, "Stage 7  ·  Datasheet audit",
        "Do the models still match commercial alloys?",
        "Eight datasheets. Locked errors 1.87, 1.00, and 7.20.",
        "#ffffff")
    box(ax, *s8, "Stage 8  ·  Closed loop",
        "Search new formulas with the models above.",
        "Propose, gate, CHGNet tiers, file, datasheet check, then stop.\nOpen flowchart_loopA.png.",
        "#f4f7fb")

    def bottom(t):
        return t[1] - t[3] / 2

    def top(t):
        return t[1] + t[3] / 2

    arrow(ax, cx, bottom(s1) - 0.15, cx, top(s2) + 0.15)
    yfork = (bottom(s2) + top(s3)) / 2 + 0.15
    ax.plot([cx, cx], [bottom(s2) - 0.1, yfork], color=INK, lw=1.05, zorder=1)
    ax.plot([left_cx, right_cx], [yfork, yfork], color=INK, lw=1.05, zorder=1)
    arrow(ax, left_cx, yfork, left_cx, top(s3) + 0.12)
    arrow(ax, right_cx, yfork, right_cx, top(s6a) + 0.12)
    label(ax, left_cx, yfork + 1.35, "label the phase field", size=6.3, color=MUTED)
    label(ax, right_cx, yfork + 1.35, "shortlist for CHGNet", size=6.3, color=MUTED)
    arrow(ax, right_cx, bottom(s6a) - 0.12, right_cx, top(s4) + 0.12)
    arrow(ax, left_cx, bottom(s3) - 0.12, left_cx, top(s6b) + 0.12)
    arrow(ax, right_cx, bottom(s4) - 0.12, right_cx, top(s6b) + 0.12)
    for a, b in ((s6b, s5), (s5, s7), (s7, s8)):
        arrow(ax, cx, bottom(a) - 0.12, cx, top(b) + 0.12)

    _rail(ax, 8.2, top(s1), bottom(s7), "Run once")
    label(ax, 12.0, s8[1], "Repeated", size=6.6, color=MUTED, weight="bold")

    frame(fig, ax, bottom(s8), top(s1), 0.0551, 8.7,
          "Eight stages of the titanium design framework",
          "Stages 1–7 were run once and frozen.  Stage 6 is drawn twice: it ranks before CHGNet and again after it.",
          "Stage 8 reuses the Stage 3–6 models on new formulas and re-checks Stage 7.")
    save(fig, "flowchart_stages")


def mini(ax, title, purpose, steps, fc):
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis("off")
    ax.set_title(title, fontsize=8.5, color=INK, fontweight="bold", pad=2, loc="left")
    label(ax, 0.15, 9.62, purpose, size=6.7, color="#1f4e79", ha="left")
    n = len(steps)
    gap = 0.26
    top = 9.15
    h = (top - 0.15 - gap * (n - 1)) / n
    y = top
    for i, step in enumerate(steps):
        cy = y - h / 2
        rounded(ax, 5, cy, 9.2, h - 0.02, fc if i == 0 else "#ffffff", lw=0.9)
        label(ax, 5, cy, step, size=6.5)
        if i < n - 1:
            arrow(ax, 5, cy - h / 2 - 0.02, 5, cy - h / 2 - gap + 0.04)
        y -= h + gap


def details():
    fig, axes = plt.subplots(4, 2, figsize=(8.5, 11.6))
    fig.patch.set_facecolor("white")
    panels = [
        ("Stage 1  ·  CrabNet screen",
         "Which compositions look promising?",
         ["39,480 compositions, seed 42",
          "CrabNet predicts modulus, hull, and Pugh",
          "Keep the 13,650 rows that pass",
          "This screen is the Stage 2 input"],
         "#eef3f8"),
        ("Stage 2  ·  Export the survivors",
         "What table do the later stages read?",
         ["Read the CrabNet screen",
          "Keep the rows that passed",
          "Sort by consensus specific stiffness",
          "Every gated row, plus a top-500 file"],
         "#ffffff"),
        ("Stage 3  ·  Phase-field gates",
         "What kind of titanium is this?",
         ["Convert atomic percent to weight percent",
          "Compute the Mo-equivalent and Al-equivalent",
          "Label near-α, α+β, or metastable-β",
          "Drop Al-eq > 9 or Mo-eq > 16"],
         "#ffffff"),
        ("Stage 4  ·  CHGNet elasticity",
         "Is the crystal elastically stable?",
         ["hcp for near-α and α+β; bcc for β",
          "54-atom special-quasirandom cell",
          "Relax, then finite-difference C11, C12, C44",
          "A run fails if C44 ≤ 0 or C11 − C12 ≤ 0"],
         "#e7f0f8"),
        ("Stage 5  ·  Yield scenarios",
         "How strong is this alloy on paper?",
         ["Phase-field base for the aged or unaged case",
          "Add 400 MPa per solute fraction above 0.10",
          "Add Hall–Petch relative to a 10 µm grain",
          "The loop uses B_aged at 10 µm"],
         "#ffffff"),
        ("Stage 6  ·  Rank before and after elasticity",
         "Who should get a crystal calculation, and who survives it?",
         ["Before CHGNet: stiffness, hull, and Pugh",
          "After CHGNet: drop a formula if more than half its runs fail",
          "In the loop: rank on the two Ashby indices"],
         "#f7f5f2"),
        ("Stage 7  ·  Datasheet audit",
         "Do the models still match commercial alloys?",
         ["Eight commercial titanium datasheets",
          "Predict density and yield with the same models",
          "Compare with the published bands",
          "Locked errors: 1.87 / 1.00 / 7.20"],
         "#ffffff"),
        ("Stage 8  ·  Closed loop",
         "Search new formulas with the models above.",
         ["Propose, then apply the Stage 3 gates",
          "Choose the CHGNet queue",
          "Tiers S, F, and U file each alloy",
          "Datasheet lock, then stop or continue"],
         "#f4f7fb"),
    ]
    for ax, (title, purpose, steps, fc) in zip(axes.ravel(), panels):
        mini(ax, title, purpose, steps, fc)
    fig.suptitle("What each stage does", fontsize=13, color=INK, fontweight="bold", y=0.985)
    fig.text(0.50, 0.012,
             "Stage 1 is the CrabNet screen of 39,480 compositions.  Stages 2–7 are frozen.  Stage 8 is the loop.",
             ha="center", va="bottom", fontsize=7.4, color=MUTED)
    fig.tight_layout(rect=(0.02, 0.03, 0.98, 0.955), h_pad=2.2, w_pad=1.5)
    save(fig, "flowchart_stage_details")


if __name__ == "__main__":
    overview()
    details()
