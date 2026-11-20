# Revising Dedi's solo practice for Hong Kong

Dedi asked to compare four problems he liked or nearly solved with his official and virtual CF round performances. He prefers solo CF, a second look the next day, and a hint if he still has no new idea. He wants the regional upsolve to be a joint attempt at AC. He confirmed the ten-hour draft fits him and would spend additional time on solo CF. The [training plan](../reports/team-r3/hong-kong-2027.md) now reflects those choices. Tamir and Erdene have yet to give their preferences.

| Problem | Dedi's account and the public submission record |
|---|---|
| [2285E, Arithmetic Subarray](https://codeforces.com/problemset/problem/2285/E) | He found the idea after about an hour and used revealed tests to debug. One TLE and two WAs preceded the AC by a total of 13m42s. Credit independent idea discovery and record test-assisted debugging. |
| [2279D, Meta Graph](https://codeforces.com/problemset/problem/2279/D) | Dedi recalls missing the last piece. A virtual WA was followed by two practice TLEs and a practice AC the same day. The submissions do not show how he obtained that last piece. |
| [2283F, Minimize the Graph](https://codeforces.com/problemset/problem/2283/F) | First recorded submission on F was a practice AC on Nov 5, the afternoon after his official round crossed midnight in Ulaanbaatar. This is his example of a successful second sitting. |
| [2260F, Edge Three-Coloring](https://codeforces.com/problemset/problem/2260/F) | Rated 2500. His first recorded submission on F was a practice AC the day after his virtual. The editorial turns the sparsity bound into a search over subsets of at most ten non-tree edges. That is one example of the kind of change in perspective he values. [Editorial](https://codeforces.com/blog/entry/156529) |

The saved rating histories put Dedi's peak at 2106 and Erdene's at 2204. An earlier [practice audit](2026-11-20-team-r3-cf-qoj-practice.md) found 43 distinct 2300–2500 practice ACs for Dedi in its November snapshot. That establishes experience in the band. The data lack a denominator for unseen problems he started and put aside.

## CF performance estimates, through November 20

| Window | Rated official | Virtual | Both |
|---|---:|---:|---:|
| Jan 1–Nov 20 | 1866 (23) | 2014 (29) | 1948 (52) |
| Oct 1–Nov 20 | 1963 (4) | 2271 (6) | 2019 (10) |

As of November 20, CF published a difficulty for 2260F only among the four examples. A full user-status/problemset check that day still gave 22 practice ACs at 2300, 12 at 2400 and nine at 2500.

For each round, find the Elo-scale rating whose expected number of opponents ahead equals the observed number. Use opponents with positive published pre-round ratings. Rated entries use the rating-changes list and actual rank. Virtual entries use the score reconstructed by the dossier and the matched official standings. Virtual ranks, ties and provisional ratings introduce uncertainty. Combining the two groups weights each appearance equally, so the mix of official and virtual rounds matters. The earlier 1870 was a fitted 50% *problem solve* level under contest conditions, a different measurement.

## Reproduce

Run from the repository root. This reads the November dossier and the public Codeforces API. For virtual round 2279, the reconstructed score is about 2246 from A/B/C accepted at minutes 39/66/86, with one charged rejection each on A and C. In the other virtuals the dossier's insertion rank identifies the weakest score still ahead. The rating estimates apply the same expected-rank equation to both formats.

```bash
python3 - <<'PY'
import gzip, json, statistics, time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen

def api(method, query):
    time.sleep(0.6)
    with urlopen(f'https://codeforces.com/api/{method}?{query}', timeout=60) as response:
        return json.load(response)['result']

def performance(ratings, ahead):
    counts = Counter(ratings)
    lo, hi = 0, 4000
    while hi - lo > 0.05:
        mid = (hi + lo) / 2
        expected = sum(n / (1 + 10 ** ((mid - r) / 400)) for r, n in counts.items())
        if expected > ahead:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2

history = api('user.rating', 'handle=Dedibeat')
entries = []
for row in history:
    date = datetime.fromtimestamp(row['ratingUpdateTimeSeconds'], timezone.utc).date().isoformat()
    if '2026-01-01' <= date <= '2026-11-20':
        entries.append((row['contestId'], date, 'rated', row['rank']))
dossier = json.loads(Path('output/team_r3_cf_rounds.json').read_text())['rounds']['Dedi']
entries.extend((r['contest_id'], r['date'], 'virtual', r['rank']) for r in dossier
               if r['kind'] == 'virtual' and r['date'] <= '2026-11-03')
entries.append((2279, '2026-11-19', 'virtual', None))

results = []
for cid, date, kind, rank in entries:
    query = f'contestId={cid}'
    changes = api('contest.ratingChanges', query)
    opponents = {r['handle'].lower(): r for r in changes
                 if r['oldRating'] > 0 and r['handle'].lower() != 'dedibeat'}
    if kind == 'rated':
        rank = next(r['rank'] for r in changes if r['handle'].lower() == 'dedibeat')
        ratings = [r['oldRating'] for r in opponents.values()]
        ahead = sum(r['rank'] < rank for r in opponents.values())
    else:
        board = api('contest.standings', query)
        icpc = board['contest']['type'] == 'ICPC'
        if cid != 2279:
            with gzip.open(f'data/team_r3/cf/standings/{cid}.json.gz') as f:
                previous = json.load(f)['rows'][rank-2]
            threshold = (previous[1], -previous[2] if icpc else 0)
        ratings, ahead = [], 0
        for row in board['rows']:
            members = row['party']['members']
            if len(members) != 1 or members[0]['handle'].lower() not in opponents:
                continue
            ratings.append(opponents[members[0]['handle'].lower()]['oldRating'])
            score = (row['points'], -row['penalty'] if icpc else 0)
            ahead += score > (2246, 0) if cid == 2279 else score >= threshold
    results.append((date, kind, performance(ratings, ahead)))
for since in ('2026-01-01', '2026-10-01'):
    for group in ('all', 'rated', 'virtual'):
        values = [v for d, k, v in results if d >= since and (group == 'all' or k == group)]
        print(since, group, len(values), round(statistics.median(values)))
PY
```
