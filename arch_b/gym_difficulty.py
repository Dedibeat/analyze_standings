"""Fixed-theta Rasch difficulty from the Codeforces gym-mirror population.

``data/cf_gym_mirrors.json`` (see details.md) records, for 62 of our contests,
every real timed gym attempt with each solver's **time-accurate Codeforces
rating** (``cf_rating_at_attempt``). Unlike the main fit, ability is therefore
*known* on the true CF scale, so we fix theta and solve a 1-D concave MAP per
problem for ``b_p`` only -- the closest thing to the strat's original CF anchor
(eq. cfprior) available in this repo:

    maximize_b  sum_t w_t [ y_tp log pi(theta_t, b) + (1-y_tp) log(1-pi) ]
                - (b - mu_b)^2 / (2 sigma_b^2)

Trust policy (clist.by-style: a rating backed by few rated contests is noisy).
Each member's likelihood weight is the repo's reliability convention
``w = 1 - 0.9^n`` with n = ``cf_rated_contests_at_attempt`` (1 contest -> 0.1,
10 -> 0.65, 30 -> ~0.96); members with no rating yet are excluded, and a team
with no rated member is dropped.

Team reduction (solving is per-team, the file keeps members grouped so the rule
is ours to choose -- two variants, compared by ``--certify``):

  * ``max`` -- theta = the strongest rated member; team weight = that member's
    trust. The standard "a team is as good as its best member" baseline.
  * ``lse`` -- theta = s * log sum_i exp(r_i / s). Principled at the hard end:
    if members solve independently with Rasch probabilities, P(team solves)
    ~= sum_i exp((r_i - b)/s) for hard problems, i.e. the team acts as one
    solver of ability logsumexp(r_i). Equal duo -> max + 120, trio -> +191.
    Team weight = the contribution-weighted (softmax) member trust.

Problem identity. Gym problem *names* live in the standings checkpoint
(``data/gym_checkpoints/api_standings.json``); we join gym problems to ours by
normalized name within the contest. The five ``labels_aligned: false`` contests
turn out to match **zero** problem names -- the keyword contest-matching picked
a different event in the same region/season (e.g. our qoj 2657 "Taiwan" is the
CF-2172-mirrored contest, but gym 106084 is a different 2025 Taiwan round; the
Iran contest's qoj names are in Farsi) -- so they are dropped wholesale, not
joined by letter. 57 contests / ~700 problems survive.

Certification (``--certify``). Before trusting b_gym as a yardstick we check it
against the two independent sources on whatever overlap exists: official CF
problemset ratings (name-join within the rated problemset, unique names only)
and Kattis difficulty. This also picks between ``max`` and ``lse``.

    python -m arch_b.gym_difficulty            # fit + write output/gym_difficulty.json
    python -m arch_b.gym_difficulty --certify  # compare reductions vs CF + Kattis
"""

import json
import os
import re
import sys
from collections import defaultdict

import numpy as np

from arch_a import elo

ROOT = os.path.join(os.path.dirname(__file__), os.pardir)
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(ROOT, "output")
GYM = os.path.join(DATA, "cf_gym_mirrors.json")
GYM_STANDINGS = os.path.join(DATA, "gym_checkpoints", "api_standings.json")
OUT_FILE = os.path.join(OUT, "gym_difficulty.json")

MU_B = 2000.0      # difficulty prior mean (as in arch_b.model)
SIGMA_B = 400.0    # difficulty prior std
REDUCTION = "lse"  # shipped team-reduction rule (certify: ties with max on both
                   # yardsticks; kept for the principled team-strength story)


def _norm(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())


def _trust(n):
    """clist.by-style reliability of a rating backed by n rated contests."""
    return 1.0 - 0.9 ** n


def team_theta(members, reduction):
    """(theta, weight) for one team from its rated members, or None.

    ``max``: ability of the strongest member, weighted by that member's trust.
    ``lse``: s*logsumexp(r_i/s) -- the ability of the single solver equivalent
    to the members solving independently (hard-problem limit) -- weighted by the
    softmax-contribution-weighted member trust.
    """
    rated = [(m["cf_rating_at_attempt"], m["cf_rated_contests_at_attempt"])
             for m in members if m["cf_rating_at_attempt"] is not None]
    if not rated:
        return None
    r = np.array([x[0] for x in rated], float)
    w = _trust(np.array([x[1] for x in rated], float))
    if reduction == "max":
        i = int(np.argmax(r))
        return float(r[i]), float(w[i])
    # lse
    z = np.exp((r - r.max()) / elo.S)
    theta = r.max() + elo.S * np.log(z.sum())
    return float(theta), float((w * z).sum() / z.sum())


