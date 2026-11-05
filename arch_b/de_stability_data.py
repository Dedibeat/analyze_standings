"""Resumable CPU feature preparation for the frozen DE stability experiment."""

import gzip
import hashlib
import json
import os
from pathlib import Path

import numpy as np

from arch_a import elo
from . import model, survival
from .context_fit import raw_by_contest, row_context
from .de_release_audit import DE
from .joint import load_joint_dataset
from .run import MIN_SOLVE_HOURS

ROOT = Path(__file__).resolve().parent.parent
RUN = ROOT / "de_stability_run"
SNAPSHOT = ROOT / "data/de_stability_inputs.json"
TRAIN = ("full", "half_a0", "half_b0", "half_a1", "half_b1", "quarter0", "quarter1")
STRESS = ("half_reserved", "quarter_reserved", "eighth_reserved", "event_only",
          "event_small", "mirror_balanced", "strength_pool", "strong", "weak")
VIEWS = TRAIN + STRESS


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


def check_inputs():
    if os.environ.get("ARCHB_EXTRA_CONTESTS"):
        raise RuntimeError("unset ARCHB_EXTRA_CONTESTS for the frozen experiment")
    snapshot = json.loads(SNAPSHOT.read_text())
    for name, expected in snapshot["sha256"].items():
        path = ROOT / name
        if not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise RuntimeError(f"missing or changed frozen input: {name}")
    if np.__version__ != snapshot["numpy"]:
        raise RuntimeError("install requirements-de-stability.txt to match the frozen NumPy version")
    return snapshot


def read_view(name, fingerprint):
    path = RUN / f"{name}.json.gz"
    if not path.exists():
        raise RuntimeError(f"missing view {name}; run prepare first")
    rec = json.loads(gzip.decompress(path.read_bytes()))
    expected = rec.pop("content_sha256")
    if digest(rec) != expected or rec["fingerprint"] != fingerprint or rec["view"] != name:
        raise RuntimeError(f"stale or corrupt view: {path}; move it aside and prepare again")
    return rec


