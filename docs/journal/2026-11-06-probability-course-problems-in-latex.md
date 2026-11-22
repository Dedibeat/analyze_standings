# Probability-course problems in LaTeX (2026-11-06, second entry)

[prob_course_problems.tex](../teaching/prob_course_problems.tex) writes up all nine picks
from the shortlist above (main five, then the four backups). Each section has
a source line (contest, QOJ link, topics), a clean problem statement with
parts (a), (b), ..., and a full solution. The statements were rewritten from
the original statements in `data/tagged.json`.

Changes from the shortlist's paper versions:
- **Every part has a worked derivation,** not just an answer. For example,
  502 Bad Gateway proves that a threshold policy is optimal; Uniform Chemistry
  proves that the visit indicators are independent by computing their joint
  law; Jinx or Jackpot proves by induction that the value is linear in the
  balance.
- **Accidental Arithmetic (b)** solves the β ≠ γ case:
  E[V] = (1−μ)E[F] + μE[S] with μ = (β−γ)/(β+γ), where F is the first term
  and S the sum of all terms with plus signs. The shortlist said the later
  terms come back "with weight (β−γ)"; that was wrong, and the shortlist now
  says (β−γ)/(β+γ).
- **Orchard Fence** states the general hull-edge formula as part (a) and adds
  the hexagon with k=4, (16+6√3)/5. With k=3 the formula is not needed: a
  triangle's perimeter is the sum of its sides.
- **Chopsticks** gets E[(−1)^X] for the hypergeometric count from
  [z^{2n}](1−z)^k(1+z)^{s−k}; for 8+8 chopsticks this is [z^10](1−z²)^8,
  giving 72/143 by hand.
- **Dropped:** the Mingle variance follow-up. It needs the joint law of pairs
  of rooms at every distance, and the result is a long sum over distances,
  too heavy for a course problem.

Checks: a scratch script (not kept) verified every formula and number by
exact enumeration with fractions, and checked each model against the original
problem's official samples. Every sample matched, including Uniform Chemistry
sample 4 (n=100) and Jinx or Jackpot sample 2 (k=30). The one exception is
Orchard Fence sample 2, which was not checked: its points are collinear, and
the paper version assumes general position. The document
compiles with `pdflatex` (TeX Live 2023) with no warnings. A minimal TeX
install also needs `cm-super`, because `\$` uses a TS1 font at 11pt. The
compiled `prob_course_problems.pdf` is committed next to the source (on
request; `strat.tex` has no committed PDF). No code or output changed.
