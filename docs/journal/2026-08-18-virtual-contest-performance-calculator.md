# Virtual contest performance calculator (2026-08-18)

`arch_b.export_virtual_calc` writes `output/virtual_calc.html`, an interactive
tool for a team that solved a past contest *virtually* (outside the official
window) to estimate the Codeforces-equivalent performance rating they would
have earned. Design was discussed with the user (four `AskUserQuestion`
rounds) before building; the agreed shape:

- **Contest source**: an existing contest already in the fit (not a freeform
  problem set), so the virtual team can be ranked against a real field.
- **Rating method**: the classic **Elo rank-inversion** primitive
  (`arch_a.elo.performance_rating`, eq. perf) — not a fresh Rasch MLE fit from
  the solve pattern. This is the same primitive `arch_b.medals` already uses
  for every real team's `performance_elo`, so the virtual number sits on a
  precedented scale rather than a new one.
- **Input granularity**: full ICPC-clock detail — solved/unsolved, minutes
  into the contest, and wrong-attempt count per problem, matching how
  `penalty_seconds` is actually computed in the source data.
  Penalty = `floor(time_seconds/60) + 20*wrong_attempts`, summed only over
  *solved* problems (standard ICPC rule; wrong attempts on unsolved problems
  don't count).
- **Interface**: a self-contained HTML page (open from disk, no server),
  following the exact convention of `ratings_viewer_b.html` /
  `medal_viewer.html` — contest picker grouped by year, `/*__DATA__*/null`
  placeholder swapped for embedded JSON, URL-hash deep links.

Mechanics: the virtual team's (solved, penalty) is compared against every
real team's (solved, penalty_seconds) in that contest using the standard ICPC
tie-break (more solved wins; ties broken by lower penalty) to get a
hypothetical rank. `elo.performance_rating(rank, rival_thetas)` then converts
that rank plus the real field's **internal-scale** fitted abilities (same
UCup-anchored survival fit as `arch_b.export_viewer`) into an internal-scale
rho. The rank-insertion and Elo bisection are reimplemented in vanilla JS
(`pi`, `weightedRating`, `performanceRating` in `virtual_calc_template.html`
directly port `arch_a/elo.py`) since they must run live against whatever the
user types.

Mapping rho to CF points reuses the same `arch_b.calibrate` gym-shape +
affine composition as `_cf_map` in `arch_b.medals`, but that map can't be
re-fit in the browser (no gym data or CF anchors shipped client-side), so
`export_virtual_calc.build_data()` samples it once into a dense lookup table
(every 5 CF points across [800, 4000], ~641 points) and the page does linear
interpolation. This is exact enough for display purposes and avoids
duplicating the shape-fitting math in JS.

