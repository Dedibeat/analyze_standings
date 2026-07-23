# External data sources for improving the fit

Research snapshot: **2026-07-21**. This note records sources found after the
initial CLIST/XCPCIO investigation, measures overlap against the current
`data/tagged.json`, and separates data that may enter the likelihood from data
that should remain external validation.

## Implementation status

AOJ is processed and shipped as a validation-only artifact:

```bash
./.venv/bin/python -m arch_b.aoj --refresh
./.venv/bin/python -m arch_b.external_validate
```

The collector writes `data/aoj_difficulty.json` with retrieval time, raw AOJ
identifier and URL, match method, accepted rows, and rejected candidates.
Unique titles are accepted only when at least three matches corroborate one
contest. The current snapshot has 71 candidates, of which 45 across four Japan
regionals are accepted. `arch_b.metric` now enforces an AOJ within-contest
Spearman floor of +0.52.

Fit-side external inputs remain gated on missing evidence rather than guessed.
A live recheck of CP-Ranking commit `c90a176` reproduced its 22 exact
year+institution+team seeds (57 appearances), but its release contains one
aggregate `average_cf_rating` per institution/year rather than the member
handles and per-target-contest histories required for a time-causal team prior.
CPHoF/profile corroboration and Codeforces `user.rating` histories are therefore
still required before those seeds can enter the fit. True-duration ingestion is
likewise waiting on contest-specific public Contest API endpoints; the API
specification alone does not supply a centralized dataset.

## Decision

The most promising additions are:

1. **CPHoF roster/profile links plus the official Codeforces API** for sparse,
   high-confidence, time-accurate participant ability priors.
2. **Public ICPC Contest API / DOMjudge feeds** for true contest duration,
   stable team/person metadata, and submission/judgement timestamps.
3. **ICPC Global and the CP-Ranking release** for official team IDs, dates,
   institutions, cross-tier standings, and a ready-made World Finalist
   Codeforces seed set.
4. **Aizu Online Judge (AOJ)** as a new independent problem-difficulty
   validator, especially for Japan regionals.

CLIST remains useful as an identity corroborator and cross-platform account
index, but it is not the authoritative source for Codeforces ratings. XCPCIO
remains the strongest source already in the repository for Asia East official
team status and medal analysis.

The sources have different statistical roles. Historical participant ratings,
true duration, and actual event histories can improve the survival fit. Practice
site difficulty and solve statistics come from a self-selected population and
should initially be used only for validation/calibration.

## Measured overlap

The checks below used Unicode normalization plus case-folding. Problem-title
counts require a title to be unique on both sides. Team counts use the stricter
keys stated in the row; they are not fuzzy matches.

| Source | Live/source size | Match against this repository | Interpretation |
|---|---:|---:|---|
| CPHoF ICPC WF 2021–2025 | 1,617 distinct participant profiles | 426 unique exact-name candidates; 2,485 member appearances | Large, high-value identity bridge, but team/institution corroboration is still required |
| CP-Ranking | 357 standings files; 383 university-year rating rows | 22 exact year + university + team-name identities, appearing in 57 rows across 24 contests | Safe seed set for recurring elite teams |
| CP-Ranking, institution-only join | same | 831 rows across 68 contests | **Unsafe**: one World Finals roster would be assigned to other teams from the same institution |
| AOJ | 3,438 problems | 71 unique exact titles; 68 have shipped fitted ratings | Useful independent practice signal |
| AOJ, Japan regional subset | — | 45 of 46 problems from 2022–2025 | Near-complete region-specific external validator |
| AtCoder Problems | 9,225 problem titles | 0 unique exact-title matches | Deprioritize unless translated/canonical title mapping is added |

For the 45 matched Japan-regional problems, AOJ's
`submissions / solvedUser` proxy has within-contest Spearman correlation
**+0.572** with the shipped Codeforces-calibrated survival difficulty. The
per-contest correlations are +0.509 (2022), +0.721 (2023), +0.622 (2024), and
+0.476 (2025). This is strong enough to add AOJ as an external guard, but not
strong enough to replace the onsite fit.

