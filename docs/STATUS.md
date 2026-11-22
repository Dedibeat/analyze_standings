# Status

Current state of the project. Keep this file short (≤150 lines) and true: when a
task changes what ships, what is open, or a rule below, edit this file in the same
commit. History belongs in [journal/](journal/INDEX.md), not here.

Last updated: 2026-11-22 (QOJ: harvested cf_clearance fallback).

## What ships

- **Production rating model: hierarchical binary Rasch with solve-time slices**
  (`arch_b.hier_time`, setting `time_skip`, K=5 slices, weight 0.25,
  `skip_partial`, frozen hierarchical priors). It has shipped since 2026-11-16 and
  replaced DE, which had shipped since 2026-09-28. Nested-LOCO CF RMSE is 205.9 on
  184 trusted anchors (DE 207.0); that gain is not significant.
  Record: [journal entry](journal/2026-11-16-ship-hierarchical-binary-with-time-to-all-rating-products.md),
  [report](reports/rating/hier_time_report.md).
- **Artifacts:** `output/problem_ratings_hier.json` and
  `output/problem_calibration_hier.json`. `arch_b.shipped` holds the one cached
  full-data fit and its affine map, which every exporter uses. `calibrate.problem_cf`
  reads the hierarchical file. DE and survival outputs are historical baselines only.
- **Products:** the virtual-contest calculator (`output/virtual_calc.html`), the
  ratings viewer, and the medal badges and medal viewer. They are copied into the
  sibling app `../my-react-app`, which is published at https://dedibeat.github.io/.
- **Ratings on small boards carry a `small_board` flag** (since 2026-11-09).

## Regenerate the shipped products

```bash
python -m arch_b.hier_time release      # problem ratings + calibration
python -m arch_b.export_virtual_calc
python -m arch_b.export_viewer
python -m arch_b.medals
python -m arch_b.export_medal_viewer
```

To add or refresh a contest, run
`QOJ_USERNAME=… QOJ_PASSWORD=… python3 scripts/add_qoj_contest.py <id> --name … --region … [--refresh]`.
The team-submission and single-contest fetchers share a browserless session.
The client impersonates Chrome and appends a query suffix to every QOJ request;
that pair is what gets past Cloudflare, which challenges the bare auth paths.
Live login and downloads verified 2026-11-22. See
[QOJ fetcher usage](usage/qoj.md).
For XCPCIO-only boards, use `scripts/fetch_xcpcio_standings.py`. Rerun
`scripts/attach_online_rosters.py` after EC online rounds change, then run the
release steps above. Full history:
[2026-11-15 entry](journal/2026-11-15-latest-standings-and-new-contests-pulled-2026-regionals-in.md).

## Rules that are easy to break

- **QOJ transport:** `scripts/qoj_auth.py` must keep `impersonate` on the
  `Session` and the `_tag()` query suffix on every request. Removing either
  makes every live QOJ call fail with a Cloudflare challenge — ungated pages
  included ([why](journal/2026-11-22-qoj-cloudflare-evasion.md)). If a challenge
  still arrives, `scripts/qoj_clearance.py` harvests a `cf_clearance` that
  `qoj_auth.py` replays ([why](journal/2026-11-22-qoj-cf-clearance.md)). That
  cookie file is a credential: gitignored, mode 600, never commit or copy it
  between machines — it is bound to the minting IP and User-Agent.
- **Fit inputs:** `data/tagged.json` plus the supplements read by `arch_b.joint`
  (`ucup_s3/s4`, `icpc_2020_2021`, `petroz_2022_2026`, `wf_tagged_format`).
  CCPC boards (`xcpcio_ccpc.json`, `qoj_ccpc.json`), AOJ and Kattis are
  **research and validation only, never fit inputs**.
- Choose model settings **without CF labels**. Fix the criteria before the run
  (pre-registered), and keep negative results.
- Two labels are documented as wrong and are excluded from the CF maps and RMSE:
  the anchor Uniform Chemistry (CF 3200, about 2000 by hand) and one blind hand
  rating.
- The cross-contest LLM LOCO "improvement" used held-out CF labels and is
  **invalid** as generalization evidence
  ([experiment review](reports/rating/experiment_review.md)).
- Research modules write their own `output/*.json` and must not change shipped
  artifacts unless the task says to ship.
