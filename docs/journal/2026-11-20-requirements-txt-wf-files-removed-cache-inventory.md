# requirements.txt, WF files removed, cache inventory (2026-11-20, second entry)

**Request.** Delete `WF.txt` and `data/wf_contests.json`, add a `requirements.txt`,
keep the committed `data/ec_online_cache/` files tracked, and propose a better way
to store cached data.

**Done.**
- **Deleted `WF.txt` and `data/wf_contests.json`.** WF.txt held four QOJ URLs:
  contests 1661, 1662, 1966 and 2522. No code or doc read either file. The World
  Finals fit supplement, `data/wf_tagged_format.json`, is untouched.
- **Added `requirements.txt`.**
  - Pins: numpy, scipy, pandas, lightgbm, openpyxl, pypinyin, curl_cffi and
    google-cloud-bigquery.
  - Found by an AST scan of every tracked `.py` file for third-party imports,
    pinned to the working venv.
  - `curl_cffi` 0.16.0 was only in the system Python, so it is now installed in
    `.venv` too.
  - `pip install --dry-run -r requirements.txt` reports nothing else to install.
  - Sibling checkouts (`qoj`, `cf_problems`) and the optional local TabFM
    checkpoint are listed as comments.
- **`data/ec_online_cache/` stays tracked.** The user's reason: refetching can be
  expensive and slow.

**Cache inventory** (sizes on this machine; the paid or irreplaceable items are
the ones worth backing up):

| cache | size | kind |
|---|---|---|
| `data/cf_ai/rc`, `st`, `contest_list.json` | ~240 MB | raw CF API downloads; hours to refetch |
| `data/cf_ai/boost_v1*`, `cross_history_v1`, `replay.npz` | ~9.5 GB | derived; rebuilt by `scripts/cf_*` |
| `data/team_r3/**` PDFs/zips/bin | 131 MB (300 files) | account and contest downloads; may vanish |
| `data/team_r3/cf/standings`, `editorials` | 12.5 MB | CF downloads |
| `data/ec_online_cache/` | 28 MB | official pages; partly tracked |
| `data/cf_pairwise/problems/` | 8 MB | CF statements for the pairwise pilot |
| `pairwise_*_run/`, `llm_survival_run/`, `gemini_gap_run/`, `llm_crosscontest_run/` | ~50 MB | **paid** Gemini outputs |
| `tabfm_bigquery_run/` | 25 MB | **paid** BigQuery TabFM responses |
| `de_stability_run/`, `hier_binary_run/` (PC only) | small here | derived fits |

Git history is not the problem: the pack is 82 MB, and its largest contributors
are regenerated HTML viewers.

**Proposed, awaiting the user's choice.** Back up only the raw and paid tier
(about 0.5 GB) to a private store, and record a checksum manifest in git. Derived
caches are rebuilt from code.
