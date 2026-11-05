"""Reading aid for the NUM-R^3 coach dossiers: one contest's problems and our runs.

    python3 scripts/team_r3_digest.py 4607            # problem table + our submissions
    python3 scripts/team_r3_digest.py 4607 E --code   # also print every attempt at E, with diffs

Minutes are from the virtual start, which is recovered from the TEAM_R3 row on
standings_all.json (AC submit time minus the board's solve time).  Field solve
counts are official teams only (standings_official.json).
"""
import difflib
import json
import math
import statistics
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
D = ROOT / "data" / "team_r3"
# Medal counts (gold, silver, bronze) by contest: board counts for the 2026 regionals (details.md
# 2026-10-26), data/ec_online/regional_teams.csv (rule 10/20/30) for the 2022 regionals,
# output/ccpc_icpc_medals.json for the 11th CCPC stations.  Elsewhere the top 10% stand in for gold.
# 2022 regionals: 35 / 70 / 105 at every site (details.md 2026-10-05 medal diagnosis); their lines
# and our rank use the XCPCIO official rows in data/ec_online/regional_teams.csv, because QOJ's
# "official" 2022 rows are a larger set (Shenyang 1004 vs 708).
MEDALS = {4607: (32, 64, 96), 4593: (41, 82, 123), 1051: (35, 70, 105), 1071: (35, 70, 105),
          1053: (35, 70, 105), 1096: (35, 70, 105), 2575: (26, 50, 76), 2693: (26, 52, 78),
          2661: (25, 50, 75)}
ONSITE_2022 = {1051: "xian", 1071: "hangzhou", 1053: "jinan", 1096: "shenyang"}
# CCPC stations: the onsite official field from the cached XCPCIO board (QOJ's "official" rows
# are not the onsite field there: 343 vs 260 at Harbin).
CCPC = {2575: "ccpc_11th_harbin", 2693: "ccpc_11th_jinan", 2661: "ccpc_11th_zhengzhou"}
ECF_LINE = 75  # 2026 EC-Final rule estimate, plausible 70-80 (details.md 2026-10-01)


