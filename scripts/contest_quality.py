#!/usr/bin/env python3
"""Are some ICPC EC regionals harder than the CCPC stations, and how good are their problem sets?

Contest-level numbers only: no problem labels, names, techniques or per-problem
results, so no set is spoiled.  Contests: the onsite XCPCIO boards of the 28
ICPC EC regionals of 2022-2025 (``build_ec_online_data.REGIONALS``) and the 16
CCPC regional stations (``ccpc_icpc_medals.CCPC``), official teams with >= 1
solve ("field").

How hard the medals are:

* ``gold_even`` (mainland ICPC 2023-2025): the CCPC percentile at which a team
  has even odds of gold at this regional, from the linked CCPC/ICPC pairs of
  ``ccpc_icpc_medals`` (pooled slope, the regional's own intercept).
  ``ecf_even``: the same for rank <= 75.  Benchmark (``pooled_even_icpc``):
  with one ICPC regional's percentile, even odds of gold at another sit near
  0.07, well inside that regional's own 0.10 gold line (regression to the
  mean).  So a regional whose gold is as hard as a CCPC gold has
  ``gold_even`` near that benchmark, and a larger value means an easier gold.
  The interval is from the intercept's Fisher standard error.
* ``perf_gold`` / ``perf_bronze``: the CF-equivalent performance of the last
  gold / bronze medallist.  Their (solved, penalty) is placed in the contest's
  QOJ board in the joint fit (``export_virtual_calc.performance_fit``) and
  ranked against the board's onsite rows only: the boards also hold UCup and
  QOJ mirror entries, which play online and finish ~100 CF above the same teams
  onsite (``export_virtual_calc.event_field``).  Only for contests with a QOJ
  board in the fit.  ``mirror_offset``: the same teams' CCPC line minus their
  ICPC line, same season.

How hard the problems are: ``diff_median`` / ``diff_q75``, the CF difficulty
(``output/problem_ratings_calibrated.json``) of the set's median and
upper-quartile problem.

Problem quality, from the onsite standings:

* ``auc``: per problem, how well solving it tracks the team's solves on the
  other problems (AUC of that rest score, solvers vs non-solvers; problems with
  >= 3 of each), averaged over the set.  Equal rest scores count half, so even
  a perfect difficulty ladder stays below 1; read it relatively.  ``flat``:
  problems with AUC < 0.80 (the lowest ~10% of all 2022-2025 problems), whose
  solvers are mixed in strength.
* ``dead``: problems no official team solved.
* ``tie_gold``: the share of the field with the same solve count as the last
  gold medallist (one solve-count group, split by penalty).
* ``rejects``: rejected runs per accepted run (compile errors excluded where
  the board separates them; 47th and 8th boards report only "REJECTED").
* ``consistency``: Spearman correlation between a team's percentile here and at
  the season's other contests (linked pairs), pooled over partners.

    python3 scripts/contest_quality.py      # writes output/contest_quality.{json,md}

Needs numpy + pypinyin; the joint fit takes ~15 s.
"""
import collections
import json
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))
from arch_a import elo  # noqa: E402
from arch_a.load import dedupe_contests  # noqa: E402
from arch_b import export_virtual_calc as ev  # noqa: E402
from arch_b.joint import TAGGED, UCUP  # noqa: E402
import build_ec_online_data as bd  # noqa: E402
import build_xcpcio_official as bxo  # noqa: E402
import ccpc_icpc_medals as cm  # noqa: E402

QOJ = {link.strip("/"): cid for cid, (link, _, _) in bxo.EA_XCPCIO_MATCHES.items()}
QOJ |= {"icpc/49th/shanghai": 1913,  # QOJ "Metropolis"
        "ccpc/10th/harbin": 1817, "ccpc/10th/jinan": 1843, "ccpc/10th/zhengzhou": 1873,
        "ccpc/11th/zhengzhou": 2661, "ccpc/11th/jinan": 2693, "ccpc/11th/chongqing": 3387}
FLAT_AUC = 0.80
OUT = cm.OUT.parent / "contest_quality"


# ------------------------------------------------------------------ boards

def contests():
    out = [dict(kind="icpc", board=b, season=str(s), site=site) for s, sites in bd.REGIONALS.items()
           for site, b in sites.items()]
    out += [dict(kind="ccpc", board=b, season=s, site=b.split("/")[1]) for s, links in cm.CCPC.items()
            for b in links]
    for c in out:
        c["link"] = f"{c['kind']}/{c['board']}"
    return out


