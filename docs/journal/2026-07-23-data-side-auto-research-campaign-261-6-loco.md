# Data-side auto-research campaign (2026-07-23): 261.6 LOCO

A 46-iteration campaign focused on standings and identity data after earlier
model-side searches had plateaued. **3 changes were kept, 43 discarded.** The
calibrated metric improves **266.4 → 261.6** (−4.8 CF points), while raw affine
LOCO improves **288.4 → 285.0** and every guard passes. Full log:
`autoresearch/loop-260723-1333/classic-results.tsv`.

The first keep fixes `_link_wf_top_team`: the purported WF-only,
season-matched affiliation join was actually touching thousands of regional
no-roster rows and ignoring season when the main identity key was
season-agnostic. Restricting it to World Finals and separating competition
season from identity-token season improves calibrated LOCO **266.4 → 264.5**;
Kattis also rises 0.795 → 0.796 and held-out AUC stays 0.8858.

The other two keeps add standings-only QOJ data: 14 Asia East ICPC contests from
2020–2021 and 57 Petrozavodsk camp contests from 2022–2026. Together they add
18,181 rows and 850 problems, improving **264.5 → 261.6**. A held-out transfer
test scored the same original `tagged.json` cells with and without all 71
supplemental contests: log-loss **0.312411 → 0.311973**, Brier
**0.097557 → 0.097385**, and AUC **0.885761 → 0.886000**. This corroborates
that the new standings improve linked team abilities rather than merely fitting
the 185 CF anchor problems. Collection used only QOJ category/dashboard labels
and unofficial standings; statements, editorials, and solutions were never
requested.

Notable discards: a conservative full-roster CF prior using only ratings known
before January 1 of each contest year moved LOCO just −0.1; live QOJ refresh
added 482 later virtual-replay rows and moved −1.0 without independent
corroboration; removing account-like replay rows was decisively harmful
(LOCO 282.8, raw guard 306.6, Kattis guard 0.707); zero-solve inclusion, stricter
identity links, duration thresholds, Asia West exclusion, and qualifier removal
were neutral or worse. A refreshed cookie made the standings audit possible,
but QOJ's historical dashboard exposes no exact start timestamp, so the
participant-prior experiment stayed on the conservative January 1 cutoff.

The continuation tested every other QOJ training-camp family separately:
ByteDance/Moscow Workshops, JAG, ICPCCamp, Moscow International Workshops,
Moscow Pre-Finals, HDU multi-university training, Osijek, and 130 older
Petrozavodsk entries. After contest-id deduplication this was 196 unique
contests (192 with standing rows). No family cleared the 5-point threshold.
The best narrow combination, HDU + pre-finals, moved LOCO only
**261.6 → 261.0** and failed the independent original-cell holdout:
log-loss **0.312698 → 0.313261** and AUC **0.885327 → 0.884989**.
Combining all camp families was harmful (**264.0**, gym pooled 0.953,
solve-count sanity 0.951). `scripts/fetch_qoj_supplemental.py` reproduces these
standings-only collections from a QOJ category while skipping already-loaded
contest ids; it never requests statements, editorials, submissions, or
solutions.

XCPCIO was also tested as a direct fit source rather than only as the official
team-label source used by the medal analysis. Its hosted `config.json`,
`team.json`, `organizations.json`, and `run.json` provide exact duration,
official groups, member rosters, and run timestamps. The resumable
`scripts/fetch_xcpcio_standings.py` converts those files to the project schema,
handles second/millisecond/minute timestamp declarations, and assigns stable
negative ids so they cannot collide with QOJ contests. A 2022–2026 sample
covered **56 provincial contests / 14,134 rows** (13,258 explicitly official;
8,188 with rosters). Individual years were neutral except 2023 (261.9);
combining all years regressed **261.6 → 262.5**, including when restricted to
official teams, and the Asia-East gym guard slipped 0.961 → 0.960. Five
official 9th CCPC boards were neutral (261.6). Existing XCPCIO East Asia
regionals were not re-imported because those same contests are already loaded
from QOJ and XCPCIO already supplies their official-team labels. The direct
XCPCIO datasets therefore remain discarded experiments, not shipped fit input.
