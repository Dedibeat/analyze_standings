# Probability-course problems cut to one trick each (2026-11-06, third entry)

The first LaTeX version asked too much of students: several problems stacked
3–4 parts, each needing a different idea (Uniform Chemistry had an
independence proof, a variance, a Stirling generating function and a race;
502 Bad Gateway had an optimality proof and asymptotics; Chopsticks and
Crashing Competition Computer each needed a second trick). On request,
[prob_course_problems.tex](../teaching/prob_course_problems.tex) now asks **one question
per problem, resting on one key idea**. Each solution opens with a "Key idea"
line. The dropped parts became a remark after the solution, for discussion
only. The PDF went from 10 to 7 pages.

| Problem | The one question | Key idea | Answer |
|---|---|---|---|
| Mingle | E[winners], general n, k | count rooms, not players | n(2k/(2k+1))^{2k} |
| Accidental Arithmetic | E[value], ± equally likely; N=12345, α=0.45 | later terms cancel by symmetry | 5.4321 |
| 502 Bad Gateway | E[time] for threshold c; best c for T=10 | resets are geometric | T/c+(c−1)/2; 4 |
| Uniform Chemistry | E[steps] | first jump into {j..n} is uniform | H_{n−a} |
| Jinx or Jackpot | best strategy, p∈{0.7,0.3}, 2 rounds | result is linear in the bet | $160 |
| Orchard Fence | E[perimeter], regular n-gon; n=6, k=4 | sum over chords | (16+6√3)/5 |
| Chopsticks | 4+4+4 chopsticks, draw 6 | mixed pairs = (odd colours)/2 | 8/11 |
| Crashing Computer | c=3, p=½, r=2, t=5 | restart recursion for a block | 26 |
| Quarantine | 3×3 grid, days 4/2/1 | linearity over seats, complements | 13263/512 |

Other changes:
- **Easier versions.** 502 Bad Gateway now fixes the threshold rule in the
  statement; that thresholds are optimal moved to the remark. Jinx or Jackpot
  is just the two-round case, solved directly without the induction. Uniform
  Chemistry asks only for E[T]. Its solution proves Pr(visit j) = 1/(n−j+1)
  by comparing, for each start x < j, landing on j with landing in {j..n}.
- **Hints** on the three problems whose idea is hardest to spot: Uniform
  Chemistry, Jinx or Jackpot and Orchard Fence.
- **New instances.** Chopsticks uses 4 red, 4 blue and 4 green with 6 drawn,
  because with two colours the parity trick is invisible: M is just the
  indicator that the red count is odd. The 8+8 case (72/143) is in the remark.
  Orchard Fence uses a regular n-gon, so "consecutive kept vertices" replaces
  the general-position "points to the left" count. With the hexagon and k=3 a
  student would just add triangle sides.

Checks: the two new instances were verified by exact brute force in a scratch
script (not kept). Chopsticks 4+4+4 gives 8/11. The n-gon formula matches
enumeration for every 3 ≤ k ≤ n ≤ 9. All other numbers are unchanged from the
second entry. The document compiles with no warnings, and the PDF was
rebuilt. The multi-part version is in commits 08188b2 (tex) and d670beb
(PDF).
