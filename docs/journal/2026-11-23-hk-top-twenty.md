# The difficulty of twentieth at Hong Kong

On the November 22 field, six Reviewed lineups satisfy both a top-30 finish on a matched 2026 mainland ICPC regional board and a top-150 finish in at least one 2026 qualifier. No Pending lineup qualifies. This deliberately conservative definition tests two different contest settings. Peking has a qualifier fourth but no matched regional in the audit. Eight lineups separately beat half of NUM-R³’s rank in both qualifiers. Five overlap with the six regional standouts. A 20th-place finish can absorb all six plus 13 more opponents ahead.

The 2026-rule replay on the 2024 and 2025 HK boards reached the tenth qualifying seat at 37th and 32nd respectively. Mid-30s is a working estimate conditional on comparable skips and ten seats. The mix of round-one EC-Final registrants in this year's weaker field is unknown. The allocation counts eligible medal teams and skips registered teams and capped schools. A place around 30th provides a modest historical buffer and 20th a much larger one.

Reproduce from the repository root with the project Python. Board ranks are the published source-board ranks.

```python
from pathlib import Path
from contextlib import redirect_stdout
from io import StringIO

audit = Path("docs/journal/2026-11-23-hk-opponent-replay.md").read_text(encoding="utf8")
with redirect_stdout(StringIO()):
    exec(audit.split("```python\n")[1].split("```")[0])
for i, team in enumerate(allteams):
    rounds = team["online_ranks"]
    results = [(site, rank) for site, rank, _ in evidence[i] if "/51st/" in site and rank <= 30]
    if results and min(rounds.values(), default=9999) <= 150:
        print(team["school_en"], team["team"], team["status"], rounds, results)
    if rounds.get("1", 9999) <= 272 and rounds.get("2", 9999) <= 174:
        print("Both qualifiers:", team["school_en"])
```
