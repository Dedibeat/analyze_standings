# Codeforces pairwise Gemini pilot (2026-08-05)

This experiment is intentionally separate from the standings fit. Codeforces
ratings supply the supervised truth because the deployed operation is itself a
binary comparison. Training directly on rating classes would add an unnecessary
absolute-calibration problem, while Vertex managed SFT does not expose a custom
pairwise loss. Each JSONL target is therefore only `{"harder":"A"}` or
`{"harder":"B"}`.

Key leakage and evaluation decisions:

- Google's Gemini 3.5 Flash knowledge cutoff is documented only as January
  2025, so 2025-02-01 is the first unambiguously post-cutoff date.
- The newest 600 usable, exact-statement-deduplicated pre-cutoff problems form
  the stage-two pool. The first pilot stratifies 200 of them by rating and draws
  400 comparisons: 25% exact-200, 35% exact-300, and 40% at least 400 points,
  with A/B truth balanced.
- February–March 2025 supplies tuning validation and the zero-shot baseline.
  April 1–May 21 supplies 96 problems in a frozen final test. Final-test
  statements and labels are never uploaded with the tuning job.
- Every baseline unordered pair is sent in both orientations. This measures
  order bias as well as accuracy. The final small Flash prefix contains 200
  requests; the Pro sanity check contains 20 requests and is not powered for a
  close model comparison.
- Tuning uses two epochs and automatic adapter selection. The tokenizer gate
  rejected the original 500-pair plan ($16.38 training and $26.38 including the
  reserve) and accepted 400 pairs ($12.99 training, $22.99 planned total).
  This preserves the two-epoch pilot while staying below the local $25 cap and
  well below the user's $100 ceiling.

Collection found 600/600 usable pre-cutoff statements and 227/248 usable rated
post-cutoff statements. Missing statement pages remain missing rather than being
filled from guessed or weak sources. The resulting partitions are 600 train
problems across 82 contests, 131 validation problems across 21 contests, and 96
test problems across 15 contests.

The frozen zero-shot results are: Gemini 3.5 Flash with minimal thinking, 69.0%
overall, 41.3% at exact 200, 55.8% at exact 300, 77.3% at gaps of at least 300,
88.2% at gaps of at least 400, and 84.0% swapped-order consistency; Gemini 3.1
Pro Preview with low thinking, 80.0% overall and 100% order consistency on only
20 requests. Capacity returned repeated 429s, so resumable checkpoints were
served across global, US, and EU endpoints; each prediction records its request
location. The Flash alias, prompt, temperature, schema, and thinking level were
unchanged.

Vertex job
`projects/703166210069/locations/us-central1/tuningJobs/2518784060365471744`
was submitted with 400 training examples, 150 validation examples, and two
epochs. It completed successfully on 2026-08-05 and produced tuned endpoint
`projects/703166210069/locations/us/endpoints/432767776692633600`.

The 2026-08-06 tuned evaluation reused all 200 frozen ordered validation
requests. All calls returned valid predictions. Tuned accuracy was 70.0%
overall, 37.0% at exact gap 200, 65.4% at exact gap 300, 79.9% at gaps of at
least 300, 87.3% at gaps of at least 400, and 94.0% swapped-order consistency.
Against the paired base results this is +1.0, -4.3, +9.6, +2.6, -1.0, and +10.0
percentage points respectively. Across all requests, tuning corrected 12 base
errors but changed 10 base successes to errors; at exact gap 300 those counts
were 8 and 3. Exact paired tests are not significant (all requests p=0.832;
gap 300 p=0.227), and the two orientations of each unordered problem pair are
correlated. Phase 1 therefore shows a promising 300-gap and order-consistency
signal, not a confirmed generalization gain. The tuned run used 319,416 prompt
tokens and 1,200 output tokens, estimated at $0.808 at the tuned non-global
rate. Estimated training plus both base and tuned validation inference is
$14.35. The untouched final test remains unevaluated.

## Phase 2 statement-plus-editorial preparation (2026-08-06)

