#!/usr/bin/env python3
"""First-pass table of NUM-R^3's 2026 official and virtual participations.

    python3 scripts/team_r3_participations.py

Reads what scripts/fetch_team_r3.py stored in data/team_r3/ (submissions,
dashboards, statements/tutorials), the member attribution
data/team_r3/members_solved.csv (from ~/Documents/team_members_solved.ods), the
boards already on disk, and output/problem_ratings_calibrated.json. Writes
output/team_r3_participations.json and .md.

* Official: the 2026 EC online rounds 4071 / 4113 were played on PTA-issued
  accounts, so they come from the NUM-R^3 row of the stored board, not from
  TEAM_R3 submissions (TEAM_R3 has only 28-byte test runs on 4071).
* Virtual: every other contest where TEAM_R3 has in-contest submissions
  (QOJ's <sup>#</sup> marker). TEAM_R3 has QOJ Training Mode on, so its own
  virtual row cannot be read. The start time is unknown, so the penalty is
  bounded instead of guessed: the start is no later than the first in-contest
  submission and no earlier than 5 h before the last accepted one. The rank
  range is taken over that interval against the official board.
"""

import csv
import datetime
import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEAM = ROOT / "data" / "team_r3"
OUT = ROOT / "output" / "team_r3_participations"
OFFICIAL = {4071: "NUM-R^3", 4113: "NUM-R^3"}
NOT_A_PARTICIPATION = {4071}  # TEAM_R3's in-contest runs there are 28-byte tests
DURATION = 5 * 3600
PENALTY = 20 * 60
XCPCIO = {4593: "/icpc/51st/xian", 4607: "/icpc/51st/chengdu"}
# first file holding the contest wins: official-only copies before full boards
BOARD_FILES = ["tagged_official.json", "tagged.json", "petroz_2022_2026.json",
               "ucup_s4.json", "ucup_s3.json"]


def load_boards(ids):
    boards = {}
    for name in BOARD_FILES:
        for c in json.loads((ROOT / "data" / name).read_text()):
            cid = int(c["contest_id"])
            if cid in ids and cid not in boards:
                boards[cid] = (name, c["standings"])
    for c in json.loads((TEAM / "boards" / "xcpcio_51st.json").read_text()):
        cid = next(k for k, v in XCPCIO.items() if v == c["board_link"])
        boards[cid] = ("xcpcio " + c["board_link"],
                       [r for r in c["standings"] if r["official"]])
    return boards


def rank_of(rows, solved, penalty):
    return 1 + sum(r["total_solved"] > solved or
                   (r["total_solved"] == solved and r["penalty_seconds"] < penalty) for r in rows)


def ts(x):
    return datetime.datetime.fromisoformat(x["submit_time"]).timestamp()


def virtual(subs):
    """Solved labels, wrong tries before AC, and the penalty interval."""
    subs = sorted(subs, key=ts)
    first = ts(subs[0])
    solved, wrong = {}, defaultdict(int)
    for x in subs:
        lab = x["label"]
        if lab in solved:
            continue
        if x["score"] is not None and x["score"] >= x["full_score"]:
            solved[lab] = ts(x)
        elif x["verdict"] != "Compile Error":
            wrong[lab] += 1
    if not solved:
        return solved, wrong, 0, 0
    last = max(solved.values())

    def pen(start):
        return sum(t - start + PENALTY * wrong[lab] for lab, t in solved.items())
    return solved, wrong, pen(first), pen(max(last - DURATION, first - DURATION))


