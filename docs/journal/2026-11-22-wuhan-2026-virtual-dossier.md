# Wuhan 2026 virtual: dossier (2026-11-22)

**Request.** Write the coach dossier for NUM-R^3's 2026-11-21 virtual of the 51st Wuhan regional
(QOJ 4694), with the TEAM_R3 data fetched as Dedibeat. Dedi described the contest: Dedi did A, then
K while Tamir was at the keyboard; Tamir got 2 WA; Erdene arrived late and got G; Tamir got J while
Dedi wrote D (RE from a sorting bug, then AC); Erdene got G while Dedi and Tamir worked on J; in the
last hour Dedi and Tamir did B, which got 3 WA from an out-of-bounds read that GPT then found. B does
not count.

**Result** (`output/team_r3_coach/4694.md`):
- QOJ board row: 6 solved / 988 min, #42 of 369 official (XCPCIO `icpc/51st/wuhan`).
- **Counted, without B: 5 / 631, #53, silver.** Lines: gold #37 6/933, EC-Final ~75 = the last
  5-solver 5/1139, silver #111, bronze #222. Medal counts follow the Xi'an/Chengdu pattern
  (⌈10%⌉ ×1/×2/×3 = 37/74/111); the board's own counts were not read.
- B on the first try would have been 6 / 928, #36, gold. 26 of 28 six-solvers have ABDGJK, and 36 of
  37 gold teams solved B.
- Tamir's 2 WAs were on D, not K: the data has D WA 42'/53', K AC 57' (first try), D RE 75', D AC 94.5'.
- Diagnoses, verified by scratch stress tests (not in the repo):
  - D RE: the sort comparator `d[u] == d[i] + 1` is not a strict weak ordering. A `_GLIBCXX_DEBUG`
    build aborts in `std::sort` on 2,264 of 3,000 random graphs.
  - Tamir's D runs checked necessary conditions but never ran the DFS. They are wrong on 10 and 3 of
    the 3,000 graphs.
  - B: `s[i]` for i up to j > `s.size()`. The last WA differs from the AC on 148 of 2,000 random
    inputs, and an `-D_GLIBCXX_ASSERTIONS` build aborts on 1,880 of them.
- G's three ACs are one solution trimmed twice (Erdene shortening his own AC). Read from the code;
  this is the open question to Dedi.

**Data and code changes.**
- `data/team_r3/`: 29 new submissions (208 total; 4694 plus the 11-06 contest 3295 and the 11-08
  contest 4582). The 14 Wuhan sources, and 4694's dashboard and both boards, are saved. The
  15 sources of 3295/4582 and their dashboards are **not** fetched.
- `boards/xcpcio_51st.json` gains the Wuhan official board, copied from
  `data/xcpcio_51st_regionals.json`. `members_solved.csv` gains the six Wuhan rows; the ODS should
  get them too.
- `team_r3_digest.py` and `team_r3_participations.py` know 4694. Participations now skips (and
  names) played contests without a dashboard instead of crashing on their unknown labels. Its
  rebuilt JSON also refreshes `difficulty_cf` of the older contests to the shipped 11-17 ratings.
- `fetch_team_r3.py`:
  - skips an attachment that answers 403/404 instead of stopping;
  - does not save an empty problem-page article as a statement;
  - writes LF. `data/team_r3/**` is `-text` and its blobs are LF, so on Windows every run had
    rewritten whole files as CRLF.
- `.venv`: `curl_cffi==0.16.0` installed (it was missing).

**Not done / open.**
- **Statements and editorial.** Every `download.php` request through `scripts/qoj_auth.py` answers
  404, for 4694 and for 4607 (fetched fine on 11-04). The same URL in a browser is a file download,
  so it is the helper's request, perhaps the evasion suffix on `download.php`. Not debugged: the
  docs forbid bypassing the helper. The dossier describes problems from our code only. QOJ lists no
  tutorial for 4694.
- **Rate.** Cloudflare challenged `/submission/<id>` after about 3 pages per run. Spaced reruns (3
  min apart) got the 14 Wuhan sources, and 4694's pages were fetched directly with `fetch_contest`.
- Who typed J; when Erdene arrived.

Reproduce:
`QOJ_USERNAME=Dedibeat .venv/Scripts/python -m scripts.fetch_team_r3 4694` (repeat until no
challenge), `python scripts/team_r3_participations.py`, `python scripts/team_r3_digest.py 4694 B --code`.