Phase 2 is a fresh-base-model experiment, not continuation tuning. Each side
of a comparison will contain `[Statement]`, `[Editorial]`, and optionally the
first scoped author reference-solution block. The intended comparison is
statement-only base versus editorial-only base versus editorial-tuned, with the
code variant admitted only after its exact token preflight. Titles, ratings,
tags, contest identifiers, and problem indices are not interpolated from their
structured fields. The official tutorial is inserted verbatim, however; the
later high-thinking audit found that many tutorials contain their own identifier
and title header, so the effective prompt does not satisfy this intended
metadata exclusion (see the forensic follow-up below). A new preparation command
uses 400 quota-balanced pairs while ensuring every selected training problem
appears at least once. Its tuning-validation and development sets are
contest-disjoint; the final test is not enriched, uploaded, or evaluated.

The integration captured 623/731 non-empty tutorials and 469/731 code-bearing
records for the original training-plus-validation pool. That count was not
accepted as evidence of usable editorials. A random manual audit of
`1975E`, `1986C`, `1989E`, `1991A`, `1999C`, `2002G`, `2032F`, `2072A`,
`2077E`, and `2081B` checked each statement against its saved Codeforces
problem and tutorial URLs. All ten tutorial headings/entities matched the
correct task; six contained substantive task-specific prose (`1975E`, `2002G`,
`2032F`, `2072A`, `2077E`, `2081B`). The other four (`1986C`, `1989E`,
`1991A`, `1999C`) were title-only or video-only captures and are excluded.

Accordingly, a tutorial is now substantive only when it has at least 200
characters after whitespace normalization and is not a video-editorial marker.
Under that rule the original split has 423/600 substantive training records and
112/131 substantive validation records. We collected 150 older exact-statement
candidates (750 pre-cutoff statement candidates total), completed their
resumable enrichment, and deduplicated exact statements again. The user
explicitly accepted the resulting 561 substantive pre-cutoff problems rather
than requiring 600. All 561 occur in the 400 quota-balanced training pairs;
458 have an extracted first author-solution block. The 75 tuning-validation
pairs and 100 swapped-order development requests are contest-disjoint.

Three independent 10-record manual audits then checked saved statement text,
tutorial text, task identifiers, and saved Codeforces problem/tutorial URLs.
All 30 were task-matched and substantive; no title/video-only capture or
cross-problem contamination was found. Live Codeforces verification remains
Cloudflare-blocked, so this is a source-metadata and content identity audit,
not a fresh-page fetch.

Exact global `countTokens` preflights on the same 400 training pairs returned
1,043,341 tokens/epoch and $20.86682 for two editorial-only epochs, versus
1,390,192 tokens/epoch and $27.80384 with code. On the clean 100-request
development ablation, base Flash with editorial-only input was 80.0% overall,
70.0% at gap 200, 72.5% at gap 300, and 76.0% order-consistent. Adding code was
77.0%, 70.0%, 65.0%, and 82.0% respectively. Code therefore added cost and
hurt the target 300-gap metric, so the submitted Phase 2 training data is
editorial-only. Actual ablation usage was 269,318 input/1,200 output tokens
for editorial-only ($0.456 estimated) and 341,994/1,200 for code
($0.576 estimated at the base rate).

The verified Cloud Storage uploads are
`gs://gctc-vertex-batch-703166210069/cf-pairwise-20260805/phase2-editorial-v1/phase2_editorial_train.jsonl`
(3,530,316 bytes) and `phase2_editorial_validation.jsonl` (754,934 bytes).
Vertex job
`projects/703166210069/locations/us-central1/tuningJobs/3895319841782890496`
was submitted with two epochs on 2026-08-06 and completed successfully. Its
endpoint is
`projects/703166210069/locations/us/endpoints/8084383543595106304`.

The tuned editorial endpoint was evaluated on the identical 100 clean
development requests: 84.0% overall, 73.3% at exact gap 200, 80.0% at exact
gap 300, 88.6% at gaps of at least 300, 100.0% at gaps of at least 400, and
84.0% swapped-order consistency. Relative to editorial-only base, these are
increases of 4.0, 3.3, 7.5, 4.3, 0.0, and 8.0 percentage points. Tuning corrected
eight base errors while losing four base successes; at gap 300 those counts
were four and one. Exact paired tests are not significant (overall p=0.388;
gap 300 p=0.727), and swapped orientations are correlated, so this is a
positive development signal rather than a final generalization claim. The
tuned evaluation used 269,318 prompt and 600 output tokens, estimated at
$0.675. The $15 evaluation reserve makes the Phase 2 planned total $35.86682
before the already-observed $1.032 base ablation, still below the overall $100
envelope. The final test remains unenriched, unuploaded, and unevaluated.

