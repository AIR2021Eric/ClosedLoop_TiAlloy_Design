"""One-command guarded iteration:
loop_A_optimizer -> equivalence gate -> stopping rule -> git commit (+ freeze tag on STOP).
ABORTS WITHOUT COMMITTING if the loop crashes or the equivalence gate fails.
Exit codes: 0 = CONTINUE, 10 = STOP rule fired, other = aborted.
"""
import argparse, re, subprocess, sys
from pathlib import Path
import os

REPO = Path(__file__).resolve().parents[1]
PY = sys.executable

def run(cmd, label):
    print(f"\n>>> {label}: {' '.join(str(c) for c in cmd)}", flush=True)
    env = {**os.environ, "PYTHONUNBUFFERED": "1", "PYTHONIOENCODING": "utf-8"}  # [v2.6] cp1252-pipe + ordering fix
    p = subprocess.Popen([str(c) for c in cmd], cwd=REPO, env=env,
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                         text=True, bufsize=1, encoding="utf-8", errors="replace")
    out = []
    for line in p.stdout:
        print(line, end="", flush=True)
        out.append(line)
    p.wait()
    return subprocess.CompletedProcess(cmd, p.returncode, "".join(out), "")

def last_streak(out):
    rows = re.findall(r"^\s*(\d+)\s+(\d+)\s+([\d.]+)\s+([-\d.]+)\s+(True|False)\s+(\d+)", out, re.M)
    return rows[-1][5] if rows else "?"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--iter-id", type=int, default=None, help="default: max(iter_id)+1 from ledger")
    ap.add_argument("--no-commit", action="store_true")
    a = ap.parse_args()

    iter_id = a.iter_id
    if iter_id is None:
        import pandas as pd
        log = REPO / "data" / "iteration_log.csv"
        iter_id = int(pd.read_csv(log).iter_id.max()) + 1 if log.exists() else 1
    print(f"=== guarded iteration {iter_id} ===")

    # 1) the loop itself
    p = run([PY, REPO / "stage8_iteration" / "loop_A_optimizer.py", "--iter-id", str(iter_id)], "Loop A")
    if p.returncode != 0:
        sys.exit(f"[ABORT] loop crashed (exit {p.returncode}); NOTHING committed - inspect artifacts.")
    m = re.search(r"=== iteration (\d+) done \| certified=(\d+) provisional=(\d+) front=(\d+) ===", p.stdout)
    if not m:
        sys.exit("[ABORT] tail line unparseable; NOTHING committed.")
    cert, prov, front = m.group(2), m.group(3), m.group(4)

    # 2) equivalence gate = hard stop before any commit
    p = run([PY, REPO / "tests" / "test_v1_equivalence.py"], "equivalence gate")
    if p.returncode != 0 or "ALL EQUIVALENCE CHECKS PASSED" not in p.stdout:
        sys.exit("[ABORT] equivalence gate FAILED; NOTHING committed - do not trust archives.")

    # 3) pre-registered stopping rule
    p = run([PY, REPO / "stage8_iteration" / "stopping_check.py"], "stopping rule")
    # [v2.7] whitespace-tolerant verdict parse (stopping_check prints "=>  CONTINUE"/"=>  STOP")
    m = re.search(r"=>\s*(STOP|CONTINUE)", p.stdout)
    verdict = m.group(1) if m else "UNKNOWN"
    streak = last_streak(p.stdout)

    # 4) commit (skip if clean); freeze tag on STOP
    if a.no_commit:
        print("[skip commit] --no-commit")
    else:
        run(["git", "add", "-A"], "git add")
        st = subprocess.run(["git", "status", "--porcelain"], cwd=REPO, capture_output=True, text=True)
        if st.stdout.strip():
            msg = (f"Loop A iter{iter_id}: certified={cert} provisional={prov} front={front}; "
                   f"stopping={verdict} (streak={streak}); equiv=green")
            run(["git", "commit", "-m", msg], "git commit")
        else:
            print("[commit] working tree clean - nothing to commit")
        if verdict == "STOP":
            t = subprocess.run(["git", "tag", "v2.0-loop-closed"], cwd=REPO, capture_output=True, text=True)
            print("[freeze] tag v2.0-loop-closed created" if t.returncode == 0
                  else f"[freeze] tag note: {t.stderr.strip()}")

    print(f"\n=== guarded iteration {iter_id} complete | certified={cert} provisional={prov} "
          f"front={front} | stopping={verdict} (streak={streak}) ===")
    return 10 if verdict == "STOP" else 0

if __name__ == "__main__":
    sys.exit(main())