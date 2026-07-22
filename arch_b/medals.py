"""Medal badges for Asia East Continent regionals + the lowest-gold-team analysis.

ICPC East Asia regionals award medals by cumulative percentile of the *official*
teams that solved at least one problem: gold 10%, silver 30%, bronze 60%. The
official field is sourced from **XCPCIO** (``data/xcpcio_ea_official.json``), which
hosts the official ICPC scoreboard data — each contest's official teams are
identified by name-matching XCPCIO's team.json against QOJ standing rows.

Badge model (medal-bar thresholds on the fitted difficulty scale): each badge
boundary is anchored at a cohort of official teams — the +-WINDOW official
ranks around an anchor rank — and set to the difficulty at which that cohort
actually solves at 50% odds: its per-problem solve rates are isotonic-regressed
(PAVA, non-increasing in the UCup-anchored survival-model difficulty b) and the
bar is the b where the smoothed rate crosses 0.5.

The ladder is the three medal tiers plus platinum, each split into a normal
and a "+" grade (TIER_BARS): the **"+" edge is the medal cutoff itself**
(gold 10% / silver 30% / bronze 60% cumulative percentile of official solving
teams) and the **normal edge is the mid-band cohort** (the rank midway to the
next weaker cutoff — 20% / 45% / 80%; for bronze the "next cutoff" is the
bottom of the field, so plain bronze covers the giveaway problems the whole
field solves). A problem gets the weakest grade whose bar clears it:

    bronze < bronze+ < silver < silver+ < gold < gold+ < plat < plat+

Above the gold-medal bar sits **platinum**, split by the crossing anchored at
the **champion cohort** (the top TOP_COHORT official teams, exact cohort — no
window): **plat** = above the gold bar but the champions still solve it at even
odds (it decides ranking *within* gold), **plat+** = beyond even the champions
(the genuinely extreme problems — almost all have 0-2 official solves). A
champion cohort that solves everything at >= 50% pins its bar to elo.HI, so
that contest simply has no plat+ problems.

Why empirical bars instead of model-predicted solve probabilities: the Elo
rank-inversion performance rating is inflated against the Rasch/survival b
scale (predicted-minus-actual solve rate +0.10 bronze / +0.34 gold), and even
the solve-count-inversion ability is miscalibrated at the 50% point (where it
predicts 50%, cutoff cohorts actually solve 57-92%) because EA fields' solve
curves are far steeper than the global Rasch slope (the 2PL finding: EA
discrimination ~2.1, see details.md). The isotonic crossing measures the 50%
point directly and stays a threshold on b, so badges remain monotone in
difficulty and cross-contest comparable.

A model-free sanity badge is reported alongside: the weakest half-band of
official teams (the ranks between consecutive badge anchors, e.g. gold+ =
ranks 1..10%, gold = 10..20%, ..., bronze = below the 60% bronze cutoff) where
>= 50% solved the problem; the top-TOP_COHORT majority splits plat from plat+.
It anchors on the band *majority* rather than the boundary cohort, so it skews
one grade easier where the two disagree.

Scope: Asia East Continent contests that actually award medals — the 6 online
qualifiers (contest_name "ICPC") and the EC-Final warm-ups are excluded.
Includes EC-Finals (Shanghai 2023 = 48th EC-Final, China 2024 = 49th EC-Final).

Bars and difficulties are also reported in Codeforces points through the same
gym-shaped two-leg map as ``arch_b.calibrate`` (monotone, so CF-space badges
are identical). The lowest-gold-team record additionally carries the classic
Elo rank-inversion performance (labelled ``performance_elo``) and the fitted
theta, for the cross-contest gold-bar analysis.

    python -m arch_b.medals

Writes output/medal_badges.json: {"contests": [...], "problems": [...]}.
"""

import json
import math
import os
import re
import statistics

import numpy as np

