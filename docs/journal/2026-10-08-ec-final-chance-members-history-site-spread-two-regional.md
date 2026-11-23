# EC-Final chance: members' history, site spread, two-regional plans (2026-10-08)

**Request.** Pull, fix the merge conflict, improve the EC-Final qualifying
prediction, and choose between Hong Kong, Shenyang, Shanghai and Nanchang.

**Merge.** Local master and `origin/master` (eb9fe8a) had each appended
sections to this file; both were kept (b20eecf). All 132 tests passed.

**2026 rules re-read** (icpc.pku.edu.cn, the PDFs read through the site's
pdf.js viewer):
- **EC-Final 名额分配办法 (2026-09-03).** 280 official seats: 240 from the
  regionals (230 mainland by the round-robin, 10 Hong Kong), up to 40 reward
  seats (WF 2023–2025 schools, hosts and setters), and up to 10 incentive
  seats (激励名额). Schools without a seat apply for an incentive seat, judged
  on their regional results. Seats left after round 2 go to applicants,
  schools with few seats first.
- **Hong Kong (2026-08-28).** HKU, 2027-01-09/10, ~120 teams including ~5
  star. 95 non-local seats: round 1, one team per school until **10-30**
  (ranked by online rank if more than 95 register); round 2, one extra team
  first-come before 11-14; round 3 by application. Up to 10 EC-Final places go
  to Hong Kong gold/silver/bronze teams in rank order, skipping a team with
  any member on the mainland round-1 list and schools at 3 − x.
- **Shenyang (2026-09-04).** 11-14/15 at Northeastern University, 400 seats:
  320 online (schools 1–100 two, 101–220 one), 50 WF/host/setter, 10 girls,
  20 provincial.
- **Regionals per student.** None of the 2026 notices read (EC-Final, Hong
  Kong, Shenyang, Nanjing guide) limits it. The 2023 Macau and 2024 Hong Kong
  notices allowed two EC regionals per student. In the data, official students
  at three mainland sites were 3 (2023), 6 (2024) and 0 (2025) of ~4,000–4,800.
  Of the online-roster members of Hong Kong-linked teams, 12 of 362 (2024) and
  14 of 298 (2025) also played two or more mainland sites (the roster and the
  Hong Kong line-up can differ by one member). Treated here as two regionals
  per student, Hong Kong included; **this needs the organisers' confirmation.**

**Registered fields are not available.** PTA's API returns
`REG_TEAM_NOT_PUBLISHED` for every 2026 regional (Xi'an, Chengdu, Wuhan,
Nanjing, Shanghai), and the site's own page shows the same error. Shanghai
registration is open until 11-01; Shenyang and Nanchang are not on PTA yet.

**1. Members' previous-season results (shipped in `scripts/ecfinal_chance.py`).**
`h` = logit of the best official rank / field any member reached at a
mainland regional in the previous season, plus a has-history flag.
- **Name matching.** Latin names are compared as sorted lower-case words,
  because boards swap the name order. English board school names map to the
  ranking's Chinese name (`school_names_en.csv`), because NUM appears both as
  "National University of Mongolia" and as "蒙古国立大学(Монгол Улсын Их
  Сургууль)". The TabFM table (`data/tabfm_gold/forecast_2026.csv`) misses
  Tamir's Nanjing 2025 #168 for that reason.
- **Held-out log loss** of P(rank ≤ the season's real qualifying rank),
  contest bootstrap:

| test season | teams (with history) | online only | + history | Δ |
|---|---|---|---|---|
| 2024 (train 2023) | 1,939 (1,056) | 0.3184 | 0.3036 | −0.0148 [−0.0251, −0.0031] |
| 2025 (train 2023–2024) | 2,019 (1,162) | 0.2847 | 0.2735 | −0.0113 [−0.0176, −0.0054] |

  The gain is larger than knowing each site's actual field (next item).
- **Hong Kong.** The same term, with members taken from the linked online
  roster, is a wash there (2024: 0.4043 → 0.4024; 2025: 0.2877 → 0.2887; 95 of
  221 teams have history), so the Hong Kong model stays online-only.

**2. Site differences are real but not predictable before registration.**
- **Size.** Per-contest intercept shifts (slopes fixed, K = 60/75/90) run from
  −0.79 (Hangzhou 2023) to +0.53 (Chengdu 2024). The between-site SD net of
  noise is 0.38 log-odds, about 8–18% around a 12% team. Shenyang:
  +0.09 / +0.04 / +0.48 (2023–2025). Shanghai: +0.47 / +0.01 (2024–2025).
- **Predicting a held-out season's offsets** (scratch script on
  `data/tabfm_gold/teams.csv`, history model; Δ log loss vs no offset):

