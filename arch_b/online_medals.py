"""Gold, silver and bronze chances at Asia East regionals from online results.

Medals go to 10% / 20% / 30% of official solvers (board configs; every
2022-2025 contest within rounding), so "gold", "silver or better" and "any
medal" are the top 10% / 30% / 60%.  Each level k reuses the gold model of
``arch_b.online_gold`` with its own fraction:

    logit P(medal >= k) = c_k + b_k * x + d_k * line_k(site)

where ``line_k`` is the rule-admitted team at fraction_k of capacity after the
quota entrants' share, with their relative rate rho_k measured on earlier
seasons (``online_gold.quota_split`` counting that level).  The gold level
reproduces ``online_gold``.  P(silver) = P(>= silver) - P(gold) and
P(bronze) = P(medal) - P(>= silver), with the cumulative probabilities made
monotone.  Hong Kong (registration field) uses ``arch_b.hk_gold``'s approach per
level: ``logit P = c_k + b_k * x`` on its linked 2024-2025 teams.

    python3 -m arch_b.online_medals [--school 蒙古国立大学]

Writes ``output/online_medals.json`` and ``output/online_medals.md``.
"""

import argparse
import collections
import json
import math

import numpy as np

from arch_b import hk_link as hk
from arch_b import online_gold as og

LEVELS = (("gold", 0.10, ("gold",)), ("silver_plus", 0.30, ("gold", "silver")),
          ("medal", 0.60, ("gold", "silver", "bronze")))
CLASSES = ("gold", "silver", "bronze", "none")
VARIANTS = ("online_only", "rules_line_quota_adjusted", "oracle_line")
FORECAST_RANKS = (25, 50, 100, 200, 300, 500)
HK_SEASONS = ("2024", "2025")


def won(medals):
    return lambda r: int(r["medal"] in medals)


def oracle_lines(rows, fraction):
    by = collections.defaultdict(list)
    for r in rows:
        by[(r["season"], r["site"])].append(r["x"])
    return {k: sorted(xs, reverse=True)[max(1, round(fraction * len(xs))) - 1] for k, xs in by.items()}


def site_lines(contests, data, strengths, fraction, rho):
    return {k: og.rules_line(*k, data, strengths, rho, fraction=fraction) for k in contests}


def class_probs(cum):
    """Cumulative P(gold), P(>= silver), P(medal) (last axis) -> class probabilities."""
    cum = np.maximum.accumulate(np.clip(cum, 1e-6, 1 - 1e-6), axis=-1)
    return np.stack([cum[..., 0], cum[..., 1] - cum[..., 0], cum[..., 2] - cum[..., 1], 1 - cum[..., 2]], -1)


def log_loss(p, y):
    p, y = np.clip(p, 1e-6, 1 - 1e-6), np.asarray(y, float)
    return -(y * np.log(p) + (1 - y) * np.log(1 - p))


# --------------------------------------------------------------- backtest

def backtest(rows, data, strengths, seed=0):
    rng = np.random.default_rng(seed)
    contests = {(r["season"], r["site"]) for r in rows}
    out = {}
    for test in og.TEST_SEASONS:
        train = [r for r in rows if r["season"] < test]
        held = [r for r in rows if r["season"] == test]
        sites = sorted({r["site"] for r in held})
        idx = {s: np.array([i for i, r in enumerate(held) if r["site"] == s]) for s in sites}
        draws = [np.concatenate([idx[s] for s in rng.choice(sites, len(sites))]) for _ in range(og.BOOTSTRAPS)]
        res, cum = {"teams": len(held), "levels": {}}, {v: [] for v in VARIANTS}
        for name, frac, medals in LEVELS:
            y = won(medals)
            _, rho = og.quota_split(data, strengths, [s for s in og.MODEL_SEASONS if s < test], won=y)
            lines, orc = site_lines(contests, data, strengths, frac, rho), oracle_lines(rows, frac)
            feats = {"online_only": lambda r: [1, r["x"]],
                     "rules_line_quota_adjusted": lambda r: [1, r["x"], lines[(r["season"], r["site"])]],
                     "oracle_line": lambda r: [1, r["x"], orc[(r["season"], r["site"])]]}
            yt = np.array([y(r) for r in held])
            losses, lev = {}, {"rho": round(rho, 3), "rate": round(float(yt.mean()), 3), "variants": {}}
            for v, f in feats.items():
                w = og.logistic([f(r) for r in train], [y(r) for r in train])
                p = og.sigmoid(np.array([f(r) for r in held], float) @ w)
                cum[v].append(p)
                losses[v] = log_loss(p, yt)
            for v in VARIANTS:
                diff = [losses[v][i].mean() - losses["online_only"][i].mean() for i in draws]
                lev["variants"][v] = {"log_loss": round(float(losses[v].mean()), 5),
                                      "delta_vs_online_only": round(float(losses[v].mean() - losses["online_only"].mean()), 5),
                                      "delta_ci95": [round(float(q), 5) for q in np.percentile(diff, [2.5, 97.5])]}
            res["levels"][name] = lev
        cls = np.array([CLASSES.index(r["medal"] or "none") for r in held])
        res["four_class_log_loss"] = {}
        for v in VARIANTS:
            c = np.stack(cum[v], -1)
            res["four_class_log_loss"][v] = round(float(-np.log(class_probs(c)[np.arange(len(held)), cls]).mean()), 5)
        c = np.stack(cum["rules_line_quota_adjusted"], -1)
        res["crossings"] = int(((c[:, 1] < c[:, 0]) | (c[:, 2] < c[:, 1])).sum())
        out[test] = res
    return out


