# How to read the flowcharts

Two pictures, two questions.

`flowchart_stages.png` is the whole pipeline, Stages 1–8. Stages 1–7 ran once and are frozen. Stage 8 is the search, and it ran ten times. `flowchart_stage_details.png` is the same eight stages, one small chart each.

`flowchart_loopA.png` is the inside of Stage 8 only: one iteration. Its boxes are named by the job they do. A small badge such as “Stage 5” means that step reuses a frozen model. The badge is not a new stage number.

## The stage map

The column is the order the frozen pipeline actually ran. Stage 6 appears twice on purpose: it ranks the table before any crystal calculation, and it ranks again after the elastic results are in. The left rail marks Stages 1–7 as run once and Stage 8 as the part that repeats.

After Stage 2 the path splits. The left branch labels the phase field. The right branch chooses who gets a CHGNet run. The two branches meet again at the second ranking.

### Stage 1 · CrabNet screen

Which compositions look promising?

This screen lives in the sibling project `CrabNet_TiAlloy_Test`, seed 42. The file Stage 2 read has 39,480 compositions. CrabNet predicts a modulus, a hull distance, and a Pugh ratio for each one, and marks the rows that pass every check. 13,650 rows passed. The palette in that screen is Ti, Al, V, Mo, Zr, Sn, Cr, and Fe. Niobium enters in Stage 8.

An earlier seed-42 file has 36,467 compositions. Stage 2 did not read that file. The count on the figure is the screen that was used.

### Stage 2 · Export the survivors

What table do the later stages read?

Keep the 13,650 rows that passed, sort them by consensus specific stiffness, and write every gated row plus a top-500 file. The first ranking uses that top 500. During the loop, this table is also where a hull distance is looked up. Pugh and hull are applied when that formula already has a value.

### Stage 3 · Phase-field gates

What kind of titanium is this?

Atomic percent is converted to weight percent. The Mo-equivalent sets the label: near-α below 2, α+β below 10, otherwise metastable-β. A composition fails when the Al-equivalent is above 9 wt% or the Mo-equivalent is above 16 wt%. In the loop the same gate also requires density between 3.8 and 4.8 g/cm³.

### Stage 6 · Rank before elasticity

Who should get a crystal calculation?

On the top 500, before any CHGNet run: maximize specific stiffness, minimize hull distance, and reward a Pugh ratio above 1.75. That shortlist is what Stage 4 spends the elastic calculation on.

### Stage 4 · CHGNet elasticity

Is the crystal elastically stable?

Build a 54-atom special-quasirandom cell, relax it with CHGNet 0.3, and compute C11, C12, and C44. A run fails when C44 ≤ 0 or C11 − C12 ≤ 0. The frozen files are this one-time ensemble. Each later iteration calls the same engine and writes its own files.

### Stage 6 · Rank after elasticity

Which alloys survive the stability check?

Join the shortlist to the Stage 3 labels and the Stage 4 bands. Drop a formula if more than half of its runs fail the Born check. Carry the rest into the yield model.

### Stage 5 · Yield scenarios

How strong is this alloy on paper?

Strength is a formula: a phase-field base, plus 400 MPa for each unit of solute fraction above 0.10, plus a Hall–Petch term. The loop uses the aged scenario `B_aged` at a 10 µm grain, so the Hall–Petch term is zero. That yield becomes the specific-strength objective. It is the declared scenario, not a measured tensile test.

### Stage 7 · Datasheet audit

Do the models still match commercial alloys?

The same density and yield models are scored on eight commercial alloys. The locked errors are 1.87 for raw density, 1.00 for calibrated density, and 7.20 for yield strength. Every iteration has to reproduce that lock before a commit.

### Stage 8 · Closed loop

Search new formulas with the models above.

Each iteration proposes, gates, spends three CHGNet budgets, files each alloy, updates the Ashby front, re-checks Stage 7, and then stops or continues. The inside of this box is `flowchart_loopA.png`.

## One iteration

The order matches `stage8_iteration/loop_A_optimizer.py`, then the datasheet check and the stop rule in `run_iteration.py`.

### Propose

Search integer compositions that raise both Ashby indices at once. Strength is σ_y,aged^(2/3) / ρ. Stiffness is E_proxy^(1/2) / ρ. E_proxy is the rule-of-mixtures modulus. The CHGNet modulus is stored and is not this stiffness. Yield is the Stage 5 `B_aged` number, computed here because the search needs it. Population 200, 40 generations, warm-started from alloys already in the archive.

### Make it legal

Turn each proposal into a legal composition and keep it only if the Stage 3 gates pass. Integer atomic percent on Ti–Al–V–Mo–Zr–Sn–Cr–Fe–Nb, summing to 100, inside the caps. Mo-equivalent at most 16 wt%, Al-equivalent at most 9 wt%, density from 3.8 to 4.8 g/cm³. The phase label follows the Mo-equivalent.

### Drop known alloys

Skip a formula that is already certified or provisional, so the crystal calculation is spent on something new.

### Choose the CHGNet queue

A Gaussian process predicts C44 from five descriptors (Mo-equivalent, Al-equivalent, solute fraction, size misfit, shear modulus) and ranks candidates by μ + 2σ. The training-set size is written to the ledger. The stop rule is the last box on this figure.

### Tier S, then Tier F, then Tier U

Spend a fixed CHGNet budget, cheapest filter first. The arrow enters Tier S.

- Tier S screens up to 50 formulas with one run (seed 42) and advances a formula when median C44 is positive.
- Tier F takes up to 10 of those, three seeds, and advances a formula when the violation fraction is at most 0.50.
- Tier U takes 4 formulas at nine runs each (3 seeds × 3 strains). Two slots promote strong provisionals that still have fewer than nine runs. The other two follow the acquisition score.

One run is a 54-atom cell and the three elastic constants. It fails when C44 ≤ 0 or C11 − C12 ≤ 0.

### File the result

Each alloy that received a run lands in one of four outcomes.

- Certified: at least 9 runs, violation fraction below 0.20, and the gates pass.
- Provisional: at least 3 runs and violation fraction below 0.50. Eligible for a later Tier U promotion.
- Screened: fewer than 3 runs. It can be proposed again.
- Vetoed: violation fraction at least 0.50, or a known Pugh ratio below 1.75, or a known hull distance above 0.05 eV/atom.

Certifying an alloy removes its provisional row. Pugh and hull are checked when that formula already has a value.

### Update the Ashby front

The live front is the non-dominated set of the certified and provisional archives, on the same two indices the proposer maximizes. The stop rule uses only the certified members of that front.

### Datasheet lock

Re-check Stage 7. The locked errors are 1.87, 1.00, and 7.20. A failure aborts the iteration and nothing is committed.

### Stop or continue

The rule was declared before the later iterations. Stop after two real iterations that certify nothing and grow the certified-front hypervolume by less than 1%, or when 10 real iterations are reached. The reference point is (21.0, 2.25). Either condition ends the search.

Yes writes the tag `v2.0-loop-closed` and returns exit code 10. No starts the next iteration from the updated archive.
