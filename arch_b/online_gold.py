"""Gold chances at Asia East regionals from online-qualifier results and slot rules.

Independent of the rating fit: the only inputs are the official online rankings,
the online registration rosters, the XCPCIO regional standings and the
hand-encoded slot rules in ``data/ec_online/`` (``scripts/build_ec_online_data.py``).

Model.  A team's online strength is ``x = -mean(log online rank)`` over the
rounds it entered.  Each regional's *rules line* is the strength of the G-th
best team the slot rules admit from the online ranking (every school's best
k teams, k = its rank-band slots plus the team-count clause, capped per
school).  Of the G = 10% x capacity golds, quota entrants (invitational, WF,
host, provincial, wildcard: the seats the online bands do not fill) are
expected to take a share set by ``rho``, their gold rate relative to
band-admitted teams, measured on earlier seasons (``quota_split``; ~0.44 and
stable 2023-2025); the line is the band team holding the last remaining gold.
Gold is a logistic regression

    logit P(gold) = c + b * x + d * line(site)

fit on linked official teams of mainland regionals, 2023-2025 (2022 was held
online under different rules).  ``d`` is free: the nominal field ignores which
sites a school's teams actually choose, so only part of the line carries over.
The 2026 forecast uses the quota-adjusted line with rho from 2023-2025.

Validation trains on earlier seasons and scores 2024 and 2025 with contest-
clustered bootstrap intervals, against: no site term, a shrunk per-site
history intercept, the rating fit's historical CF gold bar, and an oracle
line computed from the teams that actually attended.

Hong Kong / Macau are not modelled: their fields come from registration, not
rank bands, and their English team/school names do not link to the online
tables.

    python3 -m arch_b.online_gold            # backtest + 2026 forecast
    python3 -m arch_b.online_gold --school 蒙古国立大学

Writes ``output/online_gold.json`` and ``output/online_gold.md``.
"""

import argparse
import collections
import csv
import json
import math
import re
import unicodedata
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "ec_online"
OUT = ROOT / "output"
MODEL_SEASONS = ("2023", "2024", "2025")
TEST_SEASONS = ("2024", "2025")
EXCLUDED_SITES = {"hongkong", "macau"}
GOLD_FRACTION = 0.10
BOOTSTRAPS = 2000
FORECAST_RANKS = (10, 25, 50, 100, 200)


# ------------------------------------------------------------------ loading

SCHOOL_ALIAS = re.compile(r"[(（]山东省科学院[)）]")  # 齐鲁工业大学's official long form
TRADITIONAL = str.maketrans("學門灣臺國華醫東會", "学门湾台国华医东会")


def norm_school(s):
    """Keep campus qualifiers: 哈尔滨工业大学(威海) is its own school with its own
    online rank and slots (``大连理工大学(盘锦校区)`` == ``大连理工大学盘锦校区``)."""
    s = SCHOOL_ALIAS.sub("", unicodedata.normalize("NFKC", s or ""))
    return "".join(c for c in s.translate(TRADITIONAL).lower() if c.isalnum())


def norm_name(s):
    return "".join(c for c in unicodedata.normalize("NFKC", s or "").lower() if c.isalnum())


