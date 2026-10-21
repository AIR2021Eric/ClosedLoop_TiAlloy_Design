# Live front against commercial baselines

The eleven labelled alloys are the live Ashby front at iteration 10: certified and provisional alloys that no other archived alloy dominates. The eight comparison alloys are the Stage 7 datasheet set in `data/stage7_audit_report.csv`.

Two scorings are kept apart. Panel A and the datasheet columns use measured modulus, density, and the published yield band. Panel B and the model columns score those same alloys with the search's own recipe: B_aged yield at the declared datasheet family (`YS_calc`), inverse rule-of-mixtures density (`rho_calc`), and the rule-of-mixtures modulus `E_proxy`. Discovered yields remain the B_aged calculation. They are not measured tensile strengths.

On the datasheet scoring, the highest bending-strength index is **Ti-5553 and Ti-10-2-3** at 24.28 (upper yield 1200 MPa, ρ = 4.65 g/cm³). The highest buckling index is **Ti-6242** at 2.413. Ti-6Al-4V's upper specific strength is 248.3 MPa·cm³/g.

On the model scoring, the highest bending-strength index is **Ti-5553** at 25.05, and the highest buckling index is **Ti-6Al-4V** at 2.418.

A labelled alloy can lead one index and still sit behind a commercial alloy on the other. CP-Ti Grade 2 is in the tables and below the plotted window.

## Where the labelled front is higher

- Bending index against the datasheet upper bounds: all eleven are above Ti-5553 and Ti-10-2-3 (24.28). Ti69Al15V16 is +9.2%. Ti79Al15Cr4Fe2 is +0.1%.
- Buckling index against the datasheets: Ti69Al15V16, Ti70Al15V14Cr1, Ti70Al15V13Cr2 are below Ti-6242 (2.413), by -1.7% to -0.7%. From Ti72Al15V9Cr4 to the right, the front is above every commercial buckling index. The largest gain is Ti79Al15Cr4Fe2 at +2.4%.
- Both indices at once, using each frame alloy's upper datasheet yield: Ti72Al15V9Cr4 and the alloys to its right beat all 7 frame alloys. The three strength-arm leaders do not, because Ti-6Al-4V and Ti-6242 remain slightly stiffer.
- Same model: the strength arm stays above Ti-5553's bending index (25.05), by +4.3% to +5.9%. The stiffness arm falls short of that model bending index, by -2.5% to -3.0%, and stays ahead on buckling.
- Specific strength against Ti-6Al-4V's upper datasheet value (248.3 MPa·cm³/g): +16.1% at Ti69Al15V16, down to +0.4% at Ti83Al14Cr3.


## Datasheet positions

| alloy | family | E (GPa) | ρ (g/cm³) | YS band (MPa) | bending index | buckling index | specific strength (MPa·cm³/g) |
|---|---|---:|---:|---:|---:|---:|---:|
| Ti-6Al-4V | alpha+beta | 114 | 4.43 | 880–1100 | 20.73–24.05 | 2.410 | 198.6–248.3 |
| Ti-6242 | near-alpha | 120 | 4.54 | 900–1000 | 20.53–22.03 | 2.413 | 198.2–220.3 |
| Ti-6246 | alpha+beta | 120 | 4.68 | 950–1050 | 20.65–22.07 | 2.341 | 203.0–224.4 |
| Ti-5553 | metastable-beta | 110 | 4.65 | 1100–1200 | 22.92–24.28 | 2.256 | 236.6–258.1 |
| Ti-10-2-3 | metastable-beta | 110 | 4.65 | 1100–1200 | 22.92–24.28 | 2.256 | 236.6–258.1 |
| Ti-15-3-3-3 | metastable-beta | 105 | 4.90 | 1000–1150 | 20.41–22.40 | 2.091 | 204.1–234.7 |
| Beta C | metastable-beta | 110 | 4.95 | 1100–1250 | 21.53–23.44 | 2.119 | 222.2–252.5 |
| CP-Ti Gr2 | cp | 105 | 4.51 | 275–345 | 9.38–10.91 | 2.272 | 61.0–76.5 |

## Same-model positions

Yield uses the datasheet family, as in the Stage 7 audit. Density is the uncalibrated inverse rule of mixtures. Modulus is `E_proxy`.

