# East-Asia medal badges + lowest-gold analysis (`arch_b.medals`)

ICPC **Asia East Continent** regionals award medals by cumulative percentile of
the official teams that solved ≥1 problem: gold 10%, silver 30%, bronze 60%.
`arch_b.medals` assigns every problem of the medal-awarding EA contests a
**bronze / silver / gold / platinum / star badge** (weakest → hardest) and reports
the **lowest gold-medal team** per regional. Writes `output/medal_badges.json`
(`{"contests": [...], "problems": [...]}`); run
`./.venv/bin/python -m arch_b.medals`.

Key decisions:

- **Official field = XCPCIO team data** (replaced the old domjudge-id-prefix
  heuristic). ``data/xcpcio_ea_official.json`` caches XCPCIO official-team
  identity keys for 28 EA contests (regionals + EC-Finals, 2022–2025), fetched
  via ``scripts/build_xcpcio_official.py``. XCPCIO's team.json carries explicit
  ``"group": ["official"]`` tags for 49th/50th seasons; for older 47th/48th
  seasons the entire XCPCIO team list is the official field (domjudge-imported
  onsite teams). Teams are matched to QOJ standing rows by normalized
  name-matching (exact set intersection of candidate keys: bare name, org-name
  pairs with multiple separators, parenthetical-stripped variants, and
  member-stripped display_name_raw prefixes). Medal cutoffs are ranks
  ⌈0.10 n⌉ / ⌈0.30 n⌉ / ⌈0.60 n⌉ within the XCPCIO-identified official field,
  with ⌈ceil⌉ rounding (the official rounding rule is not in the data).
- **Scope: medal events only** (user decision). The 6 online qualifiers
  (contest_name ``"ICPC"``, 1.3–2.7k teams) and the EC-Final warm-ups award no
  medals and are excluded → 28 contests / 358 problems (2022–2025).  Includes
  EC-Finals (Shanghai 2023 = 48th EC-Final, China 2024 = 49th EC-Final).
- **The medal bar is an empirical 50%-crossing, not an Elo performance
  rating.** The original design compared the fitted difficulty `b_p` against
  `elo.performance_rating` of the cutoff teams. Measured against the cutoff
  cohorts' actual solve rates, that rank-inversion performance is **inflated on
  the Rasch/survival `b` scale** (predicted−actual solve rate +0.10 at the
  bronze cutoff, +0.34 at gold: gold-badged problems were solved by only ~10%
  of the gold band). Even the well-centred alternative — the ability whose
  *expected solve count* matches the cutoff team's (zero mean bias by
  construction) — is miscalibrated exactly at the decision point: where it
  predicts 50%, cutoff cohorts actually solve 57–92%, because EA fields' solve
  curves are far steeper than the global Rasch slope (the 2PL finding: EA
  discrimination ~2.1). So the bar is measured directly: per tier, take the
  ±7-official-rank cohort around the cutoff team, isotonic-regress its
  per-problem solve rates against `b` (PAVA, non-increasing), and set
  `bar_tier` = the `b` where the smoothed rate crosses 0.5. Badge = the weakest
  tier whose bar clears `b_p`, else **platinum** — still a threshold on the fitted
  difficulty, so badges are monotone in `b`, cross-contest comparable, and
  CF-mappable (the `calibrate` two-leg map is monotone, so CF-space badges are
  identical).
- **Star tier above platinum (the champion bar).** The badge ladder is
  bronze < silver < gold < **platinum** < **star** — platinum/star are *above* gold,
  not below bronze (a recurring misreading; the viewer spells it out). With
  only four tiers, "platinum" was 52% of all problems and lumped "just above the
  gold bar" with "solved by nobody", so one more crossing was added, anchored
  at the **champion cohort** (`TOP_COHORT = 5`, the top-5 official teams, exact
  cohort — no window): **platinum** = above the gold bar but the champions still
  solve it at even odds (it decides ranking *within* gold), **star** = beyond
  even the champions. This split the 200 platinum problems into **119 platinum + 81
  star**; star problems almost all have 0–2 official solves (a scarcity rule
  "≤2 official solves" selects a nearly identical set of 82, cross-validating
  the bar). A champion cohort that solves everything at ≥50% pins its bar to
  4000 → that contest has no star problems (HK & Macau 2022, Shenyang 2022 —
  correct: their top-5 were world-class). *Caveat:* 5 teams is the noisiest
  cohort of the four bars; in small/weak fields the star bar can sit close to
  the gold bar (Hong Kong 2024 gets 7 star problems, one solved by 11 teams).
- **Sanity badge: band majority.** A model-free column badges each problem with
  the weakest medal *band* (gold ranks 1..g / silver g+1..s / bronze s+1..z)
  where ≥50% of official teams solved it; if none, the top-5 majority splits
  platinum (≥50%) from star. Agreement with the model badge is
  **74%** (282/383) and the disagreements are almost all one step in the
  expected direction: the band's *median* team is stronger than the boundary
  team, so the band-majority badge skews one tier easier. The medal-bar badge
  is primary because the medal semantics is about the boundary ("what you
  needed to solve to reach the tier").

Results (current run): badge totals **86 bronze / 36 silver / 40 gold / 92
platinum / 104 star** (28 contests, 358 problems). Internal consistency:
the non-platinum badge count per contest ≈ the lowest gold team's solve count
(e.g. Jinan 2022: 6 solves, badges BBBSGG; Wuhan 2025: 6, BBBGGG). The **gold
bar in CF points** spans [2137, 2932], median **2601**: hardest golds at
EC-Final 2024 "China" (2932) and EC-Final 2023 "Shanghai" (2897); softest at
Grand Prix of Shenyang 2025 (2137). The lowest gold team solves 4–8 problems
and its classic Elo rank-inversion performance sits at 2184–2502.

**Viewer (`arch_b.export_medal_viewer` + `medal_viewer_template.html`).**
`output/medal_viewer.html` is the interactive presentation of the analysis —
self-contained (data embedded, no server, vanilla JS/SVG), light/dark aware via
`prefers-color-scheme`. Sections: a season filter scoping everything below; a
KPI row (contest/problem counts, median gold bar, model↔empirical agreement,
badge-distribution stacked bar); a dot-range chart of the three medal bars per
contest in CF points (sorted by gold bar, hover tooltips showing all three
cutoff-team details, click-to-open, URL hash `#<contest_id>` like the other
viewers); a contest detail view (three cutoff-team panels for gold/silver/bronze
with solved count, penalty, full-field rank, and Elo performance; problems
as lettered lollipop dots on the difficulty axis against the medal-bar
threshold lines and a shaded platinum zone, plus a per-problem table with band
solve-rate meters and a † marker where the empirical badge differs); and a
sortable gold-cutoff-team table. The detail strip shades both the platinum zone
(gold bar → star bar) and the star zone (beyond the star bar), the table
carries a Top-5 (champion) solve-rate column, and a star bar pinned at the
scale ceiling renders as "— (champions solve all)". Design notes: badge colors
are medal-semantic (bronze/silver-blue/gold/violet platinum/red star) and were
**validated with the dataviz palette checker in both modes** (5 slots, worst
adjacent CVD ΔE ≥ 58; the gold hue is
sub-3:1 on the light surface, mitigated by letter labels on every chip and the
table views); all dynamic text is inserted via `textContent` (team names in
the data contain raw HTML fragments, which the exporter also strips). One
bug worth remembering: the per-row transparent SVG hit-rect must be appended
*last* in its group — appended first, the row's dots/line/label paint above it
and swallow every click (SVG hit-tests in paint order).
