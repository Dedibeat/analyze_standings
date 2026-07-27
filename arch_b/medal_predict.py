"""Predict medal cutoffs and compare regional-contest choices.

The shipped chooser estimates each regular regional from regular-regionals only,
with city history shrunk toward the overall mean by one pseudo-contest.  This
avoids treating a one-off city result as certain and avoids leaking EC Final
strength into an ordinary regional hosted by the same city.

Temporal order, year trend, and field size remain descriptive analyses, but are
not used for future recommendations: they do not improve forward-in-time
validation and the 2026 dates/order are not published.

Default run: compare the current 2026 Asia East regional cities:

Run:  ./.venv/bin/python -m arch_b.medal_predict

Other useful modes:

    ./.venv/bin/python -m arch_b.medal_predict --target silver
    ./.venv/bin/python -m arch_b.medal_predict --city Hangzhou
    ./.venv/bin/python -m arch_b.medal_predict --report
"""

import argparse
import json
import math
import os
import statistics
from collections import defaultdict

import numpy as np

OUT = os.path.join(os.path.dirname(__file__), os.pardir, "output")
MEDAL = os.path.join(OUT, "medal_badges.json")
TIERS = ("gold", "silver", "bronze")
CITY_SHRINKAGE = 1.0

# ICPC Global listed these eight 2026 Asia East onsite regionals on 2026-07-27.
# Dates/order were still blank. Online contests and the EC Final are deliberately
# excluded because this chooser compares ordinary medal-awarding regionals.
# Source: https://icpc.global/regionals/results
REGIONALS_BY_YEAR = {
    2026: (
        "Chengdu", "Hong Kong", "Nanchang", "Nanjing",
        "Shanghai", "Shenyang", "Wuhan", "Xi'an",
    ),
}

# Stored contest names occasionally collapse the QOJ category's actual host.
# QOJ category 460 labels 1099 "The 2022 ICPC Asia Hong Kong Regional Contest",
# while medal_badges.json carries the shorter "Hong Kong & Macau".
CONTEST_CITY = {
    1099: "Hong Kong",
}

# --- Chronological order within each ICPC Asia East season ---
# Sourced from ICPC Beijing HQ official schedules (icpc.pku.edu.cn):
#
# 2022 (47th): Shenyang Nov 5-6, Xi'an Nov 12-13, Jinan Nov 26-27,
#   Hangzhou Dec 3-4, Nanjing Dec 17-18, Hong Kong & Macau Jan 14 2023
# 2023 (48th): Nanjing Nov 4-5, Shenyang Nov 11-12, Macau Nov 18-19,
#   Hefei Nov 25-26, Jinan Dec 2-3, Hangzhou Dec 9-10,
#   EC-Final Shanghai Jan 12-14 2024, Xi'an Invitational (~Feb/Mar 2024)
# 2024 (49th): Chengdu Oct 26-27, Nanjing Nov 2-3, Hangzhou Nov 9-10,
#   Shenyang Nov 23-24, Kunming Nov 30-Dec 1, Hong Kong Dec 21-22,
#   EC-Final (Xi'an) Dec 27-29
# 2025 (50th): Xi'an Oct 18-19, Chengdu Oct 25-26, Wuhan Nov 1-2,
#   Nanjing Nov 8-9, Shenyang Nov 15-16, Shanghai Nov 22-23,
#   Hong Kong Nov 29-30
CONTEST_ORDER = {
    # 2022
    1096: 1, 1051: 2, 1053: 3, 1071: 4, 1093: 5, 1099: 6,
    # 2023 (verified against icpc.pku.edu.cn/ssxx/1119_icpcbjzb_151096.htm)
    1435: 1, 1449: 2, 1459: 3, 1440: 4, 1472: 5, 1516: 6, 1522: 7, 1784: 8,
    # 2024
    1821: 1, 1828: 2, 1893: 3, 1865: 4, 1871: 5, 1885: 6, 1894: 7,
    # 2025
    2562: 1, 2567: 2, 2609: 3, 2581: 4, 2641: 5, 2908: 6, 3169: 7,
}

