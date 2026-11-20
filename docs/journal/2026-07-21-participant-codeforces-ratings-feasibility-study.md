# Participant Codeforces ratings: feasibility study (2026-07-21)

A live test confirmed that **some** standing members can be mapped to
Codeforces, but the bottleneck is identity rather than rating retrieval.  The
official Codeforces `user.ratedList` snapshot contained 958,447 rated accounts.
Exact normalized full-name matching against `data/tagged.json` found one distinct
handle for **1,168 of 25,656 unique member names (4.6%)** and for 4,839 of 65,588
member appearances (7.4%); 302 additional names were ambiguous.  At team level,
3,241 of 24,709 rows with rosters (13.1%) had at least one unique match, but only
560 (2.3%) had every member matched.  This is a useful sparse anchor set, not a
complete participant-rating layer.

**Source decision:** Codeforces is authoritative once a handle is known:
`user.info` supplies current records and `user.rating` supplies the history needed
to select the last rating known before each ICPC contest.  CLIST unified coder
profiles are useful secondary evidence for account identity, but the v4 account
API is handle/resource-oriented and cannot bulk-resolve arbitrary real names.
Neither current rating nor `maxRating` is valid for an old contest.

**Fit direction:** add trusted, time-accurate CF data as a confidence-weighted
prior on **team ability `theta`**, not as a prior on problem difficulty.  Start
with fully resolved rosters only and reduce member ratings with the same `lse`
team rule used by `arch_b.gym_difficulty`; ignoring an unmatched member would
bias partial rosters downward.  Architecture B should accept per-team prior
precision so verified veterans pull more strongly than weak/name-only matches;
the Gaussian MAP remains strictly concave.  This should improve cold starts,
weakly linked contest normalization, and 0–1-solver problems by identifying the
actual strength of their field.

Validation must use historical ratings only, treat the gym column as circular
(it also uses CF user ratings), and require corroboration from held-out solve
prediction and Kattis.  A CF-prior team holdout should test whether the scale
transfers through the contest graph.  Full methodology, examples, equations,
risks, and implementation order are in
[`cf_participant_ratings.md`](../reports/codeforces/cf_participant_ratings.md).

**Source layer implemented 2026-07-23.**  The reproducible
`scripts/cphof_cf_participants.py` collector now caches CPHoF's 2021–2025 World
Finals standings and relevant profile pages, follows only explicit CPHoF
Codeforces profile links, and fetches complete histories from the official
Codeforces `user.rating` API.  Raw responses live in the resumable, gitignored
`data/cphof_cache/`; the provenance-rich
`data/cphof_cf_participants.json` artifact is committed.

The current snapshot has 415 exact-name CPHoF candidates, 346 explicit
person→handle identities with available API histories, and 285 people whose
appearance in `tagged.json` is corroborated by at least one additional matching
roster member.  Those conservative links cover 1,582 standing-member
appearances; 347 unique standing rows have explicit handles for every roster
member.  Another 537 name-only appearances remain review candidates and do not
count as trusted links.  Nine stale CPHoF handles fail the official API and are
retained as rejected evidence rather than repaired by guessing.

The artifact stores 29,425 rating changes and computes 470 historical ratings
before the CPHoF World Finals calendar dates.  CPHoF does not publish a start
time on those pages, so the collector uses 00:00 UTC at the start of each date:
a conservative cutoff that excludes same-date changes rather than risk
look-ahead.  It deliberately does not derive regional priors:
`tagged.json` provides only `year`, not the exact contest start timestamp
required to choose a non-leaking historical rating.
Fit-side per-team precision, full-roster `lse` reduction, and regional date
collection therefore remain follow-ups.
