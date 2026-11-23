# Stability-penalized DE: run on the PC, no penalty gain (2026-11-05, second entry)

**Request.** Resolve the merge conflict, pull master, and continue the stable
DE experiment.

**Merge.** A pull was stopped on a `docs/journal/` conflict between the local
CCPC difficulty entry (2026-10-18) and the remote Hong Kong 10-23 / 10-26
follow-ups. Both are kept: the CCPC entry now sits after the Hong Kong
follow-ups and before the Xi'an entry. The second pull (up to `59734ac`)
merged cleanly. Full suite: **220 tests pass** (system Python 3.11).

**Running on Windows.** The PC is Windows 10 with no WSL; the CPU is an
i7-14700KF (28 threads), not the i9 the hand-off named, with 34 GB RAM.
- `core.autocrlf=true` writes CRLF into the working tree, so 64 of the 68
  frozen hashes failed `check`. The committed blobs match all 68. Fix:
  delete the 68 files and check them out again with
  `git -c core.autocrlf=false checkout HEAD -- <files>`. No source or
  config changed. A later checkout that touches them brings CRLF back.
- NumPy 2.5.1 has no Python 3.11 wheel, so `.venv` uses Python 3.12.2
  (`py -3.12 -m venv .venv`; run `./.venv/Scripts/python`, with
  `PYTHONUTF8=1`). The venv holds only NumPy; the full suite needs the
  system Python.
- Timing: full view 16 s; the other 15 views with `--jobs 8` 68 s; `evaluate`
  10 s. Under 1 GB per worker.

**Reproduction.** The full view matches the hand-off exactly: 53 binary /
154 survival iterations, max feature difference 0.0, and clipped-DE LOCO
**225.607** RMSE. All 16 views cover all 185 problems (none missing).

**Selection.** The stable fit picked beta = 0.1 in 7 of 15 outer folds and
beta = 0 in 8 (alpha 1 in 14 of 15). DE kept its usual (1, 1) in 14 folds.

**CF RMSE, outer leave-one-contest-out** (185 problems, 15 contests; paired
contest-bootstrap 95% intervals):

| view | DE | binary affine | augmented (beta 0) | stable | stable − augmented | augmented − DE |
|---|---:|---:|---:|---:|---|---|
| full | 225.6 | 246.8 | 237.8 | 238.0 | +0.2 [−1.0, +1.5] | +12.2 [+0.8, +22.8] |
| half (reserved) | 234.9 | 259.7 | 225.4 | 226.5 | +1.2 [+0.3, +2.2] | −9.5 [−19.1, +0.9] |
| quarter (reserved) | 276.8 | 279.2 | 242.5 | 243.3 | +0.8 [+0.0, +2.1] | −34.2 [−44.2, −24.9] |
| eighth (reserved) | 353.7 | 317.6 | 289.5 | 289.5 | −0.0 [−1.3, +1.6] | −64.2 [−77.4, −49.8] |
| event only | 245.0 | 270.4 | 252.0 | 252.6 | +0.6 [−0.4, +1.7] | +7.0 [−6.8, +23.6] |
| event small | 310.3 | 309.4 | 273.7 | 273.8 | +0.2 [−0.4, +0.8] | −36.7 [−56.7, −14.3] |
| mirror balanced | 264.6 | 273.9 | 244.9 | 245.7 | +0.8 [−0.1, +1.9] | −19.7 [−31.5, −6.9] |
| strong half | 369.4 | 386.9 | 327.8 | 327.5 | −0.3 [−1.7, +1.4] | −41.6 [−55.8, −26.9] |
| weak half | 450.9 | 381.8 | 356.7 | 355.4 | −1.3 [−3.1, +0.3] | −94.2 [−113.6, −74.4] |

**Drift RMS** (same problem vs the full view; strong/weak vs their own pool):

| view | DE | binary affine | augmented | stable |
|---|---:|---:|---:|---:|
| half (reserved) | 94.7 | 72.6 | 96.1 | 94.7 |
| quarter (reserved) | 185.9 | 138.4 | 177.4 | 174.9 |
| eighth (reserved) | 298.3 | 217.2 | 268.3 | 264.8 |
| event small | 207.2 | 148.6 | 185.0 | 182.3 |
| strong half | 135.8 | 159.7 | 133.9 | 131.0 |
| weak half | 231.9 | 156.7 | 196.3 | 194.1 |

**Reading it.**
- **No stability-penalty gain.** Against augmented ridge, the penalty
  changes CF RMSE by −1.3 … +1.5. It is worse in 13 of 16 views, with the
  interval excluding zero on 6 of them and never on the better side. Drift
  RMS falls only 0.5–3.5 (0.6–2.2%). Order reversals are identical in every
  view. The plan's rule applies: no stability-penalty gain is claimed.
- **Resampling alone (beta 0) is not a successor either.**
  - It beats DE on small and weak samples mainly by fixing DE's mean shift.
    DE's mean error drops to −66 (reserved quarter), −142 (eighth) and −246
    (weak half); augmented's is −4, −65 and −139.
  - It does not cut the per-problem scatter. Median absolute drift is higher
    than DE's in 10 of the 14 perturbed views (reserved half 68.9 vs 63.0,
    reserved quarter 110.0 vs 102.8). It is lower only on quarter1, eighth
    (about equal), mirror-balanced and the weak half.
  - On the full field it loses 12.2 RMSE (interval excludes zero) and is
    worse on 13 of 15 contests. The CF ≥ 2800 tail goes from 290 to 310,
    and every region gets worse.
  - On event-only boards it is no better than DE (+7.0, interval includes
    zero).
- The spread is not flattened: on the full field, augmented/stable predict
  an SD of 723–725 vs a target SD of 698 (DE 664).
- **Binary affine** is still the most field-stable: lowest drift RMS in 13
  of the 14 perturbed views (all but the strong half) and the fewest order
  reversals. But it is the least accurate on the full field (246.8). That
  supports candidate #1 (binary plus a small monotone map) as the next test.

**Caveats.**
- By the frozen seeding rule, `quarter0` / `quarter1` are the first quarters
  of the same shuffles as `half_a0` / `half_a1`, so they are nested in those
  halves rather than drawn independently.
- The reserved random views come from the same random-identity family as the
  training views. Gains there are in-distribution, not transport evidence.
  The event/mirror and strength views are the real stress tests.
- Event/mirror labels are the ID heuristic. All 15 contests were already
  inspected, so this is development data, not fresh confirmation.

**Decision.** Candidate #2 is not a DE successor. Shipped DE, its ratings
and the app are unchanged. The scorecard is in
`output/de_stability_evaluation.json` / `.md`; the run cache stays in the
gitignored `de_stability_run/`.

Run on Windows (Git Bash, from the repo root):
`export PYTHONUTF8=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1`,
then `./.venv/Scripts/python -m arch_b.de_stability check`, then
`prepare --jobs 8`, then `evaluate`.
