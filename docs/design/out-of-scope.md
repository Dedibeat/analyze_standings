# Out of scope / follow-ups

- **2PL discrimination** `a_p` (strat §4) on top of the Rasch fit in `arch_b`
  (**prototyped — overfits, see the 2PL section above; not shipped**),
  plus a calibrated joint posterior (full-Hessian Laplace / MCMC / VI) beyond the
  per-parameter Laplace SE already emitted as `difficulty_se`.
- **Per-contest `T_c` from real durations** — the survival model infers `T_c` as
  the latest solve time (a slight underestimate); public ICPC Contest API /
  DOMjudge metadata is now the preferred source for a true duration field (see
  `external_data_sources.md`).
- **Member-level identity** and entity resolution across sources (strat
  Remarks), to densify linking and handle roster changes.  CPHoF external-profile
  links are the first high-confidence bridge to harvest; CLIST remains secondary
  corroboration (see `external_data_sources.md`).
- **Time-varying ability** `theta_{team,season}` with a season-to-season smoothing
  prior — keeping **one** identity (unlike the hard `season_key` split, which was
  tried and slightly hurt difficulty, see above) but letting ability drift, so a
  recurring roster neither collapses to one blended value nor loses data to a split.
  A dedicated team-performance prediction eval (not just difficulty) is the right
  way to measure its benefit.
- ~~**Richer CF calibration.**~~ **Done (2026-07-04)** — `arch_b.calibrate` now
  ships the gym-shaped two-leg map on all 185 auto-mapped anchors (LOCO 288 →
  266, see the calibration section). Per-region maps were tried and overfit
  (298); the 1-solver hard-end *ordering* remains data-limited (the shape
  improves the tail's scale, RMSE 477 → 434, but cannot reorder 0–1-solver
  problems).
- **No external anchor for Asia West Continent.** ~~Asia East Continent~~ — **closed**:
  the gym-mirror yardstick (`arch_b.gym_difficulty`) now anchors EC at +0.95–0.98
  for all three models. Asia *West* remains uncovered (its one scraped gym, the
  Iranian contest, was a wrong-event match — see the gym section).
- ~~**Use `b_gym` as calibration anchors.**~~ **Done (2026-07-04)** — the
  gym-learned shape leg in `arch_b.calibrate` (see the calibration section) is
  exactly this, and it is the one use of the gym signal that survived
  validation. The two *in-fit* uses tested **negative**: per-problem prior
  means (80afc92, reverted — circular guard corroboration, Kattis down) and
  merged fixed-θ likelihood terms (`gym_merge` — Kattis and held-out AUC
  degrade monotonically with weight). Scale-half of the signal: used; noisy
  ranking-half: discarded, by construction of the monotone map.
- ~~**Add CF 2157 to `data/cf_team_contests.txt`.**~~ **Done** — the CF columns
  and the metric anchor set now include it (CF pooled n 152 → 160).
- **CF participant anchoring — source data collected, fit integration not
  implemented.**  The CPHoF/official-API artifact supplies 346 explicit
  identities and 347 roster-complete standing rows, while name-only matches
  remain excluded.  The proposed first fit experiment still needs exact target
  contest timestamps and per-team prior precision; see
  [`cf_participant_ratings.md`](../reports/codeforces/cf_participant_ratings.md) and the feasibility
  section above.
