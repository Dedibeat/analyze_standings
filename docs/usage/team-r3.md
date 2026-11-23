# NUM-R^3 team data and coaching: running and reproducing

> Moved verbatim from `README.md` on 2026-11-20. Text may predate later changes; [docs/STATUS.md](../STATUS.md) is authoritative for what ships now.

## NUM-R^3 participations: team-account data (2026-11-04)

```bash
QOJ_USERNAME=Dedibeat QOJ_PASSWORD=... python3 scripts/fetch_team_r3.py 4071 4113 ...  # cache in data/team_r3/
python3 scripts/team_r3_participations.py      # output/team_r3_participations.{md,json}
```

`fetch_team_r3.py` uses the [shared QOJ session](qoj.md)
and stores TEAM_R3 submissions and visible source files, plus each contest's
dashboard, per-problem statements (the HTML problem page when QOJ refuses the
PDF) and all attachments (statements, tutorials), PDFs also as text. It also
saves the QOJ boards with and without unofficial rows. Files already on disk are
reused. On a server challenge or rate limit the fetcher stops so you can resume later.

Log in with a personal account: TEAM_R3 has QOJ Training Mode on, which hides
every board. The submissions read are always TEAM_R3's.

`team_r3_participations.py` lists the 14 virtuals and the 2 official 2026
online rounds. For each it gives TEAM_R3's exact QOJ row (solved, penalty) and
its rank against the official onsite field (`data/tagged_official.json`, the
UCup/Petrozavodsk files, or XCPCIO in `data/team_r3/boards/`). Per problem it
gives board solves, calibrated difficulty and the member who solved it
(`data/team_r3/members_solved.csv`, from the team's spreadsheet). Details are
in `docs/journal/`.

## NUM-R^3 coach review: problem dossiers, bug classes, plan (2026-11-04)

```bash
python3 scripts/team_r3_digest.py 4607            # problem table, medal/EC-Final lines, our runs by minute
python3 scripts/team_r3_digest.py 4607 E --code   # every attempt at E, with diffs between attempts
```

`output/team_r3_coach/<contest>.md` has one dossier per contest (the 16
participations of 11-04, plus Wuhan 2026 `4694.md`, written without statements): the idea and difficulty of every problem, our outcome and
member, every wrong run read and diffed, a comparison with the editorial, and a
timeline against the field. `output/team_r3_coach/summary.md` has the synthesis:
topics, the 68 penalised wrong runs by bug class, per-member profiles, strategy,
and a plan for Shenyang (2026-11-15), Hong Kong and EC-Final. The digest takes
the onsite field from XCPCIO for the 2026 regionals, the CCPC stations and the
2022 regionals, and from the QOJ board for the online rounds.
`1053_checks.py` and `2661_checks.py` are brute-force and UBSan checks of our
runs, kept as evidence. Details are in `docs/journal/`.

## NUM-R^3 members on Codeforces (2026-11-05)

```bash
python3 scripts/team_r3_cf.py            # analyse the cached API data (~6 s)
python3 scripts/team_r3_cf.py --fetch    # refresh data/team_r3/cf/ from the public API first
```

Covers Dedibeat, t4_4, erdene1231 and Munkh-Erdene.B: rated rounds, virtuals
and practice. It reports each member's level (the problem rating with a 50%
in-contest solve rate), the virtual-vs-rated gap at matched dates, topic
families against expectation, accuracy (first try, test-1 failures under CF
and ICPC rules, failed system tests), silent finishes, upsolving, practice diet
and compiler. Writes `output/team_r3_cf.json`; the write-up is
`output/team_r3_coach/cf.md`. Submission code is not fetched (Cloudflare blocks
submission pages). Details are in `docs/journal/`.

```bash
python3 scripts/team_r3_cf_rounds.py     # round by round against the official standings (~100 entries)
```

Uses each round's full official standings (the anonymous `contest.standings` call)
and, through `../codeforces_integration`, the editorial of the field's next problem.
For each round it shows the same-set tier, the next tier and their median minutes.
Virtual entries are placed by recomputing the score. Writes
`output/team_r3_cf_rounds.{json,md}`; the analysis of what each member fails and
solves, with practice lists, is `output/team_r3_coach/cf_rounds.md`. The caches
`data/team_r3/cf/standings/` and `editorials/` are gitignored.
