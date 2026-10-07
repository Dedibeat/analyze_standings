"""Gold chances at the Hong Kong regional from online strength and field history.

Hong Kong admits teams by registration (one per non-local school first, then
first-come extra teams; 2024-2026 notices), so its field cannot be derived from
rank bands as ``arch_b.online_gold`` does for mainland sites.  This module
uses the Hong Kong / Macau teams linked to online results by
``arch_b.hk_link`` (2024 and 2025; the 2022 and 2023 boards list no members)
and measures:

* the field each year: schools, their combined online rank, returning schools,
  the coin-flip online rank (shared slope with the mainland contests);
* whether the field can be predicted: a school attendance model (previous
  Hong Kong attendance + online school rank) and a simulated gold line, each
  tested on the other year against "same field as last year";
* gold models tested across the two years: the mainland models applied to
  Hong Kong, a Hong Kong-only ``logit P = c + b x``, and the same plus "won a
  mainland gold earlier in the same season" (members' previous-season medals
  were tested too and did not help).

The 2026 forecast is the Hong Kong-only model fit on 2024 + 2025, with a band
for a harder or easier field (one standard deviation of the year-to-year change
in the mainland sites' coin-flip ranks) and the update once mainland results
are in (Hong Kong 2026 is on 2027-01-09, after every mainland site).

    python3 -m arch_b.hk_gold [--school 蒙古国立大学]

Writes ``output/hk_gold.json`` and ``output/hk_gold.md``.
"""

import argparse
import collections
import json
import math
import sys

import numpy as np

from arch_b import hk_link as hk
from arch_b import online_gold as og

sys.path.insert(0, str(og.ROOT / "scripts"))
import build_tabfm_gold_data as tb  # noqa: E402  contest dates and member/earlier-result history

CONTESTS = (("2022", "hongkong"), ("2023", "macau"), ("2024", "hongkong"), ("2025", "hongkong"))
SEASONS = ("2024", "2025")  # seasons whose boards carry members
FORECAST_RANKS = (10, 25, 50, 75, 100, 150, 200, 300, 500)
BANDS = (20, 60, 150, 10 ** 9)  # school combined-rank bands for the team a school sends
BOOTSTRAPS = 2000


def is_local(school):
    return bool(hk.LOCAL.search(school)) and not hk.NOT_LOCAL.search(school)


def context():
    data = og.load()
    strengths = og.online_strengths(data["online_teams"])
    rows = hk.link_hk(data, strengths)
    dates = tb.contest_dates()
    by_school = collections.defaultdict(list)
    for e in tb.regional_entries(data, dates):
        by_school[(e["season"], e["school"])].append(e)
    members = collections.defaultdict(set)
    for r in data["online_rosters"]:
        members[(r["season"], og.norm_school(r["school"]), og.norm_name(r["team"]))] |= {
            og.norm_name(m) for m in r["members"].split("|") if m}
    for r in rows:  # Chinese members of the linked online team -> previous-performance features
        if r["x"] is not None:
            team = dict(school=r["online_school"], team=r["online_team"],
                        members=members[(r["season"], r["online_school"], r["online_team"])])
            h = tb.history(team, by_school, r["season"], dates[(r["season"], r["site"])])
            r["earlier_gold"] = int(h["earlier_best_medal"] == 3)
            r["members_prev_gold"] = int((h["members_prev_golds"] or 0) > 0)
    school_rank = {(r["season"], og.norm_school(r["school"])): int(r["rank"])
                   for r in data["online_schools"] if r["table"] == "combined"}
    attend = collections.defaultdict(set)
    en2cn = hk.school_map()
    for r in rows:
        if not is_local(r["school"]):
            attend[r["season"]].add(en2cn.get(hk.norm_school_en(r["school"])) or r["online_school"]
                                    or "?" + r["school"])
    return dict(data=data, strengths=strengths, rows=rows, school_rank=school_rank, attend=attend)


def oracle(xs):
    xs = sorted(xs, reverse=True)
    return xs[max(1, round(og.GOLD_FRACTION * len(xs))) - 1]


