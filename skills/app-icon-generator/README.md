# App Icon Generator

Generate professional app icons for iOS, Android, and web apps from text descriptions using AI. Create polished mobile app icons, app store icons, launcher icons, PWA icons, and software icons instantly -- perfect for developers, startups, indie makers, and designers who need modern, clean app icon artwork without hiring a designer.

Powered by the Neta AI image generation API (api.talesofai.com) -- the same service as neta.art/open.

## Install

```bash
npx skills add blammectrappora/app-icon-generator
```

or

```bash
clawhub install app-icon-generator
```

## Token Setup

This skill requires a Neta API token (free trial available at <https://www.neta.art/open/>).

Pass it via the `--token` flag:

```bash
node <script> "your prompt" --token YOUR_TOKEN
```

## Usage

Generate a square app icon (default):

```bash
node appicongenerator.js "professional app icon design, clean modern style, rounded corners, gradient background, centered symbol, iOS and Android app store ready, high detail, flat design with subtle depth and shadows" --token YOUR_TOKEN
```

Generate with a specific size:

```bash
node appicongenerator.js "minimalist calendar app icon, blue gradient, white date number" --size square --token YOUR_TOKEN
```

Generate using a reference image for style inheritance:

```bash
node appicongenerator.js "weather app icon matching brand style" --ref PICTURE_UUID --token YOUR_TOKEN
```

### Output

Returns a direct image URL.

## Options

| Flag | Description | Values | Default |
|------|-------------|--------|---------|
| `--token` | Neta API token (required) | Your API token | -- |
| `--size` | Image dimensions | `square`, `portrait`, `landscape`, `tall` | `square` |
| `--ref` | Reference image UUID for style inheritance | A picture UUID | -- |

### Size Reference

| Size | Dimensions |
|------|-----------|
| `square` | 1024 x 1024 |
| `portrait` | 832 x 1216 |
| `landscape` | 1216 x 832 |
| `tall` | 704 x 1408 |

This skill requires a Neta API token (free trial available at https://www.neta.art/open/).
