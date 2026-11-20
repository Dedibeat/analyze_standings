# Latest standings and new contests pulled; 2026 regionals in the fit (2026-11-15)

**Request.** Pull the latest standings and the new contests. Then, explicitly, add
the 18 new contests and pull the 2026 Shenyang board from XCPCIO.

**Repo state.** Local `master` was 2 commits ahead and 17 behind `origin/master`.
The pull conflicted only in this file (the two teaching entries here vs the remote
stability/DE entries); both sides were kept, so the merge commit holds the remote
entries followed by the two local teaching sections. Nothing else conflicted.

**QOJ access.** QOJ now answers Cloudflare to non-browser clients, so the urllib
login in `scripts/add_qoj_contest.py` was replaced by the browserless flow of
`../p1/qoj/BROWSERLESS_AUTH.md`: `curl_cffi` with `impersonate="chrome136"`, the
md5 password, `_token` read from the page's JS, and the session cookies cached per
account in the git-ignored `data/.cookies-<user>.json` and reused until stale (the
same trick `fetch_team_r3.py` uses). `--refresh` was added: a contest id already in
`tagged.json` is normally left alone, but with the flag its entry is re-fetched and
replaced, which is how the newer standings below were pulled.

**Team parsing (deviation found while fetching).** `add_qoj_contest.py` only
understood `Team (m1, m2)`. The domjudge-imported regionals encode the same
information as `Affiliation - Team - m1, m2`, so the 2026 regionals arrived with no
rosters and no affiliations (Xi'an 121/753 members, Wuhan 103/546). `standing_row`
now splits that form too (affiliation from the first segment, members from a last
segment that looks like a name list), and Wuhan became 539/546. The `Aff: team`
colon form is still *not* split: team names contain colons (unchanged decision).
`fetch_xcpcio_standings.py` had the matching bug — 51st-season boards ship members
as `{"name": {"texts": ...}}` and `_plain_text` read `texts` one level too high, so
every 51st board came out with zero members; it now unwraps `name` first.

**Data.** `data/tagged.json`: **148 → 165 contests**, standing rows **61,097 →
65,758**, problems **+224**. QOJ supplies 15 contests (4,469 rows over all 17):

| contest | id | rows | note |
|---|---|---|---|
| Xi'an 2026 | 4593 | 753 | regional on QOJ (418 domjudge rows + UCup/unofficial) |
| Chengdu 2026 | 4607 | 729 | regional on QOJ |
| Wuhan 2026 | 4694 | 546 | regional on QOJ (uncategorised page, no categories) |
| Rocky Mountain 2026 | 4620 | 86 | |
| NAQ 2026 | 4566 | 21 | |
| NCPC 2026 | 4605 | 25 | |
| UKIEPC 2026 | 4606 | 11 | |
| Moscow Regional 2025 | 4614 | 184 | |
| Ho Chi Minh City 2022 | 4538 | 153 | the missing 2022 Asia Pacific regional |
| UCup S5 stages 1–7, extra stage, S4 semifinal | 4126, 4207, 4565, 4593*, 4607*, 4617, 4694*, 4569, 4576 | | *stages 4/5/7 are the three regionals above |

XCPCIO supplies the two 2026 regionals QOJ does not host yet: **Nanjing** (374 rows)
and **Shenyang** (416 rows), converted by `fetch_xcpcio_standings.py` into
`data/xcpcio_51st_regionals.json` and appended with the synthetic negative ids
`-216770522111721` / `-162528714534630` (region `Asia East Continent`, year 2026).
The same file's Xi'an/Chengdu/Wuhan boards were fetched and *not* appended: QOJ
carries those contests with the same onsite rows plus the unofficial field, and
importing both would double-count one contest (the same reason the 50th-season
XCPCIO regionals were never re-imported).

**Not added (deliberate).** Warm-ups (Xi'an 4597, Shenyang 4696, UCup S4 4575): the
repo keeps only EC-Final warm-ups. `4682` KAIST mock competition: not a regional.
XCPCIO invitational/provincial boards: outside the shipped scope. CCPC 2026 boards:
never part of `tagged.json`.

**Latest standings.** Five 2026 boards were re-pulled with `--refresh`; all had
grown since their import (QOJ adds unofficial rows after the freeze/onsite import):
Asia Pacific Championship 3747 78 → **122** rows, Latin America Championship 3762
43 → **84**, North America Championship 3518 108 → **157**, EC Online I 4071 2,754 →
**2,776**, EC Online II 4113 2,689 → **2,725**. `attach_online_rosters.py` was rerun
in place afterwards (4071: 2,415 rows attached, 4113: 2,511, 351/191 ambiguous).

**Linking of the new contests** (share of retained rows whose identity also appears
in another contest — the linking graph the scale runs on): Wuhan 88%, Shenyang 90%,
Nanjing 87%, Chengdu 78%, Xi'an **28%**, UCup S5 stages 80–98% (Extra Stage 97%),
Moscow 47%, Nordic 46%, UKIEPC 56%, NAQ 40%, Rocky Mountain 21%, Ho Chi Minh 18%.
Xi'an is the weak one because its organisers published no member names: 4593 has
121/753 rows with a roster in QOJ and 0/418 in XCPCIO, so most of its field can only
link through a trusted recurring team name.

**Fits.** 272 contests and **3,409 rated problems** (3,185 before; arch A rates
1,918 problems). Binary `theta=[1117, 3511]` mean 1963, `b=[800, 3740]` mean 2376,
`b` SE median 57; survival `theta=[800, 2726]` mean 1955, `b=[1180, 3212]` mean
2222, SE median 27; within-contest Spearman(difficulty, solve count) medians −1.000
/ −0.997.

**Calibration and metric.** DE still selects alpha=1.0, lambda=1.0 on 185 anchors.
`arch_b.metric` reads **246.3** calibrated LOCO CF RMSE (raw affine 248.2); the
previous release read 244.6. The +1.7 is inside the ~5-point noise band the
`program.md` contract sets, so it is not a regression to chase — but it is also not
a gain: the 17 added boards buy linking and coverage, not accuracy on the CF
anchors. Every guard passes: gym EC +0.977, gym pooled +0.969, Kattis pooled
+0.796, AOJ within-contest +0.563, solve-count sanity +0.997.

*(On the "~220 RMSE" numbers in this file: `hier_binary` 225.6 and the
`de_stability` DE row 225.6 are the **ablation harness's** nested-LOCO protocol
(`arch_b.calibration_ablation`), where the same shipped survival fit scores 229.97
(`ridge_DET`) and 248.24 raw affine. `arch_b.metric` — the north-star for the
shipped deliverable — reads 246.3 for that same fit. The two numbers measure
different protocols, not different models, and no estimator changed in this
release; moving the shipped rating to `hier_binary` remains the open research
decision it was on 2026-11-05.)*

**Tests.** Pins moved to the new fit: `test_calibration_experiment` raw 248.2360 /
gym 246.3485, `calibration_ablation.CONTROL_DET_RMSE` 229.9701691633,
`test_medal_predict` Shanghai 2489.3. `output/calibration_experiment.json`
(`--baseline-only`) and `output/calibration_ablation.json` were regenerated, since
both are the frozen baselines those tests compare against. 226 of 228 tests pass;
`test_hk_field_2026` errors only because this machine's Python has no `openpyxl`,
and `test_calibration_ablation`'s frozen-residual comparison is the regenerated
baseline above.

**Artifacts.** `output/problem_ratings{,_b,_survival,_calibrated}.json`,
`ratings_viewer.html` (158 contests), `ratings_viewer_b.html` (151),
`virtual_calc.html` (260), `ucup_only_*.json` (52 contests / 684 problems),
`medal_badges.json` + `medal_viewer.html` (unchanged: 358 problems / 28 contests).

**Not done.** The 2026 East Asia regionals are in the fit but **not** in the medal
analysis: `data/xcpcio_ea_official.json` has no entry for 4593/4607/4694 or the two
XCPCIO-only ids, and `medal_predict`'s 2026 forecast is trained on 2022–2025 bars
by design — extending the badges to an in-season actual is its own decision. The
app copy (`../my-react-app`) was not reshipped.

Run: `QOJ_USERNAME=… QOJ_PASSWORD=… python3 scripts/add_qoj_contest.py <id> --name
… --region … [--year …] [--refresh]`, then
`python3 scripts/fetch_xcpcio_standings.py icpc data/xcpcio_51st_regionals.json
--board-link /icpc/51st/nanjing --board-link /icpc/51st/shenyang`, then
`arch_b.run`, `arch_b.run --survival`, `arch_b.calibrate`, `arch_b.metric`,
`arch_a.run`, `arch_b.export_viewer`, `arch_b.export_virtual_calc`,
`arch_b.export_ucup_only`, `arch_b.medals`, `arch_b.export_medal_viewer`,
`arch_a.export_viewer`.
