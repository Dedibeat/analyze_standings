# Teaching material: overview

> Moved verbatim from `README.md` on 2026-11-20. Text may predate later changes; [docs/STATUS.md](../STATUS.md) is authoritative for what ships now.

## Teaching material

[Recent Codeforces Div. 2 A/B teaching notes](cf_div2_teaching.md) select five
problems for a general audience, with complete proofs, teaching prompts,
common traps, and a reproducible small-case checker. The bounded search covers
the latest 20 finished Div. 2 / Educational / combined rounds as of 2026-11-09.
Start with SauSaGe Bank for greedy and Prefix for DP; no divide-and-conquer
recommendation was found in this sample.

[CSES Introductory teaching notes](cses_intro_teaching.md) continue the same
selection for a general audience: Increasing Array, Grid Coloring I, Two Sets,
String Reorder, Tower of Hanoi, and Gray Code, plus Apple Division as a contrast
to greedy. Complete proofs distinguish recursive construction from balanced
divide and conquer and explain the lack of a strong first DP lesson within
this section. Run `python3 scripts/check_cses_teaching.py` for small-case checks.
