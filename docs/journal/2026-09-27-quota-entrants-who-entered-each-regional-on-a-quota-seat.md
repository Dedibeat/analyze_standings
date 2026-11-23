# Quota entrants: who entered each regional on a quota seat, and why (2026-09-27)

**Question.** The online-gold model treats quota entrants as one pooled group
(ρ ≈ 0.44). Which teams are they, through which channel did each get its seat,
and what patterns do they show?

**Evidence** (`scripts/build_quota_evidence.py` → `data/ec_online/quota_evidence.json`).
Site notices (read in full for 2023–2025) list the non-online channels:
World Finals schools +1 (last three WFs), recent host and problem-setter schools
+2, invitational medal schools +1 (Xi'an, Kunming), non-mainland schools +1,
provincial/local contributors +1–2, girls' teams, and leftover wildcard
rounds. One official source per channel:

- WF schools: 46th/47th from the XCPCIO WF boards (English names mapped to
  Chinese), 48th/49th verbatim from the 50th Xi'an notice. 2023 uses 46th–47th
  (45th not on XCPCIO).
- Hosts: 2025 verbatim from the same notice; 2023–2024 from notices' venue or
  signature lines; a school counts in its hosting season and the next ("近二届").
  Not stated anywhere: 2023 Xi'an/Jinan and 2024 Chengdu hosts, and every
  problem-setter school.
- Invitational medal schools from XCPCIO: Xi'an 2023 (122; the notice says 124)
  and Kunming 2024 (98, exactly the notice's count). The 2025 Shaanxi
  invitational (used by Xi'an 2025) is not on XCPCIO.
- Local: official schools on the site province's XCPCIO provincial board
  (none for Anhui/Yunnan; Sichuan's board includes some guest schools).
- Ground truth: Shanghai's published per-school lists for 2024 and 2025
  (online seats, reward seats, total). These were found by crawling the
  icpc.pku.edu.cn notice index; they are the only per-school allocations
  published centrally.

**Method** (`arch_b.quota_teams`). Each school's band slots
(`online_gold.school_slots`) go to its strongest-online teams at the site; the
rest are quota teams. Quota teams take the school's channels in the order host
(2 seats), WF, invitational, non-mainland, local; girls' flag first; anything
left is *unexplained*. Which of a school's quota teams uses which channel is a
convention; school-level counts are not. Output: one row per official team
(`output/quota_teams.csv`, 6,473 rows) and `output/quota_teams.md`.

**Validation (Shanghai).** Inferred band slots equal the published online
seats for every attending listed school (151/151 in 2024, 159/159 in 2025;
140/146 and 145/152 before the name fix below). WF + host evidence explains
34/35 and 34/36 published reward schools; the rest are 齐鲁工业大学 2024 (0
online + 2 reward, probably a 2023 host) and 北京理工大学/杭州电子科技大学 2025
(2 reward each, presumably setters). Every Shanghai quota team is accounted
for: 2024 = 40 on published reward + 64 from schools not on the list + 39
above their school's published total (the later wildcard rounds); 2025 = 41 +
48 + 38 (sum 127 vs 126: 西北工业大学 sent 5 teams against a capped total of 4
from 2 online + 3 reward, so one team counts in both columns). So roughly 70% of
Shanghai's quota seats were never in the first-round list at all.

**Patterns** (2023–2025 mainland regionals, 18 contests):

| group | teams | gold rate | vs band | median online rank |
|---|---|---|---|---|
| band | 3,954 | 12.8% | 1.00 | 425 |
| WF school extra team | 371 | 18.9% | 1.47 | 360 |
| host extra team | 190 | 11.6% | 0.91 | 719 |
| invitational medal | 191 | 4.2% | 0.33 | 815 |
| non-mainland | 25 | 4.0% | 0.31 | — |
| local / provincial | 294 | 1.0% | 0.08 | 1,032 |
| unexplained (wildcards etc.) | 1,446 | 2.6% | 0.21 | 925 |
| all quota | 2,519 | 5.6% | 0.44 | 853 |

1. Quota seats are large: 39% of official seats (24–51% per contest; the
   invitational sites Xi'an 2023 and Kunming 2024 are ~50%).
2. The pooled ρ = 0.44 averages two different populations. Elite channels
   (WF, host) beat or match band teams; mass channels (invitational, local,
   wildcard) win gold at 0.1–0.3× the band rate.
3. What decides whether a quota team contends is its **school**, not its
   channel: 127 of 142 quota golds (89%) come from schools ranked top-50 in
   the combined online ranking; schools ranked below 100 took 3 golds from
   1,315 quota teams (2 more from 81 teams of unranked schools), and schools
   with no band slot at the site took 4 golds from 1,074. Within top-50 schools, quota teams win gold at 17.7% vs 27.3%
   for their band teams (they are the school's 3rd/4th teams).
4. A handful of schools own the quota golds: 北京大学 32 of 35 quota teams won
   gold, 清华大学 15/17, 浙江大学 14/23 — 61 of 142 (43%) from three schools.
   Host extra teams of non-elite hosts almost never do (南京航空航天大学 0/28,
   杭州师范大学 0/30, 西北工业大学 0/37 over all its quota teams).
5. Channel mix is site-specific: invitational sites fill ~90–100 seats from
   the spring invitational; Hangzhou/Nanjing/Jinan give 18–31 seats to local
   schools; every site gives WF schools ~16–26 seats; wildcard/unexplained is
   the largest group everywhere (Xi'an 2025's 155 includes the ~120 invitational
   seats whose board is missing).
6. Predicting each contest's quota golds leave-season-out (MAE, golds per
   contest): pooled ρ 2.04, by channel 1.78, by school combined online rank
   (≤50 / ≤100 / >100 / none) **1.58**, by the team's own online rank 2.18
   (a third of quota teams never link to an online team). A quota adjustment
   for the rules line would do better by counting a site's quota seats from
   top-50 schools (WF/host seats) than by applying one ρ; not implemented here.

**Fixes to `arch_b.online_gold` found on the way** (both affect quota labels):
(1) `norm_school` stripped parenthesised campus names, merging distinct schools
(哈尔滨工业大学 / (威海) / (深圳), 香港中文大学 / (深圳), 中国石油大学 北京/华东,
山东大学 / (威海), …) and pooling their slots and online teams. It now keeps
the qualifier, strips only 齐鲁工业大学's "(山东省科学院)" long form, and folds a
few traditional characters (香港中文大學). (2) Roster-vote ties in
`link_regionals` were broken by set order, so ρ varied 0.440–0.444 with
`PYTHONHASHSEED`; ties are now broken deterministically. Effect on the shipped
online-gold outputs (regenerated): ρ 0.443 → 0.441; quota-adjusted rules line
Δ log loss 2024 −0.0005 → −0.0003 [−0.0007, +0.0001], 2025 −0.0016 →
−0.0015 [−0.0041, −0.0001]; 2026 order unchanged (Shenyang #89 > Wuhan #79 >
Xi'an #75 > Shanghai #74 ≈ Nanchang #73 > Chengdu = Nanjing #69); a team at
online #100 loses 1–2 points everywhere; NUM-R^3 now 3.4–4.8% (Shenyang
highest). NUM itself did not enter the online rounds in 2023–2025, so its
regional teams in those seasons are correctly non-mainland/wildcard quota
entries.

**Gaps.** No per-school allocation outside Shanghai; setter schools, three
host schools, the 45th WF list and the 2025 Shaanxi invitational are missing;
Hefei/Kunming have no provincial board; Hong Kong/Macau are excluded (their
fields are registration-based).

Run: `python3 scripts/build_quota_evidence.py` (network, `pdftotext`) then
`python3 -m arch_b.quota_teams`. Tests: `tests/test_quota_teams.py`.
