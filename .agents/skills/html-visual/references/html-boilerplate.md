# HTML Boilerplate

This template provides **structure only**. Colors, fonts, and tone should be freely decided based on context.

```html
<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <!-- Font: Choose appropriate Google Fonts for context -->
  <!-- CDN: Add only necessary libraries -->
  <style>
    /* ── Theme palette: Decide colors based on context ── */
    :root[data-theme="dark"] {
      --color-bg: /* based on context */;
      --color-surface: /* based on context */;
      --color-text: /* based on context */;
      --color-text-muted: /* based on context */;
      --color-accent: /* based on context */;
      --color-border: /* based on context */;
    }
    :root[data-theme="light"] {
      --color-bg: /* based on context */;
      --color-surface: /* based on context */;
      --color-text: /* based on context */;
      --color-text-muted: /* based on context */;
      --color-accent: /* based on context */;
      --color-border: /* based on context */;
    }

    /* ── Reset ── */
    *, *::before, *::after { margin: 0; padding: 0; box-sizing: border-box; }

    body {
      background: var(--color-bg);
      color: var(--color-text);
      min-height: 100vh;
      transition: background 0.3s ease, color 0.3s ease;
      -webkit-font-smoothing: antialiased;
    }

    /* ── Theme toggle ── */
    .theme-toggle {
      position: fixed;
      top: 1rem;
      right: 1rem;
      z-index: 1000;
      background: var(--color-surface);
      border: 1px solid var(--color-border);
      border-radius: 8px;
      padding: 0.5rem 0.75rem;
      cursor: pointer;
      color: var(--color-text);
      font-size: 1.1rem;
      transition: background 0.2s, border-color 0.2s;
    }
    .theme-toggle:hover { border-color: var(--color-accent); }
    .theme-toggle:focus-visible { outline: 2px solid var(--color-accent); outline-offset: 2px; }
  </style>
</head>
<body>
  <button class="theme-toggle" aria-label="Toggle theme">
    <span class="theme-icon">🌙</span>
  </button>

  <!-- {content} -->

  <script>
    document.querySelector('.theme-toggle').addEventListener('click', () => {
      const html = document.documentElement;
      const isDark = html.dataset.theme === 'dark';
      html.dataset.theme = isDark ? 'light' : 'dark';
      document.querySelector('.theme-icon').textContent = isDark ? '☀️' : '🌙';
    });
  </script>
</body>
</html>
```

## Enforced (Structure)

- Dark/light switching mechanism based on `data-theme` attribute
- CSS variable naming convention (`--color-bg`, `--color-surface`, `--color-text`, etc.)
- Toggle button position at top-right
- `focus-visible` focus indicator

## Free (Style)

- Color palette — freely decide based on context
- Fonts — choose appropriate Google Fonts or system fonts for context
- Layout — freely choose container, grid, flex, etc. based on type
- Motion — only as needed. Staggered reveal is optional
- Additional CSS variables — add freely as needed