EC_FINALS = {1522, 1894}  # Shanghai 48th EC-Final, China/EC-Final 49th
INVITATIONAL = {1784}      # Xi'an Invitational (small post-ECFinal event)

# City features for geographic analysis
CITY_FEATURES = {
    "Xi'an":     {"lat": 34.3, "lon": 108.9, "coastal": 0, "region": "Northwest"},
    "Jinan":     {"lat": 36.7, "lon": 117.0, "coastal": 0, "region": "Northeast Coast"},
    "Hangzhou":  {"lat": 30.3, "lon": 120.2, "coastal": 1, "region": "East"},
    "Nanjing":   {"lat": 32.1, "lon": 118.8, "coastal": 0, "region": "East"},
    "Shenyang":  {"lat": 41.8, "lon": 123.4, "coastal": 0, "region": "Northeast"},
    "Macau":     {"lat": 22.2, "lon": 113.5, "coastal": 1, "region": "South"},
    "Hefei":     {"lat": 31.8, "lon": 117.3, "coastal": 0, "region": "East"},
    "Shanghai":  {"lat": 31.2, "lon": 121.5, "coastal": 1, "region": "East"},
    "Chengdu":   {"lat": 30.6, "lon": 104.1, "coastal": 0, "region": "Southwest"},
    "Kunming":   {"lat": 25.0, "lon": 102.7, "coastal": 0, "region": "Southwest"},
    "Hong Kong": {"lat": 22.3, "lon": 114.2, "coastal": 1, "region": "South"},
    "China":     {"lat": 31.2, "lon": 121.5, "coastal": 1, "region": "East"},
    "Wuhan":     {"lat": 30.6, "lon": 114.3, "coastal": 0, "region": "Central"},
}

REGION_LABELS = {
    "Northwest": "Northwest", "Northeast Coast": "Northeast Coast",
    "East": "East", "Northeast": "Northeast", "South": "South",
    "Southwest": "Southwest", "Central": "Central",
}


def _extract_city(name: str) -> str:
    for city in CITY_FEATURES:
        if city in name:
            return city
    return name


def load_rows():
    """Return list of dicts: one per contest, with city, order, gold_cf, etc."""
    with open(MEDAL) as f:
        data = json.load(f)
    rows = []
    for c in data["contests"]:
        cid = c["contest_id"]
        order = CONTEST_ORDER.get(cid)
        if order is None:
            continue
        rows.append({
            "cid": cid, "name": c["contest_name"], "year": c["year"],
            "order": order,
            "is_ec_final": cid in EC_FINALS,
            "is_invitational": cid in INVITATIONAL,
            "is_regular": cid not in EC_FINALS and cid not in INVITATIONAL,
            "n_teams": c["official_solving_teams"],
            "city": CONTEST_CITY.get(cid, _extract_city(c["contest_name"])),
            "gold_cf": c["medal_bar_cf"]["gold"],
            "silver_cf": c["medal_bar_cf"]["silver"],
            "bronze_cf": c["medal_bar_cf"]["bronze"],
            "star_cf": c["medal_bar_cf"]["star"],
        })
    # Normalize order within each season
    by_year = defaultdict(list)
    for r in rows:
        by_year[r["year"]].append(r)
    for year, yr_rows in by_year.items():
        max_o = max(r["order"] for r in yr_rows)
        for r in yr_rows:
            r["norm_order"] = (r["order"] - 1) / max(1, max_o - 1)
    return rows


def bootstrap_ci(values, n_boot=10000, ci=95):
    """Bootstrap confidence interval for the mean."""
    vals = list(values)
    if len(vals) < 2:
        mean = statistics.mean(vals)
        return mean, mean, mean
    means = [statistics.mean(np.random.choice(vals, len(vals), replace=True))
             for _ in range(n_boot)]
    lo = np.percentile(means, (100 - ci) / 2)
    hi = np.percentile(means, 100 - (100 - ci) / 2)
    return statistics.mean(vals), lo, hi


