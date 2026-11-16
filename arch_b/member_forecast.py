"""Experiment 3: recorded-date forecasts; see member_forecast_plan.md.

Run: python -m arch_b.member_forecast. Writes separate research artifacts only.
"""

import collections
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from arch_a import elo
from arch_a.load import _norm_member, dedupe_contests, row_solved_any
from . import model
from .dynamic_rating import PAIR_SCALE, smooth_fit
from .medals import _is_official

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "output/member_forecast.json"
WEIGHTS = (0.0, 0.5, 1.0, 1.5)
SEED = 20261105
EPS = 0.01


def roster(row):
    names = tuple(sorted({_norm_member(m) for m in row.get("members") or []} - {""}))
    return names if len(names) == 3 else ()


def seconds(value):
    return float(value) / (1000 if value > 10_000_000_000 else 1)


def panel():
    paths = [ROOT / "data/tagged.json", ROOT / "data/xcpcio_ea_official.json"]
    raw = dedupe_contests(json.loads(paths[0].read_text()))
    mapping = json.loads(paths[1].read_text())
    boards, excluded = [], []
    for c in raw:
        cid = c["contest_id"]
        meta = mapping.get(str(cid))
        if not meta or "error" in meta:
            excluded.append({"contest_id": cid, "reason": "no official board mapping"})
            continue
        path = ROOT / "data/ec_online_cache/xcpcio" / meta["board_link"].removeprefix("/icpc/").replace("/", "_") / "config.json"
        if not path.exists():
            excluded.append({"contest_id": cid, "reason": "missing recorded-date config"})
            continue
        paths.append(path)
        config = json.loads(path.read_text())
        start, end = (seconds(config[k]) for k in ("start_time", "end_time"))
        if end <= start:
            raise ValueError(f"invalid duration: {cid}")
        keys = {k for group in meta["official_keys"] for k in group}
        official = [(i, r) for i, r in enumerate(c["standings"])
                    if r["team_id"].startswith("$DEFAULT") and _is_official(r, keys)]
        counts = collections.Counter(roster(r) for _, r in official if roster(r))
        labels = [p["problem_label"] for p in c["problems"]]
        rows, drops = [], collections.Counter()
        for i, r in official:
            mem = roster(r)
            if mem and counts[mem] > 1:
                drops["duplicate_full_roster"] += 1
                continue
            if not row_solved_any(r, labels):
                drops["zero_solve"] += 1
                continue
            if not mem:
                drops["retained_without_full_roster"] += 1
            rows.append({"source_row": i, "roster": mem,
                         "key": mem or (f"isolated:{cid}:{i}",), "rank": int(r["rank"]),
                         "y": [int(bool((r.get("problems") or {}).get(l, {}).get("solved"))) for l in labels]})
        boards.append({"contest_id": cid, "board_link": meta["board_link"], "start": start,
                       "end": end, "date": datetime.fromtimestamp(start, timezone.utc).date().isoformat(),
                       "n_problems": len(labels), "rows": rows, "exclusions": dict(drops),
                       "nonpanel_rows": len(c["standings"]) - len(official)})
    return sorted(boards, key=lambda b: (b["start"], b["contest_id"])), excluded, paths


def training_data(boards):
    """Build identity and response arrays from earlier boards alone."""
    teams, ti, row_t, row_c, ot, op, y = [], {}, [], [], [], [], []
    offset = 0
    for ci, b in enumerate(boards):
        for r in b["rows"]:
            key = r["key"]
            if key not in ti:
                ti[key] = len(teams)
                teams.append(key)
            rid = len(row_t)
            row_t.append(ti[key]); row_c.append(ci)
            ot.extend([rid] * b["n_problems"])
            op.extend(range(offset, offset + b["n_problems"]))
            y.extend(r["y"])
        offset += b["n_problems"]
    return SimpleNamespace(teams=teams, problems=list(range(offset)),
                           team_of_row=np.array(row_t, int), contest_of_row=np.array(row_c, int),
                           obs_row=np.array(ot, int), obs_prob=np.array(op, int), obs_y=np.array(y, bool))


