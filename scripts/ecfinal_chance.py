#!/usr/bin/env python3
"""Chance that a 2026 online team earns an EC-Final seat from each regional.

Mainland: a team qualifies at a site by finishing at or above that site's
qualifying rank K (``scripts/ecfinal_cutoff.py --project-2026``: ~75, 70-80)
unless already admitted or its school is capped (not binding for one team of
a school with few seats).  P(rank <= K) comes from a cumulative-logit model on
2023-2025 mainland teams linked to their online results
(``arch_b.online_gold.link_regionals``):

    logit P(rank <= K) = a + b x + c log K + d x log K + e h + f has_h

with x = -mean log online rank and h = logit of the members' best official
rank / field at a mainland regional of the previous season (has_h = 0 and
h = 0 without one).  Absolute rank, not percentile of the field: bigger
fields add weak teams at the bottom, and the 2025 backtest (Shenyang and
Xi'an grew to ~400) is badly biased on percentile (expected 62-64 vs actual
86-87 teams above the cutoff) and close on rank.  Sites differ (per-contest
offsets, SD ``sigma_site``), but no pre-registration site feature predicted
the offsets out of season, so every mainland site gets the same number and
the site spread only widens its interval.
Hong Kong: up to 10 places to Hong Kong medal teams, skipping teams already
registered for the EC-Final and capped schools; the depth D of the 10th place
is replayed on 2024/2025 Hong Kong boards, and P(rank <= D) uses the
online-only model fitted on Hong Kong linked teams.
Two regionals: a team-season effect u ~ N(0, tau^2) shared by a team's sites,
fitted on teams that played two sites, gives P(at least one seat).

    python scripts/ecfinal_chance.py [--team NUM-R^3] [--school 蒙古国立大学]
"""
import collections
import math
import os
import re
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))
from arch_b import hk_link as hk  # noqa: E402
from arch_b import online_gold as og  # noqa: E402
import ecfinal_cutoff as ec  # noqa: E402

THRESHOLDS = (10, 20, 30, 45, 60, 75, 90, 110, 130, 160)
K_2026 = {70: 0.25, 75: 0.5, 80: 0.25}  # projected qualifying rank (ecfinal_cutoff --project-2026)
REAL_K = {"2023": 87, "2024": 86, "2025": 91}  # real 6-site qualifying rank (ecfinal_cutoff)
HK_PLACES = 10
BOOTSTRAPS = 300
NO_HISTORY = (0.0, 0.0)
GH_Z, GH_W = np.polynomial.hermite_e.hermegauss(40)
GH_W = GH_W / GH_W.sum()
EN2CN = hk.school_map()


def official_ranks():
    out, size = {}, collections.Counter()
    for r in ec.ROWS:
        if r["official"] == "1" and r["official_rank"]:
            out[(r["season"], r["site"], r["school"], r["team"])] = (int(r["official_rank"]), ec.members(r))
            size[(r["season"], r["site"])] += 1
    return out, size


def school_key(s):
    """English board names map to the ranking's Chinese name (NUM appears both ways)."""
    en = hk.norm_school_en(s)
    return EN2CN[en] if en and en in EN2CN else og.norm_school(s)


def person_key(m):
    """Latin names as sorted lower-case words (boards swap the name order)."""
    latin = sorted(re.findall(r"[a-z]+", m.lower()))
    return " ".join(latin) if latin else og.norm_name(m)


def member_best(size):
    """(season, school, person) -> best official rank / field at a mainland regional."""
    best = {}
    for r in ec.ROWS:
        if r["official"] == "1" and r["official_rank"] and r["site"] not in ec.NON_MAINLAND:
            pct = int(r["official_rank"]) / size[(r["season"], r["site"])]
            for m in ec.members(r):
                k = (r["season"], school_key(r["school"]), person_key(m))
                best[k] = min(best.get(k, 1.0), pct)
    return best


def history(season, school, members, best):
    prev = str(int(season) - 1)
    pcts = [best[k] for m in members if (k := (prev, school_key(school), person_key(m))) in best]
    if not pcts:
        return NO_HISTORY
    p = min(max(min(pcts), 0.005), 0.995)
    return (math.log(p / (1 - p)), 1.0)


