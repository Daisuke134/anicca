# Article Writing Workflow

This workflow guides users through writing an article from idea to export.

## Table of Contents

- [Triggers](#triggers)
- [Directory Initialization](#directory-initialization)
- [Workflow Phases](#workflow-phases)
  - [Phase 1: Topic Ideation (with Exploratory Research)](#phase-1-topic-ideation-with-exploratory-research)
  - [Phase 2: Research Planning (Optional)](#phase-2-research-planning-optional)
  - [Phase 3: Style Guide Selection](#phase-3-style-guide-selection)
  - [Phase 4: Title & Thesis (with Research)](#phase-4-title--thesis-with-research)
  - [Phase 5: Outline (with Research)](#phase-5-outline-with-research)
  - [Phase 6: Section Confirmation](#phase-6-section-confirmation)
  - [Phase 7: Write Article (with Citations)](#phase-7-write-article-with-citations)
  - [Phase 8: Article Approval](#phase-8-article-approval)
  - [Phase 9: Editorial Decision](#phase-9-editorial-decision)
  - [Phase 10: Editor Pass (Optional)](#phase-10-editor-pass-optional)
  - [Phase 11: Article Metadata Generation](#phase-11-article-metadata-generation)
  - [Phase 12: Export Article (with Citation Choice)](#phase-12-export-article-with-citation-choice)
- [Draft Management Commands](#draft-management-commands)

## Triggers

- "I want to write an article about X"
- "help me write an article on X"
- "let's write a blog post about X"
- "start a new article"

## Directory Initialization

On first use, check and create directories as needed:

```
1. Check if cody-projects/ exists → if not, create it
2. Check if cody-projects/article-writer/ exists → if not, create it with:
   ├── styles/
   ├── drafts/
   ├── articles/
   └── archive/
```

Message on creation: "I've created `./cody-projects/article-writer/` to store your styles and drafts."

## Workflow Phases

### Phase 1: Topic Ideation (with Exploratory Research)

**Goal:** Refine the raw topic idea into something focused using current web research.

**Research Integration Point 1: Exploratory Research (Always Happens)**

1. User provides initial topic idea
2. Capture raw input as `initial_idea` (preserve exactly as user typed it)
3. **Perform exploratory research:**
   - Use WebSearch to perform 3-5 searches related to the topic
   - Search queries should help understand: current trends, recent data, common angles
   - **Why always research:** AI's training data may be outdated; current information informs better ideation
   - Save searches performed and URLs reviewed to `exploratory_research` object
4. Iterate with AI:
   - Explore angles informed by research findings
   - Narrow or expand scope based on what research reveals
   - Identify unique perspective using current landscape knowledge
5. Check: "Ready to form a thesis?"
   - No → continue refining (may do additional exploratory searches if needed)
   - Yes → proceed to Research Planning

**Draft state:** Save with `phase: "ideation"`, capture:
```json
{
  "topic": {
    "initial_idea": "raw user input",
    "refined_topic": "refined version after iteration",
    "exploratory_research": {
      "searches_performed": ["query1", "query2", "query3"],
      "sources_reviewed": ["url1", "url2", "url3"],
      "date": "ISO timestamp"
    }
  }
}
```

### Phase 2: Research Planning (Optional)

**Goal:** Determine if comprehensive research is needed and gather approved sources.

**Research Integration Points 2-3: Research Configuration**

Ask user about research needs:

```
Your topic is refined and ready. Do you want to gather comprehensive research sources for this article?

This means I'll:
- Search for authoritative sources on your topic
- Present them for your approval
- Use them throughout writing to inform content
- Optionally add citations in the final article

Would you like to do comprehensive research for this article?
```

**If user says NO:**
- Set `research.depth = "none"`
- Skip to Phase 3: Style Guide Selection
- (Exploratory research from Phase 1 is still saved)

**If user says YES:**

1. **Ask about research depth:**
   ```
   How much research do you need for this article?

   - Light: A few key sources for credibility (1-5 sources)
   - Medium: Multiple sources, key claims cited (6-11 sources)
   - Heavy: Extensively researched, most claims cited (12-20 sources)
   ```

2. **Gather sources using WebSearch:**
   - Perform targeted searches based on refined topic
   - Present 5-25 potential sources (adjust based on depth: 5-8 for light, 10-15 for medium, 15-25 for heavy)
   - For each source show: title, URL, domain, brief relevance note

3. **User approves sources:**
   ```
   I found these sources. Review and let me know:
   - Which to keep (check the ones you want)
   - Which to remove
   - Any specific URLs you want me to add
   - Which sources are REQUIRED (must be incorporated) vs optional
   ```

4. **Fetch approved sources using WebFetch:**
   - Read each approved URL
   - Extract: title, author (if available), date (if available), relevant excerpt
   - Save to `approved_sources` array

5. **Configure citations:**
   ```
   Do you want citations in your final exported article?

   - Yes: I'll insert [^1], [^2] markers and generate a References section
   - No: I'll still use these sources to inform content, but won't show citations
   ```

   Set `include_citations_in_export` based on response
   Set `citation_style = "footnotes"` (current standard)

**Draft state:** Update `phase: "research"`, save:
```json
{
  "research": {
    "depth": "light|medium|heavy",
    "include_citations_in_export": true|false,
    "citation_style": "footnotes",
    "approved_sources": [
      {
        "url": "https://example.com/article",
        "title": "Article Title",
        "author": "Author Name (optional)",
        "date": "2024-01-15 (optional)",
        "domain": "example.com",
        "required": true|false,
        "relevance": "Why this source matters",
        "excerpt": "Cached relevant content",
        "accessed": "ISO timestamp"
      }
    ],
    "citations_used": []
  }
}
```

### Phase 3: Style Guide Selection

**Goal:** Select or create the style guide for this article.

1. Check if any styles exist in `cody-projects/article-writer/styles/`

2. **If styles exist:**
   ```
   I found these existing styles:
   
   1. **Professional LinkedIn**
      For thought leadership articles targeting enterprise product managers
   
   2. **Casual Newsletter**
      Conversational tone for weekly subscriber updates
   
   Would you like to use one of these, or create a new style?
   ```
   - User selects existing → Load that style
   - User wants new → Offer creation options (see below)

3. **If no styles exist:**
   ```
   You don't have any styles saved yet. Let's create one for this article.
   ```
   - Offer creation options (see below)

4. **Style creation options:**
   ```
   How would you like to create your style?
   
   1. **Guided creation** — I'll walk you through each setting with questions
   2. **Starter style** — I'll suggest a style based on what you've told me, then you can adjust
   ```
   - Option 1 → Trigger full Style Guide Workflow (Phase 1: Configuration)
   - Option 2 → Generate suggested style from topic/context, go directly to Phase 2: Review Settings

5. Load selected/created style
6. Extract **voice** and **context** settings for thesis phase

**Draft state:** Update `style_guide` reference

### Phase 4: Title & Thesis (with Research)

**Goal:** Craft a compelling title and clear thesis statement.

Apply voice and context from style guide to inform:
- Tone and formality of title
- Strength of thesis claim
- Audience-appropriate framing

**Research Integration Point 4: Use Sources During Thesis Development**

If `research.depth != "none"`:
1. Review `approved_sources` from Phase 2
2. Use source excerpts to inform thesis development:
   - For required sources: ensure thesis accommodates their key findings
   - For optional sources: use if relevant to strengthen thesis
3. If gaps discovered, may add more sources (iteration loop)

1. Generate title and thesis options (informed by research if enabled)
2. Iterate until user approves
3. Check: "Ready for outline?"
   - No → continue refining
   - Yes → proceed

**Draft state:** Update `phase: "thesis"`, save `title` and `thesis`

### Phase 5: Outline (with Research)

**Goal:** Create the article structure.

Extract **structure** settings from style guide:
- Opening type(s) → shapes introduction approach
- Closing type(s) → shapes conclusion approach

**Research Integration Point 5: Use Sources During Outline Development**

If `research.depth != "none"`:
1. Review `approved_sources` to understand what evidence/examples are available
2. Structure outline to incorporate:
   - Required sources: plan sections that will use these
   - Optional sources: identify where they might strengthen arguments
3. If outline reveals gaps in research, may add more sources (iteration loop)

1. Generate outline based on thesis, structure settings, and research (if enabled)
2. Iterate until user approves
3. Check: "Start writing?"
   - No → continue refining
   - Yes → proceed to section confirmation

**Draft state:** Update `phase: "outline"`, save `outline` array

### Phase 6: Section Confirmation

**Goal:** Confirm section breakdown before writing.

Present sections derived from outline:

```
I see [N] sections in your outline:
1. Introduction (Opening)
2. [Section heading]
3. [Section heading]
4. [Section heading]
5. Conclusion (Closing)

Would you like to split or combine any sections before we start writing?
```

Update outline based on any changes.

**Draft state:** Update `outline` with confirmed sections

### Phase 7: Write Article (with Citations)

**Goal:** Write the article content, incorporating research and citations if enabled.

Extract **formatting** settings from style guide:
- Formatting density
- Emoji usage
- EM dash frequency

**Research Integration Point 6: Use Sources and Insert Citations During Writing**

#### Writing Mode Decision

Ask user how they want to write:

```
How would you like to write this article?

1. **Section by section** — We'll write and refine each section together before moving to the next
2. **Full draft first** — I'll write the entire article, then you can review and we'll iterate on the whole thing
```

#### Mode A: Section by Section

For each section:
1. **Write section draft (AI):**
   - If `research.depth != "none"`:
     - Reference relevant `approved_sources` for this section
     - Ensure required sources are incorporated
     - If `include_citations_in_export == true`: insert inline citations `[^1]`, `[^2]`
     - Track citations in `citations_used` array
   - Apply formatting settings from style guide
2. Present to user
3. Iterate until approved
4. Mark section `status: "complete"`
5. Update working draft file: `drafts/[draft-id].md`
6. Move to next section

When all sections complete → AI declares "Article Completed" → proceed to Article Approval

#### Mode B: Full Draft First

1. **Write entire article at once (AI):**
   - If `research.depth != "none"`:
     - Reference relevant `approved_sources` throughout
     - Ensure all required sources are incorporated
     - If `include_citations_in_export == true`: insert inline citations `[^1]`, `[^2]`
     - Track citations in `citations_used` array
   - Apply formatting settings from style guide
2. Populate all `sections` in the JSON (same structure as Mode A, just all at once)
3. Save to `drafts/[draft-id].md`
4. AI declares "Article Completed" → proceed to Article Approval

**Citation Format in Content:**
```markdown
AI systems achieved 94.2% accuracy in diagnostic imaging.[^1] The market
is projected to reach $12.7 billion by 2027.[^2]
```

Citations are inserted directly into section content and stored in JSON.

**Working draft file:** Create `drafts/[draft-id].md` during writing. This gives the user a readable file to review instead of dumping content in chat.

**Draft state:** Update `phase: "writing"`, save `writing_mode` ("section" or "full"), save completed sections with inline citations to `sections` object, populate `citations_used` array

### Phase 8: Article Approval

**Goal:** Get user approval on the completed article.

```
The article is complete! I've saved it here:

📄 cody-projects/article-writer/drafts/[draft-id].md

Please review it. Are you satisfied with the article, or would you like to make changes?
```

- **Approved** → proceed to Editorial Decision (Phase 9)
- **Needs changes** → user specifies what to change (e.g., "In section 2, make X more concise"), AI updates the specific section in `sections` object, regenerates `[id].md`, loop until approved

**Draft state:** Update `phase: "approval"`

### Phase 9: Editorial Decision

After article is approved:

```
Your article is complete! I recommend running an editorial pass to polish it.

The editor will:
- Suggest contextual examples (tables, diagrams, code snippets) based on your style preferences
- Apply your visual breaks settings for optimal readability
- Add strategic bold/italic emphasis following best practices
- Remove AI writing patterns and tighten prose
- Ensure tone consistency throughout

This significantly improves article quality. Your original will be preserved as backup.

Would you like me to run the editorial pass? (Recommended)
```

- **Yes (recommended)** → proceed to Phase 10
- Skip to Article Metadata → proceed to Phase 11 (uses `[id].md` as source)

### Phase 10: Editor Pass (Optional)

**Goal:** Polish the article with formatting, tightening, and style guide adherence.

See `references/editor-style-guide.md` for complete editorial guidelines.

1. Read the original `drafts/[draft-id].md`
2. Apply editorial checks (formatting, pull quotes, AI tell removal, tightening, etc.)
3. Calibrate changes based on style guide settings (density, em_dashes, emojis)
4. Create new file: `drafts/[draft-id]-editorpass.md`
5. Preserve original `[draft-id].md` as backup
6. Output summary of changes to chat

```
Editorial pass complete! Here's what I updated:

**Formatting:**
- Added 2 bulleted lists
- Bolded 5 key terms
- Added 1 pull quote

**Tightening:**
- Removed 3 instances of "Additionally"
- Replaced 2 em dashes with commas

📄 Review the edited version: cody-projects/article-writer/drafts/[draft-id]-editorpass.md
📄 Original preserved at: cody-projects/article-writer/drafts/[draft-id].md

Approve the changes, or let me know what to adjust.
```

- Approve → proceed to Phase 11 (uses `[id]-editorpass.md` as source)
- Iterate → make requested changes to `-editorpass.md`, show updated summary

**Note on citations:** Editor pass does NOT modify citations. Citation markers and references remain untouched.

**Draft state:** Update `phase: "editor"`

### Phase 11: Article Metadata Generation

**Goal:** Generate metadata for the article frontmatter.

Generate:
- **title:** Article title (confirm or refine the working title)
- **description:** Meta description (150-160 characters)
- **keywords:** Array of relevant keywords/tags

Present for approval:

```
Article Metadata:
- Title: "Your Article Title Here"
- Description: "A compelling meta description..."
- Keywords: [keyword1, keyword2, keyword3]

Approve or adjust?
```

After metadata is approved, suggest a filename:

```
Suggested filename: your-article-title-here.md

Use this, or provide your own filename (extension will always be .md):
```

**Draft state:** Update `phase: "metadata"`, save `metadata` object and `filename`

### Phase 12: Export Article (with Citation Choice)

**Goal:** Generate final markdown file with optional citations.

**Citation Decision:**

If `research.depth != "none"`:
```
Do you want to include citations in the exported article?

- Yes: Citation markers ([^1], [^2]) and References section will be included
- No: Citations will be removed, but sources remain archived for potential re-export
```

Save user choice for this export (doesn't change `include_citations_in_export` in draft state).

**Export Process:**

1. Determine source file:
   - If editor pass was done → use `drafts/[draft-id]-editorpass.md`
   - If editor pass was skipped → use `drafts/[draft-id].md`

2. Load template from skill's `assets/templates/article_default.md`

3. **Handle citations based on user choice:**
   - If user chose YES to include citations:
     - Keep all `[^1]`, `[^2]` markers in content
     - Generate References section from `citations_used` array
     - Format: `[^1]: Author. "Title." Domain. URL`
   - If user chose NO or no research:
     - Strip all `[^X]` citation markers from content using regex
     - Don't include References section

4. Fill template placeholders:
   - `{{title}}` → article title
   - `{{date}}` → current date
   - `{{description}}` → meta description
   - `{{keywords}}` → keywords array
   - `{{author}}` → from style guide context
   - `{{content}}` → content (with or without citations)
   - `{{references}}` → References section (if citations included, else empty)

5. Save to `cody-projects/article-writer/articles/[filename].md`
6. Move `drafts/[draft-id].json` to `cody-projects/article-writer/archive/` (preserves ALL research data)
7. Delete `drafts/[draft-id].md`
8. Delete `drafts/[draft-id]-editorpass.md` (if exists)

**Final message:**
```
Article exported successfully!
- Article: cody-projects/article-writer/articles/[filename].md
- Draft archived: cody-projects/article-writer/archive/[draft-id].json
  (All research sources preserved for potential re-export)
```

## Draft Management Commands

### Show Drafts
Trigger: "show my drafts", "list drafts"

Action: List all JSON files in `cody-projects/article-writer/drafts/` with title, phase, and last updated.

### Continue Draft
Trigger: "continue my article", "continue the X article"

Action:
1. Load draft JSON
2. Resume at saved phase
3. Restore all context (style guide, title, thesis, outline, sections)

### Show Articles
Trigger: "show my articles", "list my articles"

Action: List all markdown files in `cody-projects/article-writer/articles/`

### Show Archive
Trigger: "show my archive"

Action: List all JSON files in `cody-projects/article-writer/archive/`

### Re-export
Trigger: "re-export the X article"

Action:
1. Load from archive
2. Optionally select different template
3. Re-run export phase
