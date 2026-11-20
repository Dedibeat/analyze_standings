# External validation vs Codeforces ratings (`arch_b.external_validate --contest 2206`)

The 2026 ICPC Asia Pacific Championship (qoj contest 3747, 13 problems) was
mirrored on Codeforces (contest 2206), where each problem carries an official CF
problemset rating — an authoritative *numeric* opinion, independent of our
standings. All three models match it strongly (this single-contest per-problem view,
formerly `arch_b.sanity_cf`, is now `external_validate --contest 2206`):

| model           | Spearman vs CF | Pearson vs CF |
|-----------------|----------------|---------------|
| arch A          | +0.945         | +0.938        |
| arch B binary   | **+0.962**     | +0.933        |
| arch B survival | +0.956         | **+0.947**    |

All ~0.95+ on a 13-problem contest is a strong cross-check of the whole approach.
The survival model has the best *linear* calibration (Pearson). **The decisive
case is J/K:** "Worldwide Playlist" (J) and "Time Display Stickers" (K) were each
solved by exactly 76 teams, so the binary model rates them *identically* (1172 =
1172); the survival model separates them by solve time (J 1826 > K 1714) and CF
agrees (J 1700 > K 1300) — a clean illustration of the signal solve times add.
(Caveat: all models still over-shrink the very hardest problems — the three
1-solver problems A/L/M land near ~2400–2650 vs CF's 2900–3500 — since a single
solve barely constrains the top of the scale. Ranking holds; the absolute scale is
addressed by the affine calibration below.)
