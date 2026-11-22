# LLM difficulty experiments: running and reproducing

> Moved verbatim from `README.md` on 2026-11-20. Text may predate later changes; [docs/STATUS.md](../STATUS.md) is authoritative for what ships now.

## Cross-contest LLM difficulty comparisons

```bash
python llm_crosscontest.py prepare --scope mirrors --matches 6
python llm_crosscontest.py count   --project <gcp-project>
python llm_crosscontest.py run     --project <gcp-project>
python llm_crosscontest.py analyse
```

`llm_survival.py` only ever pairs problems **inside one contest**, which is the
axis the fit already gets right — hence its flat fusion result. This module
pairs problems **across** contests, the axis nothing else can measure, and
validates the instrument first on the 15 CF-mirrored contests where the true
cross-contest levels are known. Partners are drawn uniformly from other contests
(never using our difficulty, a CF rating, or any other target proxy), both A/B
orientations are sent, and `bt_scores` fits Bradley-Terry by coordinate Newton in
O(edges) per sweep so the graph can be far larger than `llm_survival.bt_fit`'s
dense Hessian allows.

**Corrected 2026-09-06:** `analyse` now constructs its held-out adjustment only
from the contest's BT-minus-survival feature; held-out CF labels are scoring-only,
with mutation invariance covered by a regression test. Reanalysis of the saved
responses scores 245.43 plain versus **246.78 adjusted**, so the LLM feature does
not improve LOCO and the wider paid run remains unjustified.

## Planned zero-shot LLM + survival integration

[`llm_survival_plan.md`](../reports/llm/llm_survival_plan.md) applies the pairwise-comparison +
Bradley--Terry method from arXiv:2512.14220 to this repository without replacing
the survival model. The plan uses base zero-shot `gemini-3.5-flash`,
metadata-sanitized statements, both A/B orientations, an uncertainty-aware
survival prior, and nested contest-level validation against the existing metric
and guards. Knowledge cutoff is reporting context, not a split requirement;
solve data, ratings, labels, and other target proxies remain excluded from the
prompt. The document records planning only; no repository problem was dispatched
during that planning task. The plan was subsequently executed on 2026-08-07 with the
user-approved $50 cap. The run used only sanitized per-problem `statement`
text: the contest-level `editorial` field (which contains all problem editorials)
was never read or sent. The 156-request pilot passed parsing and 85.9% A/B
order consistency; the full 2,128-request run completed after two transient
429 retries. Estimated actual inference cost was **$5.4270**.

The result is deliberately not integrated into standings. Re-running the local
analysis against the corrected survival fit gives nested contest-level LOCO
275.68 CF points for survival versus 282.31 for fusion (fusion worse by 6.63),
with 0.733 bootstrap probability that fusion was worse. A/B consistency was 0.816,
BT pairwise accuracy against CF ratings was 0.752, and the selected robust
sparse schedule was 10 unordered matches/problem (mean/minimum Kendall 0.974 /
0.921). Survival remains the default. Use [`llm_survival.py`](../../llm_survival.py)
to reproduce the prepared, resumable workflow; raw statements and responses are
kept in the local gitignored `llm_survival_run/` directory.

## Codeforces pairwise-difficulty tuning pilot

`pairwise_tuning.py` is a separate experiment that teaches Gemini to answer the
same pairwise question used at evaluation time: which of two Codeforces problem
statements is harder? It reuses the official metadata and statement scraper from
`../codeforces_integration`, removes exact statement duplicates, and does not
interpolate the structured problem-title, contest-index, or rating fields into
the prompt. Editorial/tutorial text now passes through a metadata sanitizer in
`cf_pairwise.py` before it is hashed or sent: problem IDs, URLs, title/header
lines, attribution, and rating-footer boilerplate are removed, with prompt-level
regression checks. The historical Phase 2/3 artifacts below predate this fix and
remain unsanitized; the clean base-model diagnostic is recorded in `docs/journal/`.

The frozen temporal contract is 600 training candidates before 2025-02-01,
validation from February–March 2025, and an untouched final test from
2025-04-01 through 2025-05-21. Raw statements and run credentials/results are
gitignored; `data/cf_pairwise/collection_summary.json` records the auditable
collection counts. Generate the deterministic files with:

