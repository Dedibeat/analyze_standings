# Codeforces rating deflation and AI use (2026-11-18)

**Request.** Analyse Codeforces rating deflation related to AI use: when it
begins, and the evidence. The user offered a browser cookie.

**Data.** `scripts/cf_ai_deflation.py` uses the public API only (anonymous GET,
calls ≥2.1 s apart, 4 overlapping downloads). Everything is kept in
`data/cf_ai/` (270 MB, gitignored) at the user's request:
- `contest.ratingChanges` for all 1,286 finished non-gym contests since
  2018-01-01: 1,097 rated, 10,919,164 rows, 910,254 accounts. Every row's old
  rating equals the account's previous new rating, except 2 rows.
- `contest.standings` for the 673 rated contests since 2021-01-01.
- `replay.npz`: replayed deltas per contest.

Results are in `output/cf_ai_deflation.json`; the write-up is
[cf_ai_deflation.md](../reports/codeforces/cf_ai_deflation.md).

**Choices.**
- Internal rating of new accounts since May 2020: displayed + 1400 − bonuses
  so far (500/350/250/150/100/50). Before May 2020 new accounts started at a
  displayed 1500.
- An established player has 10 or more earlier rated contests in the window.
- Baselines were fixed before any post-2023 number was looked at:
  - 12-month windows starting 2021Q1–2023Q2;
  - 22-month windows starting 2021Q1–2022Q3.
- 2019–2020 is not comparable. Established players gained 40–100 more per
  year then, from the May 2020 new-account rule and the COVID influx.
- Onset is dated by a two-mean change point on monthly series from 2022-01.

**Findings.**
- **Size.** Established players, 2025-01 → 2026-11, compared with the mean of
  the pre-AI 22-month windows:

  | band | loss |
  |---|---|
  | 1400–1599 | 37 |
  | 1600–1899 | 63 |
  | 1900–2099 | 87 |
  | 2100–2399 | 86 |
  | 2400+ | 113 |

  Against the last pre-AI windows only (starting 2022Q1–Q3), the losses are
  88–111. Below 1400 there is no deflation. The baseline itself varies by
  ±16–37.
- **12-month windows** fall below the baseline range from the windows starting
  2024Q4 (2100–2399), 2025Q2 (1600–2099) and 2025Q3 (2400+). All of these end
  after mid-2025. The windows starting 2025Q3–Q4 reach:
  - −42 to −66 for 1600–2399;
  - −87 and −137 for 2400+.
- **Onset: January–February 2025**, right after DeepSeek-R1 (01-20) and
  o3-mini (01-31). Four monthly series change at once:
  - rank-driven delta of established 1900+ players: 2025-02, +0.8 → −2.7 per
    contest;
  - new accounts in contests 7–10: 2025-01, −3.7 → +3.0;
  - +200 jumps by established players under 1600: 2025-02, 3.8 → 6.3 per
    1,000;
  - established 1000–1599 on problems ≥600 above them, observed/expected
    solves: 2025-02, 0.30 → 0.78.
- **No clear step at o1 or the Codeforces AI rule** (2024-09). The
  problem-level series is 0.42–0.51 in 2024-10 to 2025-01, but single pre-AI
  months reached 0.50–0.54.
- **AI signature.** On problems at or below the player's rating,
  observed/expected stays flat. The excess grows with the gap, in every band:
  1400–1599 on problems ≥800 above went from 0.33 (2023H1) to 0.78 (2025H2).
  Pre-AI, solve chances fell off steeply with problem rating; since 2025 they
  fall off much less.
- **Div. 2 median problem rating by position** fell: D 1900 → 1600, E
  2300–2400 → 2100, C 1400–1500 → 1300. Kept as context only, since easier
  sets would also do it.

**Codeforces' hidden new-account rule (found on the way).**
- The published formula (blog entry 20762), replayed, matches 90–93% of
  2018–early 2019 deltas exactly.
- Since mid-2020 it misses established low-rated players in rounds with many
  new accounts by up to −13 per contest. This is the "mathematically
  impossible deflation" posted in the community (blog entry 154911).
- Seeding new accounts in their 2nd–6th contest one bonus step lower closes
  the gap to about ±2 per contest, but only about 10% of deltas match exactly.
  The precise rule is unknown.
- The residual is flat 2021–2026 under both seedings. So the rule is a
  standing drain on players under 1600, not the AI-era change.

**Weaker or negative evidence, kept.**
- The raw count of +200 jumps did not rise (about 950–1,000 per half-year).
  The rate rose because fewer established low-rated players take part.
- New accounts reaching 1900 within 10 contests kept falling (13.0 per 1,000
  in 2022H2, 7.1–7.7 in 2025).
- Rated participations per month fell from 152,061 (2024H1) to 104,453
  (2026H1). Not tested as a cause.

**Cookie.**
- Not used for the API.
- An auto-mode check first blocked the cookie request. The user then approved
  that exact command.
- Codeforces blog pages still returned Cloudflare's 403 challenge, even with
  `cf_clearance` and the exact browser headers from the user's "Copy as cURL"
  (the TLS fingerprint differs).
- Blog 154620 ("Codeforces rating deflation", mid-2026: 150–190 points
  January 2025–June 2026) is therefore known from search excerpts only.
- No cookie was written to disk. The scratch challenge pages were deleted.
- `curl_cffi` impersonation, used here for QOJ, was not tried.

**Open.**
- Read blog 154620 in full (saved page or `curl_cffi`) and reconcile its
  150–190 with our 63–113.
- Pin down the exact new-account seeding rule.
- Test the participation drop as a cause.
