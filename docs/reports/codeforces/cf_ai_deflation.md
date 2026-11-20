# Codeforces rating deflation and AI use (2026-11-18)

Question (user): is Codeforces rating deflating because of AI use, when did it
begin, and what is the evidence?

## Answer

- **Yes, for established players rated 1400 and up.** Over January 2025 to
  November 2026 (22 months), established players lost rating relative to the
  same rating band in pre-AI windows of the same length:

  | band | loss |
  |---|---|
  | 1400–1599 | about 37 |
  | 1600–1899 | about 63 |
  | 1900–2399 | about 86 |
  | 2400+ | about 113 |

  In pre-AI windows of the same length, the same comparison varies by only
  ±16 to ±37. Below 1400 there is no deflation.
- **It began in January–February 2025.** Four independent monthly series all
  change in January or February 2025. That is right after DeepSeek‑R1
  (2025‑01‑20) and o3‑mini (2025‑01‑31, free in ChatGPT).
- **There is no clear trace in September 2024** (o1‑preview/o1‑mini on
  2024‑09‑12, the Codeforces AI rule on 2024‑09‑14). The problem-level series
  rises a little from October 2024, but single pre-AI months reached the same
  level (0.50 in 2022‑04, 0.54 in 2024‑04).
- **The deflation works through ranks, not through a rule change.**
  - Codeforces' formula, replayed on every contest, explains the actual
    deltas equally well before and after 2025.
  - What changed is who finishes ahead of whom. Established 1900+ players now
    finish worse than their rating predicts.
  - New accounts turned from net donors of rating into net takers.
  - Low-rated established players solve problems far above their rating at
    2–3 times the old rate. Rating-based honest improvement does not produce
    that pattern; in-contest AI help does.

## Data

- **Downloads.** Public API only (anonymous GET). The cookie the user offered
  was not needed for the API and could not pass Cloudflare for blog pages;
  see the end of this report.
- **Rating changes.** `contest.ratingChanges` for all 1,286 finished non-gym
  contests from 2018‑01‑01 to 2026‑11‑18:
  - 1,097 contests have rating changes;
  - 10,919,164 rows, 910,254 accounts;
  - every row's old rating equals the account's previous new rating, except
    2 rows.
- **Standings.** `contest.standings` for the 673 rated contests since
  2021‑01‑01: per-problem solves and problem ratings.
  - Div. 3 and Div. 4 standings list only trusted participants.
- **Cache.** `data/cf_ai/` (270 MB, gitignored; see the README). Results are
  in `output/cf_ai_deflation.json`; tables are printed by
  `scripts/cf_ai_deflation.py --analyze`.

## Definitions

- **Internal rating.**
  - Since May 2020 a new account shows 0 but is rated from an internal 1400.
  - Its displayed rating gets bonuses of 500/350/250/150/100/50 over its first
    six contests.
  - So internal = displayed + 1400 − bonuses so far. After six contests,
    displayed = internal.
  - Before May 2020 new accounts showed 1500.
- **Established player** ("veteran" in the code): 10 or more earlier rated
  contests since 2018.
- **Baselines, fixed before any post-2023 number was looked at.**
  - 12-month windows that start 2021Q1–2023Q2, so all of them end by mid-2024.
  - 22-month windows that start 2021Q1–2022Q3.
  - 2018–2020 is not comparable. The May 2020 new-account rule changed how
    much rating new accounts feed to everyone else: established players gained
    40–100 more per year in 2019–2020 windows.
- **Expected solve:** 1 / (1 + 10^((R − r)/400)) for problem rating R and
  player rating r. This is the Elo curve Codeforces problem ratings are built on.

## 1. Size: the same players, before and after

The same established players are followed for 12 months: they must have
played in the half-year before the window's start and in the half-year before
its end. The table shows their rating change minus the baseline mean for
their band. Rows are dated by the window's start.

| window starts | 1200–1399 | 1400–1599 | 1600–1899 | 1900–2099 | 2100–2399 | 2400+ |
|---|---|---|---|---|---|---|
| baseline range | −27.5..+23.6 | −22.8..+26.6 | −30.1..+31.5 | −27.6..+25.0 | −12.7..+13.5 | −24.3..+18.9 |
| 2024Q1 | +1.1 | +5.6 | +19.7 | +26.5 | +15.3 | +40.1 |
| 2024Q3 | −1.3 | −9.5 | −0.8 | −0.4 | −8.9 | +37.6 |
| 2025Q1 | −1.3 | −13.0 | −23.1 | −23.8 | −24.6 | +1.3 |
| 2025Q2 | −11.9 | −20.5 | −34.2 | −35.7 | −34.7 | −19.2 |
| 2025Q3 | −9.5 | −28.0 | −47.0 | −59.8 | −62.6 | −87.3 |
| 2025Q4 | −10.5 | −29.7 | −41.9 | −59.4 | −65.8 | −136.7 |