def load_gym():
    """Parse the gym file into per-contest fit inputs, name-joined to ours.

    Returns a list of dicts: {contest_id, region, gym_id, problems: [(gym_label,
    our_label, problem_name)], teams: [(theta_members, solved_set)]} where
    problems keeps only name-matched gym problems and teams keep raw members
    (the reduction is applied at fit time so --certify can sweep it).
    """
    gym = json.load(open(GYM))
    standings = json.load(open(GYM_STANDINGS))
    tagged = json.load(open(os.path.join(DATA, "tagged.json")))
    ours = {c["contest_id"]: {_norm(p["problem_name"]): p["problem_label"]
                              for p in c["problems"]} for c in tagged}

    contests, dropped = [], []
    for qoj, v in gym.items():
        cid = int(qoj)
        gym_names = {p["index"]: p["name"]
                     for p in standings[str(v["gym_id"])]["problems"]}
        probs = [(lbl, ours[cid][_norm(nm)], nm) for lbl, nm in gym_names.items()
                 if _norm(nm) in ours.get(cid, {})]
        if len(probs) < 0.6 * len(gym_names):   # wrong gym matched -> drop
            dropped.append((cid, v["contest_name"], len(probs), len(gym_names)))
            continue
        contests.append({
            "contest_id": cid, "region": v["region"], "gym_id": v["gym_id"],
            "problems": sorted(probs),
            "teams": [(t["members"], set(t["solved"])) for t in v["teams"]],
        })
    for cid, name, hit, tot in dropped:
        print(f"  dropped qoj {cid} ({name}): {hit}/{tot} problem names match "
              f"-- wrong gym event")
    return contests


def fit(contests, reduction=REDUCTION, mu_b=MU_B, sigma_b=SIGMA_B,
        eps=0.01, max_iter=100):
    """Weighted fixed-theta Rasch MAP over all contests at once.

    Returns (rows, b) where rows are output dicts (one per name-matched
    problem) and b the difficulty vector aligned with them. theta is fixed, so
    each b_p is an independent 1-D strictly concave problem; one vectorized
    Newton block (the ``b`` step of arch_b.model with per-observation weights)
    converges in a few iterations.
    """
    rows, obs_t, obs_p, obs_y, obs_w, thetas = [], [], [], [], [], []
    for c in contests:
        pidx = {}
        for gym_label, our_label, name in c["problems"]:
            pidx[gym_label] = len(rows)
            rows.append({"contest_id": c["contest_id"], "region": c["region"],
                         "gym_id": c["gym_id"], "problem_label": our_label,
                         "problem_name": name, "n_teams": 0, "n_solved": 0})
        for members, solved in c["teams"]:
            red = team_theta(members, reduction)
            if red is None:
                continue
            theta, w = red
            t = len(thetas)
            thetas.append(theta)
            for gym_label, j in pidx.items():
                y = 1.0 if gym_label in solved else 0.0
                obs_t.append(t); obs_p.append(j); obs_y.append(y); obs_w.append(w)
                rows[j]["n_teams"] += 1
                rows[j]["n_solved"] += int(y)

    theta = np.array(thetas)
    obs_t, obs_p = np.array(obs_t), np.array(obs_p)
    obs_y, obs_w = np.array(obs_y), np.array(obs_w)
    prec = 1.0 / sigma_b**2
    b = np.full(len(rows), mu_b)

    for _ in range(max_iter):
        pi = elo.pi(theta[obs_t], b[obs_p])
        grad = np.zeros_like(b)
        negH = np.full_like(b, prec)
        np.add.at(grad, obs_p, obs_w * (obs_y - pi))
        np.add.at(negH, obs_p, obs_w * pi * (1.0 - pi) / elo.S**2)
        grad = -grad / elo.S - prec * (b - mu_b)
        new_b = np.clip(b + grad / negH, elo.LO, elo.HI)
        delta = np.max(np.abs(new_b - b))
        b = new_b
        if delta < eps:
            break

    pi = elo.pi(theta[obs_t], b[obs_p])
    negH = np.full_like(b, prec)
    np.add.at(negH, obs_p, obs_w * pi * (1.0 - pi) / elo.S**2)
    se = 1.0 / np.sqrt(negH)
    for j, row in enumerate(rows):
        row["difficulty"] = round(float(b[j]), 1)
        row["difficulty_se"] = round(float(se[j]), 1)
    return rows, b


def _spearman(x, y):
    x, y = np.asarray(x, float), np.asarray(y, float)
    return float(np.corrcoef(np.argsort(np.argsort(x)), np.argsort(np.argsort(y)))[0, 1])


