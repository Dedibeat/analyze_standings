# Shenyang J credited to Dedi

Dedi recalled the 2026 Shenyang onsite J as primarily a solo AC. Added his attribution to the member sheet under the onsite board ID. The team row records J accepted with zero wrong submissions. The shipped hierarchical rating is 2304.1, Dedi’s highest documented official solve. The updated tally is 22 individual ACs (median 1878.6), three at 2300+ and six additional paired ACs.

Reproduce the [updated calculation](2026-11-20-dedi-team-solves.md) from the repository root.

```bash
sed -n '/^python3 - <</,/^PY$/p' docs/journal/2026-11-20-dedi-team-solves.md | bash | tail -1
```