def fit_ols(X, y):
    """OLS: beta = (X'X)^-1 X'y. Returns beta, y_pred, residuals, R²."""
    X = np.asarray(X, dtype=float)
    y = np.asarray(y, dtype=float)
    beta = np.linalg.inv(X.T @ X) @ X.T @ y
    y_pred = X @ beta
    resid = y - y_pred
    rss = np.sum(resid ** 2)
    tss = np.sum((y - np.mean(y)) ** 2)
    r2 = 1 - rss / tss if tss > 0 else 0.0
    return beta, y_pred, resid, r2


def loco_rmse(rows, feature_func):
    """Leave-one-contest-out RMSE for a linear model."""
    errors = []
    for i in range(len(rows)):
        train = [rows[j] for j in range(len(rows)) if j != i]
        test = rows[i]
        X_train = np.array([feature_func(r) for r in train])
        y_train = np.array([r["gold_cf"] for r in train])
        beta = np.linalg.inv(X_train.T @ X_train) @ X_train.T @ y_train
        pred = np.dot(feature_func(test), beta)
        errors.append(pred - test["gold_cf"])
    return math.sqrt(statistics.mean([e ** 2 for e in errors]))


def _city_prediction(rows, city, value_key, shrinkage=CITY_SHRINKAGE):
    """Predict a bar with a partially pooled city mean."""
    grand_mean = statistics.mean(r[value_key] for r in rows)
    city_values = [r[value_key] for r in rows if r["city"] == city]
    if not city_values:
        return grand_mean
    return (
        sum(city_values) + shrinkage * grand_mean
    ) / (len(city_values) + shrinkage)


def rolling_origin_metrics(rows, value_key, shrinkage=CITY_SHRINKAGE):
    """Evaluate later seasons using only strictly earlier regular regionals."""
    years = sorted({r["year"] for r in rows})
    errors = []
    correct_pairs = []
    for year in years[1:]:
        train = [r for r in rows if r["year"] < year]
        test = [r for r in rows if r["year"] == year]
        predictions = [
            _city_prediction(train, r["city"], value_key, shrinkage)
            for r in test
        ]
        errors.extend(
            prediction - row[value_key]
            for prediction, row in zip(predictions, test)
        )
        for i in range(len(test)):
            for j in range(i + 1, len(test)):
                actual_delta = test[i][value_key] - test[j][value_key]
                predicted_delta = predictions[i] - predictions[j]
                if actual_delta and predicted_delta:
                    correct_pairs.append(
                        (actual_delta > 0) == (predicted_delta > 0))

    return {
        "n": len(errors),
        "rmse": math.sqrt(statistics.mean(e ** 2 for e in errors)),
        "mae": statistics.mean(abs(e) for e in errors),
        "pairwise_accuracy": statistics.mean(correct_pairs),
        "n_pairs": len(correct_pairs),
    }


