"""Cached, non-OOF transfer diagnostics for the frozen ridge ablation."""

import hashlib
import json
import os
from collections import defaultdict

import numpy as np

from .aoj import load_matches, spearman, within_contest_spearman
from .calibrate import _gym_shape
from .calibration_ablation import (BUNDLES, PLAN, bundle_features,
                                   fit_predict_fixed, select_full_anchors)
from .calibration_experiment import (_affine, _full_rows, _load_json,
                                     build_anchor_table)
from .external_validate import GYM_OUT, KATTIS, _kattis_matches, _norm
from .joint import OLDER_ICPC, PETROZ, TAGGED, UCUP, WF

ROOT = os.path.join(os.path.dirname(__file__), os.pardir)
OUT = os.path.join(ROOT, "output", "calibration_ablation_transfer.json")
SURVIVAL = os.path.join(ROOT, "output", "problem_ratings_survival.json")
BINARY = os.path.join(ROOT, "output", "problem_ratings_b.json")
PRIOR = os.path.join(ROOT, "output", "calibration_experiment.json")
LUXOR_IDS = (8674, 8676, 8677, 8680, 8683)


def _sha(path):
    with open(path, "rb") as source:
        return hashlib.sha256(source.read()).hexdigest()


def _metric_rows(rows, predictions, source):
    """Return established proxy metrics; these rows are not held-out labels."""
    values = {name: [] for name in predictions}
    if source == "aoj":
        for row, proxy in rows:
            for name, predicted in predictions.items():
                values[name].append((row["contest_id"], predicted[row["index"]], proxy))
        result = {name: within_contest_spearman(part) for name, part in values.items()}
    else:
        for row, proxy in rows:
            for name, predicted in predictions.items():
                values[name].append((predicted[row["index"]], proxy))
        result = {name: spearman([x for x, _ in part], [y for _, y in part])
                  for name, part in values.items()}
    if not result or any(value is None or not np.isfinite(value) for value in result.values()):
        raise RuntimeError("non-finite cached proxy metric")
    return result


def _reorderings(rows, raw, predicted):
    changed = total = 0
    by_contest = defaultdict(list)
    for index, row in enumerate(rows):
        by_contest[row["contest_id"]].append(index)
    for indices in by_contest.values():
        for position, left in enumerate(indices):
            for right in indices[position + 1:]:
                raw_order = np.sign(raw[left] - raw[right])
                if raw_order:
                    total += 1
                    changed += raw_order != np.sign(predicted[left] - predicted[right])
    return {"changed": int(changed), "comparable_pairs": int(total)}


def _solve_count_sanity(records, rows, predictions):
    solved = {(int(row["contest_id"]), row["problem_label"]): row["solved_count"]
             for row in records}
    result = {}
    for name, predicted in predictions.items():
        grouped = defaultdict(list)
        for index, row in enumerate(rows):
            grouped[row["contest_id"]].append((predicted[index], solved[(row["contest_id"], row["problem_label"])]))
        scores = [-score for part in grouped.values() if len(part) >= 3
                  for score in [spearman([x for x, _ in part], [y for _, y in part])]
                  if np.isfinite(score)]
        if not scores:
            raise RuntimeError(f"no valid solve-count sanity contest for {name}")
        result[name] = float(np.median(scores))
    if any(not np.isfinite(value) for value in result.values()):
        raise RuntimeError("non-finite solve-count sanity metric")
    return result


