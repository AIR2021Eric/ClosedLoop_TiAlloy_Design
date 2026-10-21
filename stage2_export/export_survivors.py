import pandas as pd
from pathlib import Path

# Anchor to repo root regardless of where the script is run from
REPO_ROOT = Path(__file__).resolve().parents[1]      # .../ClosedLoop_TiAlloy_Design
PARENT    = REPO_ROOT.parent                         # .../surrogateModels

candidates = [
    PARENT / "CrabNet_TiAlloy_Test" / "results_archive" / "screen_exhaustive_39k_seed42" / "screening_results.csv",
    PARENT / "CrabNet_TiAlloy_Test" / "results_archive" / "screen_36467_seed42" / "screening_results.csv",
]
SRC = next((p for p in candidates if p.exists()), None)
if SRC is None:
    raise FileNotFoundError(
        "Could not locate CrabNet screening_results.csv. Tried:\n" +
        "\n".join(f"  - {p}" for p in candidates))

print(f"Reading: {SRC}")
df = pd.read_csv(SRC)
print(f"Loaded {len(df)} screened candidates; columns: {len(df.columns)}")

gated = df[df['pass_all'].astype(bool)].copy()
print(f"Gated survivors (pass_all): {len(gated)}")

cols = ['formula','Ti_at','Al_at','V_at','Mo_at','Zr_at','Sn_at','Cr_at','Fe_at','n_solutes',
        'K_nn','K_aflow','K_mp','K_proxy','K_spread','K_fold_std',
        'G_nn','G_proxy','G_fold_std','E_nn','E_proxy','E_consensus_diff_pct',
        'rho_proxy','hull_v1','hull_v2','pugh_proxy','spec_stiff','spec_stiff_cons',
        'flag_k_spread','flag_k_foldstd','flag_pugh','flag_red_team']
cols = [c for c in cols if c in gated.columns]
gated = gated[cols].sort_values('spec_stiff_cons', ascending=False)

out_all = REPO_ROOT / "data" / "stage2_gated_all.csv"
out_top = REPO_ROOT / "data" / "stage2_survivors.csv"
gated.to_csv(out_all, index=False)
gated.head(500).to_csv(out_top, index=False)

print(f"[Saved] {out_all} ({len(gated)} rows)")
print(f"[Saved] {out_top} (Top-500)")
print(gated.head(5)[['formula','spec_stiff_cons','hull_v2','pugh_proxy','K_spread']].to_string(index=False))