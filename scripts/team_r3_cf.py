#!/usr/bin/env python3
"""NUM-R^3 members on Codeforces: rounds, virtuals, practice.

    python3 scripts/team_r3_cf.py            # analyse the cached API data
    python3 scripts/team_r3_cf.py --fetch    # refresh the cache first (public API, ~2 s/call)

Cache: data/team_r3/cf/ (user.rating, user.status per handle, problemset.problems,
contest.list). Output: output/team_r3_cf.json (one record per timed individual
participation plus per-member aggregates) and a text report on stdout.

Only individual participations count; team entries (earlier teams on ICPC
mirrors and gyms) are listed as excluded. Gym contests have no problem ratings,
so they are counted but left out of the rating-based measures.
"""
import collections
import json
import math
import statistics
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
D = ROOT / "data" / "team_r3" / "cf"
OUT = ROOT / "output" / "team_r3_cf.json"
HANDLES = {"Dedibeat": "Dedi", "t4_4": "Tamir", "erdene1231": "Erdene", "Munkh-Erdene.B": "Erdene"}
RECENT = datetime(2025, 11, 5, tzinfo=timezone.utc).timestamp()  # "last 12 months"
BANDS = [(0, 1200), (1300, 1600), (1700, 2000), (2100, 2400), (2500, 4000)]
NOT_A_TRY = {"OK", "COMPILATION_ERROR", "SKIPPED"}
FAMILIES = {"graphs/trees": {"graphs", "trees", "dfs and similar", "dsu", "shortest paths", "graph matchings", "flows"},
            "combinatorics/probability": {"combinatorics", "probabilities"},
            "number theory/bits": {"number theory", "bitmasks", "chinese remainder theorem"},
            "constructive/greedy": {"constructive algorithms", "greedy"},
            "data structures": {"data structures", "binary search", "two pointers", "divide and conquer"},
            "dp": {"dp"},
            "strings": {"strings", "hashing", "string suffix structures"},
            "implementation": {"implementation", "brute force"},
            "interactive": {"interactive"},
            "geometry": {"geometry"}}


def fetch():
    def get(url, path):
        with urllib.request.urlopen(url, timeout=180) as r:
            data = r.read()
        assert json.loads(data)["status"] == "OK", url
        path.write_bytes(data)
        time.sleep(2.2)
    D.mkdir(parents=True, exist_ok=True)
    for h in HANDLES:
        get(f"https://codeforces.com/api/user.rating?handle={h}", D / f"rating_{h}.json")
        get(f"https://codeforces.com/api/user.status?handle={h}", D / f"status_{h}.json")
    get("https://codeforces.com/api/problemset.problems", D / "problemset.json")
    get("https://codeforces.com/api/contest.list?gym=false", D / "contest_list.json")


def division(name):
    if "Div. 1 + Div. 2" in name or "Div. 1+2" in name:
        return "Div1+2"
    if "Educational" in name:
        return "Edu"
    for k in ("Div. 1", "Div. 2", "Div. 3", "Div. 4"):
        if k in name:
            return k.replace(". ", "")
    return "Global/other"


def fit(obs):
    """MLE of P(solve) = 1 / (1 + exp((r - theta) / s)) over (rating, solved) pairs (grid search)."""
    best = None
    for s in range(100, 701, 20):
        for theta in range(600, 3201, 10):
            ll = loglik(obs, theta, s)
            if best is None or ll > best[0]:
                best = (ll, theta, s)
    return best[1], best[2]


def p_solve(theta, s, r):
    return 1 / (1 + math.exp((r - theta) / s))


def loglik(obs, theta, s):
    return sum(-math.log1p(math.exp(-(theta - r) / s)) if y else -math.log1p(math.exp((theta - r) / s))
               for r, y in obs)


def half_year(t):
    d = datetime.fromtimestamp(t, timezone.utc)
    return f"{d.year}H{1 + (d.month - 1) // 6}"


