# Mainland rank under vacancy scenarios

The 230 mainland performance offers reach projected tier 78. The HK registration-vacancy scenarios occur after those offers. If instead one extended the same mainland walk to replace vacancies until 230 teams accepted, uniform nonacceptance of 1%, 10%, or 20% would require approximately 233, 256, or 288 offers and reach tiers 78, 89, or 109. The published final rule describes a separate application-based redistribution. These extended tiers are counterfactual.

To reproduce, use the inputs and Python definitions through diminishing_yield in [the current-season replay](2026-11-23-hk-ecfinal-current-season.md), then run:

```python
for vacancy in (0, .01, .10, .20):
    offers = math.ceil(230 / (1 - vacancy))
    tier = next(k for k in range(45, 160) if diminishing_yield(k, 5) >= offers)
    print(vacancy, offers, tier)
```
