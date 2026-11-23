# NUM-R^3 coach review: dossiers, bug classes, strategy (2026-11-04, second entry)

**Request.** Act as the team's coach: read every problem of the 16
participations (statement, editorial, all our runs), write a dossier per
contest, rebuild each timeline, then synthesise strengths and weaknesses, bug
classes, per-member profiles and a plan. Step 0 (shortest public ACs) was
skipped at the user's request.

**User facts given during the work.**
- Erdene was absent at Jinan 2022 (1053), not at Jinan 2025 (2693). The
  sheet's note is moved in `members_solved.csv`; the ODS should get the same
  fix.
- In a sheet pair "A + B", A proposed the idea and B most likely implemented
  it.
- NUM-R^3 is accepted to Shenyang (2026-11-15) and Hong Kong (~2027-01-07/08).
  EC-Final is 2027-01-22/23.
- 4071 A: Dedi made the four wrong tries; Erdene took it over and got AC first
  try. This is noted in the sheet copy's "Additional info" and should be
  mirrored in the ODS. Erdene's record becomes 12 first-try solves and 13 wrong
  tries. It is the season's only recorded handover after a stall, and it
  worked; summary §5 and §6.3 cite it.
- (2026-11-05) Dedi was the one attempting 4607 E, 1053 C and 1071 M. With
  2661 J (already Dedi's in the sheet), all four problems with in-contest runs
  that we never solved in the 14 virtuals are his: 11 runs (E 5, C 2, M 2,
  J 2; checked against `submissions.json`). The sheet copy gets three rows in
  the style of the 2661 J row ("Didn’t solve during contest"), so
  `team_r3_participations.json` lists them under `sheet_only`, like J. The ODS
  should get the same rows. The per-member "wrong runs" column still counts
  solved problems only; the 11 runs are noted beside Dedi's. Summary §6.5 now
  has Dedi as geometry backup (the only geometry attempt, the right approach)
  and a rule for the last open problem: a teammate reads the diff or runs the
  brute force before each run.
- (2026-11-05, later) Further answers:
  - 4071 F and M (bonus problems) were solved by Dedi and Erdene; which took
    which is not remembered. The sheet copy says "Dedi or Erdene", so neither
    member's individual stats include them.
  - 4071 A: Dedi's four runs were a wrong idea or an implementation too
    complicated to get right.
  - 4113 A was Dedi's: the start was right (an XOR linear basis), then the idea
    went wrong. Dedi took A and D because Erdene and Tamir were stuck on them.
    He suspects a type mismatch somewhere but did not say whether in A or D,
    and when asked he did not pin it down, so the dossier records it as
    unattributed. XOR basis is therefore "half there", not a gap nobody covers;
    the code is on the other account.
  - Tamir worked on J with Dedi at 4593 and joined late at 1799 (the user
    confirmed which way round). 4593 J (95 min) and 1053 A (100 min, Tamir's
    idea, Dedi's code) had two people on them, so the summary no longer calls
    them solo stalls. That earlier label on 1053 A was my error; the sheet
    already had it as a pair.

**Script.** `scripts/team_r3_digest.py` (new) prints one contest's problem
table:
- field solves on the onsite official field;
- the top group's median solve time;
- our status and member;
- the medal and EC-Final (≈ 75) lines and our rank on that field;
- our runs by minute (start recovered from the board row);
- optionally every attempt at a problem with diffs.

Field choices:
- XCPCIO official for the 2026 regionals.
- The cached XCPCIO CCPC boards for 2575/2661/2693. QOJ's "official" CCPC rows
  are not the onsite field: Harbin has 343 there vs 260 official onsite.
- XCPCIO rows of `regional_teams.csv` with medals 35/70/105 for the 2022
  regionals (the 2026-10-05 diagnosis). QOJ's 2022 "official" rows are larger
  sets: Shenyang has 1004 vs 708.
- QOJ for the online rounds, using the NUM-R^3 row for 4071/4113.

Bugs found while building it:
- A verdict string "AC, WA" (a failed run on QOJ) was first read as an AC,
  which shifted 1794's minutes by 55. It now requires `AC ✓`.

**Ranks on the onsite fields differ from the 2026-11-04 first pass** (which
used other boards). On the right field:
- Hangzhou 2022: #19 / 556, gold.
- Xi'an 2022: #106 / 476, 5 min from silver.
- Jinan 2022: #92 / 511, silver.
- Shenyang 2022: #88 / 708, silver.
- CCPC Harbin: #118 / 260, bronze.
- CCPC Zhengzhou: #127 / 260, bronze.
- CCPC Jinan: #80 / 260, bronze (silver ends at #78).

**Main findings** (`output/team_r3_coach/summary.md`).
- **Problem sets.** We solve the field's standard set for our count almost
  every time. The rank comes from penalty and from the 6th/7th problem.
- **Wrong runs.** 68 penalised wrong runs in the 14 virtuals (1360 min). Each is
  classified, and the per-contest counts equal the boards' wrong tries. By
  class:

  | class | runs |
  |---|---|
  | unproven idea | 14 |
  | casework | 11 |
  | memory/time not estimated | 10 |
  | structure misuse | 8 |
  | edge parameters | 7 |
  | blind resubmission | 6 |
  | overflow/sentinel | 5 |
  | debug leftovers | 4 |
  | misread constant | 3 |

  One-line fixes would have crossed a medal or EC-Final line in 5 of the 9
  regional/CCPC virtuals. Example: Chengdu 2026, where the modulus and the
  overflow are exactly the 60 min to gold.
- **Silent finishes.** 7 of 14 virtuals had 80+ minutes with no submission at
  the end.
- **Members.** Erdene goes 3/3 first try on interactive problems. Dedi carries
  the most problems, and his bugs are constants and sentinels. Tamir has the
  best pace and no recorded solve at 4593/1799.
- **Library gaps.** No flow, geometry, XOR-basis or interpolation code in 179
  submissions.
- **Official vs virtual.** The official 2026 online rounds ran at pace ×1.55
  vs ×1.25 in the online virtuals.

**Verified by testing.**
- 4607 E: our final code plus two local fixes (orientation-safe triangle test,
  no sorting of output vertices) passes 14,000 random cases against a brute
  force. Scratch harness, not in the repo.
- A parallel agent (Codex), stopped by the user, wrote
  `output/team_r3_coach/{1053,2661}_checks.{py,json}`. These are brute-force
  and UBSan checks; they confirm the 1053 A/E/C and 2661 B/G/J/M diagnoses and
  are kept as evidence.
- Its own versions of 1053.md, 2661.md and 4113.md were overwritten by this
  session before the overlap was noticed. They were untracked and are lost.

**Data notes.**
- The QOJ virtual board sometimes counts one try fewer than the account's
  in-contest runs: 4607 E 4 vs 5, 2661 J 1 vs 2, 1053 C 1 vs 2. The dossiers
  give both numbers.
- 1794 L's AC was found with GPT's help (sheet note); the dossier reports the
  rank without it, #136.
- 1051, 1485, 2513, 2524, 2575 (and 4071 F/M) have no member data. 31 solves
  are marked unknown, and the open questions are listed in the summary.

**Plan.** The plan in the summary (§6) is phased around those dates. Its §6.5
gives a specialisation split, asked for by the user:
- Erdene: interactive, data structures, graphs and flows, the opening.
- Dedi: maths, number theory and bits, counting, strings.
- Tamir: geometry, constructive, long implementation.

Each category has a backup. Dedi gives ideas and Tamir types (the 1071 K
pattern). The summary is published as a private artifact:
https://claude.ai/artifact/4i24BaGeoogkxfA45ZTjp7.

**Not done.** Step 0 (shortest public ACs). The library comparison uses
editorials and our own code only.

Run: `python3 scripts/team_r3_digest.py <contest> [<problem> --code]`.
