# EC-Final regional cutoff: how deep a mainland seat reaches (2026-10-01)

**Question.** Under the 2026 EC-Final rule (`The 2026 ICPC Asia East Continent
Final 名额分配办法`, icpc.pku.edu.cn, 2026-09-03), what regional rank wins one
of the 230 mainland seats? The rule: sites ordered by valid teams; admit rank 1
of each site, then rank 2, ...; skip a team sharing a member with an admitted
team (2025 公示 wording: "有 1 名选手相同") and schools already at 3 teams. Hong
Kong gives 10 more seats (medal teams only, after round 1). The notice has no
Mongolia-specific rule; Mongolian schools qualify like any other school, or
apply for one of the ≤10 incentive seats (激励名额).

**Method** (`scripts/ecfinal_cutoff.py`). Replays the rule on
`regional_teams.csv` (XCPCIO boards, official ranks recomputed from
`run.json`). Validated on 2025 with `--check-2025` (2026-10-07; corrects the
first pass, which assumed all 240 seats were mainland): Hong Kong had 126 valid
teams (< 130, "按给定数目提取" — the number is stated nowhere, neither in the
rule nor in the HK notice; **1 is inferred** from the 公示 counts, and HKU's seat
could instead be its Nanjing #92 team with Hot Kpop Union as a substitute) and gave **1** seat — HKU "Hot Kpop Union",
Hong Kong rank 7 (ranks 1–5 already held mainland seats; rank 6, Xiamen
University of Technology's two-member team, was passed over for an unstated
reason) — so the mainland had **239**. With 239 the replay matches the published
per-school qualifier seats (公示 Table 1, sum 240) for **125/125 schools**, and
233/240 teams appear in Table 2; the 7 others were swapped by their schools for
substitutes allowed by the 2025 rule (a school's top-90 regional team, top-15
at Hong Kong), e.g. 北京大学 飞带不长队 → 呆呆鸟. Outputs:
`output/ecfinal_2025_allocation.csv` (every entry examined, in order, with the
decision) and `output/ecfinal_2025_school_check.csv`. Sources: rule
https://icpc.pku.edu.cn/docs/2025-11/413b953ddb2f444794033d868ddbd07c.pdf,
公示 https://icpc.pku.edu.cn/docs/2025-12/0629355dfddf43fd8d34ffad3fd0a3bb.pdf.
2023/2024 still assume 240 mainland seats (their Hong Kong/Macau allocation was
not checked; at most ~1 rank of effect).

| season | mainland sites | 240 seats reach rank | 2026 rule (230 seats, 7 sites, 7/6 scaling) |
|---|---|---|---|
| 2023 | 6 | 87 | ~70 |
| 2024 | 6 | 86 | ~70 |
| 2025 | 6 | 91 (actual 84–91 by site) | ~75 |

2025 per site (239 mainland seats; the last went to Shenyang #91 in tier 91,
so an eligible team at rank ≤91 qualified at Wuhan/Shenyang and ≤90 at
Xi'an/Nanjing/Chengdu/Shanghai): last admitted Wuhan #88 (5 solved), Shenyang
#91 (4), Xi'an #90 (5), Nanjing #84 (4), Chengdu #90 (6), Shanghai #84 (5); the
gaps (e.g. Nanjing #85–90) were teams already admitted or capped. Every
last-admitted team was a silver medallist.

Only ~45% of teams above the cutoff are admitted (each team plays two sites;
top schools hit the 3-team cap), so the bar is far below 240/6 ≈ 40. Rank 70–75
was a silver medal at every 2024–2025 mainland site (4–6 solved). NUM's best
mainland ranks were 116 (Hangzhou 2024) and 168 (Nanjing 2025). The 7-site
figure is an estimate: it assumes the new Nanchang site adds admits at the
6-site average rate.

**2026 projection (`--project-2026`, 2026-10-01).** The 7/6 scaling above is
biased: in a leave-one-site-out test it overshoots the true 5-site depth by
5–11 ranks. Replaced by a replay: each season's real teams (school, number of
sites, strength = mean logit rank percentile) are redrawn onto the 2026
capacities (`slot_rules.json`, 7 sites, 2,516 seats vs 2,200 in 2025) with
Gaussian rank noise, 230 seats. The noise is calibrated so the same replay
reproduces that season's real 6-site depth (2024: 86 vs 86; 2025: 91 vs 91;
2023 is barely identified, every noise scale replays 87–89). The 316 extra 2026
seats bound the answer: as second sites of one-site teams (more duplicates,
deeper) or as new teams (shallower).

| base season | extra seats → second sites | extra seats → new teams |
|---|---|---|
| 2023 (weak calibration) | 70 (67–73) | 61 (58–63) |
| 2024 | 77 (75–80) | 71 (68–73) |
| 2025 | 79 (77–82) | 75 (73–77) |

Median (10–90%) qualifying rank. Estimate for 2026: **~75, plausible 70–80,
the same at every mainland site** (±1 by site order: Wuhan/Shenyang 400, Xi'an
380, Nanchang 360, Shanghai 336, Chengdu/Nanjing 320 by capacity). Rank 75 was
silver everywhere in 2023–2025 (4 solved at Shenyang 2025 / Nanjing 2024 /
Xi'an 2023, 6 at Chengdu). Untested: team-strength drift, Nanchang's field (no
history), and whether 2026 teams still play at most two sites.
