# Stable DE exploration scripts (2026-11-10)

Exploratory scripts behind the "Stable DE, continued" entry in `details.md`.
Research only. They print to the terminal and write nothing under `output/`.
They are kept as run, without tests; treat them as a record, not a library.

Run from the repository root. `base_fit.py` must run first: it writes the
full-data hierarchical fit that several scripts load.

```bash
export PYTHONUTF8=1 OPENBLAS_NUM_THREADS=1 PYTHONPATH=.
./.venv/Scripts/python scripts/stable_de_explore/base_fit.py
```

Caches go to the gitignored `hier_binary_run/explore/`. Scripts marked
"cache" also need the `python -m arch_b.hier_binary all` cache, and "ratings"
need `output/skip_cells_ratings.json` (from `python -m arch_b.skip_cells 8`).

Rerun after the move into this folder: `base_fit`, `map_curvature`,
`floor_anchors`, `loader_unlisted_rows`, `problem_failures`, `float_seeds`.
The others were run only from the original scratch folder.

| Script | Needs | What it showed |
|---|---|---|
| `base_fit.py` | — | Full-data fit; board means μ, set means ν, linking rows per board. ν₀ = 2201. |
| `lab.py`, `fitsig.py` | — | Helpers: view cuts; a copy of `hier_binary.fit` with a per-team ability SD. |
| `float_cached_views.py` | cache | Drift of the reserved views by solve rate: the float sits at the floor. |
| `float_priors.py` | — | τ, τ_b, σ, σ_b do not remove the float. |
| `float_seeds.py 0.25` | — | 8 random quarter cuts: mean drift +11 (SE 7); floor +196, hard tail −129. |
| `sigma_b_edge.py` | — | σ_b 800–1600 is worse than 600 on both selection stages. |
| `board_spread_eb.py`, `board_spread_heldout.py`, `board_spread_checks.py` | — | Per-board ability spread (243–548): no gain. Run `heldout` before `checks`. |
| `floor_anchors.py` | — | CF anchors labelled 800–1200 read +253; all-solved problems land ~700 below the board's weakest decile. |
| `floor_timing.py`, `map_curvature.py` | cache | A timing term at the floor and curved CF maps: no LOCO gain. |
| `board_mu_extremes.py` | — | μ reaches 4562 on all-linker boards; it is not the board level. |
| `loader_unlisted_rows.py` | — | **Loader bug:** with rows that solved only unlisted problems kept, CCPC Harbin 2025 M goes 1847 → 2805. The loader was fixed on 2026-11-11, so both of its runs now print the fixed numbers. |
| `solved_vs_reported.py`, `wf_mirror_rows.py` | — | Fitted vs QOJ solve counts; the World Finals gap is mirror rows. |
| `scan_unusual.py`, `skip_partial_movers.py` | ratings | Largest model disagreements; every problem `skip_partial` lowers by ≥ 200, with solve times. |
| `problem_failures.py CID:LABEL ...` | — | Who failed a problem: submissions, official flag, team rating, other solves. |
| `latam_linkers.py` | — | Latin America 2023: the 12 linking rows and the level they imply. |
| `latam_mirror_rule.py`, `latam_unofficial_rule.py` | — | Dropping partial or all untouched cells of unofficial rows does not move the board. |
| `latam_level_drivers.py` | — | Free hyperpriors: no change. All links cut: +106. |
| `weak_board_simulation.py` | — | Parametric simulation on the real design: Latin America 2023 is recovered within −13…+13, Mid-Atlantic within +25…+95. |

The `latam` dictionary in the `latam_*.py` scripts holds the 13 blind hand
ratings for Latin America 2023.
