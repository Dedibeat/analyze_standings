# Planned zero-shot LLM × survival integration (2026-08-07)

The integration requested after reading arXiv:2512.14220 is documented in
[`llm_survival_plan.md`](../reports/llm/llm_survival_plan.md). The fixed scope is the base Vertex publisher model
`gemini-3.5-flash` with zero-shot, minimal-thinking, statement-only pairwise
comparisons. No tuned endpoint is involved. Knowledge cutoff is deliberately not
a selection constraint: the operational isolation rule is that prompts contain
no title/index/contest metadata, solve counts or times, existing labels,
survival outputs, CF ratings, tags, or medal data.

The proposed first dispatch is a separately approved 13-problem protocol pilot
on qoj 3747 / CF 2206: full round-robin in both orientations, 156 requests. If
its parsing, order-consistency, and cost checks pass, the evidence experiment
expands to all 15 rated mirrors (185 problems, 2,128 ordered requests). Gemini
comparisons are aggregated with Bradley--Terry, then enter an uncertainty-aware
MAP fusion as pairwise likelihood terms around the survival difficulty/SE prior.
Nested contest-level LOCO keeps held-out CF ratings out of the fit. Shipping
requires at least a 5-point improvement over calibrated LOCO 261.6, favorable
contest-cluster bootstrap evidence, and every existing metric guard unchanged.
Otherwise Gemini remains limited to provisional no-standings ratings or
disagreement QA. No repository problem statement or fitted rating was sent to
Gemini while preparing the plan.

## Executed zero-shot run (2026-08-07)

The plan was then executed under the user's $50 budget with the base
`gemini-3.5-flash` publisher model in Vertex `global`. The pilot used 156
ordered requests (13 problems, both orientations), all responses parsed, with
85.9% orientation consistency. The full run used 185 problems across 15 mapped
contests and 2,128 ordered requests. It completed with 2,128 valid responses;
two transient 429 responses were retried, and no malformed response remained.

This was a strict statement-only run. The sanitizer read each problem's
`statement` field and removed title/index/contest furniture, URLs, page
markers, and limits. A contest-level `editorial` field (which contains the
editorials for all problems) was never read or serialized into a prompt. The
run also excluded solve counts/times, tags, survival estimates, CF ratings, and
medal data. Knowledge cutoff was not used as a selection criterion.

Count-Tokens preflight estimated $6.3221 for the full dispatch; successful
response usage estimates total inference cost at **$5.4270**, within the $50
budget. The raw manifest, sanitized statements, checkpoints, and report remain
in the local gitignored `llm_survival_run/` directory; the resumable runner and
tests are tracked in `llm_survival.py` and `tests/test_llm_survival.py`.

The independent Gemini BT ranking reached 0.752 pairwise accuracy against CF
ratings and 0.816 orientation consistency. After the full-cell correction, the
local nested contest-level analysis gives survival-only RMSE **275.68** and
fused RMSE **282.31** (fusion worse by 6.63 points), with contest bootstrap
probability fusion was worse **0.733**. The smallest sparse graph stable in both
mean and worst-contest Kendall correlation remains 10 unordered matches/problem
(0.974 mean, 0.921 minimum). The two fusion gates therefore fail; the order,
sparse-graph, and budget checks pass. `arch_b.metric` remains unchanged and all
existing guards pass, so survival remains the default and no shadow rating
fields were added.

## Post-fix retest of the DeepResearch experiments (2026-08-08)

The earlier experiment logs were rechecked after the censored full-cell fix
(`76a458c`) and the unknown-problem-label retention fix (`c783db6`). No input
data or external ratings were changed. The regression suite passes **29/29**
tests. The main corrected fit uses 774,639 Architecture B observations after
including omitted no-attempt cells.

The current optimization results are:

| fit / check | result |
|---|---:|
| Architecture A median solve-count Spearman | −0.995 |
| Architecture B binary calibrated LOCO / raw LOCO | 254.2 / 248.3 CF |
| Architecture B survival calibrated LOCO / raw LOCO | **244.2 / 245.2 CF** |
| survival guards: Gym EC / Gym pooled / Kattis / AOJ / solve sanity | +0.978 / +0.969 / +0.772 / +0.568 / +0.995 |

The external validation retest gives the following pooled/per-region values:

| model | CF pooled | AsiaPac | N. Eur. | Europe | Kattis pooled | Gym pooled | LLM |
|---|---:|---:|---:|---:|---:|---:|---:|
| arch A | +0.913 | +0.920 | +0.973 | +0.861 | +0.692 | +0.960 | +0.907 |
| arch B binary | +0.937 | +0.942 | +0.974 | +0.896 | +0.755 | +0.971 | +0.908 |
| arch B survival | **+0.942** | **+0.944** | +0.972 | **+0.902** | **+0.771** | +0.969 | **+0.911** |

The conclusions that survive the correction are:

- The season experiment remains neutral for the 5-hour filter and slightly
  disfavors hard season splitting: baseline `245` CF LOCO, `+5h` `245`, and
  `+season +5h` `246`; the corresponding LLM Spearman is +0.911 for all three.
  Its harness had a stale unused `CF_REF` import, which was removed so the
  documented command runs again.
- The 2PL regional probe still overfits. The corrected held-out check is Rasch
  AUC **0.9733** versus 2PL **0.9724**; corrected median alpha is 2.56 in Asia
  East, 2.47 in Europe, 2.40 in Northern Eurasia, 2.02 in Asia Pacific, and
  1.55 in North America. The prototype harness now discards the anchor's
  unused `gym_obs=None` argument.
- The corrected held-out tagged-only solve check has 598,205 cells. Binary is
  better on this split (log-loss/Brier/AUC `0.2009/0.0615/0.9733`) than survival
  (`0.2309/0.0699/0.9673`), so the old claim that survival wins this internal
  check is no longer current. Survival remains the shipped model because it
  adds solve-time structure and wins the broader external ranking checks.