def xcpcio_rows(name):
    """Official rows of a cached XCPCIO board, in the QOJ standings format."""
    c = ROOT / "data" / "ec_online_cache" / "xcpcio" / name
    config = json.loads((c / "config.json").read_text())
    label = {str(p["id"]): p["label"] for p in config["problems"]}
    teams = json.loads((c / "team.json").read_text())
    teams = teams.values() if isinstance(teams, dict) else teams
    official = {str(t["id"]) for t in teams if "official" in (t.get("group") or [])}
    unit = 1000 if (config.get("options") or {}).get("submission_timestamp_unit") == "millisecond" else 1
    rows = {t: {"total_solved": 0, "penalty_seconds": 0, "problems": {}} for t in official}
    for r in sorted(json.loads((c / "run.json").read_text()), key=lambda r: r["timestamp"]):
        t = str(r["team_id"])
        if t not in rows or r["status"] in ("COMPILATION_ERROR", "PENDING", "FROZEN", "UNKNOWN"):
            continue
        cell = rows[t]["problems"].setdefault(label[str(r["problem_id"])],
                                              {"solved": False, "time_seconds": 0, "wrong_attempts": 0})
        if cell["solved"]:
            continue
        if r["status"] in ("ACCEPTED", "CORRECT"):
            cell.update(solved=True, time_seconds=r["timestamp"] // unit)
            rows[t]["total_solved"] += 1
            rows[t]["penalty_seconds"] += cell["time_seconds"] + config.get("penalty", 1200) * cell["wrong_attempts"]
        else:
            cell["wrong_attempts"] += 1
    return list(rows.values())


def main():
    cid, rest = int(sys.argv[1]), sys.argv[2:]
    want = [a for a in rest if not a.startswith("--")]
    c = D / "contests" / str(cid)
    dash = json.loads((c / "dashboard.json").read_text())
    labels = {p["problem_id"]: p["problem_label"] for p in dash["problems"]}
    official = json.loads((c / "standings_official.json").read_text())
    xc = {4593: "/icpc/51st/xian", 4607: "/icpc/51st/chengdu"}.get(cid)
    if xc:  # 2026 regionals: the onsite official field from XCPCIO, not QOJ's Universal Cup field
        board = next(b for b in json.loads((D / "boards" / "xcpcio_51st.json").read_text()) if b["board_link"] == xc)
        official = [r for r in board["standings"] if r.get("official")]
    if cid in CCPC:
        official = xcpcio_rows(CCPC[cid])
    ours = next((r for r in json.loads((c / "standings_all.json").read_text())
                 if r["team_id"] == "TEAM_R3"), None)
    if cid in (4071, 4113):  # 2026 official rounds were played on another account: use the NUM-R^3 row
        ours = next(r for r in official if r["team_name"] == "NUM-R^3")
    part = {p["contest_id"]: p for p in json.loads((ROOT / "output" / "team_r3_participations.json").read_text())}
    meta = {p["label"]: p for p in part.get(cid, {}).get("problems", [])}
    subs = sorted((s for s in json.loads((D / "submissions.json").read_text()) if s["contest_id"] == cid),
                  key=lambda s: s["submit_time"])
    t = lambda s: datetime.fromisoformat(s["submit_time"]).timestamp()

    start = None
    if ours:
        acs = [t(s) - ours["problems"][labels[s["problem_id"]]]["time_seconds"] for s in subs
               if s["in_contest"] and s["verdict"] == "AC ✓" and labels[s["problem_id"]] in ours["problems"]
               and ours["problems"][labels[s["problem_id"]]]["solved"]]
        start = min(acs) if acs else None
    p = part.get(cid, {})
    print(f"{cid} {dash['title']}\nours: solved {p.get('solved')} penalty {p.get('penalty_min')} "
          f"rank {p.get('rank')} / {p.get('board_teams')} ({p.get('board')}); field = {len(official)} official teams")
    official.sort(key=lambda r: (-r["total_solved"], r["penalty_seconds"]))
    ranked = official  # rows that define the lines and our rank
    if cid in ONSITE_2022:
        import csv
        with open(ROOT / "data" / "ec_online" / "regional_teams.csv", encoding="utf-8") as f:
            ranked = sorted(({"total_solved": int(r["solved"]), "penalty_seconds": int(r["penalty_minutes"]) * 60}
                             for r in csv.DictReader(f) if r["season"] == "2022"
                             and r["site"] == ONSITE_2022[cid] and r["official"] == "1"),
                            key=lambda r: (-r["total_solved"], r["penalty_seconds"]))
        print(f"lines/rank from XCPCIO 2022 {ONSITE_2022[cid]}: {len(ranked)} official teams "
              f"(problem columns below still use QOJ's {len(official)})")
    medals = MEDALS.get(cid)
    marks = ([("gold", medals[0]), ("silver", medals[0] + medals[1]),
              ("bronze", medals[0] + medals[1] + medals[2])] if medals
             else [(f"top {q}%", math.ceil(q / 100 * len(official))) for q in (10, 20, 30)])
    if medals and cid not in CCPC:  # ICPC regionals only
        marks.append(("EC-Final ~75", ECF_LINE))
    print("lines: " + "; ".join(f"{name} #{k} {ranked[k - 1]['total_solved']}/{ranked[k - 1]['penalty_seconds'] // 60}"
                                for name, k in sorted(marks, key=lambda m: m[1]) if k <= len(ranked)))
    if ours:
        k = 1 + sum(1 for r in ranked if (r["total_solved"], -r["penalty_seconds"])
                    > (ours["total_solved"], -ours["penalty_seconds"]))
        print(f"us on this field: #{k} ({ours['total_solved']}/{ours['penalty_seconds'] // 60})")
    top = official[:marks[0][1]]
    print(f"\nL  name                              field  cf     ours           member        {marks[0][0]} median")
    for q in dash["problems"]:
        L = q["problem_label"]
        n = sum(1 for r in official if r["problems"].get(L, {}).get("solved"))
        m = meta.get(L, {})
        o = (ours or {}).get("problems", {}).get(L)
        st = "-" if not o else (f"AC {o['time_seconds'] // 60}' +{o['wrong_attempts']}" if o["solved"]
                                else f"fail ({o['wrong_attempts']} tries)")
        cf = m.get("difficulty_cf")
        ts = [r["problems"][L]["time_seconds"] // 60 for r in top if r["problems"].get(L, {}).get("solved")]
        med = f"{statistics.median(ts):.0f}' ({len(ts)}/{len(top)})" if ts else ""
        print(f"{L:2} {q['problem_name'][:33]:33} {n:5}  {cf if cf else '':6} {st:14} {(m.get('member') or ''):13} {med}")
    print("\nsubmissions (minute from virtual start; * = practice/upsolve)")
    for s in subs:
        mn = f"{(t(s) - start) / 60:6.1f}" if start else s["submit_time"][5:16]
        print(f"  {s['submission_id']} {mn} {labels.get(s['problem_id'], '?')} {s['verdict']:4} "
              f"{s['size']:>6} {s['language']}{'' if s['in_contest'] else ' *'}")
    if "--code" in rest:
        for L in want:
            prev = None
            for s in (s for s in subs if labels.get(s["problem_id"]) == L):
                code = (D / "code" / f"{s['submission_id']}.txt").read_text(errors="replace")
                print(f"\n===== {L} {s['submission_id']} {s['verdict']} {s['submit_time']}")
                if prev is None:
                    print(code)
                else:
                    print("".join(difflib.unified_diff(prev.splitlines(True), code.splitlines(True), n=2)))
                prev = code


if __name__ == "__main__":
    main()
