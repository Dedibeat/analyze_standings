# Recent Codeforces A/B teaching selection (2026-11-09)

**Request.** Find clean, tricky recent Div. 2 A/B material for greedy, DP or
DC, with precise, simple proofs. The user specified a general audience. The
requested recency window and meaning of DC remain unconfirmed; the report
explicitly bounds this first pass to the 20 latest finished rounds containing
“Div. 2” in the official name, including Educational and combined rounds
(2026-08-01–2026-11-07). No divide-and-conquer recommendation was found.

**Artifact.** `cf_div2_teaching.md` recommends 2276A Perfect Sandwiches as a
warm-up, 2269A SauSaGe Bank for an exchange proof, 2274B Prefix for extrema DP,
2248B Merge to Match for disjoint-witness/sorted greedy reasoning, and 2256B
Domino Tiles as a DP-to-four-patterns discovery exercise. Each has a proof,
complexity, teaching prompt or role, and a common trap. Metadata came from the
live official contest API; A/B statements including split versions were read
using the existing sibling Codeforces scraper. Proofs are independently
derived, not attributed to an unread editorial. The report records source
links and all inspected contest IDs.

**Verification.** `python3 scripts/check_cf_teaching.py`: 78 withdrawal-
schedule cases, 19,525 Prefix arrays, 9,837 ternary tile strings and 12,150
Merge to Match instances pass independent exhaustive small-domain checks.
The mathematical proofs cover the full constraints; finite enumeration is
supporting evidence. No production rating, dataset, or model changed.