```bash
./.venv/bin/pip install -r ../codeforces_integration/requirements.txt google-auth
./.venv/bin/python pairwise_tuning.py collect --cf-integration ../codeforces_integration
./.venv/bin/python pairwise_tuning.py prepare --output pairwise_tuning_run
./.venv/bin/python -m unittest discover -s tests -p 'test_*.py'
```

### Copying the frozen pairwise artifacts

The raw problem cache and the three `pairwise_*_run/` directories are deliberately
gitignored. They are required to reproduce the already-submitted experiments
exactly: recollecting would re-scrape live Codeforces statements and editorials.
First clone/pull this repository at the same revision on both computers, then,
from the destination checkout, pull the artifacts over SSH:

```bash
./scripts/sync_pairwise_artifacts.sh pull dedibeat@DESKTOP_HOST
./scripts/sync_pairwise_artifacts.sh verify
```

Replace `DESKTOP_HOST` with the desktop's LAN hostname/IP or Tailscale name/IP.
The helper resumes interrupted transfers and copies `pairwise_tuning_run/`,
`pairwise_phase2_run/`, `pairwise_phase3_run/`, and
`data/cf_pairwise/problems/` (about 38 MB at the published snapshot). To copy
the other direction, run `push` instead of `pull`. If the source repository has
a different path, set `PAIRWISE_ARTIFACT_REPO` before invoking it. `verify`
checks the file counts and content hashes against the tracked
`data/cf_pairwise/artifact_snapshot.json`; update that snapshot intentionally
whenever a new frozen artifact set is published.

The 2026-08-05 pilot uses 400 balanced pairwise examples from 200 training
problems, 150 post-cutoff tuning-validation pairs, two epochs, and a $25 pilot
dispatch cap inside the overall $100 budget. Exact `countTokens` preflight was
649,514 tokens per epoch and $12.99 estimated training cost. The pre-tuning
Gemini 3.5 Flash baseline on 200 swapped-order requests was 69.0% overall,
55.8% at an exact 300-point gap, and 84.0% order-consistent. A deliberately
small 20-request Gemini 3.1 Pro Preview check scored 80.0%; its sample is too
small for a strong model comparison. Vertex accepted tuning job
`projects/703166210069/locations/us-central1/tuningJobs/2518784060365471744`,
which completed successfully. On the identical 200 validation requests, the
tuned model scored 70.0% overall, 37.0% at an exact 200-point gap, 65.4% at an
exact 300-point gap, and 94.0% order-consistent. This is a +1.0-point overall
change and +9.6 points at gap 300, but -4.3 points at gap 200; the paired changes
are too small to establish a reliable improvement. The tuned validation run used
319,416 input and 1,200 output tokens, estimated at $0.81. The final 96-problem
test partition was not uploaded or evaluated.

Phase 2 is submitted as a fresh editorial-only model. It uses all 561
exact-statement-unique substantive-editorial pre-cutoff problems in 400
coverage-guaranteed training pairs, 75 contest-disjoint tuning-validation
pairs, and a separate 100-request development evaluation. The editorial-only
base scored 80.0% overall and 72.5% at gap 300; adding the first scoped author
solution scored 77.0% and 65.0%, while increasing the two-epoch preflight from
$20.87 to $27.80. Code was therefore excluded. The editorial job
`projects/703166210069/locations/us-central1/tuningJobs/3895319841782890496`
completed successfully on 2026-08-06. On the identical clean development
requests, the tuned endpoint improved from 80.0% to 84.0% overall and from
72.5% to 80.0% at the exact 300-point gap; this is only a 100-request
development result, so the final test remains unenriched and untouched.

Phase 3 is a fresh-base-model replication with 600 rather than 400 editorial
pairs. It retains the same 561 problems, tuning-validation split, development
set, two epochs, and prompt; only the 200 additional training comparisons
change. The sampler has no duplicate unordered pairs and uses every problem
one to three times (mean 2.14), with 150/210/240 pairs at 200/300/at-least-400
rating gaps. Exact preflight was 1,608,024 tokens per epoch and $32.16 for two
epochs. Vertex job
`projects/703166210069/locations/us-central1/tuningJobs/8563467981319831552`
completed successfully. Its monitor shows no visible train/validation
divergence, but the near-perfect score is only on the 75-pair tuning-validation
set and may reflect validation-set overfitting; the final test remains
validation-only until a clean final evaluation is run.

