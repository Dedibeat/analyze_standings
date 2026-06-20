"""External validation of difficulty estimates against the LLM opinion.

Each problem in ``data/tagged.json`` carries an LLM ``difficulty_estimate``
(easy / medium / hard / very_hard) written by the sibling ``llm-integration``
tagger from the problem statement -- a signal fully independent of the standings
our estimators use. This script checks that the standings-derived difficulty rises
monotonically across those buckets, for both Architecture A
(``output/problem_ratings.json``) and Architecture B
(``output/problem_ratings_b.json``).

Only **editorial-backed** problems are trusted: the LLM label is reliable enough
to validate against only when the contest shipped an editorial, so problems from
contests with an empty editorial are excluded.

    python -m arch_b.validate
"""

import json
import os

import numpy as np

DATA = os.path.join(os.path.dirname(__file__), os.pardir, "data", "tagged.json")
OUT = os.path.join(os.path.dirname(__file__), os.pardir, "output")
ORDER = ["very_easy", "easy", "medium", "hard", "very_hard"]


def _spearman(x, y):
    rx = np.argsort(np.argsort(x))
    ry = np.argsort(np.argsort(y))
    return float(np.corrcoef(rx, ry)[0, 1])


def _llm_labels(tagged):
    """(contest_id, problem_id) -> difficulty_estimate, editorial-backed only."""
    labels = {}
    for c in tagged:
        ed = c.get("editorial")
        if not (ed and str(ed).strip()):
            continue  # untrusted: no editorial shipped
        for p in c["problems"]:
            de = p.get("difficulty_estimate")
            if de in ORDER:
                labels[(c["contest_id"], p["problem_id"])] = ORDER.index(de)
    return labels


def _report(name, ratings_path, labels):
    ratings = json.load(open(ratings_path))
    bmap = {(r["contest_id"], r["problem_id"]): r["difficulty"] for r in ratings}
    rank, diff = [], []
    buckets = {}
    for key, lvl in labels.items():
        if key in bmap:
            rank.append(lvl)
            diff.append(bmap[key])
            buckets.setdefault(lvl, []).append(bmap[key])
    rank, diff = np.array(rank), np.array(diff)
    print(f"\n{name}  (n={len(diff)} editorial-backed problems)")
    for lvl in sorted(buckets):
        v = np.array(buckets[lvl])
        print(f"    {ORDER[lvl]:10s} n={len(v):4d}  median {np.median(v):6.0f}  mean {v.mean():6.0f}")
    print(f"    Spearman(LLM bucket, difficulty) = {_spearman(rank, diff):+.3f}")


def main():
    tagged = json.load(open(DATA))
    labels = _llm_labels(tagged)
    print(f"trusted set: {len(labels)} problems from editorial-backed contests")
    _report("Architecture A", os.path.join(OUT, "problem_ratings.json"), labels)
    _report("Architecture B (binary)", os.path.join(OUT, "problem_ratings_b.json"), labels)
    surv = os.path.join(OUT, "problem_ratings_survival.json")
    if os.path.exists(surv):
        _report("Architecture B (survival)", surv, labels)


if __name__ == "__main__":
    main()
