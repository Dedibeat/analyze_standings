# Shenyang 2026 — 51st ICPC Shenyang regional, onsite, 2026-11-15

The first onsite contest of the season, so the first real measurement after 14 virtuals.

Sources and limits:
- **Board:** XCPCIO `icpc/51st/shenyang`, 401 official teams, with every team's runs. Read with
  `scripts/team_r3_onsite.py /icpc/51st/shenyang`. Minutes are contest minutes; penalty is the
  board's (seconds summed, 20 minutes per wrong run before the AC).
- **Members and the story of the contest:** Dedi's account (2026-11-16). Tamir and Erdene have not
  given theirs.
- **Missing:** the statements, the editorial and our onsite code. The set was not on QOJ at the
  2026-11-15 pull and nothing was saved in the repo. So this dossier has no per-problem ideas and
  no reading of our code; "C is a DP" and "J is an offline segment tree" are Dedi's words.
- `members_solved.csv` has no Shenyang 2026 rows: `team_r3_participations.py` needs a QOJ contest
  id in the sheet's contest name, and the set has none yet.

**Result:** 5 solved (C D H J L), 647 min, **#87 / 401, a silver medal** (40 gold, 80 silver,
120 bronze: silver is #41–#120).

## Lines (official board)

| line | rank | scoreline | set |
|---|---|---|---|
| last gold | #40 | 7 / 1169 | ACDFHJL |
| six solves | #44–#62 | | ACDHJL ×8, CDFHJL ×7, ACDFHL ×4 |
| 2026 EC-Final estimate (~81, range 77–84; re-estimated 2026-11-16 from the five finished sites, was ~75) | #81 | 5 / 604 | CDHJL |
| **us** | **#87** | **5 / 647** | CDHJL |
| last silver | #120 | 4 / 328 | CDHL |
| last bronze | #240 | 3 / 222 | DHL |

- **Six ranks and 43 minutes outside the EC-Final estimate.** The estimate was re-made on
  2026-11-16 (`scripts/ecfinal_cutoff_2026.py`, details.md): the seat rule replayed on the five
  finished sites, plus what Shanghai and Nanchang should add, puts the last seat at rank ~81
  (77–84). A seat at #87 needs those two sites to admit at most 10 new teams within their top 86;
  the smallest such number in 2023–2025 is 18. So a direct seat from Shenyang is unlikely. The
  real answer comes after Nanchang (12-19).
- **Gold needed 7 problems** (32 of the 33 seven-solvers had ACDFHJL). Gold was never in reach;
  the 6th problem (A or F) was worth #58 at the latest minute.
- **J made the medal silver.** With four problems we were 4 / 393 = #139, a bronze.
- We solved the field's standard set for our count (CDHJL: 33 of the 44 five-solvers), as in the
  virtuals.

## Timeline

| min | event | rank after |
|---|---|---|
| 11.1 | L AC (Dedi), first try | #91 |
| 64.7 | D AC (Erdene), first try | #96 |
| 129.6 | C AC (Dedi), first try. Erdene had it first and did not see the DP | #129 |
| 138.1 | H WA (Tamir) | |
| 167.7 | H AC (Tamir) | #106 |
| 168.4 | H AC again, 43 seconds later (a second submission of an accepted problem) | |
| 253.9 | J AC (Dedi, with Erdene debugging), first try. Erdene had it first and did not see the offline segment tree | #73 |
| 295.8 | F WA (not solved; who submitted is not recorded) | final #87 |