These are live-snapshot measurements, not durable source guarantees. A future
collector must save source timestamp, URL, raw identifiers, and match method so
coverage changes are auditable.

## Participant identity and ability

### CPHoF: best new identity bridge

[Competitive Programming Hall of Fame][cphof] publishes World Finals standings
with team names, institutions, and member names. Individual profile pages can
link one real person to Codeforces, AtCoder, Topcoder, and IOI profiles. For
example, the [Daiki Kodama profile][cphof-kodama] explicitly links the real name
to the Codeforces handle `Kodaman` and the AtCoder handle `KoD`.

This is materially better evidence than guessing a Codeforces account from an
exact real-name collision. It also preserves team history, which can confirm
that a person belonged to the relevant roster and season.

The 426 current-data name overlaps are **candidates**, not automatically trusted
links. A match should enter the fit only after checking at least:

- normalized full name;
- institution or country;
- team name and/or the other roster members;
- contest season;
- the external handle shown by the CPHoF profile.

CPHoF has no documented bulk API in this investigation. A collector should
cache pages, identify itself, rate-limit requests, and retain the source URL for
every accepted mapping.

### Codeforces World Finals team lists

Community-maintained Codeforces posts publish World Finals rosters, handles, and
team ratings. Lists used by the CP-Ranking paper exist for [2021][wf-2021],
[2023][wf-2023], and [2024][wf-2024], with current lists also available for
[2025][wf-2025] and [2026][wf-2026].

These tables are especially valuable because the handle is explicit. They are
community-maintained and sometimes work-in-progress, so they should be
corroborated with CPHoF/ICPC rosters and not treated as official standings.
Their displayed team rating is a useful audit value, but the fit should recompute
historical member ratings itself.

### Codeforces: authoritative rating source

After a handle is known, use the official [Codeforces API][cf-api]:

- `user.rating` supplies the complete rating-change timeline;
- select the last `newRating` whose update timestamp is at or before the target
  contest;
- record both the rating and the number/recency of rated contests;
- never use today's `rating` or career `maxRating` for a historical contest.

The detailed prior construction, existing full-name coverage experiment, and
Architecture B equations are in
[`cf_participant_ratings.md`](cf_participant_ratings.md).

### CLIST: corroboration, not authority

[CLIST API v4][clist-api] can connect accounts across resources and is useful
when a coder has deliberately linked several profiles. Limitations for this
project are:

- arbitrary real-name to account resolution is not a reliable bulk primitive;
- ratings are copied/aggregated from upstream platforms;
- the documented standard throttle is 10 requests per minute;
- API access requires an account/key and must be cached.

Use CLIST to strengthen an identity link or find a non-Codeforces account. Once
a Codeforces handle is established, retrieve its rating history from Codeforces.

## Official contest metadata and event histories

### ICPC Contest API / DOMjudge

The [ICPC Contest API specification][contest-api] defines machine-readable:

- exact contest `start_time`, `duration`, freeze duration, and penalty time;
- groups, organizations, teams, persons, and external ICPC IDs;
- problems and final scoreboard;
- submissions, judgements, and awards;
- a complete NDJSON event feed.

[DOMjudge implements this API][domjudge-docs], except for some optional
endpoints. Availability and public access are set per contest server, so the
specification is not itself a centralized dataset. For each contest we should
discover the official results URL and probe its `/api/v4/` or Contest API
endpoint.

This data can improve the likelihood directly:

1. Replace the current `T_c = latest observed solve` approximation with the true
   duration. This corrects right-censoring when the last solve happens early.
2. Use stable person/team IDs to reduce identity fragmentation.
3. Reconstruct wrong-attempt timing and distinguish no attempt from repeated
   failed attempts.
4. Eventually fit a two-stage attempt/solve hazard rather than treating all
   unsolved cells alike.

Public `persons`, `submissions`, and `judgements` cannot be assumed. The
collector must inspect the API's `access` response and store endpoint-level
availability rather than silently substituting missing data.

### ICPC Global and CP-Ranking

ICPC Global exposes public contest metadata and aggregate standings. For
example, the [2024 Europe Championship record][icpc-euc-api] supplies official
dates, contest type, sites, problem-set URL, and a DOMjudge results URL. Its
public standings contain team ID, team name, institution, rank, solved count,
penalty, and last-solve time.

