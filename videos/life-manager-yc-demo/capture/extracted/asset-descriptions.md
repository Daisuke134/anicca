# Asset Descriptions

⚠️  GEMINI_API_KEY not set — descriptions below are catalog-derived (alt text, headings, section context, filename) instead of Vision-generated. To get richer Vision descriptions on the next capture, set GEMINI_API_KEY (or GOOGLE_API_KEY) and re-run.

The `logo-<hash>.svg` filename prefix is a structural hint (DOM said this SVG was inside a `<header>`, home-link `<a>`, or had an aria-label matching the page brand). To pick the actual brand logo without Vision, open the `logo-*` candidates in a previewer or rasterize them with `sharp` before referencing — composing a fake logo ships off-brand in the final video.

- favicon.png — 80KB, favicon
- fonts/0aa834ed78bf6d07-s.woff2 — font file
- fonts/67957d42bae0796d-s.woff2 — font file
- fonts/6ed338a30d658adc-s.woff2 — font file
- fonts/7b0b24f36b1a6d0b-s.p.woff2 — font file
- fonts/886030b0b59bc5a7-s.woff2 — font file
- fonts/939c4f875ee75fbb-s.woff2 — font file
- fonts/98848575513c9742-s.woff2 — font file
- fonts/aa7f81ee08e33986-s.woff2 — font file
- fonts/ab3bd16111852789-s.woff2 — font file
- fonts/bb3ef058b751a6ad-s.p.woff2 — font file
- fonts/da18d495caa1bffe-s.woff2 — font file
- fonts/ea6791b6c54f602a-s.woff2 — font file
- fonts/f390640bdede9737-s.woff2 — font file
- fonts/f911b923c6adde36-s.woff2 — font file

## Adopted current product evidence

- `../assets/images/github-repository.png` — real 1920×1080 GitHub repository capture showing the public `Daisuke134/life-manager` source tree; use for the repository/one-product opening.
- `../assets/images/github-readme-architecture.png` — real 1920×1080 GitHub README capture around the current Life Manager identity and one-product/two-execution-surfaces section; use for the architecture beat without reconstructing the GitHub page.
- `../assets/images/dashboard-current-zero.png` — real 1920×1080 public dashboard capture showing total net worth $0.00, revenue $0.00, and zero bodies alive; use as the honest current-state close.
- `repo://agents/registry.json` — canonical current specialist-agent inventory; render only its actual lifecycle labels (`live`, `legacy_live`, `shadow`, `planned`) and names.
- `repo://README.md#quick-start` — canonical local install/runtime commands; render as source-backed terminal text, not as evidence that a command was executed during the video build.
- `repo://apps/life-manager` — canonical cloud service implementation (Telegram, scheduler, voice/calls, and authenticated panel); render as a code-backed capability map, not a fabricated public UI.
