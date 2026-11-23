"""NUM-R^3's form: does practice predict onsite, and what to expect in Hong Kong?

Every NUM-R^3 2026 result (the two official online rounds, the virtuals in
``output/team_r3_participations.json``, the CCPC Changchun virtual and Shenyang
onsite) is put on the performance scale of ``scripts/hk_shenyang_rank.py``:

* official online rounds and Shenyang: the team's own fitted row;
* 51st-season regional virtuals: between the official teams at ranks k-1 and k;
* CCPC Changchun: that board's ``a + b log(rank)`` map;
* older virtuals: the scoreline inserted into the fitted board, the mean of the
  performances of the rows just above and below it.

**Backtest.** Only results before Shenyang (2026-11-15) predict Shenyang, by
several rules; each prediction is read as a Shenyang official rank and
compared with the actual #87.

**Hong Kong.** Candidate form estimates are placed in the 11-22 field: the
field-relative Hong Kong model (``hk_shenyang_rank.hk_model``) and a
rank-based Monte Carlo. In the Monte Carlo every team's true strength is drawn
around its 2026 mean with the pooled within-team spread of single results
divided by sqrt(n), the day's result adds that spread again, and gold is the
top ``round(10% of teams)``. Teams with no 2026 result draw from the linked
field. Online-only teams can be given extra uncertainty.

    python3 scripts/hk_form_backtest.py

Writes ``output/hk_form_backtest.md``.
"""

import json
import math
import sys
from datetime import date
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import hk_shenyang_rank as hs  # noqa: E402

FILE = ROOT / "data" / "icpc_hk_macau_public_teams_20261122.xlsx"
OUT = ROOT / "output" / "hk_form_backtest.md"
SHENYANG_DAY = date(2026, 11, 15)
SOURCES = {"tagged_official.json": "tagged.json", "ucup_s4.json": "ucup_s4.json",
           "petroz_2022_2026.json": "petroz_2022_2026.json"}
CITY = {4593: "Xi'an", 4607: "Chengdu", 4694: "Wuhan"}
WUHAN_COUNTED = 53  # 5 / 631 without B, which was finished with outside help (2026-11-22 Wuhan dossier)
CHANGCHUN = ("CCPC Changchun", 29, date(2026, 11, 8))  # 7 / 683 at 3:15, two members (2026-11-08)
HALF_LIFE = 14  # days, for the recency-weighted means
DISCOUNT = 100
SIMS = 20000


def inserted_perf(perf, contest, solved, penalty_s):
    """Mean performance of the fitted rows just above and below a scoreline on the board."""
    rows = sorted(((s["total_solved"] or 0, s["penalty_seconds"] or 0, perf[(contest["contest_id"], i)])
                   for i, s in enumerate(contest["standings"]) if (contest["contest_id"], i) in perf),
                  key=lambda t: (-t[0], t[1]))
    k = sum(1 for s, p, _ in rows if s > solved or (s == solved and p < penalty_s))  # rows ahead of it
    near = [rows[j][2] for j in (k - 1, k) if 0 <= j < len(rows)]
    return float(np.mean(near))


def num_results(c):
    """[(label, date or None, kind, perf)] for every NUM-R^3 2026 result."""
    perf = c.perf
    boards = {}
    out = []
    for p in json.load(open(ROOT / "output" / "team_r3_participations.json")):
        cid, d = p["contest_id"], p["date"] and date.fromisoformat(p["date"])
        if p["kind"] == "official":
            name = {4071: "Online 1", 4113: "Online 2"}[cid]
            out.append((f"EC {name} (official)", None, "online", next(v for k, v, _ in c.me["apps"] if k == name)))
        elif cid in CITY:
            k = WUHAN_COUNTED if cid == 4694 else p["rank"][0]
            out.append((f"{CITY[cid]} 2026 virtual #{k}", d, "virtual", c.virtual_perf(CITY[cid], k)))
        else:
            src = SOURCES[p["board"]]
            if src not in boards:
                boards[src] = {x["contest_id"]: x for x in json.load(open(ROOT / "data" / src))}
            contest = boards[src][cid]
            out.append((f"{contest['year']} {contest['contest_name'][:32]} virtual", d, "virtual",
                        inserted_perf(perf, contest, len(p["solved"]), 60 * p["penalty_min"][0])))
    board, k, d = CHANGCHUN
    out.append((f"{board} virtual #{k} (2 members, 3:15)", d, "virtual", c.virtual_perf(board, k)))
    out.append(("Shenyang 2026 onsite #87", SHENYANG_DAY, "onsite",
                next(v for k, v, _ in c.me["apps"] if k == "Shenyang")))
    return out


def weighted(vs, on):
    w = [0.5 ** ((on - d).days / HALF_LIFE) for d, _ in vs]
    return float(np.average([p for _, p in vs], weights=w))


def simulate(c, me_perf, me_sd, sd_app, reviewed_only, online_extra=1.0, seed=0):
    """P(gold) for a team of true strength ~ N(me_perf, me_sd) in the Hong Kong field."""
    rng = np.random.default_rng(seed)
    field = [r for r in c.reg if r["team"] != c.me["team"] and (r["status"] == "Reviewed" or not reviewed_only)]
    known = [r for r in field if r["strength"] is not None]
    pool = np.array([r["strength"] for r in known])
    mu = np.array([r["strength"] for r in known])
    sd = np.array([sd_app / math.sqrt(len(r["apps"]))
                   * (online_extra if r["onsite"] is None else 1.0) for r in known])
    n_unknown = len(field) - len(known)
    gold = round(0.1 * (len(field) + 1))
    hits = 0
    for _ in range(SIMS):
        true = rng.normal(mu, sd)
        unk = rng.choice(pool, n_unknown) + rng.normal(0, sd_app, n_unknown)
        day = np.concatenate([true + rng.normal(0, sd_app, len(mu)), unk])
        me = rng.normal(me_perf, me_sd) + rng.normal(0, sd_app)
        hits += 1 + int((day > me).sum()) <= gold
    return hits / SIMS, gold, len(field) + 1