def _cf_contest_pairs(contests, rows):
    """Contest-scoped join of gym problems to official CF problemset ratings.

    A flat name join across the whole problemset is dominated by coincidental
    generic titles ("Flowers", "Quick Sort"), so we join at contest level, the
    same vote ``external_validate._cf_mapping`` uses: a gym contest pairs with a
    rated CF contest only if >=60% (and >=5) of its problem names appear there.
    In practice this finds the originals that were *also* run as rated CF
    mirrors (e.g. qoj 2692 <-> CF 2157, a mirror absent from
    ``cf_team_contests.txt``). Returns [(b_gym, cf_rating)] plus the mapping.
    """
    from arch_b.external_validate import CF_CACHE
    by_cf = defaultdict(dict)   # cf contest id -> {norm name: rating}
    for p in json.load(open(CF_CACHE)):
        if "rating" in p:
            by_cf[p["contestId"]][_norm(p["name"])] = p["rating"]

    by_contest = defaultdict(dict)   # qoj -> {norm name: b_gym}
    for r in rows:
        by_contest[r["contest_id"]][_norm(r["problem_name"])] = r["difficulty"]
    pairs, mapping = [], []
    for qoj, ours in by_contest.items():
        votes = {cf: sum(nm in names for nm in ours)
                 for cf, names in by_cf.items()}
        cf, hits = max(votes.items(), key=lambda kv: kv[1])
        if hits < max(5, 0.6 * len(ours)):
            continue
        mapping.append((qoj, cf, hits))
        pairs += [(ours[nm], by_cf[cf][nm]) for nm in ours if nm in by_cf[cf]]
    return pairs, mapping


def certify(contests):
    """Check b_gym against official CF ratings and Kattis; compare reductions.

    CF: contest-scoped name join (see ``_cf_contest_pairs``) -- the strongest
    check, same problems officially rated by CF. Kattis: the usual global name
    join, scored head-to-head against the shipped survival model on the *same*
    problem subset (the question is whether b_gym is a sharper yardstick than
    the model it is meant to validate). Both are independent of the gym
    standings the fit uses.
    """
    from arch_b.external_validate import KATTIS
    kat = {_norm(v["name"]): v["difficulty"]
           for v in json.load(open(KATTIS)).values()}
    surv_path = os.path.join(OUT, "problem_ratings_survival.json")
    surv = {(r["contest_id"], r["problem_label"]): r["difficulty"]
            for r in json.load(open(surv_path))} if os.path.exists(surv_path) else {}

    for reduction in ("max", "lse"):
        rows, b = fit(contests, reduction=reduction)
        print(f"\n[{reduction}]  b range [{b.min():.0f}, {b.max():.0f}], "
              f"mean {b.mean():.0f}")

        cf_pairs, mapping = _cf_contest_pairs(contests, rows)
        if cf_pairs:
            ours = np.array([a for a, _ in cf_pairs])
            cf = np.array([c for _, c in cf_pairs])
            slope, icept = np.polyfit(ours, cf, 1)
            rmse = float(np.sqrt(np.mean((slope * ours + icept - cf) ** 2)))
            print(f"  vs CF rated mirrors {[(q, c) for q, c, _ in mapping]} "
                  f"(n={len(cf_pairs)}): Spearman={_spearman(ours, cf):+.3f}  "
                  f"Pearson={np.corrcoef(ours, cf)[0, 1]:+.3f}  "
                  f"affine slope={slope:.2f} icept={icept:+.0f}  RMSE={rmse:.0f}")
        else:
            print("  vs CF rated mirrors: no contest-level match")

        tri = [(r["difficulty"], kat[nm], surv[(r["contest_id"], r["problem_label"])])
               for r in rows for nm in [_norm(r["problem_name"])]
               if nm in kat and (r["contest_id"], r["problem_label"]) in surv]
        print(f"  vs Kattis (n={len(tri)}): "
              f"gym Spearman={_spearman([g for g, _, _ in tri], [k for _, k, _ in tri]):+.3f}  "
              f"(survival model on same subset: "
              f"{_spearman([s for _, _, s in tri], [k for _, k, _ in tri]):+.3f})")


def main():
    contests = load_gym()
    n_probs = sum(len(c["problems"]) for c in contests)
    print(f"{len(contests)} contests, {n_probs} name-matched problems, "
          f"{sum(len(c['teams']) for c in contests)} team attempts")
    if "--certify" in sys.argv[1:]:
        certify(contests)
        return
    rows, b = fit(contests)
    json.dump(rows, open(OUT_FILE, "w"), indent=1, ensure_ascii=False)
    se = np.array([r["difficulty_se"] for r in rows])
    print(f"reduction={REDUCTION}: b range [{b.min():.0f}, {b.max():.0f}], "
          f"mean {b.mean():.0f}; SE median {np.median(se):.0f}")
    print(f"wrote {len(rows)} problems -> {OUT_FILE}")


if __name__ == "__main__":
    main()