def main():
    subs = json.loads((TEAM / "submissions.json").read_text())
    dashes = {int(p.name): json.loads((p / "dashboard.json").read_text())
              for p in (TEAM / "contests").iterdir() if (p / "dashboard.json").exists()}
    label = {(cid, p["problem_id"]): p["problem_label"]
             for cid, d in dashes.items() for p in d["problems"]}
    for x in subs:
        x["label"] = label.get((x["contest_id"], x["problem_id"]))
    by_contest = defaultdict(list)
    for x in subs:
        if x["contest_id"]:
            by_contest[x["contest_id"]].append(x)

    who = defaultdict(dict)
    with open(TEAM / "members_solved.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            cid = int(re.search(r"\((\d+)\)", r["Contest:"]).group(1))
            lab = r["Problem"].strip()
            who[cid][lab] = (who[cid].get(lab, "") + " / " if lab in who[cid] else "") + r["Member solved"].strip()
            if r["Additional info"].strip():
                who[cid][lab] += f" [{r['Additional info'].strip()}]"

    ratings = defaultdict(dict)
    for p in json.loads((ROOT / "output" / "problem_ratings_calibrated.json").read_text()):
        ratings[int(p["contest_id"])][p["problem_label"]] = p["difficulty_cf"]

    played = {cid for cid, xs in by_contest.items()
              if any(x["in_contest"] for x in xs) and cid not in NOT_A_PARTICIPATION}
    ids = played | set(OFFICIAL) | set(who)
    boards = load_boards(ids)

    report = []
    for cid in sorted(ids, key=lambda c: min((ts(x) for x in by_contest[c] if x["in_contest"]),
                                             default=0)):
        dash = dashes.get(cid, {})
        src, rows = boards.get(cid, (None, []))
        e = {"contest_id": cid, "title": dash.get("title"), "board": src, "board_teams": len(rows),
             "upsolved": sorted({x["label"] for x in by_contest[cid] if not x["in_contest"]
                                 and x["score"] is not None and x["score"] >= x["full_score"]})}
        if cid in OFFICIAL:
            row = next(r for r in rows if r["team_name"] == OFFICIAL[cid])
            e.update(kind="official", date=None, solved=sorted(
                lab for lab, c in row["problems"].items() if c["solved"]),
                wrong={lab: c["wrong_attempts"] for lab, c in row["problems"].items()
                       if c["wrong_attempts"]},
                penalty_min=[row["penalty_seconds"] // 60] * 2, rank=[row["rank"]] * 2)
        else:
            ins = [x for x in by_contest[cid] if x["in_contest"]]
            solved, wrong, lo, hi = virtual(ins)
            e.update(kind="virtual",
                     date=datetime.datetime.fromtimestamp(min(map(ts, ins))).date().isoformat(),
                     solved=sorted(solved), wrong=dict(wrong),
                     penalty_min=[int(lo // 60), int(hi // 60)],
                     rank=[rank_of(rows, len(solved), lo), rank_of(rows, len(solved), hi)]
                     if rows else None)
        cnt = defaultdict(int)
        for r in rows:
            for lab, c in r["problems"].items():
                cnt[lab] += c["solved"]
        e["problems"] = [{
            "label": p["problem_label"], "name": p["problem_name"],
            "board_solves": cnt.get(p["problem_label"], 0),
            "difficulty_cf": ratings[cid].get(p["problem_label"]),
            "ours": p["problem_label"] in e["solved"],
            "member": who[cid].get(p["problem_label"]),
            "statement": (TEAM / "contests" / str(cid) / "statements" /
                          f"{p['problem_label']}.txt").exists(),
        } for p in dash.get("problems", [])]
        e["sheet_only"] = sorted(set(who[cid]) - set(e["solved"]))
        e["solved_not_in_sheet"] = sorted(set(e["solved"]) - set(who[cid])) if cid in who else None
        e["tutorial"] = [a["label"] for a in dash.get("attachments", [])
                         if re.search(r"tutorial|editorial|solution|题解", a["label"], re.I)]
        report.append(e)

    OUT.with_suffix(".json").write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n")
    md = ["# NUM-R^3 participations (TEAM_R3 virtuals + 2026 official online)", "",
          "| contest | kind | date | solved | penalty (min) | rank on board | board |",
          "|---|---|---|---|---|---|---|"]
    for e in report:
        pen, rk = e["penalty_min"], e["rank"]
        md.append(f"| {e['contest_id']} {e['title']} | {e['kind']} | {e['date'] or ''} | "
                  f"{len(e['solved'])} ({' '.join(e['solved'])}) | "
                  f"{pen[0] if pen[0] == pen[1] else f'{pen[0]}–{pen[1]}'} | "
                  f"{'' if rk is None else rk[0] if rk[0] == rk[1] else f'{rk[0]}–{rk[1]}'}"
                  f" / {e['board_teams']} | {e['board']} |")
    md += ["", "Per-problem detail, member attribution and data gaps are in the .json."]
    OUT.with_suffix(".md").write_text("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
