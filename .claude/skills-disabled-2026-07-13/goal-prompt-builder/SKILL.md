---
name: goal-prompt-builder
description: Build high-quality /goal commands for OpenAI Codex CLI 0.128+ that maximize audit-friendliness and minimize false-completion. Use this skill whenever the user wants to write, draft, generate, improve, or refine a /goal prompt — even if they don't say "skill" — including phrases like "help me write a goal", "design a goal for X", "review my goal command", "make a goal for this repo", or any request involving long-running Codex tasks. Also trigger when the user mentions Ralph loop, persistent agent objectives, or asks Codex to "keep working until done". Produces a complete, copy-pasteable /goal command using the 5-section golden template (Objective/Scope/Constraints/Done when/Stop if), supports three interaction modes (step-by-step, full-description, hybrid), auto-detects project type (Node/Python/Swift/Go/Rust/static) by inspecting filesystem or repo URL, reads AGENTS.md/CLAUDE.md if present, and predicts audit-friendliness before output.
---

# /goal Prompt Builder

This skill turns a fuzzy task description ("我想让 Codex 帮我重构鉴权") into a complete, audit-friendly `/goal` command that's ready to paste into Codex CLI 0.128+.

## Why this skill exists

Codex 0.128 added `/goal` as a persistent objective with a runtime-injected audit prompt (`continuation.md`). The audit prompt forces the model to build a "prompt-to-artifact checklist" — but **only if the user's goal text can be mapped to one**. Vague goals produce vague checklists, which produce false completions. This skill exists to make sure every `/goal` you generate has the structure that lets the audit mechanism actually work.

## The golden template (5 sections, in this order)

Every `/goal` Claude generates with this skill follows this structure exactly:

```
/goal <objective>.

[Optional: First action: read X, Y, Z and report counts. Wait for ack.]

Scope: <files / subsystem / feature area>.

Constraints:
  - <what not to change>
  - <compatibility / permission boundaries>
  - <project-specific rules from AGENTS.md / CLAUDE.md>

Done when:
  1. <verifiable artifact 1 — cite file or command>
  2. <verifiable artifact 2>
  ...

Stop if:
  - <mechanically detectable condition 1>
  - <mechanically detectable condition 2>
  ...

Use a token budget of <N> tokens for this goal.
```

**Why this order**: matches `continuation.md`'s expected reading flow — objective first, then scope to bound the search, then constraints to prune options, then acceptance to define success, then stop-if as runtime guards.

## Workflow

When this skill triggers, walk the user through these 6 steps. Step 0 (interaction mode) and Step 1 (project detection) happen automatically — Step 0 needs one user choice, Step 1 needs zero if filesystem is accessible. Don't skip steps unless the user explicitly says "I'll fill it in myself, just give me the template".

### Step 0: Pick interaction mode

This skill supports three interaction modes. Ask **once** at the start:

> 你希望用哪种方式生成 /goal？
> - **A. 询问式** — 我一段一段问你（最稳，适合第一次写 /goal）
> - **B. 全描述式** — 你一句话描述需求，我拆解后只问你确认不确定的地方（最快，适合熟手）
> - **C. 混合式（默认）** — 先选场景模板，再问 3-5 个关键问题（推荐）

Once chosen, follow the matching flow:

- **A. 询问式** → Step 1 → Step 2 → Step 3a → 3b → 3c → 3d → 3e → Step 4 → Step 5 (each input gathered separately)
- **B. 全描述式** → Step 1 → ask "用一段话描述你想做什么 / scope / 验收 / 不希望发生什么" → parse into 5 sections → Step 4 → ask user to confirm only the gaps → Step 5
- **C. 混合式** → Step 1 → Step 2 → Step 3 (batched: ask all missing fields at once) → Step 4 → Step 5

Mode B is most powerful when the user has thought about the task. Mode A is safest when they haven't. Mode C is the default sweet spot.

If the user doesn't answer this question explicitly, default to mode C and proceed.

### Step 1: Detect (don't ask) the project type

**Auto-detection comes first. Only fall back to asking if detection fails.**

Run this detection sequence:

1. **Check the conversation context.** Has the user already provided a repo URL, file path, or code snippet? Read those for hints first.

