# Style Guide Workflow

This workflow guides users through creating or editing a style guide.

## Triggers

- "create a new writing style"
- "create a new article style called X"
- "edit my X style"
- "update the X writing style"

## Workflow Phases

### Phase 0: Recommendation Offer (Optional)

Before starting configuration, offer AI-recommended settings:

```
I can suggest recommended style settings based on your goals, or we can configure everything from scratch.

Would you like me to recommend settings based on:
- Your writing purpose (e.g., "technical tutorials for developers")
- Your target audience (e.g., "enterprise decision-makers")
- Example articles you admire

Or would you prefer to configure all settings manually?
```

If user wants recommendations:
1. Gather purpose/audience/examples
2. Suggest complete style guide settings
3. Present for review and adjustment
4. Skip to Phase 2 (Review Settings)

If user wants manual configuration, proceed to Phase 1.

### Phase 1: Configuration

Guide the user through each category. These can be set in any order, but present them sequentially for clarity.

**Voice Settings:**
```
Let's configure the voice for your style.

1. Tone (0-10): How formal should the writing be?
   0 = Casual, conversational | 10 = Professional, formal

2. Humor (0-10): How much levity?
   0 = Serious, straightforward | 10 = Playful, witty

3. Opinion (0-10): How strong is your viewpoint?
   0 = Balanced, presenting multiple sides | 10 = Opinionated, clear stance

4. Technical (0-10): How deep into technical details?
   0 = Accessible to all | 10 = Technical depth assumed
```

**Formatting Settings:**
```
Now let's set formatting preferences.

1. Emojis (0-10): Emoji usage?
   0 = None | 10 = Frequent

2. EM Dashes (0-10): Em dash frequency?
   0 = Avoid entirely | 10 = Use freely
   (Note: Overuse is a common AI tell)

3. Blockquotes: How often to use blockquotes/pull quotes?
   - Never: Don't use blockquotes
   - Rare: Very occasional use
   - Occasional: Use where they add value
   - Frequent: Actively look for opportunities
```

**Structure Settings:**
```
Let's define article structure.

Opening style (select one or more):
- Direct: State the main point immediately
- Contextual: Set the scene first
- Narrative: Open with a story
- Tension: Create stakes, pose a problem

Closing style (select one or more):
- Summary: Recap key points
- Call to Action: Tell reader what to do
- Open Question: Leave them thinking
- Callback: Reference the opening
- Provocation: Challenge assumptions
- Key Takeaways: Bullet list of main insights

Visual Breaks: How much white space and paragraph spacing?
- Minimal: Dense prose, longer paragraphs
- Moderate: Balanced spacing, standard length
- Generous: Short paragraphs, more breathing room

Examples: Default preference for including examples?
- None: Minimal examples, rely on explanation
- Some: Occasional examples where helpful
- Many: Liberal use of examples

Example Types (if using examples, select preferred types):
- Lists: Bulleted or numbered lists
- Tables: Comparison tables, data tables
- Diagrams: Flowcharts, visual models
- Code Snippets: Code examples (technical content)
- Quotes: Pull quotes, expert citations
- Case Studies: Real-world scenarios
```

**Context Settings:**
```
Finally, let's set the context.

1. Author Role: How do you want to be positioned?
   (e.g., "AI Educator", "Startup Founder", "Product Manager")

2. Author Topic Knowledge (0-10):
   0 = Learning alongside reader | 10 = Established expert

3. Audience Role: Who are you writing for?
   (e.g., "Enterprise PMs", "Indie Hackers", "Technical Leaders")

4. Audience Topic Knowledge (0-10):
   0 = New to the topic | 10 = Deep expertise

5. Author-Audience Relationship (0-10):
   0 = Peer, equal footing | 10 = Expert teaching
```

### Phase 2: Review Settings

Present the style guide settings for approval (without name/description yet):

```
Here's your style guide configuration:

**Voice:**
- Tone: 7/10 (leaning professional)
- Humor: 3/10 (mostly serious)
- Opinion: 8/10 (opinionated)
- Technical: 5/10 (balanced)

**Formatting:**
- Emojis: 0/10 (none)
- EM Dashes: 2/10 (minimal)
- Blockquotes: Occasional

**Structure:**
- Opening: Narrative + Tension
- Closing: Callback + Call to Action
- Visual Breaks: Moderate
- Examples: Some
- Example Types: Lists, Code Snippets, Quotes

**Context:**
- Author Role: AI Educator and Startup Founder
- Author Knowledge: 8/10
- Audience Role: Enterprise Product Managers
- Audience Knowledge: 4/10
- Relationship: 7/10 (expert positioning)

Does this look correct, or would you like to adjust anything?
```

### Phase 3: Name & Description

After settings are approved, ask for name and description. Suggest options but require user approval.

```
Great! Now let's name this style.

**Suggested name:** "Professional LinkedIn"
**Suggested description:** "For thought leadership articles targeting enterprise product managers"

Would you like to use these, or would you prefer different name/description?
```

Wait for user to approve or provide alternatives for both name and description.

### Phase 4: Final Confirmation & Save

Show the complete style with approved name and description before saving:

```
Here's your final style guide:

**Name:** Professional LinkedIn
**Description:** For thought leadership articles targeting enterprise product managers

[Show all settings again]

Ready to save? Say "save" to confirm, or tell me what to adjust.
```

On confirmation:
1. Generate filename from style name (kebab-case)
2. Validate all required fields
3. Save to `cody-projects/article-writer/styles/[name].json`
4. Confirm: "Saved style guide as `professional-linkedin.json`"

## Style Management Commands

### List Styles
Trigger: "list my writing styles", "show my styles"

Action: List all JSON files in `cody-projects/article-writer/styles/`

### Edit Style
Trigger: "edit my X style"

Action:
1. Load the style JSON
2. Show current configuration
3. Ask what to change
4. Update and save

### Delete Style
Trigger: "delete the X style"

Action:
1. Confirm deletion: "Are you sure you want to delete 'X'? This cannot be undone."
2. On confirmation, remove the JSON file
