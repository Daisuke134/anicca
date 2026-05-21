# Common Rules

## Core Principles

1. **Single HTML file** — inline CSS + JS
2. **Use CDN libraries when needed** (see recommended list below)
3. **Must be interactive** — not a static image, but actually manipulable
4. **Dark/light mode toggle** — Toggle button at top-right. Default is dark
5. **File save**: Save as `{type}-{kebab-case-name}.html` in the project root

## Aesthetics

### Forbidden Patterns

- No repeating the same default fonts (Inter, Arial, Roboto) every time
- No meaningless purple/blue gradient backgrounds
- No mindless repetition of rounded cards + shadows
- No meaningless decorative elements (floating dots, random shapes)

### Style Autonomy

Fonts, colors, layout, and motion should be **freely decided based on context**.
Follow these principles:

- **Fonts**: Choose what fits the context. Max 2 families (heading + body)
- **Colors**: Define palette with CSS variables (`--color-bg`, `--color-surface`, `--color-text`, `--color-accent`, etc.). Define for both dark/light
- **Motion**: Prefer CSS `transition`. Keep it subtle. Use consistent easing
- **If project context exists**: Follow the existing design system (colors, fonts, tone) first

## Quality Standards

- **Rendering**: Crisp rendering with SVG or Canvas. Choose what fits the type
- **Interaction**: Drag, tap/click, hover highlight, toggle — context-appropriate controls
- **Transitions**: Smooth animations for state changes, screen transitions, element enter/exit
- **Layout**: Prevent overlapping, proper spacing, responsive considerations

## Accessibility

- **Keyboard navigation**: `Tab` to move between interactive elements, `Enter` to select/activate
- **ARIA labels**: Provide `aria-label` on interactive elements (buttons, links, etc.)
- **Color contrast**: WCAG AA standard (4.5:1) or above
- **Focus indicator**: Clear outline on keyboard focus via `:focus-visible`

## Recommended CDN Libraries

Use only when needed. Do not add CDN if pure SVG/CSS is sufficient.

| Library | CDN URL | Purpose |
|---------|---------|---------|
| D3.js v7 | `https://d3js.org/d3.v7.min.js` | Custom visualizations, force graph, heatmap |
| Mermaid 11 | `https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js` | Diagrams (flow, ER, sequence, gantt, mindmap) |
| Chart.js 4 | `https://cdn.jsdelivr.net/npm/chart.js@4` | Standard charts (bar, line, pie, scatter) |
| Reveal.js 5 | `https://cdn.jsdelivr.net/npm/reveal.js@5/dist/reveal.esm.js` | Presentation slides |
| Tailwind CSS | `https://cdn.tailwindcss.com` | UI styling (mockup, dashboard) |

## Common Mistakes to Avoid

- Do not use **smart quotes** (`\u201c` `\u201d`) in HTML attributes. Always use straight quotes (`"`)
- Always include `xmlns="http://www.w3.org/2000/svg"` on SVG elements
- Close all tags properly. Watch for unclosed tags
- Prefer `addEventListener` over inline event handlers (`onclick="..."`)
- Avoid duplicate `id` values. Use unique suffixes for dynamically generated elements
