# data/: inputs and their roles

Paths are relative to `data/`. Never hand-edit a file that a script builds; rerun
the builder. Downloads go to gitignored caches here. `.gitignore` lists them:
`cf_ai/`, `cphof_cache/`, `ec_online_cache/`, `gym_checkpoints/`,
`cf_pairwise/problems/`, and the team_r3 PDFs/zips. Note: 28 files in
`ec_online_cache/` were committed before that folder was ignored.

## Fit inputs (read by `arch_b.joint`)

- `tagged.json`: the main standings. 165 contests with problem statements, LLM
  tags and `difficulty_estimate`, and team members. Changed only by
  `scripts/add_qoj_contest.py`, `add_xcpcio_official.py` and
  `attach_online_rosters.py`.
- Supplements:
  - `ucup_s3.json`, `ucup_s4.json`: Universal Cup.
  - `icpc_2020_2021.json`: older Asia East.
  - `petroz_2022_2026.json`: Petrozavodsk camps.
  - `wf_tagged_format.json`: World Finals.
- `xcpcio_51st_regionals.json`: XCPCIO-hosted 2026 EA boards. Nanjing and Shenyang
  are appended to `tagged.json`.

## Research and validation only (never fit inputs)

- CCPC boards: `xcpcio_ccpc.json`, `qoj_ccpc.json`.
- External difficulty:
  - `aoj_difficulty.json`
  - `kattis_difficulty.json`
  - `cf_problemset.json`: CF problem ratings; anchor labels.
  - `cf_team_contests.txt`: URLs of CF contests that mirror our contests; the anchor source.
  - `cf_gym_mirrors.json`, `cf_mirror_solves.json`
- `cphof_cf_participants.json`: member → CF identities and rating histories.
- `de_stability_anchors.json`, `de_stability_inputs.json`: frozen anchor set used
  by the hierarchical fits.
- `tagged_official.json`: official-row variant read by
  `scripts/team_r3_participations.py`.
- `wf_contests.json`: no code reads it; origin not recorded.

## Regional results, rosters, forecasts

- `ec_online/`: built by `scripts/build_ec_online_data.py`. It holds official online
  rankings, rosters, regional results and medals, `slot_rules.json` (hand-encoded
  2023–2026), and `quota_evidence.json`.
- `xcpcio_ea_official.json`: official identity keys for EA medal contests (used by
  medals and forecasts).
- `icpc_*_teams.csv`, `icpc_hk_macau_*`: PTA registration exports (online rounds,
  Hong Kong / Macau), read by `add_pta_rosters.py` and `arch_b.hk_field_2026`.
- `tabfm_gold/`: TabFM gold table and 2026 forecast SQL.
- `techniques_atlas.json`: named-technique snapshot from `../my-react-app`.

## Team and experiment data

- `team_r3/`: the NUM-R^3 team account. It holds QOJ submissions and code,
  contest dashboards and statements, XCPCIO boards, `members_solved.csv` and `cf/`.
  Built by `scripts/fetch_team_r3.py`.
- `cf_pairwise/`: snapshot and summary of the pairwise Gemini experiment.
- `cf_ai/` (gitignored, about 10 GB): Codeforces API cache for `scripts/cf_*`.
