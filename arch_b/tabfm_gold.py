"""Local baselines for the TabFM gold table, and scoring of TabFM predictions.

The table is ``data/tabfm_gold/`` (``scripts/build_tabfm_gold_data.py``).
Each split trains on earlier seasons and predicts one held-out season
(2024, 2025), the same leave-season-out protocol as ``arch_b.online_gold``,
but on every official team (unlinked teams included).  Baselines are L2
logistic regressions on standardized features (missing values -> 0 plus an
indicator, strings one-hot):

* ``prior``         intercept only
* ``online_only``   online strength (the shipped model's feature)
* ``online_rules``  + the site's rules line
* ``pre_registration``  every online, rules and history feature
* ``all_features``  + the registered field (band/quota, field line, ...)

Rank features enter as log(rank); the L2 strength of each model is chosen by
leave-one-contest-out log loss inside the training seasons.

A TabFM run (``data/tabfm_gold/predict.sql``) is scored against them with
``--score FILE`` (repeatable, one file per feature set; the model is named
``tabfm_<file stem>``), a CSV of ``row_id`` and ``p_gold`` (the probability
of the ``true`` class from ``predicted_gold_probs``).  Differences carry contest-
bootstrap 95% intervals.

    python3 -m arch_b.tabfm_gold                      # baselines
    python3 -m arch_b.tabfm_gold --score preds.csv    # + TabFM predictions
    python3 -m arch_b.tabfm_gold --forecast f.csv     # 2026 forecast report

Writes ``output/tabfm_gold.json`` and ``output/tabfm_gold.md``.
"""

import argparse
import csv
import json
import math
from pathlib import Path

import numpy as np

from arch_b.online_gold import BOOTSTRAPS, logistic, sigmoid

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "tabfm_gold"
OUT = ROOT / "output"
L2_GRID = (0.3, 1.0, 3.0, 10.0, 30.0, 100.0)
LOG_FEATURES = {"online_rank_r1", "online_rank_r2", "school_rank_combined", "school_rank_best_round",
                "field_strength_rank"}


