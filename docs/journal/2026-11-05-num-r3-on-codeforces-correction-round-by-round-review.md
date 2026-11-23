# NUM-R^3 on Codeforces: correction, round-by-round review (2026-11-05, second entry)

**User facts.**
- Munkh-Erdene.B's rounds are Erdene's.
- Requests: analyse more rounds for each member; study which types of problems
  they fail or solve; suggest what to work on.

**Bug found and fixed (supersedes numbers in the first CF entry above).**
- `problemset.problems` files the problems a Div. 2 round shares with its
  Div. 1 twin only under the Div. 1 id. So the first `team_r3_cf.py` saw only A
  and B in 49 Div. 2 rounds and dropped every solve on C and beyond (for
  example, Dedi's 2220 looked like 2 solves at rank 188).
- Found by comparing our rows in the official standings with the digest.
- Fix: for those 49 contests the problem list (rating, tags) comes from the
  round's standings and is stored in `data/team_r3/cf/contest_problems.json`
  (committed). Compact standings are cached in `data/team_r3/cf/standings/`
  (gitignored).
- Practice ratings now come from each submission's problem object.

Corrected figures:

| figure | Dedi | Tamir | Erdene |
|---|---|---|---|
| rated level, all / last 12 months | 1790 / 1870 | 1660 / 1710 | 1810 / 2050 |
| test-1 failures | 237 of 630 | 35 of 186 | 63 of 226 |
| idleness runs on test 1 | 15 | | 4 (2078 E) |
| failed system tests | 2 | | 2 |

- Topic families:
  - Dedi: combinatorics −1.83, graphs/trees −1.21 (trees −2.17), number
    theory/bits +1.58.
  - Tamir: graphs/trees +1.95 (trees +2.12).
  - Erdene: combinatorics +1.18, interactive −1.16.
- Virtual offsets: Erdene 300 (210–390); Tamir 310 (30–570), now measurable.
- Next unsolved problem upsolved: 28/119, 6/22, 13/58.
- Last submission before half-time, virtuals vs rated: Erdene 32/63 vs 13/59.

**Penalty rule, verified.** Codeforces does not count a test-1 failure under
either rule set. Recomputing the official penalty of all 13 ICPC-rules rated
entries is exact only without them, and CF-rules official rejected counts skip
them too. So the first entry's claim that Tamir "checks samples when the rules
punish it" was withdrawn.

**Round-by-round review.** `scripts/team_r3_cf_rounds.py` covers:
- Dedi: rated rounds since 2025-11-05.
- Erdene: rated rounds since 2025-07-01.
- Tamir: all rated rounds.
- Every 2026 virtual for all three.

That is 99 entries; it reuses `standings()` from `team_r3_cf.py`. Per entry:
- field solves and median minute per problem;
- the same-set tier and our place in it;
- the next tier (our set plus one) and its median minutes;
- the field's next problem, with its editorial via `../codeforces_integration`
  (13 of 99 missing).

Virtual entries are placed by recomputing the score: CF decay fitted per round
(within 27 points); ICPC rules exact. Outputs:
`output/team_r3_cf_rounds.{json,md}`. The analysis is
`output/team_r3_coach/cf_rounds.md`.

Findings:
- **Attempts on the field's next problem:** Erdene 2 of 21, Tamir 10 of 27,
  Dedi 11 of 51.
- **Dedi:**
  - His walls are trees (9 of 51 next problems) and counting (8).
  - Five times he solved a harder problem while the next stayed unsolved (2203
    −63, 2231 −143).
- **Tamir:**
  - Div 2 / Div 1+2 rounds: −174 in 9 since May 2025. Div 3 / Edu / Good Bye:
    +342 in 4.
  - Ad-hoc B/C chains (2175 B: 9 tries, 7 on test 1); XOR construction; binary
    search on the answer; number theory.
- **Erdene:**
  - Div 1 rounds: −174 in 5. In each he solved A and stopped; the next
    problems were DP state design (2174 B, 2190 B2), bitmask greedy (2187 B)
    and interactive (2196 C2).
  - Hardest solves are 2109 C3 (2600), 2154 E (2500) and 2176 F (2400).

Practice lists are from their own rounds, with open/upsolved status. Summary
§4b, §6.4 and §6.5 and the page (v7) were updated.