from arch_a import elo
from arch_a.load import dedupe_contests, team_key
from . import survival
from .anchor import TAGGED, estimate_anchored
from .calibrate import _anchors, _gym_shape
from .run import MIN_SOLVE_HOURS

OUT = os.path.join(os.path.dirname(__file__), os.pardir, "output")
XCPCIO_CACHE = os.path.join(os.path.dirname(__file__), os.pardir,
                            "data", "xcpcio_ea_official.json")

MEDAL_PCT = [("gold", 0.10), ("silver", 0.30), ("bronze", 0.60)]
# badge boundaries, weakest -> hardest: the "+" edge is the medal cutoff itself,
# the normal edge the mid-band cohort (midway to the next weaker cutoff; for
# bronze that is the bottom of the field, 100%)
TIER_BARS = [("bronze", 0.80), ("bronze+", 0.60), ("silver", 0.45),
             ("silver+", 0.30), ("gold", 0.20), ("gold+", 0.10)]
WINDOW = 7                     # +- official ranks around an anchor = the boundary cohort
TOP_COHORT = 5                 # the champion cohort anchoring the plat/plat+ split
BADGE_ORDER = ["bronze", "bronze+", "silver", "silver+",
               "gold", "gold+", "plat", "plat+"]  # weakest -> hardest


def _norm(name: str) -> str:
    return "".join(c for c in str(name).lower() if c.isalnum())


def _strip_paren(s: str) -> str:
    return re.sub(r"\s*\([^)]*\)", "", s).strip()


def _load_xcpcio_cache():
    """Return {contest_id: {"board_link": ..., "official_keys": [[k,...], ...]}}."""
    with open(XCPCIO_CACHE) as f:
        raw = json.load(f)
    out = {}
    for cid_str, v in raw.items():
        if "error" not in v:
            # Build flat lookup set for fast matching
            flat = set()
            for keys in v["official_keys"]:
                for k in keys:
                    flat.add(k)
            out[int(cid_str)] = {"board_link": v["board_link"],
                                 "official_set": flat,
                                 "n_official": v["n_official"]}
    return out


def _is_official(row: dict, xcpcio_set: set) -> bool:
    """Check if a QOJ standing row matches any XCPCIO official team key."""
    qoj_keys = {_norm(row.get("team_name", "") or "")}
    raw = str(row.get("display_name_raw", "") or "")
    if raw:
        qoj_keys.add(_norm(raw))
        parts = raw.split(" - ")
        for n in range(2, len(parts) + 1):
            qoj_keys.add(_norm(" - ".join(parts[:n])))
    return bool(qoj_keys & xcpcio_set)


def medal_contests():
    """Raw EA contests that award medals, keyed by contest_id.

    Only returns contests that have XCPCIO official-team data available.
    """
    xcpcio = _load_xcpcio_cache()
    with open(TAGGED) as f:
        raw = dedupe_contests(json.load(f))
    out = {}
    for c in raw:
        cid = c["contest_id"]
        name = c["contest_name"].strip()
        if (c["region"] == "Asia East Continent"
                and name != "ICPC"                      # online qualifiers
                and "warm up" not in name.lower()       # EC-Final warm-ups
                and cid in xcpcio):                     # must have XCPCIO data
            out[cid] = c
    return out


def _cf_map(records):
    """The composed b -> CF-points map from arch_b.calibrate (monotone)."""
    shape = _gym_shape(records)
    if shape is None:
        shape = lambda t: np.asarray(t, float)
    our, cf, _ = _anchors(records)
    slope, intercept = np.polyfit(shape(our), cf, 1)
    return lambda t: float(np.clip(slope * shape(np.array([t]))[0] + intercept,
                                   elo.LO, elo.HI))


def _pava_decreasing(y):
    """Isotonic non-increasing fit (pool adjacent violators), unit weights."""
    blocks = [[-v, 1] for v in y]
    out = []
    for bl in blocks:
        out.append(bl)
        while len(out) > 1 and out[-2][0] / out[-2][1] > out[-1][0] / out[-1][1]:
            s2, w2 = out.pop()
            s1, w1 = out.pop()
            out.append([s1 + s2, w1 + w2])
    res = []
    for s, w in out:
        res.extend([-s / w] * w)
    return res


