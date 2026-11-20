# NUM-R^3 participations: team-account data download (2026-11-04)

**Request.** Analyze the team's 2026 virtual and official participations.
First download everything the analysis needs (statements, editorials, code,
the team's submissions) into a reusable place, using the team account
TEAM_R3, the sibling `../qoj-intergration` and
`../p1/qoj/BROWSERLESS_AUTH.md`. The member attribution is
`~/Documents/team_members_solved.ods`.

**Scripts.**
- `scripts/fetch_team_r3.py` (new): browserless login (curl_cffi `chrome136`,
  md5 password, `_token` from the page's JS; cookies cached, git-ignored, in
  `data/team_r3/.cookies.json`). It reads the account's whole submission list
  and every source, plus each contest's dashboard, per-problem statements and
  all attachments, with PDFs also as text via `qoj.pdf_to_text`. Contests are
  the ones given on the command line plus every contest the account
  submitted in. Files already on disk are not fetched again.
- `scripts/team_r3_participations.py` (new): the first-pass table below,
  written to `output/team_r3_participations.{md,json}`.
- `scripts/fetch_xcpcio_standings.py`: 51st-season XCPCIO configs list
  `problems: [{id, label}]` instead of `problem_id`, and the converter
  rejected them. It now takes labels from `problems` and maps run ids through
  them. Older boards are unaffected: the new path applies only when
  `problems` is present.

**Account findings.**
- **TEAM_R3 has QOJ "Training Mode" on.** Every `/contest/<id>/standings`
  returns 404 and dashboards show no Standings tab. The user chose to keep it
  on (spoiler-free virtuals), so boards come from the local data files and
  XCPCIO. A first guess was that the unfinished virtuals hid the board.
  "Finish!" was pressed once, on 4607 only (POST accepted with a 302). The
  panel stayed and the board stayed hidden, so the button only re-submits
  the virtual result and was not pressed elsewhere.
- **The official 2026 online rounds were not played on TEAM_R3.** QOJ
  imported them under `$DEFAULT_DAT_PREFIX_*` ids, so their code is not
  reachable. The NUM-R^3 rows on the stored boards are used instead. TEAM_R3's
  only 4071 runs are 28-byte tests (2026-09-17 and 10-09).
- **Rate limit.** After about 65 fast page loads, Cloudflare answered 429 to
  everything. The fetcher now spaces requests 1.5 s apart and waits
  30 s × attempt on a 429, which gets about 3 pages a minute through. No Tor
  was used. A full first run takes about 2 h.
- **`qoj.py` problem regex.** `CONTEST_PROBLEM_RE` misses dashboard links that
  end in `/statement/<lang>`: 2575 Harbin parsed as M only. The fetcher uses its
  own regex. `../qoj-intergration` itself was not changed.
- **Prompt injection.** `../qoj-intergration/AGENTS.md` contains a "YOU ARE
  CAT" persona/jailbreak block unrelated to the project. It was ignored; it
  should be removed from that repo.

**Data (`data/team_r3/`, 131 MB; 4.2 MB committed, the PDFs/zips/simulators
git-ignored).**
- **Submissions:** 179, from 2026-08-20 to 11-01; 85 AC. 160 were in-contest
  and 19 practice. All sources are saved (`code/<id>.txt`).
- **Contests:** 21. That is the 11 in the spreadsheet plus 1051, 1485, 2513,
  2524 and 2575 (virtuals missing from the sheet) and 1449, 1828, 1893, 2581,
  2641 (practice only).
- **Statements:** every problem has a statement PDF and text, except 4113,
  where QOJ answers 403 per problem and offers no statement attachment.
- **Tutorials:** present for all contests except 1485, 1794, 2513 and 4593,
  which have none on QOJ. 1051's tutorial is a zip of slides and code.
- **Boards:**
  - `tagged_official.json` (official-only copy) for the 2022 regionals and the
    2023–2025 online rounds;
  - `tagged.json` for 4071/4113;
  - `ucup_s4.json` for 2661/2693;
  - `petroz_2022_2026.json` for 2575;
  - XCPCIO `icpc/51st/{xian,chengdu}` (official rows) for 4593/4607, saved in
    `boards/xcpcio_51st.json`.
- **Member attribution:** `members_solved.csv`, the sheet as exported by
  LibreOffice.

**Follow-up (same day): personal account and fixed sheet.**
- The user fixed the sheet: Chengdu 2026's second D is now C (Dedi), and
  "Erdehe" is now Erdene. 1051, 1485, 2513, 2524 and 2575 still have no
  sheet rows.
- **Dedibeat fills the gaps.** The fetcher's `QOJ_USERNAME` is now only the
  reading account: the submission list is always TEAM_R3's, and cookies are
  kept per account (`.cookies-<user>.json`, git-ignored). Run as Dedibeat
  (no Training Mode), it saves each contest's QOJ board twice:
  `standings_all.json` (with virtual rows) and `standings_official.json`.
  TEAM_R3's own virtual row is on `standings_all`, so every virtual now has
  its exact solved count, solve times, wrong tries and penalty.
- **4113 statements.** QOJ refuses the PDFs with 403 for Dedibeat too, but
  the problem page carries the statement as HTML (with LaTeX). When the PDF
  is refused, the fetcher saves `<L>.html` and a text version.
- **Rate limits.** The Dedibeat run made about 60 requests and was not
  rate-limited.

**Results.** These are exact QOJ virtual rows, ranked by solved/penalty
against the official onsite field. The 2026 online rounds use QOJ's
official board. For 4593/4607 the field is XCPCIO's official ICPC teams,
not QOJ's Universal Cup field.

| contest | kind | date | solved | penalty (min) | rank / official teams |
|---|---|---|---|---|---|
| 4071 EC Online I 2026 | official | | 6 | 877 | 544 / 2535 |
| 4113 EC Online II 2026 | official | | 4 | 482 | 352 / 2636 |
| 1485 EC Online I 2023 | virtual | 08-20 | 6 | 758 | 417 / 2554 |
| 1794 EC Online I 2024 | virtual | 08-22 | 6 | 714 | 96 / 2323 |
| 2513 EC Online I 2025 | virtual | 09-03 | 7 | 625 | 147 / 2279 |
| 2524 EC Online II 2025 | virtual | 09-09 | 5 | 890 | 345 / 2575 |
| 1799 EC Online II 2024 | virtual | 09-10 | 6 | 402 | 514 / 2450 |
| 1051 Xi'an 2022 | virtual | 10-01 | 6 | 357 | 116 / 522 |
| 1071 Hangzhou 2022 | virtual | 10-02 | 7 | 886 | 24 / 643 |
| 1053 Jinan 2022 | virtual | 10-08 | 5 | 578 | 98 / 568 |
| 1096 Shenyang 2022 | virtual | 10-09 | 4 | 435 | 193 / 1004 |
| 2693 CCPC Jinan 2025 | virtual | 10-11 | 4 | 484 | 164 / 413 |
| 2661 CCPC Zhengzhou 2025 | virtual | 10-16 | 3 | 591 | 222 / 418 |
| 2575 CCPC Harbin 2025 | virtual | 10-23 | 5 | 707 | 275 / 760 |
| 4593 Xi'an 2026 | virtual | 10-25 | 4 | 536 | 86 / 402 |
| 4607 Chengdu 2026 | virtual | 11-01 | 6 | 894 | 35 / 319 |

- **Agreement with earlier records:**
  - The rows reproduce every scoreline recorded earlier: 6/714, 6/402,
    7/626 (625 here), 5/890, Jinan 4/484 (#164), Xi'an 4/536 (#86, the
    "official rank" reading of 2026-10-26) and 4071's official #544.
  - All exact penalties lie inside the bounds of the first pass.
  - 4113 is #352 on QOJ's official board, against #349 in the PTA ranking of
    2026-10-08.
- **Fallback:** without a QOJ board (e.g. running only as TEAM_R3), the
  script still falls back to the start-time bounds.
- **Not on any board:** TEAM_R3's 0-solve row on 4071 is the 28-byte test,
  not a participation.

**Not done.** The analysis itself: per-member load, problem difficulty
reached against the field, time-to-solve and wrong-attempt patterns, virtual
vs official gap. The data for it is in place.

Run: `QOJ_USERNAME=Dedibeat QOJ_PASSWORD=… python3 scripts/fetch_team_r3.py
4071 4113 4607 4593 1071 1053 2693 2661 1096 1794 1799`, then
`python3 scripts/fetch_xcpcio_standings.py icpc data/team_r3/boards/xcpcio_51st.json
--board-link /icpc/51st/xian --board-link /icpc/51st/chengdu` and
`python3 scripts/team_r3_participations.py`.
