"""Ability-side anchor: a time-accurate Codeforces prior on team ability.

Every other anchor in the repo pins the *difficulty* axis -- the CF problemset
ratings of 185 mirrored problems, the gym-mirror difficulties, Kattis, AOJ. All
of them together reach 92 of 207 fitted contests, and all 185 CF anchor problems
come from just three regions (Asia Pacific, Northern Eurasia, Europe), so the
calibration is fit on three regions and extrapolated onto the other five.

This module anchors the *ability* axis instead, which is what ``strat.tex``
originally prescribed (eq. cfprior) and which reaches regions the problem side
cannot: of the 2,119 roster-corroborated standing appearances in
``data/cphof_cf_participants.json``, 1,677 (79%) are Asia East Continent -- the
region with no CF problem anchor at all. A team pinned on the ability axis
propagates to ``b`` through the likelihood in every contest it played.

Conservative by construction:

* **Roster-complete only.** A standing row supplies a prior only when *every*
  member resolves to an explicit CPHoF Codeforces profile with a rating at the
  cutoff. A partially resolved roster would silently treat its unknown members
  as absent and make the team look weaker than it is.
* **Leak-free cutoff.** ``tagged.json`` regionals carry only a ``year`` and no
  start time, so the cutoff is 00:00 UTC on 1 January of that year: strictly
  before any contest of that season, at the cost of a rating up to a year stale.
  No timestamp is invented (see ``cf_participant_ratings.md``).
* **Relative, not absolute.** A team's prior mean is
  ``MU0 + CF_SCALE * (cf_team - mean cf_team over anchored teams)``. Our theta
  lives on a MAP-shrunk relative scale pinned at ``MU0``; importing raw CF points
  would stretch the anchored teams against everyone else. Only the ordering and
  spacing of the CF abilities is used, never their level -- so this stays
  independent of the CF *problem* ratings the metric scores against.
* **Trust-weighted precision.** The prior sd is ``CF_SIGMA / sqrt(trust)`` with
  the repo's reliability convention ``trust = 1 - 0.9^n`` on the member's rated
  contest count at the cutoff, so a team of newcomers is barely pulled.

Team strength is the ``lse`` reduction ``gym_difficulty`` already uses:
``theta_team = s * log sum_i exp(r_i / s)``, the single solver equivalent to the
members solving independently.

**Measured: inert as a prior, useful as a yardstick.** Only 57 team identities
are roster-complete at the cutoff, and they are World-Finals-level teams that
play many contests, so their own likelihood already pins them: sweeping
``scale`` in {0.5, 1.0} against ``cf_sigma`` in {100, 200, 400} moves the
calibrated metric by at most 0.2 (245.4 -> 245.6 at the tightest setting) with
every guard unchanged. It is therefore **not enabled by default** -- pass it to
``joint.estimate_joint(prior=...)`` to turn it on.

What it does buy is the repo's first external check of the *ability* axis, which
no other yardstick reaches (``--validate``): over those 57 teams fitted theta
agrees with CF team ability at Pearson +0.75 / Spearman +0.76, and the implied
compression is ``cf ~ 2.86 * theta`` -- far steeper than the 1.63 slope the
shipped difficulty map applies over the same range, even though theta and b
share one logit scale by construction. See the anchoring audit in details.md.

    python -m arch_b.cf_prior             # coverage report
    python -m arch_b.cf_prior --validate  # + score the fitted ability axis
"""

import bisect
import calendar
import json
import os
from collections import defaultdict

import numpy as np

from arch_a import elo
from arch_a.load import team_key
from .aoj import spearman
from .model import MU0

DATA = os.path.join(os.path.dirname(__file__), os.pardir, "data")
CPHOF = os.path.join(DATA, "cphof_cf_participants.json")

CF_SCALE = 1.0    # how much of the CF ability spread to import (1 = as-is)
CF_SIGMA = 200.0  # prior sd for a fully trusted anchored team (vs 400 elsewhere)


def _rating_at(history, cutoff):
    """(rating, rated_contest_count) at ``cutoff``, or None if unrated by then."""
    times = [h["ratingUpdateTimeSeconds"] for h in history]
    i = bisect.bisect_right(times, cutoff)
    if i == 0:
        return None
    return history[i - 1]["newRating"], i


def _cutoff(year):
    """00:00 UTC on 1 January of ``year`` -- strictly before that season."""
    return calendar.timegm((year, 1, 1, 0, 0, 0))


