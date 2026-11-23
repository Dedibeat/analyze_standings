# CCPC boards collected for experiments (2026-11-15, second entry)

**Request.** Did the pull include the CCPC boards? They are useful for further
experiments, and some CCPC contests are not on XCPCIO.

**Answer.** No — the release above is ICPC-only, so CCPC was not part of it. It is
now collected separately, research-only: nothing below is in the shipped fit,
calibration or any exported rating.

**XCPCIO** (`data/xcpcio_ccpc.json`, from `scripts/fetch_xcpcio_standings.py ccpc …
--min-year 2022`): **35 contests / 16,081 rows / 15,478 with rosters**, seasons
7th–12th (2022–2026). Covers the 8th station set (Guangzhou, Guilin, Mianyang,
Weihai), 9th (Guilin, Harbin, Qinhuangdao, Shenzhen, Xiangtan, Jiangsu&Xiangtan),
10th (Chongqing, Harbin, Jinan, Zhengzhou), 11th (Chongqing, Harbin, Jinan,
Zhengzhou, Northeastern, Nanchang), the 12th invitationals so far (Guizhou,
Nanchang, Qinhuangdao), the 7th/8th/9th finals, the girls'/vocational divisions
(8th girls, 9th girl, 9th vocational, 8th gaozhi) and the 8th/9th/10th/12th online
qualifications. 25 of the 60 indexed boards were skipped: 20 warm-ups by the
board-link filter, plus 10th-final, 11th-final and 11th-online, which XCPCIO does
not host.

**QOJ** (`data/qoj_ccpc.json`, fetched with the new `--output` flag of
`scripts/add_qoj_contest.py`): **10 contests / 9,455 rows** — exactly the series
XCPCIO lacks: **CCPC Changchun 2026 `4582` (939 rows, the only 2026 station
board anywhere)**, `4128` online 2026, the Women's divisions `4613`/`2564`/`1841`,
the Vocational divisions `2565`/`1842`, and the online rounds `2534` (11th, 2025 —
also missing from XCPCIO), `2530` (10th) and `2531` (8th). The last three overlap
XCPCIO's own online boards, so a consumer must pick one source per season.

**Caveats for anyone fitting this.** `11th/northeastern` carries **no rosters**
(0/397) in XCPCIO, so it can only link by team name; `9th/jiangsu-and-xiangtan`
has rosters on 268/472 rows. The 10th and 11th **finals are not here at all** —
they were hosted as Universal Cup stages and already live in
`data/ucup_s3.json` / `data/ucup_s4.json` (`2036`, `3727`), which is why
`scripts/ccpc_difficulty_rank.py` cites those QOJ ids. The 12th-season stations
(beyond Changchun) have not been played or uploaded yet. Both files use the
project's standings-only schema with synthetic ids (`fetch_xcpcio_standings`
hashes the board link to a negative id; QOJ keeps its own ids), so they can be
passed to `arch_a.load`/`arch_b.joint` alongside `tagged.json` without colliding.

Run:
`python3 scripts/fetch_xcpcio_standings.py ccpc data/xcpcio_ccpc.json --min-year 2022`
then, for each missing QOJ id,
`python3 scripts/add_qoj_contest.py <id> --name "CCPC …" --region "China Collegiate" --year <y> --output data/qoj_ccpc.json`.