def log_loss(p, y):
    p, y = np.clip(np.asarray(p, float), 1e-6, 1 - 1e-6), np.asarray(y, float)
    return float(-(y * np.log(p) + (1 - y) * np.log(1 - p)).mean())


# ------------------------------------------------------------------ field

def field_summary(ctx, difficulty):
    out = []
    for season, site in CONTESTS:
        rs = [r for r in ctx["rows"] if (r["season"], r["site"]) == (season, site)]
        schools = ctx["attend"][season]
        ranks = [ctx["school_rank"].get((season, s)) for s in schools]
        prev = ctx["attend"].get(str(int(season) - 1), set())
        linked = [r for r in rs if r["x"] is not None]
        per_school = collections.Counter(
            hk.school_map().get(hk.norm_school_en(r["school"])) or r["school"] for r in rs if not is_local(r["school"]))
        out.append(dict(
            season=season, site=site, official=len(rs), golds=sum(r["gold"] for r in rs),
            local=sum(is_local(r["school"]) for r in rs), nonlocal_schools=len(schools),
            multi_team_schools=sum(c > 1 for c in per_school.values()),
            top50_schools=sum(1 for k in ranks if k and k <= 50), top100_schools=sum(1 for k in ranks if k and k <= 100),
            returning_schools=len(schools & prev) if prev else None,
            linked=len(linked), linked_golds=sum(r["gold"] for r in linked),
            gold_line_online_rank=round(math.exp(-oracle([r["x"] for r in linked])), 1) if len(linked) > 50 else None,
            coin_flip_online_rank=difficulty.get((season, site)),
            linked_with_earlier_gold=sum(r.get("earlier_gold", 0) for r in linked) if season in SEASONS else None,
            golds_with_earlier_gold=sum(r.get("earlier_gold", 0) for r in linked if r["gold"]) if season in SEASONS else None))
    return out


def attendance_table(ctx, season):
    """Schools with a combined online rank: [1, attended last year, two years ago, log rank], attended."""
    a = ctx["attend"]
    schools = sorted(s for (t, s) in ctx["school_rank"] if t == season)
    X = np.array([[1, s in a[str(int(season) - 1)], s in a[str(int(season) - 2)],
                   math.log(ctx["school_rank"][(season, s)])] for s in schools], float)
    return schools, X, np.array([s in a[season] for s in schools], float)


def auc(p, y):
    order = np.argsort(p)
    r = np.empty(len(p))
    r[order] = np.arange(1, len(p) + 1)
    n1 = y.sum()
    return float((r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * (len(y) - n1)))