def results(c):
    """Field rows (official, >= 1 solve) with medal, and {team: set of solved problems}, rejections, accepts."""
    config, rows = bd.regional_standings(c["board"], c["kind"])
    season = int(c["season"]) if c["kind"] == "icpc" else None  # 47th ICPC boards carry placeholder counts
    counts = bd.medal_counts(season, config, rows)[:3]
    field = {r["team_id"]: dict(r, medal=cm.medal_of(r["official_rank"], r["solved"], counts))
             for r in rows if r["official"] and r["solved"] > 0}
    base = bd.CACHE / "xcpcio" / (c["board"] if c["kind"] == "icpc" else c["link"]).replace("/", "_")
    runs = json.loads((base / "run.json").read_text(encoding="utf-8"))
    by_cell = collections.defaultdict(list)
    for r in sorted(runs, key=lambda r: (r["timestamp"], str(r.get("id")))):
        if str(r["team_id"]) in field:
            by_cell[(str(r["team_id"]), str(r["problem_id"]))].append(r["status"])
    solved, rejects, accepts = collections.defaultdict(set), 0, 0
    for (tid, pid), statuses in by_cell.items():
        for s in statuses:
            if s in ("ACCEPTED", "CORRECT"):
                solved[tid].add(pid)
                accepts += 1
                break
            if s not in ("COMPILATION_ERROR", "PENDING", "FROZEN", "UNKNOWN"):
                rejects += 1
    problems = [str(p["id"]) for p in config["problems"]]
    return field, counts, problems, solved, rejects, accepts


# ------------------------------------------------------------------ quality

def auc(scores, labels):
    """P(score of a positive > score of a negative), ties half; None with < 3 of either."""
    pos = np.array([s for s, y in zip(scores, labels) if y], float)
    neg = np.array([s for s, y in zip(scores, labels) if not y], float)
    if len(pos) < 3 or len(neg) < 3:
        return None
    return float(((pos[:, None] > neg[None, :]).sum() + 0.5 * (pos[:, None] == neg[None, :]).sum())
                 / (len(pos) * len(neg)))


def discrimination(problems, solved, teams):
    """Per-problem AUC of the rest score (solves on the other problems)."""
    out = []
    for p in problems:
        labels = [p in solved[t] for t in teams]
        a = auc([len(solved[t]) - y for t, y in zip(teams, labels)], labels)
        if a is not None:
            out.append(a)
    return out


def tie_share(field, counts):
    """Share of the field with the last gold medallist's solve count."""
    gold = [r for r in field.values() if r["medal"] == "gold"]
    if not gold:
        return None
    line = max(gold, key=lambda r: r["official_rank"])["solved"]
    return sum(r["solved"] == line for r in field.values()) / len(field)


def spearman(a, b):
    ra, rb = (np.argsort(np.argsort(x)) for x in (a, b))
    return float(np.corrcoef(ra, rb)[0, 1])


def consistency(pairs):
    """{contest link: (rho, n)} over (pct here, pct at the partner) of every linked pair touching it."""
    by = collections.defaultdict(list)
    for a, b in pairs:
        by[a["link"]].append((a["pct"], b["pct"]))
        by[b["link"]].append((b["pct"], a["pct"]))
    return {k: (spearman(*zip(*v)), len(v)) for k, v in by.items() if len(v) >= 30}


def associations(rows, n_perm=4000, seed=2026):
    """{metric: (Spearman with consistency over contests, two-sided permutation p)}."""
    rng = np.random.default_rng(seed)
    out = {}
    for k in ("auc", "flat", "dead", "tie_gold", "rejects", "field"):
        x, y = zip(*[(r[k], r["consistency_rho"]) for r in rows if r[k] is not None and r["consistency_rho"] is not None])
        rho = spearman(x, y)
        null = [spearman(x, rng.permutation(y)) for _ in range(n_perm)]
        out[k] = (rho, float(np.mean(np.abs(null) >= abs(rho))), len(x))
    return out


# ------------------------------------------------------------------ difficulty

def even_odds_by_regional(pairs):
    """{ICPC link: {outcome: (CCPC percentile at P = 50%, 90% low, high)}}: the pooled slope with the
    regional's own intercept; the interval is from the intercept's Fisher standard error (team
    clustering ignored, so slightly narrow)."""
    models = cm.curve(pairs, n_boot=0)
    out = {}
    for link in dict.fromkeys(r["link"] for _, r in pairs):
        hit = [(dict(c, board=link), r) for c, r in pairs if r["link"] == link]  # offsets grouped by "board"
        offs = cm.station_offsets(hit, models)[link]
        x = np.array([cm.logit(c["pct"]) for c, _ in hit])
        out[link] = {}
        for k in ("gold", "ecf_line"):
            (a, b), _ = models[k]
            p = 1 / (1 + np.exp(-(a + b * x + offs[k])))
            se = 1 / math.sqrt((p * (1 - p)).sum())
            out[link][k] = tuple(1 / (1 + math.exp((a + o) / b)) for o in (offs[k], offs[k] - 1.645 * se,
                                                                           offs[k] + 1.645 * se))
    return out


