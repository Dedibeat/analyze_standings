# Public release, human feedback and a paper: research (2026-11-16, third entry)

**Request.** Research how to release the ratings and tags publicly "like
Mostafa", how to gain from it, how to build a human feedback system, and whether
release → feedback → paper is a workable order. Research only; no code, data or
product changed.

**Assumptions stated, not asked.**
- "Mostafa" was read as Mostafa Saad Ibrahim's public problem sheets
  (Codeforces blog entry 79231, 2020). Codeforces returned 403 to the fetcher,
  so his method is quoted from search excerpts, not the full post.
- The "noble man" of the joint item-response idea was read as Michal Forišek,
  "Using Item Response Theory to Rate (not only) Programmers", *Olympiads in
  Informatics* 3 (2009), 3–16 (PDF read in full).

**Found in the repositories (checked, not changed).**
- `Dedibeat/analyze_standings` and `Dedibeat/my-react-app` are both public on
  GitHub with no licence; `https://dedibeat.github.io/` answers 200. The
  ratings are therefore already reachable, only unannounced.
- Tracked and public: `data/tagged.json` (full problem statements, standings
  with member names), the UCup/Petrozavodsk/CCPC standings files, and the
  app's `canonical/tagged.json` (statements, no standings).
- Tags are LLM-written (`primary_tags`, `secondary_tags`, `extra_tags`,
  `confidence`, `evidence`); no human check of them is on record.

**External findings.**
- Mostafa Saad: difficulty 1–10 is "a manual weighted average of the assigned
  levels from my trainees' sheets", plus about five importance levels. A
  third-party tool read 5,711 rows from the public sheet on 2026-11-09.
- Forišek 2009: 2PL, individuals, 88 Slovak tasks / 300 contestants and 560
  TopCoder tasks / 12,000 contestants; open points named in its conclusion
  include abilities changing over time and arguing about hardness of past
  contests. No team contests, no rating-free linking across boards.
- solved.ac: only contributors set difficulty; tags come from the easiest
  solution; manipulation is penalised.
- *Olympiads in Informatics* 2026 cycle: proposal by end of February, full
  paper by 31 March 2026, research papers 8–15 pages, open access, peer
  reviewed. No 2027 call found yet (IOI 2027 is in Germany); fees, template
  and attendance rules are not on the call page.
- Not verified this session (from memory): funding models of AtCoder
  Problems, CLIST and Mostafa Saad's paid courses; whether CLIST already rates
  the same QOJ boards; QOJ's terms on reusing standings and statements.

**Recommendations given** (in the session reply; none carried out): clear the
statements/names/licence question and ask QOJ before announcing; ship ratings
with their standard error and small-board flag; collect human feedback blind
and keep it out of the fit so it stays a held-out validation set for the
paper; target *Olympiads in Informatics* for the 2027 volume.
