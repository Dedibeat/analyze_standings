# NUM-R^3 members on Codeforces (2026-11-05)

**Request.** Analyse the members' Codeforces rounds, and virtuals too. Handles
(user):

| member | handle(s) |
|---|---|
| Dedi | Dedibeat |
| Tamir | t4_4 |
| Erdene | erdene1231 and Munkh-Erdene.B |

Background (user): Tamir (3rd year) and Erdene (1st year) are former IOI
contestants. Dedi (4th year) did maths in high school and started programming
as a freshman.

**Data.** `scripts/team_r3_cf.py --fetch` caches the public API in
`data/team_r3/cf/` (5.7 MB): `user.rating` and `user.status` per handle,
`problemset.problems` and `contest.list`. The run writes
`output/team_r3_cf.json`.

Reused and found:
- The sibling repo `../codeforces_integration` (`cf_problems`, cloudscraper)
  fetches problem pages fine.
- **Submission pages return a Cloudflare 403 even through cloudscraper**, so
  no code was read. A browser `cf_clearance` cookie in `CF_COOKIES` would be
  needed; it must not be written to disk.
- The gym-calibration artifacts (`data/cf_gym_mirrors.json`) contain none of
  our handles.
- `data/cf_pairwise/problems/` holds 978 cached CF statements and editorials,
  not needed here.

**Choices.**
- Only individual timed entries count:
  - Team entries are excluded (earlier teams on ICPC mirrors and gyms: Dedi 12,
    Tamir 3, Erdene 1).
  - April Fools contests are excluded. Erdene's 2214 had 33 tries on one
    problem and first inflated his ICPC-rules test-1 share from 21% to 41%.
- "Level" is the problem rating with a 50% in-contest solve rate, from a
  logistic MLE with a grid search over theta and s.
  - It is fitted on rated rounds only. Out-of-competition entries give 1390
    (Dedi) and 1400 (Erdene), because they are not full efforts.
- The virtual-vs-rated gap uses a shared offset with one theta per half-year in
  which both kinds occur.
- Topic results use families (each problem counted once), with theta per
  half-year and problems within ±500.
  - Single-tag z moved a lot between models: Dedi's bitmasks went from 3.15 to
    1.85, his trees from −1.29 to −2.24. So only families are quoted, and as
    leads.
- A failed system test is a non-OK final-tests verdict in a live CF-rules
  round. In virtual and ICPC-rules rounds, `TESTS` verdicts are ordinary.
- Whether CF rounds penalise a failure on test 1 was not settled (a web search
  was inconclusive). The write-up therefore compares rule types empirically
  and does not assume a penalty rule.

**Findings** (`output/team_r3_coach/cf.md`; summary §4b, §6.3, §6.4, §6.5).

Levels in rated rounds:

| member | all rated | last 12 months |
|---|---|---|
| Dedi | 1780 | 1840 |
| Tamir | 1690 | 1760 (76 problems) |
| Erdene | 1850 | 2050 |

- **Dedi:**
  - 68% first try. 36% of his rejections fail test 1 under every rule set.
  - 2196 C1: nine idleness verdicts on test 1 (362490463–362506639).
  - One failed system test in 94 live CF-rules rounds.
  - Virtuals are the same as rated.
- **Tamir:** test-1 failures are 40% of rejections under CF rules but 10–11%
  under ICPC rules.
- **Erdene:**
  - Virtuals are 320 weaker (95% 230–420); 36 of 63 virtuals have no
    submission after half-time.
  - The 32-bit GCC 7 compiler is still 139 of 348 of his 2026 submissions.
- **Topic families:**
  - Dedi: combinatorics −1.87, graphs/trees −1.49, number theory/bits +1.5.
  - Tamir: graphs/trees +1.76, strings +1.73.
  - Erdene: combinatorics +1.16, interactive −1.12.
- **Upsolving the next problem:** 25/106, 6/19, 11/51.

**Plan changes:**
- Keep the specialisation for Shenyang.
- In the Hong Kong weeks, test Erdene as counting owner and Tamir as graphs
  owner.
- Dedi gets an interactive flush template.
- Erdene moves to a 64-bit compiler.
- Virtuals are played to the end.
- Upsolve the first unsolved problem after every round.

The page https://claude.ai/artifact/4i24BaGeoogkxfA45ZTjp7 (v6) has a
Codeforces section.

**Open:**
- Code-level reading of the chains needs a cookie (above).
- Why the new account Munkh-Erdene.B? It is counted as Erdene's.
- Are other handles or platforms used for upsolving?