class Predictor:
    """Predict medal bars and rank regular ICPC Asia East contest choices.

    Usage
    -----
    >>> p = Predictor()
    >>> [r["city"] for r in p.recommend(REGIONALS_BY_YEAR[2026])[:3]]
    ['Shenyang', 'Hong Kong', 'Nanjing']
    """

    def __init__(self, rows=None, shrinkage=CITY_SHRINKAGE):
        self.rows = list(rows) if rows is not None else load_rows()
        self.regular = [r for r in self.rows if r["is_regular"]]
        self.shrinkage = shrinkage
        if len(self.regular) < 2:
            raise ValueError("at least two regular regional contests are required")

        self.grand_mean = statistics.mean(
            r["gold_cf"] for r in self.regular)

        by_city = defaultdict(list)
        for r in self.regular:
            by_city[r["city"]].append(r["gold_cf"])
        self.city_mean = {c: statistics.mean(v) for c, v in by_city.items()}
        self.city_n = {c: len(v) for c, v in by_city.items()}
        self.city_estimate = {
            city: _city_prediction(
                self.regular, city, "gold_cf", self.shrinkage)
            for city in by_city
        }
        self.city_sd = (
            statistics.stdev(self.city_mean.values())
            if len(self.city_mean) > 1 else 0
        )

        within_vars = []
        for vals in by_city.values():
            if len(vals) > 1:
                within_vars.append(statistics.variance(vals))
        self.within_sd = (
            math.sqrt(statistics.mean(within_vars)) if within_vars else 0
        )

        self.ec = [r for r in self.rows if r["is_ec_final"]]
        self.ec_mean = statistics.mean(r["gold_cf"] for r in self.ec)
        self.reg_mean = self.grand_mean
        self.ec_premium = self.ec_mean - self.reg_mean

        year_means = {}
        for r in self.regular:
            year_means.setdefault(r["year"], []).append(r["gold_cf"])
        year_means = {y: statistics.mean(v) for y, v in year_means.items()}

        reg_orders = np.array([r["norm_order"] for r in self.regular])
        reg_gold_dm = np.array([
            r["gold_cf"] - year_means[r["year"]] for r in self.regular
        ])
        self.order_slope, self.order_intercept = np.polyfit(reg_orders, reg_gold_dm, 1)

        years_arr = np.array([r["year"] for r in self.regular])
        gold_city_dm = np.array([
            r["gold_cf"] - self.city_mean.get(r["city"], self.grand_mean)
            for r in self.regular
        ])
        self.year_slope, _ = np.polyfit(years_arr - statistics.mean(years_arr), gold_city_dm, 1)

        silver_offsets = [
            r["gold_cf"] - r["silver_cf"] for r in self.regular
        ]
        bronze_offsets = [
            r["silver_cf"] - r["bronze_cf"] for r in self.regular
        ]
        self.gold_silver_gap = statistics.mean(silver_offsets)
        self.silver_bronze_gap = statistics.mean(bronze_offsets)
        self.gold_silver_gap_sd = statistics.stdev(silver_offsets)
        self.silver_bronze_gap_sd = statistics.stdev(bronze_offsets)

        self.validation = {
            tier: rolling_origin_metrics(
                self.regular, f"{tier}_cf", self.shrinkage)
            for tier in TIERS
        }

    def predict(self, city=None, year=2026, position=None, is_ec_final=False,
                n_teams=None):
        """Predict medal bars; year/order/team count are intentionally unused."""
        known = city is not None and city in self.city_mean
        n_contests = self.city_n.get(city, 0) if city else 0
        predictions = {}
        errors = {}
        for tier in TIERS:
            value_key = f"{tier}_cf"
            if is_ec_final:
                predictions[tier] = statistics.mean(
                    r[value_key] for r in self.ec)
            else:
                predictions[tier] = _city_prediction(
                    self.regular, city, value_key, self.shrinkage)
            errors[tier] = self.validation[tier]["rmse"]

        if is_ec_final:
            breakdown = [
                f"EC Final mean: {predictions['gold']:.0f} CF "
                f"(n={len(self.ec)}; city not used)"
            ]
            city_baseline = self.grand_mean
        else:
            city_baseline = predictions["gold"]
            if known:
                raw = self.city_mean[city]
                breakdown = [
                    f"regular-regional mean: {self.grand_mean:.0f} CF",
                    f"city ({city}): raw {raw:.0f} CF over n={n_contests}, "
                    f"shrunk to {city_baseline:.0f} CF",
                ]
            else:
                city_label = city if city else "unknown"
                breakdown = [
                    f"regular-regional mean: {self.grand_mean:.0f} CF",
                    f"city ({city_label}): no history; using regional mean",
                ]
            breakdown.append(
                "year/order/field size: excluded by forward validation")

        return {
            **{
                f"{tier}_{suffix}": round(
                    predictions[tier] + delta * errors[tier], 0)
                for tier in TIERS
                for suffix, delta in (("cf", 0), ("lo", -1), ("hi", 1))
            },
            "city_baseline": round(city_baseline, 0),
            "city_raw_mean": (
                round(self.city_mean[city], 0) if known else None
            ),
            "city_n_contests": n_contests,
            "city_is_known": known,
            "ec_final_premium": round(
                self.ec_premium if is_ec_final else 0, 0),
            "order_effect": 0,
            "prediction_sd": round(errors["gold"], 0),
            "prediction_rmse": round(errors["gold"], 0),
            "validation_n": self.validation["gold"]["n"],
            "breakdown": breakdown,
        }

    def recommend(self, cities, year=2026, target="gold"):
        """Return regular regional choices from easiest to hardest target bar."""
        if target not in TIERS:
            raise ValueError(f"target must be one of: {', '.join(TIERS)}")
        rows = []
        for city in cities:
            prediction = self.predict(city=city, year=year)
            prediction.update({
                "city": city,
                "year": year,
                "target": target,
                "target_cf": prediction[f"{target}_cf"],
                "target_lo": prediction[f"{target}_lo"],
                "target_hi": prediction[f"{target}_hi"],
            })
            rows.append(prediction)
        return sorted(rows, key=lambda r: (r["target_cf"], r["city"]))

    def print_prediction(self, **kwargs):
        """Pretty-print a prediction."""
        r = self.predict(**kwargs)
        city = kwargs.get("city", "unknown")
        year = kwargs.get("year", "?")
        event = "EC Final" if kwargs.get("is_ec_final") else "regular regional"
        print(f"{city}, {year} — {event}")
        for tier in TIERS:
            print(
                f"  {tier.capitalize():<6} {r[f'{tier}_cf']:>4.0f} CF  "
                f"[{r[f'{tier}_lo']:.0f}, {r[f'{tier}_hi']:.0f}] "
                "historical RMSE band"
            )
        print("\nBreakdown:")
        print("\n".join(f"  {line}" for line in r["breakdown"]))