The final evaluation then used the frozen 96-problem test partition as 500
unordered pairs in both orientations (1,000 editorial-only requests). The one
short but official tutorial for `2086A` was retained as an explicit exception;
no solution code was included. The base model ran through Vertex batch job
`projects/703166210069/locations/us/batchPredictionJobs/7631252811556061184`,
and the tuned model used endpoint
`projects/703166210069/locations/us/endpoints/4697676623812493312`. All 2,000
responses were valid. Base scored 82.3% overall versus 85.2% tuned, a +2.9
percentage-point gain. The tuned gains were +2.3 points at exact gap 200,
+5.3 at exact gap 300, +3.1 at gaps of at least 300, and +1.3 at gaps of at
least 400; swapped-order consistency rose from 77.8% to 89.2%. The scorer's
non-global list-rate estimates were $5.119 for base and $7.589 for tuned;
generated predictions and the final score remain gitignored artifacts.

As an exploratory reasoning audit, the same final-test pool was sampled into 50
unordered pairs (15 exact-200, 15 exact-300, and 20 at least 400) and sent in
both orientations with `thinkingLevel=HIGH` and returned thoughts enabled. On
these 100 requests, base scored 84.0% and tuned 81.0%; this is a -3.0-point
change and is not an independent test because it reuses the final-test pool.
Both sides returned 100 valid decisions and thought text on 98/100 requests.
The raw reasoning-audit predictions and score are gitignored under
`pairwise_phase3_run/`; the evaluator now uses a 4,096-token output allowance
when thought capture is enabled so the final JSON decision is not truncated.

A forensic join against the minimal-reasoning outputs changes the interpretation.
On those exact 100 requests, minimal reasoning scored 81.0% for both base and
tuned; high reasoning raised base to 84.0% but left tuned at 81.0%. The
high-thinking tuning delta has a wide approximate 95% paired-pair interval of
-12.0 to +6.0 points and is not evidence that tuning hurts. High reasoning cost
about 3.9x base and 4.1x tuned inference on the same sample, with no reliable
accuracy gain, so this pilot does not justify enabling it.

More importantly, verbatim tutorial text contaminates the intended metadata-free
comparison. Literal problem IDs occur in 51/96 final-test problem prompts and
title text in 66/96; 816/1,000 ordered final requests contain at least one
literal ID. The same issue affects training: 352/600 Phase 3 pairs contain at
least one literal ID, and every tuning-validation pair does. Returned thoughts
explicitly use forbidden problem letters, inferred contest positions, and
supposed ratings. Consequently the +2.9-point final gain is a positive result
only for the current unsanitized editorial input, not clean evidence that tuning
improves intrinsic algorithmic-difficulty judgment. A fresh sanitized
train/validation build, fresh tuning job, and untouched clean test are required
before making that claim; the existing final pool has already been used and does
not supply that clean test. A 40-request-per-setting base-only check after the
sanitizer gave 80.0% minimal versus 82.5% high reasoning, with 70.0% versus
85.0% swapped-order consistency. This is a small development diagnostic, not a
replacement for the fresh tuned-model and untouched-test evaluation.

## Gemini 3.6 vs 3.5 gap check

Using the same frozen statement-only pairs in both orientations, Gemini 3.5
Flash scored 21/46 (45.7%, 95% CI 32.2–59.8%) at an exact 200-point gap and
31/52 (59.6%, CI 46.1–71.8%) at 300. Gemini 3.6 Flash scored 16/46 (34.8%, CI
22.7–49.2%) and 30/52 (57.7%, CI 44.2–70.1%), respectively. The 3.5 point
estimates are higher, but the paired differences are inconclusive at this
sample size. Gemini 3.6 was more A/B-order consistent: 82.6% vs 78.3% at 200
and 84.6% vs 57.7% at 300. Details and raw ignored outputs are in
`docs/journal/` and `gemini_gap_run/`.


The [five-hour Codeforces standings search](../reports/codeforces/cf_five_hour_search.md) tested rolling player histories, solve speed, earlier ranks, problem tags and boosted models against log loss, Brier score, calibration error and within-problem AUC.
