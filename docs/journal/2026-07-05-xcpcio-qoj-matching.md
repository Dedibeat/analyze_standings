# XCPCIO ← QOJ matching

XCPCIO board data (`https://board.xcpcio.com`) hosts the official ICPC scoreboard
for East Asia regionals.  ``scripts/build_xcpcio_official.py`` fetches
``team.json`` for each matched contest and caches normalized official-team
identity keys in ``data/xcpcio_ea_official.json`` (28 contests, 2022–2025
regionals + EC-Finals — seasons 47th–50th).  Teams are matched to QOJ standing
rows by set-intersection of candidate keys: bare name, org-name pairs with
``-`` / ``: `` separators, parenthetical-stripped variants (XCPCIO bilingual
orgs like `北京航空航天大学(Beihang University)` → stripped to Chinese-only),
and member-stripped ``display_name_raw`` prefixes (QOJ domjudge rows append
`` - member1, member2, ...``).

**Coverage.**  28 of 30 EA medal contests are matched (the 6 online ``"ICPC"``
qualifiers and EC-Final warm-ups are excluded by scope, not by matching failure).
Two EA contests have no XCPCIO entry: Grand Prix of China (QOJ 3295) and
Metropolis (QOJ 1913).  Matching quality is generally high (80–100% of XCPCIO
teams found in QOJ); two contests have low match rates due to naming
differences: Xi'an 2023 (~10%, bilingual org names) and Xi'an 2025 (~50%, i18n
name dicts).  For older seasons (47th–48th) XCPCIO team data lacks per-team
``"group": ["official"]`` tags, so the entire XCPCIO team list is treated as
the official field; this is validated by comparing XCPCIO team counts against
QOJ domjudge-id row counts (they match exactly).
