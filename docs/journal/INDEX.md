# Journal index

One line per entry, oldest first: `date · area · title — outcome` → file. Entries are
append-only history; [docs/STATUS.md](../STATUS.md) says what is current. Search with
`grep -i <keyword> docs/journal/INDEX.md` or `grep -ril <keyword> docs/journal/`.

Areas: rating, validation, calibration, data, medals, forecast, hong-kong, ec-final,
team-r3, ccpc, llm, viewer-app, teaching, codeforces, meta.

Entries before 2026-11-20 were split verbatim from the old `details.md`; the dates of
undated Architecture B sections come from the commit that first added them. Their paths
to other files may name the old root locations (reports keep their filenames under `docs/`).

- 2026-06-20 · rating · [2PL per-problem discrimination, by region (`arch_b.twopl` / `arch_b.twopl_region`)](2026-06-20-2pl-per-problem-discrimination-by-region-arch-b-twopl-arch.md) — NEGATIVE: 2PL overfits; Rasch stays
- 2026-06-20 · validation · [External validation vs Codeforces ratings (`arch_b.external_validate --contest 2206`)](2026-06-20-external-validation-vs-codeforces-ratings-arch-b-external.md)
- 2026-06-20 · validation · [External validation vs the LLM difficulty (`arch_b.validate`)](2026-06-20-external-validation-vs-the-llm-difficulty-arch-b-validate.md)
- 2026-06-20 · validation · [Internal validation: held-out solve prediction (`arch_b.predict_eval`)](2026-06-20-internal-validation-held-out-solve-prediction-arch-b.md)
- 2026-06-20 · validation · [Per-region external validation (`arch_b.external_validate`)](2026-06-20-per-region-external-validation-arch-b-external-validate.md)
- 2026-06-20 · calibration · [Scale calibration to Codeforces points (`arch_b.calibrate`)](2026-06-20-scale-calibration-to-codeforces-points-arch-b-calibrate.md)
- 2026-06-20 · rating · [Season-separated identity + short-contest filter (`arch_b.season_experiment`)](2026-06-20-season-separated-identity-short-contest-filter-arch-b.md)
- 2026-07-03 · rating · [Auto-research campaign on the metric: verdict PLATEAU](2026-07-03-auto-research-campaign-on-the-metric-verdict-plateau.md) — PLATEAU
- 2026-07-03 · validation · [Gym-mirror fixed-θ difficulty (`arch_b.gym_difficulty`)](2026-07-03-gym-mirror-fixed-difficulty-arch-b-gym-difficulty.md)
- 2026-07-03 · rating · [Second auto-research campaign (2026-07-03, DeepSeek v4 Pro): verdict PLATEAU](2026-07-03-second-auto-research-campaign-verdict-plateau.md) — PLATEAU
- 2026-07-04 · rating · [Contest-link weighting experiment: NEGATIVE](2026-07-04-contest-link-weighting-experiment-negative.md) — NEGATIVE
- 2026-07-04 · rating · [Gym-merge experiment: gym attempts as fit observations — NEGATIVE](2026-07-04-gym-merge-experiment-gym-attempts-as-fit-observations.md) — NEGATIVE
- 2026-07-05 · medals · [East-Asia medal badges + lowest-gold analysis (`arch_b.medals`)](2026-07-05-east-asia-medal-badges-lowest-gold-analysis-arch-b-medals.md)
- 2026-07-05 · validation · [Official-field validation of fitted difficulties](2026-07-05-official-field-validation-of-fitted-difficulties.md)
- 2026-07-05 · data · [XCPCIO ← QOJ matching](2026-07-05-xcpcio-qoj-matching.md)
- 2026-07-21 · data · [External data-source audit](2026-07-21-external-data-source-audit.md)
- 2026-07-21 · data · [Participant Codeforces ratings: feasibility study](2026-07-21-participant-codeforces-ratings-feasibility-study.md)
- 2026-07-23 · data · [Data-side auto-research campaign: 261.6 LOCO](2026-07-23-data-side-auto-research-campaign-261-6-loco.md) — data campaign; broader datasets discarded
- 2026-07-27 · medals · [Regional medal-cutoff chooser (`arch_b.medal_predict`)](2026-07-27-regional-medal-cutoff-chooser-arch-b-medal-predict.md)
- 2026-08-05 · llm · [Codeforces pairwise Gemini pilot](2026-08-05-codeforces-pairwise-gemini-pilot.md)
- 2026-08-07 · llm · [Planned zero-shot LLM × survival integration](2026-08-07-planned-zero-shot-llm-survival-integration.md)
- 2026-08-18 · viewer-app · [Virtual contest performance calculator](2026-08-18-virtual-contest-performance-calculator.md)
- 2026-08-21 · rating · [Anchoring audit: UCup anchor, gym shape, CF affine, LLM comparisons](2026-08-21-anchoring-audit-ucup-anchor-gym-shape-cf-affine-llm.md)
- 2026-08-21 · llm · [Gemini 3.6 Flash vs 3.5 Flash: 200/300-point gap check](2026-08-21-gemini-3-6-flash-vs-3-5-flash-200-300-point-gap-check.md)
- 2026-08-21 · rating · [Implementing the structural shift](2026-08-21-implementing-the-structural-shift.md)
- 2026-09-05 · meta · [Experiment and implementation review](2026-09-05-experiment-and-implementation-review.md) — invalidates the cross-contest LLM LOCO gain
- 2026-09-06 · rating · [Fit and rating improvement strategy](2026-09-06-fit-and-rating-improvement-strategy.md)
- 2026-09-06 · meta · [Review implementation resolution](2026-09-06-review-implementation-resolution.md)
- 2026-09-17 · llm · [Jev feasibility review (no API run)](2026-09-17-jev-feasibility-review.md)
- 2026-09-27 · forecast · [Online results, slot rules and regional gold chances](2026-09-27-online-results-slot-rules-and-regional-gold-chances.md)
- 2026-09-27 · forecast · [Quota entrants: who entered each regional on a quota seat, and why](2026-09-27-quota-entrants-who-entered-each-regional-on-a-quota-seat.md)
- 2026-09-27 · forecast · [School-rank quota predictor and a TabFM gold table](2026-09-27-school-rank-quota-predictor-and-a-tabfm-gold-table.md)
- 2026-09-28 · calibration · [DE release audit on the roster-fixed fit](2026-09-28-de-release-audit-on-the-roster-fixed-fit.md)
- 2026-09-28 · calibration · [DE release](2026-09-28-de-release.md) — SHIPPED, SUPERSEDED 2026-11-16 by hier_time
- 2026-09-28 · forecast · [Forecast experiments redone with the 2025–2026 rosters](2026-09-28-forecast-experiments-redone-with-the-2025-2026-rosters.md)
- 2026-09-28 · data · [PTA registration lists for 2025–2026 (2026-09-28, review)](2026-09-28-pta-registration-lists-for-2025-2026.md)
- 2026-09-28 · rating · [Rosters as rating-fit identity links (2026-09-28, experiment, not shipped)](2026-09-28-rosters-as-rating-fit-identity-links.md) — NOT SHIPPED
- 2026-10-01 · ec-final · [EC-Final regional cutoff: how deep a mainland seat reaches](2026-10-01-ec-final-regional-cutoff-how-deep-a-mainland-seat-reaches.md)
- 2026-10-01 · meta · [Hand-off for a cloud session](2026-10-01-hand-off-for-a-cloud-session.md) — hand-off
- 2026-10-01 · hong-kong · [Hong Kong field and gold chances](2026-10-01-hong-kong-field-and-gold-chances.md)
- 2026-10-01 · hong-kong · [Hong Kong / Macau teams linked to online results](2026-10-01-hong-kong-macau-teams-linked-to-online-results.md)
- 2026-10-01 · forecast · [Silver and bronze chances](2026-10-01-silver-and-bronze-chances.md)
- 2026-10-04 · data · [2026 EC online rounds added; "ICPC" contest names fixed](2026-10-04-2026-ec-online-rounds-added-icpc-contest-names-fixed.md)
- 2026-10-04 · viewer-app · [Calibrated team performance; medal viewer in the app](2026-10-04-calibrated-team-performance-medal-viewer-in-the-app.md)
- 2026-10-04 · rating · [Time-varying team ratings (2026-10-04, research)](2026-10-04-time-varying-team-ratings.md)
- 2026-10-05 · medals · [Medal cutoffs disagreed with the real boards (diagnosis and fix, 2026-10-05)](2026-10-05-medal-cutoffs-disagreed-with-the-real-boards.md)
- 2026-10-05 · data · [Which contests are mostly EC-regional teams?](2026-10-05-which-contests-are-mostly-ec-regional-teams.md)
- 2026-10-07 · ec-final · [NUM-R^3: chance of an EC-Final seat from each 2026 regional](2026-10-07-num-r3-chance-of-an-ec-final-seat-from-each-2026-regional.md)
- 2026-10-08 · ec-final · [EC-Final chance: members' history, site spread, two-regional plans](2026-10-08-ec-final-chance-members-history-site-spread-two-regional.md)
- 2026-10-08 · ec-final · [Past-season EC-Final chance from virtual online results](2026-10-08-past-season-ec-final-chance-from-virtual-online-results.md)
- 2026-10-10 · forecast · [Hidden cycles and patterns in regional techniques](2026-10-10-hidden-cycles-and-patterns-in-regional-techniques.md)
- 2026-10-10 · forecast · [Techniques in EC regionals: 2026 forecast, tested on CCPC](2026-10-10-techniques-in-ec-regionals-2026-forecast-tested-on-ccpc.md)
- 2026-10-11 · forecast · [Anchor teams for non-regional contests](2026-10-11-anchor-teams-for-non-regional-contests.md)
- 2026-10-12 · ccpc · [CCPC findings vs the 2026 forecast and the ratings (2026-10-12, third entry)](2026-10-12-ccpc-findings-vs-the-2026-forecast-and-the-ratings.md)
- 2026-10-12 · ccpc · [CCPC medal vs ICPC EC regional medal](2026-10-12-ccpc-medal-vs-icpc-ec-regional-medal.md)
- 2026-10-12 · ccpc · [ICPC regionals vs CCPC stations: medal difficulty and problem quality](2026-10-12-icpc-regionals-vs-ccpc-stations-medal-difficulty-and.md)
- 2026-10-13 · rating · [Fixing the bar misses; performance inflation and deflation](2026-10-13-fixing-the-bar-misses-performance-inflation-and-deflation.md)
- 2026-10-13 · rating · [Root cause of the performance inflation and deflation (2026-10-13, second entry)](2026-10-13-root-cause-of-the-performance-inflation-and-deflation.md)
- 2026-10-15 · hong-kong · [2026 Hong Kong registration list: the early field](2026-10-15-2026-hong-kong-registration-list-the-early-field.md)
- 2026-10-18 · ccpc · [CCPC sets ranked by problem difficulty](2026-10-18-ccpc-sets-ranked-by-problem-difficulty.md)
- 2026-10-26 · team-r3 · [Xi'an 2026 virtual: rank 86](2026-10-26-xi-an-2026-virtual-rank-86.md) — NUM-R^3 virtual
- 2026-10-28 · hong-kong · [Hong Kong registration: 10-28 export](2026-10-28-hong-kong-registration-10-28-export.md)
- 2026-11-04 · team-r3 · [NUM-R^3 coach review: dossiers, bug classes, strategy (2026-11-04, second entry)](2026-11-04-num-r3-coach-review-dossiers-bug-classes-strategy.md)
- 2026-11-04 · team-r3 · [NUM-R^3 participations: team-account data download](2026-11-04-num-r3-participations-team-account-data-download.md)
- 2026-11-04 · rating · [Rating rethink reviewed; experiments 0–2 run (2026-11-04, second entry)](2026-11-04-rating-rethink-reviewed-experiments-0-2-run.md)
- 2026-11-04 · rating · [Rethinking performance and problem ratings](2026-11-04-rethinking-performance-and-problem-ratings.md)
- 2026-11-05 · rating · [DE successor candidates and stability experiment PC handoff](2026-11-05-de-successor-candidates-and-stability-experiment-pc-handoff.md)
- 2026-11-05 · rating · [Hierarchical binary ratings: a DE rival (2026-11-05, third entry)](2026-11-05-hierarchical-binary-ratings-a-de-rival.md)
- 2026-11-05 · team-r3 · [NUM-R^3 members on Codeforces](2026-11-05-num-r3-members-on-codeforces.md)
- 2026-11-05 · team-r3 · [NUM-R^3 on Codeforces: correction, round-by-round review (2026-11-05, second entry)](2026-11-05-num-r3-on-codeforces-correction-round-by-round-review.md)
- 2026-11-05 · rating · [Problem ratings checked by hand (2026-11-05, fourth entry)](2026-11-05-problem-ratings-checked-by-hand.md)
- 2026-11-05 · forecast · [Rating rethink, experiment 3: recorded-date member priors](2026-11-05-rating-rethink-experiment-3-recorded-date-member-priors.md)
- 2026-11-05 · rating · [Stability-penalized DE: run on the PC, no penalty gain (2026-11-05, second entry)](2026-11-05-stability-penalized-de-run-on-the-pc-no-penalty-gain.md) — NEGATIVE: penalty adds nothing
- 2026-11-06 · teaching · [Probability-course problems cut to one trick each (2026-11-06, third entry)](2026-11-06-probability-course-problems-cut-to-one-trick-each.md)
- 2026-11-06 · teaching · [Probability-course problems in LaTeX (2026-11-06, second entry)](2026-11-06-probability-course-problems-in-latex.md)
- 2026-11-06 · teaching · [Probability-course shortlist](2026-11-06-probability-course-shortlist.md)
- 2026-11-08 · rating · [Skipped cells as missing data: tested](2026-11-08-skipped-cells-as-missing-data-tested.md)
- 2026-11-09 · teaching · [CSES Introductory teaching selection](2026-11-09-cses-introductory-teaching-selection.md)
- 2026-11-09 · rating · [Rating debugging by hand, second pass: 2524 D, strong floors, tiny boards](2026-11-09-rating-debugging-by-hand-second-pass-2524-d-strong-floors.md)
- 2026-11-09 · teaching · [Recent Codeforces A/B teaching selection](2026-11-09-recent-codeforces-a-b-teaching-selection.md)
- 2026-11-09 · rating · [Shipped ratings flag small boards (2026-11-09, second entry)](2026-11-09-shipped-ratings-flag-small-boards.md) — SHIPPED
- 2026-11-10 · rating · [Stable DE, continued: six ideas tested, a loader bug found](2026-11-10-stable-de-continued-six-ideas-tested-a-loader-bug-found.md) — found the loader bug fixed 2026-11-16
- 2026-11-15 · data · [CCPC boards collected for experiments (2026-11-15, second entry)](2026-11-15-ccpc-boards-collected-for-experiments.md)
- 2026-11-15 · data · [Latest standings and new contests pulled; 2026 regionals in the fit](2026-11-15-latest-standings-and-new-contests-pulled-2026-regionals-in.md)
- 2026-11-16 · rating · [Hierarchical fit: loader bugs fixed, solve time added, release candidate](2026-11-16-hierarchical-fit-loader-bugs-fixed-solve-time-added-release.md) — release candidate (shipped next entry)
- 2026-11-16 · meta · [Public release, human feedback and a paper: research (2026-11-16, third entry)](2026-11-16-public-release-human-feedback-and-a-paper-research.md)
- 2026-11-16 · rating · [Ship hierarchical binary with time to all rating products](2026-11-16-ship-hierarchical-binary-with-time-to-all-rating-products.md) — SHIPPED: current production model
- 2026-11-18 · codeforces · [Codeforces blog topic shortlist](2026-11-18-codeforces-blog-topic-shortlist.md) — also holds the 2026-11-18/19 CF standings-experiment summaries
- 2026-11-18 · codeforces · [Codeforces rating deflation and AI use](2026-11-18-codeforces-rating-deflation-and-ai-use.md)
- 2026-11-19 · meta · [README snapshot before the reorganization (findings summary + old layout)](2026-11-19-readme-snapshot-before-reorganization.md) — partly stale: still calls DE shipped
- 2026-11-20 · meta · [Repository reorganized for agent navigation](2026-11-20-repository-reorganized-for-agent-navigation.md) — docs only; details.md split into this journal
- 2026-11-20 · meta · [requirements.txt, WF files removed, cache inventory](2026-11-20-requirements-txt-wf-files-removed-cache-inventory.md) — raw+paid caches ≈0.5 GB; derived ≈9.5 GB
- 2026-11-20 · data · [Expensive caches committed to git](2026-11-20-expensive-caches-committed-to-git.md) — ~490 MB raw/paid caches tracked; derived and cookies stay ignored
