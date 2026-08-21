---
lane: A
created: "2026-07-20T20:25:00+09:00"
updated: "2026-07-22T11:21:44+09:00"
status: in_progress
voice: recit
sources:
  - /Users/anicca/anicca-project/docs/reference/orca-mac-mini-mobile-setup.md
  - https://www.onorca.dev/docs/mobile
  - https://github.com/stablyai/orca
  - https://code.claude.com/docs/en/claude-code-on-the-web
title: ノートPCを返却しました。今日からiPhoneだけでAI開発します
subtitle: Orca という Agent IDE で、スマホが自宅マシンのリモコンになる。セットアップと初日の正直な所感
angle: >-
  「MacBook を大学に返却して、iPhone だけで AI agent 開発する」Dais 一人称の実録。AI agent（Claude Code）が自分で Orca を Mac Mini に install し、onboarding を画面クリックで突破し、pairing QR を Telegram/Gmail で人間に配送した構図がフック。Orca 実使用の生の所感（下記）+ 「自宅マシン遠隔 vs cloud sandbox」の本質差（state はどこにあるか）で締める。タイトル方向:「ノートPCを返却しました。今日からiPhoneだけでAI開発します」（rule 51: 未知語で始めない）。
published_urls:
  note_ja: https://note.com/anicca123/n/nfeca7663e750
  note_en: https://note.com/anicca123/n/nb90003c0baef
  x_articles_ja: https://x.com/diceai0/article/2079585582758646185
  x_articles_en: https://x.com/diceai0/article/2079586493526675550
planned_urls:
  zenn_ja: https://zenn.dev/anicca/articles/orca-iphone-ai-development-ja
  zenn_en: https://zenn.dev/anicca/articles/orca-iphone-ai-development-en
---

Dais 指名カード（2026-07-20「I wanna write an article on this」）。価格帯 ¥1,000（explainer 型、稼いだ証明型ではない）。

## Dais の生の所感（2026-07-20、実使用初日 — [5] ブロックの原文としてほぼそのまま使う）

> Orca iOSの所感：自動でワークツリーも切ってくれるし、各セッションのベースブランチがわかりやすくて最高です（ターミナルはこちらがすごくわかりにくかった）。
> ワンタップで、Claude/Codex/Openclawに繋げられますし、GithubのIssuesやLinearとも連携できるみたいです。
> 直近のセッションにもワンタップで戻れるので、非常に作業しやすい。Mac miniにSSH接続してますが、接続も良好です。並列開発が最高に捗りますね。画面下側にCodex・Claudeの残量も出るので最高です。
> これで心置きなく、PCでの開発から卒業できます！

注意: Fable/Sol モデル分業の段落は**この記事に入れない**（別記事ネタ、spine が割れる）。
注意: 「ターミナルはこちらがわかりにくかった」の「こちら」が Cmux か Orca か Dais に未確認。文脈上 Cmux（前に使っていた比較対象）の可能性が高いが、**執筆時に Dais に 1 行確認するか、曖昧なら本文からこの一文を落とす**。

## 検証済み事実（sources の MD が正本。再検索不要）

- Orca = worktree-native Agent IDE。stablyai/orca、MIT、YC-backed（Stably AI / Lovecast Inc.）。1 task = 1 git worktree + 専用 terminal。
- 対応 agent: Claude Code / Codex / OpenCode / OpenClaw / Pi 他。BYO subscription。
- Mobile companion (beta) = 「desktop の remote control」設計。full editor は意図的に非搭載。cloud relay 無し（device token の desktop⇔phone 直接続、desktop app を閉じると切断）。
- Install の罠: 素の `brew install --cask orca` は plotly の deprecated ツール。正解は `brew install --cask stablyai/orca/orca`。Gatekeeper は `xattr -dr com.apple.quarantine` で回避。
- Pairing 実録: Network selector で Tailscale IP を選ぶのが鍵（LAN IP だと外出先から届かない）。QR は数分で期限切れ。
- Claude Code on the web / iOS: Anthropic 管理 VM で実行、repo は GitHub から clone、`~/.claude/CLAUDE.md` は載らない（明記）、secrets store 無し（明記）、network = None/Trusted/Full の 3 段階。

## ★未検証 — 記事化前に loop が必ず検索する事項★

執筆 agent への指示: 以下を `crwl <url> -o markdown` + `gh search repos` / `gh api` で一次情報確認してから [2]（選択肢の地図）と [6]（cloud との比較）を書け。検索せずに断定したら rule 63 違反。

1. **競合の全数調査（[2] の材料）**。各々の 実在/最終更新/stars/提供形態/実行場所(自マシン or cloud)/接続方式 を確認:
   - Happy (slopus/happy, happy.engineering) — Claude Code mobile client。Orca mobile の直接競合
   - omnara (omnara-ai/omnara) — agent 統合 dashboard + mobile
   - VibeTunnel (steipete) — browser 経由 terminal 遠隔
   - 定番 SSH 系: Termius / Blink Shell / mosh + tmux
   - cloud sandbox 系: Claude Code on the web(iOS), OpenAI Codex cloud(ChatGPT app), Google Jules, Cursor cloud agents, Devin mobile
   - cloud dev env 系: GitHub Codespaces(mobile), vscode.dev + Remote Tunnels, code-server, Gitpod/Ona
   - 新顔: `gh search repos "claude code mobile"` / "agent ide mobile" 等で 2026 年の新規参入を探す
2. **「スマホ開発の選択肢は 2 系統(自宅遠隔 vs cloud)しかない」という単純化が正しいか**。前セッションで Dais が「100% wrong では」と指摘済み。上記調査の結果で分類軸を実測から作り直す（例: hybrid 系 = Codespaces は cloud だが自分の永続 env、Remote Tunnels は自マシンだが Microsoft relay 経由、等。分類は調査後に決める）。
3. **cloud sandbox から Tailscale で自宅マシンに入れるか**（[6] の断定の裏取り）。userspace tailscaled (`--tun=userspace-networking`) + DERP over 443 が Anthropic sandbox の egress proxy を通るか。tailscale.com/kb の一次情報 + 実挙動の報告(gh issues 等)で判定。「構造的に不可能」と書くのは検証後のみ。可能なら記事の結論が変わる（cloud 案でも自宅に届く hack が存在することになる）。
4. **Orca の残量表示（Codex/Claude usage）の仕組み** — 何を読んで表示しているか（公式 docs か repo で確認。Dais 所感で言及するので 1 行の裏取りが要る）。
5. **Cmux との比較 1 行分** — Dais が乗り換え元として言及。cmux の repo/現状を 1 検索で確認し、名指しできる程度の事実を取る。

## 構成メモ（lane A、verdict box 無し・アニッチャ CTA 無し）

[1] フック: MacBook 返却、手元は iPhone だけ / [2] 選択肢の地図（★上記 1-2 の調査結果で書く★、表 1 枚）/ [3] Orca とは（mermaid 図 1 枚、≤6 node）/ [4] セットアップ実録（screenshot、brew 罠、Tailscale）/ ここまで無料 ~2,500字 / [5] 所感（上記引用ベース、iPhone screenshot）/ [6] cloud との本質差（★上記 3 の検証結果で書く★、比較表 1 枚）/ [7] おすすめする人・しない人 + 1 週間後追記の予約
