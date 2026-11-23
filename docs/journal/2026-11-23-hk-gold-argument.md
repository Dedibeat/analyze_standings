# Which Hong Kong gold estimate applies?

Compared Claude's November 16 argument with the November 22 registration snapshot. Renmin's All ways Onward is Reviewed. The snapshot has 112 Reviewed plus 14 Pending. The historic HK table records Fudan gold in 2025 only. The current checkout lacks the cited Changchun calculation, so the supplied result is additional evidence outside the 15-virtual average.

Running the November 23 medal calculation at single-contest performance levels gives the following gold percentages, Reviewed / Reviewed plus Pending: Shenyang 8.4 / 14.4, Chengdu 41.0 / 56.1, Chengdu less 100 points 20.7 / 32.4, Wuhan unassisted 22.1 / 34.2, Wuhan less 100 points 10.1 / 17.1. These use linked-field cutoffs. The 30–60% claim is reasonable conditional on Chengdu form. Forecasting contest day also requires an estimate of how often the team produces that form.

Reproduce by running the Python block in [the season calculation](2026-11-23-team-form-hk.md), then:

```python
for score in (2327, 2542, 2442, 2451, 2351):
    print(score, project(score))
```
