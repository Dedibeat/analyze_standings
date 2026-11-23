# scripts/: module map

One-off analyses, data builders and fetchers. Run them from the repository root,
either `python3 scripts/<name>.py` or `python -m scripts.<name>`. The docstring
gives the exact command and outputs. Credentials come from the environment
(`QOJ_USERNAME`/`QOJ_PASSWORD`). Session cookies are cached in gitignored
`data/.cookies-*.json`.

## Data: fetch, build, attach (they change `data/`)

- `add_qoj_contest.py`: add or refresh one QOJ contest in `data/tagged.json`
  (shared QOJ login).
- `fetch_xcpcio_standings.py`: XCPCIO boards → standings JSON (CCPC, XCPCIO-only
  regionals).
- `fetch_qoj_supplemental.py`: standings-only QOJ category collector.
- `add_xcpcio_official.py`, `build_xcpcio_official.py`: official/unofficial tags
  and the official identity cache.
- `build_ec_online_data.py`: `data/ec_online/` (online results, rosters,
  regional results, slot rules).
- `add_pta_rosters.py`: append the 2025–2026 PTA registration lists.
- `attach_online_rosters.py`: attach roster members to EC online rows (rerun after
  online rounds change).
- `build_quota_evidence.py`, `build_tabfm_gold_data.py`: the quota evidence and
  TabFM gold table.
- `cphof_cf_participants.py`: CPHoF → Codeforces identities.
- `backfill_standings.py`: no docstring.
- `fetch_team_r3.py`: download the team account's QOJ submissions and contests.
- `qoj_clearance.py`: harvest a QOJ `cf_clearance` with a headful Chrome when
  Cloudflare challenges again; writes the gitignored clearance file that
  `qoj_auth.py` replays. [Usage](../docs/usage/qoj.md).
- `qoj_auth.py`: shared password login, session cache and QOJ HTTP requests
  for the single-contest and team fetchers. Impersonates Chrome and appends
  the challenge-evasion query suffix to every request (not to `/cached-downloads/`,
  which 404s with a query) — keep both.
  [Usage](../docs/usage/qoj.md).

## Forecasts and contest analysis

- `ecfinal_chance.py`, `ecfinal_cutoff.py`, `ecfinal_retro.py`: EC-Final seat
  chances and cutoffs.
- `anchor_teams.py`: anchor teams for judging non-regional contests.
- `ec_overlap.py`: how much of each field played an EC regional.
- `technique_forecast.py`, `technique_patterns.py`: named techniques in EA
  regionals.
- `ccpc_icpc_medals.py`, `contest_quality.py`, `ccpc_difficulty_rank.py`: CCPC
  vs ICPC comparisons.

## NUM-R^3 (our team)

- `team_r3_participations.py`: official and virtual participations.
- `hk_shenyang_rank.py`: Hong Kong registrants ranked by Shenyang-equivalent 2026 strength; `--virtual BOARD:RANK` places a virtual result there.
- `team_r3_digest.py`: per-contest dossier reading aid.
- `team_r3_cf.py`, `team_r3_cf_rounds.py`: members on Codeforces.

## Rating audits

- `problem_rating_audit.py`: hand-audit support (~3 min).
- `rating_rethink_audit.py`: read-only evidence for `rating_rethink.md`.
- `identity_links.py`: shipped identity vs no two-shared-member links (2026-11-17).
- `stable_de_explore/`: kept-as-run exploration scripts from 2026-11-10 (see its
  README).

## Codeforces research (reports in `docs/reports/codeforces/`)

- **Rating deflation:**
  - `cf_ai_deflation.py`: CF deflation and AI use (API cache in gitignored
    `data/cf_ai/`).
  - `cf_participation_check.py`
- **Solve-prediction pipeline, in run order:**
  - `cf_difficulty_pilot.py`
  - `cf_player_rating.py`
  - `cf_solve_history.py`
  - `cf_history_sweep.py`
  - `cf_metric_search.py`
  - `cf_four_metrics.py`
  - `cf_boost_data.py`, `cf_boost_search.py`
  - `cf_cross_history.py`
  - `cf_field_search.py`
  - `cf_factor_search.py`
  - `cf_rolling_boost.py`
  - `cf_crossfit_curve.py`, `cf_crossfit_result.py`
  - `cf_confirm_models.py`
  - `cf_feature_ablation.py`
  - `cf_official_metrics.py`
  - `cf_search_audit.py`

## Other

- `check_cf_teaching.py`, `check_cses_teaching.py`: small-case checks for the
  teaching notes.
- `sync_pairwise_artifacts.sh`: rsync and verify the pairwise artifacts. Since
  2026-11-20 they are in git, so only `verify` still matters. Its 2026-08-06
  snapshot predates the phase 3 results and the problem enrichment, so it reports
  2 mismatches.
