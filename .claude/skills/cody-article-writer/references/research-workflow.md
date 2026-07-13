# Research Workflow

This document provides detailed instructions for the 6 research integration points in the article writing workflow.

## Table of Contents

- [Research Integration Points](#research-integration-points)
  - [Point 1: Exploratory Research (Phase 1 - Topic Ideation)](#point-1-exploratory-research-phase-1---topic-ideation)
  - [Point 2: Research Planning Question (Phase 2)](#point-2-research-planning-question-phase-2)
  - [Point 3: Research Configuration (Phase 2 continued)](#point-3-research-configuration-phase-2-continued)
  - [Point 4: Use Sources During Thesis Development (Phase 4)](#point-4-use-sources-during-thesis-development-phase-4)
  - [Point 5: Use Sources During Outline Development (Phase 5)](#point-5-use-sources-during-outline-development-phase-5)
  - [Point 6: Use Sources and Insert Citations During Writing (Phase 7)](#point-6-use-sources-and-insert-citations-during-writing-phase-7)
- [Citation Format Reference](#citation-format-reference)
- [Research Workflow States](#research-workflow-states)
- [Troubleshooting](#troubleshooting)

## Research Integration Points

### Point 1: Exploratory Research (Phase 1 - Topic Ideation)

**When:** Always happens during Topic Ideation, regardless of whether user wants comprehensive research later.

**Why:** AI's training data may be outdated. Current web information helps refine topics and identify viable angles.

**Tools:** WebSearch

**Process:**

1. **After user provides initial topic idea, perform 3-5 exploratory searches:**
   ```
   Example topic: "AI in healthcare"

   Searches to perform:
   - "AI healthcare 2025 trends"
   - "AI medical diagnosis accuracy"
   - "healthcare AI adoption statistics 2025"
   ```

2. **Use search results to inform ideation conversation:**
   - Identify current trends and angles
   - Understand what's been covered recently
   - Find data points that make topic interesting
   - Discover unique perspectives

3. **Save to draft state:**
   ```json
   {
     "topic": {
       "exploratory_research": {
         "searches_performed": [
           "AI healthcare 2025 trends",
           "AI medical diagnosis accuracy",
           "healthcare AI adoption statistics 2025"
         ],
         "sources_reviewed": [
           "https://healthtech.com/ai-trends-2025",
           "https://jamanetwork.com/ai-diagnosis-study",
           "https://forbes.com/healthcare-ai-stats"
         ],
         "date": "2025-01-05T10:30:00Z"
       }
     }
   }
   ```

**Important:** Don't fetch full content with WebFetch at this stage—just use search snippets. This is exploratory, not comprehensive research.

---

### Point 2: Research Planning Question (Phase 2)

**When:** After topic is refined and user says "Ready to form thesis"

**Why:** Not all articles need comprehensive research. Give user control over research depth.

**Process:**

```
Your topic is refined and ready: "[refined topic]"

Do you want to gather comprehensive research sources for this article?

This means I'll:
- Search for authoritative sources on your topic
- Present them for your approval
- Use them throughout writing to inform content
- Optionally add citations in the final article

Would you like to do comprehensive research for this article?
```

**If NO:**
- Set `research.depth = "none"`
- Set `research.approved_sources = []`
- Set `research.citations_used = []`
- Skip to Phase 3: Style Guide Selection
- Exploratory research from Phase 1 is still preserved

**If YES:**
- Proceed to Point 3 (Research Configuration)

---

### Point 3: Research Configuration (Phase 2 continued)

**When:** User said YES to comprehensive research

**Tools:** WebSearch, WebFetch

**Process:**

#### Step 1: Determine Research Depth

```
How much research do you need for this article?

- Light: A few key sources for credibility (1-5 sources)
- Medium: Multiple sources, key claims cited (6-11 sources)
- Heavy: Extensively researched, most claims cited (12-20 sources)
```

Save response as `research.depth = "light"|"medium"|"heavy"`

#### Step 2: Gather Sources with WebSearch

Perform targeted searches based on refined topic. Number of searches depends on depth:
- Light: 2-3 searches
- Medium: 4-6 searches
- Heavy: 7-10 searches

Example for "AI radiology error rates vs human radiologists":
```
Searches:
- "AI radiology diagnostic accuracy study 2024"
- "FDA approval AI medical imaging"
- "AI vs human radiologist error rates"
- "limitations AI diagnostic systems"
```

From search results, compile 5-25 potential sources (adjust based on depth: 5-8 for light, 10-15 for medium, 15-25 for heavy).

#### Step 3: Present Sources for User Approval

```
I found these sources for your article on "[topic]":

1. ☐ "Comparative Analysis of AI vs Human Diagnostic Accuracy"
   Domain: jamanetwork.com
   Relevance: Primary study with error rate data
   URL: https://jamanetwork.com/...

2. ☐ "FDA Guidelines for AI-Assisted Diagnostic Tools"
   Domain: fda.gov
   Relevance: Regulatory requirements
   URL: https://www.fda.gov/...

3. ☐ "Market Trends in AI Medical Imaging"
   Domain: healthtechmagazine.net
   Relevance: Industry adoption statistics
   URL: https://healthtechmagazine.net/...

[... more sources ...]

Review these sources:
- Which ones do you want to keep? (I'll use them in your article)
- Are there any I should remove?
- Do you have specific URLs you want me to add?
- Which sources are REQUIRED (must be incorporated) vs. optional?
```

#### Step 4: Mark Required vs. Optional

For each source user wants to keep, ask:
```
For "[Source Title]":
- Required (must incorporate this in the article)
- Optional (use if relevant)
```

Or simpler: "Which of these sources are required (must be used)? The rest will be optional."

#### Step 5: Fetch Approved Sources with WebFetch

For each approved source:
1. Use WebFetch to read the URL
2. Extract:
   - Title (from page)
   - Author (if available in page metadata)
   - Date (if available)
   - Domain (from URL)
   - Relevant excerpt (2-3 paragraphs of most relevant content)
3. Save to `approved_sources` array

**Handling fetch failures:**
- If WebFetch fails (paywall, 404, etc.), notify user and ask if they want to:
  - Provide the content manually
  - Remove this source
  - Try an alternative URL

#### Step 6: Configure Citations

```
Do you want citations in your final exported article?

- Yes: I'll insert [^1], [^2] markers as I write and generate a References section
- No: I'll still use these sources to inform content, but won't show citation markers
```

Set `research.include_citations_in_export = true|false`
Set `research.citation_style = "footnotes"`

#### Final State:

```json
{
  "research": {
    "depth": "medium",
    "include_citations_in_export": true,
    "citation_style": "footnotes",
    "approved_sources": [
      {
        "url": "https://jamanetwork.com/...",
        "title": "Comparative Analysis of AI vs Human Diagnostic Accuracy",
        "author": "Dr. Sarah Chen",
        "date": "2024-03-15",
        "domain": "jamanetwork.com",
        "required": true,
        "relevance": "Primary study with error rate data",
        "excerpt": "AI systems demonstrated 94.2% accuracy compared to 91.8% for human radiologists in detecting lung nodules. The study analyzed 50,000 scans across 12 hospitals...",
        "accessed": "2025-01-05T14:20:00Z"
      },
      {
        "url": "https://www.fda.gov/...",
        "title": "FDA Guidelines for AI-Assisted Diagnostic Tools",
        "author": null,
        "date": "2023-11-20",
        "domain": "fda.gov",
        "required": true,
        "relevance": "Regulatory framework",
        "excerpt": "All AI diagnostic systems must demonstrate non-inferiority to board-certified radiologists through prospective clinical trials...",
        "accessed": "2025-01-05T14:22:00Z"
      },
      {
        "url": "https://healthtechmagazine.net/...",
        "title": "Market Trends in AI Medical Imaging",
        "author": "James Rodriguez",
        "date": "2024-01-10",
        "domain": "healthtechmagazine.net",
        "required": false,
        "relevance": "Industry statistics",
        "excerpt": "The AI medical imaging market is projected to reach $12.7B by 2027, driven by hospital adoption and improved accuracy rates...",
        "accessed": "2025-01-05T14:25:00Z"
      }
    ],
    "citations_used": []
  }
}
```

---

### Point 4: Use Sources During Thesis Development (Phase 4)

**When:** Developing title and thesis

**Condition:** Only if `research.depth != "none"`

**Process:**

1. **Review approved sources before generating thesis:**
   - Read `excerpt` field from each source
   - Identify key findings, data points, arguments
   - Note any contradictions or nuances

2. **Ensure thesis accommodates research:**
   - For **required sources**: thesis must reflect their findings
   - For **optional sources**: use if they strengthen thesis
   - Don't contradict well-supported source claims

3. **Example:**
   ```
   Required source says: "AI accuracy 94.2% vs human 91.8%"
   Required source says: "FDA requires non-inferiority to humans"

   Weak thesis: "AI will replace human radiologists"
   (Contradicts FDA requirement)

   Strong thesis: "While AI radiology systems now exceed human diagnostic
   accuracy in specific tasks, regulatory frameworks and edge case limitations
   mean the technology should augment rather than replace human radiologists."
   (Incorporates both required sources)
   ```

4. **If research gaps discovered during iteration:**
   - User may request additional sources
   - Perform new WebSearch, get approval, WebFetch
   - Add to `approved_sources` array

**Don't insert citations yet** - that happens during writing. Just use research to inform thesis.

---

### Point 5: Use Sources During Outline Development (Phase 5)

**When:** Creating article outline

**Condition:** Only if `research.depth != "none"`

**Process:**

1. **Review approved sources to plan structure:**
   - What evidence is available for each part of thesis?
   - Where do required sources fit naturally?
   - What order makes logical sense given the research?

2. **Structure outline to incorporate sources:**
   ```
   Example with 2 required sources:

   Required source 1: AI accuracy study
   Required source 2: FDA regulatory guidelines

   Outline:
   - Introduction (hook with accuracy stats from source 1)
   - The Accuracy Comparison (deep dive into source 1)
   - Regulatory Landscape (covers source 2)
   - Where AI Falls Short (balances the narrative)
   - Conclusion
   ```

3. **Verify all required sources have a home:**
   - Each required source should map to at least one section
   - If a required source doesn't fit, may need to revise outline or thesis

4. **If outline reveals research gaps:**
   - "This section needs data on X, but we don't have a source"
   - Offer to search for additional sources
   - Add to `approved_sources` if user approves

**Don't insert citations yet** - still just planning. Citations come during writing.

---

### Point 6: Use Sources and Insert Citations During Writing (Phase 7)

**When:** Writing article sections

**Condition:** Only if `research.depth != "none"`

**Tools:** No new web tools needed (use cached `approved_sources`)

**Process:**

#### Step 1: Reference Sources While Writing

For each section being written:

1. **Identify relevant sources for this section:**
   - Check which `approved_sources` have excerpts relevant to this section
   - Prioritize required sources

2. **Incorporate source information:**
   - Use data, quotes, findings from source excerpts
   - Paraphrase or quote as appropriate
   - Maintain accuracy to original source

3. **Ensure required sources are used:**
   - All sources marked `required: true` must appear somewhere in article
   - If a required source doesn't fit current section, ensure it fits elsewhere

#### Step 2: Insert Inline Citations (if enabled)

If `research.include_citations_in_export == true`:

1. **Add citation markers as you write:**
   ```markdown
   AI systems achieved 94.2% diagnostic accuracy—outperforming the 91.8%
   average of board-certified radiologists.[^1] The market is projected to
   reach $12.7 billion by 2027.[^2]
   ```

2. **Number citations sequentially:**
   - First source cited = `[^1]`
   - Second source cited = `[^2]`
   - Same source cited again = use same number

3. **Track citations in state:**
   As you insert citations, update `citations_used`:
   ```json
   {
     "citations_used": [
       {
         "source_url": "https://jamanetwork.com/...",
         "citation_count": 3,
         "cited_in_sections": ["introduction", "accuracy-comparison", "conclusion"]
       },
       {
         "source_url": "https://healthtechmagazine.net/...",
         "citation_count": 1,
         "cited_in_sections": ["introduction"]
       }
     ]
   }
   ```

4. **Store content with citations in JSON:**
   ```json
   {
     "sections": {
       "introduction": {
         "content": "AI systems achieved 94.2% accuracy.[^1] The market will reach $12.7B.[^2]",
         "status": "completed"
       }
     }
   }
   ```

#### Step 3: Verify Required Sources Used

Before declaring article complete:

1. **Check all required sources are cited:**
   ```
   Required sources check:
   ✅ Source 1 (cited 3 times in sections: intro, body, conclusion)
   ✅ Source 2 (cited 2 times in sections: regulatory, conclusion)
   ❌ Source 3 (not cited yet)

   Source 3 is marked as required but hasn't been used. Would you like me to:
   - Add it to an existing section
   - Skip it (mark as optional instead)
   ```

2. **Offer citation summary:**
   ```
   Your article used 7 of 10 approved sources:

   Required (all used): ✅
   - Source 1: 3 citations
   - Source 2: 2 citations

   Optional (4 of 7 used):
   - Source 3: 1 citation
   - Source 4: 2 citations
   - Source 5: 1 citation
   - Source 6: 1 citation

   Unused but available for editing:
   - Source 7, Source 8, Source 9
   ```

---

## Citation Format Reference

### Inline Citation Markers

Use markdown footnote syntax:
```markdown
This is a claim that needs a source.[^1]
```

Multiple claims, multiple sources:
```markdown
AI accuracy improved 15% in 2024.[^1] Adoption rates doubled.[^2]
```

Same source cited multiple times:
```markdown
The study found X.[^1] Later analysis confirmed Y.[^1]
```

### References Section Generation (at Export)

If user chooses to include citations at export, generate References section from `citations_used` array:

```markdown
## References

[^1]: Chen, S. (2024). "Comparative Analysis of AI vs Human Diagnostic Accuracy in Radiology." *JAMA Network*. https://jamanetwork.com/journals/jama/article/2023/ai-radiology-study

[^2]: Rodriguez, J. (2024). "Market Trends in AI Medical Imaging." *Health Tech Magazine*. https://healthtechmagazine.net/ai-radiology-trends

[^3]: "FDA Guidelines for AI-Assisted Diagnostic Tools." *FDA.gov*. https://www.fda.gov/medical-devices/ai-radiology-approval
```

**Format rules:**
- If author available: `Author. "Title." Domain. URL`
- If no author: `"Title." Domain. URL`
- If date available: Include in author line: `Author (YYYY).`
- Use markdown footnote syntax: `[^1]: ...`

---

## Research Workflow States

### No Research Path

```
Phase 1: Topic Ideation → exploratory research (always)
Phase 2: Research Planning → User says NO
└─ Set depth="none", skip to Phase 3

Phases 4-7: No research integration
Phase 12: Export → No citation handling
```

### Research Enabled Path

```
Phase 1: Topic Ideation → exploratory research (always)
Phase 2: Research Planning → User says YES → configure depth/sources/citations
Phase 4: Thesis → Use approved sources
Phase 5: Outline → Use approved sources
Phase 7: Writing → Use approved sources + insert citations
Phase 12: Export → Ask about including citations, generate References if yes
```

---

## Troubleshooting

### WebSearch returns no good results
- Try alternative search queries
- Ask user if they have specific sources in mind
- Broaden or narrow search terms

### WebFetch fails (paywall, 404, etc.)
- Notify user
- Ask if they can provide content manually
- Offer to find alternative source
- Remove source if not critical

### User wants to add sources mid-writing
- Any phase with research integration has iteration loop
- Can add sources during thesis, outline, or writing phases
- Perform WebSearch → user approval → WebFetch → add to approved_sources

### Required source doesn't fit anywhere
- During outline review, identify this issue
- Ask user: "This source is marked required but doesn't fit the current outline. Would you like to:"
  - Revise outline to include it
  - Mark it as optional instead
  - Revise thesis to accommodate it

### Citation numbering gets confusing
- Use simple sequential numbering as sources appear
- Track in `citations_used` array
- Don't worry about alphabetical ordering—footnotes use order of appearance
