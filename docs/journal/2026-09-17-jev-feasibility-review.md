# Jev feasibility review (2026-09-17; no API run)

**Jev feasibility review (2026-09-17; no API run):** TypeSafe AI's early-access
Jev is a typed decision model (`Choice`, `Score`, `Noul`), not a text generator.
Its cleanest experiment in this repository is a shadow implementation of the
already-frozen `llm_crosscontest` mirror protocol: ask which of two sanitized
statements is harder, retain both orientations, and fit probability-weighted
Bradley--Terry rather than discarding the returned distribution. This is a
cheap instrument test, not a production proposal; it must beat the existing
Gemini cross-contest baselines on pairwise accuracy, order consistency, global
BT correlation, and leak-free LOCO before expansion. Jev should not replace the
survival, DE/ridge, or calibration arithmetic: its own model notes warn about
numeric precision and multi-step reasoning. A secondary research use is to turn
sanitized statements into a small frozen set of semantic features (insight,
proof, implementation, and standard-technique burden) for the existing nested
contest-held-out residual harness. Identity/entity matching is suitable only
for audit triage, never automatic roster union. No request was sent, no output
artifact changed, and no implementation was added.