- 60 minutes after the start we still had one problem (#191 at that moment).
- From 168' to 254' there was no submission: Dedi and Erdene were on J, and F was open.
- Dedi asked Erdene to take F with Tamir. By Dedi's account Erdene had lost confidence after C
  and J and stayed on J with him.

## Against the field

Median solve minute among the teams of each medal tier that solved the problem (count in
brackets), and the share of solvers who got it first try.

| problem | solved / tried | first try | gold | silver | bronze | ours |
|---|---|---|---|---|---|---|
| L | 398 / 401 | 79% | 10 (40) | 12 (80) | 14 (120) | 11.1, first try |
| D | 387 / 399 | **17%** | 41 (40) | 51 (80) | 62 (120) | 64.7, first try |
| H | 357 / 381 | 61% | 83 (40) | 105 (80) | 131 (120) | **167.7, +1** |
| C | 229 / 319 | 62% | 60 (40) | 112 (80) | 197 (105) | 129.6, first try |
| J | 93 / 188 | 45% | 131 (40) | 251 (51) | 243 (2) | 253.9, first try |
| F | 60 / 124 | 47% | 146 (40) | 215 (20) | — | 1 wrong run at 295.8 |
| A | 59 / 81 | 51% | 184 (40) | 229 (19) | — | not submitted |

B, E, I, M: 3–6 solves each; G, K: none. Correct skips.

The 33 teams that finished with the same five problems:

| | the 33 CDHJL teams (median) | us |
|---|---|---|
| C, D, H, L all done | 143' | 168' |
| J accepted | 253' | 254' |
| wrong runs on solved problems | 4 | **1** |

## What the board says

1. **This was our cleanest contest, and Dedi's cleanest.** One penalised wrong run in five solves;
   the virtuals averaged 4.9 per contest (68 in 14). Dedi: three solves, three first tries,
   including the two hardest we solved. The teams around us made four wrong runs. D went in first
   try (Erdene) where 83% of the field needed more than one run.
2. **We lost on speed, not on accuracy.** Against the gold medians we were ×1.6 on D, ×2.2 on C,
   ×2.0 on H and ×1.9 on J. The virtuals ran at ×1.3–1.9. This repeats the official online rounds
   ("more careful but much slower", summary §5) and confirms that the virtual results were an upper
   bound: #87 of 401 is the 22nd percentile, the same as the Xi'an 2026 virtual (#86 / 402) and
   twice the Chengdu virtual (#35 / 319).
3. **H is the gap to the EC-Final estimate.** H was the third-easiest problem (357 solves). Our first run on it came
   at 138', when half of its eventual solvers already had it, and the AC at 168' was later than the
   bronze median (131'). Against our own tier that is 63 minutes late plus the 20-minute wrong run.
   - H first try at 138' → 5 / 598 → **#81, the estimated last seat**.
   - H clean at the silver median (105') → 5 / 565 → #75.
   - Why H was this late is not known (open questions). It was submitted 8 minutes after C's AC,
     which suggests it was waiting for the keyboard.
4. **C and J were not slow by our tier's standard.** C at 130' is 18 minutes behind the silver
   median; J at 254' is on it. After C, D, H, L the same-set teams needed 89 minutes for J and we
   needed 86. The two handovers from Erdene to Dedi both ended in a first-try AC.
5. **The 6th problem had one person on it.** A and F were equally solved (59 and 60), and the
   six-solvers split evenly between them. 21 of A's 59 solves and 10 of F's 60 came in the last
   hour. A converted better (59 of 81 teams that tried it, against 60 of 124 for F). Our only run
   on either was F at 295.8'.
6. **Load.** Dedi 3 of 5 (L, C, J), Erdene 1 (D), Tamir 1 (H). This is the overload pattern of
   4593, 1799, 4113 and 1053 (summary §4), now onsite.

## The opening pattern: Erdene takes a hard problem early

The team's usual plan: Erdene gets a harder problem early while Dedi and Tamir clear the rest.
Dedi credits it for the Chengdu virtual (59 minutes from gold).

- **What Chengdu actually shows.** Erdene's four solves there were the two easiest problems (M, D)
  and the two interactive/communication problems (I, H): his best category, 3 of 3 first try over
  the season. The plan worked because the mid problems were his type.
- **Shenyang's mid problems were not his type.** C was a DP; on Codeforces his wall is DP state
  design (`cf_rounds.md`: 2174 B, 2190 B2). J was an offline data-structure problem. The plan in
  summary §6.5 made him the data-structure owner on the evidence of one problem (2693 L); J is the
  first evidence against that.
- **The weak point is not the miss, it is the missing clock.** A plan that rests on one member
  hitting needs a fixed moment at which the problem is explained aloud and handed over. Rule 3 of
  §6.3 has it (25 minutes without a submission → a second reader; 45 minutes stuck → switch).
  When C and J changed hands is not known (open questions).
- **After a miss he stops attempting.** This is the same behaviour as in his Codeforces data: he
  attempted the field's next problem in 2 of 21 rounds, and 32 of 63 virtuals have no submission
  after half-time. So it is a habit to train, not a one-off. Asking him to start a third problem
  cold after two misses was the hardest thing to ask for; that he stayed on J is understandable.
- **Staying on J was not the loss.** A second reader on the last open problem is the rule in §6.5,
  and J went in first try. The loss was that A/F had one person from 168' on.
- **Dedi's call (Erdene and Tamir on F) was the right one by the board.** It needs to be a
  standing rule, so that nobody has to be persuaded in the fourth hour.

## Health

Dedi had an allergic reaction to an insect bite in Shenyang: a hormonal injection, then ebastine
in the morning and bismuth potassium citrate in the evening. Tamir was bitten after the contest.
- The board shows no sign of it in Dedi's work (three first-try solves), but thinking speed cannot
  be read from a board, so the effect is unknown.
- For Hong Kong: finish the course as prescribed, ask the doctor whether to carry an antihistamine,
  and pack repellent. This is a travel checklist item, not a coaching finding.

## What changes for Hong Kong (HKU, 2027-01-09/10 by the notice; an EC-Final place needs about rank 21–25, re-estimated 2026-11-16; was 32–37)

Keep: the opening (first AC at 11'), the pre-submit checklist (1 wrong run), a second reader on
Dedi's last problem.

1. **Assign mid problems by type, with a clock.** No "hard problem for Erdene" by default. The
   owner of the category takes it. At 30 minutes without a solution he can state in two sentences,
   he explains the problem to a teammate; at 45 minutes it changes hands.
2. **The keyboard goes to the most-solved open problem that has a complete solution.** Everyone
   else writes on paper. (To be checked against why H waited.)
3. **Two on the next problem while the closer codes.** From the moment Dedi starts the last
   standard problem, Tamir and Erdene pair on the field's next one (most-solved on the board, then
   best conversion). One of them reads Dedi's diff before each run, for at most 15 minutes.
4. **Erdene after a miss:** a fixed next job, so that a miss is not the end of his contest: first
   the cold read for the closer, then the next problem with Tamir. In training: every virtual
   played to the end, and a submission on the field's next problem in every round (already in
   summary §6.4; now his first item).
5. **Speed on the easy-mid problems is the main training target**, ahead of new topics: it is
   what separated #87 from the EC-Final line here. All virtuals on one computer, as onsite.
6. **Topic weeks** (summary §6.1) stay, with two additions from this contest: DP state design
   and offline data-structure techniques for Erdene. Problem lists follow once the statements are
   in the repo.
7. **Upsolve this set first:** F and A (all three), C and J from scratch (Erdene), H (Tamir, until
   the wrong run is explained).
8. **Incentive seat.** If the allocation after Nanchang leaves NUM without a seat, the rule lets a
   school apply for one of up to 10 incentive seats, judged on regional results (details.md
   2026-10-08). A silver at #87 is the result to cite. Deadline and form are not known here.

## Open questions

1. **Statements, editorial, our code.** Can the PDF be shared, or the QOJ id once the set is
   uploaded? Was any onsite code saved?
2. **H:** when did Tamir start it and when was it ready? Was it waiting for the keyboard while C
   was typed? What was the wrong run, and why did the fix take 30 minutes? Who submitted the second
   AC at 168.4', and why?
3. **D:** who read it, and why 65'? What was Erdene doing between 11' and 65' besides D?
4. **Handovers:** at what minute did C and then J move from Erdene to Dedi?
5. **F at 295.8':** whose run, and what was the idea? Did anyone read A?
6. **Setup:** are the virtuals played on one computer? Who typed between 168' and 254'?
7. Tamir's and Erdene's own accounts of the contest.