- **`data/cf_gym_mirrors.json` — scraped; now consumed by `arch_b.gym_difficulty`
  (see that section).** For contests whose
  problems were also mirrored as a Codeforces **Gym** contest (training replay, not
  the officially-rated rounds `cf_team_contests.txt` uses), CF's own practice
  population gives an independent difficulty signal: solve outcome vs. each
  solver's *own* established Codeforces rating — closer to the strat's originally
  recommended CF-anchor (eq. cfprior) than anything else in the repo, since our own
  contestants have no CF handles (see the roster-identity decision above).
  - **Contest → gym matching (62 of 146 contests mapped).** Matched two ways:
    36 by a distinctive city/country keyword in `contest_name` + season year
    (e.g. "Nanjing" 2023 → the CF gym titled "The 2023 ICPC Asia Nanjing Regional
    Contest"); 26 more (the Europe/North America contests, whose `contest_name` is
    only the broad sub-region label like "Northwestern Europe" — indistinguishable
    from NWERC/BAPC/UKIEPC/GCPC/NCPC by name alone) by the same problem-name-vote
    technique `external_validate._cf_mapping` already uses for CF-rated mirrors,
    pointed at each candidate gym's problem list instead of `problemset.problems`.
    The gym listing itself was scraped through an authenticated browser session
    (`claude-in-chrome`) since CF sits behind a Cloudflare bot check that blocks
    plain `curl`/`WebFetch`; standings and rating history, once a user-supplied CF
    **API key + secret** were available, came from the signed `contest.standings` /
    `user.rating` endpoints directly (`curl`/Python, HMAC-SHA512 `apiSig`, no
    browser needed — gym `contest.standings` returns `"You have to be authenticated"`
    without a signed request even though the contest itself is public).
  - **Upsolvers excluded.** `contest.standings` mixes real timed attempts
    (`participantType: VIRTUAL`/`CONTESTANT`) with open-ended `PRACTICE` rows (no
    time pressure, solved whenever) — 34% of all rows (17,353 of 50,716) were
    `PRACTICE` and are dropped, since unlimited time on a problem is a different
    signal from solving it live and would bias problems toward looking easier than
    they are under real contest conditions. `ghost: true` rows (the original
    onsite field, replayed into the mirror's standings for comparison) already
    contribute nothing — they carry `members: []`, no real CF handle.
  - **Rating and contest count are time-accurate, not "current."** A gym's virtual
    attempt can happen years after the original contest, and a solver's CF rating
    drifts a lot over that span, so using their rating *today* would be
    systematically wrong for older mirrors. Each solver's full rating-change
    history (`user.rating`, one call per handle — not batchable like `user.info`)
    is fetched once, then `cf_rating_at_attempt` / `cf_rated_contests_at_attempt`
    are computed by truncating that history to entries at or before the party's
    own `startTimeSeconds` (bisection on timestamp). A solver with no rated
    contest yet at attempt time gets `cf_rating_at_attempt: null`,
    `cf_rated_contests_at_attempt: 0` (kept, not dropped — 3,016 of 57,695 rows).
  - **Collection notes.** CF's rate limit rejected even 4 concurrent signed
    requests (`"Call limit exceeded"`, HTTP 429) but tolerated a plain serial loop
    at the network's natural ~0.2s/call latency with zero added delay (17,162
    handles in ~64 min, 0 failures). Progress was checkpointed to
    `data/gym_checkpoints/` (gitignored, survives outside `/tmp`) every 200
    handles and the fetch resumes from there, since `/tmp` does not survive a
    machine restart.
  - **Schema.** Keyed by our `qoj_contest_id`; each entry has `gym_id`/`gym_url`,
    `gym_problem_labels` vs. `our_problem_labels` (5 of the 62 mismatch — different
    problem subset between the mirror and our record — flagged via
    `labels_aligned` rather than dropped, so a consumer must join by problem
    *name*, not letter, when false), and `teams`: one entry per team **attempt**
    (`participant_id`, `team_name`, `rank`, `attempt_time`, the shared `solved`
    letter list — since solving is per-team, not per-member — and `members`,
    each with `handle`, `cf_rating_at_attempt`, `cf_rated_contests_at_attempt`).
    Kept grouped by team rather than flattened, so a consumer can choose how to
    reduce a team to one ability value (max member rating, best-known member,
    etc.) instead of that choice being silently baked into the file
    (25,003 teams / 57,695 member-rows total).
  - **Consumed (2026-07-03).** `arch_b.gym_difficulty` runs exactly the fit this
    bullet anticipated — a fixed-θ Rasch MAP for `b_p` with a trust-weighted
    team reduction — and `external_validate` now reports it as the third
    yardstick column. Note the matching caveat discovered on consumption: the
    five `labels_aligned: false` entries are *wrong gym events* (zero
    problem-name overlap), not merely re-lettered mirrors.
