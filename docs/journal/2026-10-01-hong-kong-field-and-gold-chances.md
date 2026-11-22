# Hong Kong field and gold chances (2026-10-01)

**Question.** Can the Hong Kong field be estimated from earlier fields
(2022–2025), online ranks and previous results, and turned into a 2026 gold
forecast? Module: `arch_b.hk_gold`, built on the `arch_b.hk_link` links.

**Selection rules** (official notices; the PDFs' Chinese text was read through
the site's pdf.js viewer, because `pdftotext` returns only digits):

| | 2023 Macau | 2024 HK | 2025 HK | 2026 HK |
|---|---|---|---|---|
| date | 11-18/19 | 12-21/22 | 11-29/30 | 2027-01-09/10 (HKU) |
| non-local / local official seats | 65 / 15 | 95 / 15 | 100 / 20 | 95 / 20 |
| round 1 | 1 team/school, by online rank if oversubscribed | same | same | same, until 10-30 |
| round 2 | as round 1 (by 10-21) | first-come extra team | same | same, before 11-14 |
| round 3 | host/setter schools | applications | applications | applications |
| notes | max 2 EC regionals per student | same | not stated | up to 10 EC-Final places (below) |

The 2026 EC-Final places go to Hong Kong medal teams in rank order. A team
is skipped if any member is already on the EC-Final first-round list, and a
school gets at most 3 − x (4 − x with reward seats) such places.

**Field (2024/2025 linked teams):**
- Non-local schools: 107 and 110, of which 31 and 33 are top-50 by combined
  online rank. 62% of 2024's schools returned in 2025.
- Multi-team schools dropped from 28 to 1 in 2025.
- Coin-flip online rank (shared slope with the mainland contests): **#80
  (2024), #74 (2025)**, the hardest site of each season except Chengdu 2025
  (#79). Mainland sites ranged from #79 to #134.
- A school often sends a weaker team: the Hong Kong team is the school's best
  online team in only 39/118 and 34/97 cases.
- **11 of 13 and 9 of 12 linked golds had already won a mainland gold earlier
  that season.** Of the 14 and 13 teams that arrived with one, 11 and 9 won
  gold at Hong Kong.
- 2022 and 2023 are known only at school level, and their rules differed
  (2022: 2–3 teams per school; 2023: an 80-team Macau contest).

**Field prediction (train one season, test the other):**
- School attendance, logistic on previous Hong Kong attendance (t−1, t−2)
  and log school rank: AUC 0.87 (2024→2025) and 0.76 (2025→2024). Expected
  top-50 schools 34.4 vs 33 actual and 33.1 vs 31. A previous Hong Kong medal
  adds nothing.
- Turning attendance into a gold line does not work. Simulating which team
  each school sends (absolute online position by school-rank band, line = 10%
  of the linked share) gives absolute log-rank errors of 0.28 / 0.52, against
  0.23 for "same line as the training season".
- For 2026 the attendance model is also biased: both previous fields
  (2024/2025) were large, which the training seasons never had, so it
  predicts ~130 schools for 95 seats. Not used.

**Gold models (held-out log loss, expected / actual golds):**

| model | 2024 | 2025 |
|---|---|---|
| mainland online-only | 0.1026 (14.7 / 13) | 0.1227 (14.1 / 12) |
| mainland oracle line (actual HK field) | 0.1036 (11.1 / 13) | 0.1258 (9.4 / 12) |
| **HK online-only (other year)** | **0.1007 (12.3 / 13)** | **0.1165 (12.6 / 12)** |
| HK + earlier mainland gold | 0.0880 (12.5 / 13) | 0.1119 (12.3 / 12) |
| HK + member with previous-season gold | 0.1165 | 0.1219 |

- The mainland coefficients under-predict Hong Kong golds when given its
  actual field, because Hong Kong golds concentrate among strong online teams.
- Members' previous-season golds (8/13 and 10/12 golds had one) add nothing
  beyond online rank.

**2026 forecast** (`output/hk_gold.md`): Hong Kong-only model on 2024 + 2025
(215 teams, 25 golds), coin flip at **online #77**:

| | #25 | #50 | #100 | #200 | #300 |
|---|---|---|---|---|---|
| P(gold) | 94% | 75% | 34% | 8% | 3% |
| 90% CI (team bootstrap) | 85–99% | 57–89% | 21–50% | 3–13% | 1–6% |

- **Harder / easier field band:** the coin flip moved by ±0.253 in log rank,
  the SD of consecutive-season changes at the same mainland site (7 pairs). At
  #100 this gives 21% / 49%.
- **Update after the mainland contests:** P(gold) at #100 is 19% for a team
  without a 2026 mainland gold and 58% for one with it.
- **For comparison:** the mainland online-gold model gives 54–57% at #100.
  For the same online rank, Hong Kong is the harder gold.
- **NUM-R^3** (online #544/#349): **1.3%** (0.7–2.4% across the band); other
  NUM teams ≤ 0.3%.
- **Not modelled:** the new EC-Final places and the January date. The
  direction of their effect is unknown. Every Hong Kong gold in 2024/2025
  came from a team that also played a mainland regional, and teams already on
  the EC-Final list gain no EC place at Hong Kong in 2026.

**Hong Kong vs the rating fit.** The rating fit's CF gold bars put Hong Kong
in the middle or easy end: 2024 bar 2517 (4th of 6 with bars), 2025 2473 (5th
of 7), and the 2026 chooser ranks it easiest (2505). Online evidence ranks it
hardest. Added to the contest-difficulty comparison, Hong Kong 2025 is the
largest fit-minus-online gap of all 20 contests (−137 CF; Hong Kong 2024 −71),
and the Spearman correlation between coin-flip rank and CF bar falls from
−0.48 to −0.26. The online measure is checked directly on Hong Kong gold
outcomes (calibrated across years). The rating-fit chooser's within-season
pair ordering was 47.9%. So for "where does a given team have the better gold
chance", the online evidence is the one to use.

**Data gaps found:**
- The 2026 Hong Kong registration is not on PTA's public contest list. The
  2026 season shows the online rounds, the Shenzhen/Shenyang invitationals
  and Xi'an/Chengdu/Wuhan/Nanjing.
- Earlier PTA seasons need a login (`/api/seasons` returns
  `REG_REQUIRE_ADMIN_USER`), so it is unknown whether the 2024/2025 Hong Kong
  lists are there.
- The 2026 mainland registration team lists are public via
  `/api/teams/public` (not yet used).

Run: `python3 -m arch_b.hk_gold [--school NAME]` (needs the XCPCIO config
cache or network for contest dates, via `scripts/build_tabfm_gold_data.py`;
on Windows set `PYTHONUTF8=1`). Tests: `tests/test_hk_gold.py`.
