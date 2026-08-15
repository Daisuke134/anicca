---
name: music-score-omr
description: Use an installed Audiveris CLI to extract source-only MusicXML and OMR evidence before producing or reviewing an annotated score.
---

# Music score OMR

Use this skill when supplied sheet music requires note-level source fidelity.

Run `scripts/source_notehead_overlay.py` against source material only. Set
`AUDIVERIS_BIN` or pass `--audiveris`; never include a candidate deliverable in
the OMR input directory. Bind every output and the source by SHA-256.

The overlay fills recognized noteheads green and writes
`detector-manifest.json`. Inspect every source/overlay tile. Black source
noteheads are omissions; green marks without a source notehead are false
positives. Resolve both from source pixels before freezing the census.

OMR counts are corroboration, not proof of completeness. Preserve locators,
semantic values, modifiers, ties, and written or carried accidentals.
