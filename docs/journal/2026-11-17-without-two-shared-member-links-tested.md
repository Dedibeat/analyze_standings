# Without two-shared-member links: tested (2026-11-17, fourth entry)

**Request.** Test dropping the two-shared-member identity links through the
protocol. Script `scripts/identity_links.py` → `output/identity_links.json`.

**Comparison, written before the run.** `shipped` (the identity just
released) against `no_pair_links` (the same, without two-shared-member links;
exact rosters, stable ids, trusted names and the WF link stay). Both fit the
shipped setting on the same rows.
- Team prediction: the same 20% of standing rows held out in both (row-level
  draw, splits 1 and 2; `appearance_split` cannot be shared because it keys on
  identity). Held-out cell log loss, paired contest bootstrap.
- CF accuracy: nested-LOCO affine map on the 184 trusted anchors (full-data
  fit, purged folds as in `scorecard`), paired contest bootstrap.
- Both hand panels pooled (103 problems; development data).
- Not measured: the stability views (their row samples are drawn per
  identity), the 2026 replay.

**Rule.** `no_pair_links` replaces `shipped` only if all hold:
1. its nested-LOCO CF RMSE is lower;
2. on both splits, its held-out log loss is not significantly worse (the
   2.5% bound of the difference is ≤ 0);
3. its pooled hand-panel RMSE is not worse by more than 10.
Otherwise `shipped` stays and nothing is re-released. Reported, no rule:
Jinan 2022 D, the CF 1900–2500 anchor bias, EC model − gym.

**Result: rejected (criterion 2); `shipped` stays, nothing re-released.**

| | `shipped` | `no_pair_links` |
|---|---|---|
| teams | 37,797 | 42,860 |
| nested-LOCO CF RMSE | 205.7 | 204.4 (diff −1.3 [−3.0, +0.1]) |
| hand panels pooled (unclipped) | 229.8 | 227.3 |
| held-out log loss, split 1 / 2 | 0.24025 / 0.24220 | 0.24567 / 0.24754 |
| difference, split 1 / 2 | | +0.0054 [+0.0035, +0.0076] / +0.0053 [+0.0035, +0.0073] |
| held-out cells of teams seen nowhere else | 68,907 / 68,366 | 81,600 / 81,476 |
| CF 1900–2500 anchor bias | +62 | +61 |
| EC model − gym (median) | +314 | +297 |
| Jinan 2022 D | 2359 | 2305 |

- The links carry real identity: without them about 12,700 more held-out
  cells have no other appearance of their team, and they are predicted
  worse. Criteria 1 and 3 pass, by small margins.
- So the −54 on Jinan D is a level shift that only an unlinked fit produces,
  and it costs prediction. D stays at 2359.
- The shipped `nested_loco_rmse` reproduces `hier_time evaluate` (205.7).
  The hand figure is unclipped here (229.8; 225.3 clipped in the evaluate),
  the same for both identities.
- Run (~8 min, 6 workers):
  `PYTHONUTF8=1 OPENBLAS_NUM_THREADS=1 python -m scripts.identity_links 6`.

**Where Jinan D's 2359 now stands** (all entries of 2026-11-17): about 50 of
it is the solve-time release's band lift (+56 on CF-labelled 1900–2500
problems, binary +7), about 40 the single Rasch slope on a steep problem.
Neither is a bug. The identity bug was real and is fixed, and did not
touch D.
