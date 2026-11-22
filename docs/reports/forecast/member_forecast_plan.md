# Experiment 3: recorded-date roster forecasts

Protocol frozen 2026-11-05 before scoring. This continues experiments 0–2 in
`rating_rethink_experiments.md`; research only.

1. Use `data/tagged.json` boards mapped in `data/xcpcio_ea_official.json`
   with numeric XCPCIO start/end times. Require imported `$DEFAULT` rows
   matching the existing official-team matcher. Exclude mirrors, unresolved
   dates, duplicate normalized full rosters within a board and zero-solve rows.
   Record all exclusions. Zero-solve exclusion matches the existing model;
   results are conditional on solving something, not all registered teams.
2. At each target start, train only on boards whose recorded end precedes it.
   Identity is an exact normalized three-person roster, never a stable account,
   a two-member overlap, university ranking or a future identity edge. Other
   rows get isolated identities. No target responses measure training problems.
3. Static binary Rasch is the history baseline. A separate fixed q=50/year
   random walk challenges it on the same history rows, using the existing
   smoother. Do not combine dynamics with member priors in this experiment.
4. For a new full roster, find each member's latest completed earlier roster
   (same-time conflicting rosters are ambiguous and supply no evidence).
   Transfer its static ability, average with MU0 for missing members, then
   multiply the deviation from MU0 by w in {0, 0.5, 1, 1.5}. Multiple members
   from one earlier roster share one evidence source; report that source count,
   and do not multiply its precision. This is a point-forecast experiment,
   not a posterior uncertainty model for individuals.
5. Select w only on 2023 contest-balanced pair log loss involving a cold roster.
   Ties choose the smaller w. Initial history is 2022; evaluate from 2024 onward.
   This is a stricter **development replay**, since these seasons were already
   inspected in October. It is not untouched confirmation. The pair scale is
   frozen at the historical 1.25 * Elo.S, not tuned on evaluation contests.
6. Score different-rank pairs, forecast ties worth half: pair log loss and order
   accuracy, both contest-balanced and pair-weighted. Matched populations:
   history only; cold-with-member-history only; combined; and combined pairs
   involving at least one cold roster (primary member-prior comparison).
   Report per-contest scores, row forecasts, known-member/source counts,
   paired contest-bootstrap intervals, calendar-season resampling, and a
   first-evaluation-appearance-per-roster sensitivity for recurring teams.
7. Save source/code hashes, excluded inputs, exact cutoffs and training contest
   manifests. Check that future results cannot change an earlier forecast,
   changed rosters stay distinct, simultaneous contests do not cross cutoffs,
   ambiguous member histories are excluded, and ties are handled correctly.

Limitations to retain: normalized names are not verified personal IDs; cached
rosters have no publication timestamps, so their availability at each historical
cutoff cannot be certified. The narrower panel omits online/UCup histories and
must not be compared numerically with the October full-panel gain. No production
promotion without fresh confirmation. Appearance effects, timing and canonical
task linking remain separate later experiments.