The public [CP-Ranking repository][cp-ranking] already implements a harvester for
ICPC Global tags and contains ten years of standings across World Finals,
superregionals, North American regionals, and Northern Eurasian regionals. Its
associated [paper][cp-ranking-paper] reports 366 World Finalist teams with
pre-contest Codeforces ratings for 2021–2024 and finds Codeforces rating more
aligned with World Finals rank (Kendall's tau +0.596) than any single ICPC tier.

Recommended uses:

- canonical contest IDs, dates, institutions, and official aggregate results;
- cross-tier team-performance validation;
- discovery of each contest's richer `resultsUrl`;
- a reviewed seed set for participant priors.

The public standings projection used by CP-Ranking has aggregate totals, not the
per-problem cells required by the current difficulty likelihood. Institution
normalization is also difficult and the repository documents manual fixes.
Therefore, do not identify a team by institution alone.

## External problem-difficulty sources

### Aizu Online Judge

The official [AOJ API documentation][aoj-api] exposes problem names, submissions,
accepted counts, solved users, categories, and source metadata. The newer live
JSON endpoint used for the overlap check was:

```text
https://judgeapi.u-aizu.ac.jp/problems?page=0&size=10000
```

For matched problems retain `id`, `name`, `solvedUser`, `submissions`, and fetch
source/category metadata where available. Match by contest/source plus title;
the exact-title experiment is deliberately conservative.

AOJ observations are accumulated practice behavior with unequal exposure time.
Use their within-contest order as an external validator. Do not interpret
`solvedUser / submissions` as an onsite solve probability.

### solved.ac / BOJ

[solved.ac problem levels][solved-level] provide a community-derived ordinal
difficulty from 1 to 30, plus accepted-user count, average tries, vote count,
vote dispersion, and tags. This is potentially valuable for Asia East/Pacific
problems mirrored on BOJ.

Risks:

- community ratings can change over time;
- practice population and exposure differ from onsite contests;
- English/Korean title differences require canonical contest/source matching;
- solved.ac [announced][solved-shutdown] that BOJ integration would end on
  2026-04-28, although retained problem difficulty data would continue in some
  form.

If used, cache a dated snapshot immediately. Start with validation or monotone
calibration, not likelihood terms.

### ICPC Archives

[ICPC Archives][icpc-archive] covers most contest families in this repository
and links problem sets and solutions. It has no numeric difficulty itself, but
it is useful as a canonical join registry between QOJ, AOJ, BOJ/solved.ac,
Kattis, and Codeforces mirrors. A problem-set fingerprint is safer than global
title matching and can recover translated-title matches.

### AtCoder Problems

The [AtCoder Problems bulk catalog][atcoder-catalog] was cheap to test but had no
unambiguous exact-title overlap with the current corpus. This does not prove
zero shared tasks—translated titles can differ—but it makes AtCoder a lower
priority than AOJ and solved.ac for the next experiment.

## Fit integration

### Participant prior

For a fully resolved roster, compute each member's historical pre-contest
Codeforces rating and reduce the three ratings with the same candidate team rule
already evaluated in the repository (`lse` first, `max` as an ablation). Learn
an affine mapping from the team rating to latent ability and add it as a
confidence-weighted Gaussian prior:

```text
theta_t ~ Normal(alpha + beta * R_t, sigma_match^2)
```

`sigma_match` must depend on evidence quality and rating recency. Fully verified
rosters receive the strongest precision. Partial rosters should initially be
excluded: dropping an unmatched member changes the meaning of the team rating
and usually biases it downward.

This prior should help cold-start teams, weakly connected regions, field-strength
normalization, and 0–1-solver problems. It is an ability prior, not a direct
problem-difficulty anchor.

### Contest duration and attempts

True duration can be added without changing the model family. Event-level
submission data is a later likelihood extension. Test these independently:

1. current survival baseline;
2. true duration only;
3. participant prior only;
4. duration plus participant prior;
5. event-history likelihood on the subset with public feeds.

This separation identifies which new source causes a gain and avoids making a
sparse event-feed subset silently define the global result.

### External difficulty guards

Add AOJ alongside Kattis, Codeforces, Gym, and LLM validation. Keep AOJ and
solved.ac out of training for the first experiment. If a later monotone
calibration/shrinkage experiment is attempted, evaluate it with source-held-out
problems so the same practice statistic is not both input and metric.

Official/unofficial status from ICPC/XCPCIO should define evaluation slices and
identity confidence. Do not automatically downweight unofficial rows: the
existing official-only/downweighting experiments did not improve the shipped
fit.

## Matching and leakage policy

- **Person:** explicit external-profile link is strongest; otherwise require
  full name plus team/roster and institution/country corroboration.
- **Team:** exact official team ID when available; otherwise roster + season +
  institution, then exact team name as supporting evidence.
- **Problem:** contest/source plus normalized title; require a one-to-one mapping
  and preferably at least three matched problems to establish a contest mirror.
- **Rating time:** last Codeforces rating known before the target contest.
- **No future data:** current/max ratings, later team results, and post-contest
  roster changes cannot be predictors for an earlier contest.
- **Provenance:** every derived row stores source URL, source timestamp, raw
  identifier, matching fields, confidence class, and rejection reason if
  manually reviewed.

## Evaluation and acceptance

Compare each variant with the shipped baseline documented in `details.md`:

- leave-one-contest-out CF-point MAE;
- held-out solve log-loss, Brier score, and AUC;
- Kattis and CF external correlations;
- new AOJ within-contest correlation;
- region and year slices, especially Asia West and weakly linked contests;
- hard-tail changes for 0–1-solver problems;
- a prior holdout in which some linked teams' ratings are hidden during fit.

The Gym difficulty column is not independent for the participant-prior
experiment because it also uses Codeforces participant ratings. A gain seen
only on the Gym guard is insufficient. Reject changes that improve CF-scale
MAE but hurt held-out prediction or Kattis/AOJ agreement.

## Recommended implementation order

1. Build a cached CPHoF/Codeforces-team-list identity artifact with reviewable
   confidence and provenance.
2. Resolve historical ratings through `user.rating` and produce a full-roster
   team-prior dry-run report.
3. Add the Architecture B per-team prior precision described in
   `cf_participant_ratings.md`, preserving byte-identical output with no priors.
4. Harvest ICPC Global metadata and probe every official `resultsUrl` for a
   public Contest API.
5. Add true duration where available and evaluate it separately.
6. Add AOJ as a permanent external validator.
7. Use ICPC Archives to pilot solved.ac canonical mappings; cache a dated
   snapshot before considering calibration.
8. Consider a submission-event likelihood only after public-feed coverage is
   measured.

[aoj-api]: https://judge.u-aizu.ac.jp/onlinejudge/api.jsp
[atcoder-catalog]: https://kenkoooo.com/atcoder/resources/problems.json
[cf-api]: https://codeforces.com/apiHelp/methods?locale=en
[clist-api]: https://clist.by/api/v4/doc/
[contest-api]: https://ccs-specs.icpc.io/2026-01/contest_api
[cphof]: https://cphof.org/standings/icpc/2025
[cphof-kodama]: https://cphof.org/profile/icpc%3ADaiki%20Kodama
[cp-ranking]: https://github.com/zhtluo/cp-ranking
[cp-ranking-paper]: https://arxiv.org/abs/2505.04143
[domjudge-docs]: https://www.domjudge.org/documentation
[icpc-archive]: https://icpcarchive.github.io/
[icpc-euc-api]: https://icpc.global/api/contest/public/EUC-2024
[solved-level]: https://help.solved.ac/en/problem/level
[solved-shutdown]: https://help.solved.ac/en/updates/260415
[wf-2021]: https://codeforces.com/blog/entry/102593
[wf-2023]: https://codeforces.com/blog/entry/117183
[wf-2024]: https://codeforces.com/blog/entry/129887
[wf-2025]: https://codeforces.com/blog/entry/143861?locale=en
[wf-2026]: https://codeforces.com/blog/entry/149719?locale=en
