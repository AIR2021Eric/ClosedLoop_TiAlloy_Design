# Stages 1–8

The boxes on `flowchart_loopA.png` are the steps inside one iteration. Stage 8 is that whole iteration. Stages 1–7 were run once and frozen under the tag `v1.0-validated`. The loop does not retrain them.

How the pieces connect is `flowchart_stages.png`. What happens inside each stage is `flowchart_stage_details.png`. The inside of Stage 8 is `flowchart_loopA.png`. A block-by-block reading of the figures is `flowchart_guide.md`.

Stage 6 appears twice on the overview. The frozen pipeline ranks the CrabNet table before any CHGNet run, then ranks again after the elastic ensemble. Stage 8 later uses a third, simpler ranking: the two Ashby indices.

## Stage 1 — CrabNet screen

This stage is not a folder in this repository. It is the screen in the sibling project `CrabNet_TiAlloy_Test`, seed 42. Stage 2 read the exhaustive screen: 39,480 compositions. CrabNet predicts modulus terms, a hull distance, and a Pugh ratio for each composition. A row that passes every screen is marked `pass_all` (13,650 rows). The element list in that screen is Ti, Al, V, Mo, Zr, Sn, Cr, and Fe. Niobium enters in Stage 8.

## Stage 2 — Export the gated survivors

`stage2_export/export_survivors.py` reads the CrabNet CSV, keeps `pass_all`, and sorts by consensus specific stiffness. It writes every gated row to `data/stage2_gated_all.csv` and the top 500 to `data/stage2_survivors.csv`.

That file is also the only source of a hull distance during the loop. If a new formula is not already in it, `hull_src` stays `pending`. A pending hull does not by itself reject the alloy.

## Stage 3 — Phase-field gates

`stage3_calphad/moeq_aleq_gates.py` and `framework/physics.py` convert atomic percent to weight percent and compute the Mo-equivalent and Al-equivalent used for titanium alloys. The phase-field label follows the Mo-equivalent: near-α below 2, α+β below 10, otherwise metastable-β. A composition fails the gate if Al_eq is above 9 wt% or Mo_eq is above 16 wt%.

Density, used with these gates in the loop, is the inverse rule-of-mixtures and must lie between 3.8 and 4.8 g/cm³. Proposals must also stay inside the atomic-percent caps in `framework/config.py`. The phase label used throughout is the Mo-equivalent cutoff above.

## Stage 4 — CHGNet elasticity

`stage4_mlip/stage4_uq_bands.py` is the only GPU step. It builds a 54-atom cell, hexagonal for near-α and α+β and body-centered cubic for metastable-β, then shuffles the atoms into a special-quasirandom arrangement. CHGNet 0.3 relaxes the cell. Finite differences give C11, C12, and C44.

A run is a Born violation when C44 ≤ 0 or C11 − C12 ≤ 0. Across the ensemble, a violation fraction above 0.50 is unstable, above 0.20 is marginal, and otherwise the cell is soft but stable.

The frozen v1 files are `data/stage4_uq_bands.csv` and `data/stage4_uq_raw.csv`. The loop is not allowed to overwrite them. Each iteration writes its own files, `stage4_uq_{raw,bands}_it<N>{S,F,U}.csv`.

Inside the loop the same engine is called in three budgets:

- Tier S: up to 50 formulas, one run (seed 42, strain 0.015). Advance if C44_med > 0.
- Tier F: up to 10 formulas, three seeds. Advance if the violation fraction is at most 0.50.
- Tier U: 4 formulas, three seeds and three strains, nine runs. Two of the four slots are reserved for the highest-strength provisionals that still have fewer than nine runs. The other two follow the acquisition score.

## Stage 5 — Yield scenarios

`framework/strength.py` is a closed-form model, not a tensile test:

σ_y = base(scenario, phase field) + 400 MPa × (solute fraction − 0.10) + a Hall–Petch term relative to a 10 µm grain.

The loop uses scenario `B_aged` at that 10 µm reference, so the Hall–Petch increment is zero. The metastable-β aged base is 1200 MPa. The α+β aged base is 1050 MPa. The near-α aged base is 950 MPa. A formula with solute fraction at least 0.20 away from 0.10 is flagged `SS_LINEAR_EDGE`, meaning the linear solid-solution term is being used at the edge of its declared range. A stored solute fraction of 0.30 falls one floating-point step short of that test, so those alloys are flagged OK.

