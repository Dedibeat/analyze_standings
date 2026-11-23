# CSES Introductory teaching selection (2026-11-09)

**Request.** Continue the clean/tricky greedy, DP, or DC teaching selection
using CSES Introductory Problems, retaining the general-audience requirement.
Read the current official category list and candidate statements, including
newer introductory tasks Grid Coloring I and String Reorder.

**Artifact.** `cses_intro_teaching.md` recommends Increasing Array for a first
greedy proof, Grid Coloring I for the four-choices/three-forbidden argument,
Two Sets for a residual-sum invariant, String Reorder for lexical greed with
an exact continuation-feasibility condition, Tower of Hanoi for recursive
construction plus optimality, and Gray Code for reflected recursion. Apple
Division provides a verified counterexample to balancing greedily and a short
exhaustive-search proof. Full proofs, traps, teaching prompts and complexities
are included. Hanoi's lower bound does not assume the largest disk moves once.
String Reorder includes the boundary condition imposed by the preceding letter.

**Technique limits.** If DC means divide and conquer, Hanoi and Gray Code
illustrate recursive construction rather than balanced independent halves.
Apple Division's large weights make a total-weight-indexed DP inappropriate;
ordinary exhaustive search is not mislabeled as efficient DP. A first DP lesson
should use the separate DP category if the section restriction is relaxed.

**Verification.** `python3 scripts/check_cses_teaching.py` passes 363 Increasing
Array inputs, 4,372 original grids, 100 Two Sets sizes checked with independent
reachable-sum DP, all 219 three-letter count vectors with total length 1–9
against enumerated lexical minima, Hanoi sizes 1–7 against BFS shortest paths,
Gray Code lengths 1–10, and the Apple Division counterexample. Mathematical
proofs cover full constraints; finite checks are supporting evidence. No CSES
submission, production model, rating, or dataset changed.
