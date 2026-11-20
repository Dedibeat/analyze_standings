# Dedi's in-contest solves in the team rounds

Joined the actual AC labels and member credits to the shipped hierarchical binary ratings. Twelve rounds have at least one member credit, including Shenyang onsite J. Five other virtuals and the other four Shenyang onsite ACs lack individual attribution. Xi’an J is credited to Dedi with help from Tamir. EC Online I F and M were split between Dedi and Erdene. Both are rated 800, so the unknown assignment leaves the distribution unchanged.

Dedi has 21 named individual credits plus one of the two 800s, giving 22 individually credited solves with median 1878.6, range 800–2428.9. Three are at least 2300 and one is at least 2400. His six explicitly paired solves give a total of 28 credited contributions. The highest individual credits are Permutation Counting 4 (2428.9, determinant parity, first try) and Grid Filling Game (2315.6, greedy segmentation). The highest official credit is Shenyang J (2304.1), which Dedi described as primarily his own solve. On the Hangzhou virtual he implemented Tamir’s idea for Subgraph Isomorphism (2602.4). On Bull Farm (2680.4) Dedi supplied the idea, Tamir implemented and GPT helped find the bug. [Member dossier](../../output/team_r3_coach/summary.md) · [Permutation Counting 4 and Bull Farm](../../output/team_r3_coach/1794.md) · [Hangzhou](../../output/team_r3_coach/1071.md)

Reproduce from the repository root.

```bash
python3 - <<'PY'
import csv
import json
from pathlib import Path
from statistics import median

def load(name):
    return json.loads(Path('output', name).read_text())

ratings = {(p['contest_id'], p['problem_label']): p['difficulty_cf']
           for p in load('problem_ratings_hier.json')}
groups = {'individual': [], 'paired': [], 'ambiguous': []}
for r in load('team_r3_participations.json'):
    for p in r['problems']:
        member = (p['member'] or '').split(' [')[0]
        if p['label'] not in r['solved'] or 'Dedi' not in member:
            continue
        group = 'ambiguous' if ' or ' in member else 'paired' if '+' in member else 'individual'
        value = ratings[r['contest_id'], p['label']]
        groups[group].append(value)
        print(r['contest_id'], p['label'], p['name'], value, member)
onsite = next(b for b in json.loads(Path('data/xcpcio_51st_regionals.json').read_text())
              if b['board_link'].endswith('/shenyang'))
team = next(r for r in onsite['standings'] if r['team_name'] == 'NUM-R^3')
with open('data/team_r3/members_solved.csv') as f:
    for row in csv.DictReader(f):
        label = row['Problem'].strip()
        if row['Contest:'].endswith(f"({onsite['contest_id']})") and row['Member solved'] == 'Dedi':
            assert team['problems'][label]['solved']
            groups['individual'].append(ratings[onsite['contest_id'], label])
assert groups['ambiguous'] == [800, 800]
individual = groups['individual'] + [800]
print(len(individual), median(individual), min(individual), max(individual),
      sum(v >= 2300 for v in individual), sum(v >= 2400 for v in individual),
      len(groups['paired']))
PY
```