def design(x, k, h=NO_HISTORY):
    lk = math.log(k)
    return np.array([1.0, x, lk, x * lk, *h])


def fit(rows, l2=1e-3, use_h=True):
    X, y = [], []
    for r in rows:
        for k in THRESHOLDS:
            X.append(design(r["x"], k, r["h"] if use_h else NO_HISTORY))
            y.append(int(r["rank"] <= k))
    return og.logistic(X, y, l2=l2)


def fit_boot(rows, rng, n=BOOTSTRAPS, l2=1e-3):
    groups = collections.defaultdict(list)
    for r in rows:
        groups[(r["season"], r["site"])].append(r)
    keys = sorted(groups)
    return np.array([fit([r for j in rng.integers(0, len(keys), len(keys)) for r in groups[keys[j]]], l2)
                     for _ in range(n)])


def prob(w, x, rank, h=NO_HISTORY):
    return float(og.sigmoid(design(x, rank, h) @ w))


def logit(p):
    return math.log(p / (1 - p))


def p_any(ps, tau):
    """P(at least one success) for one team whose sites share u ~ N(0, tau^2);
    conditional log-odds are the marginal ones scaled to keep the marginals."""
    s = math.sqrt(1 + math.pi * tau ** 2 / 8)
    miss = np.ones_like(GH_Z)
    for p in ps:
        miss *= 1 - og.sigmoid(logit(p) * s + tau * GH_Z)
    return float(1 - GH_W @ miss)


def fit_tau(pairs):
    """Maximum-likelihood tau from [(p1, y1, p2, y2)] of teams that played two sites."""
    def loglik(tau):
        s = math.sqrt(1 + math.pi * tau ** 2 / 8)
        total = 0.0
        for p1, y1, p2, y2 in pairs:
            q1 = og.sigmoid(logit(p1) * s + tau * GH_Z)
            q2 = og.sigmoid(logit(p2) * s + tau * GH_Z)
            total += math.log(GH_W @ ((q1 if y1 else 1 - q1) * (q2 if y2 else 1 - q2)))
        return total
    return max(np.arange(0.0, 3.01, 0.05), key=loglik)


def site_spread(rows, w, ks=(60, 75, 90)):
    """Per-contest intercept shifts (slopes fixed) and the between-site SD net of noise."""
    offsets, variances = {}, []
    for key in sorted({(r["season"], r["site"]) for r in rows}):
        sub = [r for r in rows if (r["season"], r["site"]) == key]
        eta = np.array([design(r["x"], k, r["h"]) @ w for r in sub for k in ks])
        y = np.array([r["rank"] <= k for r in sub for k in ks])
        d = 0.0
        for _ in range(30):
            z = og.sigmoid(eta + d)
            info = float(np.sum(z * (1 - z)))
            d += float(np.sum(y - z)) / info
        offsets[key] = d
        variances.append(1 / info)
    return offsets, math.sqrt(max(0.0, np.var(list(offsets.values())) - np.mean(variances)))


def heldout(rows, rng):
    """Held-out log loss at the season's real qualifying rank: online only vs + members' history."""
    for test in ("2024", "2025"):
        train = [r for r in rows if r["season"] < test]
        tests = [r for r in rows if r["season"] == test]
        w0, w1 = fit(train, use_h=False), fit(train)
        k = REAL_K[test]
        loss = {}
        for name, w, use_h in (("online", w0, False), ("history", w1, True)):
            p = np.array([prob(w, r["x"], k, r["h"] if use_h else NO_HISTORY) for r in tests])
            y = np.array([r["rank"] <= k for r in tests])
            loss[name] = -np.where(y, np.log(p), np.log(1 - p))
        diff = loss["history"] - loss["online"]
        keys = sorted({r["site"] for r in tests})
        idx = [np.array([i for i, r in enumerate(tests) if r["site"] == s]) for s in keys]
        boots = [diff[np.concatenate([idx[j] for j in rng.integers(0, len(keys), len(keys))])].mean()
                 for _ in range(2000)]
        lo, hi = np.percentile(boots, [2.5, 97.5])
        print(f"  {test} (train earlier seasons, {len(tests)} teams, "
              f"{sum(r['h'][1] for r in tests):.0f} with member history): online only {loss['online'].mean():.4f}, "
              f"+ history {loss['history'].mean():.4f}, diff {diff.mean():+.4f} [{lo:+.4f}, {hi:+.4f}]")