def performance(cids):
    """perf(QOJ id, solved, penalty minutes): CF performance of that onsite result placed in the
    QOJ board, ranked within the event's own rows when the board also holds mirror rows
    (``ev.event_field``)."""
    _, theta, to_cf, row_lookup = ev.performance_fit()
    raw = []
    for path in [TAGGED] + list(UCUP):
        with open(path, encoding="utf-8") as f:
            raw += [c for c in json.load(f) if c["contest_id"] in cids]
    boards = {}
    for c in dedupe_contests(raw):  # the fit's copy (tagged.json first): row_lookup indexes its rows
        rows = [(s["total_solved"], s["penalty_seconds"], row_lookup[(c["contest_id"], i)][0],
                 str(s.get("team_id") or "").startswith("$DEFAULT"))
                for i, s in enumerate(c["standings"]) if (c["contest_id"], i) in row_lookup]
        s, p, idx, official = (np.array(x) for x in zip(*rows))
        field = ev.event_field(official)
        boards[c["contest_id"]] = (s[field], p[field], idx[field])
    cache = {}

    def perf(cid, solved, penalty):
        if (cid, solved, penalty) not in cache:
            s, p, idx = boards[cid]
            rank = 1 + int(((s > solved) | ((s == solved) & (p < penalty * 60))).sum())
            cache[(cid, solved, penalty)] = to_cf(elo.performance_rating(rank, theta[idx]))
        return cache[(cid, solved, penalty)]
    return perf


def mirror_offset(pairs, perf):
    """The same teams, same season: CCPC result placed in the CCPC set's QOJ mirror minus ICPC result
    placed in the regional's QOJ board, by the mean of the two (so no regression to the mean)."""
    both = [(perf(QOJ[c["link"]], c["solved"], c["penalty_minutes"]),
             perf(QOJ[r["link"]], int(r["solved"]), int(r["penalty_minutes"])))
            for c, r in pairs if c["link"] in QOJ and r["link"] in QOJ and int(r["solved"]) > 0]
    mean = np.array([(a + b) / 2 for a, b in both])
    diff = np.array([a - b for a, b in both])
    out = []
    for lo, hi in ((0, 2200), (2200, 2400), (2400, 2600), (2600, 2800), (2800, 4000)):
        s = (mean >= lo) & (mean < hi)
        out.append(dict(lo=lo, hi=hi, n=int(s.sum()), diff=float(diff[s].mean())))
    return dict(bands=out, n=len(both), diff=float(diff.mean()))


def problem_difficulty():
    by = collections.defaultdict(list)
    for p in json.loads((cm.og.OUT / "problem_ratings_calibrated.json").read_text(encoding="utf-8")):
        by[p["contest_id"]].append(p["difficulty_cf"])
    return by


# ------------------------------------------------------------------ report

def fmt(v, spec):
    return "–" if v is None else format(v, spec)


def even(v):
    return "–" if v is None else f"{v[0]:.3f} ({v[1]:.3f}–{v[2]:.3f})"


