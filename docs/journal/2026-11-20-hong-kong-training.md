# Training for the Hong Kong regional

The team asked for a plan through HK using original training advice, the recorded dossiers and the sibling Mostafa sheet. The [plan](../reports/team-r3/hong-kong-2027.md) covers 20 November through the official 9–10 January event. It schedules six one-computer mocks and a taper, with ten hours per member assumed in full weeks. Unseen-set checks account for members' earlier line-ups.

Matched SuperJ6's 30–40% unaided practice heuristic to the corrected individual CF fits. The starting buckets are Dedi 2000, Tamir 1800 and Erdene 2100/2200. Compared Mostafa's prescription with three OI tasks and their 23 trainee records. Forišek's 2007 training paper supplies the proof drill and his 2009 IRT paper supplies measurement context.

Reviewed the 16-contest synthesis and member dossiers alongside the newer official Shenyang appearance. Its raw board rank was 94 of 416 with five ACs. Among the official six-solvers with the same five, eight added A and seven added F. Both prior HK seat-replay cutoffs had three solves. These support training early penalty and the first reachable extra AC together. Corrected the HK dates in Status. Changes are confined to coaching documentation and navigation.

## Reproduce the numeric inputs

From the repository root, with sibling `../mostafa_sheet` at `a64d81d`:

```bash
python3 - <<'PY'
import csv
import json
import math
from collections import Counter

def read_json(path):
    with open(path) as f:
        return json.load(f)

members = read_json("output/team_r3_cf.json")["members"]
for name, row in members.items():
    theta, slope, n = row["level_rated_recent"]
    print(name, n, [round(theta + slope * math.log((1-p)/p)) for p in (.4, .3)])

boards = read_json("data/xcpcio_51st_regionals.json")
board = next(b for b in boards if b["board_link"].endswith("/shenyang"))
rows = board["standings"]
team = next(r for r in rows if r["team_name"] == "NUM-R^3")
def accepted(r):
    return {label for label, p in r["problems"].items() if p["solved"]}
ours = accepted(team)
extra = Counter()
for row in rows:
    difference = accepted(row) - ours
    if row["official"] and ours <= accepted(row) and len(difference) == 1:
        extra.update(difference)
print(team["rank"], len(rows), sorted(ours), extra)

with open("data/ec_online/regional_teams.csv") as f:
    for r in csv.DictReader(f):
        if r["site"] == "hongkong" and (r["season"], r["official_rank"]) in {("2024","37"), ("2025","32")}:
            print(r["season"], r["official_rank"], r["solved"], r["penalty_minutes"])

with open("../mostafa_sheet/submissions.csv") as f:
    logs = list(csv.DictReader(f))
for task in ("ioi 13-dreaming", "ioi 12-city", "ioi 13-robots"):
    print(task, Counter((r["Status"], r["By yourself?"].upper()) for r in logs if r["Problem"].strip().lower() == task))
PY
```