## Phase 3: larger pairwise supervision (completed 2026-08-06)

Phase 3 is intentionally a fresh `gemini-3.5-flash` base-model run, not an
attempt to continue the Phase 2 endpoint. That isolates the change from 400 to
600 diverse comparisons instead of confounding additional data with repeated
epochs on the old 400-pair signal. It retains Phase 2's 561 substantive,
exact-statement-unique pre-cutoff problems, editorial-only prompt, two epochs,
75 tuning-validation pairs, and frozen 100-request development set.

The first 600-pair draft was sparse but had a degree range of 1--8. Before any
upload, the sampler was corrected to track pair-bucket allocation separately
from problem degree. The submitted set has no duplicate unordered pair, covers
all 561 problems, has degree distribution 26 once / 431 twice / 104 three
times (mean 2.14, max 3), and preserves 150 exact-200, 210 exact-300, and 240
at-least-400 gap pairs. The correction is regression-tested.

The corrected global `countTokens` preflight returned 1,608,024 tokens per
epoch and $32.16048 estimated training cost for two epochs ($47.16048 with the
$15 evaluation reserve). Verified uploads are in
`gs://gctc-vertex-batch-703166210069/cf-pairwise-20260805/phase3-editorial600-v1/`:
the train file is 5,438,197 bytes and the validation file 754,934 bytes. Vertex
job `projects/703166210069/locations/us-central1/tuningJobs/8563467981319831552`
completed successfully, as shown by the Vertex tuning monitor. The monitor's
training and tuning-validation curves do not show the usual visual signature of
overfitting: validation accuracy rises with training accuracy and validation
loss does not turn upward. This is not an independent generalization result,
however—the 75-pair validation set was used by the tuning job, and the curves
reach nearly perfect accuracy/near-zero loss. The final test remains
unenriched, unuploaded, and unevaluated at that point in the phase-completion
record; the authorized evaluation is recorded below.

The final evaluation was subsequently authorized after the development decision.
All 96 frozen final-test problems were editorial-enriched from the sibling
Codeforces scraper and verified against the manifest hashes. The test contains
500 unordered pairs in both orientations, for 1,000 ordered requests. The
input mode was editorial-only: each prompt contained the statement and official
tutorial, with no author solution code. Problem `2086A` had a short but genuine
official tutorial, so it was included under an explicit final-test exception
rather than silently falling back to statement-only input.

The base requests were completed by batch job
`projects/703166210069/locations/us/batchPredictionJobs/7631252811556061184`;
the tuned requests used endpoint
`projects/703166210069/locations/us/endpoints/4697676623812493312`. All 1,000
responses on each side parsed as valid `{"harder":"A"|"B"}` predictions.
The paired results were:

| Metric | Base | Tuned | Change |
|---|---:|---:|---:|
| Overall | 82.3% | **85.2%** | **+2.9 pp** |
| Exact gap 200 | 67.7% | 70.0% | +2.3 pp |
| Exact gap 300 | 77.0% | 82.3% | +5.3 pp |
| Gap at least 300 | 88.6% | 91.7% | +3.1 pp |
| Gap at least 400 | 97.3% | 98.8% | +1.3 pp |
| Swapped-order consistency | 77.8% | 89.2% | +11.4 pp |

Usage was 3,030,230 prompt and 12,000 output tokens for base, and 3,030,230
prompt and 6,000 output tokens for tuned (plus 15,870 cached-content tokens
reported by the tuned endpoint). At the evaluator's non-global list-rate
estimate, this was $5.118679 for base and $7.588919 for tuned. These are final
test results, not tuning-validation results. They support a positive Phase 3
result on the current unsanitized editorial input, while the forensic audit below
means they do not establish metadata-free intrinsic-difficulty generalization.

## High-thinking reasoning audit (2026-08-07)

To inspect whether additional reasoning changed the comparison, a deterministic
50-pair exploratory sample was drawn from the already-used final-test pool:
15 unordered pairs at gap 200, 15 at gap 300, and 20 at gaps at least 400.
Both orientations were evaluated, giving 100 requests per model. The prompt
remained editorial-only; `thinkingLevel=HIGH` and Vertex's
`thinkingConfig.includeThoughts=true` were enabled. The evaluator stores the
returned thought text with each prediction, while the final JSON decision is
parsed separately. Google's REST schema documents `includeThoughts` as the
switch that returns thoughts when available.

