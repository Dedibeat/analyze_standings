# Hidden cycles and patterns in regional techniques (2026-10-10)

**Question.** Is there a hidden cycle or pattern in which techniques appear?
Script `scripts/technique_patterns.py` (same data as the technique forecast
above); report `output/technique_patterns.md` (numbers in `.json`); tests
`tests/test_technique_patterns.py`. All tests are permutation tests (4,000
draws, seed 2026), two-sided, with Holm correction within each table.

**No cycles, no fashion, no site style.**
- *Season gap.* Two regionals 1, 2 or 3 seasons apart are no less alike than
  two from the same season. This holds for named techniques (Jaccard),
  derived categories and DeepSeek general tags (cosine). Neither drift nor a
  2-season cycle (gap 2 above the line through gaps 1 and 3) is anywhere
  near significant (raw p ≥ .32).
- *Zigzag per tag.* Lag-1 autocorrelation of each tag's per-season mean: none
  survives Holm over 26 tags. The pooled value matches chance (p = .70). The
  apparent zigzags, e.g. general dp 1.83 / 2.57 / 1.43 / 2.14 (p = .13), are
  noise at this size.
- *Site style.* Same-site regionals are no more alike than regionals at
  different sites (technique Jaccard .093 vs .075, p = .23; general-tag cosine
  .741 vs .742). The highest descriptive same-site value is Shenyang .84.
- *ICPC vs CCPC in the same season* are no more alike than across seasons
  (p ≥ .82). The two circuits do not share a seasonal fashion.

**Balancing inside a set: suggestive only.**
- Every one of the 27 regionals has a problem DeepSeek tags `graphs`, against
  89% if problems were dealt at random within the season. The counts are
  1 / 2 / 3 / 4 graph problems in 8 / 14 / 3 / 2 regionals (variance ratio
  0.45). This gives raw p = .005, but Holm p = .14 over 26 tags.
- Geometry appears in 85% of regionals (chance 73%, p = .09). The four
  regionals without it are Xi'an 2022, Hefei 2023, Wuhan 2025 and Xi'an 2025.
- A named technique is used twice in one set 10 times (chance 13.7, p = .30).
  This is consistent with setters avoiding repeats, but it is not shown.
- CCPC has too few contests to tell.

**The one solid pattern: tags have fixed slots in the difficulty order.**
Mean difficulty percentile inside the contest (0 = easiest):
- *Easy end (ICPC, Holm p < .05):* implementation .20, greedy .35, no named
  technique .39.
- *Hard end (ICPC):* data structures .61 (general) / .65 (derived), named
  math .68, geometry .69 (derived) / .76 (general).
- *CCPC replication:* problems with no named technique sit at .36 (Holm
  p = .004). Data structures sit at .69 (Holm p = .06, 17 problems).

**For the forecast:** nothing here changes the model. With no cycle, trend or
site effect, one pooled profile per regional stays right. The useful
additions are the slot pattern (geometry and data structures are late
problems; greedy and implementation are early) and the near-certain graph
problem.

Run: `python scripts/technique_patterns.py`.
Tests: `python -m unittest tests.test_technique_patterns`.
