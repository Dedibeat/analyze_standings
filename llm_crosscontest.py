"""Cross-contest pairwise difficulty comparisons: the missing level anchor.

``llm_survival.py`` asks Gemini which of two statements is harder, but it only
ever pairs problems **inside one contest** (``_make_requests`` groups by
``contest_id``), and only over the 185 problems of the 15 CF-mirrored contests.
That is the axis the standings fit already gets right: within-contest Spearman
against official CF ratings is +0.85 to +1.00 and there is no within-contest
compression left to remove, which is why fusing those comparisons into the fit
came out flat-to-negative (nested LOCO 275.68 survival vs 282.31 fused).

The open problem is the other axis. The 2026-08-21 anchoring audit measured that
per-contest offsets carry 17% of the CF-anchor residual variance, that only 92
of 207 fitted contests have any external anchor at all, and -- worst -- that the
two standings-free referees disagree in *sign* on the per-region level: against
the gym yardstick Europe minus Asia East is +117 +- 42 CF points, against the
LLM bucket labels the same pair is -134 +- 30. Neither can settle it, because
each scores a region against its own absolute scale (who virtual-participates
there; how a 4-level label is applied to that region's statement style).

A pairwise comparison has no absolute scale to drift. Asking one model directly
"is this Europe problem harder than this Asia East problem?" measures the level
difference head to head. This module builds that schedule, and -- crucially --
validates the instrument before trusting it: run it first over the 15 CF-mirrored
contests, where the true cross-contest levels are known from official CF ratings,
and check whether the fitted Bradley-Terry scores recover them.

Design carried over from the earlier runs: statements only (the contest-level
``editorial`` field is never read), the same metadata sanitizer and prompt, both
A/B orientations with order-consistency reporting, a seeded deterministic
schedule, resumable checkpoints, and a hard preflight budget gate. Partners are
drawn uniformly at random from *other* contests -- never chosen using our own
difficulty, a CF rating, or any other target proxy -- so the schedule carries no
information about the answer.

    python llm_crosscontest.py prepare --scope mirrors --matches 6
    python llm_crosscontest.py count   --project <gcp-project>
    python llm_crosscontest.py run     --project <gcp-project>
    python llm_crosscontest.py analyse

``--scope mirrors`` is the validation stage (185 problems, 15 contests, truth
available). ``--scope all`` is the deployment stage over every statement-bearing
contest; it is only worth dispatching if the validation stage passes.
"""

import argparse
import hashlib
import json
import random
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import redirect_stdout
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path

import numpy as np

from arch_b.calibrate import _gym_shape
from arch_b.external_validate import _cf_mapping, _cf_problemset, _norm
from llm_survival import (DATA, LOCATION, MODEL, OUTPUT, PROMPT_VERSION, SYSTEM,
                          _cost, _load_contests, _load_survival, _read_predictions,
                          _run_one, generate_url, count_url, prompt_payload,
                          sanitize_statement, sha256_text)
from pairwise_tuning import Vertex

ROOT = Path(__file__).resolve().parent
DEFAULT_RUN_DIR = ROOT / "llm_crosscontest_run"
SEED = 20260821
UCUP = [DATA / "ucup_s3.json", DATA / "ucup_s4.json"]


# --------------------------------------------------------------------------- rows

def _sanitized(problem, contest):
    """The sanitized statement, or None if it cannot be made metadata-free.

    ``sanitize_statement(strict=True)`` raises when a leak survives -- usually a
    "Problem C" phrase wrapped across a line break, which the per-line
    substitution misses and the joined text reintroduces. Such a problem is
    **skipped**, never sent with the leak: the Phase-3 forensics showed that
    verbatim ids and labels in the prompt invalidate the intended metadata-free
    comparison.
    """
    try:
        text = sanitize_statement({**problem, "contest_name": contest.get("contest_name", "")})
    except ValueError:
        return None
    return text if len(text) >= 40 else None