def field_backtest(ctx, n_sims=1000, seed=0):
    """Train on one season, predict the other: attendance (AUC, schools, top-50
    schools) and the simulated gold line vs 'same line as the training season'.

    Simulation: each school attends with its model probability and sends the
    team at an online position (1 = its best) drawn from the training season's
    linked teams of schools in the same rank band; the line is the 10% team of
    the linked share (78%) of the simulated field."""
    by_school = collections.defaultdict(list)
    for (s, school, _), t in ctx["strengths"].items():
        by_school[(s, school)].append(t["x"])
    for v in by_school.values():
        v.sort(reverse=True)
    band = lambda k: next(i for i, b in enumerate(BANDS) if k <= b)  # noqa: E731
    lines = {s: oracle([r["x"] for r in ctx["rows"] if r["season"] == s and r["x"] is not None]) for s in SEASONS}
    rng = np.random.default_rng(seed)
    out = []
    for train, test in (("2024", "2025"), ("2025", "2024")):
        _, X, y = attendance_table(ctx, train)
        w = og.logistic(X, y)
        schools, Xt, yt = attendance_table(ctx, test)
        p = og.sigmoid(Xt @ w)
        top = np.array([ctx["school_rank"][(test, s)] <= 50 for s in schools])
        pos = collections.defaultdict(list)
        for r in ctx["rows"]:
            k = ctx["school_rank"].get((train, r["online_school"]))
            if r["season"] == train and r["x"] is not None and k:
                pos[band(k)].append(sum(v > r["x"] + 1e-3 for v in by_school[(train, r["online_school"])]))
        sims = []
        for _ in range(n_sims):
            xs = sorted((by_school[(test, s)][min(rng.choice(pos[band(ctx["school_rank"][(test, s)])]),
                                                  len(by_school[(test, s)]) - 1)]
                         for s in np.array(schools)[rng.random(len(schools)) < p] if by_school[(test, s)]),
                        reverse=True)
            sims.append(xs[max(1, round(og.GOLD_FRACTION * 0.78 * len(xs))) - 1])
        sim = float(np.median(sims))
        out.append(dict(train=train, test=test, attendance_auc=round(auc(p, yt), 3),
                        schools_expected=round(float(p.sum()), 1), schools_actual=int(yt.sum()),
                        top50_expected=round(float(p[top].sum()), 1), top50_actual=int(yt[top].sum()),
                        coef=[round(float(c), 2) for c in w],
                        line_actual=round(math.exp(-lines[test]), 1),
                        line_simulated=round(math.exp(-sim), 1),
                        line_simulated_80=[round(math.exp(-float(np.percentile(sims, q))), 1) for q in (90, 10)],
                        line_same_as_train=round(math.exp(-lines[train]), 1),
                        abs_log_error_simulated=round(abs(sim - lines[test]), 3),
                        abs_log_error_same_as_train=round(abs(lines[train] - lines[test]), 3)))
    return out


# ------------------------------------------------------------------ gold

VARIANTS = {
    "hk_online_only": lambda r: [1, r["x"]],
    "hk_earlier_mainland_gold": lambda r: [1, r["x"], r["earlier_gold"]],
    "hk_members_prev_gold": lambda r: [1, r["x"], r["members_prev_gold"]],
}


def gold_backtest(ctx, mainland):
    linked = {s: [r for r in ctx["rows"] if r["season"] == s and r["x"] is not None] for s in SEASONS}
    w_main = og.logistic([[1, r["x"]] for r in mainland], [r["gold"] for r in mainland])
    w_oracle = og.logistic([[1, r["x"], r["oracle"]] for r in mainland], [r["gold"] for r in mainland])
    out = {}
    for test in SEASONS:
        te, tr = linked[test], [r for s in SEASONS if s != test for r in linked[s]]
        y = [r["gold"] for r in te]
        preds = {"mainland_online_only": og.sigmoid(np.array([[1, r["x"]] for r in te]) @ w_main),
                 "mainland_oracle_line": og.sigmoid(
                     np.array([[1, r["x"], oracle([q["x"] for q in te])] for r in te]) @ w_oracle)}
        for name, f in VARIANTS.items():
            w = og.logistic([f(r) for r in tr], [r["gold"] for r in tr], l2=1e-2)
            preds[name] = og.sigmoid(np.array([f(r) for r in te], float) @ w)
        out[test] = {"teams": len(te), "golds": sum(y), "variants": {
            k: {"log_loss": round(log_loss(p, y), 4), "expected_golds": round(float(p.sum()), 1)}
            for k, p in preds.items()}}
    return out


def year_shift_sd(difficulty):
    """SD of the change in log coin-flip rank between consecutive seasons of the
    same mainland site."""
    by_site = collections.defaultdict(dict)
    for (season, site), rank in difficulty.items():
        if site not in hk.SITES:
            by_site[site][season] = math.log(rank)
    diffs = [d[b] - d[a] for d in by_site.values() for a, b in zip(sorted(d), sorted(d)[1:])
             if int(b) == int(a) + 1]
    return float(np.std(diffs, ddof=1)), len(diffs)