`stage5_strength/stage5_strength_scenarios.py` is the original one-time table on the carried alloys. The loop calls the same formula for every new proposal.

## Stage 6 — Pareto ranking

There are three rankings, and they do not use the same objectives.

The first ranking, `stage6_pareto/pareto_front_now.py`, runs on `stage2_survivors.csv` before CHGNet. It maximizes consensus specific stiffness, minimizes the hull distance, and rewards a Pugh ratio above 1.75. The saved front is `data/pareto_front_current.csv`. That file is the old v1 front. It is not the live loop front.

The second ranking, `stage6_pareto/repareto_ensemble.py`, joins that front to the Stage 4 bands. A formula whose ensemble is Born-unstable on more than half of its runs is vetoed. The rest are carried. Stiffness is reported two ways: the CHGNet median modulus, and the rule-of-mixtures modulus. The carried list is what Stage 5 scores.

The loop ranking, `framework/pareto.py`, keeps only two objectives, both maximized: σ_y,aged^(2/3) / ρ and E_proxy^(1/2) / ρ. E_proxy is the rule-of-mixtures modulus from the elemental bulk and shear moduli. The CHGNet median modulus is stored as E_med and does not enter the Ashby index. The live front is the non-dominated set of the certified and provisional archives. The stopping rule uses only the certified members of that front.

## Stage 7 — Datasheet audit

`stage7_audit/blind_holdout_audit.py` scores eight commercial alloys with the same density and yield models: Ti-6Al-4V, Ti-6242, Ti-6246, Ti-5553, Ti-10-2-3, Ti-15-3-3-3, Beta C, and CP-Ti Grade 2. The comparison is written to `data/stage7_audit_report.csv`.

`tests/test_v1_equivalence.py` recomputes that table from the current code and requires the mean absolute errors to stay at 1.87 for raw density, 1.00 for calibrated density, and 7.20 for yield strength, on the v1 alloy subset. Stage 8 runs this test after every iteration. A failure aborts the commit. The loop does not get to move those error bars.

For the paper, the Ti-6Al-4V row in that audit file is the anchor: ρ = 4.43 g/cm³ and a yield-strength band of 880–1100 MPa. The upper specific strength is 248.3 MPa·cm³/g. Loop yields are the B_aged scenario, not measured tensile results.

## Stage 8 — Closed loop

`stage8_iteration/run_iteration.py` is one guarded iteration:

1. `loop_A_optimizer.py` proposes and evaluates.
2. The Stage 7 equivalence test must pass.
3. `stopping_check.py` applies the rule that was declared before the later iterations.
4. The iteration is committed. A stop writes the tag `v2.0-loop-closed` and returns exit code 10.

Inside the optimizer, NSGA-II (population 200, 40 generations) proposes integer atomic-percent alloys and is warm-started from the live archive. Stage 3 gates them. Formulas already certified or provisional are removed. A Gaussian process, trained on one C44 median per formula already screened, scores the rest with μ + 2σ. Stage 4 spends the tier budget. Stage 5 and Stage 6 assign the two Ashby indices and the archive class.

A formula is certified at nine or more runs, a violation fraction below 0.20, and a pass of the inline gates and of any soft gate whose number is already known (Pugh ratio at least 1.75, hull distance at most 0.05 eV/atom). It is provisional at three or more runs and a violation fraction below 0.50. It is vetoed at a violation fraction of 0.50 or higher, or when a known soft gate fails. Certifying a formula removes its provisional row.

The search stops if two consecutive real iterations add no certified alloy and the certified-front hypervolume grows by less than 1%, or if the real-iteration count reaches 10. The hypervolume reference point is (21.0, 2.25). The GP-label count and the Tier-S kill rate are printed and do not decide the stop.

Iteration 10 hit the cap. The stagnation clause had not fired. The certified archive holds 25 alloys, the provisional archive holds 55, and the certified-front hypervolume is 1.0740, unchanged from iteration 8. The tag on that commit is `v2.0-loop-closed`.

## What is frozen, and what the loop still writes

Stages 1–7 stay as they were validated. In particular the loop must not overwrite `data/stage4_uq_bands.csv`, `data/stage4_uq_raw.csv`, or `data/stage7_audit_report.csv`. New CHGNet evidence goes to iteration-scoped files. The certified and provisional archives, the ledger, and the iteration snapshots are the Stage 8 record.
