# Related published work (2026-10-06)

Literature search for a paper on this repository's main result: rating ICPC
problems from team standings alone, linking contests through recurring
teams, and calibrating to Codeforces points. Every entry below was looked up
in this search (title, authors, venue checked against the publisher, arXiv or
the PDF), except the three marked *not looked up*.

## Closest prior work

- **M. Forišek (2009). Using Item Response Theory to Rate (not only)
  Programmers.** *Olympiads in Informatics* 3, 3–16.
  [PDF](https://ioinformatics.org/journal/INFOL049.pdf)
  - An IRT rating system for programming contests whose rounds differ in
    difficulty. It rates tasks and contestants together and gives the
    precision of each skill estimate.
  - Data: 88 Slovak olympiad tasks and 560 TopCoder tasks (12,000+
    contestants). It also finds that solve times are roughly log-normal.
  - **Difference:** individuals on one platform, where the same people
    compete in every round. Here, ICPC teams change between seasons, so
    contests are linked through recurring teams and rosters. This work also
    adds a solve-time survival layer, Codeforces-point calibration and
    outside validation. This is the paper to cite first and compare against.
- **M. Forišek (2010). The Difficulty of Programming Contests Increases.**
  ISSEP 2010, LNCS 5941, Springer.
  [doi:10.1007/978-3-642-11376-5_8](https://doi.org/10.1007/978-3-642-11376-5_8)
  - Uses IRT on past contest results to show that task difficulty rose over
    the years.
- **G. Kemkes, T. Vasiga, G. Cormack (2006). Objective scoring for computing
  competition tasks.** ISSEP 2006 (*Information Technologies at School*).
  *Not looked up; taken from Forišek (2009)'s reference list.*
  - IRT analysis of IOI 2005 scoring.
- **M. Ding et al. (2024). Easy2Hard-Bench: Standardized Difficulty Labels
  for Profiling LLM Performance and Generalization.** NeurIPS 2024 Datasets
  and Benchmarks.
  [PDF](https://proceedings.neurips.cc/paper_files/paper/2024/file/4e6f22305275966513990f53cec908e0-Paper-Datasets_and_Benchmarks_Track.pdf)
  - Puts IRT/Glicko-2 difficulty scores on Codeforces problems (E2H-Codeforces)
    using the solvers' Codeforces ratings.
  - **Difference:** they start from native ratings. ICPC has none, which is
    the problem this repository solves.
- **Z. Luo, E. Dickey (2025). Evaluating Performance Consistency in
  Competitive Programming: Educational Implications and Contest Design
  Insights.** arXiv:2505.04143.
  [arXiv](https://arxiv.org/abs/2505.04143)
  - Ten years of ICPC standings. Superregional ranks predict World Finals
    ranks only moderately (τ = 0.407), while Codeforces ratings predict them
    better (τ = 0.596).
  - Supports using Codeforces as the outside scale. `external_data_sources.md`
    already lists the World Finals rosters it used.

## ICPC and online-judge data

- **R. H. de Boer, C. P. de Campos (2019). A retrospective overview of
  International Collegiate programming contest data.** *Data in Brief* 25,
  104382. [doi:10.1016/j.dib.2019.104382](https://doi.org/10.1016/j.dib.2019.104382)
  - Cleaned ICPC scoreboards from 2012–2018 (Europe, Latin America, North
    America, South Pacific, World Finals). No Asia regionals.
- **J. J. Blum (2023). Competitive programming participation rates: an
  examination of trends in U.S. ICPC regional contests.** *Discover
  Education* 2, 11.
  [doi:10.1007/s44217-023-00034-1](https://doi.org/10.1007/s44217-023-00034-1)
- **C. M. Intisar, Y. Watanobe (2018). Cluster Analysis to Estimate the
  Difficulty of Programming Problems.** ICAIT 2018, 23–28.
  [ResearchGate](https://www.researchgate.net/publication/329023483_Cluster_Analysis_to_Estimate_the_Difficulty_of_Programming_Problems)
  - Estimates difficulty from Aizu Online Judge submission logs. Relevant
    because `arch_b.aoj` uses AOJ as a validator.
- **Z. Wang, W. Zhang, J. Wang (2024). Estimating Difficulty Levels of
  Programming Problems with Pre-trained Model.** arXiv:2406.08828.
  [arXiv](https://arxiv.org/abs/2406.08828)
  - Predicts difficulty from the statement text and solution code, not from
    results.

## Rating systems

- **A. Ebtekar, P. Liu (2021). Elo-MMR: A Rating System for Massive
  Multiplayer Competitions.** WWW 2021.
  [doi:10.1145/3442381.3450091](https://doi.org/10.1145/3442381.3450091)
  - A Bayesian rating system for ranked contests with many players, tested on
    Codeforces and TopCoder. It rates contestants, not problems.
- **R. Pelánek (2016). Applications of the Elo rating system in adaptive
  educational systems.** *Computers & Education* 98, 169–179.
  [doi:10.1016/j.compedu.2016.03.017](https://doi.org/10.1016/j.compedu.2016.03.017)
  - Elo for item difficulty and student skill, and how it compares with IRT.
- **M. E. Glickman (1999). Parameter estimation in large dynamic paired
  comparison experiments.** *JRSS Series C* 48(3), 377–394.
  [OUP](https://academic.oup.com/jrsssc/article/48/3/377/6990661) (Glicko)
- **R. Herbrich, T. Minka, T. Graepel (2006). TrueSkill™: A Bayesian Skill
  Rating System.** NIPS 19.
  [NeurIPS](https://papers.nips.cc/paper/3079-trueskilltm-a-bayesian-skill-rating-system)
  - Infers each player's skill from team results.

## Measurement theory

- **W. J. van der Linden (2007). A Hierarchical Framework for Modeling Speed
  and Accuracy on Test Items.** *Psychometrika* 72, 287–308.
  [doi:10.1007/s11336-006-1478-z](https://doi.org/10.1007/s11336-006-1478-z)
  - Models responses and response times together. It is the standard
    reference for using time as well as correctness (here, `arch_b.survival`).
- **M. J. Kolen, R. L. Brennan (2014). Test Equating, Scaling, and Linking**,
  3rd ed. Springer.
  [doi:10.1007/978-1-4939-0317-7](https://doi.org/10.1007/978-1-4939-0317-7)
  - Linking separate tests through people who take more than one of them.
    This is the textbook name for linking contests through recurring teams.
- G. Rasch (1960), *Probabilistic Models for Some Intelligence and Attainment
  Tests*; R. A. Bradley, M. E. Terry (1952), *Biometrika* 39, 324–345.
  *Classic references; not looked up in this search.*

## LLMs and problem difficulty

- **M. Ballon, A. Algaba, B. Verbeken, V. Ginis (2025). Estimating problem
  difficulty without ground truth using Large Language Model comparisons.**
  arXiv:2512.14220. [arXiv](https://arxiv.org/abs/2512.14220)
  - Asks an LLM which of two problems is harder and fits Bradley–Terry
    scores to the answers. This repository's `llm_survival_plan.md` and
    `llm_crosscontest.py` build on it.
- **U. Bezirhan, M. von Davier (2026). Anchored Bradley-Terry Calibration
  Using LLM Comparative Judgments.** AIME-Con 2026, 365–371.
  [ACL Anthology](https://aclanthology.org/2026.aimecon-main.40/)
  - LLM judges compare new items with already-rated anchor items, and a
    fixed-anchor Bradley–Terry model turns that into difficulty. It is the
    same design as the anchored cross-contest comparisons here.
- **V. Yaneva et al. (2024). Findings from the First Shared Task on Automated
  Prediction of Difficulty and Response Time for Multiple-Choice Questions.**
  BEA 2024, 470–482. [ACL Anthology](https://aclanthology.org/2024.bea-1.39/)
- **W. Lugoloobi, C. Russell (2025). LLMs Encode How Difficult Problems
  Are.** arXiv:2510.18147. [arXiv](https://arxiv.org/abs/2510.18147)

## LLM coding benchmarks that need difficulty labels

These show why calibrated ICPC ratings are useful to others.

- **S. Quan et al. (2025). CodeElo: Benchmarking Competition-level Code
  Generation of LLMs with Human-comparable Elo Ratings.** arXiv:2501.01257.
  [arXiv](https://arxiv.org/abs/2501.01257)
- **Z. Zheng et al. (2025). LiveCodeBench Pro: How Do Olympiad Medalists
  Judge LLMs in Competitive Programming?** NeurIPS 2025 Datasets and
  Benchmarks. [arXiv](https://arxiv.org/abs/2506.11928)
  - Includes ICPC problems and reports results by difficulty tier.
- **S. Zheng et al. (2026). When Elo Lies: Hidden Biases in
  Codeforces-Based Evaluation of Large Language Models.** arXiv:2602.05891.
  [arXiv](https://arxiv.org/abs/2602.05891)
- **Y. Huang et al. (2024). Competition-Level Problems are Effective LLM
  Evaluators.** ACL 2024. [arXiv](https://arxiv.org/abs/2312.02143)

## Web tools to mention (not papers)

- clist.by problem ratings, which invert Codeforces/AtCoder ratings; cited
  in `strat.tex`.
- Codeforces' own problem ratings.

## What this search did not find

No published paper found here rates **ICPC problems from team standings**
by linking 200+ contests through recurring teams and then calibrating the
scale to **Codeforces points** with outside validation. This is a claim
about this search only. Before writing "first", check Google Scholar,
Semantic Scholar and the *Olympiads in Informatics* index.