def load():
    meta = json.loads((DATA / "features.json").read_text())
    with open(DATA / "teams.csv", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return rows, meta


def model_features(meta):
    tiers = meta["tiers"]
    pre = tiers["online"] + tiers["rules"] + tiers["history"]
    return {"prior": [], "online_only": ["online_x"], "online_rules": ["online_x", "site_rules_line_x"],
            "pre_registration": pre, "all_features": pre + tiers["registration"]}


def design(train, test, names, types):
    """Standardized numeric columns (+ missing indicators), one-hot strings."""
    cols_tr, cols_te = [np.ones(len(train))], [np.ones(len(test))]
    for n in names:
        if types[n] == "STRING":
            for level in sorted({r[n] for r in train})[1:]:
                cols_tr.append(np.array([r[n] == level for r in train], float))
                cols_te.append(np.array([r[n] == level for r in test], float))
            continue

        def values(rs):
            v = np.array([np.nan if r[n] == "" else (r[n] == "true") if types[n] == "BOOL"
                          else float(r[n]) for r in rs], float)
            return np.log(v) if n in LOG_FEATURES else v
        tr, te = values(train), values(test)
        mu, sd = np.nanmean(tr), np.nanstd(tr) or 1.0
        cols_tr.append(np.nan_to_num((tr - mu) / sd))
        cols_te.append(np.nan_to_num((te - mu) / sd))
        if np.isnan(tr).any():
            cols_tr.append(np.isnan(tr).astype(float))
            cols_te.append(np.isnan(te).astype(float))
    return np.column_stack(cols_tr), np.column_stack(cols_te)


def baselines(rows, meta):
    types = {f["name"]: f["type"] for f in meta["features"]}
    preds, chosen = {}, {}
    for split, s in meta["splits"].items():
        train = [r for r in rows if r["season"] in s["train"]]
        test = [r for r in rows if r["season"] == s["test"]]
        y = np.array([r["gold"] == "true" for r in train], float)
        preds[split], chosen[split] = {}, {}
        for model, names in model_features(meta).items():
            l2 = chosen[split][model] = choose_l2(train, names, types)
            Xtr, Xte = design(train, test, names, types)
            w = logistic(Xtr, y, l2=l2)
            preds[split][model] = {r["row_id"]: float(p) for r, p in zip(test, sigmoid(Xte @ w))}
    return preds, chosen


def choose_l2(train, names, types):
    """L2 with the lowest leave-one-contest-out log loss within ``train``."""
    contests = sorted({(r["season"], r["site"]) for r in train})
    best = None
    for l2 in L2_GRID:
        losses = []
        for c in contests:
            fit = [r for r in train if (r["season"], r["site"]) != c]
            held = [r for r in train if (r["season"], r["site"]) == c]
            Xf, Xh = design(fit, held, names, types)
            w = logistic(Xf, [r["gold"] == "true" for r in fit], l2=l2)
            p = np.clip(sigmoid(Xh @ w), 1e-6, 1 - 1e-6)
            y = np.array([r["gold"] == "true" for r in held], float)
            losses.extend(-(y * np.log(p) + (1 - y) * np.log(1 - p)))
        loss = float(np.mean(losses))
        if best is None or loss < best[1]:
            best = (l2, loss)
    return best[0]


def evaluate(rows, meta, preds, reference="online_only", seed=0):
    """Log loss / Brier per model, on all held-out teams and on online-linked
    ones, with the contest-bootstrap interval of each model minus reference."""
    rng = np.random.default_rng(seed)
    out = {}
    for split, s in meta["splits"].items():
        test = [r for r in rows if r["season"] == s["test"]]
        y = np.array([r["gold"] == "true" for r in test], float)
        sites = sorted({r["site"] for r in test})
        idx = {site: np.array([i for i, r in enumerate(test) if r["site"] == site]) for site in sites}
        draws = [np.concatenate([idx[site] for site in rng.choice(sites, len(sites))]) for _ in range(BOOTSTRAPS)]
        linked = np.array([r["online_x"] != "" for r in test])
        loss = {}
        for model, p in preds[split].items():
            p = np.clip([p[r["row_id"]] for r in test], 1e-6, 1 - 1e-6)
            loss[model] = (-(y * np.log(p) + (1 - y) * np.log(1 - p)), (p - y) ** 2)
        ref = loss[reference][0]
        out[split] = {"teams": len(test), "linked": int(linked.sum()), "golds": int(y.sum()), "models": {}}
        for model, (ll, br) in loss.items():
            d = ll - ref
            out[split]["models"][model] = {
                "log_loss": round(float(ll.mean()), 5), "brier": round(float(br.mean()), 5),
                "log_loss_linked": round(float(ll[linked].mean()), 5),
                "log_loss_unlinked": round(float(ll[~linked].mean()), 5),
                f"delta_vs_{reference}": round(float(d.mean()), 5),
                "delta_ci95": [round(float(q), 5) for q in np.percentile([d[i].mean() for i in draws], [2.5, 97.5])]}
    return out


def read_predictions(path, rows, meta):
    """TabFM output CSV (row_id, p_gold) -> {split: {row_id: p}}; every held-out row required."""
    with open(path, encoding="utf-8") as f:
        p = {r["row_id"]: float(r["p_gold"]) for r in csv.DictReader(f)}
    out = {}
    for split, s in meta["splits"].items():
        ids = [r["row_id"] for r in rows if r["season"] == s["test"]]
        missing = [i for i in ids if i not in p]
        if missing:
            raise ValueError(f"{split}: {len(missing)} held-out rows lack a prediction, e.g. {missing[0]}")
        out[split] = {i: p[i] for i in ids}
    return out


REFERENCE_RANKS = (10, 25, 50, 100, 200)


def forecast_report(path):
    """2026 forecast from TabFM output on ``forecast_2026.csv``: per site, the
    gold chance of teams near reference online ranks and of a top-300 team,
    next to the online-gold model; plus every NUM team."""
    with open(DATA / "forecast_2026.csv", encoding="utf-8") as f:
        rows = {r["row_id"]: r for r in csv.DictReader(f)}
    with open(path, encoding="utf-8") as f:
        p = {r["row_id"]: float(r["p_gold"]) for r in csv.DictReader(f)}
    missing = set(rows) - set(p)
    if missing:
        raise ValueError(f"{len(missing)} forecast rows lack a prediction")
    og_forecast = {e["site"]: e for e in json.loads((OUT / "online_gold.json").read_text())["forecast_2026"]}
    sites = {}
    for r in rows.values():
        rank = math.exp(-float(r["online_x"]))
        sites.setdefault(r["site"], []).append((rank, p[r["row_id"]], r))
    out = []
    for site, teams in sites.items():
        ref = {k: float(np.median([q for rank, q, _ in teams if 0.8 * k <= rank <= 1.25 * k]))
               for k in REFERENCE_RANKS}
        top = [q for rank, q, _ in teams if rank <= 300]
        e = og_forecast.get(site, {})
        out.append(dict(site=site, date=e.get("date"), top300_mean=round(float(np.mean(top)), 4),
                        tabfm=ref, online_gold={k: e["gold_by_online_rank"][str(k)]["p"] for k in REFERENCE_RANKS},
                        online_gold_line=e.get("rules_line_online_rank")))
    out.sort(key=lambda o: -o["top300_mean"])
    num = sorted(((r["team"], r["site"], q, math.exp(-float(r["online_x"]))) for _, q, r in
                  [t for ts in sites.values() for t in ts] if "蒙古国立" in r["school"]), key=lambda t: t[3])
    return {"sites": out, "num": num}


def forecast_markdown(fc):
    L = ["# 2026 gold forecast with TabFM", "",
         "Generated by `python3 -m arch_b.tabfm_gold --forecast FILE` from managed TabFM (BigQuery "
         "`AI.PREDICT`) trained on every 2023-2025 mainland regional team with the 28 forecast features "
         "(`data/tabfm_gold/forecast_2026.sql`). Probability of gold **if the team attends**, before "
         "registration: no member history, no earlier 2026 results, field unknown. Cells: median over "
         "2026 online teams within ±25% of the online rank (TabFM / online-gold model).", "",
         "| # | site | date | mean, top-300 teams | " + " | ".join(f"#{k}" for k in REFERENCE_RANKS) +
         " | online-gold rules line |", "|---|---|---|---|" + "---|" * (len(REFERENCE_RANKS) + 1)]
    for i, s in enumerate(fc["sites"], 1):
        cells = [f"{s['tabfm'][k]:.0%} / {s['online_gold'][k]:.0%}" for k in REFERENCE_RANKS]
        L.append(f"| {i} | {s['site']} | {s['date']} | {s['top300_mean']:.1%} | " + " | ".join(cells) +
                 f" | {s['online_gold_line']} |")
    L += ["", "## National University of Mongolia teams", "",
          "| team | online rank (geo. mean) | " + " | ".join(s["site"] for s in fc["sites"]) + " |",
          "|---|---|" + "---|" * len(fc["sites"])]
    by_team = {}
    for team, site, q, rank in fc["num"]:
        by_team.setdefault((team, rank), {})[site] = q
    for (team, rank), qs in sorted(by_team.items(), key=lambda kv: kv[0][1]):
        L.append(f"| {team} | {rank:.0f} | " + " | ".join(f"{qs[s['site']]:.1%}" for s in fc["sites"]) + " |")
    return "\n".join(L) + "\n"


def markdown(res):
    L = ["# Gold prediction table for TabFM: local baselines", "",
         "Generated by `python3 -m arch_b.tabfm_gold`. Train on earlier seasons, predict the held-out "
         "season; every official team of the mainland regionals. Δ = log loss minus `online_only`, "
         "with contest-bootstrap 95% interval (negative = better). Features and tiers: "
         "`data/tabfm_gold/features.json`.", ""]
    for split, v in res["evaluation"].items():
        L += [f"## {split} ({v['teams']} teams, {v['linked']} linked, {v['golds']} golds)", "",
              "| model | log loss | Δ vs online_only (95% CI) | linked | unlinked | Brier |",
              "|---|---|---|---|---|---|"]
        for m, x in v["models"].items():
            L.append(f"| {m} | {x['log_loss']:.4f} | {x['delta_vs_online_only']:+.4f} "
                     f"[{x['delta_ci95'][0]:+.4f}, {x['delta_ci95'][1]:+.4f}] | {x['log_loss_linked']:.4f} | "
                     f"{x['log_loss_unlinked']:.4f} | {x['brier']:.4f} |")
        L.append("")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--score", action="append", default=[],
                    help="TabFM predictions CSV with row_id,p_gold (repeatable)")
    ap.add_argument("--forecast", help="TabFM predictions CSV (row_id,p_gold) for forecast_2026.csv")
    args = ap.parse_args()
    if args.forecast:
        fc = forecast_report(args.forecast)
        OUT.mkdir(exist_ok=True)
        (OUT / "tabfm_forecast_2026.json").write_text(json.dumps(fc, ensure_ascii=False, indent=1) + "\n")
        md = forecast_markdown(fc)
        (OUT / "tabfm_forecast_2026.md").write_text(md)
        print(md)
        return
    rows, meta = load()
    preds, chosen = baselines(rows, meta)
    for path in args.score:
        for split, p in read_predictions(path, rows, meta).items():
            preds[split][f"tabfm_{Path(path).stem}"] = p
    res = {"l2_chosen": chosen, "models": model_features(meta), "evaluation": evaluate(rows, meta, preds)}
    OUT.mkdir(exist_ok=True)
    (OUT / "tabfm_gold.json").write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n")
    md = markdown(res)
    (OUT / "tabfm_gold.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
