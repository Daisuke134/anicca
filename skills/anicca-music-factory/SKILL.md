---
name: anicca-music-factory
description: 毎日1曲、瞑想用アンビエント音楽を作って DistroKid に上げる。04:00 JST cron で走る。
---

# Anicca Music Factory

毎日やること:

1. `~/.openclaw/skills/anicca-music-factory/config/prompt-rotation.json` を開いて、今日の曜日 (`date +%u`, 1=月〜7=日) の `day_N` の row を取る。`theme` / `title_seed` / `genre_primary` / `genre_secondary` / `suno_prompt` / `cover_prompt` が入ってる。

2. `~/.openclaw/skills/anicca-music-factory/state/catalog.json` で過去のタイトル一覧を見る。

3. 今日の `theme` と `title_seed` を眺めて、2〜4 語の英語タイトルを 1 個考える。瞑想/アンビエントのアルバムタイトルっぽい雰囲気で（例: *Empty Sky*, *Returning to Stillness*, *The River Remembers*, *528 Heart*）。catalog に既にあるタイトルとは被らせない。`peace` / `calm` / `zen` 単独は陳腐すぎるので避ける。

4. 走らせる:

```bash
TITLE="<考えたタイトル>" bash ~/.openclaw/skills/anicca-music-factory/scripts/00-run-daily.sh
```

これで Suno で音楽生成 → FAL で cover 画像生成 → DistroKid へアップ、まで全部やる。最後の stdout 1 行が Slack #metrics に投稿される。

成功:
```
📀 Day N: "Title" (theme) → DistroKid (release YYYY-MM-DD) | catalog: N tracks | HF: <hyperfollow url>
```

失敗:
```
❌ FAILED at step <name>: <one-line error>
```

失敗時は `$OUTDIR/.upload-err.log` / `.music-err.log` / `.cover-err.log` の最後 5 行も一緒に出す。

## 参考ファイル

| File | 役割 |
|------|-----|
| `scripts/00-run-daily.sh` | orchestrator |
| `scripts/01-generate-music.sh` | apiframe Suno V5 |
| `scripts/02-generate-cover.sh` | FAL FLUX 1.1 |
| `scripts/04-upload-distrokid.sh` | playwright-cli で DistroKid 自動アップロード |
| `config/prompt-rotation.json` | 曜日 × theme/seed/prompt/genre |
| `state/catalog.json` | これまでのトラック一覧（タイトル重複チェックに使う） |
| `state/daily-log.jsonl` | 日次実行ログ |

`~/.openclaw/.env` から `APIFRAME_API_KEY` と `FAL_KEY` が読まれる。DistroKid cookie は playwright-cli の `distrokid` セッションに保存済み。
