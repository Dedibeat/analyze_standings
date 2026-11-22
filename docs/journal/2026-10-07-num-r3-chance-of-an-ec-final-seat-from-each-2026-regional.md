# NUM-R^3: chance of an EC-Final seat from each 2026 regional (2026-10-07)

**Model** (`scripts/ecfinal_chance.py`, needs numpy + pypinyin):
`logit P(rank ≤ K) = a + b x + c log K + d x log K` on 2023–2025 mainland
teams linked to their online results (`online_gold.link_regionals`, x = −mean
log online rank), thresholds K = 10…160. Qualifying at a site = rank ≤ the
projected 2026 qualifying rank (K = 70/75/80 weighted ¼/½/¼; one team of a
school with few seats is never skipped). Absolute rank rather than percentile
of the field: in the 2025 backtest (train 2023–2024) percentile badly
under-predicted the grown Shenyang/Xi'an fields (62/64 expected vs 87/86
actual teams above the cutoff); rank totals 503 expected vs 520 actual, with
real site-strength scatter (Wuhan 107 vs 86, Shenyang 75 vs 87). By online
band: #1–150 93% vs 94%, #151–400 46% vs 55%, #401–800 11% vs 10%, #801+ 3% vs
1%. Mainland sites therefore get one number; site differences come from the
attending field, unknown before registration.

**Hong Kong** (2026 rule: ≤10 places, medal teams, skip teams registered in
round 1 and capped schools): replaying 2024/2025 boards, the 10th place falls
at rank 37 / 32 (registered = replayed mainland qualifiers; reward/incentive
teams not known, so slightly shallow). Under this rule NUM's N^3 (HK 2025 #30)
would have taken a place. P(rank ≤ 32–37) uses the same model fitted on Hong
Kong linked teams.

**NUM-R^3** (online #544 / #349, geometric mean #436), P(qualify | attends):

| site | P | 10–90% (model) | K = 70 / 80 |
|---|---|---|---|
| any one mainland site | 13.8% | 12.4–15.1% | 11.7% / 15.9% |
| Hong Kong | 19.0% | 17.2–21.4% | needs HK rank ≤ 32–37 |

Two sites are correlated: among 2023–2025 teams at online #400–700 that played
two mainland sites, "at least one" was 22.9% vs 13.3% per site (independence
24.8%), ≈1.7×. So two mainland sites ≈ 22–24%; mainland + Hong Kong ≈ 27–30%.
Not in the model: member history (Tamir: Nanjing 2025 #168, HK #39/#42;
Dugarjantsan: Shanghai 2025 #209, HK 2025 #30), which points slightly lower on
the mainland and supports the Hong Kong route; the projected K's own error.

**Member history check (2026-10-07).** NUM had no 2025 online rows (only Inner
Mongolia schools), so NUM's online-vs-onsite gap can't be measured. N^3 (2025:
Shanghai #209, HK #30 silver) shares one member with NUM-R^3 (Dugarjantsan
Bilguun). Over 2024–2025 mainland entries at online #300–600, 16.3% reached
rank ≤ 75 (947); with the best member's previous-year mainland rank 130–250
(R^3: Tamir #168, Dugarjantsan #209) 10.4% (307). So R^3's mainland chance is
nearer **~10%** per site than the online-only 13.8%. Hong Kong: members' HK
ranks 30 / 39 / 42 sit at the needed ≤ 32–37; 2/6 HK 2025 teams with a member
at HK 2024 #20–50 finished ≤ 35 (too few to fit), so ~20–30%.

**NUM at the 2025 EC-Final (2026-10-07).** NUM is in neither the 12 Dec 2025
公示 (first allocation, Tables 1–2) nor the EC-Final board
(`board.xcpcio.com/icpc/50th/ecfinal`: 306 teams, 280 official). The coach
reports N^3 was invited from Hong Kong 2025; that would have come through the
channels outside the first allocation — the second registration round
(6–10 Jan 2026, leftover seats, per the 18 Dec invitation notice) or a 推广名额
applied for by email — which are not published, and the invitation was
evidently not taken up.
