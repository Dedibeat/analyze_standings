# analyze_standings

Estimates ICPC-style **problem difficulties and team performances from contest
standings**, on a Codeforces-like scale. ICPC has no native contestant rating to
invert, so abilities and difficulties are fitted jointly from who solved what,
and teams that recur across contests link everything onto one scale. The same
data feeds medal-cutoff and qualification forecasts for the Asia East regionals,
coaching material for our team (NUM-R^3), CCPC comparisons and Codeforces research.

This file is the **master map**: what is where and what it is for.

## Start here

| Need | Read |
|---|---|
| What ships now, rules that are easy to break, open threads | [docs/STATUS.md](docs/STATUS.md) |
| Why something is the way it is, past experiments | [docs/journal/INDEX.md](docs/journal/INDEX.md) (grep it, then open the entry) |
| How to run a tool | [docs/usage/](docs/usage/) and the module's docstring |
| The method | [docs/design/](docs/design/) |
| Code in one folder | that folder's `CLAUDE.md` (module map) |

Setup: `python3 -m venv .venv && ./.venv/bin/pip install -r requirements.txt`.
Tests: `./.venv/bin/python -m unittest discover -s tests -p 'test_*.py'`.
The release commands are in [docs/STATUS.md](docs/STATUS.md#regenerate-the-shipped-products).

## Repository map

| Path | Purpose |
|---|---|
| `CLAUDE.md` (`AGENTS.md` → symlink) | Agent rules: what to read first, how to record work, coding rules |
| `README.md` | This map |
| `arch_b/` | **Main code.** Architecture B: joint item-response fits (Rasch, survival, hierarchical, `hier_time` = production), calibration to CF points, validation, medals and forecasts, exporters. Map: [arch_b/CLAUDE.md](arch_b/CLAUDE.md) |
| `arch_a/` | Architecture A: alternating fixed-point fit. Also the shared standings loader (`load.py`, used by everything), Elo primitive, ratings viewer and contest-graph exporters |
| `scripts/` | Data builders and fetchers, forecasts, NUM-R^3 tools, CCPC and Codeforces research, audits. Map: [scripts/CLAUDE.md](scripts/CLAUDE.md) |
| `llm_survival.py`, `llm_crosscontest.py`, `pairwise_tuning.py`, `cf_pairwise.py` | Gemini difficulty experiments: zero-shot pairwise × survival, cross-contest comparisons, CF pairwise tuning. Usage: [docs/usage/llm-difficulty.md](docs/usage/llm-difficulty.md) |
| `tests/` | `unittest` suite, one file per module |
| `data/` | Inputs: standings, rosters, official results, external difficulty sources, team-account data. Map: [data/CLAUDE.md](data/CLAUDE.md) |
| `output/` | Generated results (`*.json`, `*.md`) and HTML viewers. Shipped: `problem_ratings_hier.json`, `problem_calibration_hier.json`, `virtual_calc.html`, `ratings_viewer.html`, `medal_viewer.html`. Everything else is a research or forecast artifact named after its module |
| `docs/STATUS.md` | Current state (short, kept true) |
| `docs/journal/` | Dated, append-only record of every task: `YYYY-MM-DD-slug.md` plus `INDEX.md` |
| `docs/design/` | Method and design notes (see below) |
| `docs/reports/<area>/` | Long-form plans and reports, one per experiment (see below) |
| `docs/usage/` | How to run each tool family |
| `docs/teaching/` | Teaching selections and the probability-course problems (`.tex` + `.pdf`) |
| `autoresearch/` | Logs of the July 2026 auto-research campaigns on the metric (see `docs/design/program.md`) |
| `requirements.txt` | Pinned dependencies of the venv; sibling checkouts it needs are listed inside |
| `requirements-de-stability.txt` | Pinned NumPy for the frozen DE stability experiment |
| `*_run/` | Paid experiment outputs, committed: Gemini pairwise/LLM runs and the BigQuery TabFM responses. `de_stability_run/` and `hier_binary_run/` are local, derived and gitignored |

Sibling repositories:
- `../my-react-app`: the public app that receives the exported viewers and ratings.
- `../llm-integration`: the LLM tags and `difficulty_estimate` in `tagged.json`, and
  the named-technique extraction.
- `../qoj-intergration`: the QOJ HTML parser that the QOJ fetchers import.

## Docs

**Design** (`docs/design/`)
- `goal-and-data.md`: goal, inputs, id regimes.
- `architecture-a.md`: Architecture A and its key decisions.
- `architecture-b.md`: Architecture B and its key decisions.
- `metric.md`: north-star metric, calibrated LOCO CF RMSE (`arch_b.metric`).
- `program.md`: the auto-research program on that metric.
- `rating_bias.md`: every mechanism that inflates or deflates difficulties.
- `out-of-scope.md`: deliberate exclusions and old follow-ups.
- `strat.tex`, `strat_detailed.tex`: the mathematical write-up that code comments cite.

**Reports** (`docs/reports/`)
- `rating/`
  - `hier_time_report.md`: solve time in the hierarchical fit (the shipped model).
  - `hier_binary_report.md`: hierarchical binary as a DE rival.
  - `skip_cells_report.md`: skipped cells treated as missing data.
  - `problem_rating_audit.md`: ratings checked by hand.
  - `rating_rethink.md`, `rating_rethink_experiments.md`: rating design review and experiments 0–2.
  - `rating_improvement_strategy.md`: measurement improvements beyond the benchmark.
  - `de_successors.md`, `de_stability_plan.md`: DE successor candidates; stability-penalized DE.
  - `de_release_audit.md`: DE release audit.
  - `data_influence.md`: influence of supplemental contests.
  - `experiment_review.md`: 2026-09-05 audit with leakage findings.
  - `experiment_roadmap.md`: remaining audits and research.
  - `shipped_fit_update_plan.md`: TabFM/DE replay and update preparation.
- `calibration/`
  - `calibration_*`: ridge/DE calibration experiment, ablation, audit, interpretation.
  - `tabfm_cloud_plan.md`, `tabfm_bigquery_report.md`: managed TabFM on BigQuery.
- `forecast/`
  - `member_forecast_plan.md`, `member_forecast_report.md`: recorded-date forecasts with member priors.
  - `forecast_next_steps.md`: medal-forecast hand-off from 2026-10-01.
- `codeforces/`
  - `cf_ai_deflation.md`: CF rating deflation and AI use.
  - `cf_standings_experiments.md`: difficulty pilot and transfers.
  - `cf_25_experiments.md`, `cf_metric_search.md`, `cf_four_metrics.md`, `cf_five_hour_search.md`: solve-prediction searches.
  - `cf_participant_ratings.md`: member → CF rating feasibility.
- `llm/`
  - `llm_survival_plan.md`: zero-shot LLM × survival plan.
- `data/`
  - `external_data_sources.md`: audit of internet sources.

**Usage** (`docs/usage/`): `rating-model.md`, `medals-and-forecasts.md`, `team-r3.md`,
`ccpc.md`, `codeforces.md`, `llm-difficulty.md`, `viewers-and-app.md`.

## Where new work goes

- **Code:**
  - a model or experiment on the rating fit → `arch_b/<name>.py`;
  - a one-off analysis, fetcher or builder → `scripts/<name>.py`;
  - a test → `tests/test_<name>.py`.
- **Results:** `output/<name>.json` (+ `.md`). Downloaded raw data goes to a
  gitignored cache under `data/<topic>/`.
- **Docs:**
  - every task → a journal entry, plus one line in `docs/journal/INDEX.md`;
  - a long plan or report → `docs/reports/<area>/<name>.md`;
  - a change to what ships, or to a rule → `docs/STATUS.md`;
  - a new folder, top-level file or tool family → this map and the folder's `CLAUDE.md`.
