"""Reading aid for an onsite regional of NUM-R^3: our runs against the official field.

    python3 scripts/team_r3_onsite.py /icpc/51st/shenyang
    python3 scripts/team_r3_onsite.py /icpc/51st/shenyang --at 5:597 --at 6:960

Reads the live XCPCIO board (config, team, run) and prints the medal and EC-Final lines,
every run of ours by minute, our rank after each solve, the field's solve sets and a
per-problem table.  Only official teams count.  Penalty is the board's: seconds summed,
20 minutes per wrong run before the AC.  --at SOLVED:MINUTES gives the rank a score would have.
"""
import argparse
import statistics
from collections import Counter

from fetch_xcpcio_standings import DATA_URL, _fetch_json

ECF_LINE = 81  # 2026 EC-Final qualifying rank, 77-84 (ecfinal_cutoff_2026.py, details.md 2026-11-16)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("board_link")
    ap.add_argument("--team", default="NUM-R^3")
    ap.add_argument("--at", action="append", default=[], metavar="SOLVED:MINUTES")
    args = ap.parse_args()
    config, teams, runs = (_fetch_json(f"{DATA_URL}{args.board_link}/{f}.json") for f in ("config", "team", "run"))
    label = {str(p["id"]): p["label"] for p in config["problems"]}
    unit = 1000 if config["options"].get("submission_timestamp_unit") == "millisecond" else 1
    cells = {t["id"]: {} for t in teams if "official" in t["group"]}  # team -> label -> [ac second, wrong]
    us = next(t["id"] for t in teams if t["name"] == args.team)
    ours = []
    for r in sorted(runs, key=lambda r: r["timestamp"]):
        if r["team_id"] not in cells or r["status"] == "COMPILATION_ERROR":
            continue
        cell = cells[r["team_id"]].setdefault(label[str(r["problem_id"])], [None, 0])
        if r["team_id"] == us:
            ours.append((r["timestamp"] / unit, label[str(r["problem_id"])], r["status"]))
        if cell[0] is None:
            if r["status"] == "ACCEPTED":
                cell[0] = r["timestamp"] / unit
            else:
                cell[1] += 1

    def score(team, until=float("inf")):
        ac = [(s, w) for s, w in cells[team].values() if s is not None and s <= until]
        return len(ac), sum(s + config["penalty"] * w for s, w in ac)

    def rank(solved, penalty, until=float("inf")):
        return 1 + sum(1 for t in cells if t != us and (score(t, until)[0] > solved or
                       (score(t, until)[0] == solved and score(t, until)[1] < penalty)))

    final = {t: score(t) for t in cells}
    order = sorted(cells, key=lambda t: (-final[t][0], final[t][1]))
    medal = config["medal"]["official"]
    gold, silver, bronze = medal["gold"], medal["gold"] + medal["silver"], sum(medal.values())
    tiers = {"gold": order[:gold], "silver": order[gold:silver], "bronze": order[silver:bronze]}
    sets = {t: "".join(sorted(k for k, c in cells[t].items() if c[0] is not None)) for t in cells}

    print(f"{len(cells)} official teams, medals {gold}/{silver}/{bronze}")
    lines = [("last gold", gold), ("EC-Final estimate", ECF_LINE), ("last silver", silver), ("last bronze", bronze)]
    for name, i in sorted(lines + [("us", order.index(us) + 1)], key=lambda x: x[1]):
        s, p = final[order[i - 1]]
        print(f"  #{i:<4} {s} / {p / 60:6.1f}  {sets[order[i - 1]]:<12} {name}")
    for a in args.at:
        s, m = map(int, a.split(":"))
        print(f"  {s} / {m} would be #{rank(s, m * 60)}")

    print("\nour runs (minute, problem, verdict, rank after an AC)")
    for sec, lab, status in ours:
        after = f"#{rank(*score(us, sec), until=sec)}" if status == "ACCEPTED" else ""
        print(f"  {sec / 60:6.1f} {lab} {status} {after}")

    print("\nsolve sets by count")
    for k in sorted({s for s, _ in final.values()}, reverse=True):
        group = [t for t in order if final[t][0] == k]
        print(f"  {k}: {len(group)} teams, #{order.index(group[0]) + 1}-#{order.index(group[-1]) + 1}  "
              + ", ".join(f"{s} x{n}" for s, n in Counter(sets[t] for t in group).most_common(4)))

    print("\nprob solved/tried first-try  median minute gold/silver/bronze (solvers)  last hour  ours")
    for lab in sorted(label.values()):
        ac = [c[lab] for c in cells.values() if lab in c and c[lab][0] is not None]
        tried = sum(1 for c in cells.values() if lab in c)
        med = []
        for group in tiers.values():
            v = [cells[t][lab][0] / 60 for t in group if lab in cells[t] and cells[t][lab][0] is not None]
            med.append(f"{statistics.median(v):5.0f} ({len(v)})" if v else "    - (0)")
        mine = cells[us].get(lab)
        mine = "" if mine is None else (f"{mine[0] / 60:.1f} +{mine[1]}" if mine[0] is not None else f"- +{mine[1]}")
        first = f"{sum(1 for _, w in ac if w == 0) / len(ac):4.0%}" if ac else "   -"
        late = sum(1 for s, _ in ac if s >= config["end_time"] / 1000 - config["start_time"] / 1000 - 3600)
        print(f"  {lab}  {len(ac):3}/{tried:<3}  {first}   {'  '.join(med)}  {late:3}  {mine}")


if __name__ == "__main__":
    main()
