"""Explain how standings-only supplemental contests affect the shipped metric.

This is a diagnostic, not a tuning harness.  It compares the shipped fit with
tagged-only, identity-only, older-ICPC-only, Petroz-only, linked-row-only, and a
graph-selected Petroz subset.
The subset is selected without looking at Codeforces ratings: it contains the
Petroz contests in the top quartile by retained rows belonging to teams already
seen in ``tagged.json``.  That makes it a useful anti-overfitting control for the
tempting (but invalid) strategy of selecting contests directly on LOCO.

For each variant the report includes calibrated/raw LOCO, RMSE by held-out CF
contest, and the existing guards.  It also records per-supplemental-contest link
counts so a metric change can be related to the actual path by which the extra
standings affect rated problems: shared team abilities.

    python -m arch_b.data_influence

Writes ``output/data_influence.json`` by default.  Expect several minutes on the
full dataset because the family/row controls and five targeted contest ablations
require independent anchored survival fits.
"""

import argparse
import contextlib
import io
import json
import os
import tempfile
from collections import Counter, defaultdict
from dataclasses import replace

import numpy as np

from arch_a import elo
from arch_a.load import (_max_solve_seconds, dedupe_contests, load,
                         member_identity, row_solved_any, team_key)
from . import survival
from .joint import OLDER_ICPC, PETROZ, TAGGED, UCUP, WF, estimate_joint
from .calibrate import _anchors, _gym_shape
from .metric import GUARDS, RAW_LOCO_CEILING, _spearman
from .external_validate import (GYM_OUT, KATTIS, _cf_mapping, _cf_problemset,
                                _norm)
from .aoj import load_matches as load_aoj_matches, within_contest_spearman
from .predict_eval import SEED, TEST_FRAC, _metrics
from .run import MIN_SOLVE_HOURS

OUT = os.path.join(os.path.dirname(__file__), os.pardir, "output", "data_influence.json")


def _read(paths):
    raw = []
    for path in paths:
        with open(path) as f:
            raw.extend(json.load(f))
    return dedupe_contests(raw)


def _retained_rows(contest):
    labels = {p["problem_label"] for p in contest["problems"]}
    return [row for row in contest["standings"] if row_solved_any(row, labels)]


def _loco_details(z, cf, groups):
    """Return pooled LOCO RMSE and its held-out-contest decomposition."""
    z, cf, groups = np.asarray(z, float), np.asarray(cf, float), np.asarray(groups)
    errors = []
    per_group = {}
    for group in np.unique(groups):
        train, test = groups != group, groups == group
        slope, intercept = np.polyfit(z[train], cf[train], 1)
        err = slope * z[test] + intercept - cf[test]
        errors.append(err)
        per_group[str(int(group))] = {
            "n": int(test.sum()),
            "rmse": float(np.sqrt(np.mean(err ** 2))),
            "bias": float(np.mean(err)),
        }
    return float(np.sqrt(np.mean(np.concatenate(errors) ** 2))), per_group


def _guards(ds, b):
    by_label = {(int(cid), label): float(b[p])
                for p, (cid, label, _pid, _name) in enumerate(ds.problems)}
    by_name = {(int(cid), _norm(name)): float(b[p])
               for p, (cid, _label, _pid, name) in enumerate(ds.problems)}

    gym_all, gym_ec = [], []
    for record in json.load(open(GYM_OUT)):
        key = (record["contest_id"], record["problem_label"])
        if key not in by_label:
            continue
        pair = (by_label[key], record["difficulty"])
        gym_all.append(pair)
        if record["region"] == "Asia East Continent":
            gym_ec.append(pair)

    kattis = {_norm(v["name"]): v["difficulty"]
              for v in json.load(open(KATTIS)).values()}
    tagged = json.load(open(TAGGED))
    covered_region = {c["contest_id"] for c in tagged
                      if c["region"] in ("North America", "Europe")}
    kat = [(difficulty, kattis[name]) for (cid, name), difficulty in by_name.items()
           if cid in covered_region and name in kattis]
    aoj = load_aoj_matches()
    ao = [(cid, difficulty, aoj[(cid, label)])
          for (cid, label), difficulty in by_label.items() if (cid, label) in aoj]

    per_contest = defaultdict(list)
    for p in range(len(ds.problems)):
        ci = int(ds.contest_of_problem[p])
        solved = int(ds.solved_count[p])
        per_contest[ci].append((float(b[p]), solved))
    sanity = [-rho for values in per_contest.values() if len(values) >= 3
              for rho in [_spearman([x for x, _ in values], [y for _, y in values])]
              if not np.isnan(rho)]
    return {
        "gym_ec_spearman": _spearman(*zip(*gym_ec)),
        "gym_pooled_spearman": _spearman(*zip(*gym_all)),
        "kattis_pooled_spearman": _spearman(*zip(*kat)),
        "aoj_within_spearman": within_contest_spearman(ao),
        "solvecount_sanity": float(np.median(sanity)),
    }