def hk_depth(season, mainland_rows, hk_rows):
    """Hong Kong rank of the HK_PLACES-th eligible medal team under the 2026 rule.

    Registered = the replayed mainland qualifiers (online key) plus each
    school's published / simulated seat count as its x."""
    _, _, taken = ec.admits_by_depth(season)
    taken = taken[:239 if season == "2025" else 240]
    keyed = {(r["school"], r["team"]): r["online_key"] for r in mainland_rows if r["season"] == season}
    registered = {keyed.get((t["school"], t["team"])) for t in taken} - {None}
    seats = collections.Counter(og.norm_school(t["school"]) for t in taken)
    got, depth = collections.Counter(), None
    for r in sorted((r for r in hk_rows if r["season"] == season), key=lambda r: int(r["official_rank"])):
        if not r["medal"]:
            break
        key = (season, r["online_school"], r["online_team"]) if r["online_school"] else None
        school = r["online_school"] or og.norm_school(r["school"])
        if key in registered or seats[school] + got[school] >= 3:
            continue
        got[school] += 1
        depth = int(r["official_rank"])
        if sum(got.values()) == HK_PLACES:
            break
    return depth


def main():
    team_q = sys.argv[sys.argv.index("--team") + 1] if "--team" in sys.argv else "NUM-R^3"
    school_q = sys.argv[sys.argv.index("--school") + 1] if "--school" in sys.argv else "蒙古国立大学"
    data = og.load()
    strengths = og.online_strengths(data["online_teams"])
    ranks, size = official_ranks()
    best = member_best(size)
    linked = og.link_regionals(data, strengths)
    rows = []
    for r in linked:
        k = (r["season"], r["site"], r["school"], r["team"])
        if r["season"] in og.MODEL_SEASONS and r["site"] not in og.EXCLUDED_SITES and r["link"] and k in ranks:
            rank, members = ranks[k]
            rows.append(dict(r, rank=rank, h=history(r["season"], r["school"], members, best)))
    hk_all = [r for r in hk.link_hk(data, strengths) if r["site"] == "hongkong"]
    hk_rows = [dict(r, rank=int(r["official_rank"]), h=NO_HISTORY) for r in hk_all if r["x"] is not None]
    rng = np.random.default_rng(1)

    print("Held-out log loss of P(rank <= real qualifying rank), contest-bootstrap 95% CI:")
    heldout(rows, rng)
    w_bt = fit([r for r in rows if r["season"] != "2025"])
    print("Backtest 2025 (train 2023-2024): linked teams at or above the site's qualifying rank")
    walk = {"wuhan": 91, "shenyang": 91, "xian": 90, "nanjing": 90, "chengdu": 90, "shanghai": 90}
    for site, k in walk.items():
        test = [r for r in rows if r["season"] == "2025" and r["site"] == site]
        exp = sum(prob(w_bt, r["x"], k, r["h"]) for r in test)
        act = sum(r["rank"] <= k for r in test)
        print(f"  {site}: expected {exp:.1f}, actual {act} (of {len(test)} linked)")
    for lo, hi in ((1, 150), (151, 400), (401, 800), (801, 10 ** 6)):
        band = [r for r in rows if r["season"] == "2025" and lo <= math.exp(-r["x"]) <= hi]
        exp = np.mean([prob(w_bt, r["x"], walk[r["site"]], r["h"]) for r in band])
        act = np.mean([r["rank"] <= walk[r["site"]] for r in band])
        print(f"  online #{lo}-{hi if hi < 10 ** 6 else '+'}: predicted {exp:.1%}, actual {act:.1%} ({len(band)} teams)")

    w, boots = fit(rows), fit_boot(rows, rng)
    w_hk, boots_hk = fit(hk_rows, l2=1e-2, use_h=False), fit_boot(hk_rows, rng, l2=1e-2)
    depths = {s: hk_depth(s, linked, hk_all) for s in ("2024", "2025")}
    print(f"Hong Kong: 10th eligible medal team at rank {depths} (2026 rule replayed)")
    offsets, sigma_site = site_spread(rows, w)
    print(f"Site offsets (log-odds, + = easier for a linked team), between-site SD net of noise {sigma_site:.2f}:")
    for site in sorted({s for _, s in offsets}):
        print(f"  {site}: " + ", ".join(f"{season} {d:+.2f}" for (season, s), d in sorted(offsets.items()) if s == site))

    by_team = collections.defaultdict(list)
    for r in rows:
        by_team[r["online_key"]].append(r)
    pairs = [(prob(w, a["x"], REAL_K[a["season"]], a["h"]), a["rank"] <= REAL_K[a["season"]],
              prob(w, b["x"], REAL_K[b["season"]], b["h"]), b["rank"] <= REAL_K[b["season"]])
             for g in by_team.values() if len(g) == 2 for a, b in [g]]
    tau = fit_tau(pairs)
    hk_pairs = [(prob(w, m["x"], REAL_K[m["season"]], m["h"]), m["rank"] <= REAL_K[m["season"]],
                 prob(w_hk, r["x"], depths[r["season"]]), r["rank"] <= depths[r["season"]])
                for r in hk_rows for m in by_team.get((r["season"], r["online_school"], r["online_team"]), [])]
    tau_hk = fit_tau(hk_pairs)
    print(f"Team-season effect: tau {tau:.2f} from {len(pairs)} teams at two mainland sites; "
          f"{tau_hk:.2f} from {len(hk_pairs)} Hong Kong + mainland pairs")

    roster = collections.defaultdict(set)
    for r in data["online_rosters"]:
        if r["season"] == "2026":
            roster[(og.norm_school(r["school"]), og.norm_name(r["team"]))].update(m for m in r["members"].split("|") if m)
    teams = [(k, t) for k, t in strengths.items() if k[0] == "2026" and school_q in t["school"]]
    for (_, school, team), t in sorted(teams, key=lambda kv: -kv[1]["x"]):
        if team_q not in ("*", t["team"]):
            continue
        x, h = t["x"], history("2026", t["school"], roster[(school, team)], best)
        hist = f"members' best 2025 mainland rank/field {1 / (1 + math.exp(-h[0])):.2f}" if h[1] else "no 2025 mainland history"
        print(f"\n{t['team']} (online ranks {t['ranks']}, geometric mean #{math.exp(-x):.0f}; {hist}); "
              f"P(EC-Final seat | plays), 10-90%:")
        p_m = sum(wk * prob(w, x, k, h) for k, wk in K_2026.items())
        draws = np.array([sum(wk * prob(b, x, k, h) for k, wk in K_2026.items()) for b in boots])
        site_draws = og.sigmoid(np.log(draws / (1 - draws)) + sigma_site * rng.standard_normal(len(draws)))
        print(f"  any one mainland site: {p_m:5.1%}  (model {np.percentile(draws, 10):.1%}-{np.percentile(draws, 90):.1%}; "
              f"with site-to-site spread {np.percentile(site_draws, 10):.1%}-{np.percentile(site_draws, 90):.1%}); "
              f"K=70 {prob(w, x, 70, h):.1%}, K=80 {prob(w, x, 80, h):.1%}")
        ds = [d for d in depths.values() if d]
        p_h = float(np.mean([prob(w_hk, x, d) for d in ds]))
        draws_hk = [np.mean([prob(b, x, d) for d in ds]) for b in boots_hk]
        print(f"  Hong Kong:             {p_h:5.1%}  (model {np.percentile(draws_hk, 10):.1%}-"
              f"{np.percentile(draws_hk, 90):.1%}); needs Hong Kong rank <= {ds}")
        print(f"  two mainland sites:    {p_any([p_m, p_m], tau):5.1%}  (independent sites would give "
              f"{1 - (1 - p_m) ** 2:.1%})")
        print(f"  mainland + Hong Kong:  {p_any([p_m, p_h], tau_hk):5.1%}  (independent {1 - (1 - p_m) * (1 - p_h):.1%})")
        print(f"  two mainland + Hong Kong (only if Hong Kong is outside the two-regional limit): "
              f"{p_any([p_m, p_m, p_h], tau):5.1%}")


if __name__ == "__main__":
    main()