def sample_rows(ds, ctx, anchor_boards, view, selector=None, eligible=None):
    """Sample whole identities on each board; return retained row indices."""
    kept = []
    for c in anchor_boards:
        rows = np.flatnonzero(ds.contest_of_row == c)
        team = ds.team_of_row[rows]
        seed = 20261105 + int(view[-1]) if view in TRAIN and view != "full" else 20261205
        rng = np.random.default_rng([seed, int(ds.contests[c])])
        teams = rng.permutation(np.unique(team))
        n = len(teams)
        if view == "full":
            chosen = teams
        elif view.startswith("half_b"):
            chosen = teams[n // 2:]
        elif view.startswith("half"):
            chosen = teams[:n // 2]
        elif view.startswith("quarter"):
            chosen = teams[:max(1, n // 4)]
        elif view == "eighth_reserved":
            chosen = teams[:max(1, n // 8)]
        elif view.startswith("strength") or view in ("strong", "weak"):
            teams = teams[eligible[teams]]
            order = teams[np.argsort(selector[teams], kind="stable")]
            half = len(order) // 2
            chosen = order if view == "strength_pool" else order[-half:] if view == "strong" and half else order[:half]
        else:
            event = np.array([t for t in teams if np.all((ctx[rows[team == t]] == 0)
                                                       & ds.official_of_row[rows[team == t]])], int)
            mirror = np.array([t for t in teams if np.all(ctx[rows[team == t]] > 0)], int)
            count = min(len(event) // 2, len(mirror))
            chosen = event if view == "event_only" else event[:2 * count] if view == "event_small" else np.r_[event[:count], mirror[:count]]
        kept.extend(rows[np.isin(team, chosen)].tolist())
    return np.array(kept, int)


_STATE = None


def initialize():
    global _STATE
    ds, _, _ = load_joint_dataset(min_solve_hours=MIN_SOLVE_HOURS)
    anchors = json.loads((ROOT / "data/de_stability_anchors.json").read_text())
    ci = {cid: i for i, cid in enumerate(ds.contests)}
    boards = sorted({ci[r["contest_id"]] for r in anchors})
    _STATE = ds, anchors, boards, row_context(ds, raw_by_contest())


def prepare_view(view):
    snapshot = check_inputs()
    fingerprint = digest(snapshot)
    if (RUN / f"{view}.json.gz").exists():
        read_view(view, fingerprint)
        return f"reused {view}"
    if _STATE is None:
        initialize()
    ds, anchors, boards, ctx = _STATE
    team, prob = ds.team_of_row[ds.obs_row], ds.obs_prob
    y = ds.obs_y.astype(float)
    excluded = np.array([], int)
    selector = eligible = None
    if view in ("strength_pool", "strong", "weak"):
        others = np.setdiff1d(np.arange(len(ds.contests)), boards)
        a = np.random.default_rng(20261305).permutation(others)[::2]
        cells_a = np.isin(ds.contest_of_row[ds.obs_row], a)
        cells_b = ~np.isin(ds.contest_of_row[ds.obs_row], np.r_[boards, a])
        selector, _, _ = model.fit(ds, obs=(team[cells_a], prob[cells_a], y[cells_a]), verbose=False)
        eligible = np.zeros(len(ds.teams), bool)
        eligible[np.intersect1d(team[cells_a], team[cells_b])] = True
        excluded = a
    rows = sample_rows(ds, ctx, boards, view, selector, eligible)
    active = ~np.isin(ds.contest_of_row, np.r_[boards, excluded])
    active[rows] = True
    cells = active[ds.obs_row]
    _, _, _, rho = survival._survival_observations(ds, duration_mask=cells)
    tb, bb, hb = model.fit(ds, obs=(team[cells], prob[cells], y[cells]), verbose=False)
    ts, bs, hs = survival.fit(ds, obs=(team[cells], prob[cells], y[cells], rho[cells]), verbose=False)
    lam = survival.LN2 * np.exp((ts[team[cells]] - bs[prob[cells]]) / elo.S) * rho[cells]
    se = 1 / np.sqrt(np.bincount(prob[cells], lam, len(bs)) / elo.S ** 2 + 1 / model.SIGMA_B ** 2)
    solves = np.bincount(prob[cells], y[cells], len(bs))
    fields = np.bincount(ds.contest_of_row[rows], minlength=len(ds.contests))
    pi = {(cid, label): p for p, (cid, label, _, _) in enumerate(ds.problems)}
    features, missing = [], []
    for anchor in anchors:
        p = pi[(anchor["contest_id"], anchor["problem_label"])]
        field = int(fields[ds.contest_of_problem[p]])
        if not field:
            missing.append(anchor["row_id"])
            continue
        r = {**anchor, "raw_b": round(float(bs[p]), 1), "b_bin": round(float(bb[p]), 1),
             "conditional_fit_se": round(float(se[p]), 1), "solve_rate": float(solves[p] / field),
             "log_field_size": float(np.log1p(field))}
        r["binary_minus_survival"] = r["b_bin"] - r["raw_b"]
        features.append(r)
    full_difference = None
    if view == "full":
        full_difference = max(abs(r[f] - a[f]) for r, a in zip(features, anchors) for f in DE)
        if missing or full_difference > 0.11:
            raise RuntimeError(f"full refit does not reproduce anchor features: {full_difference}")
        features = anchors  # released rounded features reproduce the exact clipped-DE benchmark
    rec = {"fingerprint": fingerprint, "view": view, "rows": features, "missing_rows": missing,
           "kept_anchor_rows": rows.tolist(), "excluded_contests": [ds.contests[c] for c in excluded],
           "binary_iterations": len(hb), "survival_iterations": len(hs),
           "binary_final_delta": float(hb[-1]), "survival_final_delta": float(hs[-1]),
           "full_max_feature_difference": full_difference}
    payload = {**rec, "content_sha256": digest(rec)}
    RUN.mkdir(exist_ok=True)
    path = RUN / f"{view}.json.gz"
    tmp = path.with_suffix(".tmp")
    tmp.write_bytes(gzip.compress(json.dumps(payload, allow_nan=False).encode(), mtime=0))
    tmp.replace(path)
    return f"prepared {view}: {len(features)} problems, {len(missing)} missing"
