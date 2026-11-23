# Online results, slot rules and regional gold chances (2026-09-27)

**Provenance.** A ChatGPT session (shared link, reviewed 2026-09-27) built an
online/slot-rule data layer, bronze-cutoff tweak, online→regional mapping, a
gold model, NUM probabilities, a provisional Hong Kong model and a rating-fit
comparison, but none of it reached GitHub (every push returned 403) and the
share omits all code and tool output. That work was **rebuilt from official
sources**, not copied; GPT's numbers are not reused.

**Data layer** (`scripts/build_ec_online_data.py` → `data/ec_online/`; raw
downloads cached in git-ignored `data/ec_online_cache/`):

- `online_teams.csv` — every team of both official online rounds 2022–2026
  (22,701 rows) from the icpc.pku.edu.cn ranking PDFs. Layouts differ by year
  (centred wrapped cells in 2022–23, left-aligned tables since 2024), so the
  parser reads word coordinates (`pdftotext -tsv`), finds column boundaries at
  the x crossed by the fewest words, anchors rows on the solved-count column
  (2023–24 list zero-solve teams without a rank) and assigns wrapped name
  fragments to rows by a DP that keeps each cell contiguous and centred on its
  row. Every ranked school parses to a school in the official school ranking.
- `online_schools.csv` — per-round and combined school rankings (the combined
  ranking drives slot rules; NFKC fixes the 2026 PDF's CJK radical code points).
- `online_rosters.csv` — registration lists (报名公示) with members for
  2022–2024. **2025–2026 lists exist only on uep.pintia.cn (PTA)**; an
  automated fetch was not possible in this session, so 2025 links rely on names.
- `regional_teams.csv` — every team of the 28 ordinary 2022–2025 regionals from
  XCPCIO: official flag (explicit `group`, or the per-team `official` field on
  47th/48th boards), standings recomputed from `run.json` (ICPC penalty, CE not
  counted), official rank and medal. Medal counts come from the board config,
  which equals ⌈10%⌉ of official solvers for 2024–25 and most of 2023; the 47th
  boards carry a constant 35/70/105 placeholder, so 2022 uses the 10/20/30%
  rule. Solved counts agree with QOJ for ~99% of name-matched teams.
- `slot_rules.json` — hand-encoded 2023–2026 site notices: rank bands on the
  combined school ranking, the "≥3 teams in the top N" clause, per-school caps,
  capacity and approximate non-online quotas. Checked against the one published
  per-school allocation (Shanghai 2025): the band rule reproduces all 178
  schools' online slots exactly. 2022 notices describe online-held contests with
  different rules and are marked, not encoded. Hong Kong/Macau allocate by
  registration (one team per non-local school, ranked by online school rank if
  oversubscribed).

**Linking.** School + team name links only 45–56% of official regional teams
(teams rename after the online rounds); adding roster matches (≥2 shared
members at the same school) raises 2022–2024 to 78–86%. Remaining teams mostly
entered through non-online quotas. 2025 stays name-only (~54%). Hong Kong/Macau
use English names and are unlinked.

**Model (`arch_b.online_gold`).** Online strength `x = −mean(log online rank)`
over the rounds entered (beat best-round and percentile variants overall;
percentiles drift because round sizes vary 1,745–2,500). A site's *rules line*
is the strength of the G-th best rule-admitted team (each school's best k
teams, k = rank-band + team-count slots, capped; G = 10% of official capacity).
`logit P(gold) = c + b·x + d·line`, fit on linked official mainland teams
2023–2025 (4,962 rows).

**Held-out results** (log loss; Δ vs online-only with contest-bootstrap 95% CI;
numbers in this section predate the 2026-09-27 school-name/tie-break fixes —
updated values are in the next section):

| model | 2024 (1,938 teams) | 2025 (1,282 teams) |
|---|---|---|
| online only | 0.1658 | 0.1614 |
| + same-site history | +0.0001 [−0.0008, +0.0010] | **+0.0046** [+0.0005, +0.0097] |
| + rating-fit CF gold bar history | −0.0000 [−0.0006, +0.0005] | **+0.0008** [+0.0001, +0.0017] |
| + rules line | **−0.0004** [−0.0008, −0.0000] | **−0.0013** [−0.0028, −0.0000] |
| + rules line, quota-adjusted (ρ from earlier seasons; shipped) | **−0.0005** [−0.0011, +0.0001] | **−0.0016** [−0.0044, +0.0000] |
| + oracle line (actual attendees) | −0.0017 [−0.0031, −0.0008] | −0.0044 [−0.0114, +0.0003] |

Online strength dominates (held-out gold rate ≈ prediction within ~15 points
in every rank bin). Slot rules add a small, consistent gain, largest where a
site's rules changed (Shenyang 2025: two-slot band 1–50 → 1–100); the fitted
line coefficient is ~20–45% of the strength slope because the nominal field
ignores which sites schools actually choose. Site history and the rating fit's
historical CF bars do not help and hurt in 2025, so they are not combined. A
quadratic strength term was mixed (worse 2024, better 2025) and not adopted.

**Rating fit vs online evidence.** With a shared slope and one intercept per
contest, each regional gets the online rank at which gold is a coin flip.
Across 16 regionals with a CF gold bar, Spearman with the bar is **−0.50**
(agreement; ≈ −358 CF points per unit log rank). The Shenyang swing is
corroborated by data that never touch the ratings: 2024 needed ≈ online #83
(bar 2703), 2025 ≈ #151 (bar 2382, easiest of all). Largest fit-minus-online
disagreements: Kunming 2024 **+151** (fit says much harder), Nanjing 2024
**−118**, Shenyang 2024 +92, Shanghai 2025 −90 — candidates for a
contest-level fit-bias audit, not proven bias (online-to-onsite form and
unlinked quota teams also move the online estimate).

**Quota entrants (measured, not assumed).** Seats the online bands do not
fill go to invitational, WF, host, provincial, girls' and wildcard teams. Per
2023–2025 mainland regional, each school's band slots were given to its
strongest-online teams present and the rest counted as quota entrants
(`quota_split`). Quota entrants win gold at **ρ ≈ 0.44** of band teams' rate,
stable from earlier seasons (0.44 from 2023 alone, 0.40 from 2023–24, 0.44 from
all); their share of golds is 21%/21%/25% by season, while per contest it is
noisy (9–37%, relative rate 0.16–0.89 on 3–15 quota golds), so ρ is pooled,
not per site. Band teams keep G·(1−q)/(1−q+ρq) of the G golds (q = planned
quota seat share = 1 − band slots/capacity); ρ = 0 was the first shipped line
(quota teams never win gold), ρ = 1 the online-slots-only alternative that
reproduces the ChatGPT order. The ρ-adjusted line improves on the ρ = 0 line in
both held-out seasons (table above; intervals just touch zero) and ships.

**2026 forecast** (`output/online_gold.md`, ρ = 0.443): easiest → hardest
Shenyang (line ≈ online #89) > Wuhan (#79) > Xi'an = Shanghai (#74) ≈
Nanchang (#73) > Chengdu = Nanjing (#68: one slot per top-160 school plus the
team-count clause). A team ranked #100 in both rounds: 69% / 65% / 62% / 59%.
Robust across ρ = 0, 0.44, 1 and GPT's order: Shenyang/Wuhan near the top,
Chengdu/Nanjing last; Xi'an/Nanchang move with ρ because of their ~100
invitational seats. The rating-fit chooser (`arch_b.medal_predict`) ranks
Wuhan hardest from its single 2025 contest; its city history did not help
held-out gold prediction.

National University of Mongolia (combined rank 128, one band slot at every
mainland site), conditional on attending: NUM-R^3 (online #544/#349) Shenyang
5.3%, Wuhan 4.5%, Xi'an/Shanghai/Nanchang 4.0%, Chengdu/Nanjing 3.6%; NUM-MNM
0.9–1.4%; the rest ≤ 0.5%. NUM's own record in `regional_teams.csv` points to
the unmodelled site: every NUM silver since 2022 came at Hong Kong/Macau
(official ranks 22–39 of 82–149 teams; 2025 N^3 30th with the gold line at
13th), while its mainland best is bronze (Hangzhou 2024 116th; Nanjing/Wuhan
2025).

**Pre-existing bugs found (not fixed here).** (1) `scripts/build_xcpcio_official.py`
treats every XCPCIO team as official when a board has no `group` field, but the
47th/48th boards carry a per-team `official` flag (e.g. Xi'an 2022: 476 official
+ 46 star, cache uses 522), so `arch_b.medals` includes star teams in 2022–23
medal cutoffs. (2) QOJ 1784 (Xi'an 2023) is mapped to XCPCIO
`48th/xian-invitational` instead of `48th/xian`; its medal bar is computed on a
34-team "official" field (4 golds, bar 2321). (3) `arch_b.medals` excludes QOJ
1197 (EC-Final 2022, named "ICPC") as an online qualifier; latent today because
1197 has no XCPCIO data.

**Limitations.** No 2025/2026 rosters (PTA); Hong Kong/Macau not modelled;
probabilities assume the team attends and the rest of the field follows the
rule-admitted pattern; 2022 excluded as an online-held regime.

Run: `python3 scripts/build_ec_online_data.py` (needs `pdftotext`, network) then
`python3 -m arch_b.online_gold [--school NAME]`.