def _solve_rate(rows, label):
    """Fraction of standing rows that solved the problem with this label."""
    return sum(1 for r in rows
               if (r.get("problems") or {}).get(label, {}).get("solved")) / len(rows)


def _medal_bar(officials, cut_idx, bs_sorted, labels_sorted):
    """Difficulty at which the boundary cohort's solve rate crosses 50%.

    ``bs_sorted`` / ``labels_sorted`` are the contest's problems in increasing
    fitted difficulty; the cohort is the +-WINDOW official ranks at the cutoff.
    """
    lo, hi = max(0, cut_idx - WINDOW), min(len(officials), cut_idx + WINDOW + 1)
    return _cohort_bar(officials[lo:hi], bs_sorted, labels_sorted)


def _cohort_bar(cohort, bs_sorted, labels_sorted):
    """Difficulty at which this cohort's isotonic solve rate crosses 50%."""
    iso = _pava_decreasing([_solve_rate(cohort, lab) for lab in labels_sorted])
    if iso[0] < 0.5:
        return elo.LO
    if iso[-1] >= 0.5:
        return elo.HI
    for i in range(1, len(iso)):
        if iso[i] < 0.5 <= iso[i - 1]:
            t = (iso[i - 1] - 0.5) / max(iso[i - 1] - iso[i], 1e-9)
            return float(bs_sorted[i - 1] + t * (bs_sorted[i] - bs_sorted[i - 1]))