| Metric | Base | Tuned | Change |
|---|---:|---:|---:|
| Overall | 84.0% | 81.0% | -3.0 pp |
| Exact gap 200 | 60.0% | 70.0% | +10.0 pp |
| Exact gap 300 | 90.0% | 73.3% | -16.7 pp |
| Gap at least 300 | 94.3% | 85.7% | -8.6 pp |
| Gap at least 400 | 97.5% | 95.0% | -2.5 pp |
| Swapped-order consistency | 88.0% | 86.0% | -2.0 pp |

All 200 responses were valid. Thought text was returned on 98/100 requests for
each model. Usage was 321,452 prompt, 157,497 thought, and 1,185 output tokens
for base; tuned used 321,452 prompt, 168,434 thought, and 600 output tokens.
The evaluator's non-global list-rate estimates were $2.101348 and $3.305749,
respectively. Because this audit reuses final-test problems and has only 50
unordered pairs, it is diagnostic evidence rather than a replacement for the
1,000-request final result.

An additional paired close-gap check used 10 new unordered validation pairs
(five at a 200-point gap and five at 300), sent in both orientations to both
models. On these 20 new requests, Flash scored 12/20 (60%) and Pro 11/20 (55%):
both were 4/10 at gap 200, while Flash was 8/10 and Pro 7/10 at gap 300. Combining
these with the earlier paired close-gap requests gives 28 matched ordered
comparisons: both models are 6/14 (42.9%) at gap 200; Flash is 12/14 (85.7%) and
Pro 9/14 (64.3%) at gap 300. This is still only 14 unordered problems represented
twice, and order consistency on the new close-gap subset was 60% for Flash and
70% for Pro, so the apparent 300-gap advantage remains a pilot signal rather
than a reliable model-ranking claim.

### Forensic follow-up: reasoning behavior and prompt contamination

Joining the high-thinking audit back to the minimal-thinking final predictions
separates the sample effect from the reasoning setting:

| Same 50 unordered pairs / 100 requests | Base | Tuned | Tuning change |
|---|---:|---:|---:|
| Minimal thinking | 81.0% | 81.0% | 0.0 pp |
| High thinking | 84.0% | 81.0% | -3.0 pp |

At the unordered-pair cluster level, the high-thinking tuning change has an
approximate 95% interval of **-12.0 to +6.0 points**. High thinking changed
13/100 base decisions and 18/100 tuned decisions; it corrected eight and lost
five base decisions, while correcting and losing nine tuned decisions. It cost
$2.101348 base and $3.305749 tuned, versus $0.542276 and $0.804504 under minimal
thinking on the same requests (**3.9x / 4.1x**). Incorrect high-thinking answers
were also much longer on average than correct ones (base 2,355 vs 1,426 thought
tokens; tuned 2,498 vs 1,494). These are diagnostic associations on a small
sample, not evidence that length causes errors, but they show no return from the
extra reasoning budget. The large minimal-thinking final comparison remains
+2.9 points (an approximate paired-pair 95% interval of **+0.9 to +4.9**) with
the much stronger 77.8% to 89.2% order-consistency gain.

The trace audit also found a contract violation in the *effective* prompt. The
prompt builder omits structured title, ID, index, and rating fields and tells the
model not to use them, but `editorial_text` passes the official tutorial through
verbatim. Many tutorials start with text such as `2096E - Wonderful Teddy Bears`
or `Problem G1 - BAUDELAIRE (Easy Version)`:

- 192/561 Phase 3 training problems contain their literal problem ID in the
  rendered editorial input and 247/561 contain title text. Across the submitted
  600 training comparisons, 352 have at least one literal ID (71 have two).
- All 75 tuning-validation pairs expose at least one literal ID (47 expose both).
- 51/96 final-test problems expose a literal ID and 66/96 expose title text.
  Thus 816/1,000 ordered final requests contain at least one literal ID; the
  high-thinking audit contains 82/100.

The returned reasoning uses exactly this forbidden channel: problem letters,
supposed contest placement, and numerical-rating guesses appear repeatedly. A
representative tuned failure is `2084F` versus `2106G1` (true ratings 2900 vs
2200). The high-thinking base chose `2084F` in both orientations from the
algorithmic burden. The tuned trace chose `2106G1` in both, incorrectly asserted
that the two were from the same round, and treated the later `G1` position as
decisive. On `2096E` versus `2109C3`, the base trace reversed its semantic
judgment when A/B order was swapped, alternately prioritizing a rare one-trick
discovery and a longer invariant proof. This is label/order-sensitive narrative,
not stable difficulty comparison.

