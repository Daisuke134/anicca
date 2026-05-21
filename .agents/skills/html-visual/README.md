# html-visual

Generates interactive single-file HTML visualizations — UI mockups, ERDs, flowcharts, data charts, presentations, and more.

## When to use

- Need a UI mockup or wireframe
- Visualize a database schema as an ERD
- Map out business logic as a flowchart
- Create a data chart, architecture diagram, or dashboard
- Build a quick presentation from content

## Supported types

`mockup` · `wireframe` · `erd` · `flow` · `chart` · `slides` · `arch` · `dashboard` · `timeline` · `mindmap` · `kanban` · `table`

## Usage

```
# UI mockup
/html-visual mockup login page

# Auto-generate ERD from a Prisma schema file
/html-visual erd schema.prisma

# Flowchart for a process
/html-visual flow payment approval process

# Data chart
/html-visual chart monthly revenue 2024

# Architecture diagram
/html-visual arch microservice overview

# Omit type — it will be inferred from context
/html-visual diagram the user signup flow
```

## How it works

1. Determines the visualization type (or infers it from context).
2. If a file path is given, analyzes the file first (e.g., Prisma schema → ERD).
3. Generates a single HTML file with dark/light mode toggle, draggable nodes, and responsive layout.
4. Opens the file in the browser.

## Installation

### Claude Code

```bash
claude plugin marketplace add 2ykwang/agent-skills
claude plugin install html-visual@2ykwang-agent-skills
```

### npx skills

```bash
npx skills add 2ykwang/agent-skills --skill html-visual
```
