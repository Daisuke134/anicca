# Clip-Rewards: Dual-Instance (claude-p + ClawRouter) + Self-Improvement Loop — Design

**Date**: 2026-07-03 · **Branch**: `feature/clip-rewards` · **Owner**: 私 (myclaude, human-funded)
**Inspiration**: やまもとりゅうじ氏の記事(Claude=切り抜きページのオペレーター論、2026-07-03 Dais共有)
**Prior state**: `2026-06-28-clip-rewards-state.md` (D-01〜D-59、5日前から更新停止 = 実質stall)

## 0. 記事から抽出した設計原則(北極星)

1. **再生数のために作るな。再生数の"先にある出口"のために作れ。** → 出口(payout先)が確定しないユニットは着手しない。
2. **Claude=オペレーター、ツールではない。** 1本ずつの手動切り抜きではなく、「発信者選定→出口選定→生成→投稿→採点→改善」を1つの自然文指示で回し続ける系にする。
3. **判断はモデルに委ねる、regexハードコードしない。** どの瞬間を切るか(ジャンル別の型)、どの発信者/出口を選ぶかは、SKILL.mdの自然言語指示 + 実データで判断させる。
4. **週次の採点ループが無いと「ただのギャンブル」。** 掴みの型・発信者・プラットフォーム・再生数・視聴維持・保存・コメント・クリックを記録し、勝ちパターンに寄せる。
5. **初日から詰め込まない。** 新規アカウントは段階的投稿(記事: week2は1日2-3本)。

## 1. 現状の根本問題(2026-07-03 調査で確認、要再修正)

- `producer.sh` が `~/.cache/anicca-clones/AI-Youtube-Shorts-Generator/.venv` 消失で5日間 fail-closed。`~/clips/queue/` が空。
- claude-p (tmux `anicca-clip-core`, Dais の Claude subscription) だけが動いており、ClawRouter (自己資金、`~/anicca/runtime/loop/brain.mjs`) は clip-earn に一切関与していない。
- 出口(promote.fun state machine)はコード完成・テストGREENだが、自走させる Sutando loop harness が未着工 = 休眠。
- 週次採点ループが存在しない。

## 2. To-Be アーキテクチャ

### 2.1 インスタンス分離(絶対に混ぜない)

| | claude-p インスタンス | ClawRouter インスタンス(新規) |
|---|---|---|
| 実行基盤 | tmux + `claude --dangerously-skip-permissions` (Dais subscription) | genesis `~/anicca` loop 経由、ClawRouter (:8402) 課金 |
| wallet | `~/.cloak/myclaude-solana.json` (既存、xxKC33TY...) | 新規keypair(このユニット専用、myclauseと非重複) |
| clip accounts | `~/.cloak/clip-accounts.json` (既存、@aiclipsvault等) | 新規ファイル、別ハンドル群、既存accountと重複禁止 |
| ledger | `~/.openclaw/state/clip-earn-ledger.jsonl` (既存) | 別ファイル(instance別に分離、dashboard集計時にmerge) |
| 判断層(モデル) | Claude Sonnet | ClawRouterがルーティングするモデル(現行 `auto` 方針) |
| 決定論コード(producer/run.sh/poster.sh) | **共通**、`ANICCA_INSTANCE` env で wallet/account-list/ledger pathを切替 | 同上 |

理由: 1 wallet を複数callerが共有すると出金が食い合う(既存メモリ実例)。判断ロジック(SKILL.md自然言語)は共有できるが、実行基盤(wallet/account/ledger)は完全分離必須。

### 2.2 self-improvement loop(記事の週3パターンを実装)

```
毎投稿 → ledgerに記録: {creator, hook_type, platform, views, retention, saves, comments, clicks_to_exit}
週次 wake →
  1. ledgerを集計、hook_type × platform でパフォーマンス比較
  2. 勝ちパターン(views/saves上位)を SELECT の優先順位に反映
  3. 負けパターン(記事: 「教育系が死んでるなら未練を捨てて、やめる」)を自動デプライオリタイズ
  4. producer/run.shが5日以上fail-closedし続けている等の異常は self/issue-dev 経由で自動issue化
```

### 2.2.5 producer.sh 自己修復(2026-07-04 追加、タスク#9)

★ 実インシデント: `~/.cache/anicca-clones/AI-Youtube-Shorts-Generator/.venv` はディスク掃除で
定期的に消える(このセッション中だけで2回発生)。従来は「人間/devセッションが気づいて手で
再構築」していた = HARD RULE #-2「人間をloopに入れるな」違反。★

修正: `producer.sh` 自身が起動時にvenv欠落を検知したら、自分でリポジトリの再clone
(`--depth 1`) + venv再構築 + pip installを行い、そのまま処理を継続する。日次cron
(`ai.anicca.clip-producer`、AM3:17)が完全に無人で回復する。人間/dev/私が二度と気づいて
直す必要が無くなる。

### 2.3 出口(payout)の優先順位

記事原則1「出口のために作れ」に従い、着手順は **出口の確度が高い順**:
1. promote.fun (`~/anicca/skills/earn/clip-promote/`) — コード完成済、Sutando harness作るだけで動く。最短。
2. ClipAffiliates — wallet bind API発見済だがcampaign枯渇中(D-22)、定期リトライのみ。
3. Whop — GraphQL cookie-replay実証済だがjoin mutationがiframeにブロックされ未解決。
4. Vyro — CPM$3(最良)だが未着手、要調査。

## 3. VCSDD実装順序(タスク化、この直後にTaskCreate)

1. producer.sh 復旧(venv再構築 or 依存を軽量化、disk-cleanup耐性を持たせる)
2. `ANICCA_INSTANCE` env切替をproducer/run.sh/poster.shに追加(claude-p既存動作を壊さない後方互換で)
3. ClawRouterインスタンス用の新規wallet+account群+ledger初期化 + genesis loopから呼べるエントリポイント
4. 週次self-improvementループ(集計スクリプト + SELECTへのフィードバック)
5. self/issue-dev への stall検知配線(queue空N日 → 自動issue)
6. promote.fun Sutando loop harness (`clip-promote-cli.sh` + healthcheck + launchd) — 出口を1つ確定させる本命

各項目は vcsdd-init → spec → red → green → adversary → E2E(実際にIG/YT投稿URL確認)で進める。