def forecast(ctx, shift, schools, seed=1):
    rows = [r for r in ctx["rows"] if r["season"] in SEASONS and r["x"] is not None]
    f0, f1 = VARIANTS["hk_online_only"], VARIANTS["hk_earlier_mainland_gold"]
    w0 = og.logistic([f0(r) for r in rows], [r["gold"] for r in rows], l2=1e-2)
    w1 = og.logistic([f1(r) for r in rows], [r["gold"] for r in rows], l2=1e-2)
    rng = np.random.default_rng(seed)
    boots = []
    for _ in range(BOOTSTRAPS):
        pick = rng.integers(0, len(rows), len(rows))
        boots.append(og.logistic([f0(rows[i]) for i in pick], [rows[i]["gold"] for i in pick], l2=1e-2))
    boots = np.array(boots)

    def entry(x):
        ps = og.sigmoid(boots @ np.array([1, x]))
        return dict(p=round(float(og.sigmoid(w0 @ [1, x])), 3),
                    ci90=[round(float(q), 3) for q in np.percentile(ps, [5, 95])],
                    p_harder_field=round(float(og.sigmoid(w0 @ [1, x] - w0[1] * shift)), 3),
                    p_easier_field=round(float(og.sigmoid(w0 @ [1, x] + w0[1] * shift)), 3),
                    p_after_mainland_gold=round(float(og.sigmoid(w1 @ [1, x, 1])), 3),
                    p_without_mainland_gold=round(float(og.sigmoid(w1 @ [1, x, 0])), 3))
    grid = [dict(online_rank=k, **entry(-math.log(k))) for k in FORECAST_RANKS]
    teams = {}
    for q in schools:
        teams[q] = [dict(team=t["team"], school=t["school"], online_ranks=t["ranks"],
                         mean_online_rank=round(math.exp(-t["x"]), 1), **entry(t["x"]))
                    for (s, _, _), t in sorted(ctx["strengths"].items(), key=lambda kv: -kv[1]["x"])
                    if s == "2026" and q in t["school"]]
    return dict(coef_online_only=[round(float(c), 3) for c in w0],
                coef_earlier_gold=[round(float(c), 3) for c in w1],
                coin_flip_online_rank=round(math.exp(w0[0] / w0[1]), 1), grid=grid, schools=teams)


def run(schools=("蒙古国立大学",)):
    ctx = context()
    mainland = og.model_rows(ctx["data"], ctx["strengths"])
    hk_rows = [dict(r, site="hongkong") for r in ctx["rows"] if r["season"] in SEASONS and r["x"] is not None]
    cd = og.contest_difficulty(mainland + hk_rows)
    difficulty = {(c["season"], c["site"]): c["online_rank_for_even_gold"] for c in cd["contests"]}
    shift, n_pairs = year_shift_sd(difficulty)
    return {"field": field_summary(ctx, difficulty),
            "mainland_coin_flip_online_rank": {f"{s} {site}": v for (s, site), v in sorted(difficulty.items())
                                               if site not in hk.SITES},
            "field_backtest": field_backtest(ctx),
            "gold_backtest": gold_backtest(ctx, mainland),
            "year_shift_sd_log_rank": round(shift, 3), "year_shift_pairs": n_pairs,
            "forecast_2026": forecast(ctx, shift, schools)}


