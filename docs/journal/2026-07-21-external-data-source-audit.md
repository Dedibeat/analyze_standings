# External data-source audit (2026-07-21)

**Implemented 2026-07-23:** AOJ is now a reproducible validation-only dataset
and metric guard (45 accepted problems across four Japan regionals; survival
within-contest Spearman +0.576).  The CPHoF→Codeforces identity/history source
layer described above is also implemented; fit-side participant priors remain
deferred because exact regional timestamps and per-team prior precision are
still missing.  CP-Ranking alone remains insufficient because it lacks the
member-level histories needed to use its 22 identity seeds without leakage.

A broader live-source audit identified three concrete additions beyond the
initial CLIST/XCPCIO pass.  First, CPHoF World Finals rosters and external-profile
links provide a higher-confidence real-name→handle bridge: its 2021–2025 ICPC
pages yielded 426 unique exact-name candidates in the current standings, covering
2,485 member appearances before roster/institution verification.  The prepared
CP-Ranking data gives a smaller immediately conservative seed—22 exact
year+institution+team identities appearing in 57 standing rows—but an
institution-only join is invalid because it would assign one finalist roster's
rating to unrelated teams from the same university.

Second, public ICPC Contest API / DOMjudge endpoints can provide the true contest
duration, stable team/person IDs, and submission/judgement event history.  True
duration directly closes the `T_c = latest solve` approximation; event feeds
could later distinguish no-attempt cells from failed-attempt histories.  Endpoint
access is contest-specific and must be measured rather than assumed.

Third, AOJ is now a permanent independent difficulty guard. The reproducible
collector found 71 unique exact-title candidates and accepts 45 of 46 Japan
Regional problems from 2022–2025; the other 26 candidates are retained with a
rejection reason because fewer than three titles corroborate their contest.
Current within-contest Spearman is +0.587 (Architecture A), +0.650 (binary), and
+0.576 (survival). The north-star metric floors the survival AOJ guard at +0.52.
AtCoder Problems produced no unique exact matches and is lower priority;
solved.ac remains promising but should be cached because its BOJ integration
ended in 2026. Source URLs, matching policy, leakage rules, measurements, and
the staged experiment order are documented in
[`external_data_sources.md`](../reports/data/external_data_sources.md).
