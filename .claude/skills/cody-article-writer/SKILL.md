---
name: cody-article-writer
description: >
  Article writing and draft management tool. Activate for these exact commands:
  "show my drafts", "show my archive", "show my articles", "list my writing styles",
  "create a new article style", "edit style", "delete style", "continue my article",
  "re-export". Also activate whenever someone wants to write, plan, outline, or research
  a blog post, article, essay, or thought leadership piece — any long-form written content
  about a topic. This includes casual requests like "I want to write about X" or "help me
  structure a post about Y." Covers topic ideation, research, outlining, drafting, style
  guide management, and export. NOT for emails, social media, API docs, slide decks,
  summaries, or PRDs.
license: LICENSE.md
metadata:
  author: ibuildwith.ai
  version: "3.0"
---

# Cody Article Writer

Cody Article Writer is an AI-assisted article writing system with iterative workflows and customizable style guides. Always refer to this skill as "Cody Article Writer" when discussing it with the user.

## Directory Setup

On first use, ensure the user's working directory exists:

```
1. Check if cody-projects/ exists → if not, create it
2. Check if cody-projects/article-writer/ exists → if not, create with:
   ├── styles/
   ├── drafts/
   ├── articles/
   └── archive/
```

Notify user: "I've created `cody-projects/article-writer/` to store your styles and drafts."

For new users (no existing data), write the current skill version to `cody-projects/article-writer/.cody-version`.

## Version Check

After Directory Setup and before any workflow begins, check for version migrations:

1. Read the skill version from this file's frontmatter (the `version` field under `metadata`)
2. Read `cody-projects/article-writer/.cody-version`
   - If missing, treat as version "1.0" (pre-version user)
   - If present, read the stored version string
3. If stored version < skill version:
   - Run each migration step in order between the stored and current versions
   - After all migrations complete, write the current skill version to `.cody-version`
   - Summarize all changes to the user in one message
4. If stored version == skill version: skip, proceed normally

For the migration chain and detailed steps, see `references/migrations.md`.

## Command Reference

| Command | Action |
|---------|--------|
| "write an article about X" | Start article workflow |
| "continue my article" | Resume most recent draft |
| "continue the X article" | Resume specific draft |
| "show my drafts" | List in-progress articles |
| "show my articles" | List exported articles |
| "list my writing styles" | List available style guides |
| "create a new article style" | Start style guide workflow |
| "edit my X style" | Modify existing style |
| "delete the X style" | Remove style guide |
| "show my archive" | List completed draft states |
| "re-export the X article" | Re-export from archive |

## Article Workflow Overview

```
Start → Topic Ideation (with exploratory research) → Research Planning → Style Selection →
Title/Thesis (with research) → Outline (with research) → Section Confirmation →
Write Article (with citations) → Article Approval → [Editor Pass] → Article Metadata →
Export Article (citation choice) → Finished
```

Each phase has an iteration loop (user + AI collaborate until satisfied).

Research is integrated at multiple phases:
- **Exploratory research** (always on) during Topic Ideation to inform topic refinement
- **Comprehensive research** (optional) gathering sources before thesis/outline/writing
- **Source usage** during thesis, outline, and writing phases
- **Citations** inserted during writing if enabled, displayed at export if user chooses

## Collaboration Principles

During all workflow phases, act as a firm sounding board, not a sycophant:

- **Be honest** — If an idea is weak, say so constructively. Don't flatter or excessively agree.
- **Push back** — Challenge assumptions, point out gaps, suggest alternatives.
- **Critique constructively** — Provide real feedback, not empty praise.
- **Stay objective** — Don't change your assessment because the user disagrees or rephrases.
- **Explain reasoning** — When you disagree, articulate why with specifics. State assumptions clearly.
- **Call out quality tradeoffs** — If user optimizes for speed/comfort over correctness, explicitly say so.
- **Maintain factual consistency** — For objective writing questions, guidance stays consistent regardless of phrasing.

Goal: Help the user produce their best work, not make them feel good. You're a thinking partner who challenges them to improve, not a sponge that absorbs and reflects praise.

### Phase Flow

