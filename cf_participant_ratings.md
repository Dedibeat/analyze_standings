# Participant Codeforces ratings: feasibility and fit plan

Status: research note, **not yet used by the shipped fit**.  Measurements below
are from a live snapshot on 2026-07-21.

## Conclusion

Some standing participants can be linked to Codeforces, but neither CLIST nor
Codeforces provides a reliable universal real-name-to-handle map.

- Use **Codeforces as the authoritative rating source** after a handle is known.
  Its public API supplies current user records and full rating histories.
- Use **CLIST only as secondary identity evidence**.  Its unified coder profiles
  are useful for manually confirming that accounts on different judges belong to
  one person, but its API is handle/resource-oriented and does not turn arbitrary
  ICPC member names into Codeforces handles in bulk.
- Treat identity resolution as the hard part.  Do not select the highest-rated
  same-name account: that would create both false identities and ability-biased
  matching.
- Use the rating that was known **before the ICPC contest**, never today's rating
  or `maxRating`.  Otherwise older contests receive future information.

The likely first useful experiment is a conservative CF prior on team ability for
fully resolved rosters.  Partial-roster matches must not be treated as complete
team ratings: the unmatched member is unknown, not necessarily unrated.

A follow-up internet-source audit found that **CPHoF profiles and Codeforces
World Finals team lists are the strongest high-confidence identity bridges**:
they explicitly connect rosters or real names to handles.  Measured overlap,
corroboration rules, CP-Ranking coverage, and the wider contest/problem source
audit are in [`external_data_sources.md`](external_data_sources.md).

## Sources

Codeforces exposes the required data directly:

- [`user.ratedList`](https://codeforces.com/apiHelp/methods?locale=en) with
  `activeOnly=false&includeRetired=true` returns every account that has played a
  rated contest.  User records include handle, optional first/last name,
  organization, country, current rating, and maximum rating.
- `user.info?handles=...` refreshes current records in batches once handles are
  known.
- `user.rating?handle=...` returns one handle's complete rating-change history.
  It is not batchable, so histories must be cached and fetched serially within
  the Codeforces API limit.

CLIST has two useful surfaces:

- `/coder/<coder>/` shows a unified profile containing accounts from multiple
  judges; this can corroborate a disputed identity.
- `/api/v4/account/` exposes account `handle`, `name`, `rating`, resource, and
  contest count.  The [declared v4 filters](https://github.com/aropan/clist/blob/master/src/clist/api/v4.py#L20-L43)
  cover handle/resource/rating, not the account `name`, and
  [API access requires a key](https://clist.by/api/v4/doc/) (standard limit: 10
  requests per minute).  Thus a query such as
  `/api/v4/account/?resource=codeforces.com&handle=tourist` retrieves a known
  account but does not solve `Gennady Korotkevich -> tourist` in bulk.

The rating itself should therefore come from Codeforces.  CLIST adds value only
when resolving or corroborating the handle.

## Coverage experiment

### Method

1. Downloaded the complete Codeforces rated list:

       https://codeforces.com/api/user.ratedList?activeOnly=false&includeRetired=true

   The snapshot contained **958,447 users** and was **340,760,709 bytes** as
   uncompressed JSON, so it should be cached rather than fetched during a fit.
2. Read every non-empty `members` entry in `data/tagged.json`.
3. Normalized names with Unicode NFKC, case-folding, whitespace collapse, and
   indexed both `firstName lastName` and `lastName firstName`.
4. Counted a match as automatic only when the normalized full name selected one
   distinct Codeforces handle.  No fuzzy matching and no highest-rating tie-break
   were used.

### Result

| unit | total | any exact-name candidate | exactly one handle |
|---|---:|---:|---:|
| distinct member names | 25,656 | 1,470 (5.7%) | **1,168 (4.6%)** |
| member appearances | 65,588 | 6,093 (9.3%) | **4,839 (7.4%)** |
| team rows with members | 24,709 | — | **3,241 (13.1%) have at least one** |
| team rows with members | 24,709 | — | **560 (2.3%) have every member** |

The 1,470 matched names include **302 ambiguous names** with multiple handles.
Exact full-name matching therefore produces a useful but sparse seed set, not a
complete participant-rating dataset.  Recurring famous participants make
appearance coverage higher than unique-name coverage, which is favorable for
anchoring even though raw coverage is small.

Illustrative snapshot values (these ratings will drift):

| standing member | supported handle | rating on 2026-07-21 | evidence note |
|---|---|---:|---|
| Andrew He | `ecnerwala` | 3191 | unique exact name; MIT profile |
| Kevin Sun | `ksun48` | 3162 | name alone ambiguous; MIT context distinguishes it |
| Gennady Korotkevich | `tourist` | 3530 | name alone ambiguous; established CLIST/CF identity |
| Aleksei Daniliuk | `Um_nik` | 3389 | unique exact name |
| Yui Hosaka | `hos.lyric` | 3017 | unique exact name |

Even famous names demonstrate the danger: the snapshot had two Kevin Sun
accounts, two Gennady Korotkevich accounts, and three Qiwen Xu accounts.

## Identity policy

Store a versioned, auditable member map rather than resolving names inside the
fit.  Each accepted edge should include `member_name`, `cf_handle`, evidence,
confidence, verification status, and retrieval timestamps.

Suggested confidence levels:

- **verified:** self-linked CLIST profile or another direct authoritative link;
- **corroborated:** exact name plus independent organization/country/team
  evidence;
- **name-only:** one exact full-name candidate but no corroborating evidence;
- **ambiguous/rejected:** multiple candidates, fuzzy-only match, or conflicting
  context.

Only verified/corroborated identities should enter the first fit experiment.
Name-only matches are useful for a coverage upper bound and a sensitivity run,
not as trusted anchors.  Ambiguous accounts must never be resolved by choosing
the rating that best explains the observed rank or solve count; that would use
the model target to manufacture the identity.

Useful disambiguating evidence is organization/affiliation, country, a direct
profile link, and consistent teammate/account history.  Transliteration and
name-order fuzzing may generate review candidates but should not auto-accept an
edge.

## Building time-accurate ratings

For every accepted handle, cache `user.rating`.  For a contest beginning at
time `t_c`, use the `newRating` from the latest rating change whose
`ratingUpdateTimeSeconds <= t_c`; also count how many such rated contests exist.
If no change predates `t_c`, the member has no established CF rating for that
contest and contributes no numeric prior.

Use the existing trust convention

    w_ic = 1 - 0.9 ** n_ic

where `n_ic` is the member's rated-contest count before contest `c`.  This is the
same convention used by `arch_b.gym_difficulty`: one CF contest is weak evidence,
while a long rating history approaches full weight.

When **every roster member** has a time-accurate rating, reduce the three members
to the existing team-equivalent ability

    R_tc = s * log(sum_i exp(r_ic / s)),    s = 400 / ln(10).

This is the `lse` rule already certified in `arch_b.gym_difficulty`; at the hard
end it is the single-solver ability equivalent to independent team members.  The
`max(member rating)` reduction should remain an ablation.

If only part of the roster is resolved, this formula is a lower bound, not an
estimate of the whole team's ability.  The first experiment should therefore
exclude incomplete rosters.  Later options are an explicit member-level latent
model or a correctly derived censored prior; silently dropping unknown members
would bias teams downward.

## How this can improve the fit

The current fit gives every cold-start team a neutral `MU0=2000` prior and learns
the absolute scale indirectly through UCup plus post-fit problem calibration.
Historical CF team ratings add independent information at exactly the weak point:
one-off or thinly linked teams whose strength cannot be recovered well from these
standings alone.

Expected benefits:

1. **A real ability-scale anchor.** CF priors identify the absolute team scale
   rather than merely pinning it near an arbitrary 2000.
2. **Better contest-strength normalization.** Europe and other weakly linked
   regions rely heavily on one-off teams.  A few trusted CF-rated rosters can
   anchor their fields directly instead of waiting for long cross-contest paths.
3. **Better sparse-problem difficulty.** For a 0- or 1-solver problem, knowing
   whether the field and exceptional solver were around 2400 or 3400 is valuable
   information that raw solve count cannot supply.
4. **Less cold-start shrinkage.** A strong one-contest team currently leans
   toward 2000; a historical CF prior prevents it from making its contest look
   artificially weak and its problems artificially easy.
5. **More meaningful raw `theta`.** The calibrated output may still need a
   monotone map, but team abilities and pre-calibration problem difficulties
   should be closer to CF points and the affine calibration slope should move
   toward one.

Coverage is missing-not-at-random: Codeforces-linked contestants are unusually
strong and internationally active.  The result is an anchor set, not a
representative sample, and must be modelled as such.

## Architecture B integration (recommended)

Add per-team prior **precision**, not only a different prior mean.  For a static
team identity `t`, combine the neutral prior and all trusted historical CF team
ratings available on that team's contest appearances:

    P_t = 1 / sigma_0^2 + sum_c q_tc * w_tc / sigma_cf^2
    mu_t = (MU0 / sigma_0^2
            + sum_c q_tc * w_tc * R_tc / sigma_cf^2) / P_t

where `q_tc` is identity confidence, `w_tc` is rating-history trust, and
`sigma_cf` represents the residual gap between a three-person CF-derived team
rating and onsite ICPC ability.  The MAP objective then uses

    -0.5 * P_t * (theta_t - mu_t)^2

instead of one global `sigma_theta` for all teams.

This requires `model.fit` and `survival.fit` to accept a per-team precision array.
It preserves strict concavity and only changes the existing prior gradient and
Hessian terms.  UCup and CF evidence should be combined explicitly in the same
prior builder rather than overwriting one prior mean with another.

Because the current model has one `theta_t` across years, multiple historical
ratings collapse to a precision-weighted mean.  That is consistent with the
current static-ability assumption.  A later time-varying `theta_{t,season}` with
a smoothing prior would use each historical rating at the corresponding season
instead of averaging career stages.

## Architecture A integration

Architecture A already accepts per-team `prior_mu` and `prior_strength`.  Convert
trusted CF evidence into pseudo-contest strength, combine it with the standing
neutral/UCup prior, and pass the resulting arrays to `fixedpoint.estimate`.
Confidence and rating-history trust must scale `prior_strength`; changing only
`prior_mu` would give a weak name-only match the same influence as a verified
veteran.

Architecture B is the primary experiment because the Gaussian precision has a
direct uncertainty interpretation and the survival fit is the shipped model.

## Evaluation and acceptance criteria

CF participant ratings are external ability data, not the official CF problem
ratings used by `arch_b.metric`, so using them is not direct target leakage.
Nevertheless, all validation must be time-causal and source-aware:

1. Run `arch_b.metric` and require an improvement larger than its noise floor or
   corroboration from independent checks.
2. Run `arch_b.predict_eval`; held-out solve AUC/log-loss must not regress.
3. Check Kattis and LLM validation.  The gym yardstick is **not independent** for
   this experiment because it is also built from Codeforces user ratings.
4. Report per-region and per-contest changes; a pooled gain must not come solely
   from already CF-rich contests.
5. Perform an identity-confidence ablation: verified only, then corroborated,
   then name-only sensitivity.  Gains that appear only after name-only matches
   are suspect.
6. Perform a CF-prior holdout: withhold a fold of resolved teams' CF priors, fit
   on the rest, and measure how well fitted `theta` predicts the held-out
   historical team ratings.  This directly tests whether the priors transfer
   through the contest graph.
7. Compare full-roster-only `lse` against `max`.  Do not add partial rosters until
   their missing-member treatment is specified and validated.

The change should be rejected if it improves the CF problem metric while hurting
held-out solves or Kattis, repeats the circular gym-guard mistake documented in
`details.md`, or depends on future/current ratings.

## Proposed implementation order

1. Add a reproducible collector that caches the rated-list snapshot and per-handle
   histories outside the fit path.
2. Produce a reviewed `member -> CF handle` artifact plus a coverage report by
   region, contest, roster completeness, and confidence.
3. Build time-causal full-roster team priors and a dry-run report; do not change
   the estimator yet.
4. Add per-team prior precision to the survival/binary MAP fit and verify the
   baseline is byte-identical when no CF prior is supplied.
5. Run the evaluation matrix above.  Only then make CF priors a default.