2. **Probe the filesystem** (if you have file tools and the user is in a project directory):
   - `package.json` exists → **Node / TypeScript**
   - `pyproject.toml` or `requirements.txt` or `setup.py` → **Python**
   - `*.xcodeproj/` or `Package.swift` → **Swift / iOS**
   - `Cargo.toml` → **Rust**
   - `go.mod` → **Go**
   - `astro.config.*` / `next.config.*` / `_config.yml` / `mkdocs.yml` → **Static / docs project**

3. **Fetch the repo if the user gave a URL** (only if web tools available):
   - GitHub URL → fetch the README + try to identify config files
   - Read `CLAUDE.md` and `AGENTS.md` if they exist (these are gold for Constraints)

4. **Fall back to asking** only if all auto-detection failed:
   > 我没法自动判断项目类型——这是 Node / Python / Swift / Go / Rust / 静态 / 其他？

When detection succeeds, **announce what you found** in one sentence so the user can correct you:

> 检测到这是一个 Swift / iOS 项目（找到 lingolearn.xcodeproj + CLAUDE.md）。
> 我会按 Swift 项目默认约束适配。如果不对，告诉我。

Then load the matching reference from `references/project-types.md`. **Also load any `CLAUDE.md` / `AGENTS.md` found** — these contain project-specific rules that override defaults.

### Step 2: Pick a scenario template

Ask: **这个 goal 属于哪种类型？**

| 选项 | 说明 |
|---|---|
| **A. 重构** | 改一个文件 / 子系统 |
| **B. 新功能实现** | 已有 SDD spec 的功能 |
| **C. 批量补测试 / 修 bug** | 重复型任务，可枚举来源 |
| **D. 代码考古 / 研究** | 只读不动手 |
| **E. UI / 行为 audit** | 对照文档审实现 |
| **F. 守门员 review** | 评估能否合并，不修改 |
| **G. 自定义** | 让我描述 |

Each option maps to a different default skeleton — see `references/scenarios.md` for the full templates.

### Step 3: Gather the 5 inputs (in this order)

Ask only what's still missing. Don't ask all 5 at once — ask incrementally so the user can think.

**3a. Objective (一句话)**
- One sentence describing what changes by the end.
- If the user gives a verb-less noun phrase ("Cohere rerank support"), turn it into a verb phrase ("Add Cohere rerank support to retrieval pipeline").
- Reject vague verbs like "improve", "optimize", "clean up" — ask for the concrete change.

**3b. Scope (改什么、不改什么)**
- Which files / directories / subsystems are in play
- For brownfield projects: probe whether v1.x beta files or sensitive modules exist that should be off-limits

**3c. Constraints (硬约束)**
- Pull from AGENTS.md / CLAUDE.md if available
- Add project-type defaults from the loaded reference (e.g., for Swift: "do not modify project.pbxproj")
- Ask if there's a "MUST NOT modify" list

**3d. Done when (验收清单)**
- This is the most important section. Push back hard if items are vague.
- Each item must cite a file, command, test name, or measurable artifact.
- Replace "测试通过" → "`<exact command>` exits 0; paste summary"
- Replace "做完" → enumerate the deliverables
- Aim for 5-8 items; fewer than 3 is a red flag

**3e. Stop if (停止条件)**
- Each must be mechanically detectable
- Include project-type defaults (e.g., for Node: "needs npm install for new dep")
- Include a regression guard: "existing tests start failing — do not fix by editing tests"

### Step 4: Predict audit-friendliness