| predictor | 2024 | 2025 |
|---|---|---|
| actual field (oracle offsets) | −0.0114 [−0.0184, −0.0054] | −0.0069 [−0.0120, −0.0022] |
| same site's earlier offsets, shrunk by 0.5–2 contests | +0.0007 to +0.0020 | −0.0005 to −0.0008 |
| capacity | −0.0053 [−0.0087, −0.0013] | +0.0027 [−0.0073, +0.0126] |
| last mainland site of the season | −0.0044 [−0.0076, −0.0020] | +0.0037 [−0.0024, +0.0135] |
| calendar order | −0.0029 [−0.0088, +0.0026] | +0.0034 [−0.0022, +0.0096] |
| two-slot band | −0.0013 [−0.0026, −0.0001] | +0.0029 [−0.0064, +0.0122] |
| slot-rule 10% line | −0.0011 [−0.0038, +0.0010] | +0.0022 [−0.0093, +0.0111] |
| quota share | +0.0010 [+0.0005, +0.0016] | +0.0002 [−0.0025, +0.0031] |

  None helps in both seasons; the online-only model gives the same picture.
  So every mainland site gets the same number, and the spread only widens its
  interval. The last site was the hardest in 2023 (Hangzhou) and 2024
  (Kunming), but not in 2025 (Shanghai +0.01). Nanchang 2026 is the last
  mainland site and has no history.

**3. Two regionals.** A team-season effect u ~ N(0, τ²) is shared by a
team's sites; the conditional log-odds are scaled so the marginal
probabilities stay the same.
- **Fit.** τ = 1.05 by maximum likelihood on 1,926 teams at two mainland
  sites, and 0.80 on 137 Hong Kong + mainland pairs (2024–2025).
- **Check.** It reproduces the earlier raw check: at online #400–700, "at
  least one of two" was 22.9% against 13.3% per site (×1.72); the model gives
  ×1.77.
- **Mainland + Hong Kong** = 1 − P(miss the mainland and miss Hong Kong),
  because Hong Kong places go only to teams that are not on the round-1 list.

**NUM-R^3** (online #544 / #349). Members' best 2025 mainland rank / field
is 0.50 (Tamir, Nanjing #168; Dugarjantsan, Shanghai #209 = 0.63).
P(EC-Final seat | plays):

| plan | P | 10–90% |
|---|---|---|
| one mainland site (Shenyang, Shanghai or Nanchang alike) | 12.2% (was 13.8% online-only) | model 10.7–13.8%; with site spread 7.6–18.1%; K = 70 / 80: 10.3% / 14.3% |
| Hong Kong | 19.0% | 17.3–21.7% (needs Hong Kong rank ≤ 32–37) |
| two mainland sites | 21.6% | independent sites would give 23.0% |
| one mainland site + Hong Kong | 27.9% | independent 28.9% |
| two mainland + Hong Kong (only if Hong Kong is outside the limit) | 34.0% | τ = 1.05 for all three |

NUM-MNM: 3.9% / 6.0% / 6.6% / 8.9% (one mainland / Hong Kong / two mainland /
mainland + Hong Kong). Every other NUM team is at most 1.5% per mainland site.

**Answer to the site question.**
- **Under the two-regional limit, Hong Kong + one mainland site (27.9%) beats
  two mainland sites (21.6%).** Hong Kong alone (19.0%) also beats any single
  mainland site (12.2%).
- **NUM's own Hong Kong record points the same way but is not in the
  model.** In 2025, N^3 was #30 (silver) and NUM-NTN #42 (bronze). The Hong
  Kong data are too thin to test a members' Hong Kong-history term.
- **Shenyang vs Shanghai vs Nanchang: no measurable difference before the
  fields are known.** Choose on cost, travel and dates (Shenyang 11-14,
  Shanghai 12-05, Nanchang 12-19). A weak, unvalidated tie-breaker: Shenyang
  and Shanghai were never harder than average in their five contests, while
  Nanchang is new and the last mainland site.
- **Deadlines.** Hong Kong round 1 closes 10-30, one team per school, so
  register NUM-R^3. Shanghai registration closes 11-01.
- **Not modelled:**
  - an incentive-seat application;
  - reward and incentive teams on the round-1 list, which would make the Hong
    Kong depth slightly deeper (better for NUM);
  - the members' Hong Kong record;
  - 2026 form changes.

**Next step once PTA publishes the lists.** Actual-field offsets cut held-out
log loss by 0.007–0.011, so the registered fields would make the mainland site
choice data-driven.

Run (~30 s; on Windows set `PYTHONUTF8=1`):
`python scripts/ecfinal_chance.py [--team '*'] [--school NAME]`.
Tests: `tests/test_ecfinal_chance.py`.