- Below 1200 the change stays inside the baseline range: +14.7 (2024Q4 and
  2025Q1), +9.2, +9.8 and +0.8 (2025Q2–Q4).
- Each window holds 22,000–27,000 players.
- The 2025Q3 and 2025Q4 windows end in July and October 2026.

**22-month total.** The window from 2025‑01‑01 to 2026‑11‑01 holds 12,111
players. Its change minus the mean of the 22-month baseline windows:

| band | 2025‑01 → 2026‑11 vs baseline | baseline range |
|---|---|---|
| <1200 | +15.1 | −51.1..+25.2 |
| 1200–1399 | −9.1 | −34.1..+23.7 |
| 1400–1599 | −37.4 | −33.7..+27.4 |
| 1600–1899 | −62.7 | −31.2..+34.4 |
| 1900–2099 | −86.6 | −36.2..+36.9 |
| 2100–2399 | −86.3 | −15.8..+20.6 |
| 2400+ | −113.4 | −18.1..+11.3 |

- **The baseline choice moves these numbers.** The 2021 windows sit low
  (post-COVID), the 2022 ones high.
- **Against the last pre-AI windows only** (starting 2022Q1–Q3), the losses
  are about 88 (1600–1899), 111 (1900–2099), 92 (2100–2399) and 110 (2400+).
- **Community estimate.** Codeforces blog entry 154620 (mid-2026) estimates
  150–190 points for January 2025 to June 2026, "after accounting for natural
  improvement". Only search excerpts were readable, so its cohort and baseline
  could not be compared.

## 2. When it begins: change points

Each series is fitted with two means, monthly from 2022‑01 to 2026‑10, and the
month of the best split is reported.

| monthly series | change month | before | after |
|---|---|---|---|
| established 1900+: rank-driven delta per contest (formula replay, minus its 2021–23 mean) | 2025‑02 | +0.8 | −2.7 |
| new accounts in contests 7–10: internal delta per contest | 2025‑01 | −3.7 | +3.0 |
| established <1600: one-contest gains of +200 or more, per 1,000 | 2025‑02 | 3.8 | 6.3 |
| established 1000–1599 on problems ≥600 above them: observed / expected solves | 2025‑02 | 0.30 | 0.78 |

**Monthly values around the onset.**
- Problem-level series: 0.26 (2024‑06), 0.28 (2024‑09), then 0.43, 0.51, 0.42
  and 0.50 for 2024‑10 to 2025‑01. From 2025‑02 it reads 0.60, 0.66, 0.72,
  0.51, 0.81, and reaches 1.15 in 2025‑08.
- Jump rate: every month from 2023‑07 to 2025‑01 is 2.96–4.97; from 2025‑02 on
  it is 4.17–8.47.

## 3. Mechanism: who takes the points

**The formula is unchanged.** The published algorithm (Codeforces blog entry
20762) was replayed on every contest since 2019‑06. In 2018–early 2019 it
reproduces 90–93% of deltas exactly.
- Since mid-2020 it misses established low-rated players in rounds with many
  new accounts by 3–13 points per contest. This is the "mathematically
  impossible deflation" reported in the community (blog entries 154911 and
  related).
- Seeding new accounts in their 2nd–6th contest one bonus step lower
  (displayed + 1400 − bonuses including the next one) closes the gap. The
  replay then matches established players within about ±2 points per contest
  in every band and half-year. Exact matches stay at about 10%, so the precise
  rule is still unknown.
- Under either seeding, the error is flat from 2021 to 2026. Seeding A, the
  natural reading, leaves −9.7..−13.3 per contest below 1200. So this
  new-account rule is a standing drain on low-rated established players, not
  an AI-era change.

**Rank-driven deltas of established players** (seeding B, mean per contest):

| band | 2023H1–2024H2 | 2025H1 | 2025H2 | 2026H1 |
|---|---|---|---|---|
| 1900–2099 | −1.03..+0.47 | −3.10 | −4.61 | −5.51 |
| 2100–2399 | −6.21..−3.75 | −8.64 | −7.51 | −9.11 |
| 2400+ | −1.83..+4.72 | −0.60 | −0.90 | −11.41 |

**New accounts, mean internal change per contest:**

| stage | 2022H2–2024H2 | 2025H1 | 2025H2 | 2026H1 |
|---|---|---|---|---|
| contests 1–6 | −62.5..−66.7 | −62.6 | −59.1 | −57.4 |
| contests 7–10 | −5.0..−1.9 | +2.3 | +2.3 | +3.9 |