def main():
    c = hs.build(FILE)
    *_, chances = hs.hk_model(c, FILE)
    res = num_results(c)
    actual = next(p for _, _, k, p in res if k == "onsite")
    online = [p for _, _, k, p in res if k == "online"]
    virt = [(d, p) for _, d, k, p in res if k == "virtual"]
    before = [(d, p) for d, p in virt if d < SHENYANG_DAY]
    after = [(d, p) for d, p in virt if d > SHENYANG_DAY]

    # Pooled within-team spread of single 2026 results (registrants with >= 2 results).
    resid = [p - np.mean([q for _, q, _ in r["apps"]]) for r in c.reg if len(r["apps"]) >= 2
             for _, p, _ in r["apps"]]
    dof = sum(len(r["apps"]) - 1 for r in c.reg if len(r["apps"]) >= 2)
    sd_app = math.sqrt(sum(x * x for x in resid) / dof)

    L = ["# NUM-R^3: does practice predict onsite, and what to expect in Hong Kong", "",
         f"Field: `{FILE.name}`. Scale: `hk_shenyang_rank` (hier_time performances). "
         f"Single-result spread within a team (pooled, {dof} dof): **{sd_app:.0f}**.", "",
         "## Every 2026 result", "", "| result | date | perf | Shenyang-eq. |", "|---|---|---|---|"]
    for label, d, _, p in sorted(res, key=lambda t: (t[1] or date(2026, 9, 1))):
        L.append(f"| {label} | {d or '09'} | {p:.0f} | {c.sy_rank(p)} |")

    rules = [("Online rounds (official) mean", np.mean(online)),
             ("All virtuals before Shenyang, mean", np.mean([p for _, p in before])),
             (f"… −{DISCOUNT}", np.mean([p for _, p in before]) - DISCOUNT),
             (f"Recency-weighted virtuals (half-life {HALF_LIFE} d)", weighted(before, SHENYANG_DAY)),
             (f"… −{DISCOUNT}", weighted(before, SHENYANG_DAY) - DISCOUNT),
             ("Last 3 virtuals (Xi'an, Chengdu, Changchun) mean", np.mean([p for _, p in sorted(before)[-3:]])),
             ("Chengdu virtual repeated", next(p for l, _, _, p in res if l.startswith("Chengdu"))),
             ("Online + all virtuals, mean", np.mean(online + [p for _, p in before]))]
    L += ["", f"## Backtest: predicting Shenyang (actual #87, perf {actual:.0f}) from results before 11-15", "",
          "| rule | predicted perf | predicted Shenyang rank | error (perf) |", "|---|---|---|---|"]
    for name, p in rules:
        L.append(f"| {name} | {p:.0f} | {c.sy_rank(p)} | {p - actual:+.0f} |")
    gap = actual - weighted(before, SHENYANG_DAY)
    L += ["", f"Measured virtual → onsite gap (Shenyang − recency-weighted virtuals): **{gap:+.0f}** "
          f"(one onsite result; its own uncertainty is about ±{sd_app:.0f})."]

    wuhan = after[0][1]
    shift = wuhan - weighted(before, date(2026, 11, 21))
    cands = [("Shenyang onsite repeated", actual),
             ("Shenyang + change in virtual form since (Wuhan − earlier weighted virtuals)", actual + shift),
             ("All virtuals (incl. Wuhan) recency-weighted, + measured gap", weighted(virt, date(2027, 1, 9)) + gap),
             (f"All virtuals recency-weighted −{DISCOUNT}", weighted(virt, date(2027, 1, 9)) - DISCOUNT),
             ("Chengdu virtual repeated", rules[6][1]),
             ("Mean of the 15 QOJ virtuals (Changchun left out)",
              np.mean([p for l, _, k, p in res if k == "virtual" and not l.startswith("CCPC Changchun")]))]
    L += ["", "## Hong Kong: candidate form estimates", "",
          f"Monte Carlo: gold = top round(10%) of the attending field; NUM-R^3's own strength sd {sd_app / math.sqrt(3):.0f} "
          f"(= spread/√3). 'online ×2' doubles the strength uncertainty of the {sum(1 for r in c.reg if r['strength'] is not None and r['onsite'] is None)} "
          "online-only registrants.", "",
          "| estimate | perf | Shenyang-eq. | HK position | model gold | MC gold: Reviewed | MC: all | MC Reviewed, online ×2 |",
          "|---|---|---|---|---|---|---|---|"]
    for name, p in cands:
        pos = 1 + sum(1 for r in c.ranked if r["strength"] > p and r["team"] != c.me["team"])
        _, pr = chances(p)
        mc = [simulate(c, p, sd_app / math.sqrt(3), sd_app, rev, extra)
              for rev, extra in ((True, 1.0), (False, 1.0), (True, 2.0))]
        L.append(f"| {name} | {p:.0f} | {c.sy_rank(p)} | {pos} | {100 * pr['gold']:.0f}% | "
                 + " | ".join(f"{100 * g:.0f}% (top {k} of {n})" for g, k, n in mc) + " |")
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