def markdown(res):
    rows = res["contests"]
    pooled = res["pooled_even"]
    out = ["# ICPC regionals vs CCPC stations: medal difficulty and problem quality", "",
           "Generated by `scripts/contest_quality.py`. Contest-level numbers only (no problem labels, "
           "names or per-problem results). Field = official teams with >= 1 solve.", "",
           "## ICPC regional medals measured against CCPC (same teams, same season)", "",
           "CCPC percentile at which a team has even odds of gold / rank <= 75 at the regional, with a 90% "
           "interval. CCPC lines: gold 0.10, silver 0.30, bronze 0.60. Pooled over all mainland regionals "
           f"2023-2025: gold {pooled['gold']:.3f}, rank <= 75 {pooled['ecf_line']:.3f}, silver or better "
           f"{pooled['silver+']:.3f}, any medal {pooled['medal']:.3f}. Benchmark: with one ICPC regional's "
           f"percentile, even odds of gold at another regional sit at {res['pooled_even_icpc']['gold']:.3f} "
           "(not at its own 0.10 line: teams regress to the mean). So a regional whose gold is as hard as a "
           f"CCPC gold has a value near {res['pooled_even_icpc']['gold']:.3f}; above it, the gold is easier.", "",
           "| regional | field | gold even | rank <= 75 even |", "|---|---|---|---|"]
    for r in sorted((r for r in rows if r["gold_even"]), key=lambda r: r["gold_even"][0]):
        out.append(f"| {r['label']} | {r['field']} | {even(r['gold_even'])} | {even(r['ecf_even'])} |")
    out += ["", "## Medal lines in CF-equivalent performance, and problem difficulty", "",
            "Performance of the last gold / bronze medallist, its (solved, penalty) placed in the contest's "
            "QOJ board in the joint fit. ICPC boards hold the onsite teams; CCPC sets only have a UCup mirror, "
            "on which the same teams read the same as on the onsite boards (next table). Problem difficulty: "
            "CF rating of the set's median and upper-quartile problem.", "",
            "| season | contest | field | perf gold | perf bronze | median problem | q75 problem |",
            "|---|---|---|---|---|---|---|"]
    for r in sorted((r for r in rows if r["perf_gold"]), key=lambda r: (r["season"], r["kind"], -r["perf_gold"])):
        out.append(f"| {r['season']} | {r['label']}{' (mirror)' if r['kind'] == 'ccpc' else ''} | {r['field']} | "
                   f"{r['perf_gold']:.0f} | {fmt(r['perf_bronze'], '.0f')} | {fmt(r['diff_median'], '.0f')} | "
                   f"{fmt(r['diff_q75'], '.0f')} |")
    m = res["mirror_offset"]
    out += ["", f"**Mirror check.** {m['n']} linked (CCPC, ICPC) pairs with both sets in the fit: CCPC result "
            f"on the mirror minus ICPC result on the onsite board, mean {m['diff']:+.0f}, by the mean of the two:", "",
            "| mean performance | n | CCPC mirror − ICPC onsite |", "|---|---|---|"]
    for b in m["bands"]:
        out.append(f"| {b['lo']}–{b['hi']} | {b['n']} | {b['diff']:+.0f} |")
    out += ["", "## Problem quality", "",
            f"`auc`: mean per-problem AUC (solving it vs solves on the rest); `flat`: problems with AUC < "
            f"{FLAT_AUC}; `dead`: unsolved by every official team; `tie gold`: share of the field on the gold "
            "line's solve count; `rejects`: rejected runs per accepted run; `consistency`: Spearman with the "
            "same teams' percentiles at the season's other contests (n pairs).", "",
            "| contest | problems | auc | flat | dead | tie gold | rejects | consistency (n) |",
            "|---|---|---|---|---|---|---|---|"]
    for r in sorted(rows, key=lambda r: -r["auc"]):
        cons = "–" if r["consistency"] is None else f"{r['consistency'][0]:.2f} ({r['consistency'][1]})"
        out.append(f"| {r['label']} | {r['problems']} | {r['auc']:.3f} | {r['flat']} | {r['dead']} | "
                   f"{fmt(r['tie_gold'], '.0%')} | {r['rejects']:.2f} | {cons} |")
    out += ["", "Which signals go with a consistent ranking? Spearman of each metric with `consistency` "
            "across contests (permutation p):", "", "| metric | rho | p | contests |", "|---|---|---|---|"]
    for k, (rho, p, n) in res["associations"].items():
        out.append(f"| {k} | {rho:+.2f} | {p:.3f} | {n} |")
    out += ["", "## ICPC vs CCPC (mainland ICPC; 2023-2025, or the seasons with CCPC values)", "",
            "| metric | ICPC mean | CCPC mean | difference (90% bootstrap over contests) | contests |",
            "|---|---|---|---|---|"]
    for k, v in res["compare"].items():
        out.append(f"| {k} | {v['icpc']:.3f} | {v['ccpc']:.3f} | {v['diff']:+.3f} ({v['lo']:+.3f} … {v['hi']:+.3f}) "
                   f"| {v['n'][0]} / {v['n'][1]} |")
    return "\n".join(out) + "\n"


