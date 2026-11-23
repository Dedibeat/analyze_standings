# QOJ downloads: the query suffix broke `/cached-downloads/` (2026-11-22)

**Request.** Debug why every statement and attachment download through
`scripts/qoj_auth.py` answered 404 (found while writing the
[Wuhan 2026 dossier](2026-11-22-wuhan-2026-virtual-dossier.md)), so the Wuhan statements can be
added.

**Cause.** `download.php` was never the problem. Live probes on the signed-in session:

| request | result |
|---|---|
| `download.php?…&x=1` (helper form), bare, with or without Referer | 302 → `/cached-downloads/<hash>/<hash>` |
| `/cached-downloads/<hash>/<hash>?x=1` | **404**, empty body, no challenge |
| `/cached-downloads/<hash>/<hash>` (bare) | 200, `application/pdf`, 1,179,398 bytes, no challenge |

`_request` follows redirects itself and tags every target with `_tag()`, so every download chain
ended on the tagged cached file and got a 404. A browser follows the same redirect without the
suffix, which is why the URL "worked in a browser". This broke all QOJ file downloads since the
suffix was introduced earlier on 11-22; 4607's statements (fetched 11-04) also 404'd.

**Fix.** `_tag()` returns `/cached-downloads/…` URLs unchanged. Every other request is still
tagged, and the rule in `docs/STATUS.md`, `docs/usage/qoj.md` and `scripts/CLAUDE.md` now names
the exception. New test `test_cached_download_redirect_target_is_not_tagged` failed before the fix
and passes after it. `tests.test_qoj_auth`: 15 pass.

**Also run.** Upstream's `9d66cf2` (harvested `cf_clearance` fallback) was merged first.
`websocket-client==1.9.0` is installed in `.venv`. `tests.test_qoj_clearance` has one Windows-only
error, `test_chrome_override_is_honoured`: it expects `/bin/sh` to exist. That is upstream code and
was left alone.

**Result.**
- 4694 now has all 13 statement PDFs (+ text) and the full English set under
  `data/team_r3/contests/4694/`. QOJ still lists no tutorial.
- The dossier's problem notes now follow the statements. K's "every kept edge parent-first"
  shortcut was checked: both ends of a parent-first edge strictly increase and both ends of a
  child-first edge strictly decrease, so components are uniform. Our code matches a brute force on
  400 random trees of ≤ 6 vertices.
- Dedi settled the two open questions (user, 2026-11-22):
  - J was Dedi's idea and code, with Tamir giving counterexamples and directions;
  - Erdene resubmitted G to shorten his own code.
  The sheet copy and dossier are updated.

Reproduce:
`./.venv/Scripts/python -m unittest tests.test_qoj_auth`, then
`QOJ_USERNAME=Dedibeat ./.venv/Scripts/python -c "from contextlib import closing; from scripts.fetch_team_r3 import authenticate, fetch_contest; s=authenticate(); fetch_contest(s, 4694); s.close()"`.

**Follow-up (same day).** Dedi confirmed the K reversal argument (he saw it in the contest) and
said he gave Tamir the keyboard for D after A because more teams were solving D. The dossier
now records the choice and proposes "a complete idea gets the keyboard before an unfinished one,
the scoreboard breaks ties"; the sheet copy's K row notes it.