def markdown(res):
    L = ["# Hong Kong gold chances from online strength and field history", "",
         "`arch_b.hk_gold`. Linked = tied to an online-qualifier result by `arch_b.hk_link` (members only exist",
         "on the 2024-2025 boards). Online rank = exp(mean log rank) over the rounds entered.", "",
         "## Field", "",
         "| contest | official | golds | local | non-local schools | multi-team | top-50 / top-100 schools | "
         "returning schools | linked (golds) | gold line (online rank) | coin flip (online rank) | "
         "linked golds with an earlier mainland gold |", "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for f in res["field"]:
        eg = f"{f['golds_with_earlier_gold']} / {f['linked_golds']} (teams: {f['linked_with_earlier_gold']})" \
            if f["golds_with_earlier_gold"] is not None else "-"
        L.append(f"| {f['season']} {f['site']} | {f['official']} | {f['golds']} | {f['local']} | {f['nonlocal_schools']} | "
                 f"{f['multi_team_schools']} | {f['top50_schools']} / {f['top100_schools']} | "
                 f"{f['returning_schools'] if f['returning_schools'] is not None else '-'} | "
                 f"{f['linked']} ({f['linked_golds']}) | {f['gold_line_online_rank'] or '-'} | "
                 f"{f['coin_flip_online_rank'] or '-'} | {eg} |")
    mc = res["mainland_coin_flip_online_rank"]
    L += ["", "Mainland coin-flip online ranks (same shared slope): " +
          ", ".join(f"{k} {v}" for k, v in mc.items()) + ".", "",
          "## Can the field be predicted? (train one season, test the other)", "",
          "| train → test | attendance AUC | schools exp. / act. | top-50 schools exp. / act. | gold line actual | "
          "simulated (80%) | same as train | abs log error sim. / same |", "|---|---|---|---|---|---|---|---|"]
    for b in res["field_backtest"]:
        L.append(f"| {b['train']} → {b['test']} | {b['attendance_auc']} | {b['schools_expected']} / {b['schools_actual']} | "
                 f"{b['top50_expected']} / {b['top50_actual']} | {b['line_actual']} | {b['line_simulated']} "
                 f"({b['line_simulated_80'][0]}–{b['line_simulated_80'][1]}) | {b['line_same_as_train']} | "
                 f"{b['abs_log_error_simulated']} / {b['abs_log_error_same_as_train']} |")
    L += ["", "## Gold models (train one season, test the other)", "",
          "| model | 2024 log loss (exp. golds) | 2025 log loss (exp. golds) |", "|---|---|---|"]
    gb = res["gold_backtest"]
    for v in gb["2024"]["variants"]:
        L.append(f"| {v} | " + " | ".join(
            f"{gb[s]['variants'][v]['log_loss']} ({gb[s]['variants'][v]['expected_golds']} / {gb[s]['golds']})"
            for s in SEASONS) + " |")
    fc = res["forecast_2026"]
    L += ["", "## 2026 forecast (conditional on attending; 2027-01-09)", "",
          f"Hong Kong-only model fit on 2024 + 2025 linked teams: coin flip at online #{fc['coin_flip_online_rank']}. "
          f"Harder / easier field = the coin flip moved by one SD ({res['year_shift_sd_log_rank']} in log rank, "
          f"{res['year_shift_pairs']} consecutive-season mainland pairs) of the mainland year-to-year change. "
          "The last two columns use the model with an earlier mainland gold, for the update once 2026 mainland "
          "results are in.", "",
          "| online rank | P(gold) | 90% CI | harder field | easier field | no mainland gold | won a mainland gold |",
          "|---|---|---|---|---|---|---|"]
    for g in fc["grid"]:
        L.append(f"| {g['online_rank']} | {g['p']:.1%} | {g['ci90'][0]:.1%}–{g['ci90'][1]:.1%} | "
                 f"{g['p_harder_field']:.1%} | {g['p_easier_field']:.1%} | {g['p_without_mainland_gold']:.1%} | "
                 f"{g['p_after_mainland_gold']:.1%} |")
    for q, teams in fc["schools"].items():
        L += ["", f"### {q} (2026 online teams)", "",
              "| team | online ranks | P(gold) | 90% CI | harder / easier field |", "|---|---|---|---|---|"]
        L += [f"| {t['team']} | {'/'.join(str(round(k)) for k in t['online_ranks'])} | {t['p']:.1%} | "
              f"{t['ci90'][0]:.1%}–{t['ci90'][1]:.1%} | {t['p_harder_field']:.1%} / {t['p_easier_field']:.1%} |"
              for t in teams]
    return "\n".join(L) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--school", action="append", default=["蒙古国立大学"],
                    help="also list every 2026 online team of this school (substring)")
    res = run(schools=tuple(dict.fromkeys(ap.parse_args().school)))
    og.OUT.mkdir(exist_ok=True)
    (og.OUT / "hk_gold.json").write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    md = markdown(res)
    (og.OUT / "hk_gold.md").write_text(md, encoding="utf-8")
    print(md)


if __name__ == "__main__":
    main()
