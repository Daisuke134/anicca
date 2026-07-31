# Migrations

This file defines the migration chain for Cody Article Writer. Migrations run automatically when the skill version (from SKILL.md frontmatter) is newer than the user's stored version (from `cody-projects/article-writer/.cody-version`).

## How Migrations Work

1. Read skill version from SKILL.md frontmatter (e.g., "3.0")
2. Read `cody-projects/article-writer/.cody-version` (e.g., "2.0", or missing = "1.0")
3. If stored version < skill version, run each migration step in order between those versions
4. After all migrations complete, write current skill version to `.cody-version`
5. Summarize all changes to user in one message

New users with no existing data: skip migrations entirely, just write current version to `.cody-version` during Directory Setup.

## Migration Chain

### 2.0 → 3.0

**Humor slider inversion in style guides:**

The `voice.humor` field direction was reversed for clarity. Previously `0 = Playful, 10 = Serious` (counterintuitive — higher value meant less humor). Now `0 = Serious, 10 = Playful` (consistent with other sliders where higher = more of the named quality).

**Steps:**
1. Scan all JSON files in `cody-projects/article-writer/styles/`
2. For each style guide, invert the humor value: `new_value = 10 - old_value`
3. Save the updated file

**User notification:**
```
I've updated your style guides to v3.0 format. The humor scale now runs
0 (Serious) to 10 (Playful) — this aligns it with the other sliders where
higher values mean more of the named quality. Your settings have been
converted automatically with no change in behavior.

Updated styles: [list style names]
```
