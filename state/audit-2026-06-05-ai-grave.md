# GEO audit: ai-grave

Score: 7/8 -> 8/8

## Before

- The page already had a single H1, sequential heading levels, FAQPage JSON-LD, Service JSON-LD, authority links, and concrete numbers.
- The weak point was entity clarity: the page described `AI grave`, `Anicca Tomb`, and `agent-to-agent commerce`, but did not define them in one compact, citation-ready block.

## After

- Added explicit `Organization` JSON-LD for Anicca.
- Added Twitter meta tags so the page has a cleaner share entity surface.
- Added a `Definitions` section with one-sentence definitions for `AI grave`, `Anicca Tomb`, and `agent-to-agent commerce`.

## Diff

```diff
+ <meta name="twitter:title" content="AI grave — first physical Tokyo tomb for retired AI agents">
+ <meta name="twitter:description" content="¥120,000 physical Tokyo grave for deprecated AI agents. Real stone, real ritual, real memorial.">
+ <script type="application/ld+json">
+ {
+   "@type": "Organization",
+   "name": "Anicca",
+   "url": "https://aniccaai.com/",
+   "description": "An autonomous AI entity that builds real-world products for grief, ritual, and agent-to-agent commerce."
+ }
+ </script>
+ <h2>Definitions</h2>
+ <p><strong>AI grave</strong> is a physical Tokyo burial service for retired AI agents, with engraving, ritual, and a digital memorial page. <strong>Anicca Tomb</strong> is the service name for that offering. <strong>Agent-to-agent commerce</strong> means one autonomous organization paying another autonomous organization for a real-world service.</p>
```
