# Techniques in EC regionals: 2026 forecast, tested on CCPC (2026-10-10)

**Question.** Which techniques appear in ICPC Asia East regionals, and which
are likely in the 2026 regionals? Test the forecast on CCPC contests too.
Script `scripts/technique_forecast.py`; report `output/technique_forecast.md`
(numbers in `.json`); tests `tests/test_technique_forecast.py` (8 pass).

**Data.**
- Named techniques come from `../llm-integration` (Gemini extraction, 128-id
  taxonomy in `techniques_taxonomy.md`). They were taken from the Technique
  Atlas page `../my-react-app/data/techniques_viewer.html`; the source
  `tagged_gemini.json` is no longer on disk. `--snapshot` copies ids, tiers,
  categories and confidences, without evidence text, into
  `data/techniques_atlas.json` (3,023 problems, with the page's sha256).
- A technique *appears* when it is a primary or secondary tag. Freeform
  `named_extras` are not counted.
- 27 regionals 2022–2025 (346 problems). Each QOJ id was checked on QOJ's
  category pages (Cloudflare blocks scripts, so the built-in browser was used).
- 8 CCPC contests (104 problems):
  - 10th CCPC (2024 season): Harbin 1817, Jinan 1843, Zhengzhou 1873, and the
    final 2036 (the UCup "Guangzhou" stage, held May 2025).
  - 11th CCPC (2025): Zhengzhou 2661, Jinan 2693, Chongqing 3387, and the
    final 3727 (Nanyang, April 2026).
- **Missing.** 2024 Chongqing (QOJ 1840) and 2025 Harbin (2575, 1 problem)
  are not in the atlas. No 2022–2023 CCPC is either (QOJ 1833, 1493, 1303,
  1480, 1244, 1412, 1404, 1540, 1411, 1596). The 2026 EC online rounds
  (4071, 4113) have no statements or tags.
- Difficulty is `difficulty_cf` from `output/problem_ratings_calibrated.json`.
  *Position* is a problem's rank by difficulty inside its contest
  (1 = easiest).

**The tags have no general categories (graph, dp, ...).**
- The extractor leaves out ambient basics: generic dp and greedy, sorting,
  plain binary search, modular arithmetic. So 56% of regional problems carry
  no named technique.
- UCup, Petrozavodsk and CCPC problems have only named tags. The DeepSeek
  general tags (`primary_tags`) exist for the ICPC contests only.
- General categories are therefore *derived* from each named technique's
  taxonomy category, the same way for ICPC and CCPC. Against DeepSeek on ICPC
  regionals:

  | derived category | recall | precision |
  |---|---|---|
  | graph | .38 | .90 |
  | dp | .15 | .53 |
  | data-structures | .58 | .61 |
  | math | .16 | .81 |
  | string | .48 | .82 |
  | geometry | .48 | .71 |

- So general dp / greedy / math / constructive are reported for ICPC only and
  not compared with CCPC.
- **Fix:** run the DeepSeek general tagger in `../llm-integration` on the 104
  CCPC problems. `DEEPSEEK_API_KEY` is not set here, so this was not done.

**Model.**
- P(technique *k* appears in a contest) is a recency-weighted presence rate,
  shrunk toward the mean rate of *k*'s taxonomy category:
  `p_k = (Σ w_c y_ck + α m_cat(k)) / (Σ w_c + α)`.
- Tuned on 2022–2023 → 2024: α = 16, decay = 1.0. Across decays the log loss
  stays within 0.2474–0.2512, so recency hardly matters.
- Then fitted on 2022–2024 and scored on every (contest, technique) cell of
  the 2025 regionals and of all 8 CCPC contests.

**Results.**

| test | log loss model | category-only | uniform | gain vs uniform (90% CI) | top-20 coverage (random) |
|---|---|---|---|---|---|
| ICPC 2025 (7) | .2169 | .2349 | .2368 | .0199 (.0095–.0305) | 39% (18%) |
| CCPC 2024–2025 (8) | .2356 | .2544 | .2574 | .0218 (.0184–.0250) | 42% (18%) |

- The ICPC-fitted forecast transfers to CCPC with the same gain. Calibration
  is close in every bin.
- 16–18% of named test problems use only techniques never seen in training.
- Adding CCPC 2024 to training does not help ICPC 2025 (.2169 → .2166). The
  2026 forecast is fitted on ICPC only.
- **No site effect.** Shrinking toward a site's own past regionals is worse
  in 7 of 8 (season, β) cases. The one win is β = 16 in 2025, by .001. One
  profile serves every site.
- **No trend survives Holm** over 26 tags. The smallest raw p are general
  constructive (+0.34 per season, p = .08) and game theory (p = .08).
- **ICPC vs CCPC** (2024–2025, problems per contest): no difference survives
  Holm. Raw p: CCPC has more dp (1.12 vs 0.43, p = .09) and string (1.00 vs
  0.50, p = .06); ICPC has more graph (1.79 vs 1.00, p = .09).
- **By position:**
  - Positions 1–3 (median CF 1671) need a named technique in only 10% of
    regionals (CCPC 12%). They are math, greedy, constructive and
    implementation.
  - The share rises to 36%, 59% and 64% for positions 4–6, 7–9 and 10+
    (CCPC: 33%, 71%, 69%).
- **2026 forecast, P per regional (P in any of 8 sites):** dsu 25% (89%),
  fenwick 25%, fft 23%, convex hull 21%, rolling hash 21%, lazy segment tree
  20%, sqrt decomposition 20%, sweep line 19%, segment tree 18%, max flow 16%.
  The 45 techniques never seen in a regional get 0.9–3.6% each.

**Data-label issues found (not changed).**
- `data/tagged.json` names QOJ 1522 "Shanghai 2023"; it is EC-Final 2023
  (`build_xcpcio_official.py` has it right).
- QOJ 1913 "Metropolis" is the 2024 Shanghai regional.
- The ucup_s3 stage QOJ 1807 "Qinhuangdao" is the 2017 CCPC Qinhuangdao set,
  so it is not used as CCPC.

**TabFM (asked).** It is not installed on this Windows machine: no torch, no
`tabfm` package, no checkpoint, and no WSL distribution. The verified local
runtime (TabFM 1.0.1, pinned checkpoint) was under `/home/dedibeat`. The
hardware would do: 32 GB RAM, 28 threads, RTX 4070 12 GB; the earlier CPU
smoke run used 12.6 GiB.

Setting it up means downloading the source, torch and the v1 weights, whose
license is non-commercial and non-production. The earlier checkpoint held the
regression model; this task needs the classifier.

TabFM is not expected to help here:
- The table is one row per (contest, technique), about 1.8k training rows
  with about 8% positives.
- The only signal is each technique's past rate and its category. That is
  what the shrinkage formula estimates.
- Site, trend and recency effects all tested null, so there is no interaction
  to learn. On the gold table, TabFM's gain came from the online × history
  interaction.
- A 7-contest test cannot separate two good models: the model's own gain over
  uniform has a CI of ±0.01.

Not run.

Run: `python scripts/technique_forecast.py`; refresh the snapshot with
`python scripts/technique_forecast.py --snapshot ../my-react-app/data/techniques_viewer.html`.
Tests: `python -m unittest tests.test_technique_forecast`.