def report():
    """Print the full analysis report + example predictions."""
    p = Predictor()
    rows = p.rows
    regular = p.regular
    ec = p.ec

    print("=" * 72)
    print("MEDAL CUTOFF PREDICTION: City + Temporal Order + Event Type")
    print(f"{len(rows)} East Asia contests (2022–2025), gold bar in CF points")
    print("=" * 72)

    # ---- 1. EC Final premium ----
    print("\n1. EVENT TYPE — the strongest signal")
    print("-" * 36)
    print(f"  EC Finals (n={len(ec)}):           mean gold = {p.ec_mean:.0f} CF")
    for r in ec:
        print(f"    {r['name']:<45} {r['gold_cf']:.0f} CF  ({r['year']})")
    print(f"  Regular regionals (n={len(regular)}): mean gold = {p.reg_mean:.0f} CF")
    inv_rows = [r for r in rows if r["is_invitational"]]
    if inv_rows:
        print(f"  Invitationals (n={len(inv_rows)}):    gold = {inv_rows[0]['gold_cf']:.0f} CF")
    print(f"  EC Final premium: {p.ec_premium:+.0f} CF")

    # ---- 2. City effect ----
    print("\n2. CITY EFFECT — regular regionals only")
    print("-" * 42)
    print(f"  Grand mean: {p.grand_mean:.0f} CF")
    print(f"  Between-city SD: {p.city_sd:.0f} CF")
    print(f"  Within-city SD:  {p.within_sd:.0f} CF")
    print(f"\n  {'City':<14} {'raw':>7} {'pooled':>8} {'n':>3}")
    print(f"  {'':-<38}")
    for city in sorted(p.city_estimate, key=p.city_estimate.get, reverse=True):
        n = p.city_n[city]
        print(
            f"  {city:<14} {p.city_mean[city]:>7.0f} "
            f"{p.city_estimate[city]:>8.0f} {n:>3}"
        )

    # ---- 3. Temporal order effect ----
    print("\n3. TEMPORAL ORDER — weak within-season effect")
    print("-" * 46)

    year_means = {}
    for r in regular:
        year_means.setdefault(r["year"], []).append(r["gold_cf"])
    year_means = {y: statistics.mean(v) for y, v in year_means.items()}

    print("  Regular regionals, season-adjusted (Δ from season mean):")
    by_pos = defaultdict(list)
    for r in regular:
        by_pos[r["order"]].append(r["gold_cf"] - year_means[r["year"]])
    for pos in sorted(by_pos):
        vals = by_pos[pos]
        mean, lo, hi = bootstrap_ci(vals)
        bar = "█" * max(1, int(abs(mean) / 10))
        sign = "+" if mean >= 0 else "-"
        print(f"  pos {pos}: {mean:>+5.0f} CF [{lo:+.0f}, {hi:+.0f}] "
              f"(n={len(vals)}) {sign}{bar}")

    print(f"\n  Order slope: {p.order_slope:.0f} CF from first→last (regular regionals)")
    print(f"  Year trend:  {p.year_slope:.0f} CF/year")

    # Per-season trends
    print("\n  Per-season trend (regular regionals):")
    by_year = defaultdict(list)
    for r in regular:
        by_year[r["year"]].append(r)
    for year in sorted(by_year):
        yr = sorted(by_year[year], key=lambda r: r["order"])
        if len(yr) >= 3:
            slope, _ = np.polyfit([r["order"] for r in yr],
                                  [r["gold_cf"] for r in yr], 1)
            r_yr = np.corrcoef([r["order"] for r in yr],
                               [r["gold_cf"] for r in yr])[0, 1]
            label = "← strongest" if abs(r_yr) > 0.5 else ""
            print(f"    {year}: {slope:+.0f} CF/position, r={r_yr:+.3f}  {label}")

    # ---- 4. Forward model comparison ----
    print("\n4. MODEL VALIDATION — train on earlier seasons only")
    print("-" * 51)
    pooled = p.validation["gold"]
    raw_city = rolling_origin_metrics(regular, "gold_cf", shrinkage=0)
    print(
        f"  raw city mean:          RMSE={raw_city['rmse']:.0f} CF, "
        f"pair ordering={raw_city['pairwise_accuracy']:.1%}"
    )
    print(
        f"  pooled city (shipped):  RMSE={pooled['rmse']:.0f} CF, "
        f"pair ordering={pooled['pairwise_accuracy']:.1%} "
        f"(n={pooled['n']}, {pooled['n_pairs']} pairs)"
    )

    # ---- 5. Silver/bronze gap stats ----
    print("\n5. SILVER & BRONZE BAR RELATIONSHIPS")
    print("-" * 37)
    print(f"  gold→silver gap:  {p.gold_silver_gap:.0f} ± {p.gold_silver_gap_sd:.0f} CF")
    print(f"  silver→bronze gap: {p.silver_bronze_gap:.0f} ± {p.silver_bronze_gap_sd:.0f} CF")

    # ---- 6. Known city table ----
    print("\n6. KNOWN CITY BASELINES")
    print("-" * 22)
    print(f"  {'City':<14} {'pooled':>8} {'n':>3}  {'raw SD':>7}")
    print(f"  {'':-<39}")
    for city in sorted(p.city_estimate, key=p.city_estimate.get, reverse=True):
        n = p.city_n[city]
        if n >= 2:
            vals = [r["gold_cf"] for r in regular if r["city"] == city]
            sd = statistics.stdev(vals)
        else:
            sd = float("nan")
        sd_str = f"{sd:.0f}" if not math.isnan(sd) else "?"
        print(
            f"  {city:<14} {p.city_estimate[city]:>8.0f} "
            f"{n:>3}  {sd_str:>7}"
        )

    # ---- 7. Example predictions ----
    print("\n7. EXAMPLE PREDICTIONS")
    print("-" * 21)

    examples = [
        {"city": "Hangzhou", "year": 2026, "position": None, "is_ec_final": False,
         "desc": "Hangzhou 2026 (three prior regular regionals)"},
        {"city": "Wuhan", "year": 2026, "position": None, "is_ec_final": False,
         "desc": "Wuhan 2026 (one prior regular regional, partially pooled)"},
        {"city": None, "year": 2026, "position": None, "is_ec_final": False,
         "desc": "New city 2026 (no city history)"},
        {"city": "Shanghai", "year": 2026, "position": None, "is_ec_final": True,
         "desc": "EC Final 2026 in Shanghai (championship event)"},
    ]
    for ex in examples:
        r = p.predict(city=ex["city"], year=ex["year"], position=ex["position"],
                      is_ec_final=ex["is_ec_final"])
        print(f"\n  {ex['desc']}:")
        print(f"    gold   = {r['gold_cf']:.0f}  [{r['gold_lo']:.0f} – {r['gold_hi']:.0f}] CF")
        print(f"    silver = {r['silver_cf']:.0f}  [{r['silver_lo']:.0f} – {r['silver_hi']:.0f}] CF")
        print(f"    bronze = {r['bronze_cf']:.0f}  [{r['bronze_lo']:.0f} – {r['bronze_hi']:.0f}] CF")
        print(f"    ±{r['prediction_rmse']:.0f} CF historical gold RMSE")

    # ---- 8. Summary ----
    print("\n" + "=" * 72)
    print("SUMMARY")
    print("=" * 72)
    print(f"""
    1. EC FINAL is the dominant predictor: +{p.ec_premium:.0f} CF harder
       than regular regionals.

    2. CITY is useful only with partial pooling. The shipped model adds one
       grand-mean pseudo-contest so one-off hosts do not get full weight.

    3. TEMPORAL ORDER is descriptive only: its per-season pattern is
       inconsistent, so it is excluded from future recommendations.

    4. FORWARD VALIDATION: pooled-city RMSE={pooled['rmse']:.0f} CF and
       pairwise ordering={pooled['pairwise_accuracy']:.1%} over {pooled['n']}
       later-season contests.

    5. FIELD SIZE is not used; travel, quotas, eligibility, and registration
       limits are outside this model and still matter to the final choice.
    """)