def main():
    ds, theta, b, _, uf = estimate_anchored(fit_fn=survival.fit,
                                            min_solve_hours=MIN_SOLVE_HOURS)
    # records for the calibration helpers (same shape run.py exports)
    records = [{"contest_id": int(cid), "problem_label": label,
                "problem_name": name, "difficulty": float(b[p])}
               for p, (cid, label, _pid, name) in enumerate(ds.problems)]
    to_cf = _cf_map(records)

    team_idx = {tk: i for i, tk in enumerate(ds.teams)}
    contest_idx = {cid: ci for ci, cid in enumerate(ds.contests)}
    xcpcio = _load_xcpcio_cache()

    contests_out, problems_out, agree, total = [], [], 0, 0
    for cid, c in sorted(medal_contests().items(),
                         key=lambda kv: (kv[1].get("year"), kv[0])):
        ci = contest_idx.get(cid)
        if ci is None:
            print(f"skip {cid} {c['contest_name']}: not in the fit")
            continue

        xc = xcpcio[cid]
        officials = sorted(
            (r for r in c["standings"]
             if _is_official(r, xc["official_set"])
             and r["total_solved"] >= 1),
            key=lambda r: r["rank"])
        n = len(officials)
        if n < 10:
            print(f"skip {cid} {c['contest_name']}: only {n} official solving teams "
                  f"(XCPCIO has {xc['n_official']} total)")
            continue

        ps = np.flatnonzero(ds.contest_of_problem == ci)
        order = np.argsort(b[ps])
        bs_sorted = b[ps][order]
        labels_sorted = [ds.problems[p][1] for p in ps[order]]

        cuts = {tier: math.ceil(n * pct) for tier, pct in MEDAL_PCT}
        anchor = {tier: math.ceil(n * pct) for tier, pct in TIER_BARS}
        bar = {tier: _medal_bar(officials, anchor[tier] - 1, bs_sorted, labels_sorted)
               for tier, _ in TIER_BARS}
        bar["plat"] = _cohort_bar(officials[:TOP_COHORT], bs_sorted, labels_sorted)
        for weak, hard in zip(BADGE_ORDER, BADGE_ORDER[1:-1]):  # enforce tier order
            bar[hard] = max(bar[hard], bar[weak])

        # Medal cutoff teams: solved count, penalty, full-field rank and performance.
        # Cutoff ranks are computed from the XCPCIO-identified official field, but
        # the cutoff team's performance is ranked against the FULL standings (all teams,
        # including unofficial/star) — they competed on-site and carry signal.
        rows = np.flatnonzero(ds.contest_of_row == ci)
        field_theta = theta[ds.team_of_row[rows]]
        cutoff_teams = {}
        for tier, _ in MEDAL_PCT:
            ct = officials[cuts[tier] - 1]
            tk = team_key(cid, ct["team_id"], ct.get("members"), uf)
            ti = team_idx.get(tk)
            rivals = field_theta
            if ti is not None:
                drop = np.flatnonzero(ds.team_of_row[rows] == ti)[:1]
                rivals = np.delete(field_theta, drop)
            perf = elo.performance_rating(ct["rank"], rivals)
            cutoff_teams[tier] = {
                "team_name": ct["team_name"],
                "affiliation": ct.get("affiliation"),
                "rank_full_field": ct["rank"],
                "rank_official": cuts[tier],
                "solved": ct["total_solved"],
                "penalty_seconds": ct.get("penalty_seconds"),
                "performance_elo": round(float(perf), 1),
                "theta": round(float(theta[ti]), 1) if ti is not None else None,
            }

        contests_out.append({
            "contest_id": cid, "contest_name": c["contest_name"],
            "year": c["year"], "official_solving_teams": n,
            "cutoff_ranks_official": cuts,
            "medal_bar": {t: round(bar[t], 1) for t in bar},
            "medal_bar_cf": {t: round(to_cf(bar[t]), 1) for t in bar},
            "cutoff_teams": cutoff_teams,
        })

        # per-band empirical solve rates over official teams (sanity badge):
        # the half-bands between consecutive badge anchors, weakest -> hardest
        edges = [0] + [anchor[t] for t, _ in reversed(TIER_BARS)]  # gold+ ... bronze
        bands = {"champion": officials[:TOP_COHORT]}
        for (tier, _), lo_e, hi_e in zip(reversed(TIER_BARS), edges, edges[1:]):
            bands[tier] = officials[lo_e:hi_e]
        bands["bronze"] = officials[anchor["bronze+"]:]  # whole below-cutoff field

        for p in ps:
            cid_, label, _pid, name = ds.problems[p]
            bp = float(b[p])
            badge = next((t for t in BADGE_ORDER[:-1] if bp <= bar[t]), "plat+")
            rates = {t: round(_solve_rate(members, label), 3) if members else None
                     for t, members in bands.items()}
            emp = next((t for t, _ in TIER_BARS
                        if rates[t] is not None and rates[t] >= 0.5), None)
            if emp is None:
                emp = "plat" if (rates["champion"] or 0) >= 0.5 else "plat+"
            agree += badge == emp
            total += 1
            problems_out.append({
                "contest_id": cid_, "problem_label": label, "problem_name": name,
                "difficulty": round(bp, 1), "difficulty_cf": round(to_cf(bp), 1),
                "badge": badge, "badge_empirical": emp,
                "band_solve_rates": rates,
            })

    os.makedirs(OUT, exist_ok=True)
    out_path = os.path.join(OUT, "medal_badges.json")
    with open(out_path, "w") as f:
        json.dump({"contests": contests_out, "problems": problems_out},
                  f, indent=2, ensure_ascii=False)

    _report(contests_out, problems_out, agree, total)
    print(f"\nwrote {len(problems_out)} problem badges over {len(contests_out)} "
          f"contests to {os.path.normpath(out_path)}")


