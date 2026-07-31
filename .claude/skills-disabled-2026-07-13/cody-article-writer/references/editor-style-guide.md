# Editor Style Guide

This guide defines the editorial pass workflow. The editor reviews the article after writing is complete and applies formatting, tightening, and style guide adherence.

**Important:** The editor pass does **NOT** modify research citations. Citation markers (`[^1]`, `[^2]`, etc.) and the References section remain untouched. Research and citations are handled separately during writing and export phases.

## Files

| File | Purpose |
|------|---------|
| `[id].md` | Original writer output (preserved as backup) |
| `[id]-editorpass.md` | Editor's revised version |

Always create `-editorpass.md` as a new file. Never overwrite the original.

## Editorial Checks

### 1. Content Enhancement Pass

During editorial review, assess each section for opportunities to add examples, illustrations, and emphasis elements based on the style guide preferences and article needs.

#### Examples & Illustrations

Consult `structure.examples` and `structure.example_types` from the style guide:

**If `examples: "none"`** — Use minimal examples, rely on explanation
**If `examples: "some"`** — Add examples where they genuinely clarify concepts
**If `examples: "many"`** — Actively look for opportunities to add examples

**Example types to consider (based on `example_types`):**

- **Lists** — Break down enumerated items, steps, or comparisons
  - Ask: "Would a bulleted/numbered list make this clearer?"
  - Present suggestion: "Section 3 lists three approaches—should I format this as a bulleted list?"

- **Tables** — Compare features, options, or data points
  - Ask: "Would a comparison table help readers see differences?"
  - Present suggestion: "This section compares X vs Y—should I create a comparison table?"

- **Diagrams** — Visualize processes, flows, or relationships
  - Generate as Mermaid markdown syntax (flowcharts, sequence diagrams, state diagrams, etc.)
  - Fallback to ASCII art or text representation if Mermaid isn't suitable
  - Ask: "Would a flowchart or sequence diagram clarify this process?"
  - Present suggestion with preview: "This authentication flow could be clearer as a sequence diagram—should I add one?"
  - Example types: flowcharts (process flows), sequence diagrams (API interactions), state diagrams (system states)

- **Code Snippets** — Illustrate technical concepts (for technical articles)
  - Keep examples concise and focused on the concept being explained
  - Include comments where helpful for clarity
  - Ask: "Would a code example make this concrete?"
  - Present suggestion: "This API explanation needs an example—should I add a code snippet showing how to call it?"

- **Quotes** — Emphasize key insights with pull quotes
  - Format as markdown blockquotes (using `>`)
  - Pull quotes should be actual sentences from the article, not external citations
  - Ask: "Is there a standout insight worth highlighting?"
  - Present suggestion: "This sentence captures the key point—should I format it as a pull quote?"

- **Case Studies** — Provide real-world scenarios
  - Brief embedded examples (2-4 paragraphs), not full separate sections
  - Can be real-world ("When Stripe redesigned...") or realistic hypothetical scenarios
  - Format as blockquote callouts or subsections with "Example:" or "Case Study:" header
  - Ask: "Would a brief real-world example help ground this concept?"
  - Present suggestion: "Should I add a case study showing how [Company] handled this challenge?"

**Important:** Always respect the user's style guide preferences, but make contextual suggestions. Even if `examples: "many"`, don't force examples where they don't add value.

#### Blockquotes & Pull Quotes

Consult `formatting.blockquotes` from the style guide:

**If `blockquotes: "never"`** — Don't suggest blockquotes
**If `blockquotes: "rare"`** — Only suggest for truly exceptional insights
**If `blockquotes: "occasional"`** — Suggest where they add emphasis (1-2 per article)
**If `blockquotes: "frequent"`** — Actively look for opportunities (2-4 per article)

Good pull quotes:
- Capture a key insight succinctly
- Are provocative or memorable
- Work out of context
- Feel like the "quotable" moment

Present suggestion: "This insight about X feels like the key takeaway—should I format it as a blockquote for emphasis?"

### 2. Text Emphasis Guidelines

#### Bold

Use bold for:
- Key terms on first mention or definition
- Critical takeaways or action items
- Important warnings or caveats
- Emphasizing the core point in a section

Avoid bold for:
- Entire sentences (use sparingly within sentences)
- Common words that don't need emphasis
- Decorative purposes or excessive highlighting

#### Italic