The existing +2.9-point result is therefore valid only as an operational score
for **unsanitized tutorial inputs**. It cannot establish that tuning improves the
intended metadata-free, inherent-difficulty judgment, even though the observed
gain is not confined to the simplest literal-ID subgroup. At the time of this
audit the clean test was still missing: tutorials needed to be sanitized (with
regression checks against IDs, contest/index markers, and titles), training and
tuning validation regenerated, a fresh base model tuned, and evaluation run on
an untouched temporal test. Cleaning only the current endpoint's evaluation
would introduce a train/eval distribution shift, and the existing final pool has
already been evaluated repeatedly.

## Metadata-sanitized base reasoning check (2026-08-07)

`cf_pairwise.editorial_text` now sanitizes tutorial and optional reference-solution
text before it is used for hashes, tuning JSONL, or evaluation prompts. It removes
problem-ID tokens (including IDs mentioned in a tutorial), URLs, title/header
lines, author/analysis/credit attribution, and the Codeforces rating footer. The
prompt path raises if an ID, URL, or source problem title survives. The tests cover
the `2084F`-style header, the `Problem G1` header, parenthesized attribution, and
reference-solution preservation. The cached-source audit found 845 non-empty
metadata-free tutorials; 17 records contain only metadata headers and remain
excluded. Rebuilding the editorial dataset gives 558 substantive pre-cutoff
training problems (the old unsanitized build had 561), 400 training pairs, 75
contest-disjoint tuning-validation pairs, and a 100-request contest-disjoint
development pool.

As a small base-model diagnostic, 20 unordered development pairs were sent in
both orientations (40 requests per setting) to `gemini-3.5-flash` with the same
clean editorial prompts and captured thoughts:

| setting | accuracy | exact-300 | ≥300 | ≥400 | swapped consistency | estimated inference cost |
|---------|---------:|----------:|-----:|-----:|---------------------:|--------------------------:|
| minimal | 80.0% | 68.2% | 80.6% | 100.0% | 70.0% | $0.184028 |
| high | 82.5% | 68.2% | 80.6% | 100.0% | 85.0% | $0.800352 |

High reasoning changed 5 of the 20 unordered-pair outcomes relative to minimal
(three improved, two worsened), so this sample suggests a +2.5-point accuracy
and +15-point order-consistency difference but is too small for a model-setting
claim. It cost about 4.35× as much. All 40 responses in each setting were valid.

Manual prompt inspection found no problem-ID token in the 400 training, 75
tuning-validation, or 40 evaluated development prompts, and neither member of
an evaluated pair's title appeared in the other prompt's editorial snippet. No
Codeforces ID appeared in the 40 high-thinking traces. Some high-thinking traces
guessed or reconstructed titles/divisions despite their absence from the prompt;
that is model behavior or pretraining, not input leakage, and is a reason to keep
the system instruction prohibiting external metadata. This check does not make
the old 2026-08-05/06 final result clean: that final pool was already evaluated
with unsanitized tutorials. A fresh tuned checkpoint and a new untouched temporal
test are still required for a clean tuning claim.

## Frozen-artifact transfer protocol (2026-08-06)

The raw Codeforces cache and pairwise run directories are intentionally excluded
from Git: `data/cf_pairwise/problems/`, `pairwise_tuning_run/`,
`pairwise_phase2_run/`, and `pairwise_phase3_run/`. They must be copied to
resume or audit the existing experiments, because a new collection re-scrapes
mutable live statement/editorial pages and is not an exact reproduction.

`scripts/sync_pairwise_artifacts.sh pull USER@HOST` transfers all four roots
from a matching checkout at the fixed default source path, resuming partial
transfers through `rsync`. `push` reverses the direction; set
`PAIRWISE_ARTIFACT_REPO` when the remote checkout uses another path. After any
transfer, `scripts/sync_pairwise_artifacts.sh verify` checks all copied files
against the tracked `data/cf_pairwise/artifact_snapshot.json`. That snapshot
records the 3f58b08 artifact set: 29 pilot-run files, 15 Phase-2 files, 9
Phase-3 files, and 978 cached problem records. A future frozen set requires an
intentional snapshot update and commit; it must never silently replace the
published verification target.
