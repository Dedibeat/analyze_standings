# Codeforces research: running and reproducing

> Moved verbatim from `README.md` on 2026-11-20. Text may predate later changes; [docs/STATUS.md](../STATUS.md) is authoritative for what ships now.

## Codeforces rating deflation and AI use (2026-11-18)

```bash
./.venv/bin/python scripts/cf_ai_deflation.py --fetch-rc   # rating changes of every contest since 2018 (~50 min, resumable)
./.venv/bin/python scripts/cf_ai_deflation.py --fetch-st   # standings of rated rounds since 2021 (~45 min, resumable)
./.venv/bin/python scripts/cf_ai_deflation.py --analyze    # tables on stdout, output/cf_ai_deflation.json (~1.5 min)
```

Public API only, no cookie. The downloads are kept for later use in
`data/cf_ai/` (270 MB, gitignored):

- `contest_list.json`;
- `rc/<contest>.json.gz`: handle, rank, old and new rating;
- `st/<contest>.json.gz`: problem ratings and each contestant's solve times;
- `replay.npz`: the published rating formula replayed on every contest since
  2019-06, the slow step of `--analyze`.

The script rebuilds every account's internal rating history and measures:

- the 12- and 22-month rating change of the same established players against
  pre-AI windows;
- change points of four monthly series;
- the formula replay, and how much of each rating change it explains;
- solves on problems far above a player's rating, against Codeforces' Elo
  expectation.

Findings: established players rated 1400+ lost about 37–113 points
(January 2025 to November 2026, beyond pre-AI variation). The onset is
January–February 2025. The write-up is [cf_ai_deflation.md](../reports/codeforces/cf_ai_deflation.md).
The [standings experiments](../reports/codeforces/cf_standings_experiments.md) test the participation explanation and compare fitted problem ratings with official ratings on held-out handles.
A follow-up on the same players reduced log loss from 0.204245 to 0.201600 by learning a separate solve-curve slope per problem.
Modelling pre-round player strength from rating history reduced it further to 0.201037.
Using past solve histories and flexible problem curves reached 0.197900 in 2025 and improved all 43 later rounds evaluated in 2026.
A [25-model history search](../reports/codeforces/cf_25_experiments.md) lowered the later-period loss further to 0.201981.
The [multi-metric follow-up](../reports/codeforces/cf_metric_search.md) reached 0.201862 on the later period and reports Brier score, calibration error, and within-problem AUC.
The [timing-history comparison](../reports/codeforces/cf_four_metrics.md) tests whether solve speed improves all four measures.
The [extended CF search](../reports/codeforces/cf_five_hour_search.md) documents the time-budgeted experiments and confirmation protocol.

## One player's improvement, net of deflation (2026-11-21)

```bash
./.venv/bin/python scripts/cf_self_check.py <handle>   # ~75 s, needs the data/cf_ai/ cache above
```

The script compares the player's rating level and solve level in each half-year since
2024H2 with accounts that were at the same level in 2024H2. It then corrects by how
such accounts moved over the same span from 2021–2022 bases. Output:
`output/cf_self_check_<handle>.json`. The first run (Dedibeat) is in the
[2026-11-21 journal entry](../journal/2026-11-21-dedibeat-improvement-net-of-cf-deflation.md).