Before showing the final command, internally score it (don't show the math, just the verdict):

- **Acceptance count**: 0 = bad, 1-2 = warn, 3-5 = good, 6-8 = excellent
- **Vague verbs detected**: "improve", "optimize", "全部", "彻底", "all", "everything" → flag
- **Stop-if specificity**: "if unclear" = bad, "if file X appears in git diff" = good
- **Token budget present**: missing = warn
- **Mechanical verifiability**: every Done-when item has a cite-able artifact = good

If score is below ~70%, **don't ship the command yet**. Instead, surface the weak spots and ask the user to refine. Be specific:

> ⚠ 我发现三处可以加强的地方：
> 1. Done when 第 2 条"测试覆盖" → 改成"测试名称 + 退出码"会更准
> 2. Stop if 缺少"现有测试 regression"兜底
> 3. Token 预算未指定，建议 80K（基于 scope 大小）

### Step 5: Render and cite design choices

When all checks pass, render the final `/goal` in a code block (so it's copy-pasteable) and follow with a **brief** explanation of the key design choices — not a tutorial, just enough so the user knows why each choice was made.

Format:

```
/goal <full command here>
```

**几个关键设计选择**：
- 为什么 Done when 第 N 条这么写
- 为什么 Stop if 包含某条
- 为什么预算定这个数

Keep this explanation under 8 short lines. The user is here for the command, not a lecture.

## Project type loading

When the project type is known, read the corresponding reference:

- Node / TypeScript → `references/project-types.md` (Node section)
- Python → `references/project-types.md` (Python section)
- Swift → `references/project-types.md` (Swift section)
- Go → `references/project-types.md` (Go section)
- Rust → `references/project-types.md` (Rust section)
- Static / docs → `references/project-types.md` (Static section)

Each section provides:
- Default test command with full flags
- Default build / type-check command
- Project-type-specific Stop-if bullets to include
- Common false-completion traps to guard against

## Scenario templates

For the chosen scenario, read the corresponding skeleton:

- A. 重构 → `references/scenarios.md` § Refactor
- B. 新功能实现 → `references/scenarios.md` § Feature
- C. 批量补测试 / 修 bug → `references/scenarios.md` § Batch
- D. 代码考古 → `references/scenarios.md` § Archaeology
- E. UI / 行为 audit → `references/scenarios.md` § UI Audit
- F. 守门员 review → `references/scenarios.md` § Gatekeeper
- G. 自定义 → use bare 5-section template, no skeleton

Each scenario has its own emphasis — e.g., archaeology goals emphasize Constraints (禁区), feature goals emphasize "First action: read SPEC + report counts".

## Worked examples

When the user's case is ambiguous about how to fill a section, consult `references/examples.md`. It contains 5 end-to-end transformations (vague request → final command) covering the most common patterns:

- Refactor (Node/TS) — cleanest baseline
- Feature with SDD spec (Swift) — most heavily constrained
- Vague request → push back instead of rendering — when *not* to render
- Archaeology (static / docs project) — read-only goals
- "Just give me the template" — when to skip the interview

Especially read example 3 for guidance on when to refuse rendering. Don't ship a goal you can't defend — surface the weak spots and ask for refinement first.

## Hard rules (always follow)

These are non-negotiable. They come from `continuation.md`'s actual behavior.

1. **Never write Stop-if as "if unclear, stop"** — that's not mechanically detectable. Ask the user to enumerate concrete conditions.
2. **Never let "all / everything / 全部 / 彻底" through** — flag and ask for a number or enumerable source.
3. **Always include a token budget** — missing budget = no soft stop = potential runaway.
4. **Always include a "no test-rewriting" stop-if** for any goal that touches tested code: "Existing tests start failing — this is a regression, do not 'fix' by editing tests."
5. **For SDD-driven goals (scenario B), the first action is always "read X files and report counts"** — bypasses `@filename` reference uncertainty and exposes loading failures early.
6. **For brownfield projects, always ask about MUST NOT modify list** — the absence of one is the #1 cause of scope creep.

## Common failure modes to coach the user through

- **"测试通过"做验收**: too vague. Force into "exact command + exit code + paste summary".
- **没有 Stop if**: goal is a one-way door. Add at least 3 mechanically detectable conditions.
- **预算 > 300K**: too big to audit reliably. Suggest splitting into two goals.
- **Scope = "整个仓库"**: too wide. Push for a specific directory or subsystem.
- **"我之后再补 acceptance"**: this is the failure pattern. Refuse to render until at least 3 items exist.

## What this skill does NOT do

- Does not run the `/goal` for the user — it only generates the text
- Does not validate the project state (no `git status` checks, no test runs)
- Does not handle Codex versions older than 0.128 — `/goal` doesn't exist there
- Does not generate prompts for `/plan`, `/compact`, or other Codex commands

## Output format reminder

Final output is **always**:
1. A markdown code block containing the `/goal` command (so the user can copy)
2. A short bullet list of the key design choices (no more than 8 short lines)
3. **Optional**: a one-line "audit-friendliness verdict" (e.g., "审计友好度：优秀 · 7 项验收 · 0 风险标记")

That's it. No long lecture. The user is here for a command.
