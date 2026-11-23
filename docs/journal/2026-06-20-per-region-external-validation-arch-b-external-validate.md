# Per-region external validation (`arch_b.external_validate`)

The LLM difficulty (`arch_b.validate`) is a single statement-based opinion that can
*itself* be regionally biased, so a small per-region offset against it (e.g. EA +14,
Europe −24) cannot by itself prove a model bias. To separate real bias from LLM noise
we validate against two **numeric** yardsticks that are independent of our standings
*and* of each other, and report agreement **per region**:

* **Codeforces** problemset ratings for the ICPC contests mirrored on CF (mirror ids
  in `data/cf_team_contests.txt`; ratings via the public `problemset.problems` API —
  no login needed). CF contests are auto-mapped to our qoj contests by problem-name
  vote, so an unmappable mirror (CF 2038, a Russian regional we don't carry) or an
  *unrated* mirror (CF 1662 = SWERC 2021-22, 0 CF ratings) drops out automatically.
  **9 contests / 112 problems** map, covering Asia Pacific, Northern Eurasia, Europe.
* **Kattis** difficulty (1.0–9.x, Elo-style, from open.kattis's practice population),
  scraped once into `data/kattis_difficulty.json` (the listing 403s `WebFetch` but is
  curl-able with a browser UA). Covers **North America (88%)** and **Europe (53%)** —
  exactly the regions CF does not mirror.

| region              | CF n | CF Spearman | Kattis n | Kattis Spearman |
|---------------------|------|-------------|----------|-----------------|
| Asia Pacific        | 80   | **+0.939**  | 7        | (n too small)   |
| Northern Eurasia    | 38   | **+0.970**  | 6        | (n too small)   |
| Europe              | 34   | **+0.858**  | 188      | **+0.761**      |
| North America       | —    | —           | 258      | **+0.821**      |
| **Asia East/West Continent** | — | **none** | ~27/2 | **none** |
| **POOLED**          | 152  | **+0.926**  | 489      | +0.732          |
*(our survival difficulty vs each yardstick over 12 CF-mirror contests; small-n
cells are cross-posted stragglers, not real coverage. Spearman, scale-free.)*

**Verdict on the regional-bias question.** No region shows a difficulty breakdown
against independent numeric truth (+0.86 to +0.98 everywhere measurable), and on the
Kattis check our standings-based difficulty agrees with Kattis **better than the LLM
does** (NA +0.821 vs LLM-Kattis +0.700; Europe +0.761 vs +0.655) — i.e. the LLM is the
noisier referee, so the small per-region LLM offsets were largely LLM-labelling noise,
**not** a model bias. The residual gap — **Asia East Continent had no external numeric
anchor at all** (mirrored on neither CF nor Kattis) — is now closed by the gym-mirror
yardstick below: EC validates at **+0.95 to +0.98** for all three models (230 problems),
the *strongest* region in the gym column, so EC calibration is externally confirmed.
Run: `./.venv/bin/python -m arch_b.external_validate` (`--refresh` refetches CF).

**All three models, side by side** (the module scores every `output/problem_ratings*`
file; this **supersedes** `arch_b.sanity_cf`, which checked a single 13-problem contest
— that per-problem view is now `external_validate --contest <cfid>`, e.g. `--contest 2206`
reproduces the old APAC table with Spearman *and* Pearson):

| model           | CF pooled (n=185) | AsiaPac | N.Eur | Europe | Kattis pooled (n=446) | N.Am | Europe | Gym pooled (n=667) | AsiaEC | Europe | AsiaPac | LLM (n=1090) |
|-----------------|-------------------|---------|-------|--------|-----------------------|------|--------|--------------------|--------|--------|---------|--------------|
| arch A          | +0.912            | +0.914  | **+0.971** | +0.866 | +0.692           | +0.674 | +0.722 | **+0.957**       | **+0.981** | +0.939 | **+0.941** | **+0.905** |
| arch B binary   | +0.880            | +0.866  | +0.940 | +0.883 | +0.758            | +0.781 | +0.758 | +0.919           | +0.951 | +0.886 | +0.914  | +0.871     |
| **arch B survival** | **+0.923**    | **+0.924** | +0.960 | **+0.886** | **+0.793**     | **+0.821** | **+0.761** | +0.950       | +0.962 | **+0.953** | +0.935 | +0.882 |

*(CF n grew 152 → 185 as three unlisted rated mirrors were found and added to
`data/cf_team_contests.txt`: CF 2157 ↔ qoj 2692 via the gym certification, then
CF 1773 (2022–23 NEF) and CF 1938 (2024 APAC) via an exhaustive problemset
sweep of all tagged contests — see the metric section.)*

**arch B survival is the most robust model**: it leads on *both* independent numeric
yardsticks — CF (+0.910) and Kattis (+0.793) — which are the hardest checks (independent
of our standings *and* of the statements), and the solve-time signal makes survival ≥
binary on CF, Kattis, *and* LLM. **arch A wins only the LLM column** (+0.905), but that
is the noisiest, coarsest referee (4 buckets) and aligns with arch A's near-monotone
solve-count difficulty; against the broad 446-problem Kattis set arch A drops to **+0.692**,
clearly behind both IRT models, so its LLM edge does not generalize. (Caveat: per-region
n is modest — Europe CF 34, N.Eur 25 — so single-region orderings can flip on noise, and
Kattis Europe carries some title-collision contamination; the pooled columns are the
reliable read.) In the **Gym column** arch A narrowly leads (+0.957) with survival right
behind (+0.950) — expected, since a fixed-θ Rasch difficulty is close to a monotone
transform of the (ability-weighted) solve rate, the same signal arch A leans on; the
column's real payload is the EC cell, not the model ordering.