def compare(rows, seed=2026, n_boot=4000):
    """ICPC (mainland) minus CCPC means, bootstrap over contests, over the 2023-2025 seasons in which the
    CCPC side has the metric (problem difficulty: 2024-2025).  Performance lines are left out: CCPC has
    them only for the six sets with a QOJ mirror."""
    rng = np.random.default_rng(seed)
    out = {}
    for k in ("auc", "flat", "dead", "tie_gold", "rejects", "consistency_rho", "diff_median", "diff_q75"):
        seasons = {r["season"] for r in rows if r["kind"] == "ccpc" and r[k] is not None} & set(cm.og.MODEL_SEASONS)
        groups = [[r[k] for r in rows if r["season"] in seasons and r["kind"] == kind and r[k] is not None
                   and (kind == "ccpc" or r["mainland"])] for kind in ("icpc", "ccpc")]
        if min(map(len, groups)) < 3:
            continue
        a, b = (np.array(g, float) for g in groups)
        boot = [rng.choice(a, len(a)).mean() - rng.choice(b, len(b)).mean() for _ in range(n_boot)]
        out[k] = dict(icpc=a.mean(), ccpc=b.mean(), diff=a.mean() - b.mean(), n=(len(a), len(b)),
                      lo=float(np.percentile(boot, 5)), hi=float(np.percentile(boot, 95)))
    return out


def main():
    data = cm.og.load()
    rows, lines, diffs = [], {}, problem_difficulty()
    ccpc_rows, field_of = [], {}
    for c in contests():
        field, counts, problems, solved, rejects, accepts = results(c)
        teams = list(field)
        aucs = discrimination(problems, solved, teams)
        cid = QOJ.get(c["link"])
        for tier, last in (("gold", counts[0]), ("bronze", sum(counts))):
            line = [r for r in field.values() if r["official_rank"] <= last]
            if cid in diffs and line:
                r = max(line, key=lambda r: r["official_rank"])
                lines[(c["link"], tier)] = (cid, r["solved"], r["penalty_minutes"])
        d = diffs.get(cid)
        rows.append(dict(c, label=f"{c['kind'].upper()} {c['site']} {c['season']}", field=len(field),
                         mainland=c["site"] not in cm.og.EXCLUDED_SITES, problems=len(problems),
                         auc=float(np.mean(aucs)), flat=sum(a < FLAT_AUC for a in aucs),
                         dead=sum(not any(p in solved[t] for t in teams) for p in problems),
                         tie_gold=tie_share(field, counts), rejects=rejects / accepts,
                         diff_median=float(np.median(d)) if d else None,
                         diff_q75=float(np.percentile(d, 75)) if d else None))
        field_of[c["link"]] = field
        if c["kind"] == "ccpc":
            ccpc_rows += [dict(r, season=c["season"], board=c["board"], link=c["link"],
                               pct=r["official_rank"] / len(field), s=cm.og.norm_school(r["school"]),
                               m=cm.members(r["members"]), py=[cm.hk.pinyin_variants(m) for m in r["members"].split("|")])
                          for r in field.values()]

    icpc = cm.icpc_rows(data["regional_teams"])
    for r in icpc:
        r["link"] = f"icpc/{bd.REGIONALS[int(r['season'])][r['site']]}"
        r["pct"] = r["rank"] / len(field_of[r["link"]])
    pairs = cm.link(ccpc_rows, icpc)
    cons = consistency(pairs + [(a, b) for a, b in cm.icpc_pairs(icpc) if a["site"] < b["site"]])
    model_pairs = [(c, r) for c, r in pairs if c["season"] in cm.og.MODEL_SEASONS and r["mainland"]]
    odds = even_odds_by_regional(model_pairs)
    perf = performance(set(QOJ.values()))
    for r in rows:
        r["consistency"] = cons.get(r["link"])
        r["consistency_rho"] = r["consistency"][0] if r["consistency"] else None
        r["gold_even"] = odds.get(r["link"], {}).get("gold")
        r["ecf_even"] = odds.get(r["link"], {}).get("ecf_line")
        r["perf_gold"], r["perf_bronze"] = (perf(*lines[(r["link"], t)]) if (r["link"], t) in lines else None
                                            for t in ("gold", "bronze"))
    res = dict(contests=rows, compare=compare(rows), associations=associations(rows),
               pooled_even={k: 1 / (1 + math.exp(w[0] / w[1])) for k, (w, _) in cm.curve(model_pairs, n_boot=0).items()},
               pooled_even_icpc={k: 1 / (1 + math.exp(w[0] / w[1])) for k, (w, _) in cm.curve(
                   [(a, b) for a, b in cm.icpc_pairs(icpc) if a["season"] in cm.og.MODEL_SEASONS], n_boot=0).items()},
               mirror_offset=mirror_offset(pairs, perf))
    OUT.with_suffix(".json").write_text(json.dumps(res, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    OUT.with_suffix(".md").write_text(markdown(res), encoding="utf-8")
    print(f"{len(rows)} contests -> {OUT.relative_to(cm.og.ROOT)}.json / .md")


if __name__ == "__main__":
    main()
