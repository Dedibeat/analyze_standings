# Fresh CF problems and QOJ upsolving before HK

The team proposed CF 2300–2500 for fresh ideas and QOJ for upsolving. The [HK plan](../reports/team-r3/hong-kong-2027.md) assigns one of the two weekly 75-minute CF sessions to the shared stretch problem. The other uses the member's personal band. The existing two-hour regional upsolve and five-hour mock fit the same ten-hour weekly budget with a 30-minute debrief.

The November cache gives 43 distinct 2026 CF practice ACs in the inclusive band for Dedi, four for Tamir and eight for Erdene across both handles. These are first practice ACs per contest/index, following the member report. Prior exposure, hint use and abandoned reads are unknown. The two linked CF starters have no contest submission or same-title problem submission on any of the four cached handles. Replace either if a teammate recognizes it. The QOJ starter 1799 E had no recorded contest attempt and is fitted at 2324.5.

## Reproduce from the repository root

```bash
python3 - <<'PY'
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

cache = Path("data/team_r3/cf")
for handles in [("Dedibeat",), ("t4_4",), ("erdene1231", "Munkh-Erdene.B")]:
    subs = [s for h in handles for s in json.loads((cache / f"status_{h}.json").read_text())["result"]]
    first = {}
    for s in sorted(subs, key=lambda s: s["creationTimeSeconds"]):
        if s["author"]["participantType"] == "PRACTICE" and s["verdict"] == "OK":
            first.setdefault((s["contestId"], s["problem"]["index"]), s)
    ratings = Counter(s["problem"].get("rating") for s in first.values()
                      if datetime.fromtimestamp(s["creationTimeSeconds"], timezone.utc).year == 2026)
    print(handles, [ratings[r] for r in (2300, 2400, 2500)])
PY
```
