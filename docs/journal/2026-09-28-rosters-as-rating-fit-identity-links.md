# Rosters as rating-fit identity links (2026-09-28, experiment, not shipped)

**Question.** Can the online-round rosters improve the rating fit? The other new
findings do not touch the fit. The CJK-radical bug is in `online_schools.csv`
only: the fit's member normalizer (NFKD) folds Kangxi radicals, and only 10
Radicals Supplement characters occur in the fit data (one member name). ρ, the
aliases and TabFM do not feed the fit.

**What was missing.** QOJ 1794/1799 (2024 online rounds 1/2) and 2513/2524 (2025
rounds 1/2) are in the fit, but their rows carry members on only 4–9 rows each.
Their ~2,400–2,600 teams per round therefore link to other contests only through
trusted team names (mostly to each other). The 2024 boards embed the school
(`team (<b>school</b>)`), and the 2024 rosters were already in
`online_rosters.csv`.

**Method** (scratch scripts; `tagged.json` untouched). Members from the same
round's roster were attached to rows without them. The key is school + team for
2024 and a unique team name for 2025, and the solved count had to match the PKU
ranking; zero-solve rows are absent from the ranking and match by key alone.
Attached rows: 2,315 / 2,423 (2024) and 2,185 / 2,449 (2025). Rows in the 2025
rounds linked to a non-online contest rose from 240 / 205 to ~1,400 / ~1,300.
Variant A attaches 2025 only; B attaches 2024 and 2025.

**Results.**

- **North-star metric** (`arch_b.metric`, this machine): baseline **245.4**, A 245.5,
  B 246.3, i.e. neutral within the 5-point keep threshold. Every guard is
  unchanged (gym EC 0.977, Kattis 0.795, raw LOCO 246.9). The CF anchors contain
  no Asia East regional, which is where the links act.
- **Held-out Asia East cells.** A fixed 20% of cells, keyed by contest, row and
  problem, was hidden in the 36 contests sharing ≥50 teams with the online
  rounds, and the survival fit was scored on those 67,063 cells. Log loss:
  baseline 0.22088; A 0.22038 (Δ −0.00050 [−0.00107, −0.00005]); B **0.22020
  (Δ −0.00069 [−0.00141, −0.00005])**; AUC 0.9701 → 0.9704. The 2024–2025
  contests improve (most −0.002 to −0.005). The 2022–2023 ones get slightly
  worse (+0.0003 to +0.0017), because identities are season-agnostic, so later
  online form leaks into earlier seasons' abilities. The size is comparable to
  the supplemental-contest corroboration (−0.00044).
- **What moves** (full fits, B − baseline). The four online rounds' own problems
  become **35–54 rating points easier** (2025 r2 −54, r1 −45, 2024 r1 −38, r2
  −35). Their level had rested on the ~200 teams linked before. Regional
  problems barely move (mostly under 5 points; mean |shift| 1.9 over 3,159
  problems).

**Verdict.** This is a small, real gain for Asia East prediction and a
correction of the online-round problem levels. It is not a metric win. Shipping
it would mean attaching members in the data layer (or at load time from
`online_rosters.csv`) and accepting the slight 2022–2023 regression, or pairing
it with season-scoped identity for these rows.
