# Ship hierarchical binary with time to all rating products (2026-11-16)

Authorized switch from the DE problem / flat-binary performance / survival medal
mixture to the `hier_time` release candidate at b3119a1: `time_skip`, K=5,
w=0.25, skip_partial, frozen hierarchical priors. This is hierarchical binary
with solve-time slices, not the old survival fit. Nested-LOCO RMSE is 205.9
on 184 trusted anchors; the gain over DE on that metric is not significant.

`arch_b.shipped` supplies one cached full-data fit and the release affine map
for every production exporter. `calibrate.problem_cf` reads
`problem_ratings_hier.json`. DE artifacts and its research/calibration command
remain historical baselines; they are not used by these product exporters.
The release metadata is marked production. Viewers describe the new model.
Official-event ranking rules and medal counts are preserved.

Regenerated virtual calculator (260 contests), ratings viewer (151 tagged
contests), medal badges/viewer (358 problems, 28 contests). Checked all 3,409
problem appearances against the shared fit within displayed rounding. The app
copies the hierarchical problem file and calibration metadata, re-exports all
260 contest fields and copies the medal viewer. It also adds the 17 newly
available nonempty tagged contests, preserving prior app tags. The two XCPCIO
boards use their real board URLs rather than synthetic QOJ ids.

Validation: 23 focused unit tests (shipped fit/map, hierarchical time and binary,
standings loader, official-event ranking) pass; app lint/build pass. App checks
cover 5,556 sampled official performances and 1,040 virtual results over all
260 contests. Conditional difficulty SEs exclude map and board-level error;
research limitations in hier_time_report.md still apply.