Bundled per contest: problems (label, name, `difficulty_cf` only — no SE,
since it's just reference context while filling the form) and every real
team (rank, name, affiliation, solved, `penalty_seconds`, internal `theta`).
Teams with zero solves are already absent from the fit (dropped at the loader
level, `README.md`), matching `arch_b.medals`'s convention of restricting
rivals to solving teams. Scope is the 189 contests that survive
`MIN_SOLVE_HOURS` filtering: the 132 tagged.json regionals `arch_b.export_viewer`
also uses, plus all 57 standings-only Petrozavodsk camp contests
(`arch_b.anchor.PETROZ`) — not the UCup-anchor-only seasons, the older-ICPC
supplement, or World Finals, since those either lack full problem/statement
metadata (unlike Petroz, which does carry problem names) or aren't a natural
"your contest" target. Both sources are already part of the shipped fit by
default (`estimate_anchored`'s supplemental inputs), so no extra fitting is
needed to add Petroz — only its raw standings had to be reloaded and folded
into the same contest-building loop as tagged.json.

The picker also accepts a **qoj contest id** directly (a text box + Go
button, `goToContestId` in the template), not just the year-grouped
dropdown — useful once Petroz's 57 similarly-named "Petrozavodsk ... Day N ...
Contest" entries are mixed in. An unknown id shows an inline error rather
than a blocking `alert()`; the existing `#<contest_id>` URL-hash deep link
now routes through the same lookup.

Verified with headless Chrome (`google-chrome --headless=new --dump-dom`,
plus a scripted harness that checks boxes and calls `recompute()` directly)
rather than by inspection alone: this caught a real bug (`$(...).forEach is
not a function` — `$` is `querySelector`, singular; needed `$$` /
`querySelectorAll` for the per-row solve loop) that silently broke every
computation before the fix. Post-fix, spot checks on the 2026 ICPC Asia
Pacific Championship (77 real teams) match expectations: zero solves → rank
78/78, performance floor 800; solving all 13 problems fastest → rank 1/78,
performance ceiling 4000; a mid-pack 6-of-13 solve pattern → rank 38/78,
performance ≈2383 CF, consistent with the field's ~2340 mean θ. The Petroz
addition and contest-id lookup were re-verified the same way: a bad id shows
the inline error and clears on a valid one, `goToContestId(819)` lands on
"Petrozavodsk Winter 2022. Day 1. Kyoto U Contest 2" (147 teams), and a
5-of-13 partial solve there gives a plausible mid-field rank/performance.

## Revision: manual solved/penalty entry + calibrated standings performance (2026-08-18)

Two follow-up changes, both user-requested same day:

1. **Input switched from per-problem detail to direct solved-count +
   penalty entry.** The original design (above) had the user check off each
   problem with a time and wrong-attempt count, and the page summed those
   into solved/penalty itself. The user asked to enter solved/penalty
   directly instead — the two numbers actually used for rank-insertion (the
   per-problem breakdown was never itself part of the ranking math, only a
   way to derive the total). `#inSolved`/`#inPenalty` are now editable
   number inputs feeding `recompute()` directly; the problems table lost its
   checkbox/time/wrong-attempt columns and is now pure reference (label,
   name, `difficulty_cf`) for judging what a plausible solved/penalty pair
   would be. This is a strict simplification, not a scope change — the
   rank-insertion and Elo-inversion math are untouched.
2. **Standings table gains a calibrated Performance column** for every real
   team, not just the virtual one. Reuses `arch_a.fixedpoint.
   _performance_ratings` exactly as `arch_b.export_viewer` does (each real
   team's rho from its *actual* rank), then the same `to_cf` map already
   built for the virtual team's own number. The row→(contest, team) mapping
   needed to attach the right rho to the right team is looked up by
   `(contest_id, team index)` from `ds.contest_of_row`/`ds.team_of_row`
   directly, rather than by an incrementing counter over raw-JSON row order
   (the trick `export_viewer.py` uses, which only works because it reads
   *exactly* the fit's first source in the fit's own concatenation order).
   That trick would silently misalign here: this module's `SOURCES` is
   `[TAGGED, PETROZ]`, but the actual fit's supplemental order is
   `[OLDER_ICPC, PETROZ, WF]` — older-ICPC's rows sit between tagged's and
   Petroz's in the row array this module never reads. The `(contest_id, team
   index)` lookup sidesteps that fragility entirely and is asserted non-None
   for every team the picker builds.

Verified with headless Chrome again: default load has solved/penalty
inputs at 0/0 (rank last, performance floor); setting them to 8 solved / 900
min penalty on a 150-team contest recomputes live to rank 46/150, performance
2658 CF; the standings table now renders 5 columns per row, the top real team
shows the 4000 ceiling performance, and the highlighted "YOU" row's
Performance cell matches the summary stat exactly.
"Petrozavodsk Winter 2022. Day 1. Kyoto U Contest 2" (147 teams), and a
5-of-13 partial solve there gives a plausible mid-field rank/performance.

## Revision: Universal Cup contests added to the picker (2026-08-19)

User asked why UCup contests (e.g. `qoj.ac/contest/2921`, "Grand Prix of
Ōokayama") weren't showing up in the virtual calc. Root cause: `SOURCES =
[TAGGED, PETROZ]` never included `ucup_s3.json`/`ucup_s4.json` — UCup was
loaded only for the Phase-1 anchor fit inside `estimate_anchored`, and its
resulting UCup-only `theta_u`/`b_u` were discarded (`_`) rather than
returned, so the raw standings were never reloaded for the picker either.
(Separately: SEERC 2023–2025 aren't in the picker for an unrelated reason —
they were never fetched from QOJ into any dataset file at all; only the 2022
edition exists, as `tagged.json` contest 2511. That's a data-collection gap,
not a code fix, and is still open.)

Fix: `arch_b.anchor.estimate_anchored` gained an opt-in `return_ucup=False`
flag; when `True` it additionally returns `(ds_ucup, theta_u, b_u)` from the
Phase-1 fit it already runs internally (previously `b_u` was thrown away).
Default behavior/return arity is unchanged for every other caller.
`export_virtual_calc.py` now builds the picker's contest list twice — once
from the tagged-scale fit over `SOURCES` (unchanged), once from the UCup-only
fit over `UCUP_SOURCES = UCUP` — via a shared `_contests_from(ds, theta, b,
to_cf, paths, uf, exclude_ids=())` helper (the previous single inline loop
in `build_data()`, factored out unchanged apart from the new parameter). The
same `to_cf` map (fit once from the tagged-scale records) is reused for both,
since it's a general internal-scale→CF-points affine map, not tied to which
dataset the internal thetas came from.

17 contest ids appear in *both* `tagged.json` and the UCup files (e.g. id
2511 above is not among them, but ids like 1784/2908/3169/... are) — without
handling, they'd be listed twice with two different fits' numbers. Fixed by
passing `exclude_ids={int(cid) for cid in ds.contests}` (the tagged fit's
own contest set) to the UCup pass, so an overlapping contest is shown once,
from the tagged-scale fit only.

Contest count: 189 → 241 (132 tagged + 57 Petroz, unchanged, plus 52 UCup
rounds not already in tagged.json; UCup's raw 76 contests minus the 17
overlaps minus a few dropped by the same `MIN_SOLVE_HOURS`/dedupe filters
`load()` applies). Verified `2921` now appears with real problem
`difficulty_cf` values and team performances, no contest id is duplicated in
the output (`grep`-checked), and `arch_b.export_virtual_calc` still runs
clean end-to-end.

## Revision: export the 52 UCup-only contests for ../my-react-app (2026-08-19)

Follow-up: the user wanted these same 52 UCup-only contests' problems added
to `../my-react-app`'s problemset app, with their calibrated ratings — a
different consumer than the virtual calc, so a separate script,
`arch_b/export_ucup_only.py`, was added rather than reusing
`export_virtual_calc`'s in-memory picker data. It fits the same UCup-only
Phase-1 fit (`estimate_anchored(..., return_ucup=True)`), computes Laplace
SE (`survival.laplace_se`), and calibrates to CF points with the same
shape+affine map as `arch_b.calibrate` (`_gym_shape`/`_anchors`, duplicated
inline rather than importing `calibrate.main`'s internals, since that
function also writes a file and picks between binary/survival models —
more than this script needs). Writes `output/ucup_only_contests.json`
(canonical/tagged.json-shaped, no LLM tag fields) and
`output/ucup_only_ratings.json` (problem_ratings_calibrated.json-shaped).

37 of the 52 contests carry no `year` in the source UCup JSON (`ucup_s3`/
`ucup_s4.json`); the react app's display string is `contest_name + ' ' +
year` verbatim, so those were rendering as e.g. "Grand Prix of Ōokayama
null". Fixed by falling back to each season file's most common non-null
year when a contest's own `year` is missing (2024 for `ucup_s3.json`, 2025
for `ucup_s4.json`, computed dynamically via `Counter.most_common`, not
hardcoded) — only affects the exported `year` field, not the fit itself.

The my-react-app side (`scripts/merge_ucup.py`, `DETAILS.md`) is documented
in that repo.
