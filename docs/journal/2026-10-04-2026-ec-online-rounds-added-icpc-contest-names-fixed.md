# 2026 EC online rounds added; "ICPC" contest names fixed (2026-10-04)

**Request.** The EC online rounds were all named "ICPC", so Online I and II
could not be told apart. Add the 2026 Online I and II to the fit, write a
script for adding a contest, then ship to `../my-react-app`.

**Names.** QOJ titles were checked on qoj.ac/contests. The five online rounds
are now `EC Online (I)` (1485, 1794, 2513) and `EC Online (II)` (1799, 2524).
Three EC-Finals were also named "ICPC" and are now `EC-Final`: 1197 (2022) in
`tagged.json`, and 1040 (2020) and 1041 (2021) in `icpc_2020_2021.json`. Only
`contest_name` changed. `arch_a.load` reads the name only for the
championship/World Finals season rule, which these names do not match, so the
fit inputs are otherwise identical.
- `arch_b.medals` found online qualifiers by `name != "ICPC"`. It now skips
  names starting with `EC Online`. This also fixes pre-existing bug (3) in the
  2026-09-27 entry: 1197 is no longer excluded as an online round. It still
  drops out because it has no XCPCIO data, so the 28 medal contests do not
  change.
- `data/tagged_official.json` still has the old names. No code reads it.

**`scripts/add_qoj_contest.py` (new).**
`python3 scripts/add_qoj_contest.py <id> --name … --region … [--year …]`
appends one contest to `data/tagged.json` and skips ids already there.
- **Login:** QOJ now shows contest pages only to logged-in users, so the
  script logs in with `QOJ_USERNAME`/`QOJ_PASSWORD`. This is the same flow as
  the app's `src/qoj_sync.py`. The `qoj-intergration` module that
  `fetch_qoj_supplemental.py` imports is not on this machine.
- **Pages read:** the dashboard (problem names, and the year from the title)
  and the standings page. The standings page embeds `standings`, `score`,
  `problems` and `problems_id` as JSON, one variable per line.
- **Rows:** taken as served, with QOJ's default "Show unofficial" on, the same
  as earlier fetches. Rows use the existing format.
- **Solved cells:** a cell is solved when its score is positive. On an ICPC
  board the total is 100 per positive cell (checked on every 4071 row), and
  97 marks an accepted run that later failed added tests.
- **Empty cells:** a team's cells come as a JSON list when keyed 0..k-1, or
  `[]` when the team made no attempts.
- **Members:** a name ending in `(A, B, C)` gives the members; other names are
  kept whole. Team names contain colons, so the old `Aff: team` split is not
  reproduced.
- **Check against stored data:** on 2524, the 2,575 official rows of the
  live page match the stored copy exactly (per-problem solved, solve-time and
  wrong-attempt sums). The live page has 287 more unofficial rows than the
  stored copy, which was fetched earlier. Older rounds were not re-fetched.

**Data.**
- **4071 (EC Online (I) 2026):** 14 problems, 2,754 rows.
- **4113 (EC Online (II) 2026):** 12 problems, 2,689 rows.
- **Rosters:** `attach_online_rosters.py` now covers both rounds, using the
  2026 rows that `add_pta_rosters.py` had already put in `online_rosters.csv`.
  2,401 and 2,492 rows get a roster; 331 and 161 names are ambiguous; 14
  solved counts disagree on 4113. A second run changes nothing.
- **Old contests:** every pre-existing contest is identical to HEAD apart from
  the renames. `tagged.json` now holds 148 contests.

**Fit and release.** Same steps as the DE release: `arch_b.run`,
`arch_b.run --survival`, `arch_b.calibrate`, `export_viewer`,
`export_virtual_calc`, `export_ucup_only`, `medals`, `export_medal_viewer`,
`metric`.
- **Ratings:** 3,159 → 3,185 rated problems (+26). 255 contests are fitted;
  the calculator covers 241 → 243.
- **Calibration:** DE still selects alpha = 1, lambda = 1 on 185 anchors.
- **Movement of existing problems:** mean +3.6, median +2.3, max 56.8; 14
  move by ≥50 and none by ≥100. The five earlier online rounds rise 23.5 on
  average, because the 2026 rosters link more of their teams.
- **New problems:** they span the scale. 4071 F (2,620 solves) sits on the 800
  floor, 4113 J is 827 and 4113 G (0 solves) is 3982.
- **Metric:** `arch_b.metric` 246.3 → **244.6**; all guards pass (raw LOCO
  246.7).

**Tests.** Pins moved to the new fit:
- `test_calibration_experiment`: raw 246.6616, gym 244.3776.
- `calibration_ablation.CONTROL_DET_RMSE`: 229.0324113.
- `test_medal_predict`: Shanghai 2482.1.

`output/calibration_experiment.json` was regenerated with `--baseline-only`.
All 122 tests pass.

**Not regenerated:** the same historical/research artifacts as in the DE
release. The audits' hard-coded online-round lists (`fit_mechanism_audit`,
`de_release_audit`) describe their own runs and were left as they are.

Run (Windows: `PYTHONUTF8=1`):
`QOJ_USERNAME=… QOJ_PASSWORD=… python3 scripts/add_qoj_contest.py 4071 --name "EC Online (I)" --region "Asia East Continent"`
(likewise 4113), then
`python3 scripts/attach_online_rosters.py data/tagged.json data/tagged.json`
and the release steps above.
