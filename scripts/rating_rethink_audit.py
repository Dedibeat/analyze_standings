"""Read-only evidence for rating_rethink.md; print JSON, never regenerate ratings.

Run from the repository root: python -m scripts.rating_rethink_audit
The calibration scores reuse development anchors, not a fresh test set.
"""

import hashlib
import json
import os
from pathlib import Path

import numpy as np

from arch_a.load import dedupe_contests, row_solved_any
from arch_b.calibrate import _anchors, _gym_shape, _loco_rmse
from arch_b.calibration_experiment import _full_rows, build_anchor_table
from arch_b.de_release_audit import DE, full_anchor_fit, loco, rmse
from arch_b.joint import OLDER_ICPC, PETROZ, TAGGED, UCUP, WF, load_joint_dataset
from arch_b.run import MIN_SOLVE_HOURS

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def fingerprint(paths):
    return {str(Path(p).resolve().relative_to(ROOT)):
            hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in paths}


def main():
    if os.environ.get("ARCHB_EXTRA_CONTESTS"):
        raise RuntimeError("Audit requires the shipped inputs, without ARCHB_EXTRA_CONTESTS")
    paths = [TAGGED, OLDER_ICPC, PETROZ, WF, *UCUP]
    ds, _, _ = load_joint_dataset(min_solve_hours=MIN_SOLVE_HOURS)
    fitted_contests = set(ds.contests)
    raw = [c for c in dedupe_contests([c for p in paths for c in read(p)])
           if c["contest_id"] in fitted_contests]
    mixed = sum(0 < ds.official_of_row[ds.contest_of_row == ci].sum()
                < (ds.contest_of_row == ci).sum() for ci in range(len(ds.contests)))
    dropped, active_zero = 0, 0
    for c in raw:
        labels = {p["problem_label"] for p in c["problems"]}
        for row in c["standings"]:
            if not row_solved_any(row, labels):
                dropped += 1
                active_zero += any((p.get("wrong_attempts") or 0) > 0
                                   for label, p in (row.get("problems") or {}).items()
                                   if label in labels)
    keys, counts = np.unique(np.column_stack((ds.contest_of_row, ds.team_of_row)),
                             axis=0, return_counts=True)
    assert len(keys) == len(counts)
    out = {"scope": "Read-only audit; cached calibration fits, no candidate model",
           "dataset": {"contests": len(ds.contests), "identities": len(ds.teams),
                       "appearances": len(ds.team_of_row), "problems": len(ds.problems),
                       "cells": len(ds.obs_y), "mixed_imported_and_other_boards": int(mixed),
                       "repeated_contest_identity_groups": int((counts > 1).sum()),
                       "excess_rows_in_repeated_groups": int(np.maximum(counts - 1, 0).sum()),
                       "zero_solve_rows_dropped": dropped,
                       "dropped_with_wrong_attempts": int(active_zero),
                       "zero_solve_problems": int((ds.solved_count == 0).sum()),
                       "one_solve_problems": int((ds.solved_count == 1).sum())}}

    fit_paths = [ROOT / "output" / f"problem_ratings_{m}.json" for m in ("survival", "b")]
    records, binary = map(read, fit_paths)
    shipped_path = ROOT / "output/problem_ratings_calibrated.json"
    meta_path = ROOT / "output/problem_calibration.json"
    anchors = build_anchor_table(records, binary)
    full = _full_rows(records, binary)
    meta = read(meta_path)
    ranges = {f: [min(r[f] for r in anchors), max(r[f] for r in anchors)] for f in DE}
    outside = {f: int(sum(not lo <= r[f] <= hi for r in full))
               for f, (lo, hi) in ranges.items()}
    pred, setting = full_anchor_fit(anchors, full, "clip", DE)
    expected = [round(float(x), 1) for x in np.clip(pred, 800, 4000)]
    shipped = read(shipped_path)
    assert [(r["contest_id"], r["problem_label"]) for r in records] == [
        (r["contest_id"], r["problem_label"]) for r in shipped]
    assert expected == [r["difficulty_cf"] for r in shipped]
    oof, _ = loco(anchors, "clip", DE)
    scores = {"DE_clipped_nested_loco": rmse(oof, anchors)}
    for name, recs in (("survival", records), ("binary", binary)):
        x, y, group = _anchors(recs)
        shape = _gym_shape(recs)
        scores[name + "_affine_loco"] = _loco_rmse(x, y, group)
        scores[name + "_gym_loco"] = _loco_rmse(shape(x) if shape else x, y, group)
    out["calibration"] = {"anchors": len(anchors), "contests": len(set(r["cf_contest"] for r in anchors)),
                          "outside_anchor_range": outside, "scores": scores,
                          "selected_alpha_lambda": list(setting), "shipped_reproduced": True,
                          "metadata_ranges_match_current_anchors": meta["anchor_feature_range"] == ranges,
                          "metadata_matches_saved_fits": {
                              p.name: meta["inputs_sha256"].get(p.name) == digest
                              for p, digest in zip(fit_paths, fingerprint(fit_paths).values())}}

    cache = ROOT / "data/ec_online_cache/xcpcio"
    configs, runs = sorted(cache.glob("*/config.json")), sorted(cache.glob("*/run.json"))
    timed = []
    for p in configs:
        config = read(p)
        if (all(isinstance(config.get(k), (int, float)) for k in ("start_time", "end_time"))
                and config["end_time"] > config["start_time"]):
            timed.append(p)
    out["local_cache"] = {"config_directories": len(configs), "run_directories": len(runs),
                          "configs_with_numeric_start_end": len(timed),
                          "timed_configs_with_runs": sum(p.with_name("run.json").exists() for p in timed),
                          "unique_run_file_hashes": len(set(fingerprint(runs).values())),
                          "gym_raw_checkpoint_exists": (ROOT / "data/gym_checkpoints/api_standings.json").exists(),
                          "note": "Directory inventory only; aliases, joins and run completeness require audit."}
    cache_hashes = fingerprint(configs + runs)
    out["cache_manifest_sha256"] = hashlib.sha256(
        json.dumps(cache_hashes, sort_keys=True).encode()).hexdigest()
    out["inputs_sha256"] = fingerprint(paths + fit_paths + [shipped_path, meta_path,
        ROOT / "data/cf_problemset.json", ROOT / "data/cf_team_contests.txt",
        ROOT / "output/gym_difficulty.json"])
    print(json.dumps(out, ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