- Re-running `arch_b.medals` produces **85 bronze / 41 silver / 40 gold / 88
  platinum / 104 star**; gold bars span **[2316, 2828] CF** with median **2540**.
  The regional chooser still reports the same top three 2026 cities:
  Hong Kong, Shanghai, and Shenyang, with 105 CF historical forward RMSE.
- The frozen zero-shot Gemini responses were analysed locally again against the
  corrected survival ratings; no inference was dispatched. Nested LOCO is
  survival **275.68** versus fusion **282.31** CF (fusion worse by 6.63), with
  bootstrap probability fusion is worse **0.733**. This reinforces the prior
  decision not to integrate the pairwise model into standings. Pairwise
  accuracy remains 0.752, order consistency 0.816, and the stable sparse
  schedule remains 10 matches/problem.

The specific keep/control rows from
`autoresearch/loop-260723-1333/classic-results.tsv` were also rerun where the
source inputs are present:

| TSV experiment/control | corrected calibrated LOCO | conclusion |
|---|---:|---|
| current WF links + older ICPC + Petroz | **244.2** | baseline |
| no WF identity links | 244.2 | metric-neutral; keep for correctness |
| include WF solve rows | 244.3 | discard |
| omit older ICPC | 244.3 | addition is only −0.1, below noise |
| omit Petroz | 245.9 | addition is −1.7, below the 5-point keep threshold |
| `sigma_theta=300 / 500 / 600` | 243.8 / 243.5 / 242.9 | sub-noise; survival AUC 0.9674 / 0.9670 / 0.9666 |
| latest solve threshold 3.0 / 4.0 / 4.5 h | 244.2 / 244.1 / 244.0 | sub-noise; 4.5 h lowers Kattis slightly |
| exclude Asia West / exclude online qualifiers | 242.1 / 243.5 | sub-noise; no independent corroboration |
| all zero-solve / stable-ID zero-solve rows | 245.7 / 245.9 | discard |
| trusted-name minimum length 6 / recurrence in 3 contests | 243.9 / 243.9 | sub-noise |
| disable trusted names / scope names by affiliation / scope roster pairs by affiliation | 246.7 / 243.6 / 244.1 | no improvement; discard |

Thus none of the discarded rows becomes a justified new keep under the corrected
contract. The three historical keeps remain defensible as data-quality choices,
but their numeric gains are now smaller than the campaign's noise threshold;
the WF change is retained because it fixes an over-broad identity join, not
because this scalar metric moves.

Rows for the time-causal participant prior, refreshed live-QOJ replay rows, and
the additional camp/XCPCIO collections were not rerun individually: the prior
experiment patch is not part of the shipped code, the refreshed replay snapshot
is not present, and those candidate collection files are not tracked in this
checkout. Their TSV values remain historical results, not post-fix measurements.

The gym-merge experiment could not be rerun from this checkout because its
loader requires the missing, gitignored
`data/gym_checkpoints/api_standings.json`; the tracked gym difficulty artifact
does not contain the raw standings needed to reconstruct fixed-ability gym
observations. Its historical negative result is therefore retained as
pre-fix evidence, not relabeled as a post-fix measurement. The unrelated
Codeforces pairwise-tuning experiments do not consume `solve_mask` and were not
rerun.

## Supplemental-contest influence audit (2026-08-09)

`arch_b.data_influence` now explains the corrected effect instead of reporting
only the scalar ablation. Tagged-only calibrated LOCO is 245.253; older ICPC
alone is worse at 245.887, Petroz alone improves to 244.285, and the shipped
combination is 244.188. The same direction holds under a custom equal-contest
LOCO (249.592 → 248.560), and all ordinary guards pass, but the total 1.065-CF
gain remains well below the 5-point keep threshold.

A strict no-link control assigns every standing row its own theta and disables
UCup prior transfer, preserving all within-contest cells but sharing no ability
between contests. Calibrated LOCO degrades **244.188 → 333.469** and raw LOCO
degrades **245.192 → 330.307**, failing the raw guard. Solve-count sanity remains
+0.995 because within-contest ordering survives; what is lost is the absolute
cross-contest scale. Linking is therefore structurally essential even though
the marginal value of an arbitrary new link is not monotonic.

The causal decomposition shows that supplemental identity unions without solve
evidence move only −0.069 CF. Keeping only supplemental rows whose identities
already occur in tagged retains −0.827 of the −1.065 gain; the remaining −0.238
comes from unlinked opponents calibrating the new contests' problem scales.
Petroz supplies 4,736 linked rows and 2,976 UCup-team appearances, versus older
ICPC's 1,100 and 201. Its direct CF-anchor overlaps are overwhelmingly Northern
Eurasian (3,411, vs 307 Europe and 296 Asia Pacific), matching the observed
regional change: Northern Eurasia LOCO improves 220.13 → 214.28 while Asia
Pacific slightly regresses 208.99 → 209.73 and Europe is flat 332.48 → 332.54.
Seven of the 15 CF contests improve and eight regress.

A mutation control removed the five highest-link supplemental contests whose
individual deletion happened to improve LOCO. The post-selected metric reaches
243.646, but a fixed 117,634-cell original-`tagged.json` holdout rejects it:
tagged-only / all-supplemental / mutation log-loss is 0.229876 / 0.230252 /
0.230105, and AUC is 0.967638 / 0.967626 / 0.967593. The mutation is therefore
an example of selection overfit, not a shipped change. The full rationale and
per-contest artifact are in `data_influence.md` and
`output/data_influence.json`; run `./.venv/bin/python -m arch_b.data_influence`.
