# Auto-research program: minimize LOCO CF-RMSE

## Invocation (uditgoenka/autoresearch skill)

Run from a dedicated branch (`git checkout -b autoresearch` — the loop
auto-commits and auto-reverts):

```
/autoresearch
Goal: Reduce the survival difficulty model's leave-one-contest-out CF-point
  RMSE. Read program.md (this file) first and obey its Scope and Hard rules.
Scope: arch_b/survival.py, arch_b/model.py, arch_b/anchor.py, arch_b/run.py,
  arch_a/load.py
Metric: loco_cf_rmse (lower is better); improvements under 5 points are noise
  — discard unless a guard value or held-out AUC also improves
Verify: ./.venv/bin/python -m arch_b.metric | tail -1
Guard: ./.venv/bin/python -m arch_b.metric
Iterations: 25
Delegation: reserve your own reasoning for picking the next change, deriving
  the math (gradients/curvatures), reviewing diffs, and keep/discard. Delegate
  the mechanical part of a change you have fully specified — the edit itself,
  running verify, log bookkeeping — to a subagent with model: sonnet (include
  the exact spec and file paths in its prompt; it starts with no context).
  Never delegate design, math derivation, or keep/discard judgment. Parameter
  sweeps are not LLM work at all: write a bash/python loop over the values.
```

(Verify parses the scalar off the last line; Guard reruns the same command for
its exit code — nonzero = a guard floor was violated. Two ~5 s runs per
iteration.)

## Goal

Improve the **survival difficulty model** (the shipped deliverable:
CF-equivalent problem ratings) as measured by one scalar: leave-one-contest-out
RMSE in Codeforces points against official CF problem ratings.

## Verify

```bash
./.venv/bin/python -m arch_b.metric
```

Contract:
- Last stdout line is `METRIC loco_cf_rmse=<value>`. **Lower is better.**
- Exit code `1` means a guard was violated → **discard the change**, whatever
  the metric says. Exit `0` + lower RMSE → keep.
- Runs in ~5 s, fully deterministic (no RNG anywhere in the fit).
- Baselines (2026-07-03): survival **290.2**, binary (`--binary`) 344.3, on
  185 anchor problems / 15 contests (every rated CF mirror our dataset has —
  an exhaustive problemset sweep found no more). Guard floors are calibrated
  to the survival baseline; the binary variant already sits below one of them.

**Noise floor / keep threshold.** The cluster-bootstrap SE of the metric is
**±20 points** (contests resampled as units). Keep/discard comparisons are
paired on the same anchors so they are more sensitive than that, but still:
**treat improvements smaller than ~5 points as noise** — do not keep them
unless a guard or the held-out AUC (`python -m arch_b.predict_eval`) also
improves. Many small "wins" kept against a fixed 185-anchor set is how a loop
overfits the anchors without LOCO noticing.

The guards (printed as `GUARD <name>=<value> (floor <f>) ok|FAIL`) protect what
the metric cannot see: the CF anchors cover only Asia Pacific / Northern
Eurasia / Europe, so `gym_ec_spearman` (Asia East Continent vs the gym-mirror
yardstick), `gym_pooled_spearman`, `kattis_pooled_spearman` (North America +
Europe) and `solvecount_sanity` (within-contest ordering) must not regress
below their floors.

## Scope — what may be changed

Fair game (one focused change per iteration):

- `arch_b/survival.py` — the likelihood itself: hazard shape (constant → e.g.
  Weibull-in-time), the `lambda0` convention, using `wrong_attempts` (present in
  the raw `tagged.json` rows but not yet parsed by `arch_a/load.py` — wiring it
  through the loader is in scope), a recalibrated link.
- `arch_b/model.py` — priors: `SIGMA_THETA`, `SIGMA_B`, `MU0`; a
  **heavier-tailed difficulty prior** (the known worst failure is over-shrunk
  1-solver problems: we say ~2500 where CF says 2900–3500); per-problem prior
  scale by observation count.
- `arch_b/anchor.py` — the UCup anchor pull (e.g. per-team evidence-scaled
  prior strength as in `arch_a/anchor.py`, `anchor_weight` analog).
- `arch_b/run.py` — `MIN_SOLVE_HOURS` and other data-hygiene thresholds.
- `arch_a/load.py` — data hygiene and identity keying (season keying, zero-solve
  policy, dropping **Asia West Continent** contests is explicitly permitted —
  we don't practice on those and they have no anchor coverage).
- Reading `output/gym_difficulty.json` as **input** is allowed (e.g. gym-informed
  per-problem prior means `N(b_gym, se_gym)` — it is on the CF scale and pins the
  hard tail where onsite fields have 0–1 solvers). Caveat: that makes the
  `gym_*` guards partly circular, but the metric itself (official CF ratings)
  stays independent.

## Hard rules — violating any of these invalidates the run

1. **Never read** `data/cf_problemset.json`, `data/cf_team_contests.txt`, or any
   CF problemset rating inside the fit path, and never special-case the anchor
   contest ids. The metric must stay a held-out test.
2. **Do not modify** `arch_b/metric.py`, `arch_b/external_validate.py`,
   `arch_b/gym_difficulty.py`, anything under `data/`, or
   `output/gym_difficulty.json`.
3. Keep the fit deterministic and the verify runtime under ~2 minutes.
4. numpy only (no scipy — it is not installed).

## Prioritized ideas (from the analyses in details.md)

1. Heavier-tailed / evidence-scaled difficulty prior → hard-tail fix (biggest
   known point-error source at the 2900–3500 end).
2. Gym-informed prior means for the ~700 gym-covered problems (see caveat above).
3. Use solve times harder: hazard shape, per-contest duration handling, or the
   unused `wrong_attempts` penalty signal.
4. Prior/anchor sweeps: `sigma_theta`, `sigma_b`, UCup pull strength.
5. Time-varying `theta_{team,season}` with a smoothing prior (keep one identity;
   the hard season split was already tried and hurt — see details.md).
6. Data hygiene: `min_solve_hours`, Asia West exclusion, zero-solve policy.

Log each iteration: what changed, metric before → after, guard values.
