# Style Guide Schema

Style guides are saved as JSON files in `cody-projects/article-writer/styles/`.

**Important:** Research settings (research depth, citations, approved sources) are **NOT** part of style guides. Research is configured per-article during the Research Planning phase. Style guides are reusable across articles regardless of research needs.

## File Naming

- Filename: kebab-case version of the style name
- Example: "Professional LinkedIn" → `professional-linkedin.json`
- No special characters, lowercase only

## JSON Structure

```json
{
  "name": "Style Name",
  "description": "Brief description of when to use this style",
  "voice": {
    "tone": 5,
    "humor": 5,
    "opinion": 5,
    "technical": 5
  },
  "formatting": {
    "emojis": 0,
    "em_dashes": 2,
    "blockquotes": "occasional"
  },
  "structure": {
    "opening": ["narrative"],
    "closing": ["call_to_action"],
    "visual_breaks": "moderate",
    "examples": "some",
    "example_types": ["lists", "code_snippets"]
  },
  "context": {
    "author_role": "Role description",
    "author_topic_knowledge": 5,
    "audience_role": "Audience description",
    "audience_topic_knowledge": 5,
    "author_relationship_to_audience": 5
  }
}
```

## Field Definitions

### Voice (0-10 sliders)

| Field | 0 | 10 | Description |
|-------|---|-----|-------------|
| tone | Casual | Professional | Formality level |
| humor | Serious | Playful | Use of wit and levity |
| opinion | Balanced | Opinionated | Strength of viewpoint |
| technical | Less | More | Depth of technical detail |

### Formatting (mixed types)

| Field | Type | Values | Description |
|-------|------|--------|-------------|
| emojis | integer | 0-10 | Emoji frequency (0 = None, 10 = Heavy) |
| em_dashes | integer | 0-10 | Em dash usage (0 = None, 10 = Frequent; AI tell when overused) |
| blockquotes | string | never, rare, occasional, frequent | Preference for using blockquotes/pull quotes |

### Structure (mixed types)

| Field | Type | Valid Values | Description |
|-------|------|--------------|-------------|
| opening | array | `direct`, `contextual`, `narrative`, `tension` | How to begin the article (multi-select) |
| closing | array | `summary`, `call_to_action`, `open_question`, `callback`, `provocation`, `key_takeaways` | How to end the article (multi-select) |
| visual_breaks | string | `minimal`, `moderate`, `generous` | Amount of white space and paragraph spacing |
| examples | string | `none`, `some`, `many` | Default preference for including examples |
| example_types | array | `lists`, `tables`, `diagrams`, `code_snippets`, `quotes`, `case_studies` | Preferred example types (only if examples != "none") |

**Opening types:**
- `direct` — State the main point immediately
- `contextual` — Set the scene, provide background first
- `narrative` — Open with a story or anecdote
- `tension` — Create stakes, pose a problem

**Closing types:**
- `summary` — Recap key points
- `call_to_action` — Tell reader what to do next
- `open_question` — Leave them thinking
- `callback` — Reference the opening
- `provocation` — Challenge assumptions
- `key_takeaways` — Bullet list of main insights

**Visual breaks:**
- `minimal` — Dense prose, longer paragraphs, fewer section breaks
- `moderate` — Balanced spacing, standard paragraph lengths
- `generous` — Shorter paragraphs, more white space, frequent breaks

**Examples:**
- `none` — Minimal to no examples, rely on explanation
- `some` — Occasional examples where helpful
- `many` — Liberal use of examples throughout

**Example types:**
- `lists` — Bulleted or numbered lists
- `tables` — Comparison tables, data tables
- `diagrams` — Flowcharts, sequence diagrams, state diagrams (generated as Mermaid markdown syntax)
- `code_snippets` — Code examples (for technical content)
- `quotes` — Pull quotes, expert citations, testimonials
- `case_studies` — Brief real-world examples (2-4 paragraphs, not full sections)

### Context

| Field | Type | Range/Format | Description |
|-------|------|--------------|-------------|
| author_role | string | Free text | e.g., "AI Educator", "Product Manager" |
| author_topic_knowledge | integer | 0 (Learning) to 10 (Expert) | Author's expertise level |
| audience_role | string | Free text | e.g., "Enterprise PMs", "Indie Hackers" |
| audience_topic_knowledge | integer | 0 (Learning) to 10 (Expert) | Audience's expertise level |
| author_relationship_to_audience | integer | 0 (Peer) to 10 (Expert) | Authority dynamic |

## Validation Rules

- All slider values (voice, emojis, em_dashes) must be integers 0-10
- `name` is required and must be non-empty
- `opening` and `closing` must contain at least one valid value
- `visual_breaks` must be one of: `minimal`, `moderate`, `generous`
- `examples` must be one of: `none`, `some`, `many`
- `example_types` only required if `examples` is not `none`
- `blockquotes` must be one of: `never`, `rare`, `occasional`, `frequent`
- `author_role` and `audience_role` should be non-empty strings