def team_abilities(uf, season_by_cid=None):
    """Resolve roster-complete CF rosters to {team_key: (cf_theta, trust, n)}.

    ``uf`` is the union-find the fit resolved identity through, so the returned
    keys line up with ``ds.teams``. ``n`` is how many standing rows contributed.
    """
    with open(CPHOF) as f:
        art = json.load(f)

    history = {}
    for p in art["participants"]:
        if p.get("cf_handle") and p.get("rating_history"):
            history[p["normalized_name"]] = p["rating_history"]

    # group the corroborated appearances by the standing row they came from
    rows = defaultdict(lambda: {"members": {}, "meta": None})
    for p in art["participants"]:
        name = p["normalized_name"]
        if name not in history:
            continue
        for a in p.get("tagged_appearances", []):
            if a.get("identity_evidence", {}).get("status") != "roster_corroborated":
                continue
            roster = a.get("roster") or []
            if not roster or a.get("year") is None:
                continue
            key = (a["contest_id"], a["team_id"], tuple(roster))
            rows[key]["members"][name] = history[name]
            rows[key]["meta"] = a

    out = {}
    for (cid, team_id, roster), row in rows.items():
        a = row["meta"]
        cutoff = _cutoff(a["year"])
        ratings, trusts = [], []
        for member in roster:
            hit = row["members"].get(_norm_name(member))
            at = _rating_at(hit, cutoff) if hit else None
            if at is None:
                break                      # roster not complete at the cutoff
            rating, count = at
            ratings.append(rating)
            trusts.append(1.0 - 0.9 ** count)
        if len(ratings) != len(roster):
            continue
        ratings = np.array(ratings, float)
        share = np.exp((ratings - ratings.max()) / elo.S)
        share /= share.sum()
        cf_theta = ratings.max() + elo.S * np.log(np.sum(np.exp((ratings - ratings.max()) / elo.S)))
        trust = float(np.dot(share, trusts))

        season = None if season_by_cid is None else season_by_cid.get(cid)
        tk = team_key(cid, team_id, list(roster), uf, season)
        prev = out.get(tk)
        if prev is None:
            out[tk] = [cf_theta * trust, trust, 1]
        else:
            prev[0] += cf_theta * trust
            prev[1] += trust
            prev[2] += 1
    return {tk: (total / w, w / n, n) for tk, (total, w, n) in out.items() if w > 0}


def _norm_name(name):
    import unicodedata
    return unicodedata.normalize("NFKC", name).casefold().strip()


def prior(ds, uf, sigma_theta, season_by_cid=None, scale=CF_SCALE,
          cf_sigma=CF_SIGMA, verbose=False):
    """(prior_mu, sigma_theta) arrays for ``ds.teams`` with the CF anchor applied."""
    abilities = team_abilities(uf, season_by_cid)
    mu = np.full(len(ds.teams), float(MU0))
    sd = np.full(len(ds.teams), float(sigma_theta))

    hits = [(i, abilities[tk]) for i, tk in enumerate(ds.teams) if tk in abilities]
    if not hits:
        if verbose:
            print("cf_prior: no anchored teams in this dataset")
        return mu, sd
    centre = float(np.mean([cf for _, (cf, _, _) in hits]))
    for i, (cf, trust, _n) in hits:
        mu[i] = MU0 + scale * (cf - centre)
        sd[i] = cf_sigma / max(np.sqrt(trust), 1e-3)
    if verbose:
        pulled = np.array([mu[i] for i, _ in hits])
        print(f"cf_prior: {len(hits)} of {len(ds.teams)} teams anchored; "
              f"prior mean [{pulled.min():.0f}, {pulled.max():.0f}] "
              f"(centre {centre:.0f} CF), sd [{sd[[i for i, _ in hits]].min():.0f}, "
              f"{sd[[i for i, _ in hits]].max():.0f}]")
    return mu, sd


def main(validate=False):
    """Coverage report; ``--validate`` also scores the fitted ability axis."""
    import contextlib
    import io

    from arch_a.load import _max_solve_seconds, dedupe_contests, member_identity
    from .joint import OLDER_ICPC, PETROZ, TAGGED, UCUP, WF, estimate_joint
    from .run import MIN_SOLVE_HOURS

    with open(CPHOF) as f:
        art = json.load(f)
    print(f"artifact: {len(art['participants'])} explicit identities, "
          f"{art['matching']['roster_corroborated_tagged_appearances']} corroborated appearances")

    raw = []
    for path in [TAGGED, OLDER_ICPC, PETROZ, WF] + UCUP:
        with open(path) as f:
            raw.extend(json.load(f))
    raw = dedupe_contests(raw)
    raw = [c for c in raw if _max_solve_seconds(c) >= MIN_SOLVE_HOURS * 3600]
    uf = member_identity(raw, None)

    ab = team_abilities(uf)
    cf = np.array([v[0] for v in ab.values()])
    trust = np.array([v[1] for v in ab.values()])
    print(f"roster-complete anchored team identities: {len(ab)} "
          f"from {sum(v[2] for v in ab.values())} standing rows")
    print(f"team CF ability: [{cf.min():.0f}, {cf.max():.0f}] mean {cf.mean():.0f} "
          f"sd {cf.std():.0f}; trust median {np.median(trust):.2f} min {trust.min():.2f}")
    if not validate:
        return

    from . import survival
    with contextlib.redirect_stdout(io.StringIO()):
        ds, theta, _b, _h, uf_fit = estimate_joint(fit_fn=survival.fit,
                                                   min_solve_hours=MIN_SOLVE_HOURS)
    index = {tk: i for i, tk in enumerate(ds.teams)}
    pairs = [(theta[index[tk]], v[0]) for tk, v in team_abilities(uf_fit).items()
             if tk in index]
    x = np.array([a for a, _ in pairs])
    y = np.array([c for _, c in pairs])
    slope, icept = np.polyfit(x, y, 1)
    print(f"\n=== ability-axis validation ({len(x)} teams) ===")
    print(f"fitted theta vs CF team ability: Pearson "
          f"{np.corrcoef(x, y)[0, 1]:+.3f}  Spearman {spearman(x, y):+.3f}")
    print(f"cf_ability ~ {slope:.2f} * theta {icept:+.0f}  "
          f"(sd ratio {y.std() / x.std():.2f}; residual sd {(y - (slope * x + icept)).std():.0f} CF)")
    print(f"theta [{x.min():.0f}, {x.max():.0f}] sd {x.std():.0f}  |  "
          f"cf [{y.min():.0f}, {y.max():.0f}] sd {y.std():.0f}")


if __name__ == "__main__":
    import sys
    main(validate="--validate" in sys.argv[1:])