def main():
    if "--fetch" in sys.argv:
        fetch()
    probs = json.loads((D / "problemset.json").read_text())["result"]["problems"]
    prob = {(p["contestId"], p["index"]): p for p in probs}
    by_contest = collections.defaultdict(list)
    for p in probs:
        by_contest[p["contestId"]].append(p)
    contests = {c["id"]: c for c in json.loads((D / "contest_list.json").read_text())["result"]}

    parts, excluded, practice, history = [], [], collections.defaultdict(list), {}
    for h, member in HANDLES.items():
        subs = json.loads((D / f"status_{h}.json").read_text())["result"]
        history[h] = json.loads((D / f"rating_{h}.json").read_text())["result"]
        rated = {r["contestId"]: r for r in history[h]}
        groups = collections.defaultdict(list)
        for s in subs:
            a = s["author"]
            if a["participantType"] == "PRACTICE":
                practice[member].append((h, s))
                continue
            key = (s["contestId"], a["participantType"], a.get("startTimeSeconds"))
            if len(a["members"]) > 1 or a.get("teamName"):
                excluded.append((h, key, a.get("teamName")))
                continue
            if "April Fools" in contests.get(s["contestId"], {}).get("name", ""):
                excluded.append((h, key, "April Fools (joke problems)"))
                continue
            groups[key].append(s)
        for (cid, ptype, start), ss in groups.items():
            c = contests.get(cid, {})
            gym = cid >= 100000
            kind = ("virtual" if ptype == "VIRTUAL" else "unofficial" if ptype == "OUT_OF_COMPETITION"
                    else "rated" if cid in rated else "unrated")
            listed = [p["index"] for p in by_contest.get(cid, [])] or sorted({s["problem"]["index"] for s in ss})
            rec = {"handle": h, "member": member, "contest_id": cid, "name": c.get("name", f"gym {cid}"),
                   "division": "gym" if gym else division(c.get("name", "")), "rules": c.get("type"),
                   "kind": kind, "start": start, "duration_min": c.get("durationSeconds", 0) // 60 or None,
                   "complete_problem_list": bool(by_contest.get(cid)), "problems": []}
            if cid in rated:
                r = rated[cid]
                rec.update(rank=r["rank"], old=r["oldRating"], new=r["newRating"])
            for L in listed:
                mine = sorted((s for s in ss if s["problem"]["index"] == L), key=lambda s: s["creationTimeSeconds"])
                meta = prob.get((cid, L), mine[0]["problem"] if mine else {})
                ac = next((s for s in mine if s["verdict"] == "OK"), None)
                before = [s for s in mine if ac is None or s["creationTimeSeconds"] < ac["creationTimeSeconds"]]
                tries = [s for s in before if s["verdict"] not in NOT_A_TRY]
                # failed system test: CF rules, live participation, a final-tests verdict that is not OK
                fst = [s["id"] for s in mine if rec["rules"] == "CF" and ptype != "VIRTUAL" and not ac
                       and s.get("testset") == "TESTS" and s["verdict"] not in NOT_A_TRY]
                rec["problems"].append({
                    "index": L, "rating": meta.get("rating"), "tags": meta.get("tags", []),
                    "solved": bool(ac), "ac_min": ac["relativeTimeSeconds"] // 60 if ac else None,
                    "ac_id": ac["id"] if ac else None, "tries": len(tries),
                    "try_ids": [s["id"] for s in tries],
                    "test1": [s["id"] for s in tries if s.get("passedTestCount") == 0],
                    "verdicts": [s["verdict"] for s in tries], "fst": fst,
                    "hacked": [s["id"] for s in mine if s["verdict"] == "CHALLENGED"],
                    "last_sub_min": mine[-1]["relativeTimeSeconds"] // 60 if mine else None})
            parts.append(rec)
    parts.sort(key=lambda r: (r["member"], r["start"] or 0))

    # Upsolving: attempted in a timed participation, not solved there, later AC in practice.
    practice_ac, practice_ac_time = collections.defaultdict(dict), collections.defaultdict(dict)
    for member, lst in practice.items():
        for h, s in sorted(lst, key=lambda x: x[1]["creationTimeSeconds"]):
            if s["verdict"] == "OK":
                k = (s["contestId"], s["problem"]["index"])
                practice_ac[member].setdefault(k, s["id"])
                practice_ac_time[member].setdefault(k, (s["id"], s["creationTimeSeconds"]))

    report = {}
    for member in ("Dedi", "Tamir", "Erdene"):
        P = [r for r in parts if r["member"] == member]
        usable = [r for r in P if r["division"] != "gym" and r["complete_problem_list"]]

        def obs(pred):
            return [(q["rating"], q["solved"]) for r in usable if pred(r) for q in r["problems"] if q["rating"]]

        m = {"participations": collections.Counter(r["kind"] for r in P),
             "gyms": sorted({r["contest_id"] for r in P if r["division"] == "gym"})}
        # Level = problem rating with a 50% in-contest solve rate. CF problem ratings are defined on the
        # user-rating scale, so this is comparable to a rating. Out-of-competition entries are not full
        # efforts (they stop after the problems they care about), so levels use rated rounds only.
        for name, pred in (("level_rated", lambda r: r["kind"] == "rated"),
                           ("level_rated_recent", lambda r: r["kind"] == "rated" and r["start"] >= RECENT),
                           ("level_virtual", lambda r: r["kind"] == "virtual"),
                           ("level_unofficial", lambda r: r["kind"] == "unofficial")):
            o = obs(pred)
            m[name] = fit(o) + (len(o),) if len(o) >= 30 else None
        s_fix = (m["level_rated"] or fit(obs(lambda r: r["kind"] in ("rated", "virtual"))))[1]

        # Virtual vs rated, time-matched: shared offset delta, one theta per half-year with both kinds.
        per = collections.defaultdict(list)
        for r in usable:
            if r["kind"] in ("rated", "virtual"):
                per[half_year(r["start"])] += [(q["rating"], q["solved"], r["kind"] == "virtual")
                                               for q in r["problems"] if q["rating"]]
        both = [h for h, o in per.items() if any(x[2] for x in o) and any(not x[2] for x in o)]

        def profile(delta):
            return sum(max(loglik([(rr + (delta if v else 0), y) for rr, y, v in per[h]], t, s_fix)
                           for t in range(600, 3201, 20)) for h in both)
        grid = {dl: profile(dl) for dl in range(-700, 701, 10)}
        best = max(grid, key=grid.get)
        inside = [dl for dl, v in grid.items() if v >= grid[best] - 1.92]
        nv = sum(x[2] for h in both for x in per[h])
        m["virtual_offset"] = {"delta": best, "ci95": (min(inside), max(inside)), "half_years": sorted(both),
                               "n_virtual": nv, "n_rated": sum(len(per[h]) for h in both) - nv,
                               "at_grid_edge": min(inside) == -700 or max(inside) == 700}

        # Solve rate by band, rated rounds only.
        rated_obs = obs(lambda r: r["kind"] == "rated")
        m["band_rated"] = {f"{lo}-{hi}": (sum(y for rr, y in rated_obs if lo <= rr <= hi),
                                          sum(1 for rr, y in rated_obs if lo <= rr <= hi)) for lo, hi in BANDS}

        # Tags: observed vs expected solves within 500 of the level of that half-year (rated + virtual).
        theta_h = {h: max(range(600, 3201, 10), key=lambda t: loglik([(rr, y) for rr, y, v in o], t, s_fix))
                   for h, o in per.items()}
        tag = collections.defaultdict(lambda: [0, 0.0, 0.0, 0])
        for r in usable:
            if r["kind"] not in ("rated", "virtual"):
                continue
            th = theta_h[half_year(r["start"])]
            for q in r["problems"]:
                if q["rating"] is None or abs(q["rating"] - th) > 500:
                    continue
                pe = p_solve(th, s_fix, q["rating"])
                for t in q["tags"]:
                    a = tag[t]
                    a[0] += q["solved"]; a[1] += pe; a[2] += pe * (1 - pe); a[3] += 1
        # Topic families: each problem counted once if it carries any tag of the family.
        fam = collections.defaultdict(lambda: [0, 0.0, 0.0, 0])
        for r in usable:
            if r["kind"] not in ("rated", "virtual"):
                continue
            th = theta_h[half_year(r["start"])]
            for q in r["problems"]:
                if q["rating"] is None or abs(q["rating"] - th) > 500:
                    continue
                pe = p_solve(th, s_fix, q["rating"])
                for f, ts in FAMILIES.items():
                    if ts & set(q["tags"]):
                        a = fam[f]
                        a[0] += q["solved"]; a[1] += pe; a[2] += pe * (1 - pe); a[3] += 1
        m["families"] = {f: {"n": a[3], "solved": a[0], "expected": round(a[1], 1),
                             "z": round((a[0] - a[1]) / math.sqrt(a[2]), 2) if a[2] else None}
                         for f, a in fam.items()}
        m["theta_by_half_year"] = dict(sorted(theta_h.items()))
        m["tags"] = {t: {"n": a[3], "solved": a[0], "expected": round(a[1], 1),
                         "z": round((a[0] - a[1]) / math.sqrt(a[2]), 2) if a[2] else None}
                     for t, a in sorted(tag.items(), key=lambda kv: -kv[1][3])}
        exposure = collections.Counter(); exp_solved = collections.Counter()
        for r in P:
            for q in r["problems"]:
                for t in q["tags"]:
                    exposure[t] += 1; exp_solved[t] += q["solved"]
        m["exposure"] = {t: (exp_solved[t], exposure[t]) for t in
                         ("geometry", "flows", "graph matchings", "probabilities", "hashing", "interactive",
                          "fft", "string suffix structures", "matrices", "chinese remainder theorem")}

        # Accuracy (all timed individual participations; PARTIAL verdicts of IOI-style contests left out)
        solved = [(r, q) for r in P for q in r["problems"] if q["solved"]]
        tried = [(r, q) for r in P for q in r["problems"]]
        rej = [(r, q, i, v) for r, q in tried for i, v in zip(q["try_ids"], q["verdicts"]) if v != "PARTIAL"]
        t1 = collections.Counter(); tot = collections.Counter()
        for r, q, i, v in rej:
            k = f"{r['rules']}-{'virtual' if r['kind'] == 'virtual' else 'live'}"
            tot[k] += 1; t1[k] += i in q["test1"]
        m["accuracy"] = {
            "solved": len(solved), "first_try": sum(q["tries"] == 0 for _, q in solved),
            "wrong_before_ac": sum(q["tries"] for _, q in solved),
            "wrong_on_unsolved": sum(q["tries"] for _, q in tried if not q["solved"]),
            "rejections": len(rej), "test1": sum(t1.values()),
            "test1_by_rules": {k: (t1[k], tot[k]) for k in sorted(tot)},
            "verdicts": dict(collections.Counter(v for *_, v in rej).most_common()),
            "idleness_on_test1": [(r["contest_id"], q["index"], i) for r, q, i, v in rej
                                  if v == "IDLENESS_LIMIT_EXCEEDED" and i in q["test1"]],
            "fst": [(r["contest_id"], q["index"], q["fst"][-1]) for r, q in tried if q["fst"]],
            "hacked": [(r["contest_id"], q["index"], i) for r, q in tried for i in q["hacked"]],
            "live_cf_rounds": sum(1 for r in P if r["rules"] == "CF" and r["kind"] in ("rated", "unofficial", "unrated"))}
        m["first_try_by_band"] = {f"{lo}-{hi}": (sum(q["tries"] == 0 for q in xs), len(xs)) for lo, hi in BANDS
                                  for xs in [[q for _, q in solved if q["rating"] and lo <= q["rating"] <= hi]]}
        m["long_chains"] = sorted(((r["contest_id"], q["index"], q["rating"], q["tries"], q["solved"]) for r, q in tried
                                   if q["tries"] >= 5), key=lambda x: -x[3])

        # Speed: minutes since the previous AC in the same participation, by band
        gaps = collections.defaultdict(list)
        for r in P:
            prev = 0
            for q in sorted((q for q in r["problems"] if q["solved"]), key=lambda q: q["ac_min"]):
                for lo, hi in BANDS:
                    if q["rating"] and lo <= q["rating"] <= hi:
                        gaps[f"{lo}-{hi}"].append(q["ac_min"] - prev)
                prev = q["ac_min"]
        m["solve_gap_median"] = {k: (statistics.median(v), len(v)) for k, v in sorted(gaps.items())}

        # End of contest: rated rounds and virtuals with >= 45 min and no submission at the end, and the
        # cheapest unsolved problem still had >= 30% solve chance at the rated level.
        th_r, s_r = m["level_rated"][:2]
        ends = []
        for r in usable:
            if r["kind"] not in ("rated", "virtual") or not r["duration_min"]:
                continue
            last = max((q["last_sub_min"] for q in r["problems"] if q["last_sub_min"] is not None), default=None)
            nxt = min((q["rating"] for q in r["problems"] if not q["solved"] and q["rating"]), default=None)
            if last is not None:
                ends.append((r["duration_min"] - last, nxt, r["contest_id"], r["kind"]))
        silent = [e for e in ends if e[0] >= 45]
        reach = [e for e in silent if e[1] and p_solve(th_r, s_r, e[1]) >= 0.3]
        m["silent_end"] = {"participations": len(ends), "median_min": statistics.median(e[0] for e in ends),
                           "silent_ge_45": len(silent), "next_problem_reachable": len(reach),
                           "examples": sorted(reach, key=lambda e: -e[0])[:5]}

        # Upsolving on CF
        unsolved_tried = {(r["contest_id"], q["index"]) for r in P for q in r["problems"] if not q["solved"] and q["try_ids"]}
        nxt_unsolved = []
        for r in usable:
            if r["kind"] == "rated":
                un = [q for q in r["problems"] if not q["solved"] and q["rating"]]
                if un:
                    nxt_unsolved.append((r["contest_id"], min(un, key=lambda q: q["rating"])["index"]))
        m["upsolve"] = {"attempted_unsolved": len(unsolved_tried),
                        "attempted_unsolved_later_ac": sum(k in practice_ac[member] for k in unsolved_tried),
                        "next_unsolved_rated": len(nxt_unsolved),
                        "next_unsolved_later_ac": sum(k in practice_ac[member] for k in nxt_unsolved)}

        # Practice: unique ACs per half-year; 2026 ratings; share from contests the member took part in
        took = {r["contest_id"] for r in P}
        vol = collections.Counter(); y26 = []
        for k, (sid, t) in practice_ac_time[member].items():
            vol[half_year(t)] += 1
            if t >= datetime(2026, 1, 1, tzinfo=timezone.utc).timestamp():
                y26.append(k)
        rs = sorted(prob[k]["rating"] for k in y26 if prob.get(k, {}).get("rating"))
        m["practice"] = {"unique_ac_by_half_year": dict(sorted(vol.items())),
                         "2026_unique_ac": len(y26), "2026_from_own_contests": sum(k[0] in took for k in y26),
                         "2026_rating_quartiles": (rs[len(rs) // 4], rs[len(rs) // 2], rs[3 * len(rs) // 4]) if rs else None}

        # Compiler: share of submissions on the 32-bit GCC 7 (no __int128, slow 64-bit arithmetic)
        langs = collections.defaultdict(collections.Counter)
        for h, mm in HANDLES.items():
            if mm == member:
                for sub in json.loads((D / f"status_{h}.json").read_text())["result"]:
                    y = datetime.fromtimestamp(sub["creationTimeSeconds"], timezone.utc).year
                    langs[y]["32-bit" if "-32" in sub["programmingLanguage"] else "other"] += 1
        m["compiler_32bit_by_year"] = {y: (c["32-bit"], sum(c.values())) for y, c in sorted(langs.items())}
        m["rating"] = {h: {"rounds": len(history[h]), "current": history[h][-1]["newRating"] if history[h] else None,
                           "max": max((x["newRating"] for x in history[h]), default=None),
                           "last_round": datetime.fromtimestamp(history[h][-1]["ratingUpdateTimeSeconds"], timezone.utc).date().isoformat() if history[h] else None}
                       for h, mm in HANDLES.items() if mm == member}
        report[member] = m

    OUT.write_text(json.dumps({"built_from": "data/team_r3/cf (Codeforces public API)",
                               "participations": parts, "members": report,
                               "excluded_team_entries": sorted({(h, k[0], k[1], t) for h, k, t in excluded})},
                              ensure_ascii=False, indent=1, default=list))

    for member, m in report.items():
        print(f"\n=== {member}")
        for k in ("rating", "participations", "gyms", "level_rated", "level_rated_recent", "level_virtual",
                  "level_unofficial", "virtual_offset", "theta_by_half_year", "band_rated", "first_try_by_band",
                  "solve_gap_median", "accuracy", "long_chains", "silent_end", "upsolve", "practice", "exposure", "families",
                  "compiler_32bit_by_year"):
            print(f"{k}: {m[k]}")
        print("tags (n >= 8):")
        for t, v in m["tags"].items():
            if v["n"] >= 8:
                print(f"  {t:28} n={v['n']:3} solved={v['solved']:3} expected={v['expected']:5} z={v['z']}")


if __name__ == "__main__":
    main()
