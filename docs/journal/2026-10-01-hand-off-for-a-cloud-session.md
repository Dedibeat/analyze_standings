# Hand-off for a cloud session (2026-10-01)

- `forecast_next_steps.md` holds the module state, the ranked ways to improve
  the forecasts (registered 2026 fields, in-season updates, member history for
  silver/bronze, merging renamed teams) with the PTA API details, and the open
  asks to the user.
- **PTA exports now committed.** The four PTA exports used by
  `add_pta_rosters.py` are committed at the user's request (the coach names
  are public on PTA's team pages). This replaces the earlier note that they
  stay untracked. `icpc_2025_online_2_teams.csv` (byte-identical to the 2026
  round-2 file) stays uncommitted.
- **XCPCIO configs committed.** The 28 cached `config.json` files in
  `data/ec_online_cache/xcpcio/` are force-added, because `arch_b.hk_gold`
  reads contest dates from them. Without them a fresh clone downloads them,
  and XCPCIO often fails (curl exit 35/52 in this session). The rest of the
  cache stays ignored.
- **Setup:** `pip install numpy pypinyin` (README updated).
