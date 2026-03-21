# Public Xiangqi Data Source Scouting (Phase 0)

This document records candidate public data sources for future dataset ingestion. This scouting does not block the pure self-play RL path.

| Source | Format(s) | Approx Scale | Acquisition Method | Suitability Notes |
|---|---|---:|---|---|
| Xiangqi.com public game exports / archives | PGN-like / move text | Medium-to-large (platform dependent) | Manual export / API if available | Useful for modern online play; verify license and export terms. |
| Chinese Chess DB mirrors (community collections) | ICCS / custom plain text | Large (historical collections) | Download archive + format adapter | Good for opening and tactical variety; schema normalization required. |
| Tournament bulletin/game books published online | PDF / human notation | Small-to-medium | Manual extraction + OCR + curation | Quality can be high but conversion effort is significant. |
| GitHub/open datasets tagged Xiangqi | JSON / text / mixed | Varies | Git clone / release download | Easy experimentation source; must vet duplicates and provenance. |

## Planned Integration Path (Future)

1. Add source-specific parsers into a staging adapter layer.
2. Normalize all records to canonical internal form (`initial_fen`, `moves_iccs`).
3. Emit schema-versioned datasets with mandatory version metadata.
4. Run legality and terminal validation in batch before training ingestion.

## Phase 0 Boundaries

- No dependency on these sources for core environment correctness.
- No production ingestion pipeline in Phase 0.
- Keep this as scouting-only documentation and revisit in later phases.