def _mirror_rows():
    """The 185 problems of the 15 rated CF mirrors, with their official ratings."""
    contests = _load_contests()
    by_contest = {int(c["contest_id"]): c for c in contests}
    region_of = {int(c["contest_id"]): c.get("region", "?") for c in contests}
    rating = _cf_problemset()
    with redirect_stdout(StringIO()):
        mapping = _cf_mapping(contests, region_of, rating)
    survival = _load_survival()
    rows, statements = [], {}
    for cf_id, qoj_id, region, matched in mapping:
        contest = by_contest[qoj_id]
        by_name = {_norm(p["problem_name"]): p for p in contest["problems"]}
        for name in matched:
            problem = by_name[name]
            text = _sanitized(problem, contest)
            if text is None:
                continue
            pid = str(problem["problem_id"])
            statements[pid] = text
            rows.append({
                "problem_id": pid,
                "contest_id": qoj_id,
                "problem_label": problem["problem_label"],
                "statement_sha256": sha256_text(text),
                "statement_chars": len(text),
                "survival_difficulty": float(
                    survival[(qoj_id, problem["problem_label"])]["difficulty"]),
                "cf_contest_id": cf_id,
                "cf_rating": int(rating[(cf_id, name)]),
                "region": region,
            })
    return rows, statements


def _all_rows():
    """Every statement-bearing fitted problem (tagged.json + the UCup seasons)."""
    contests = _load_contests()
    for path in UCUP:
        contests.extend(json.loads(path.read_text(encoding="utf-8")))
    seen, survival = set(), _load_survival()
    rows, statements = [], {}
    for contest in contests:
        cid = int(contest["contest_id"])
        if cid in seen:
            continue          # dedupe_contests keeps the first entry per id
        seen.add(cid)
        for problem in contest.get("problems") or []:
            key = (cid, problem["problem_label"])
            if key not in survival:
                continue      # not in the fit (short contest, dropped row, ...)
            text = _sanitized(problem, contest)
            if text is None:
                continue
            pid = str(problem["problem_id"])
            statements[pid] = text
            rows.append({
                "problem_id": pid,
                "contest_id": cid,
                "problem_label": problem["problem_label"],
                "statement_sha256": sha256_text(text),
                "statement_chars": len(text),
                "survival_difficulty": float(survival[key]["difficulty"]),
                "cf_contest_id": None,
                "cf_rating": None,
                "region": contest.get("region") or "Universal Cup",
            })
    return rows, statements


# ------------------------------------------------------------------- schedule

def _cross_pairs(rows, matches_per_problem):
    """Deterministic cross-contest unordered pairs, uniformly drawn.

    Each problem seeks ``matches_per_problem`` partners from *other* contests.
    Partners are uniform over the eligible pool -- no difficulty, rating, or
    other target proxy enters the choice -- and a pair is emitted once.
    """
    rng = random.Random(SEED)
    by_contest = defaultdict(list)
    for row in rows:
        by_contest[row["contest_id"]].append(row["problem_id"])
    ids = [r["problem_id"] for r in rows]
    contest_of = {r["problem_id"]: r["contest_id"] for r in rows}
    pairs, degree = set(), defaultdict(int)
    order = list(ids)
    rng.shuffle(order)
    for pid in order:
        tries = 0
        while degree[pid] < matches_per_problem and tries < 50 * matches_per_problem:
            tries += 1
            other = ids[rng.randrange(len(ids))]
            if contest_of[other] == contest_of[pid]:
                continue
            key = (pid, other) if pid < other else (other, pid)
            if key in pairs:
                continue
            pairs.add(key)
            degree[pid] += 1
            degree[other] += 1
    return sorted(pairs)


def _requests(pairs):
    """Two orientations per unordered pair, display order fixed by a seeded hash."""
    out = []
    for left, right in pairs:
        digest = hashlib.sha256(f"{SEED}:{left}:{right}".encode()).digest()
        first, second = (left, right) if digest[0] & 1 else (right, left)
        for orientation, a, b in ((0, first, second), (1, second, first)):
            out.append({
                "request_id": f"x:{left}:{right}:{orientation}",
                "pair_key": [left, right],
                "display_a": a,
                "display_b": b,
                "orientation": orientation,
            })
    return out