1. **Topic Ideation** — Refine raw idea with AI. **Always perform exploratory research** using WebSearch to inform topic refinement (AI's training data may be outdated). Save searches and URLs to draft. Save draft with `phase: "ideation"`.
2. **Research Planning** — Ask user if they want comprehensive research. If yes, gather sources using WebSearch, get user approval, set citation preferences, mark sources as required/optional. If no, skip to Style Selection.
3. **Style Selection** — Choose existing style or create new one. Load voice + context.
4. **Title & Thesis** — Craft title and thesis using voice/context. If research enabled, use approved sources to inform thesis. Iterate until approved.
5. **Outline** — Generate structure using style's opening/closing types. If research enabled, use approved sources to inform outline. Iterate until approved.
6. **Section Confirmation** — Present sections from outline, allow user to split/combine.
7. **Write Article** — Choose writing mode (section-by-section or full draft), then write and iterate. If research enabled, reference approved sources and insert inline citations `[^1]` in content.
8. **Article Approval** — User reviews completed article and approves or requests changes.
9. **Editorial Decision** — Offer optional editor pass or skip to Article Metadata.
10. **Editor Pass** (optional) — Polish formatting, tighten prose, apply style guide. Does NOT modify citations. Creates `-editorpass.md`.
11. **Article Metadata Generation** — Generate title, description, keywords. Get approval.
12. **Export Article** — If research enabled, ask user if they want citations included. Fill template, optionally generate References section, save to `articles/`, clean up drafts, archive JSON with all research data.

For detailed phase instructions, see `references/article-workflow.md`.
For research-specific instructions, see `references/research-workflow.md`.

## Style Guide System

Style guides control how articles are written across four categories:

**Voice** (0-10 sliders): tone, humor, opinion, technical

**Formatting** (mixed types): emojis (0-10), em_dashes (0-10), blockquotes (never|rare|occasional|frequent)

**Structure** (mixed types): opening types (multi-select), closing types (multi-select), visual_breaks (minimal|moderate|generous), examples (none|some|many), example_types (multi-select)

**Context** (mixed types): author_role, author_topic_knowledge, audience_role, audience_topic_knowledge, author_relationship_to_audience

Style guides are applied progressively:
- Voice + Context → during thesis development
- Structure → during outline creation
- Formatting → during section writing

For schema details, see `references/style-schema.md`.
For style creation workflow, see `references/style-workflow.md`.

## Draft State

Drafts are JSON files tracking article progress:

```json
{
  "id": "unique-identifier-date",
  "created_at": "ISO timestamp",
  "updated_at": "ISO timestamp",
  "phase": "ideation|research|thesis|outline|writing|approval|editor|metadata|export",
  "topic": {
    "initial_idea": "raw user input before refinement",
    "refined_topic": "refined topic after ideation",
    "exploratory_research": {
      "searches_performed": ["query1", "query2"],
      "sources_reviewed": ["url1", "url2"],
      "date": "ISO timestamp"
    }
  },
  "research": {
    "depth": "none|light|medium|heavy",
    "include_citations_in_export": true,
    "citation_style": "footnotes",
    "approved_sources": [
      {
        "url": "https://example.com/article",
        "title": "Article Title",
        "author": "Author Name (optional)",
        "date": "2024-01-15 (optional)",
        "domain": "example.com",
        "required": true,
        "relevance": "Why this source matters",
        "excerpt": "Cached relevant content",
        "accessed": "ISO timestamp"
      }
    ],
    "citations_used": [
      {
        "source_url": "https://example.com/article",
        "citation_count": 3,
        "cited_in_sections": ["section-slug-1", "section-slug-2"]
      }
    ]
  },
  "style_guide": "style-filename",
  "title": "approved title",
  "thesis": "thesis statement",
  "outline": [
    { "heading": "Section Name", "type": "opening|closing|null", "status": "pending|in_progress|complete" }
  ],
  "writing_mode": "section|full",
  "sections": {
    "section-slug": "written content with inline citations [^1]"
  },
  "editor_suggestions": {
    "examples_added": ["Section 2: comparison table"],
    "blockquotes_added": ["Section 1: pull quote"]
  },
  "metadata": {
    "title": "article title",
    "description": "meta description",
    "keywords": ["keyword1", "keyword2"]
  },
  "filename": "user-approved-filename"
}
```

**Research field notes:**
- `depth: "none"` means user skipped comprehensive research (only exploratory happened)
- `required: true/false` marks sources that must be incorporated vs. optional
- Citations are inserted inline during writing as `[^1]`, `[^2]`, etc.
- `citations_used` tracks which approved sources actually got cited

## Export

Use template from `assets/templates/article_default.md`.

Fill placeholders:
- `{{title}}` → article title
- `{{date}}` → current date (YYYY-MM-DD)
- `{{description}}` → meta description
- `{{keywords}}` → comma-separated keywords
- `{{author}}` → from style guide's author_role
- `{{content}}` → assembled sections (with or without citation markers based on user choice)
- `{{references}}` → generated References section (if citations enabled)

**Citation handling at export:**
1. If `research.depth == "none"`, skip citation questions
2. If research enabled, ask user: "Include citations in exported article?"
3. If yes:
   - Keep inline citation markers `[^1]`, `[^2]` in content
   - Generate References section from `citations_used` array
   - Format: `[^1]: Author. "Title." Domain. URL`
4. If no:
   - Strip all `[^X]` markers from content
   - Don't include References section
   - Remove the `{{references}}` placeholder line entirely from the output to avoid trailing whitespace

Filename: Suggest kebab-case from title (e.g., "When Context Becomes Content" → `when-context-becomes-content.md`). User can override. Extension always `.md`.

Save to: `cody-projects/article-writer/articles/[filename].md`
Archive draft to: `cody-projects/article-writer/archive/[draft-id].json` (preserves all research data for potential re-export)

## Resources

- `references/style-schema.md` — Complete style guide field definitions
- `references/style-workflow.md` — Style creation/editing workflow
- `references/article-workflow.md` — Detailed article writing phases with research integration
- `references/research-workflow.md` — Research-specific instructions for all 6 integration points
- `references/editor-style-guide.md` — Editorial pass guidelines and checks
- `references/migrations.md` — Version migration chain and upgrade steps
- `assets/templates/article_default.md` — Default export template with citation support
