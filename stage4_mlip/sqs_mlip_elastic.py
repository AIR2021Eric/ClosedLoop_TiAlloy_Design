"""Stage 4: Phase-Aware MC-SQS + CHGNet Elastic Tensor.
Uses Stage 3 phase_field to assign HCP (alpha) or BCC (beta) lattices."""
import re
import numpy as np
import pandas as pd
from pathlib import Path
from ase.build import bulk
from ase.neighborlist import neighbor_list
from ase.optimize import BFGS
from chgnet.model.dynamics import CHGNetCalculator

REPO = Path(__file__).resolve().parents[1]
N_CELL, DELTA = 54, 0.015
EV_A3_TO_GPA = 160.21766208
RNG = np.random.default_rng(42)

def build_supercell(counts, phase_field):
    # Alpha/Alpha+Beta = HCP; Metastable-Beta = BCC
    if phase_field in ['alpha+beta', 'near-alpha']:
        # HCP Ti: a=2.95, c=4.68. repeat(3,3,3) = 54 atoms
        base = bulk('Ti', 'hcp', a=2.95, c=4.68).repeat((3, 3, 3))
    else:
        # BCC Ti: a=3.30. repeat(3,3,3) = 54 atoms
        base = bulk('Ti', 'bcc', a=3.30, cubic=True).repeat((3, 3, 3))
        
    syms = [el for el, n in counts.items() for _ in range(n)]
    RNG.shuffle(syms)
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

def mc_sqs(atoms, counts, steps=4000):
    conc = {k: v / sum(counts.values()) for k, v in counts.items()}
    syms = np.array(atoms.get_chemical_symbols()); cur = sro_objective(atoms, conc)
    for _ in range(steps):
        p, q = RNG.choice(len(syms), 2, replace=False)
        if syms[p] == syms[q]: continue
        syms[[p, q]] = syms[[q, p]]; atoms.set_chemical_symbols(syms.tolist())
        new = sro_objective(atoms, conc)
        if new <= cur: cur = new
        else: syms[[p, q]] = syms[[q, p]]; atoms.set_chemical_symbols(syms.tolist())
    return atoms, cur

def voigt_strain(g):
    return np.array([[g[0], g[5]/2, g[4]/2],
                     [g[5]/2, g[1], g[3]/2],
                     [g[4]/2, g[3]/2, g[2]]])

def strain_energy(atoms0, calc, g, fmax=0.01):
    a = atoms0.copy(); a.calc = calc
    a.set_cell(np.dot(a.cell, (np.eye(3) + voigt_strain(g)).T), scale_atoms=True)
    BFGS(a, logfile=None).run(fmax=fmax, steps=300)
    return a.get_potential_energy()

def elastic_constants(atoms0, calc, delta=DELTA):
    V = atoms0.get_volume()
    E0 = strain_energy(atoms0, calc, np.zeros(6))
    def u(g): return (strain_energy(atoms0, calc, g) + strain_energy(atoms0, calc, -g) - 2*E0) / 2.0
    U = {}
    for i in range(6):
        g = np.zeros(6); g[i] = delta; U[i] = u(g)
    C = np.zeros((6, 6))
    for i in range(6): C[i, i] = 2 * U[i] / (V * delta**2)
    for i, j in [(0, 1), (0, 2), (1, 2)]:
        g = np.zeros(6); g[i] = delta; g[j] = delta
        C[i, j] = C[j, i] = (u(g) - U[i] - U[j]) / (V * delta**2)
    return C * EV_A3_TO_GPA

def vrh(C):
    S = np.linalg.inv(C)
    KV = (C[0,0]+C[1,1]+C[2,2] + 2*(C[0,1]+C[0,2]+C[1,2])) / 9
    GV = (C[0,0]+C[1,1]+C[2,2] - (C[0,1]+C[0,2]+C[1,2]) + 3*(C[3,3]+C[4,4]+C[5,5])) / 15
    KR = 1.0 / (S[0,0]+S[1,1]+S[2,2] + 2*(S[0,1]+S[0,2]+S[1,2]))
    GR = 15.0 / (4*(S[0,0]+S[1,1]+S[2,2]) - 4*(S[0,1]+S[0,2]+S[1,2]) + 3*(S[3,3]+S[4,4]+S[5,5]))
    K, G = (KV+KR)/2, (GV+GR)/2
    return K, G, 9*K*G/(3*K+G)

# Load Pareto front AND Stage 3 phase gates
df_pareto = pd.read_csv(REPO / "data" / "pareto_front_current.csv")
df_stage3 = pd.read_csv(REPO / "data" / "stage3_tier2_phase_gates.csv")[['formula', 'phase_field']].set_index('formula')
df = df_pareto.join(df_stage3, on='formula').dropna(subset=['phase_field'])

src = pd.read_csv(REPO / "data" / "stage2_gated_all.csv").set_index('formula')
print(f"Stage 4 (Phase-Aware MC-SQS + CHGNet) on {len(df)} Pareto candidates...")

results = []
for _, row in df.iterrows():
    formula = row['formula']
    phase_field = row['phase_field']
    comp = {el: float(n) for el, n in re.findall(r'([A-Z][a-z]?)([\d\.]+)', formula)}
    tot = sum(comp.values())
    counts = {el: max(1, int(round(n / tot * N_CELL))) for el, n in comp.items()}
    counts[max(counts, key=counts.get)] += N_CELL - sum(counts.values())
    
    print(f"\n--- {formula} [{phase_field.upper()}]: 54-atom supercell {counts} ---")
    atoms, sro = mc_sqs(build_supercell(counts, phase_field), counts)
    print(f"MC-SQS first-shell SRO: {sro:.5f}")

    try:    calc = CHGNetCalculator(use_device='cuda')
    except Exception: calc = CHGNetCalculator(use_device='cpu')
    atoms.calc = calc
    BFGS(atoms, logfile=None).run(fmax=0.05, steps=300)
    print(f"Relaxed: {atoms.get_potential_energy()/len(atoms):.4f} eV/atom")

    C = elastic_constants(atoms, calc)
    K, G, E = vrh(C)
    
    # Flag mechanical instability
    stable = "STABLE" if (C[0,0] > abs(C[0,1]) and C[3,3] > 0 and G > 0) else "UNSTABLE_0K"
    
    print(f"MLIP  K={K:.1f} G={G:.1f} E={E:.1f} GPa  (C11={C[0,0]:.0f}, C12={C[0,1]:.0f}, C44={C[3,3]:.0f}) -> {stable}")
    crab = src.loc[formula] if formula in src.index else None
    if crab is not None:
        print(f"CrabNet K_nn={crab.K_nn:.1f} G_nn={crab.G_nn:.1f} E_nn={crab.E_nn:.1f} | E_proxy={crab.E_proxy:.1f}")
        
    results.append({"formula": formula, "phase_field": phase_field, "sro": round(sro, 5),
                    "K_mlip": round(K, 1), "G_mlip": round(G, 1), "E_mlip": round(E, 1),
                    "stability": stable,
                    "K_crabnet": round(crab.K_nn, 1) if crab is not None else np.nan,
                    "E_crabnet": round(crab.E_nn, 1) if crab is not None else np.nan,
                    "E_proxy": round(crab.E_proxy, 1) if crab is not None else np.nan})

out = pd.DataFrame(results)
out.to_csv(REPO / "data" / "stage4_mlip_elastic.csv", index=False)
print(f"\n[Saved] data/stage4_mlip_elastic.csv")