| alloy | family | E_proxy (GPa) | ρ_model | σ_Baged (MPa) | bending index | buckling index | specific strength |
|---|---|---:|---:|---:|---:|---:|---:|
| Ti-6Al-4V | alpha+beta | 112.2 | 4.380 | 1065 | 23.81 | 2.418 | 243.2 |
| Ti-6242 | near-alpha | 111.7 | 4.469 | 968 | 21.90 | 2.365 | 216.6 |
| Ti-6246 | alpha+beta | 114.1 | 4.571 | 1077 | 22.99 | 2.337 | 235.6 |
| Ti-5553 | metastable-beta | 119.6 | 4.596 | 1235 | 25.05 | 2.379 | 268.7 |
| Ti-10-2-3 | metastable-beta | 116.9 | 4.577 | 1225 | 25.01 | 2.362 | 267.6 |
| Ti-15-3-3-3 | metastable-beta | 118.5 | 4.707 | 1254 | 24.71 | 2.313 | 266.4 |
| Beta C | metastable-beta | 124.1 | 4.787 | 1252 | 24.27 | 2.327 | 261.5 |
| CP-Ti Gr2 | cp | 116.5 | 4.510 | 300 | 9.94 | 2.393 | 66.5 |

## Labelled front versus the best commercial alloy

Bending and buckling deltas use the best frame alloy in that column (datasheet bending: Ti-5553 and Ti-10-2-3; datasheet buckling: Ti-6242; model bending: Ti-5553; model buckling: Ti-6Al-4V). Specific-strength deltas use Ti-6Al-4V. “Dominates” counts how many of the seven frame alloys the row beats on both indices at once. The datasheet count uses each alloy's upper yield. CP-Ti is excluded from that count.

| formula | class | runs | viol | bending | vs best datasheet | vs best model | buckling | vs best datasheet | vs best model | σ/ρ | vs Ti-64 upper | vs Ti-64 model | dominates (datasheet) | dominates (model) |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Ti69Al15V16 | certified | 9 | 0.00 | 26.53 | +9.2% | +5.9% | 2.372 | -1.7% | -1.9% | 288.3 | +16.1% | +18.6% | 5/7 | 5/7 |
| Ti70Al15V14Cr1 | certified | 9 | 0.00 | 26.52 | +9.2% | +5.9% | 2.387 | -1.1% | -1.3% | 287.9 | +15.9% | +18.4% | 5/7 | 6/7 |
| Ti70Al15V13Cr2 | certified | 9 | 0.00 | 26.48 | +9.0% | +5.7% | 2.396 | -0.7% | -0.9% | 287.5 | +15.8% | +18.2% | 5/7 | 6/7 |
| Ti72Al15V9Cr4 | certified | 9 | 0.00 | 26.46 | +9.0% | +5.6% | 2.424 | +0.5% | +0.2% | 286.6 | +15.4% | +17.9% | 7/7 | 7/7 |
| Ti72Al15V7Cr4Fe2 | provisional | 3 | 0.00 | 26.33 | +8.4% | +5.1% | 2.430 | +0.7% | +0.5% | 285.3 | +14.9% | +17.3% | 7/7 | 7/7 |
| Ti74Al14V6Cr4Fe2 | provisional | 3 | 0.00 | 26.19 | +7.8% | +4.6% | 2.431 | +0.8% | +0.5% | 283.2 | +14.1% | +16.5% | 7/7 | 7/7 |
| Ti74Al14V5Cr4Fe3 | provisional | 9 | 0.33 | 26.13 | +7.6% | +4.3% | 2.434 | +0.9% | +0.6% | 282.6 | +13.8% | +16.2% | 7/7 | 7/7 |
| Ti83Al14V3 | certified | 9 | 0.00 | 24.42 | +0.6% | -2.5% | 2.440 | +1.1% | +0.9% | 250.3 | +0.8% | +3.0% | 7/7 | 4/7 |
| Ti81Al15Cr2Fe2 | provisional | 3 | 0.00 | 24.39 | +0.4% | -2.6% | 2.464 | +2.1% | +1.9% | 250.7 | +1.0% | +3.1% | 7/7 | 4/7 |
| Ti83Al14Cr3 | provisional | 3 | 0.00 | 24.32 | +0.1% | -2.9% | 2.467 | +2.2% | +2.0% | 249.4 | +0.4% | +2.6% | 7/7 | 4/7 |
| Ti79Al15Cr4Fe2 | provisional | 3 | 0.00 | 24.30 | +0.1% | -3.0% | 2.471 | +2.4% | +2.2% | 250.5 | +0.9% | +3.0% | 7/7 | 4/7 |

Positive means the labelled alloy is higher than that reference. Ti69Al15V16 carries `SS_LINEAR_EDGE`: its solute fraction is far from the 0.10 calibration point of the solid-solution term.
