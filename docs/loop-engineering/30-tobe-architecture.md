# 30 — TO-BE Architecture（P9完了後の profitable-claude 全景 + life-manager/clip の AS-IS→TO-BE）

正本index = 00-SSOT.md（§2e GOALS / §5 P1-P9）。本ファイルは Dais 2026-07-12 夕方の音声確定を図で固定したもの。

## 1. life-manager loop

### AS-IS（毎日10:15、動くが5欠陥）
```
launchd 10:15 → life-manager-daily.sh（巨大プロンプト→claude -p）
 ├ IG: MPT未導入→Pillow静止画カード(❌動画でない)、@anicca.affirms2(❌借り物垢)、:9222ロック無し(❌)
 ├ Reddit: @anicca_sao karma=1+shadowban(❌)
 └ Telegram ✅(7/12修理済)
別系統(健在): lm-video = gateway live cron(store-recording 2h毎 + post 09:30/21:00)
 通話録音→transcript→字幕焼きリール→TikTok @anicca.comedy 実投稿(7/12 00:31記録)。公開視認は未検証⚠️
```

### TO-BE（P1+P3）
```
クリエイティブ=lm-videoパイプ流用(録音→リール)をIG向けに接続 / LM専用IG垢新設 /
Reddit復旧+karma育成(90/10) / browser-lock / 投稿毎に実URL→ledger+Telegram /
reality-verifier日次「24h内に公開動画が logged-out で見えるか」→FAILでself-fix
保留: issue→build→PR→merge の開発loop（別Claudeが担当中。マーケの数字が出たら追加 — Dais決定）
```

## 2. clip loop

### AS-IS（製造は健在・出荷口が詰まって7/11 17:00から投稿0）
```
[製造✅] producer 03:17: yt-dlp→whisper+Gemini採点→9:16→字幕→品質ゲート(1080/2.5Mbps、ブラー根絶済)→queue
[出荷❌] run.sh 5分毎: accounts.json両方"investigating"→選択不能。post_reel(:9223/9224)はIG共有確認でハング/202後消滅
[報告❌] mail経路のみ、Telegram実装ゼロ
[監視❌] healthcheck=プロセス生死のみ→投稿0の2日間に無自覚
[収益] ¥0(clip-promote回収も未検証)。最終実投稿=instagram.com/aiclipsvault/reel/DanlbElPLGr/
```

### TO-BE（P2+P3）
```
ハングRCA(CDP Networkで共有確認コール捕捉)→@aiclipsvaultへ毎日実投稿再開 /
成功毎にTelegramへ実URL / reality-verifier「24h内新リール公開?」→FAILでself-fix /
PC repoにfiat-affiliate派生(同じ製造ライン、報酬先=人間の銀行)
```

共通診断: 両loopとも「製造」は生きていて、壊れているのは**出荷口・報告・自己監視**。P3の共有libが両方の恒久fix。

## 3. P9完了後の profitable-claude folder tree（confinement完成形）

```
profitable-claude/          # OSS。「install 1コマンド→あなたのClaude課金が稼ぎ出す」
├── install.sh              # 依存検出→.env対話→scheduler登録
├── .env.example            # 秘密はrepoにゼロ
├── bin/ pc(CLI) + ceo-run.sh(薄い機械gate: 予算hard-stop+registryのみ)
├── harness/                # ★心臓(P3成果物)★
│   ├── reality-verifier/   # report-blind、logged-out browser/APIでside-effect実在確認
│   ├── self-fix/           # FAIL→調査→コード修正→再発防止焼込
│   ├── funnel/             # 投稿→再生→CV→¥ のjsonl(自己改善の燃料)
│   ├── notify/             # Telegram実配信ラッパ
│   └── browser-lock/       # mkdir排他
├── adapters/               # P8: claude-code(launchd/routines) / openclaw(gateway cron) / hermes
├── loops/                  # 全loop=prompt+cli+jsonl state(model-agnostic)
│   ├── life-manager/ article/ gig/ capafy/ clip/ connector/ ios-marketing/(larry+reelclaw+honne vendor)
│   └── _deferred/(affiliate bounty explorer)
├── skills/                 # vendor実体(外部参照0件、C1-C7パターン)
├── state/                  # ledger/funnel jsonl(gitignore)
├── tests/                  # TDD spec→RED→GREEN
└── docs/                   # SSOT/specs/evidence
```

## 4. デプロイ TO-BE（P9）
```
cloud routines ── ブラウザ不要loop(article draft等)
Akash/DO box ─── CloakBrowser必須loop(IG/Reddit/gig/capafy)
Dais = スマホ+Telegram(毎朝、実URL付き日報)+claude.ai/code
```