def print_recommendations(predictor, cities, year, target):
    rows = predictor.recommend(cities, year=year, target=target)
    metric = predictor.validation[target]
    print(f"ASIA EAST {year} REGIONAL CHOOSER — target: {target.upper()}")
    print("Lower predicted bar means a historically softer medal cutoff.")
    if year == 2026 and tuple(cities) == REGIONALS_BY_YEAR[2026]:
        print(
            "Official city list checked 2026-07-27; dates/order were not "
            "published, so no temporal adjustment is used."
        )
    print()
    print(f"{'#':>2}  {'City':<12} {'bar':>7} {'RMSE band':>17} {'history':>9}")
    print("-" * 54)
    for rank, row in enumerate(rows, start=1):
        history = (
            f"n={row['city_n_contests']}"
            if row["city_is_known"] else "new city"
        )
        print(
            f"{rank:>2}  {row['city']:<12} {row['target_cf']:>5.0f} CF "
            f"[{row['target_lo']:.0f}, {row['target_hi']:.0f}] "
            f"{history:>9}"
        )

    leaders = ", ".join(r["city"] for r in rows[:3])
    print(
        f"\nPoint-estimate leaders: {leaders}. The {metric['rmse']:.0f}-CF "
        f"historical RMSE band comes from {metric['n']} forward predictions; "
        "overlapping bands mean the exact order is uncertain."
    )
    print(
        "Not modeled: travel/cost, school quotas, eligibility, registration "
        "limits, or the strength of this year's applicant pool."
    )


def main():
    parser = argparse.ArgumentParser(
        description="Predict medal bars and compare Asia East regionals.")
    parser.add_argument("--year", type=int, default=2026)
    parser.add_argument("--target", choices=TIERS, default="gold")
    parser.add_argument(
        "--cities", nargs="+",
        help="candidate host cities; quote names such as 'Hong Kong'")
    parser.add_argument("--city", help="show one city's full medal prediction")
    parser.add_argument("--ec-final", action="store_true")
    parser.add_argument("--report", action="store_true")
    args = parser.parse_args()

    if args.report:
        report()
        return

    predictor = Predictor()
    if args.city:
        predictor.print_prediction(
            city=args.city, year=args.year, is_ec_final=args.ec_final)
        return

    cities = args.cities or REGIONALS_BY_YEAR.get(args.year)
    if not cities:
        parser.error(
            f"no built-in regional list for {args.year}; pass --cities")
    print_recommendations(predictor, cities, args.year, args.target)


if __name__ == "__main__":
    main()