def hk_rows(data, strengths):
    return [r for r in hk.link_hk(data, strengths) if r["season"] in HK_SEASONS and r["x"] is not None]


def hk_backtest(rows, mainland):
    """Hong Kong-only per level (train the other season) vs mainland online-only."""
    out = {}
    for test in HK_SEASONS:
        te, tr = [r for r in rows if r["season"] == test], [r for r in rows if r["season"] != test]
        res = {}
        for name, _, medals in LEVELS:
            y = won(medals)
            yt = np.array([y(r) for r in te])
            X = np.array([[1, r["x"]] for r in te])
            w_hk = og.logistic([[1, r["x"]] for r in tr], [y(r) for r in tr], l2=1e-2)
            w_ml = og.logistic([[1, r["x"]] for r in mainland], [y(r) for r in mainland])
            res[name] = {"actual": int(yt.sum()), **{
                k: {"log_loss": round(float(log_loss(og.sigmoid(X @ w), yt).mean()), 4),
                    "expected": round(float(og.sigmoid(X @ w).sum()), 1)}
                for k, w in (("hk_only", w_hk), ("mainland_online_only", w_ml))}}
        out[test] = res
    return out


# --------------------------------------------------------------- forecast

def fit_levels(rows, X_of, l2, n_boot, rng, cluster):
    """Coefficients per level and joint bootstrap draws (same resample for every level)."""
    groups = collections.defaultdict(list)
    for i, r in enumerate(rows):
        groups[cluster(r)].append(i)
    keys = sorted(groups)
    picks = [np.concatenate([groups[keys[j]] for j in rng.integers(0, len(keys), len(keys))]) for _ in range(n_boot)]
    w, boots = {}, {}
    for name, _, medals in LEVELS:
        y, X = [won(medals)(r) for r in rows], [X_of(name, r) for r in rows]
        w[name] = og.logistic(X, y, l2=l2)
        boots[name] = np.array([og.logistic([X[i] for i in p], [y[i] for i in p], l2=l2) for p in picks])
    return w, boots


def forecast(rows, hk_teams, data, strengths, schools, seed=1):
    rng = np.random.default_rng(seed)
    contests = {(r["season"], r["site"]) for r in rows}
    sites26 = [r["site"] for r in sorted(data["rules"].values(), key=lambda r: r.get("date", ""))
               if r["season"] == 2026]
    lines, lines26, rhos = {}, {}, {}
    for name, frac, medals in LEVELS:
        _, rhos[name] = og.quota_split(data, strengths, og.MODEL_SEASONS, won=won(medals))
        lines[name] = site_lines(contests, data, strengths, frac, rhos[name])
        lines26[name] = {s: og.rules_line("2026", s, data, strengths, rhos[name], fraction=frac)
                         for s in sites26 if data["rules"][("2026", s)].get("online_bands")}
    w, boots = fit_levels(rows, lambda n, r: [1, r["x"], lines[n][(r["season"], r["site"])]],
                          1e-3, og.BOOTSTRAPS, rng, lambda r: (r["season"], r["site"]))
    w_hk, boots_hk = fit_levels(hk_teams, lambda n, r: [1, r["x"]], 1e-2, og.BOOTSTRAPS, rng, id)

    def predict(site, x):
        if site in hk.SITES:
            z = {n: np.array([1, x]) for n, _, _ in LEVELS}
            ww, bb = w_hk, boots_hk
        else:
            z = {n: np.array([1, x, lines26[n][site]]) for n, _, _ in LEVELS}
            ww, bb = w, boots
        point = class_probs(np.array([og.sigmoid(z[n] @ ww[n]) for n, _, _ in LEVELS]))
        draws = class_probs(np.stack([og.sigmoid(bb[n] @ z[n]) for n, _, _ in LEVELS], -1))
        lo, hi = np.percentile(draws, [10, 90], axis=0)
        return {c: {"p": round(float(point[i]), 4), "p10": round(float(lo[i]), 4), "p90": round(float(hi[i]), 4)}
                for i, c in enumerate(CLASSES[:3])} | {
            "any_medal": round(float(1 - point[3]), 4)}

    modelled = [s for s in sites26 if s in lines26["gold"] or s in hk.SITES]
    grid = {s: {k: predict(s, -math.log(k)) for k in FORECAST_RANKS} for s in modelled}
    teams = {}
    for q in schools:
        teams[q] = [dict(team=t["team"], online_ranks=t["ranks"], mean_online_rank=round(math.exp(-t["x"]), 1),
                         sites={s: predict(s, t["x"]) for s in modelled})
                    for (season, _, _), t in sorted(strengths.items(), key=lambda kv: -kv[1]["x"])
                    if season == "2026" and q in t["school"]]
    return {"rho": {n: round(v, 3) for n, v in rhos.items()},
            "line_online_rank": {n: {s: round(math.exp(-v), 1) for s, v in ls.items()} for n, ls in lines26.items()},
            "sites": modelled, "grid": grid, "schools": teams}


