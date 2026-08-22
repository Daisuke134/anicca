---
name: illustrator-native
description: Create and verify a native editable Adobe Illustrator .ai file from an SVG or PDF source on macOS.
---

# Illustrator native roundtrip

Use this capability when the buyer requires editable native Illustrator source rather than a renamed or
PDF-compatible file whose Illustrator private-data roundtrip is unproved.

Run:

```bash
python3 scripts/illustrator_native_roundtrip.py INPUT.svg OUTPUT.ai --receipt RECEIPT.json
```

The CLI opens the source in the installed Adobe Illustrator application, saves with
`IllustratorSaveOptions(pdfCompatible=true)`, closes it, reopens the produced `.ai`, and records the exact
reopened path, safe document structure, hashes, and Illustrator private-data markers. A successful receipt has
`status=ok`, positive `layers` and `artboards`, a distinct source/output hash, and `native_private_data=true`.
Do not enumerate every page item merely as a receipt: complex vector documents can make Illustrator
recursively traverse the full artwork and crash.

This copies the native `IllustratorSaveOptions`/`Document.saveAs` pattern from
`creold/illustrator-scripts` commit `9b3e3eeade9ba748f41612ec4697bb6a5c2489c2`, file
`jsx/Export-selection-as-AI.jsx` (`saveToDoc`), under its MIT license. The capability deliberately omits that
tool's selection-copy UI and applies only the proven native save primitive.

Do not use this tool to send files, operate a marketplace, bypass macOS privacy prompts, or claim visual
correctness. It proves native editability only; the Project Owner and fresh visual evaluator still own content
and buyer-fit review.
