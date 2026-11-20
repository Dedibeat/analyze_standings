# Season-separated identity + short-contest filter (`arch_b.season_experiment`)

Two data options were tried and validated on the UCup-anchored survival fit:

* `load(season_key=True)` — separate a recurring roster's ability by ICPC season,
  using the **map** (championships / World Finals belong to the *previous* season:
  `load.season_of`); stable `ucup-*` ids stay season-agnostic as the cross-season
  backbone, so the scale does not fragment.
* `load(min_solve_hours=3.5)` — drop short-format contests (warm-ups, 3 h rounds)
  whose latest solve is under 3.5 h (a duration proxy; 4.5 h would wrongly drop
  small 5 h regionals whose last solve happened early). Now the **default in
  `arch_b.run`**.

| config             | teams | contests | graph (comp / biggest) | CF Spearman | CF LOCO-RMSE | LLM Spearman |
|--------------------|-------|----------|------------------------|-------------|--------------|--------------|
| baseline           | 33991 | 146      | 9 / 138                | +0.954      | 252          | +0.880       |
| +5 h filter        | 33186 | 133      | 3 / 131                | +0.954      | 252          | +0.880       |
| +season +5 h       | 34117 | 133      | 3 / 131                | +0.949      | 270          | +0.880       |

The **5 h filter is a clean hygiene win** — identical external agreement while
removing 13 noisy short contests and *improving* connectivity (9→3 components), so
it is on by default. **Season-keying is validated as not worth it**: it preserves
connectivity (the map + stable-ucup backbone avoids the per-season islands that
sank plain year-keying) but slightly *worsens* CF agreement and leaves LLM
unchanged — the +929 per-season roster splits each carry less data, and that cost
cancels the time-varying benefit for *difficulty*. It stays an opt-in flag.