def forecast(boards, target):
    earlier = [b for b in boards if b["end"] < target["start"]]
    manifest = {"contest_id": target["contest_id"], "cutoff": target["start"],
                "training_contests": [b["contest_id"] for b in earlier]}
    if not earlier:
        return [], manifest
    ds = training_data(earlier)
    th, _, hist = model.fit(ds, verbose=False, eps=EPS, max_iter=400)
    static = dict(zip(ds.teams, th))
    day = np.array([b["start"] / 86400 for b in earlier])
    dyn, _, _, nt, nd = smooth_fit(ds, day, q=50.0, eps=EPS)
    dynamic = {}
    for n in np.argsort(nd, kind="stable"):
        dynamic[ds.teams[nt[n]]] = float(dyn[n])
    latest = {}
    for b in sorted(earlier, key=lambda b: b["end"]):
        for r in b["rows"]:
            for m in r["roster"]:
                when, sources = latest.get(m, (-1, set()))
                if b["end"] > when:
                    latest[m] = (b["end"], {r["key"]})
                elif b["end"] == when:
                    sources.add(r["key"])
    out = []
    for r in target["rows"]:
        if not r["roster"]:
            continue
        sources = [next(iter(latest[m][1])) for m in r["roster"]
                   if m in latest and len(latest[m][1]) == 1]
        seen = r["key"] in static
        if not seen and not sources:
            continue
        base = float(static[r["key"]]) if seen else model.MU0
        delta = sum(float(static[s]) - model.MU0 for s in sources) / 3
        out.append({"source_row": r["source_row"], "roster": r["roster"], "rank": r["rank"],
                    "history": seen, "known_members": len(sources), "prior_sources": len(set(sources)),
                    "static": base, "dynamic_q50": dynamic[r["key"]] if seen else base,
                    "member_delta": 0.0 if seen else delta})
    manifest.update(training_rows=len(ds.team_of_row), training_teams=len(ds.teams),
                    static_iterations=len(hist), static_final_delta=float(hist[-1]),
                    dynamic_converged=True)
    return out, manifest


def score(rows, weight=0.0, dynamic=False, population="combined"):
    rows = [r for r in rows if (population != "history" or r["history"])
            and (population != "cold" or not r["history"])]
    if len(rows) < 2:
        return None
    i, j = np.triu_indices(len(rows), 1)
    rank = np.array([r["rank"] for r in rows])
    keep = rank[i] != rank[j]
    if population == "cold_involving":
        cold = np.array([not r["history"] for r in rows])
        keep &= cold[i] | cold[j]
    f = np.array([r["dynamic_q50" if dynamic else "static"] + weight * r["member_delta"] for r in rows])
    gap = (np.where(rank[i] < rank[j], 1, -1) * (f[i] - f[j]))[keep]
    if not len(gap):
        return None
    return [float(np.sum((gap > 0) + 0.5 * (gap == 0))), len(gap),
            float(np.logaddexp(0, -gap / (PAIR_SCALE * elo.S)).sum())]


def aggregate(scores):
    if not scores:
        return {"contests": 0}
    a = np.array(list(scores.values()))
    return {"contests": len(a), "pairs": int(a[:, 1].sum()),
            "accuracy": float(a[:, 0].sum() / a[:, 1].sum()),
            "pair_log_loss": float(a[:, 2].sum() / a[:, 1].sum()),
            "contest_accuracy": float(np.mean(a[:, 0] / a[:, 1])),
            "contest_log_loss": float(np.mean(a[:, 2] / a[:, 1]))}


def comparison(candidate, base, groups=None):
    keys = sorted(base)
    if not keys:
        return {}
    assert keys == sorted(candidate)
    a, b = (np.array([s[k] for k in keys]) for s in (candidate, base))
    labels = [groups[k] for k in keys] if groups else keys
    unique = sorted(set(labels))
    blocks = [np.flatnonzero(np.array(labels) == g) for g in unique]
    rng = np.random.default_rng(SEED)
    draws = rng.integers(0, len(blocks), (2000, len(blocks)))
    def metrics(x):
        return np.array([x[:, 0].sum() / x[:, 1].sum(), x[:, 2].sum() / x[:, 1].sum(),
                         np.mean(x[:, 0] / x[:, 1]), np.mean(x[:, 2] / x[:, 1])])
    diffs = np.array([metrics(a[idx]) - metrics(b[idx]) for d in draws
                      for idx in [np.concatenate([blocks[g] for g in d])]])
    lo, hi = np.percentile(diffs, [2.5, 97.5], axis=0)
    return {"blocks": len(blocks), **{k: [float(v), float(l), float(h)] for k, v, l, h in zip(
        ("accuracy", "pair_log_loss", "contest_accuracy", "contest_log_loss"), metrics(a) - metrics(b), lo, hi)}}