def _rows(name):
    with open(DATA / name, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load():
    return {n: _rows(n + ".csv") for n in ("online_teams", "online_schools", "online_rosters",
                                             "regional_teams")} | {
        "rules": {(str(r["season"]), r["site"]): r
                  for r in json.loads((DATA / "slot_rules.json").read_text())["rules"]}}


def online_strengths(online_teams):
    """{(season, school, team): {"ranks": [...], "school":..., "team":...}}.

    Unranked (zero-solve) teams get the midpoint of the unranked tail.
    """
    by_round = collections.defaultdict(list)
    for r in online_teams:
        by_round[(r["season"], r["round"])].append(r)
    teams = {}
    for rs in by_round.values():
        ranked = sum(1 for r in rs if r["rank"])
        for r in rs:
            rank = int(r["rank"]) if r["rank"] else (ranked + 1 + len(rs)) / 2
            key = (r["season"], norm_school(r["school"]), norm_name(r["team"]))
            t = teams.setdefault(key, {"ranks": [], "school": r["school"], "team": r["team"]})
            t["ranks"].append(rank)
    for t in teams.values():
        t["x"] = -float(np.mean(np.log(t["ranks"])))
    return teams


def link_regionals(data, strengths):
    """Official regional rows with the linked online team (by school + team
    name, else a roster sharing >= 2 members at the same school)."""
    roster = collections.defaultdict(set)
    for r in data["online_rosters"]:
        for m in r["members"].split("|"):
            if m:
                roster[(r["season"], norm_school(r["school"]), norm_name(m))].add(norm_name(r["team"]))
    out = []
    for r in data["regional_teams"]:
        if r["official"] != "1":
            continue
        season, school = r["season"], norm_school(r["school"])
        key, how = (season, school, norm_name(r["team"])), "name"
        if key not in strengths:
            votes = collections.Counter()
            for m in r["members"].split("|"):
                votes.update(sorted(roster.get((season, school, norm_name(m)), ())))  # deterministic ties
            best = votes.most_common(1)
            key, how = ((season, school, best[0][0]), "roster") if best and best[0][1] >= 2 else (None, "")
            if key not in strengths:
                key, how = None, ""
        out.append(dict(season=season, site=r["site"], team=r["team"], school=r["school"],
                        gold=int(r["medal"] == "gold"), link=how,
                        x=strengths[key]["x"] if key else None))
    return out


# -------------------------------------------------------------- rules line

def school_slots(season, rule, data):
    slots = collections.Counter()
    for r in data["online_schools"]:
        if r["season"] == season and r["table"] == "combined":
            for lo, hi, n in rule.get("online_bands") or []:
                if lo <= int(r["rank"]) <= hi:
                    slots[norm_school(r["school"])] += n
    clause = rule.get("team_count_clause")
    if clause:
        best = collections.Counter()
        for rnd in ("1", "2"):
            count = collections.Counter(
                norm_school(r["school"]) for r in data["online_teams"]
                if r["season"] == season and r["round"] == rnd and r["rank"]
                and int(r["rank"]) <= clause["top_n"])
            for s, c in count.items():
                best[s] = max(best[s], c)
        for s, c in best.items():
            if c >= clause["min_teams"]:
                slots[s] += clause["slots"]
    cap = rule.get("school_cap") or 4
    return {s: min(k, cap) for s, k in slots.items()}


def rules_line(season, site, data, strengths, rho=0.0):
    """Strength of the last gold among rule-admitted (band) teams.

    Quota entrants (invitational, WF, host, provincial, wildcard...) fill the
    share ``q = 1 - band slots / capacity`` of seats and win gold at ``rho``
    times the band teams' rate, so band teams keep
    ``G * (1 - q) / (1 - q + rho * q)`` of the G golds.  ``rho = 0`` hands
    every gold to band teams; ``rho = 1`` treats quota teams as equally strong.
    """
    rule = data["rules"].get((season, site))
    if not rule or not rule.get("online_bands"):
        return None
    by_school = collections.defaultdict(list)
    for (s, school, _), t in strengths.items():
        if s == season:
            by_school[school].append(t["x"])
    field, slots = [], school_slots(season, rule, data)
    for school, k in slots.items():
        field.extend(sorted(by_school.get(school, []), reverse=True)[:k])
    field.sort(reverse=True)
    capacity = rule["official_capacity"]
    q = max(0.0, 1 - sum(slots.values()) / capacity)
    band_golds = GOLD_FRACTION * capacity * (1 - q) / (1 - q + rho * q)
    return field[max(1, round(band_golds)) - 1]


def quota_split(data, strengths, seasons):
    """Per mainland regional: seats and golds of band vs quota teams.

    Each school's rule-based online slots go to its strongest-online teams at
    the site (unlinked teams last); its other teams, and every team of a school
    without band slots, count as quota entrants.  Returns the per-contest table
    and the pooled relative gold rate rho = quota rate / band rate.
    """
    regional = collections.defaultdict(list)
    for r in link_regionals(data, strengths):
        if r["season"] in seasons and r["site"] not in EXCLUDED_SITES:
            regional[(r["season"], r["site"])].append(r)
    table = []
    for (season, site), teams in sorted(regional.items()):
        rule = data["rules"].get((season, site))
        if not rule or not rule.get("online_bands"):
            continue
        slots = school_slots(season, rule, data)
        by_school = collections.defaultdict(list)
        for r in teams:
            by_school[norm_school(r["school"])].append(r)
        band = []
        for school, rs in by_school.items():
            rs.sort(key=lambda r: -(r["x"] if r["x"] is not None else -1e9))
            band.extend(rs[:slots.get(school, 0)])
        band_ids = {id(r) for r in band}
        quota = [r for r in teams if id(r) not in band_ids]
        table.append(dict(season=season, site=site, band_seats=len(band), quota_seats=len(quota),
                          band_golds=sum(r["gold"] for r in band),
                          quota_golds=sum(r["gold"] for r in quota)))
    tot = {k: sum(t[k] for t in table) for k in ("band_seats", "quota_seats", "band_golds", "quota_golds")}
    rho = (tot["quota_golds"] / tot["quota_seats"]) / (tot["band_golds"] / tot["band_seats"])
    for t in table:
        t["quota_gold_share"] = round(t["quota_golds"] / max(1, t["band_golds"] + t["quota_golds"]), 3)
        t["relative_gold_rate"] = round((t["quota_golds"] / max(1, t["quota_seats"]))
                                        / max(1e-9, t["band_golds"] / max(1, t["band_seats"])), 3)
    return table, rho


# ------------------------------------------------------------------ fitting

def logistic(X, y, l2=1e-3):
    X, y = np.asarray(X, float), np.asarray(y, float)
    w = np.zeros(X.shape[1])
    for _ in range(100):
        p = 1 / (1 + np.exp(-X @ w))
        step = np.linalg.solve((X.T * (p * (1 - p))) @ X + l2 * np.eye(len(w)),
                               X.T @ (p - y) + l2 * w)
        w -= step
        if np.abs(step).max() < 1e-10:
            break
    return w


def sigmoid(z):
    return 1 / (1 + np.exp(-np.asarray(z, float)))


def cf_gold_bars():
    """(season, site) -> the rating fit's CF gold bar (output/medal_badges.json)."""
    path = OUT / "medal_badges.json"
    boards = json.loads((ROOT / "data" / "xcpcio_ea_official.json").read_text())
    season_of = {"47th": "2022", "48th": "2023", "49th": "2024", "50th": "2025"}
    bars = {}
    for c in json.loads(path.read_text())["contests"]:
        link = boards.get(str(c["contest_id"]), {}).get("board_link", "")
        parts = link.strip("/").split("/")  # icpc/<season>/<site>
        if len(parts) == 3 and parts[1] in season_of:
            bars[(season_of[parts[1]], parts[2])] = c["medal_bar_cf"]["gold"]
    return bars


def model_rows(data, strengths):
    linked = [r for r in link_regionals(data, strengths)
              if r["season"] in MODEL_SEASONS and r["site"] not in EXCLUDED_SITES and r["link"]]
    contests = {(r["season"], r["site"]) for r in linked}
    lines = {k: rules_line(*k, data, strengths) for k in contests}
    # quota-adjusted lines, with rho estimated only from seasons before each test season
    quota_lines = {}
    for test in TEST_SEASONS:
        _, rho = quota_split(data, strengths, [s for s in MODEL_SEASONS if s < test])
        quota_lines[test] = {k: rules_line(*k, data, strengths, rho) for k in contests}
    by_contest = collections.defaultdict(list)
    for r in linked:
        r["line"] = lines[(r["season"], r["site"])]
        r["quota_line"] = {t: ql[(r["season"], r["site"])] for t, ql in quota_lines.items()}
        by_contest[(r["season"], r["site"])].append(r)
    for rs in by_contest.values():  # oracle: 10%-line of the linked teams that came
        xs = sorted((r["x"] for r in rs), reverse=True)
        for r in rs:
            r["oracle"] = xs[max(1, round(GOLD_FRACTION * len(xs))) - 1]
    return linked


def _site_history(train, key, shrink=1.0):
    """Per-site mean of ``key`` over earlier contests, shrunk toward the
    overall mean by ``shrink`` pseudo-contests (medal_predict's pooling)."""
    per = collections.defaultdict(dict)
    for r in train:
        if r.get(key) is not None:
            per[r["site"]][r["season"]] = r[key]
    values = [v for d in per.values() for v in d.values()]
    grand = float(np.mean(values)) if values else 0.0
    return {s: (sum(d.values()) + shrink * grand) / (len(d) + shrink) for s, d in per.items()}, grand


VARIANTS = ("online_only", "site_history", "cf_bar_history", "rules_line",
            "rules_line_quota_adjusted", "oracle_line")


def features(rows, variant, train, test=None):
    if variant == "online_only":
        return [[1, r["x"]] for r in rows]
    if variant == "rules_line":
        return [[1, r["x"], r["line"]] for r in rows]
    if variant == "rules_line_quota_adjusted":
        return [[1, r["x"], r["quota_line"][test]] for r in rows]
    if variant == "oracle_line":
        return [[1, r["x"], r["oracle"]] for r in rows]
    if variant == "site_history":  # shrunk historical oracle line of the same site
        hist, grand = _site_history(train, "oracle")
        return [[1, r["x"], hist.get(r["site"], grand)] for r in rows]
    if variant == "cf_bar_history":  # rating fit: shrunk historical CF gold bar / 1000
        hist, grand = _site_history(train, "cf_bar")
        return [[1, r["x"], hist.get(r["site"], grand) / 1000] for r in rows]
    raise ValueError(variant)


def backtest(rows, seed=0):
    bars = cf_gold_bars()
    for r in rows:
        r["cf_bar"] = bars.get((r["season"], r["site"]))
    rng = np.random.default_rng(seed)
    results = {}
    for test in TEST_SEASONS:
        train = [r for r in rows if r["season"] < test]
        held = [r for r in rows if r["season"] == test]
        y = np.array([r["gold"] for r in held])
        loss = {}
        for v in VARIANTS:
            w = logistic(features(train, v, train, test), [r["gold"] for r in train])
            p = np.clip(sigmoid(np.asarray(features(held, v, train, test), float) @ w), 1e-6, 1 - 1e-6)
            loss[v] = (-(y * np.log(p) + (1 - y) * np.log(1 - p)), (p - y) ** 2, w)
        sites = sorted({r["site"] for r in held})
        idx = {s: np.array([i for i, r in enumerate(held) if r["site"] == s]) for s in sites}
        draws = [np.concatenate([idx[s] for s in rng.choice(sites, len(sites))]) for _ in range(BOOTSTRAPS)]
        base = loss["online_only"][0]
        results[test] = {"teams": len(held), "sites": sites, "variants": {}}
        for v in VARIANTS:
            ll, br, w = loss[v]
            diff = [ll[i].mean() - base[i].mean() for i in draws]
            results[test]["variants"][v] = {
                "log_loss": round(float(ll.mean()), 5), "brier": round(float(br.mean()), 5),
                "delta_log_loss_vs_online_only": round(float(ll.mean() - base.mean()), 5),
                "delta_ci95": [round(float(q), 5) for q in np.percentile(diff, [2.5, 97.5])],
                "per_site_delta": {s: round(float(ll[idx[s]].mean() - base[idx[s]].mean()), 5) for s in sites},
                "coef": [round(float(c), 3) for c in w]}
    return results


def contest_difficulty(rows):
    """Per regional: online rank at which gold is a coin flip (shared slope,
    per-contest intercept), next to the rating fit's CF gold bar."""
    contests = sorted({(r["season"], r["site"]) for r in rows})
    col = {c: i for i, c in enumerate(contests)}
    X = []
    for r in rows:
        onehot = [0.0] * len(contests)
        onehot[col[(r["season"], r["site"])]] = 1.0
        X.append(onehot + [r["x"]])
    w = logistic(X, [r["gold"] for r in rows], l2=1e-4)
    slope, bars = w[-1], cf_gold_bars()
    out = [dict(season=s, site=site, online_rank_for_even_gold=round(math.exp(w[col[(s, site)]] / slope), 1),
                cf_gold_bar=bars.get((s, site)),
                linked_teams=sum(1 for r in rows if (r["season"], r["site"]) == (s, site)))
           for s, site in contests]
    have = [o for o in out if o["cf_gold_bar"] is not None]
    a, b = np.polyfit([math.log(o["online_rank_for_even_gold"]) for o in have],
                      [o["cf_gold_bar"] for o in have], 1)
    for o in have:  # CF bar the online evidence implies, and the disagreement
        o["cf_bar_implied_by_online"] = round(a * math.log(o["online_rank_for_even_gold"]) + b, 1)
        o["fit_minus_online"] = round(o["cf_gold_bar"] - o["cf_bar_implied_by_online"], 1)
    ranks = [np.argsort(np.argsort(v)) for v in
             ([o["online_rank_for_even_gold"] for o in have], [o["cf_gold_bar"] for o in have])]
    rho = float(np.corrcoef(*ranks)[0, 1])
    return {"slope": round(float(slope), 3), "spearman_rank_vs_bar": round(rho, 3),
            "cf_points_per_log_rank": round(float(a), 1), "contests": out}


# ----------------------------------------------------------------- forecast

def fit_final(rows, final_lines, n_boot=BOOTSTRAPS, seed=1):
    X = [[1, r["x"], final_lines[(r["season"], r["site"])]] for r in rows]
    w = logistic(X, [r["gold"] for r in rows])
    rng = np.random.default_rng(seed)
    contests = sorted({(r["season"], r["site"]) for r in rows})
    idx = {c: [i for i, r in enumerate(rows) if (r["season"], r["site"]) == c] for c in contests}
    boots = []
    for _ in range(n_boot):
        pick = np.concatenate([idx[contests[j]] for j in rng.integers(0, len(contests), len(contests))])
        boots.append(logistic([X[i] for i in pick], [rows[i]["gold"] for i in pick]))
    return w, np.array(boots)


def forecast_2026(data, strengths, w, boots, rho):
    sites = [r for r in data["rules"].values() if r["season"] == 2026]
    lines = {r["site"]: rules_line("2026", r["site"], data, strengths, rho) for r in sites
             if r.get("online_bands")}

    def prob(x, line):
        z = np.array([1, x, line])
        lo, hi = np.percentile(sigmoid(boots @ z), [10, 90])
        return {"p": round(float(sigmoid(z @ w)), 4), "p10": round(float(lo), 4), "p90": round(float(hi), 4)}

    ranking = []
    for r in sorted(sites, key=lambda r: r.get("date", "")):
        site = r["site"]
        entry = {"site": site, "date": r.get("date"), "source": r["source"]}
        if site in lines:
            entry["rules_line_online_rank"] = round(math.exp(-lines[site]), 1)
            entry["gold_by_online_rank"] = {k: prob(-math.log(k), lines[site]) for k in FORECAST_RANKS}
        else:
            entry["not_modelled"] = "registration-based field; no linked history"
        ranking.append(entry)
    modelled = [e for e in ranking if "rules_line_online_rank" in e]
    for i, e in enumerate(sorted(modelled, key=lambda e: -e["rules_line_online_rank"]), 1):
        e["easiest_rank"] = i
    return ranking, lines


def school_forecast(school_query, data, strengths, w, boots, lines):
    comb = {norm_school(r["school"]): int(r["rank"]) for r in data["online_schools"]
            if r["season"] == "2026" and r["table"] == "combined"}
    teams = [t for (s, school, _), t in strengths.items()
             if s == "2026" and norm_school(school_query) in school]
    out = []
    for t in sorted(teams, key=lambda t: -t["x"]):
        school = norm_school(t["school"])
        row = {"team": t["team"], "school": t["school"], "combined_school_rank": comb.get(school),
               "online_ranks": [int(r) if float(r).is_integer() else r for r in t["ranks"]],
               "gold": {}}
        for site, line in lines.items():
            z = np.array([1, t["x"], line])
            lo, hi = np.percentile(sigmoid(boots @ z), [10, 90])
            rule = data["rules"][("2026", site)]
            entitled = school_slots("2026", rule, data).get(school, 0)
            row["gold"][site] = {"p": round(float(sigmoid(z @ w)), 4), "p10": round(float(lo), 4),
                                 "p90": round(float(hi), 4), "rank_band_slots": entitled}
        out.append(row)
    return out


# ------------------------------------------------------------------- report

def markdown(result):
    L = ["# Gold chances from online results and slot rules", "",
         "Generated by `python3 -m arch_b.online_gold`. Probabilities are for an official "
         "team that attends; they are not medal counts. Hong Kong is not modelled.", "",
         "## Held-out validation (train on earlier seasons)", "",
         "| test | model | log loss | Δ vs online only (95% CI) | Brier |", "|---|---|---|---|---|"]
    for test, res in result["backtest"].items():
        for v, m in res["variants"].items():
            L.append(f"| {test} ({res['teams']} teams) | {v} | {m['log_loss']:.4f} | "
                     f"{m['delta_log_loss_vs_online_only']:+.4f} [{m['delta_ci95'][0]:+.4f}, "
                     f"{m['delta_ci95'][1]:+.4f}] | {m['brier']:.4f} |")
    cd = result["contest_difficulty"]
    L += ["", "## Contest difficulty: online evidence vs the rating fit", "",
          f"Spearman(online rank for an even gold chance, CF gold bar) = {cd['spearman_rank_vs_bar']} "
          "(negative = agreement: harder contests need a better online rank and have a higher bar).", "",
          "| season | site | online rank for 50% gold | CF gold bar | bar implied by online | fit − online |",
          "|---|---|---|---|---|---|"]
    for o in cd["contests"]:
        L.append(f"| {o['season']} | {o['site']} | {o['online_rank_for_even_gold']} | "
                 f"{o['cf_gold_bar'] or '—'} | {o.get('cf_bar_implied_by_online', '—')} | "
                 f"{o.get('fit_minus_online', '—')} |")
    q = result["quota"]
    L += ["", "## Quota entrants (not admitted by online rank bands)", "",
          f"Pooled gold rate of quota entrants relative to band teams: rho = {q['rho']}.", "",
          "| season | site | band seats | quota seats | band golds | quota golds | quota share of golds | relative rate |",
          "|---|---|---|---|---|---|---|---|"]
    for t in q["contests"]:
        L.append(f"| {t['season']} | {t['site']} | {t['band_seats']} | {t['quota_seats']} | {t['band_golds']} | "
                 f"{t['quota_golds']} | {t['quota_gold_share']:.0%} | {t['relative_gold_rate']} |")
    L += ["", "## 2026 regionals ranked for gold (easiest first)", "",
          f"Rules line = online rank of the band team holding the last gold after quota "
          f"entrants take their share (rho = {result['quota']['rho']}; higher = easier). "
          "Cells: gold chance for a team with that online rank in both rounds (10th–90th "
          "percentile over contest-bootstrap refits). The last column is the rating-fit "
          "chooser (`arch_b.medal_predict`) for comparison; it did not improve held-out gold "
          "prediction above.", "",
          "| # | site | date | rules line (online rank) | " +
          " | ".join(f"online #{k}" for k in FORECAST_RANKS) + " | rating-fit gold bar |",
          "|---|---|---|---|" + "---|" * (len(FORECAST_RANKS) + 1)]
    cf = result.get("rating_fit_2026_gold_cf", {})
    for e in sorted(result["forecast_2026"], key=lambda e: e.get("easiest_rank", 99)):
        if "easiest_rank" not in e:
            L.append(f"| — | {e['site']} | {e['date']} | not modelled | " + " | ".join("—" for _ in FORECAST_RANKS)
                     + f" | {cf.get(e['site'], '—')} |")
            continue
        cells = [f"{g['p']:.0%} ({g['p10']:.0%}–{g['p90']:.0%})" for g in e["gold_by_online_rank"].values()]
        L.append(f"| {e['easiest_rank']} | {e['site']} | {e['date']} | {e['rules_line_online_rank']} | "
                 + " | ".join(cells) + f" | {cf.get(e['site'], '—')} |")
    for school, teams in result.get("schools", {}).items():
        L += ["", f"## {school} teams, 2026", ""]
        if not teams:
            L.append("No 2026 online teams found.")
            continue
        sites = list(teams[0]["gold"])
        L += ["| team | online ranks | " + " | ".join(sites) + " |", "|---|---|" + "---|" * len(sites)]
        for t in teams:
            L.append(f"| {t['team']} | {t['online_ranks']} | " +
                     " | ".join(f"{t['gold'][s]['p']:.1%}" for s in sites) + " |")
        L.append(f"\nCombined school rank {teams[0]['combined_school_rank']}; rank-band slots per site: " +
                 ", ".join(f"{s} {teams[0]['gold'][s]['rank_band_slots']}" for s in sites) + ".")
    return "\n".join(L) + "\n"


def run(schools=()):
    data = load()
    strengths = online_strengths(data["online_teams"])
    rows = model_rows(data, strengths)
    result = {"model_rows": len(rows),
              "link_counts": dict(collections.Counter(f"{r['season']}/{r['link']}" for r in rows)),
              "backtest": backtest(rows), "contest_difficulty": contest_difficulty(rows)}
    table, rho = quota_split(data, strengths, MODEL_SEASONS)
    result["quota"] = {"rho": round(rho, 3), "contests": table}
    final_lines = {k: rules_line(*k, data, strengths, rho) for k in {(r["season"], r["site"]) for r in rows}}
    w, boots = fit_final(rows, final_lines)
    result["final_coef"] = [round(float(c), 3) for c in w]
    result["forecast_2026"], lines = forecast_2026(data, strengths, w, boots, rho)
    result["schools"] = {q: school_forecast(q, data, strengths, w, boots, lines) for q in schools}
    result["rating_fit_2026_gold_cf"] = rating_fit_2026()
    return result


def rating_fit_2026():
    """The existing rating-fit chooser's 2026 gold bars, keyed by site."""
    from arch_b.medal_predict import REGIONALS_BY_YEAR, Predictor
    return {norm_name(r["city"]): r["target_cf"]
            for r in Predictor().recommend(REGIONALS_BY_YEAR[2026])}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--school", action="append", default=["蒙古国立大学"],
                    help="also forecast every 2026 online team of this school (substring)")
    args = ap.parse_args()
    result = run(schools=dict.fromkeys(args.school))
    OUT.mkdir(exist_ok=True)
    (OUT / "online_gold.json").write_text(json.dumps(result, ensure_ascii=False, indent=1) + "\n")
    md = markdown(result)
    (OUT / "online_gold.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