def _report(contests_out, problems_out, agree, total):
    by_cid = {}
    for p in problems_out:
        by_cid.setdefault(p["contest_id"], []).append(p)
    letter = {"bronze": "b", "bronze+": "B", "silver": "s", "silver+": "S",
              "gold": "g", "gold+": "G", "plat": "p", "plat+": "P"}

    print("\n=== medal cutoff teams (official field from XCPCIO, ranked in full standings) ===")
    header = (f"{'cid':>5} {'year':>4} {'contest':<28} {'n_off':>5} "
              f"{'| gold cutoff':>40s} {'| silver cutoff':>40s} {'| bronze cutoff':>40s}")
    print(header)
    print(f"{'':5} {'':4} {'':28} {'':5}  "
          f"{'rank solv penalty perf':>40s}  "
          f"{'rank solv penalty perf':>40s}  "
          f"{'rank solv penalty perf':>40s}")
    print("-" * 155)
    for c in contests_out:
        ct = c["cutoff_teams"]
        parts = [f"{c['contest_id']:>5} {c['year']:>4} {c['contest_name'][:28]:<28} {c['official_solving_teams']:>5}"]
        for tier in ["gold", "silver", "bronze"]:
            t = ct[tier]
            pen = t.get("penalty_seconds")
            pen_str = f"{pen//60:4d}m" if isinstance(pen, (int, float)) and pen else "   ?"
            parts.append(f"r{t['rank_full_field']:>4d} {t['solved']:2d}s {pen_str} {t['performance_elo']:5.0f}")
        print("  ".join(parts))

    print(f"\n=== badge bars (raw scale; letters b B s S g G p P = "
          f"bronze..plat+, '+' grades in caps) ===")
    print(f"{'cid':>5} {'year':>4} {'contest':<28} {'n_off':>5} "
          f"{'b':>6} {'B+':>6} {'s':>6} {'S+':>6} {'g':>6} {'G+':>6} {'plat':>6} "
          f"{'G+CF':>6}  badges")
    for c in contests_out:
        ps = sorted(by_cid[c["contest_id"]], key=lambda p: p["difficulty"])
        badges = "".join(letter[p["badge"]] for p in ps)
        mb = c["medal_bar"]
        print(f"{c['contest_id']:>5} {c['year']:>4} {c['contest_name'][:28]:<28} "
              f"{c['official_solving_teams']:>5} "
              f"{mb['bronze']:>6.0f} {mb['bronze+']:>6.0f} "
              f"{mb['silver']:>6.0f} {mb['silver+']:>6.0f} "
              f"{mb['gold']:>6.0f} {mb['gold+']:>6.0f} {mb['plat']:>6.0f} "
              f"{c['medal_bar_cf']['gold+']:>6.0f}  "
              f"{badges:<14}")

    counts = {}
    for p in problems_out:
        counts[p["badge"]] = counts.get(p["badge"], 0) + 1
    print(f"\nbadge totals: {[(t, counts.get(t, 0)) for t in BADGE_ORDER]}")
    print(f"model vs empirical badge agreement: {agree}/{total} ({agree/total:.0%})")

    gold_cf = [c["medal_bar_cf"]["gold+"] for c in contests_out]
    print(f"\ngold-medal bar (the gold+ edge) across contests (CF points): "
          f"[{min(gold_cf):.0f}, {max(gold_cf):.0f}] median {statistics.median(gold_cf):.0f}")

    # Summarize cutoff performance
    gold_perf = [c["cutoff_teams"]["gold"]["performance_elo"] for c in contests_out]
    print(f"gold cutoff performance (full-field Elo): "
          f"[{min(gold_perf):.0f}, {max(gold_perf):.0f}] median {statistics.median(gold_perf):.0f}")

    # sanity: within each contest, badges must be monotone in difficulty
    tier_order = {t: i for i, t in enumerate(BADGE_ORDER)}
    for cid, ps in by_cid.items():
        ps = sorted(ps, key=lambda p: p["difficulty"])
        tiers = [tier_order[p["badge"]] for p in ps]
        assert tiers == sorted(tiers), f"non-monotone badges in {cid}"


if __name__ == "__main__":
    main()