def run_transfer(output_path=None):
    """Refit all frozen choices on all anchors for descriptive cached proxies."""
    anchors = build_anchor_table()
    records = _load_json(SURVIVAL)
    rows = _full_rows(records)
    selection = select_full_anchors(anchors)
    raw = _affine(anchors, rows, None)
    shape = _gym_shape(records)
    if shape is None:
        raise RuntimeError("locked gym shape unavailable")
    predictions = {"raw_affine": raw,
                   "gym_shape_affine": _affine(anchors, rows, shape)}
    for bundle, setting in selection["fixed"].items():
        predictions["ridge_" + bundle] = fit_predict_fixed(
            anchors, rows, bundle, setting["alpha"], setting["lambda"])
    adaptive = selection["adaptive"]
    predictions["ridge_adaptive"] = fit_predict_fixed(
        anchors, rows, adaptive["bundle"], adaptive["alpha"], adaptive["lambda"])
    if any(not np.isfinite(value).all() for value in predictions.values()):
        raise RuntimeError("non-finite transfer prediction")

    for index, row in enumerate(rows):
        row["index"] = index
    by_label = {(row["contest_id"], row["problem_label"]): row for row in rows}
    by_name = {(int(record["contest_id"]), _norm(record["problem_name"])): by_label[(int(record["contest_id"]), record["problem_label"])]
               for record in records}
    anchor_tasks = {row["canonical_task"] for row in anchors}
    anchor_contests = {row["contest_id"] for row in anchors}
    non_anchor_task = lambda pairs: [(row, proxy) for row, proxy in pairs
                                     if row["canonical_task"] not in anchor_tasks]
    # Keep the stricter whole-contest exclusion visible because it reproduces
    # the historical 655/412 report counts.
    non_anchor_contest = lambda pairs: [(row, proxy) for row, proxy in pairs
                                        if row["canonical_task"] not in anchor_tasks and
                                        row["contest_id"] not in anchor_contests]

    gym = _load_json(GYM_OUT)
    gym_all = [(by_label[(int(item["contest_id"]), item["problem_label"])], item["difficulty"])
               for item in gym if (int(item["contest_id"]), item["problem_label"]) in by_label]
    gym_ec = [(by_label[(int(item["contest_id"]), item["problem_label"])], item["difficulty"])
              for item in gym if item["region"] == "Asia East Continent" and
              (int(item["contest_id"]), item["problem_label"]) in by_label]
    tagged = _load_json(os.path.join(ROOT, "data", "tagged.json"))
    kattis = _kattis_matches(tagged, _load_json(KATTIS))
    regions = {int(contest["contest_id"]): contest["region"] for contest in tagged}
    kat_all = [(row, proxy) for key, proxy in kattis.items() if key in by_name
               for row in [by_name[key]] if regions[row["contest_id"]] in ("North America", "Europe")]
    aoj = load_matches()
    aoj_all = [(row, proxy) for key, proxy in aoj.items() if key in by_label
               for row in [by_label[key]]]
    expected = {"gym_pooled": 667, "gym_east_asia_continent": 230,
                "kattis_na_europe": 427, "aoj_within_contest": 45}
    pairs = {"gym_pooled": (gym_all, "spearman"),
             "gym_east_asia_continent": (gym_ec, "spearman"),
             "kattis_na_europe": (kat_all, "spearman"),
             "aoj_within_contest": (aoj_all, "aoj")}
    proxies = {}
    for name, (all_pairs, kind) in pairs.items():
        if len(all_pairs) != expected[name]:
            raise RuntimeError(f"{name} matching count {len(all_pairs)} != {expected[name]}")
        task_subset = non_anchor_task(all_pairs)
        contest_subset = non_anchor_contest(all_pairs)
        proxies[name] = {
            "metric": "within_contest_spearman" if kind == "aoj" else "spearman",
            "all_cached_proxy": {"n": len(all_pairs), "outcomes": _metric_rows(all_pairs, predictions, kind)},
            "non_cf_anchor_canonical_task_subset": {"n": len(task_subset), "outcomes": _metric_rows(task_subset, predictions, kind)},
            "stricter_non_cf_anchor_contest_and_task_subset": {"n": len(contest_subset), "outcomes": _metric_rows(contest_subset, predictions, kind)},
        }
    if proxies["gym_pooled"]["stricter_non_cf_anchor_contest_and_task_subset"]["n"] != 655 or \
       proxies["kattis_na_europe"]["stricter_non_cf_anchor_contest_and_task_subset"]["n"] != 412:
        raise RuntimeError("non-anchor cached-proxy counts do not reproduce frozen matching: "
                           f"gym={proxies['gym_pooled']['stricter_non_cf_anchor_contest_and_task_subset']['n']} "
                           f"kattis={proxies['kattis_na_europe']['stricter_non_cf_anchor_contest_and_task_subset']['n']}")

    raw_lo, raw_hi = min(row["raw_b"] for row in anchors), max(row["raw_b"] for row in anchors)
    tails = [row for row in rows if row["raw_b"] < raw_lo or row["raw_b"] > raw_hi]
    tail_detail = {name: {"correction_range": [float(np.min(value[[row["index"] for row in tails]] - raw[[row["index"] for row in tails]])),
                                                   float(np.max(value[[row["index"] for row in tails]] - raw[[row["index"] for row in tails]]))],
                          "prediction_range": [float(np.min(value)), float(np.max(value))],
                          "outside_800_4000_count": int(np.sum((value < 800) | (value > 4000)))}
                   for name, value in predictions.items()}
    luxor = {}
    for task in LUXOR_IDS:
        pair = sorted((row for row in rows if row["problem_id"] == task and row["contest_id"] in (1661, 1662)),
                      key=lambda row: row["contest_id"])
        if len(pair) != 2:
            raise RuntimeError(f"Luxor task {task} lacks both cached appearances")
        luxor[str(task)] = {name: float(abs(value[pair[0]["index"]] - value[pair[1]["index"]]))
                            for name, value in predictions.items()}
    result = {
        "research_only": True, "not_oof": True, "fresh_confirmation": False,
        "not_used_to_select_hyperparameters_or_model": True,
        "description": "All-anchor refits evaluated only against pre-existing cached transfer proxies; no proxy outcome selected settings.",
        "subset_definitions": {"canonical_task_only": "removes every full row sharing any of the 185 anchor qoj:<problem_id> tasks",
                               "stricter_anchor_contest_and_task": "also removes every full row from an anchor QOJ contest; this reproduces the historical 655/412 report counts"},
        "full_anchor_inner_selection_not_oof_not_deployment": selection,
        "feature_bundles": {bundle: bundle_features(bundle) for bundle in BUNDLES},
        "cached_proxy_diagnostics": proxies,
        "tail_diagnostics": {"anchor_raw_range": [raw_lo, raw_hi], "out_of_range_count": len(tails),
                             "all_outside_above_anchor_max": all(row["raw_b"] > raw_hi for row in tails),
                             "no_artificial_prediction_clipping": True, "methods": tail_detail},
        "luxor_shared_task_absolute_gaps": luxor,
        "within_contest_pair_reorderings_vs_raw": {name: _reorderings(rows, raw, value)
                                                     for name, value in predictions.items() if name != "raw_affine"},
        "solve_count_sanity_descriptive_not_production_guard": _solve_count_sanity(records, rows, predictions),
        "provenance_sha256": {os.path.relpath(path): _sha(path) for path in
                               (TAGGED, OLDER_ICPC, PETROZ, WF, *UCUP,
                                os.path.join(ROOT, "data", "cf_problemset.json"),
                                os.path.join(ROOT, "data", "cf_team_contests.txt"),
                                SURVIVAL, BINARY, GYM_OUT, KATTIS,
                                os.path.join(ROOT, "data", "aoj_difficulty.json"), PRIOR, PLAN,
                                os.path.join(os.path.dirname(__file__), "calibration_experiment.py"),
                                os.path.join(os.path.dirname(__file__), "calibration_ablation.py"), __file__)},
    }
    if output_path:
        with open(output_path, "w") as destination:
            json.dump(result, destination, indent=2, allow_nan=False)
            destination.write("\n")
    return result


def main():
    result = run_transfer(OUT)
    print(json.dumps({name: value["all_cached_proxy"]["outcomes"]
                      for name, value in result["cached_proxy_diagnostics"].items()}, sort_keys=True))


if __name__ == "__main__":
    main()
