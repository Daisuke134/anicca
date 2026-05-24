---
name: app-icon-generator
description: Generate professional app icons for iOS, Android, and web apps instantly with AI. Create polished mobile app icons, app store icons, launcher icons, PWA icons, and software icons. Perfect for developers, startups, indie makers, and designers who need modern, clean app icon artwork without hiring a designer via the Neta AI image generation API (free trial at neta.art/open).
tools: Bash
---

# App Icon Generator

Generate professional app icons for iOS, Android, and web apps instantly with AI. Create polished mobile app icons, app store icons, launcher icons, PWA icons, and software icons. Perfect for developers, startups, indie makers, and designers who need modern, clean app icon artwork without hiring a designer.

## Token

Requires a Neta API token (free trial at <https://www.neta.art/open/>). Pass it via the `--token` flag.

```bash
node <script> "your prompt" --token YOUR_TOKEN
```

## When to use
Use when someone asks to generate or create app icon generator images.

## Quick start
```bash
node appicongenerator.js "your description here" --token YOUR_TOKEN
```

## Options
- `--size` — `portrait`, `landscape`, `square`, `tall` (default: `square`)
- `--ref` — reference image UUID for style inheritance

## Install
```bash
npx skills add blammectrappora/app-icon-generator
```