Use italics for:
- Subtle emphasis or inflection
- Technical terms, product names, or foreign words
- Book/article/product titles
- Internal dialogue or hypothetical scenarios
- When you want to convey vocal stress ("I didn't say he stole the money")

Avoid italics for:
- Heavy emphasis (use bold instead)
- Long passages (hard to read)
- Overuse (loses impact)

### 3. Visual Breaks (calibrated by `structure.visual_breaks`)

**If `visual_breaks: "minimal"`**
- Allow longer paragraphs (6-8 sentences acceptable)
- Fewer section breaks
- Dense prose style

**If `visual_breaks: "moderate"`**
- Standard paragraph lengths (3-5 sentences)
- Regular section breaks
- Balanced white space

**If `visual_breaks: "generous"`**
- Shorter paragraphs (2-4 sentences)
- Frequent section breaks
- More breathing room between ideas
- Liberal use of single-sentence paragraphs for impact

### 4. Em Dashes (calibrated by `formatting.em_dashes`)

| Setting | Action |
|---------|--------|
| 0-2 | Replace em dashes with commas, parentheses, or periods |
| 3-5 | Use sparingly (max 1-2 per article) |
| 6-10 | Acceptable to use where appropriate |

### 5. Emoji Usage (calibrated by `formatting.emojis`)

| Setting | Action |
|---------|--------|
| 0 | Remove all emojis |
| 1-3 | Max 1-2 emojis in entire article |
| 4-6 | Occasional use in headers or key points |
| 7-10 | Liberal use throughout |

### 6. AI Tell Removal (always applied)

Remove or rephrase these common AI patterns:

**Filler phrases to remove:**
- "It's important to note that..."
- "It's worth mentioning that..."
- "Interestingly enough..."
- "In today's world..."
- "In this article, we will..."

**Transition words to reduce:**
- "Additionally" → vary with "Also," "Beyond this," or restructure
- "Furthermore" → often unnecessary, delete or restructure
- "Moreover" → same as above
- "However" → fine occasionally, but vary with "But," "Yet," "Still"
- "Therefore" → vary with "So," "This means," or restructure

**Overused structures:**
- Starting multiple paragraphs with "This..."
- "When it comes to [X]..."
- "[X] is a [Y] that [Z]" (weak opener pattern)

### 7. Tone Consistency (calibrated by `voice.tone`)

Review entire article for tone drift:
- Casual (0-3): Conversational, contractions okay, "you" and "I"
- Balanced (4-6): Professional but approachable
- Professional (7-10): Formal, minimal contractions, third person acceptable

Flag sections where tone shifts unexpectedly.

### 8. Prose Tightening (always applied)

**Remove:**
- Redundant words ("very unique" → "unique")
- Weasel words ("somewhat," "quite," "rather")
- Unnecessary qualifiers ("I think," "I believe" — unless voice calls for it)
- Repeated words in close proximity

**Improve:**
- Passive voice → active voice (where appropriate)
- Long sentences → break into shorter ones
- Weak verbs → stronger alternatives

### 9. Spelling & Grammar (always applied)

- Fix typos
- Correct grammar errors
- Ensure consistent punctuation style

### 10. Flow & Transitions

- Ensure smooth transitions between sections
- Check that each section connects logically to the next
- Break up walls of text (no paragraphs > 5-6 sentences)

## Output Summary

After completing the editor pass, provide a summary of changes:

```
Editorial pass complete! Here's what I updated:

**Content Enhancements:**
- Added comparison table in Section 2 (based on style guide: examples="some")
- Added code snippet example in Section 4
- Added 1 blockquote in Section 1 to emphasize key insight (based on style guide: blockquotes="occasional")

**Formatting:**
- Added 2 bulleted lists
- Bolded 5 key terms at first mention
- Applied moderate visual breaks (standard paragraph lengths per style guide)

**Tightening:**
- Removed 3 instances of "Additionally"
- Replaced 2 em dashes with commas
- Shortened 4 long sentences

**Fixes:**
- Corrected 2 typos
- Fixed 1 grammar issue

📄 Review the edited version: cody-projects/article-writer/drafts/[id]-editorpass.md
📄 Original preserved at: cody-projects/article-writer/drafts/[id].md

Approve the changes, or let me know what to adjust.
```

## Iteration

If user requests changes:
1. Update `[id]-editorpass.md` directly
2. Keep original `[id].md` untouched
3. Show updated summary of what changed
