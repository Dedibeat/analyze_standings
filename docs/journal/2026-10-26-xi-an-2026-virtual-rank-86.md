# Xi'an 2026 virtual: rank 86 (2026-10-26)

**Report.** The user: NUM-R^3 placed 86th in a virtual of the 51st Xi'an
regional (onsite 10-17). No scoreline was given. "86" is read against the
XCPCIO board `icpc/51st/xian`: 418 teams, 402 official, medals 41 / 82 / 123
(board counts).
- If 86 is the overall rank: 4 solved / 511 min, official-equivalent #81.
- If it is the official rank: 4 / 536.
Both readings give the same conclusions.

**Placement.**
- The set was a 4-solve plateau. Only 13 official teams solved 5 or more,
  and ranks 14–153 all solved 4. A fifth problem would have been gold, inside
  the top 13; among 4-solvers, penalty decides.
- Lines at 4 solved: gold (#41) at ≤ 405 min; the 2026 EC-Final estimate
  (#75, plausible 70–80, 2026-10-01) at 502 min; silver to #123 at 709 min.
- The virtual is a **silver**, just outside the EC-Final line: 9 min (or
  34 min) of penalty behind #75, i.e. one or two fewer wrong submissions. It
  is 106–131 min from gold.
- NUM's best real mainland ranks were 116 (Hangzhou 2024) and 168 (Nanjing
  2025).

**Anchors** (`scripts/anchor_teams.py --board icpc/51st/xian --solved 4
--penalty 511|536`):
- gold anchors present 11, beaten 0;
- EC-Final anchors present 15, beaten 6 (5 at 536 min).
- So: at the EC-Final line, below gold, the same reading as the CCPC Jinan
  virtual of 10-11.
- All tiers are still predicted. `regional_teams.csv` has no 51st-season
  rows yet, so the actual-result override does not fire.

**Hong Kong registrants who played onsite** (10-26 list, matched by school +
≥ 2 members):
- **Xi'an:** 9 registrants, the best 四川大学 渡川 at #107 (4 / 618). Then
  广东工业大学 #129, CUHK 慶曆四年春 #137 (a local team with no online result;
  this is its first measurement) and 西南财经大学 #143. The virtual beats all 9
  under either reading.
- **Chengdu** (`icpc/51st/chengdu`, 10-24; 319 official, medals 32 / 64 / 96):
  - 香港中文大学（深圳） Mynoghra gold #21 (6 solved);
  - SUSTech-Ok silver #87 (5 solved; first measurement of this unlinked
    team);
  - 杭州电子科技大学 2026杭电负1队 played unofficially, 7 solved;
  - 4 more registrants at #178–237.

**What it means for Hong Kong** (online-rank equivalent; scratch query, not
shipped):
- 203 of the 402 official Xi'an teams link to 2026 online results.
  Regressing x on log official rank (r = −0.81) gives the typical online rank
  of a team placing there: #75 → online #315, #81 → #335, #86 → #351. The
  linked teams placing 70–90 have median online #359.
- NUM-R^3's online average is #436 (round 2 alone: #349). So the virtual
  reads as a team about one online-round step stronger.
- Hong Kong absolute model:

  | strength | gold | silver | bronze |
  |---|---|---|---|
  | online #436 (current) | 1.3% | 34% | 46% |
  | Xi'an #86 equivalent (#351) | 2.2% | 43% | 41% |
  | Xi'an #81 equivalent (#335) | 2.5% | 45% | 40% |

- **Caveat: a virtual is not onsite form.** Earlier measurements: the online
  virtuals ran ~2× stronger in rank terms than the official 2026 rounds
  (2026-10-08). The same scoreline reads up to ~100 CF points lower as a
  virtual entry (mirror advantage, 2026-10-13). So read the table as an upper
  bound: silver-or-better somewhere between ~36% and ~47%, gold ~1–2.5%.
  Either way, the medal band does not change.

**Fix in shared code.** `scripts/anchor_teams.py` had crashed since the
10-11 merge (`KeyError: 'h'`). Since 10-08, `ecfinal_chance.fit` uses
members' history by default, and `official_ranks()` returns (rank, members).
The anchor tiers were defined on the online-only model, so `ecfinal_model`
now fits with `use_h=False` and takes the rank from the tuple. NUM-R^3 again
gets the documented 13.8% EC-Final / 3.4% gold; tiers are 88 gold and 83
EC-Final. A new test, `test_ecfinal_model_uses_online_rank_only`, runs the
model end to end; the old tests never called it.

**Not done.** `regional_teams.csv` was not rebuilt with the 51st-season
boards (Xi'an 10-17, Chengdu 10-24). That rebuild would turn on the anchors'
actual-result tiers and let the Hong Kong EC-Final skip rule see which
registrants already hold mainland seats.
