# Zero-shot LLM + survival-model integration plan

Status: **plan only**. No repository problem statement or model output was sent
to Gemini while preparing this document.

## Fixed decisions

- Use the base Vertex publisher model `gemini-3.5-flash` zero-shot. Do not use a
  tuned endpoint or pairwise training data.
- Use minimal thinking, temperature 0, structured output, and a binary
  `{"harder":"A"|"B"}` response.
- Keep the survival model as the empirical backbone. Gemini is a second,
  statement-derived signal; it does not replace standings evidence.
- Do not make knowledge cutoff a dataset-selection requirement. The experiment
  is about operational incremental value, not a contamination-proof benchmark.
- Enforce target isolation instead: Gemini must not receive problem labels or
  order, titles/URLs, contest identity, solve counts/times, tags, existing LLM
  labels, survival ratings, Codeforces ratings, or medal information.
- Start with statement-only comparisons. Editorials and solution code are out of
  scope for the first experiment.

Google documents `gemini-3.5-flash` as the GA model ID and supports system
instructions, structured output, thinking control, and Count Tokens. See the
[official model card](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/models/gemini/3-5-flash).

## What the paper contributes

[Ballon et al. (arXiv:2512.14220)](https://arxiv.org/abs/2512.14220) propose
**LLM compare**:

1. Ask an LLM which of two problems is harder, without asking it to solve them.
2. Aggregate the comparison graph into continuous Bradley--Terry (BT) strengths.

For their small 34-problem dataset they compare every pair. For larger datasets,
they subsample and select 36 or 66 matches per problem after checking convergence
against a 200-match reference. They fit BT strengths with iterative Luce spectral
ranking (`alpha=0.01`). Their strongest relevant findings are good alignment with
human labels, similar rankings from two different frontier models, and graceful
degradation when comparison outcomes are randomly flipped.

The paper does **not** show that its match counts transfer to competitive
programming, does not test a standings-survival model, and does not measure the
incremental value of fusing LLM judgments with strong performance evidence.
Those are the questions for this repository.

## Why fusion may help

The two signals fail differently:

- The survival model uses who solved a problem and when. It is strongest for
  well-observed problems, is already calibrated to CF-equivalent points, and
  emits a difficulty standard error. It becomes weak in the 0--1-solver hard
  tail because standings contain little ordering information there.
- Gemini sees algorithmic insight, proof burden, and implementation complexity
  in the statement. It can distinguish two equally rare problems, but its scale
  is ordinal, comparisons can be inconsistent, and it can use unintended
  metadata if prompts are not sanitized.

The intended role of Gemini is therefore to move high-uncertainty survival
estimates more than low-uncertainty ones and to provide provisional ordering when
standings are absent.

## Planned experiment

### Stage 1: one-contest protocol pilot

Use QOJ contest 3747 / Codeforces 2206 (2026 ICPC Asia Pacific Championship):
13 problems, 78 unordered pairs, both orientations, **156 ordered requests**.
This contest already has survival outputs and 13 official CF ratings.

The pilot may validate only the pipeline, prompt contract, cost, parsing, and
order consistency. It is too small to select a fusion method or claim an
accuracy improvement.

For every request:

- strip the title, contest/index headers, page markers, URL, and all structured
  metadata from both statements;
- randomize the displayed A/B orientation deterministically, then send the
  reverse orientation as a second request;
- cache model ID, prompt version/hash, statement hashes, response, token usage,
  request location, and timestamp;
- never interpolate survival or evaluation values into the request.

Treat the two orientations as two BT matches. If Gemini selects the same
underlying problem both times, it supplies two wins; if it reverses its judgment,
each problem receives one win. This incorporates order inconsistency without a
hidden tie-breaking rule.

### Stage 2: all rated mirrors

If Stage 1 passes its execution checks, run the same protocol on all 15 mapped
CF mirrors already used by `arch_b.metric`: **185 problems and 2,128 ordered
full-round-robin requests**. Repeated statement text is roughly 11.4 million
characters (about 2.9 million tokens before exact tokenization). Run Vertex
Count Tokens and record a current price estimate before dispatch.

Full round-robin is affordable here because each contest has only 8--14 mapped
problems. It also creates the reference graph needed to test cheaper schedules.
Subsample each completed graph to 4, 6, 8, and 10 matches per problem and measure
Kendall correlation against its full BT ranking. Do not import the paper's
36/66-match thresholds without this domain-specific check.

### Stage 3: aggregate and fuse

First report Gemini independently, within contest:

- BT score and Hessian/bootstrap uncertainty;
- Spearman/Kendall correlation and pairwise accuracy versus official CF rating;
- A/B order consistency;
- stability under match-graph subsampling;
- results by CF gap and by survival uncertainty bucket.

Then fit an uncertainty-aware fusion in the survival model's raw scale. For
problem difficulties `d_i`, use

```text
d_i ~ Normal(b_survival_i, se_survival_i^2 + tau^2)
P(Gemini says i > j) = sigmoid((d_i - d_j) / kappa)
```

`tau` is an uncertainty floor and `kappa` is Gemini's comparison temperature.
An optional likelihood weight may account for correlated/repeated judgments.
This is preferable to a fixed 50/50 average: strong standings evidence stays
stable, while sparse high-SE problems can move more.

Choose `tau`, `kappa`, and any likelihood weight only inside the training side of
a nested leave-one-contest-out evaluation. The held-out contest's CF ratings must
never affect its fusion. Apply the repository's locked gym shape and refit only
the affine scale leg on the other contests, matching the current metric contract.
The fit path must not read `data/cf_problemset.json` or any other yardstick.

## Evaluation and success criteria

The primary comparison is survival-only versus fused calibrated LOCO CF RMSE.
The current survival baseline is 261.6 CF points.

Proceed to shadow integration only if all conditions hold:

- fused calibrated LOCO improves by at least **5 CF points** (the repository's
  existing noise-aware keep threshold);
- a contest-cluster paired bootstrap gives less than 10% probability that fusion
  is worse;
- the existing raw-affine, gym Asia-East, gym pooled, Kattis, AOJ, and solve-count
  guards all pass unchanged;
- the full BT reference has at least 80% A/B order consistency, and the selected
  sparse schedule reaches Kendall `tau >= 0.90` against the full graph;
- every request parses, prompt/statement hashes verify, and cost/latency are
  recorded.

Also report per-contest results. A pooled win driven by one contest is not enough.
Official CF ratings are an evaluation yardstick only; they do not become prompt
content, a BT prior, or a fusion feature.

## Workflow integration if the experiment wins

1. Run the survival fit and calibration exactly as today.
2. Select all high-SE / 0--1-solver problems plus a small set of well-observed
   anchors spanning the contest's survival scale.
3. Compare selected pairs in both orientations with base zero-shot Gemini.
4. Update the uncertainty-aware fusion and write separate fields such as
   `difficulty_cf_fused`, `difficulty_cf_fused_se`, and `llm_comparison_count`.
   Do not overwrite the survival fields during shadow deployment.
5. Show the LLM adjustment and large disagreement flags in the viewer. Preserve
   the raw comparison artifact so every adjustment is auditable.
6. When final standings arrive, compare the provisional LLM/fused estimate with
   the new survival estimate. This prospective check is more useful here than a
   strict knowledge-cutoff split.

For a brand-new problem with no standings, compare it adaptively with 8--12
sanitized anchor statements spanning the calibrated scale. Give it a broad
prior, label the result **LLM-provisional**, and replace or fuse it once real
standings arrive.

## Decision branches

- **Fusion clears every gate:** add it in shadow mode, then require a second
  prospective contest set before making it the displayed default.
- **Gemini correlates with CF but fusion does not improve LOCO:** keep survival as
  the rating and use Gemini only for no-standings estimates and disagreement QA.
- **Order consistency or stability is weak:** do not integrate; test one prompt
  revision on development contests only, or stop.
- **External guards regress:** reject the fusion even if CF LOCO improves.

## Planned implementation order

1. Add statement sanitizer, immutable manifest builder, paired request runner,
   resumable checkpoints, and tests. Verify locally without API calls.
2. Add BT aggregation, uncertainty, scoring, and graph-subsampling tests.
3. Produce a Count Tokens/cost preflight and request explicit approval before the
   156-request Stage 1 dispatch.
4. Review Stage 1. Request separate approval before the 2,128-request Stage 2.
5. Add the fusion only after all raw Stage 2 responses are frozen; run nested
   LOCO and existing guards.
6. If accepted, add shadow output/viewer fields and prospective monitoring.

This order keeps the first code change small and makes every paid or externally
mutating step separately reviewable.