def prepare(args):
    rows, statements = _mirror_rows() if args.scope == "mirrors" else _all_rows()
    pairs = _cross_pairs(rows, args.matches)
    requests = _requests(pairs)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "statements.json").write_text(
        json.dumps(statements, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8")
    (args.output / "manifest.json").write_text(json.dumps({
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model": MODEL, "location": LOCATION, "prompt_version": PROMPT_VERSION,
        "seed": SEED, "scope": args.scope, "matches_per_problem": args.matches,
        "system_sha256": sha256_text(SYSTEM),
        "problems": rows, "requests": requests,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    contests = len({r["contest_id"] for r in rows})
    print(json.dumps({"scope": args.scope, "problems": len(rows), "contests": contests,
                      "unordered_pairs": len(pairs), "requests": len(requests),
                      "run_dir": str(args.output)}, indent=2))


def _manifest(run_dir):
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    statements = json.loads((run_dir / "statements.json").read_text(encoding="utf-8"))
    for row in manifest["problems"]:
        if sha256_text(statements[row["problem_id"]]) != row["statement_sha256"]:
            raise ValueError(f"statement hash mismatch for {row['problem_id']}")
    return manifest, statements


def count(args):
    """Exact countTokens preflight over a sample, extrapolated to the full run."""
    manifest, statements = _manifest(args.run_dir)
    requests = manifest["requests"]
    sample = requests[:: max(1, len(requests) // args.sample)][: args.sample]
    vertex = Vertex(args.project)
    url = count_url(args.project, args.location, manifest["model"])
    totals = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(vertex.request, url,
                               prompt_payload(statements[r["display_a"]],
                                              statements[r["display_b"]]))
                   for r in sample]
        for future in as_completed(futures):
            totals.append(int(future.result()["totalTokens"]))
    mean_in = float(np.mean(totals))
    input_tokens = int(round(mean_in * len(requests)))
    output_tokens = 12 * len(requests)          # the JSON answer is a few tokens
    cost = _cost(input_tokens, output_tokens)
    preflight = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model": manifest["model"], "requests": len(requests),
        "sampled": len(totals), "mean_input_tokens": round(mean_in, 1),
        "estimated_input_tokens": input_tokens, "estimated_output_tokens": output_tokens,
        "estimated_cost_usd": round(cost, 4), "budget_usd": args.budget,
        "dispatch_allowed": cost <= args.budget,
    }
    (args.run_dir / "preflight.json").write_text(
        json.dumps(preflight, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(preflight, indent=2))


def run(args):
    manifest, statements = _manifest(args.run_dir)
    preflight = json.loads((args.run_dir / "preflight.json").read_text(encoding="utf-8"))
    if not preflight.get("dispatch_allowed"):
        raise SystemExit("preflight forbids dispatch")
    if preflight["model"] != manifest["model"]:
        raise ValueError("preflight model mismatch")
    path = args.run_dir / "predictions.json"
    saved = _read_predictions(path)
    done = {p["request_id"] for p in saved.get("predictions", [])}
    pending = [r for r in manifest["requests"] if r["request_id"] not in done]
    vertex = Vertex(args.project)
    url = generate_url(args.project, manifest["model"], args.location)
    print(f"dispatching {len(pending)} requests ({len(done)} cached)", flush=True)
    errors = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(_run_one, vertex, url, r, statements): r for r in pending}
        for i, future in enumerate(as_completed(futures), 1):
            request = futures[future]
            try:
                item = future.result()
            except Exception as exc:            # absent -> a rerun retries it
                errors.append({"request_id": request["request_id"], "error": repr(exc)})
                continue
            saved.setdefault("predictions", []).append(item)
            if i % 25 == 0 or i == len(pending):
                saved.update({"model": manifest["model"], "project": args.project,
                              "updated_at": datetime.now(timezone.utc).isoformat()})
                path.write_text(json.dumps(saved, indent=2) + "\n", encoding="utf-8")
                print(f"[{len(saved['predictions'])}/{len(manifest['requests'])}]", flush=True)
    saved.update({"model": manifest["model"], "project": args.project,
                  "updated_at": datetime.now(timezone.utc).isoformat()})
    path.write_text(json.dumps(saved, indent=2) + "\n", encoding="utf-8")
    if errors:
        raise RuntimeError(f"{len(errors)} requests failed; rerun to retry")


# ------------------------------------------------------------------------- BT

def bt_scores(problem_ids, rows, kappa=400.0, alpha=0.01, iters=400):
    """Bradley--Terry MAP by coordinate Newton (the repo's block-Newton style).

    ``llm_survival.bt_fit`` builds a dense (n-1)^2 Hessian per iteration, which
    is fine for one 13-problem contest and hopeless for a cross-contest graph of
    thousands of problems. This is the same model and the same symmetric
    pseudo-count, solved one coordinate block at a time in O(edges) per sweep,
    then centred (the scale is identified only up to a shift).
    """
    index = {pid: i for i, pid in enumerate(problem_ids)}
    counts = defaultdict(lambda: [0.0, 0.0])
    for row in rows:
        a, b = index[row["display_a"]], index[row["display_b"]]
        key = (a, b) if a < b else (b, a)
        harder_is_a = row["predicted"] == "A"
        first_wins = harder_is_a if a < b else not harder_is_a
        counts[key][0 if first_wins else 1] += 1.0
    if not counts:
        return np.zeros(len(problem_ids))
    ea = np.array([k[0] for k in counts], dtype=int)
    eb = np.array([k[1] for k in counts], dtype=int)
    wins = np.array([v[0] for v in counts.values()]) + alpha
    losses = np.array([v[1] for v in counts.values()]) + alpha
    total = wins + losses

    x = np.zeros(len(problem_ids))
    for _ in range(iters):
        d = (x[ea] - x[eb]) / kappa
        p = 1.0 / (1.0 + np.exp(-d))
        resid = wins - total * p
        info = total * p * (1.0 - p)
        grad = np.zeros_like(x)
        curv = np.full_like(x, 1e-6)
        np.add.at(grad, ea, resid / kappa)
        np.add.at(grad, eb, -resid / kappa)
        np.add.at(curv, ea, info / kappa**2)
        np.add.at(curv, eb, info / kappa**2)
        step = grad / curv
        x = x + step
        x -= x.mean()
        if np.max(np.abs(step)) < 1e-4:
            break
    return x


def _predictions(run_dir):
    return _read_predictions(run_dir / "predictions.json").get("predictions", [])


def _order_consistency(rows):
    by_pair = defaultdict(list)
    for row in rows:
        by_pair[tuple(row["pair_key"])].append(row)
    both, agree = 0, 0
    for pair, items in by_pair.items():
        if len(items) != 2:
            continue
        both += 1
        winners = {r["display_a"] if r["predicted"] == "A" else r["display_b"]
                   for r in items}
        agree += len(winners) == 1
    return both, agree


def _spearman(a, b):
    r = lambda v: np.argsort(np.argsort(v))  # noqa: E731
    return float(np.corrcoef(r(a), r(b))[0, 1])


def analyse(args):
    manifest, _ = _manifest(args.run_dir)
    rows = _predictions(args.run_dir)
    if not rows:
        raise SystemExit("no predictions yet")
    problems = {r["problem_id"]: r for r in manifest["problems"]}
    ids = sorted(problems)

    within = []
    if args.within and Path(args.within).exists():
        saved = json.loads(Path(args.within).read_text(encoding="utf-8"))
        within = [p for p in saved.get("predictions", [])
                  if p["display_a"] in problems and p["display_b"] in problems]

    both, agree = _order_consistency(rows)
    print(f"cross-contest requests: {len(rows)}  unordered pairs with both "
          f"orientations: {both}  order-consistent: {agree/both:.3f}" if both else "")
    print(f"within-contest predictions reused: {len(within)}")

    x = bt_scores(ids, rows + within)
    score = dict(zip(ids, x))

    have_cf = [pid for pid in ids if problems[pid]["cf_rating"] is not None]
    out = {"scope": manifest["scope"], "matches_per_problem": manifest["matches_per_problem"],
           "cross_requests": len(rows), "within_reused": len(within),
           "order_consistency": (agree / both) if both else None,
           "bt_scores": {pid: round(float(score[pid]), 3) for pid in ids}}

    if have_cf:
        cf = np.array([problems[pid]["cf_rating"] for pid in have_cf], float)
        bt = np.array([score[pid] for pid in have_cf], float)
        sur = np.array([problems[pid]["survival_difficulty"] for pid in have_cf], float)
        grp = np.array([problems[pid]["cf_contest_id"] for pid in have_cf], int)
        print(f"\n=== global agreement with official CF ratings (n={len(cf)}) ===")
        print(f"cross-contest BT   Spearman {_spearman(bt, cf):+.3f}")
        print(f"survival fit       Spearman {_spearman(sur, cf):+.3f}")

        # per-contest level: the quantity nothing else can estimate
        print("\n=== per-contest level offsets (CF points) ===")
        # the gym shape needs the whole ratings file to have enough joined
        # pairs; building it from these 185 problems alone silently returns None
        shape = _gym_shape(json.loads(
            (OUTPUT / "problem_ratings_survival.json").read_text(encoding="utf-8")))
        z = shape(sur) if shape else sur
        a_s, b_s = np.polyfit(z, cf, 1)
        fit_resid = cf - (a_s * z + b_s)
        a_b, b_b = np.polyfit(bt, cf, 1)
        bt_resid = cf - (a_b * bt + b_b)
        groups = list(np.unique(grp))
        true_off, bt_off = [], []
        for g in groups:
            m = grp == g
            true_off.append(fit_resid[m].mean())
            bt_off.append(bt_resid[m].mean())
            print(f"  CF {g}: n={m.sum():3d}  fit offset {true_off[-1]:+7.1f}  "
                  f"BT-implied {bt_off[-1]:+7.1f}")
        true_off, bt_off = np.array(true_off), np.array(bt_off)
        corr = float(np.corrcoef(true_off, bt_off)[0, 1])
        print(f"\ncorrelation of BT-implied vs true per-contest offsets: {corr:+.3f}")

        # The BT offsets are noisy, so they must be shrunk before use -- applying
        # them raw overcorrects and makes things worse. k is refit inside each
        # fold, and the held-out contest contributes only its own BT offset.
        rmse = lambda v: float(np.sqrt(np.mean(v ** 2)))  # noqa: E731
        plain, shrunk = [], []
        for g in groups:
            tr, te = grp != g, grp == g
            a_, b_ = np.polyfit(z[tr], cf[tr], 1)
            r_ = cf[tr] - (a_ * z[tr] + b_)
            ab_, bb_ = np.polyfit(bt[tr], cf[tr], 1)
            br_ = cf[tr] - (ab_ * bt[tr] + bb_)
            others = [h for h in groups if h != g]
            to = np.array([r_[grp[tr] == h].mean() for h in others])
            bo = np.array([br_[grp[tr] == h].mean() for h in others])
            k = float(np.dot(to, bo) / np.dot(bo, bo)) if np.dot(bo, bo) > 0 else 0.0
            off = float((cf[te] - (ab_ * bt[te] + bb_)).mean())
            plain.append(cf[te] - (a_ * z[te] + b_))
            shrunk.append(cf[te] - (a_ * z[te] + b_ + k * off))
        loco_plain = rmse(np.concatenate(plain))
        loco_shrunk = rmse(np.concatenate(shrunk))
        k_full = float(np.dot(true_off, bt_off) / np.dot(bt_off, bt_off))
        print(f"shrink factor k (in-sample) {k_full:.3f}   "
              f"(1.0 would mean the BT offsets are noise-free)")
        print(f"LOCO plain {loco_plain:.1f}   LOCO + shrunk BT contest offset "
              f"{loco_shrunk:.1f}   ({loco_shrunk - loco_plain:+.1f})")
        out.update({"cf_spearman_bt": _spearman(bt, cf),
                    "cf_spearman_survival": _spearman(sur, cf),
                    "contest_offset_corr": corr, "shrink_k": k_full,
                    "loco_plain": loco_plain, "loco_with_bt_offset": loco_shrunk})

    (args.run_dir / "analysis.json").write_text(
        json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(f"\nwrote {args.run_dir / 'analysis.json'}")


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("prepare")
    p.add_argument("--scope", choices=("mirrors", "all"), default="mirrors")
    p.add_argument("--matches", type=int, default=6)
    p.add_argument("--output", type=Path, default=DEFAULT_RUN_DIR)
    p.set_defaults(func=prepare)

    c = sub.add_parser("count")
    c.add_argument("--project", required=True)
    c.add_argument("--run-dir", type=Path, default=DEFAULT_RUN_DIR)
    c.add_argument("--location", default=LOCATION)
    c.add_argument("--sample", type=int, default=60)
    c.add_argument("--workers", type=int, default=8)
    c.add_argument("--budget", type=float, default=15.0)
    c.set_defaults(func=count)

    r = sub.add_parser("run")
    r.add_argument("--project", required=True)
    r.add_argument("--run-dir", type=Path, default=DEFAULT_RUN_DIR)
    r.add_argument("--location", default=LOCATION)
    r.add_argument("--workers", type=int, default=8)
    r.set_defaults(func=run)

    a = sub.add_parser("analyse")
    a.add_argument("--run-dir", type=Path, default=DEFAULT_RUN_DIR)
    a.add_argument("--within", default=str(ROOT / "llm_survival_run" / "predictions_full.json"),
                   help="reuse the already-paid within-contest predictions as extra BT edges")
    a.set_defaults(func=analyse)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
