# Competitive programming training methods for HK

The team asked for more research on competitive programming training. The [research note](../reports/team-r3/cp-training-evidence.md) compares CF training histories, competing approaches to hints, an ICPC reading drill, two coaches' strategy guides, and two classroom studies on mixed practice. The [HK plan](../reports/team-r3/hong-kong-2027.md) incorporates a three-mock trial within the ten-hour week.

Checked all shipped-rated 2300–2500 problems in the 14 virtuals, two official online rounds and Shenyang onsite. Seven of 16 were solved. The two submitted misses were 2661 J and Shenyang F. The seven misses without a recorded submission were 1485 K, 2524 I, 1799 E, 1051 B, 2693 A, 2661 I and Shenyang A. The six virtual non-submissions also agree with the individual dossiers. Harbin has no shipped ratings. The records do not capture thinking time.

## Reproduce the team result

```bash
python3 - <<'PY'
import json
from collections import Counter
from pathlib import Path

def load(path):
    return json.loads(Path(path).read_text())

ratings = {(p["contest_id"], p["problem_label"]): p["difficulty_cf"]
           for p in load("output/problem_ratings_hier.json")}
counts = Counter()
def record(cid, label, solved, wrong):
    rating = ratings.get((cid, label))
    if rating is None or not 2300 <= rating <= 2500:
        return
    result = "AC" if solved else "submitted miss" if wrong else "no submission"
    counts[result] += 1
    print(cid, label, rating, result)

for contest in load("output/team_r3_participations.json"):
    for p in contest["problems"]:
        record(contest["contest_id"], p["label"], p["ours"], contest["wrong"].get(p["label"], 0))

sy = next(b for b in load("data/xcpcio_51st_regionals.json") if b["board_link"].endswith("/shenyang"))
team = next(r for r in sy["standings"] if r["team_name"] == "NUM-R^3")
for p in sy["problems"]:
    label = p["problem_label"]
    cell = team["problems"].get(label, {})
    record(sy["contest_id"], label, cell.get("solved", False), cell.get("wrong_attempts", 0))
print(counts)
PY
```
