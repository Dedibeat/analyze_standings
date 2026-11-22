# 2PL per-problem discrimination, by region (`arch_b.twopl` / `arch_b.twopl_region`)

Motivated by the observation that in some regions the solve rate almost *determines*
difficulty (e.g. the large **Asia East Continent** online qualifiers) while others
(**Asia Pacific** / Japan) show much more spread at the same solve rate. That is the
signature of per-problem **discrimination** `a_p` (strat eq. twopl) — the one thing
the shipped 1-parameter Rasch fit cannot represent (it fixes every logistic slope at
`1/s`). So 2PL was prototyped to ask: does discrimination vary by region, and is it
worth modelling?

- **Model / fitter (`twopl.py`).** Keep `theta`, `b` on the ELO scale and add a
  dimensionless multiplier `alpha_p` (Rasch ≡ `alpha_p=1`):
  `pi = sigma(alpha_p·(theta−b)/s)`. Fit `g_p = log alpha_p` with a Gaussian prior
  `g_p ~ N(0, sigma_g^2)` that both regularizes sparse problems back to Rasch *and*
  (with the existing `theta` prior) fixes the 2PL scale indeterminacy
  (`theta→c·theta, b→c·b, alpha→alpha/c`). Same block-coordinate Newton as
  `model.py` with a third block: `theta`/`b` blocks are unchanged in form (they enter
  `eta` linearly), the `g` block uses **Fisher scoring** (expected information, since
  its observed Hessian can be indefinite). The joint objective is **non-convex** (the
  `alpha·theta` interaction), so it **warm-starts from a Rasch basin** (`alpha=1` for
  the first `warmup` iters). Converges in ~65 iters / ~6 s.

- **Finding 1 — discrimination does track region, in-sample.** UCup-anchored
  (`sigma_g=0.5`), median `alpha` by region: **Asia East Continent 2.14**, Europe
  1.98, Northern Eurasia 1.91, Asia Pacific 1.68, **North America 1.35**. EA's huge
  homogeneous fields produce the sharpest-discriminating problems; tiny-field NA
  (median field 16) the dullest. So the observation is *representable*. **Caveat: this
  is confounded with field size** (EA median field 198 vs NA 16) — a large field makes
  the logistic transition look sharp, so per-region `alpha` is partly a field-size
  artifact, not a pure intrinsic-problem property. (And the within-region
  `b ~ logit(solve_rate)` residual SD did **not** cleanly fall as `alpha` rose, so
  "discrimination = tightness" is not a clean 1:1.)

- **Finding 2 — but 2PL does not generalize; it overfits.** On the held-out
  solve-prediction check (80/20, identical cells), 2PL is **worse than Rasch at every
  regularization level** — even shrunk almost to Rasch (`sigma_g=0.15`, median
  `alpha≈1.08`):

  | model | log-loss | Brier | AUC |
  |-------|----------|-------|-----|
  | Rasch | **0.3173** | **0.1001** | **0.8710** |
  | 2PL `sg=0.15` | 0.368 | 0.106 | 0.853 |
  | 2PL `sg=0.50` | 0.410 | 0.111 | 0.853 |

  A handful of problems escape to the `alpha` clamp (4.48) regardless of the prior and
  make over-confident, rank-wrong held-out predictions (AUC drops, not just
  calibration). The **LLM-bucket Spearman also falls** to **+0.856** (vs shipped Rasch
  +0.874, survival +0.880, arch A +0.908), and difficulties move materially
  (`corr 0.979` to Rasch but 895/1579 problems shift >100). So the extra parameter
  buys nothing on either the internal predictive check or the external ranking.

- **Verdict.** 2PL *captures* the regional discrimination signal but as prototyped it
  **overfits and degrades validation**, so the shipped fit stays **Rasch** (the
  original scope decision now has evidence behind it). To make 2PL pay off would need
  a field-size-aware discrimination prior (decoupling `alpha` from sheer field size),
  a tighter clamp / heavier-tailed `g` prior, and ideally a 2PL re-derivation of the
  *survival* likelihood rather than the binary one. `twopl.py` is kept as a runnable
  prototype (`python -m arch_b.twopl_region` reproduces all numbers above).