- Frozen research artifacts record SHA-256 hashes by file path. Their recorded
  paths predate the 2026-11-20 move (for example `calibration_audit_plan.md` at
  the root), and the hashes were already stale after the 2026-11-16 loader fix.
  Don't edit those JSONs to make them pass.

## Environment

- Linux: `./.venv/bin/python`. The Windows PC: `./.venv/Scripts/python`, with
  `PYTHONUTF8=1 OPENBLAS_NUM_THREADS=1` for long fits.
- Long fits (`hier_binary all`, `hier_time evaluate`) run on the PC. Their caches
  (`hier_binary_run/`) exist only there.
- **Expensive caches are committed** (since 2026-11-20, about 490 MB): the paid
  `*_run/` outputs, raw CF API data, `team_r3` downloads, `ec_online_cache` and
  `cf_pairwise/problems`. Machines sync them with `git pull`. Derived caches
  stay gitignored; see `data/CLAUDE.md`.
- **The repository is public** (not announced). Never commit cookies or tokens.
- Dependencies: `./.venv/bin/pip install -r requirements.txt`. Sibling checkouts
  are listed inside. The DE stability experiment pins
  `requirements-de-stability.txt`.
- **Tests:** `./.venv/bin/python -m unittest discover -s tests -p 'test_*.py'`
  (about 1 min). **Known failures:** 3 in `test_medal_predict` (city-mean and 2026
  recommendation expectations predate the current fit).

## Open threads (newest first)

- **QOJ transport is a moving target** ([usage](usage/qoj.md),
  [entry](journal/2026-11-22-qoj-cloudflare-evasion.md)). Live fetching works by
  impersonating Chrome and appending a query suffix to beat a Cloudflare rule
  that matches the bare auth path. Both are client-side and portable, but the
  rule can be tightened to include the query string at any time, and
  datacenter ASNs can still be challenged. The fallback is a harvested
  `cf_clearance` ([entry](journal/2026-11-22-qoj-cf-clearance.md)), which is not
  portable: it is bound to the minting IP and User-Agent and must be re-harvested
  per machine when QOJ expires it. The failure is immediate and explicit
  (`python -m scripts.qoj_auth` stops with the reason), so no silent bad data.
- **Codeforces research** ([usage](usage/codeforces.md), reports in
  [reports/codeforces/](reports/codeforces/)). The five-hour all-metric search is
  complete; the loss-selected model beats the incumbent on all four point metrics.
  Still open:
  - read CF blog 154620 in full and reconcile its 150–190 deflation with ours (63–113);
  - pin down the new-account seeding rule;
  - test whether the participation drop is a cause;
  - find an independent later timed field and dated CLIST ratings.
- **Public release, feedback, paper** (research only,
  [entry](journal/2026-11-16-public-release-human-feedback-and-a-paper-research.md)).
  Settle statements, names and licence before announcing. *Olympiads in Informatics*
  is the 2027 target.
- **Rating model:**
  - Weak, weakly linked boards read about 300 too hard by hand (Latin America 2023).
    Settling it needs CF ratings of some of those teams.
  - Strong-board floors read high.
  - Within-contest order reversals under field cuts roughly doubled with the time term.
  - Record: [hier_time report](reports/rating/hier_time_report.md),
    [problem rating audit](reports/rating/problem_rating_audit.md).
- **Medals for the 2026 regionals:** the 2026 EA regionals are in the fit but not
  in the medal analysis (`data/xcpcio_ea_official.json` lacks them).
- **NUM-R^3 season** (our team): Shenyang was 2026-11-15. Hong Kong is
  [2027-01-09/10](https://registration.nerc.icpc.global/regionals/finder/HongKong-2027).
  The [training plan](reports/team-r3/hong-kong-2027.md) starts with a Wuhan 2026 virtual on Nov 21 and runs through the regional.
  The EC-Final estimate is 2027-01-22/23. Forecasts are in the
  hong-kong / ec-final journal entries; coaching data is in `data/team_r3/` and
  [usage/team-r3.md](usage/team-r3.md).

## Where to look next

- Repository map: [README.md](../README.md). Folder maps: `arch_b/CLAUDE.md`,
  `scripts/CLAUDE.md`, `data/CLAUDE.md`.
- History: [journal/INDEX.md](journal/INDEX.md). How to run things:
  [usage/](usage/). Method: [design/](design/).