def _score(ds, b):
    records = [{"contest_id": int(cid), "problem_label": label,
                "problem_name": name, "difficulty": float(b[p])}
               for p, (cid, label, _pid, name) in enumerate(ds.problems)]
    our, cf, groups = _anchors(records)
    shape = _gym_shape(records)
    if shape is None:
        raise RuntimeError("locked gym calibration shape is unavailable")
    raw, raw_by_contest = _loco_details(our, cf, groups)
    calibrated, calibrated_by_contest = _loco_details(shape(our), cf, groups)
    equal_contest = float(np.sqrt(np.mean([
        value["rmse"] ** 2 for value in calibrated_by_contest.values()
    ])))
    guards = _guards(ds, b)
    passed = (raw <= RAW_LOCO_CEILING and
              all(guards[name] >= floor for name, floor in GUARDS.items()))
    return {
        "calibrated_loco": calibrated,
        "equal_contest_calibrated_loco": equal_contest,
        "raw_loco": raw,
        "guards": guards,
        "guards_pass": passed,
        "calibrated_by_cf_contest": calibrated_by_contest,
        "raw_by_cf_contest": raw_by_contest,
    }


def _fit(paths, identity_paths=None):
    """Fit with ``paths`` as the only supplemental *standings* under test.

    The Universal Cup seasons are always included: since the 2026-08-21 audit
    they are ordinary fit data rather than a separate anchor phase, so they are
    part of the baseline every variant is compared against, not a variable.
    """
    with contextlib.redirect_stdout(io.StringIO()):
        ds, _theta, b, _history, _uf = estimate_joint(
            fit_fn=survival.fit, min_solve_hours=MIN_SOLVE_HOURS,
            supplemental_paths=list(paths) + UCUP,
            identity_paths=(None if identity_paths is None
                            else list(identity_paths) + UCUP))
    result = _score(ds, b)
    result.update({
        "contests": len(ds.contests),
        "rows": len(ds.team_of_row),
        "teams": len(ds.teams),
        "problems": len(ds.problems),
    })
    return result


def _without_cross_contest_links(ds):
    """Give every standing row its own ability parameter.

    There is one standing row per team per contest, so this preserves all
    within-contest response cells while preventing theta from being shared
    across contests.  It also deliberately removes UCup prior transfer: that
    transfer is itself a cross-dataset identity link.
    """
    n_rows = len(ds.team_of_row)
    return replace(ds, teams=[f"row:{i}" for i in range(n_rows)],
                   team_of_row=np.arange(n_rows, dtype=int))


def _fit_without_cross_contest_links():
    ds = load([TAGGED, OLDER_ICPC, PETROZ], min_solve_hours=MIN_SOLVE_HOURS)
    ds = _without_cross_contest_links(ds)
    _theta, b, _history = survival.fit(ds, verbose=False)
    result = _score(ds, b)
    result.update({
        "contests": len(ds.contests),
        "rows": len(ds.team_of_row),
        "teams": len(ds.teams),
        "problems": len(ds.problems),
    })
    return result


def _heldout_original_cells(paths):
    """Score a fixed tagged-cell holdout while training on all supplemental cells."""
    raw = _read([TAGGED, WF] + list(paths) + UCUP)
    raw = [c for c in raw if _max_solve_seconds(c) >= MIN_SOLVE_HOURS * 3600]
    uf = member_identity(raw)
    ds = load([TAGGED] + list(paths), uf=uf, min_solve_hours=MIN_SOLVE_HOURS)
    obs_team, obs_prob, obs_y, rho = survival._survival_observations(ds)
    tagged_cids = {c["contest_id"] for c in _read([TAGGED])}
    original = np.array([
        ds.contests[int(ds.contest_of_problem[p])] in tagged_cids for p in obs_prob
    ])
    original_index = np.flatnonzero(original)
    rng = np.random.default_rng(SEED)
    heldout_original = rng.random(len(original_index)) < TEST_FRAC
    test = original_index[heldout_original]
    train = np.ones(len(obs_y), dtype=bool)
    train[test] = False
    theta, b, _history = survival.fit(
        ds, obs=(obs_team[train], obs_prob[train], obs_y[train], rho[train]),
        verbose=False)
    gap = (theta[obs_team[test]] - b[obs_prob[test]]) / elo.S
    prediction = 1.0 - np.exp(-survival.LN2 * np.exp(gap))
    logloss, brier, auc = _metrics(obs_y[test], prediction)
    return {"n": len(test), "logloss": logloss, "brier": brier, "auc": auc}


