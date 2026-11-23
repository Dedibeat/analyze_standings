# Viewers, calculator and graph: running and reproducing

> Moved verbatim from `README.md` on 2026-11-20. Text may predate later changes; [docs/STATUS.md](../STATUS.md) is authoritative for what ships now.

## Interactive viewer

```bash
./.venv/bin/python -m arch_a.export_viewer
```

Writes a self-contained `output/ratings_viewer.html` from the same UCup-anchored
fit as `run` — the full `tagged.json`, 146 unique contests after deduplication
(Architecture A keeps its two-phase anchor, which measurably works there) —
just open it in a browser (no server needed). The contest picker is grouped by year
(newest first); the header shows the year and a link to the qoj contest. Pick a
contest to see its problems ranked by difficulty and its teams with both their
overall ability `θ` and their **performance** in that contest (the rating implied
by their final rank, eq. perf) — the gap shows who over- or under-performed. Click
any column to sort, filter teams by name/member/affiliation, and use the URL hash
(`#<contest_id>`) to share a link straight to a contest.

To view just the UCup-only anchor fit (Phase 1: seasons s3 + s4, 76 contests)
instead of the full anchored tagged fit:

```bash
./.venv/bin/python -m arch_a.export_viewer --ucup
```

This writes a separate `output/ratings_viewer_ucup.html` (the main viewer is
left untouched).

### Architecture B viewer (Codeforces-calibrated)

```bash
./.venv/bin/python -m arch_b.export_viewer
```

Writes `output/ratings_viewer_b.html` from the **survival** fit in
**Codeforces-equivalent points**: problem difficulties are the shipped DE
ratings (no ±SE, since DE has none), and team abilities/performances use the
scalar gym-shape map. This is the recommended viewer. It is published live via GitHub Pages:

**<https://dedibeat.github.io/analyze_standings/output/ratings_viewer_b.html>**

(The Architecture A viewer is also live at `.../output/ratings_viewer.html`.)

## Virtual contest performance calculator

```bash
./.venv/bin/python -m arch_b.export_virtual_calc
```

Writes `output/virtual_calc.html`: pick one of the 241 fitted contests (132
tagged.json regionals + all 57 Petrozavodsk camp contests + 52 Universal Cup
rounds not already in tagged.json, rated on their own Phase-1 UCup-only fit)
by name from the year-grouped dropdown, or jump straight to one by its qoj
**contest id** in the id box. Enter your team's solved count and penalty (minutes) from a
virtual (out-of-window) run — standard ICPC scoring, the same two numbers any
real team's standings line carries — and see the Codeforces-equivalent
performance rating you'd have earned. Method: standard ICPC tie-break (most
solved, then lowest penalty) inserts your team into that contest's real final
standings to get a hypothetical rank, then the same Elo rank-inversion
primitive `arch_b.medals` uses for every real team's `performance_elo`
converts that rank plus the real field's fitted abilities into a rating. The
standings table shows every real team's own calibrated performance
alongside yours for direct comparison. On a board that merges an event's official rows with
online mirror entries, an official row is ranked within its own event, while your virtual entry is
ranked on the whole board, like the mirror entries. So the same scoreline can read up to ~100 lower
as a virtual entry: mirror entries finish well above the same teams onsite (2026-10-13). Abilities and performances come from the
**binary** fit (`performance_fit`), mapped to CF by the scalar gym-shape +
affine map of that fit's difficulties, sampled into a dense lookup table at
export time so the browser doesn't need to re-fit it. The reference problems table shows the
shipped DE problem ratings.
Self-contained, no server; recomputes live as you edit solved/penalty.

## Contest-linking graph

```bash
./.venv/bin/python -m arch_a.export_graph
```

Writes a self-contained `output/contest_graph.html`: each node is a contest, an
edge joins contests that share team identities (the links that put every contest
on one scale). Toggle between the current roster/id keying and a year-appended
keying to see that adding the season to the team key fragments the single scale
into per-year islands. Runs on the 5-season `data/tagged.json`.

Module self-checks:

```bash
./.venv/bin/python -m arch_a.elo         # worked-example unit tests
./.venv/bin/python -m arch_a.load        # data summary
./.venv/bin/python -m arch_a.fixedpoint  # convergence trace
./.venv/bin/python -m arch_b.model       # MAP convergence trace
./.venv/bin/python -m arch_b.survival    # survival-model convergence trace
```
