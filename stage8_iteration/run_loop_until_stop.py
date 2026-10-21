"""Unattended batch: repeat guarded iterations until the pre-registered STOP rule fires,
the equivalence gate fails, or --max-iters is reached. Human reviews the ledger afterwards."""
import argparse, subprocess, sys
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]

ap = argparse.ArgumentParser()
ap.add_argument("--max-iters", type=int, default=4, help="real iterations in THIS batch (cap 10 total)")
a = ap.parse_args()

for k in range(a.max_iters):
    p = subprocess.run([sys.executable, str(REPO / "stage8_iteration" / "run_iteration.py")], cwd=REPO)
    if p.returncode == 10:
        print("STOP rule fired - loop frozen at v2.0-loop-closed. Review ledger + slides; write the paper.")
        sys.exit(0)
    if p.returncode != 0:
        sys.exit(f"batch aborted after {k} iteration(s) (exit {p.returncode}) - human inspection required")
print("batch reached --max-iters without STOP; review before launching another batch.")