**Jumps by established players under 1600** (+200 or more in one contest):
- The rate rose from 3.8 to 6.3 per 1,000.
- The raw count did not rise (about 950–1,000 per half-year, 2021H2–2025H2).
  The rate rose because fewer established low-rated players take part.
- Jumps already "stuck" well in 2023H2: +74 over the next five contests.
- So the jumps are supporting evidence only.

**Fast climbers are not the channel.** New accounts reaching 1900 within ten
contests kept falling: 13.0 per 1,000 in 2022H2 and 7.1–7.7 in 2025. So
cheating does not mainly show up as accounts racing to Candidate Master.

## 4. AI signature in the problems

Observed / expected solves by established players, split by their rating band
and by how far the problem's rating R lies above their rating r. The
expectation is Codeforces' own Elo curve.

| band | R−r ≤ 0 | 0..200 | 200..400 | 400..600 | 600..800 | ≥800 |
|---|---|---|---|---|---|---|
| 1000–1199, 2023H1 | 1.11 | 1.09 | 0.84 | 0.62 | 0.22 | 0.12 |
| 1000–1199, 2025H2 | 1.16 | 1.31 | 1.09 | 1.10 | 0.95 | 0.82 |
| 1400–1599, 2023H1 | 1.02 | 1.22 | 0.91 | 0.55 | 0.44 | 0.33 |
| 1400–1599, 2025H2 | 1.04 | 1.34 | 1.42 | 1.19 | 0.99 | 0.78 |
| 1900–2099, 2023H1 | 1.00 | 1.13 | 1.12 | 0.80 | 0.71 | 0.18 |
| 1900–2099, 2025H2 | 1.00 | 1.24 | 1.50 | 1.52 | 1.14 | 1.11 |

- On problems at or below the player's rating nothing changed. The excess grows
  with the gap.
- **Pre-AI, the chance of solving fell off steeply** with the problem's
  rating. Since 2025 it falls off much less: hard problems are solved almost
  as often as the player's rating predicts for easy ones. That is the
  footprint of solutions that do not come from the player.
- The measure is **conservative**. Codeforces computes problem ratings after
  the round from the same solves, so cheater solves already pull R down.

**Problem ratings themselves fell.** Median rating by position in Div. 2
rounds:

| position | 2021H2–2024H1 | 2025H2 | 2026H1 | 2026H2 (to Nov) |
|---|---|---|---|---|
| C | 1400–1500 | 1300 | 1300 | 1300 |
| D | 1900 | 1800 | 1700 | 1600 |
| E | 2300–2400 | 2200 | 2100 | 2100 |

This can come from rating deflation, from cheater solves, or from easier sets.
So it is context, not evidence.

## Not the cause, or not tested

- **Codeforces' new-account rule.** It is real and drains low-rated
  established players, but it is unchanged since 2020 (section 3).
- **Natural improvement.** Handled by comparing each band with itself in
  pre-AI windows. The baseline still varies by ±16–37 over 22 months.
- **Fewer players.** Rated participations per month fell from 152,061 in
  2024H1 to 104,453 in 2026H1, and new accounts from 11,535 to 9,032 a month.
  The drop happens alongside the deflation. It was not tested as a cause.
- **Honest learning with AI tools.** It cannot be separated per account.
  However, it would raise solve rates near a player's level first, while the
  observed excess is concentrated 600+ points above.

## Limits

- Cheating is inferred from aggregate patterns. No account is identified, and
  no submission was read.
- Div. 3/4 standings omit untrusted accounts, so the problem-level test covers
  established accounts only.
- The exact Codeforces rule for new accounts in contests 2–6 is unknown
  (about 10% exact matches under the best seeding found).
- The 2026H2 rows are partial (to 2026‑11‑18). The latest 12-month window
  starts 2025Q4.

## Reproduce

    ./.venv/bin/python scripts/cf_ai_deflation.py --fetch-rc   # ~50 min, resumable
    ./.venv/bin/python scripts/cf_ai_deflation.py --fetch-st   # ~45 min, resumable
    ./.venv/bin/python scripts/cf_ai_deflation.py --analyze    # ~1.5 min with the replay cache

Model dates used as markers: o1‑preview/o1‑mini 2024‑09‑12; Codeforces "Rule
Restricting the Use of AI" 2024‑09‑14 (blog entry 133941); o1 2024‑12‑05;
DeepSeek‑R1 2025‑01‑20; o3‑mini 2025‑01‑31.

**Blog pages could not be read.** Codeforces blog pages answer 403 with a
Cloudflare challenge to curl and WebFetch. The user's cookies, including
`cf_clearance` and the exact browser headers, did not pass: the TLS
fingerprint differs. Blog content is therefore quoted from search excerpts.
