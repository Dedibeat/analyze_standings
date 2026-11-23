# Repository reorganized for agent navigation (2026-11-20)

**Request.** Clean and organize the repository so that people and agents can find
things easily, and agents get the important context without filling the context
window. The user chose:
- split `details.md` into dated entries with an index;
- tidy the docs and the root, but leave the code layout alone;
- make one master file that summarizes the whole repository.

**Problem.**
- `CLAUDE.md` told every agent to read `details.md` first: 548 KB, 9,260 lines,
  about 140k tokens of append-only history, much of it superseded.
- `README.md` (92 KB) still called DE the shipped calibration in places.
- 45 reports, plans and `.tex` files sat loose at the root.
- `AGENTS.md` was a byte-for-byte copy of `CLAUDE.md`.

**Guidance used.**
- Claude Code loads `CLAUDE.md` in full every session. Its docs advise under 200
  lines, and `@imports` load in full too.
- A nested `CLAUDE.md` loads only when files in its folder are opened.
- A root `AGENTS.md` is ignored when a `CLAUDE.md` exists.
- Anthropic's context-engineering note recommends a few always-loaded facts,
  lightweight identifiers (paths, dated names, folders as metadata), and loading
  the rest on demand.

**What changed** (no model, data or output changed):
- **`details.md` split verbatim** with a script that checks every line lands in
  exactly one file and round-trips:
  - 90 dated `docs/journal/` entries plus `INDEX.md`, with an area tag and the
    known outcome on each line;
  - 5 design notes in `docs/design/`;
  - its two pointer banners rewritten into `docs/STATUS.md`.
  - Undated Architecture B sections take the date of the commit that added them
    (`git log -S`).
- **The README split the same way:**
  - its run sections → 7 `docs/usage/*.md` files and `docs/teaching/README.md`;
  - its findings summary and old Layout → a dated snapshot entry.
- **43 files moved with `git mv`,** keeping their names: reports to
  `docs/reports/<area>/`, teaching to `docs/teaching/`, `strat*.tex`,
  `program.md` and `rating_bias.md` to `docs/design/`. Relative links were
  rewritten.
- **New files:**
  - `docs/STATUS.md`: what ships, rules, environment, open threads.
  - A new `README.md` as the master map.
  - Module maps `arch_b/CLAUDE.md`, `scripts/CLAUDE.md` and `data/CLAUDE.md`.
- **`CLAUDE.md` protocol changed:** read STATUS, use the map, grep the index.
  After a task: a journal entry plus an index line, and STATUS when the current
  state changes. The coding rules are unchanged. `AGENTS.md` is now a symlink.
- **Code:**
  - five plan paths updated in `calibration_ablation`, `calibration_audit`,
    `member_forecast`, `shipped_fit_audit` and `tabfm_bigquery`;
  - "details.md" in 13 code comments now says `docs/journal/`.
- **`tests/test_docs.py` added:** 242 relative links resolve, and INDEX lists
  exactly the journal files.

**Startup reading:** about 643 KB before (`CLAUDE.md` + `details.md` + README),
16 KB after (`CLAUDE.md` + STATUS + README).

**Not done, and why.**
- **The `*_run/` folders were not moved under `runs/`.**
  `scripts/sync_pairwise_artifacts.sh verify` hashes relative paths into
  `data/cf_pairwise/artifact_snapshot.json`, and the other checkout uses the
  same layout. The folders are gitignored, so search tools skip them anyway.
- **Saved `output/*.json` provenance still names the old root plan paths.**
  Those hashes were already stale (`arch_a/load.py` etc., since 2026-11-16), so
  no replay that currently works was broken.
- **Things left for the user:** `WF.txt` and `data/wf_contests.json` have no
  recorded purpose. No `requirements.txt` exists. The 28 committed files in the
  ignored `data/ec_online_cache/` were left as they are.

**Tests:** 247 run. The only failures are the 3 that already failed in
`test_medal_predict`, whose expected city means predate the current fit.