def _link_stats(supplemental):
    """Measure the only causal route from new problems to shipped difficulties."""
    raw = _read([TAGGED, WF, OLDER_ICPC, PETROZ] + UCUP)
    raw = [c for c in raw if _max_solve_seconds(c) >= MIN_SOLVE_HOURS * 3600]
    uf = member_identity(raw)

    def identities(contests):
        found = set()
        for contest in contests:
            if _max_solve_seconds(contest) < MIN_SOLVE_HOURS * 3600:
                continue
            for row in _retained_rows(contest):
                found.add(team_key(contest["contest_id"], row["team_id"],
                                   row.get("members"), uf))
        return found

    tagged = [c for c in _read([TAGGED])
              if _max_solve_seconds(c) >= MIN_SOLVE_HOURS * 3600]
    tagged_ids = identities(tagged)
    ucup_ids = identities(_read(UCUP))
    contests_like = [
        {"contest_id": c["contest_id"], "problems": [
            {"problem_label": p["problem_label"], "problem_name": p["problem_name"]}
            for p in c["problems"]
        ]} for c in tagged
    ]
    with contextlib.redirect_stdout(io.StringIO()):
        mapping = _cf_mapping(contests_like, defaultdict(lambda: "?"),
                              _cf_problemset())
    anchor_ids = {str(cfid): identities([
        next(c for c in tagged if c["contest_id"] == qoj)
    ]) for cfid, qoj, _region, _matched in mapping}
    stats = []
    for contest in supplemental:
        if _max_solve_seconds(contest) < MIN_SOLVE_HOURS * 3600:
            continue
        rows = _retained_rows(contest)
        ids = [team_key(contest["contest_id"], row["team_id"],
                        row.get("members"), uf) for row in rows]
        counts = Counter(ids)
        contest_ids = set(counts)
        linked = {identity for identity in counts if identity in tagged_ids}
        anchored = {identity for identity in counts if identity in ucup_ids}
        stats.append({
            "contest_id": int(contest["contest_id"]),
            "name": contest.get("contest_name"),
            "year": contest.get("year"),
            "rows": len(rows),
            "teams": len(counts),
            "tagged_linked_teams": len(linked),
            "tagged_linked_rows": sum(counts[x] for x in linked),
            "ucup_anchored_teams": len(anchored),
            "link_rate": len(linked) / max(len(counts), 1),
            "cf_anchor_team_links": {
                cfid: len(contest_ids & target_ids)
                for cfid, target_ids in anchor_ids.items()
                if contest_ids & target_ids
            },
        })
    return stats


def _bridge_subset(contests, stats):
    """Top quartile by linked rows, selected without consulting CF outcomes."""
    by_id = {record["contest_id"]: record for record in stats}
    eligible = [c for c in contests if c["contest_id"] in by_id]
    if not eligible:
        return []
    values = np.array([by_id[c["contest_id"]]["tagged_linked_rows"] for c in eligible])
    cutoff = float(np.quantile(values, 0.75))
    return [c for c in eligible
            if by_id[c["contest_id"]]["tagged_linked_rows"] >= cutoff]


def _linked_rows_only(supplemental):
    """Keep supplemental rows connected to tagged, without consulting outcomes."""
    raw = _read([TAGGED, WF, OLDER_ICPC, PETROZ] + UCUP)
    raw = [c for c in raw if _max_solve_seconds(c) >= MIN_SOLVE_HOURS * 3600]
    uf = member_identity(raw)
    tagged_ids = set()
    for contest in _read([TAGGED]):
        if _max_solve_seconds(contest) < MIN_SOLVE_HOURS * 3600:
            continue
        for row in contest["standings"]:
            tagged_ids.add(team_key(contest["contest_id"], row["team_id"],
                                    row.get("members"), uf))

    selected = []
    for contest in supplemental:
        copy = dict(contest)
        copy["standings"] = [
            row for row in contest["standings"]
            if team_key(contest["contest_id"], row["team_id"],
                        row.get("members"), uf) in tagged_ids
        ]
        selected.append(copy)
    return selected


