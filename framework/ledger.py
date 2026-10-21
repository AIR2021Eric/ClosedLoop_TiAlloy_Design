"""framework/ledger.py - append-only iteration provenance for the closed loop.
[v2.5] snapshot() accepts a tag so re-runs of the same iter-id keep every snapshot."""
import json, hashlib, subprocess, datetime
import pandas as pd
from pathlib import Path
from . import config as C

LOG = C.DATA / "iteration_log.csv"
SNAP = C.ARCH / "iterations"
FIELDS = ["iter_id", "ts_utc", "git_commit", "config_sha", "pop_source", "pop_n",
          "n_proposed", "n_tierS", "n_tierF", "n_tierU", "run_ids",
          "new_certified", "new_provisional", "new_vetoed", "front_members",
          "decision", "next_action", "notes"]

def _git():
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"],
                                       cwd=C.REPO, text=True).strip()
    except Exception:
        return "unknown"

def _config_sha():
    return hashlib.sha256((C.REPO / "framework" / "config.py").read_bytes()).hexdigest()[:12]

def record(**kw):
    SNAP.mkdir(parents=True, exist_ok=True)
    row = {f: kw.get(f, "") for f in FIELDS}
    row["ts_utc"] = datetime.datetime.utcnow().isoformat(timespec="seconds")
    row["git_commit"] = _git(); row["config_sha"] = _config_sha()
    df = pd.read_csv(LOG) if LOG.exists() else pd.DataFrame(columns=FIELDS)
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    df.to_csv(LOG, index=False)
    return row

def snapshot(iter_id, payload: dict, tag: str = ""):
    SNAP.mkdir(parents=True, exist_ok=True)
    p = SNAP / f"iter_{iter_id:03d}{('_' + tag) if tag else ''}.json"
    p.write_text(json.dumps(payload, indent=2, default=str))
    return p