def run(schools=("蒙古国立大学",)):
    data = og.load()
    strengths = og.online_strengths(data["online_teams"])
    rows = [r for r in og.link_regionals(data, strengths)
            if r["season"] in og.MODEL_SEASONS and r["site"] not in og.EXCLUDED_SITES and r["link"]]
    hk_ = hk_rows(data, strengths)
    return {"rows": len(rows), "backtest": backtest(rows, data, strengths),
            "hk_backtest": hk_backtest(hk_, rows),
            "forecast_2026": forecast(rows, hk_, data, strengths, schools)}


def markdown(res):
    L = ["# Gold, silver and bronze chances from online results", "",
         "`arch_b.online_medals`: the online-gold model per medal level (gold = top 10%, silver or better = 30%,",
         "any medal = 60% of official solvers), with a site line and quota-entrant rate per level; Hong Kong",
         "uses a Hong Kong-only model per level. Probabilities assume the team attends.", "",
         "## Backtest (train earlier seasons; Δ log loss vs online-only, contest-bootstrap 95% CI)", "",
         "| test | level | rate | rho | online-only | rules line, quota adjusted | oracle line |",
         "|---|---|---|---|---|---|---|"]
    for test, b in res["backtest"].items():
        for name, lev in b["levels"].items():
            v = lev["variants"]
            L.append(f"| {test} ({b['teams']}) | {name} | {lev['rate']} | {lev['rho']} | {v['online_only']['log_loss']} | "
                     f"{v['rules_line_quota_adjusted']['delta_vs_online_only']:+.4f} "
                     f"[{v['rules_line_quota_adjusted']['delta_ci95'][0]:+.4f}, {v['rules_line_quota_adjusted']['delta_ci95'][1]:+.4f}] | "
                     f"{v['oracle_line']['delta_vs_online_only']:+.4f} |")
    L += ["", "Four-class log loss (gold / silver / bronze / none): " + "; ".join(
        f"{t}: " + ", ".join(f"{v} {x}" for v, x in b["four_class_log_loss"].items()) +
        f" ({b['crossings']} crossings)" for t, b in res["backtest"].items()), "",
        "## Hong Kong (train the other season)", "",
        "| test | level | actual | Hong Kong-only: log loss (expected) | mainland online-only: log loss (expected) |",
        "|---|---|---|---|---|"]
    for test, b in res["hk_backtest"].items():
        for name, v in b.items():
            L.append(f"| {test} | {name} | {v['actual']} | {v['hk_only']['log_loss']} ({v['hk_only']['expected']}) | "
                     f"{v['mainland_online_only']['log_loss']} ({v['mainland_online_only']['expected']}) |")
    fc = res["forecast_2026"]
    L += ["", "## 2026 forecast", "",
          f"Quota-entrant rates: {fc['rho']}. Site lines as online rank (gold / silver+ / medal): " + "; ".join(
              f"{s} {fc['line_online_rank']['gold'][s]} / {fc['line_online_rank']['silver_plus'][s]} / "
              f"{fc['line_online_rank']['medal'][s]}" for s in fc["line_online_rank"]["gold"]) + ".", ""]
    for k in FORECAST_RANKS:
        L += [f"### Team at online #{k}: gold / silver / bronze (any medal)", "",
              "| " + " | ".join(fc["sites"]) + " |", "|" + "---|" * len(fc["sites"]),
              "| " + " | ".join(f"{g['gold']['p']:.0%} / {g['silver']['p']:.0%} / {g['bronze']['p']:.0%} "
                                f"({g['any_medal']:.0%})" for g in (fc["grid"][s][k] for s in fc["sites"])) + " |", ""]
    for q, teams in fc["schools"].items():
        L += [f"### {q}: gold / silver / bronze (any medal)", "",
              "| team | online ranks | " + " | ".join(fc["sites"]) + " |", "|---|---|" + "---|" * len(fc["sites"])]
        for t in teams:
            L.append(f"| {t['team']} | {'/'.join(str(round(k)) for k in t['online_ranks'])} | " + " | ".join(
                f"{p['gold']['p']:.1%} / {p['silver']['p']:.1%} / {p['bronze']['p']:.1%} ({p['any_medal']:.0%})"
                for p in (t["sites"][s] for s in fc["sites"])) + " |")
        L.append("")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--school", action="append", default=["蒙古国立大学"],
                    help="also list every 2026 online team of this school (substring)")
    res = run(schools=tuple(dict.fromkeys(ap.parse_args().school)))
    og.OUT.mkdir(exist_ok=True)
    (og.OUT / "online_medals.json").write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    md = markdown(res)
    (og.OUT / "online_medals.md").write_text(md, encoding="utf-8")
    print(md)


if __name__ == "__main__":
    main()
