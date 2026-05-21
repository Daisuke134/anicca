# Remotion動画制作ガイド

Remotionを使ってAniccaのマーケティング動画を作るためのガイド。

## セットアップ

### プロジェクト場所
```
/Users/cbns03/Downloads/anicca-videos
```

### スキル場所（Claude Code / Cursor / Codex 共通）
```
.claude/skills/remotion/
.cursor/skills/remotion/
.codex/skills/remotion/
```

### 起動コマンド
```bash
cd /Users/cbns03/Downloads/anicca-videos
npm run dev          # Studio起動 (http://localhost:3000)
npx remotion render <CompositionId> out/<filename>.mp4  # レンダリング
```

---

## 作成済みコンポジション

| ID | 説明 | サイズ |
|----|------|--------|
| `HelloWorld` | サンプル | 1920x1080 |
| `OnlyLogo` | Remotionロゴのみ | 1920x1080 |
| `AniccaLogo` | Aniccaロゴ回転 | 1080x1080 (Instagram用) |

---

## よく使うプロンプト例

### 基本アニメーション
```
「黒背景に白テキストで "Anicca" がフェードインする3秒の動画」
```

### ロゴアニメーション
```
「Aniccaロゴが中央でフェードイン後、ゆっくり回転する5秒動画」
```

### TikTok/Reels用
```
「縦型(1080x1920)で、上から文字がスライドインして
"6年間、何も変われなかった"
というフックが表示される動画」
```

### ターミナル風アニメーション
```
「macOSターミナル風のUIで、コマンドがタイプされていくアニメーション」
```

### キャプション付き
```
「音声ファイルに合わせてTikTokスタイルのワードハイライト字幕を付ける」
```

---

## 技術メモ

### フレームレート・尺
- **fps**: 30（標準）または60（滑らか）
- **5秒動画**: 150フレーム（30fps）
- **10秒動画**: 300フレーム（30fps）

### サイズ
| 用途 | サイズ |
|------|--------|
| YouTube/横動画 | 1920x1080 |
| Instagram/TikTok正方形 | 1080x1080 |
| TikTok/Reels/Shorts | 1080x1920 |

### アセット場所
- ロゴ: `/Users/cbns03/Downloads/anicca-videos/public/anicca-logo.png`
- フォント: Google Fontsまたは`public/`に配置

---

## Remotion基本API

```tsx
import {
  useCurrentFrame,      // 現在のフレーム番号
  useVideoConfig,       // fps, width, height, durationInFrames
  interpolate,          // 値の補間
  spring,               // スプリングアニメーション
  Sequence,             // タイミング制御
  AbsoluteFill,         // フルスクリーンコンテナ
  Img,                  // 画像
  staticFile,           // publicフォルダのファイル参照
} from "remotion";
```

### フェードイン例
```tsx
const frame = useCurrentFrame();
const opacity = interpolate(frame, [0, 30], [0, 1]);
```

### スプリング例
```tsx
const { fps } = useVideoConfig();
const scale = spring({ frame, fps, config: { damping: 100 } });
```

---

## スキルルール参照

詳細なアニメーションパターンは以下を参照：
- `.claude/skills/remotion/rules/animations.md`
- `.claude/skills/remotion/rules/text-animations.md`
- `.claude/skills/remotion/rules/transitions.md`

---

## 出力先

レンダリング済み動画：
```
/Users/cbns03/Downloads/anicca-videos/out/
```

---

最終更新: 2026-01-22
