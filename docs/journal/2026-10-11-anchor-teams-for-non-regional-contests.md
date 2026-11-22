# Anchor teams for non-regional contests (2026-10-11)

**Request.** Goal for the 51st season: an EC-Final seat, possibly gold. To
judge results on non-regional contests with a Chinese field (CCPC, provincial,
invitational), pick anchor teams so a result reads as "we beat most of the
gold / EC-Final-level anchors present". Anchors must have played both 2026 EC
online rounds. Also: find the contests with high overlap with the 2026 online
field. Choices put to the user and accepted: predicted tiers now, replaced by
actual 51st results later; a CLI over any XCPCIO board.

**Pool** (`scripts/anchor_teams.py`). The two 2026 PTA registration exports
are paired by school + team name, else school + ≥ 2 shared members (107 teams
kept their members but renamed between rounds), one-to-one; each round's
online rank is looked up by that round's registered name. 2,153 teams (vs
2,073 by name alone). x = −mean log online rank, zero-solve teams at the
unranked midpoint as in `online_strengths`.

**Tiers** (P for one mainland site the team attends; threshold 0.5, i.e. more
likely than not):
- gold: `online_gold` final model (rules lines quota-adjusted, ρ from
  2023–2025), P averaged over the seven 2026 lines — 88 teams, geometric-mean
  online rank 1–107;
- ecfinal: `ecfinal_chance` model, K = 70/75/80 weighted ¼/½/¼ — 83 more
  teams, #112–205. NUM-R^3 reproduces the earlier 13.8% (gold 3.4%).
- Override: once a team (school + ≥ 2 members) has a 2026 official regional
  row in `regional_teams.csv`, its tier is its best actual result so far —
  gold medal → gold; official rank ≤ 75 at a mainland site → ecfinal (a proxy
  until the EC-Final 公示); otherwise none. This can demote a team that still
  has a second site to play. No 2026 regional rows exist yet, so every tier is
  currently predicted.

**Board comparison** (`--board LINK --team NAME`). Any XCPCIO board; standings
from `build_ec_online_data.regional_standings` (now takes the board kind:
`icpc`, `ccpc`, `provincial-contest`), all teams, compared on (solved,
penalty). Anchors match board rows one-to-one, most shared members first,
then school + team name; English school names (Jiangxi invitational) map to
Chinese via the PTA `school_name_en`. Example, NUM-NTN at Nanjing 2025 (3
solved): 14 gold anchors present, beaten 0; 12 ecfinal anchors, beaten 1.
(That board is last season; anchors are 2026 rosters seen there.)

**Overlap** (`--overlap --since 2025-09-01`, 2026-10-11). online% = board
teams sharing ≥ 2 members (or their only member) with a 2026 online team of
the same school. Non-regional boards, plus regionals for reference:

| board | teams | online% | gold | ecfinal |
|---|---|---|---|---|
| ICPC 50th regionals (Xi'an … Shanghai) | 328–520 | 39–47% | 9–19 | 7–19 |
| ICPC 50th EC-Final | 306 | 49% | 36 | 19 |
| CCPC 11th Harbin / Jinan / Zhengzhou / Chongqing | 278–324 | 42–46% | 10–17 | 6–16 |
| CCPC 2025 Nanchang inv. | 270 | 27% | 0 | 1 |
| ICPC 51st Shenzhen inv. (Apr 2026) | 326 | 54% | 8 | 11 |
| ICPC 51st Wuhan / Jiangxi / Shenyang inv. | 236–384 | 57–80% | 1–4 | 6–7 |
| CCPC 12th Nanchang / Qinhuangdao / Guizhou inv. | 222–375 | 44–65% | 0–3 | 2–3 |
| Provincials 2026 (Zhejiang, Guangdong, Jiangsu, Shanghai, …) | 155–467 | 23–54% | 0–6 | 0–5 |
| CCPC 12th online qualification (Sep 2026, online) | 2,173 | 93% | 78 | 71 |

The CCPC regional stations are as anchor-dense as ICPC regionals and are the
natural measuring contests; the 12th-season stations (Oct–Nov 2026) are not on
XCPCIO yet — rerun `--overlap` once they are. Spring invitationals and
provincials have many 2026 contestants but few gold anchors (≤ 8), so "beat
most anchors" there rests on a handful of teams. Boards with no members
(Xi'an inv., Shaanxi, GBA, HKJCPC) match by team name only and undercount;
GBA/HKJCPC/HK use English names and show ~0%.

**Fix in shared code.** `regional_standings` dropped members stored as a bare
multilingual name (`{"texts": {...}}`, no `name` key; the 50th EC-Final board)
— now read. `regional_teams.csv` was not rebuilt; a rebuild can only fill
previously empty member fields.

Tests: `tests/test_anchor_teams.py`. This environment needed
`pip install numpy pypinyin`.

## Anchor performances on recent contests (2026-10-11 follow-up)

Scratch query (not shipped): `export_virtual_calc.performance_fit()` CF
performances (the app's calibrated binary-fit numbers) for every anchor row in
the fit's contests with QOJ id ≥ 3500 (~March 2026 on). Anchors matched to
rows by ≥ 2 members, in Chinese or in pinyin (`hk_link.pinyin_variants`); every
non-EC-online hit was checked by hand (the NAC/APAC 2026 hits are QOJ mirrors
played by 人大/同济/港中深; pre-university affiliations such as THU1 are the
same people). 166/171 anchors have EC Online 2026 rows; 25 gold and 24 ecfinal
anchors also played another contest (mostly UCup S4: Shenzhen, Shaanxi and
Hubei mirrors of the 2026 Shenzhen invitational, Shaanxi provincial and Wuhan
invitational; GP Wulin/Kyoto/Zagreb/India/Kamigō).

| tier | EC Online 2026 perf, quartiles | other 2026 contests, quartiles (rows) |
|---|---|---|
| gold | 2870 / 2999 / 3188 | 2447 / 2691 / 3144 (44) |
| ecfinal | 2620 / 2712 / 2790 | 2440 / 2500 / 2670 (28) |

Anchors perform ~200–300 lower off the online rounds, consistent with the
DE audit's online offset (+102 binary points) plus selection (anchors were
picked on online form).

## Teams at the 50% line, and the cutoff in performance terms (2026-10-11 follow-up)

Scratch query (not shipped). Boundary teams: P in [0.4, 0.6] in
`output/anchor_teams.csv` — 25 at the gold line (geometric-mean online rank
94–127), 56 at the EC-Final line (#178–246). Their 2026 performances
(`performance_fit`, matched as above):

| line | EC Online 2026 perf, quartiles | other 2026 contests, quartiles (rows) |
|---|---|---|
| gold (P ≈ 0.5) | 2747 / 2836 / 2881 | 2343 / 2661 / 2851 (10) |
| EC-Final (P ≈ 0.5) | 2510 / 2618 / 2707 | 2432 / 2483 / 2663 (21) |

Cross-check against the real cutoffs: performance of the official
⌈10%⌉-th team and of official rank 75, on the 18 mainland 2023–2025
regionals in the fit with ≥ 100 official solvers: gold 2610 / **2712** / 2774,
rank 75 2415 / **2456** / 2556. The boundary teams' off-online performances
agree (2661 vs 2712; 2483 vs 2456). Their online-round performances run
~150 higher (online offset).

## CCPC sets on QOJ for a virtual strength test (2026-10-11 follow-up)

Request: which CCPC contests to use to test strength now; they must be on
QOJ. The 12th-season stations (Changchun 17–18 Oct, Jingzhou 7–8 Nov, Leshan
14–15 Nov, Xiamen 21–22 Nov 2026, per ccpc.io) have not happened, so the
candidates are past CCPC sets with a QOJ mirror in the fit:

| set | QOJ | Spearman of per-problem solves, QOJ vs onsite | onsite gold / ecfinal anchors | onsite teams at the gold / ECF 50% line |
|---|---|---|---|---|
| CCPC 2025 Jinan | 2693 (UCup "GP of Jinan") | 0.96 | 14 / 16 | 4 / 12 |
| CCPC 2025 Chongqing | 3387 (UCup "Chongqing") | 0.99 | 17 / 9 | 4 / 9 |
| CCPC 2025 Zhengzhou | 2661 (UCup "GP of Zhengzhou") | 0.93 | 10 / 12 | 2 / 11 |

The correlation confirms the UCup stages are the CCPC sets. CCPC 2025 Harbin
(QOJ 2575) holds one problem in the data (unusable). "GP of Nanyang" (QOJ
3727, April 2026, 13 problems) is probably the 11th CCPC Final; it has no
XCPCIO board and one anchor on QOJ, so it gives a calculator performance but
no anchor comparison. The 2026 CCPC invitationals (Nanchang, Qinhuangdao,
Guizhou) are not in the QOJ data. No NUM team played any of these sets.
Anchor counts: 2026-online rosters seen onsite (≥ 2 members), so these are the
2026 anchors' 2025 selves.

**Bug fixed.** CCPC boards mark accepted runs `CORRECT`, not `ACCEPTED`;
`regional_standings` counted only `ACCEPTED`, so every CCPC team scored 0
solved and `--board` comparisons on CCPC boards were wrong (overlap and anchor
counts were unaffected: they use rosters only). Now both count. ICPC boards
use `ACCEPTED` and are unchanged.

`--solved N --penalty M` (instead of `--team`) compares a virtual run with
the onsite anchors; e.g. Jinan, 6 solved / 800 min: beat 7 of 15 gold and 14
of 16 ecfinal anchors.

## Spoiler-free target places for a CCPC 2025 Jinan virtual (2026-10-11 follow-up)

Ranks only (scratch query; no solve counts reported to the user). Onsite
field 320 teams; QOJ 2693 field 413 (UCup teams, stronger). Cutoff
performances (2023–2025 medians and quartiles above) converted to ranks; for
onsite, each result gets the QOJ performance of the same (solved, penalty).

| line | onsite rank (q25 perf … q75 perf) | QOJ 2693 rank | onsite ranks of anchors / 50%-line teams |
|---|---|---|---|
| EC-Final (perf 2456) | **83** (99 … 63) | **149** (168 … 123) | ecfinal anchors median 84.5; ECF 50%-line teams median 101.5 (12 teams, 18–162) |
| gold (perf 2712) | **42** (55 … 33) | **94** (113 … 80) | gold anchors median 29; gold 50%-line teams 21/25/30/199 |

**Result (2026-10-11):** virtual 4 solved / 484 min → QOJ rank 164/413,
performance ≈ 2425; onsite-equivalent rank 95/320 (4-solvers span 84–140, so
any 5th solve lands ≤ 83). Onsite anchors beaten: gold 2/15, ecfinal 8/16 —
at the EC-Final line (target 83, range 63–99), below gold.
