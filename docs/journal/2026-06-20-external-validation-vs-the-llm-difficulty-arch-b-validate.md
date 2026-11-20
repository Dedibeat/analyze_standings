# External validation vs the LLM difficulty (`arch_b.validate`)

`tagged.json` carries an LLM `difficulty_estimate` (easy / medium / hard /
very_hard) per problem, written by the sibling `llm-integration` tagger from the
problem **statement** — independent of the standings both estimators use. We trust
it only on **editorial-backed** contests (128 of 146 contests, 1066 of the rated
problems): the LLM label is reliable enough to validate against only where an
editorial shipped. All three architectures' difficulty rises monotonically across
every bucket:

| LLM bucket | n   | arch A | arch B binary | arch B survival |
|------------|-----|--------|---------------|-----------------|
| easy       | 317 | 1618   | 1440          | 1782            |
| medium     | 230 | 2058   | 1942          | 2032            |
| hard       | 247 | 2382   | 2210          | 2153            |
| very_hard  | 272 | 2948   | 2535          | 2318            |
| **Spearman** |   | **+0.908** | **+0.874**  | **+0.880**      |
*(medians per bucket; Spearman over all 1066 problems)*

After the contest deduplication, **arch A now agrees most** with the
editorial-informed ranking (+0.908) — removing the double-counted rows sharpened
its solve-count-driven estimate substantially (it was +0.792 before the fix). The
two IRT fits are essentially unchanged (the duplicates barely moved their MAP) and
remain close behind, with the survival model (which also uses solve *times*) ahead
of the binary Rasch. So on the LLM check arch A leads, while on the Codeforces
numeric checks below the IRT fits stay ahead — the architectures are now closely
matched rather than IRT dominating. (Restricting to editorial-backed problems
*raised* binary arch B's agreement from +0.844 on the full set to +0.874 — the
no-editorial labels are genuinely noisier.)
Run: `./.venv/bin/python -m arch_b.validate`.