def run():
    boards, excluded, paths = panel()
    records, manifests = [], []
    for b in boards:
        rows, manifest = forecast(boards, b)
        manifests.append(manifest)
        records.append({"contest_id": b["contest_id"], "date": b["date"], "rows": rows})
        print(f"{b['date']} {b['contest_id']}: {len(rows)} forecast rows", file=sys.stderr, flush=True)
    tune = [r for r in records if r["date"].startswith("2023")]
    evaluation = [r for r in records if r["date"] >= "2024-01-01"]
    def scores(recs, weight=0.0, dynamic=False, population="combined"):
        return {r["contest_id"]: s for r in recs
                if (s := score(r["rows"], weight, dynamic, population)) is not None}
    tuning = {str(w): aggregate(scores(tune, weight=w, population="cold_involving")) for w in WEIGHTS}
    if not any("contest_log_loss" in s for s in tuning.values()):
        raise RuntimeError("no tuning cold-roster pairs; cannot select a member weight")
    weight = min(WEIGHTS, key=lambda w: (tuning[str(w)]["contest_log_loss"], w))
    results = {}
    for population in ("history", "cold", "combined", "cold_involving"):
        variants = {"static": scores(evaluation, population=population),
                    "members": scores(evaluation, weight=weight, population=population)}
        if population == "history":
            variants["dynamic_q50"] = scores(evaluation, dynamic=True, population=population)
        seasons = {r["contest_id"]: r["date"][:4] for r in evaluation}
        results[population] = {name: {**aggregate(s), "per_contest": s,
                              "minus_static": comparison(s, variants["static"]),
                              "season_sensitivity": comparison(s, variants["static"], seasons)}
                              for name, s in variants.items()}
    first, seen = [], set()
    for r in evaluation:
        rows = [x for x in r["rows"] if x["roster"] not in seen]
        seen.update(x["roster"] for x in r["rows"])
        first.append(dict(r, rows=rows))
    base = scores(first, population="cold_involving")
    candidate = scores(first, weight=weight, population="cold_involving")
    subgroups = {}
    for feature in ("known_members", "prior_sources"):
        for count in (1, 2, 3):
            subset = [dict(r, rows=[x for x in r["rows"] if x["history"] or x[feature] == count])
                      for r in evaluation]
            base_group = scores(subset, population="cold_involving")
            member_group = scores(subset, weight=weight, population="cold_involving")
            subgroups[f"{feature}={count}"] = {
                "cold_rows": sum(not x["history"] for r in subset for x in r["rows"]),
                "static": aggregate(base_group), "members": aggregate(member_group),
                "minus_static": comparison(member_group, base_group)}
    code = ["arch_b/member_forecast.py", "arch_b/model.py", "arch_b/dynamic_rating.py",
            "arch_b/medals.py", "arch_a/load.py", "arch_a/elo.py", "member_forecast_plan.md"]
    paths += [ROOT / p for p in code]
    return {"scope": "Recorded-event-date development replay; retrospective roster snapshots; research only",
            "sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
            "convergence_tolerance": EPS, "selected_weight": weight,
            "tuning_2023": tuning, "evaluation_2024_onward": results,
            "first_roster_appearance_sensitivity": {"static": aggregate(base), "members": aggregate(candidate),
                                                    "minus_static": comparison(candidate, base)},
            "member_subgroups": subgroups,
            "panel": [{k: v for k, v in b.items() if k != "rows"} | {"rows": len(b["rows"])} for b in boards],
            "excluded_contests": excluded, "split_manifest": manifests, "forecasts": records}


def main():
    out = run()
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    print(json.dumps({k: out[k] for k in ("selected_weight", "tuning_2023", "first_roster_appearance_sensitivity")}, indent=2))


if __name__ == "__main__":
    main()
