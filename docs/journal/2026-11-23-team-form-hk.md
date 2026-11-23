# NUM-R^3 contest performances and Hong Kong projections

Through November 21, the 15 virtuals averaged 2463 CF-equivalent points and the three officials averaged 2267. Each contest has equal weight. The combined average is 2430, or 2347 after deducting 100 from each virtual. Official performances rose from 2156 to 2319 to 2327. Successive five-virtual averages were 2463, 2527 and 2399.

| Performance basis | Reviewed linked position | Gold / silver / bronze | All linked position | Gold / silver / bronze |
|---|---:|---|---:|---|
| Officials | 24/85 | 5 / 36 / 46% | 25/97 | 9 / 39 / 39% |
| Virtuals | 14/85 | 24 / 48 / 24% | 14/97 | 37 / 41 / 19% |
| Virtuals minus 100 | 18/85 | 11 / 45 / 36% | 19/97 | 19 / 45 / 29% |
| Combined | 14/85 | 19 / 48 / 28% | 14/97 | 30 / 43 / 22% |
| Combined with virtual deduction | 18/85 | 10 / 44 / 38% | 19/97 | 17 / 44 / 31% |

The virtual calculator inserts the unassisted score on the whole board, excluding our practice account. The official results use the shipped event performance. To translate a mean performance into HK odds, find its equivalent rank on each 2026 official online qualifier and take their geometric mean. Feed this into the repository's 2024–25 field-relative HK medal model with each field's own cutoffs. The rating-to-rank translation is approximate. The November 22 registration snapshot has 112 Reviewed and 126 total teams. Unlinked teams have unknown strength. The positions above compare qualifier-equivalent strengths among linked teams only.

Virtuals in time order (contest ID, rounded CF performance):

| August–September | Early October | October 16–November 21 |
|---|---|---|
| 1485 · 2363 | 1051 · 2433 | 2661 · 2205 |
| 1794 · 2653 | 1071 · 2834 | 2575 · 2397 |
| 2513 · 2596 | 1053 · 2500 | 4593 · 2398 |
| 2524 · 2394 | 1096 · 2468 | 4607 · 2542 |
| 1799 · 2310 | 2693 · 2399 | 4694 · 2451 |

Used the coaching dossiers' unassisted reconstructions for 1794 (5/394) and 4694 (5/631). Official contest IDs are 4071, 4113 and the 2026 Shenyang onsite board.

## Reproduce

Run the following Python from the repository root with the project environment.

```python
from pathlib import Path
import json
import numpy as np
from arch_a.elo import performance_rating
from arch_b import hk_field_2026 as hk

def read(path):
    return json.loads(Path(path).read_text(encoding="utf8"))

html = Path("output/virtual_calc.html").read_text(encoding="utf8")
calc = json.JSONDecoder().raw_decode(html.split("const DATA = ", 1)[1])[0]
boards = {b["contest_id"]: b["teams"] for b in calc["contests"]}
scale = calc["to_cf"]
axis = scale["lo"] + np.arange(len(scale["ys"])) * scale["step"]
scores = []
for row in read("output/team_r3_participations.json"):
    cid = row["contest_id"]
    if row["kind"] == "virtual":
        solved, penalty = {1794: (5, 394), 4694: (5, 631)}.get(
            cid, (len(row["solved"]), row["penalty_min"][0]))
        rivals = [t for t in boards[cid] if t["name"].casefold() != "team_r3"]
        rank = 1 + sum((-t["solved"], (t["penalty"] + 30) // 60) < (-solved, penalty)
                       for t in rivals)
        rho = performance_rating(rank, [t["theta"] for t in rivals])
        score = np.interp(rho, axis, scale["ys"])
        scores.append((row["date"], cid, score))
virtual = [s for date, cid, s in sorted(scores)]
official = [next(t["performance"] for t in boards[cid] if t["name"] == "NUM-R^3")
            for cid in (4071, 4113, -162528714534630)]
print([(date, cid, round(s)) for date, cid, s in sorted(scores)], official)
reg = read("output/hk_field_2026.json")
assert reg["file"].endswith("20261122.xlsx")
data = hk.og.load()
past = hk.hk.link_hk(data, hk.og.online_strengths(data["online_teams"]))
weights = hk.fit([r for r in past if r["season"] in hk.om.HK_SEASONS and r["x"] is not None], True)
qualifiers = [np.array([t["performance"] for t in boards[cid] if t.get("event")])
              for cid in (4071, 4113)]
def project(score):
    x = -np.mean([np.log(1 + np.sum(q > score)) for q in qualifiers])
    output = []
    for statuses in ({"Reviewed"}, {"Reviewed", "Pending"}):
        field = [t for t in reg["teams"] if t["status"] in statuses]
        line = hk.lines([t["x"] for t in field])
        pos = 1 + sum(t["team"] != "NUM-R^3" and t["x"] > x for t in field)
        p = hk.predict(weights, x, line)
        output.append((len(field), pos, [round(p[k]*100,1) for k in ("gold","silver","bronze")]))
    return output

for label, sample in (("official", official), ("virtual", virtual), ("virtual -100", np.subtract(virtual,100)),
                      ("combined", virtual+official), ("combined -100", list(np.subtract(virtual,100))+official)):
    print(label, np.mean(sample), project(np.mean(sample)))
for sample in (virtual[:5],virtual[5:10],virtual[10:],virtual[5:9],virtual[-3:]):
    print("block",np.mean(sample))
```
