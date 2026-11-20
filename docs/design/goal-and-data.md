# Goal

Rate ICPC-style problems by difficulty from contest standings alone (no native
contestant rating, unlike Codeforces/AtCoder). Strategy is described in
`strat.tex` (concise) and `strat_detailed.tex` (gentle long-form). This repo
implements both **Architecture A — the alternating fixed point** (strat.tex §3,
`arch_a/`) and **Architecture B — the joint item-response (Rasch) MAP model**
(strat.tex §4, `arch_b/`).

# Data

`data/tagged.json` — 146 contests, 99,754 standing rows, 1,668 problems (the full
mixed ICPC + Universal Cup set). The file *originally* held **213 contest entries**:
67 were exact duplicates of an earlier entry (the same `contest_id` repeated up to
6×, with identical standings but an empty problem list). These have been **dropped
from the source file** (146 unique contests remain); the loader still dedupes
defensively in case the data is regenerated (see the deduplication decision).

`data/tagged_with_official.json` — same 146 contests, with an added `official:
true/false` field on every standing row. Official/unofficial tags are sourced from
**XCPCIO** (`https://board.xcpcio.com`), which hosts the official ICPC scoreboard
data (domjudge-imported onsite teams). For 26 East Asia regional contests (seasons
47th–50th, 2022–2025), XCPCIO's team.json was fetched and teams were matched by
normalized name against QOJ standing rows (see `scripts/add_xcpcio_official.py`).
13 contests carry **explicit** XCPCIO group tags (`"group": ["official"]`); the
other 13 (older 47th/48th seasons where XCPCIO team data lacks per-team group
labels) use the entire XCPCIO team list as the official field — validated by
comparing XCPCIO team counts against domjudge-id row counts (they match exactly).
12 East Asia contests could not be matched (6 online "ICPC" qualifiers, 3 EC-Final
warm-ups, Shanghai 2023 which XCPCIO has no entry for, "China" / "Grand Prix of
China" which lack a city match). Non-EA contests are unaffected.

`data/ucup_s3.json` and `data/ucup_s4.json` are
the two Universal Cup seasons (43 and 33 contests) used to anchor the scale.
Per standing row: `rank`, `team_id`, `members`, `total_solved`, and per-problem
`{solved, score, time_seconds, wrong_attempts}`. This yields the model inputs
`y_tp` (solved), `tau_tp` (solve time), `r_{t,c}` (rank).

`data/icpc_2020_2021.json` adds 14 Asia East ICPC regional contests
(8,487 standing rows, 179 problems), and `data/petroz_2022_2026.json` adds 57
Petrozavodsk Programming Camp contests (9,694 rows, 671 problems). Both were
fetched from QOJ on 2026-07-23 using dashboard problem labels plus unofficial
standings only—no statements, editorials, or solutions. Architecture B loads
these 71 supplemental contests with `tagged.json`; the `MIN_SOLVE_HOURS=3.5`
filter leaves 204 fitted contests total. Their value is extra cross-contest team
evidence: calibrated LOCO improves 264.5 → 261.6, corroborated by an original-cell
holdout (AUC 0.885761 → 0.886000).