@contextlib.contextmanager
def _contest_file(contests):
    """Expose an in-memory diagnostic subset through the loader's file API."""
    handle = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
    try:
        with handle:
            json.dump(contests, handle, ensure_ascii=False)
        yield handle.name
    finally:
        os.unlink(handle.name)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default=OUT)
    args = parser.parse_args(argv)

    older = _read([OLDER_ICPC])
    petroz = _read([PETROZ])
    stats = _link_stats(older + petroz)
    bridge = _bridge_subset(petroz, stats)
    linked_rows = _linked_rows_only(older + petroz)

    variants = {
        "tagged_only": [],
        "older_icpc_only": [OLDER_ICPC],
        "petroz_only": [PETROZ],
        "all_supplemental": [OLDER_ICPC, PETROZ],
    }
    results = {}
    for name, paths in variants.items():
        print(f"fitting {name} ...", flush=True)
        results[name] = _fit(paths)
        print(f"  calibrated={results[name]['calibrated_loco']:.1f}  "
              f"raw={results[name]['raw_loco']:.1f}")
    print("fitting without any cross-contest team links ...", flush=True)
    results["no_cross_contest_links"] = _fit_without_cross_contest_links()
    print("fitting supplemental identity links without solve evidence ...", flush=True)
    results["identity_only"] = _fit([], identity_paths=[OLDER_ICPC, PETROZ])
    with _contest_file(bridge) as path:
        print(f"fitting graph-selected Petroz subset ({len(bridge)} contests) ...",
              flush=True)
        results["petroz_top_link_quartile"] = _fit([path])
        results["petroz_top_link_quartile"]["contest_ids"] = [
            int(c["contest_id"]) for c in bridge]
    with _contest_file(linked_rows) as path:
        print("fitting only supplemental rows linked to tagged teams ...", flush=True)
        results["all_supplemental_linked_rows_only"] = _fit([path])

    # Exact marginal effects for the five most connected supplemental contests.
    # Candidate selection uses graph connectivity only, never CF error or rating.
    top = sorted(stats, key=lambda record: record["tagged_linked_rows"], reverse=True)[:5]
    leave_one_out = {}
    for record in top:
        cid = record["contest_id"]
        remaining = [c for c in older + petroz if c["contest_id"] != cid]
        with _contest_file(remaining) as path:
            print(f"fitting all supplemental except contest {cid} ...", flush=True)
            leave_one_out[str(cid)] = _fit([path])

    # This mutation is deliberately labelled post-selection: its members are
    # the top-link candidates whose individual deletion improved LOCO above.
    harmful = {int(cid) for cid, result in leave_one_out.items()
               if result["calibrated_loco"] < results["all_supplemental"]["calibrated_loco"]}
    mutation = [c for c in older + petroz if c["contest_id"] not in harmful]
    with _contest_file(mutation) as path:
        print(f"fitting post-selected mutation without {sorted(harmful)} ...", flush=True)
        results["postselected_remove_harmful_top_links"] = _fit([path])
        results["postselected_remove_harmful_top_links"]["removed_contest_ids"] = sorted(harmful)
        mutation_holdout = _heldout_original_cells([path])

    print("running original-cell transfer controls ...", flush=True)
    heldout = {
        "tagged_only": _heldout_original_cells([]),
        "all_supplemental": _heldout_original_cells([OLDER_ICPC, PETROZ]),
        "postselected_remove_harmful_top_links": mutation_holdout,
    }

    baseline = results["tagged_only"]["calibrated_loco"]
    for result in results.values():
        result["calibrated_delta_vs_tagged_only"] = result["calibrated_loco"] - baseline
    full = results["all_supplemental"]["calibrated_loco"]
    for result in leave_one_out.values():
        result["calibrated_delta_vs_full"] = result["calibrated_loco"] - full

    report = {
        "selection_rule": "Petroz top quartile by tagged-linked retained rows; no CF data",
        "min_solve_hours": MIN_SOLVE_HOURS,
        "variants": results,
        "top_linked_leave_one_out": leave_one_out,
        "heldout_original_cells": heldout,
        "supplemental_contests": stats,
    }
    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"wrote {args.output}")


if __name__ == "__main__":
    main()
