# Expensive caches committed to git (2026-11-20, third entry)

**Request.**
- The user considered other storage: Hugging Face, then the PC, then Syncthing
  between the laptop and the PC.
- The PC is a Windows machine and is often off. The laptop runs no SSH server.
- The user chose: "let's just use git for now. And push expensive ones."
- The repository is public but not announced.

**Committed:** 3,891 files, about 490 MB, until now gitignored.

| cache | why it is expensive |
|---|---|
| `pairwise_tuning_run/`, `pairwise_phase2_run/`, `pairwise_phase3_run/`, `llm_survival_run/`, `gemini_gap_run/`, `llm_crosscontest_run/` | paid Gemini calls |
| `tabfm_bigquery_run/` | paid BigQuery TabFM responses |
| `data/cf_ai/rc/`, `st/`, `contest_list.json` | hours of rate-limited CF API calls |
| `data/team_r3/**` PDFs, zips, `.bin`; `cf/standings/`, `cf/editorials/` | QOJ login and CF downloads; Cloudflare blocks blog pages |
| `data/ec_online_cache/` (the files not yet tracked) | official pages that can change |
| `data/cf_pairwise/problems/`, `phase2_enrichment_summary.json` | statements and editorials for the pairwise pilot |

**Kept out:**
- QOJ cookies (`data/team_r3/.cookies*.json`, `data/.cookies-*.json`).
- Derived caches, rebuilt from code: `data/cf_ai/boost_v1*`, `cross_history_v1/`,
  `replay.npz` (about 9.5 GB), `de_stability_run/` and `hier_binary_run/`.
- `cphof_cache/` and `gym_checkpoints/`: still ignored, and not on this laptop.

**Checks before committing.**
- **Secrets:** no API keys, OAuth or bearer tokens, private keys or session
  cookies. The scan covered every text file, including gzipped ones. The
  "password" hits were problem statements.
- **Personal data:** one email, a team contact in XCPCIO's public EC-Final
  `team.json`.
- **GCP project ids:** already in tracked docs.
- **Size:** the largest file is 24 MB (TabFM `manifest.json`), under GitHub's
  limits.
- **Scope:** the set of newly untracked files equals the candidate list
  exactly.
- **Line endings:** `.gitattributes` marks these paths `-text`, so a Windows
  checkout keeps them byte-identical.
- **Pairwise snapshot:** `scripts/sync_pairwise_artifacts.sh verify` already
  reported 2 mismatches before this commit. `pairwise_phase3_run` has 21 files
  against the snapshot's 9, and `data/cf_pairwise/problems` has the same 978
  files with new contents. The 2026-08-06 snapshot predates the phase 3 results
  and the problem enrichment. It was left unchanged; git history now records the
  exact files.

**Sync:** `git pull` on the PC. Git history grows by the compressed size of these
files: the pack was 82 MB before.
