# AiToEarn 実測評価 — 「直接使う vs pattern 移植」判定（2026-07-16）

対象: https://github.com/yikart/AiToEarn（MIT、23.7k stars、最終 push 2026-07-09、contributors 12）
方法: shallow clone 深読み（file 引用裏取り済み）+ Mac Mini で docker 実起動（全7サービス healthy、
`curl http://localhost:8080/` で `<title>AiToEarn - Content Management ...</title>` 実確認）。
調査 = sonnet subagent 2体（reader/runner）、orchestrator が引用 spot-check 済み。

## 結論（1行）

**丸ごと採用しない。clip loop の現行方式（instagrapi + Reflexion + Digistore）が IG 単騎では優位。
AiToEarn は「将来の multi-platform 展開（YouTube/TikTok/X 等）時の投稿 hub」として self-host 候補 No.1。**

## 我々の要件 × AiToEarn 実装の対照表

| 要件（汎用 marketing engine の柱） | AiToEarn 実装 | 判定 |
|---|---|---|
| account 自動作成 | 無し（該当 keyword ゼロ件） | 我々の `ig-account-create` skill が先行 |
| warmup | 無し | 我々の `ig-account-warmer` skill が先行 |
| 投稿（IG） | 公式 Graph API のみ（`instagram.service.ts` → `graph.instagram.com`、OAuth2 + Meta App Review or Relay cloud key 必須） | **我々の instagrapi+sessionid が優位**（$0・審査なし・reel/DaxPaF9saPA 実証済） |
| 投稿（multi-platform） | **15 platform の publish provider**（youtube/twitter/tiktok/facebook/instagram/threads/pinterest/linkedin/google-business + 中国6種）、全て公式 API | ★ここだけ本物の価値★ |
| headless 投稿 API | あり。`POST /channels/publish/flows/`（media[].url + items[{accountId, platform}]）+ MCP tool `publishChannelTaskNow` | bash loop から HTTP POST で叩ける設計 |
| metrics 収集 | あり（insights snapshot、`instagram-analytics.provider.ts`） | dashboard 表示用のみ |
| **自己改善 loop** | **無し**（`optimi[sz]e\|self.?improv\|ab.?test\|recommend` grep 全滅、偽陽性のみ） | 我々の `clip_pass.sh` Reflexion（LEARN→REFLECT + bible 47/49）が先行 |
| affiliate / Monetize | **コード無し**（README の謳い文句のみ。CPS/CPE/CPM/marketplace で backend ゼロヒット。closed cloud 側） | 我々の Digistore24 + GMX rail が先行 |
| Engage（自動いいね/AI返信） | ブラウザ拡張の実コードが repo に無い（privacy policy ページのみ） | 使えない |

## docker 実起動の実測

- `docker compose up -d` で mongodb(replica)+redis+rustfs(S3互換)+nginx+ai+server+web の7サービスが
  Mac Mini (Apple Silicon, colima) で全て healthy。イメージは Docker Hub 公式、arm64 対応、中国 registry 依存なし。
- ハマり: colima 既定 mount が `$HOME` のみ → `/private/tmp` 配下で bind mount が空になり
  `aitoearn-init` が `npm error EISDIR` で死ぬ。`colima start --mount /private/tmp:w` で解決。
- 投稿の実運用に必要な残り1点 = account OAuth 認可。選択肢:
  (a) aitoearn.ai signup で Relay API Key（彼らの cloud への依存が新規に発生。signup は AI own email で可能）
  (b) 各 platform の自前 developer credentials（IG は Meta App Review = 人間審査 2-4週）
  DOCKER_DEPLOYMENT_EN.md:74-92 "Without Relay: You'd need to register as a developer on each platform ... With Relay: just one API Key"

## 判定と統合方針

1. **今（IG 単騎、clip loop closed 化）**: AiToEarn は使わない。既存 5手（bio-set / LOOP-4 / MEASURE→$ /
   skillify / shared offer）を進める。投稿 = instagrapi、自己改善 = Reflexion + bible、金 = Digistore/GMX。
2. **engine の一般化**: 汎用化の軸は「content producer だけ差し替え可能な chain」= 既に clip_pass.sh の設計
   （LEARN→AFF-FIND→PRODUCE→POST→MEASURE→REFLECT）。producer を slideshow / money-printer / clipping /
   life-manager 宣伝に差し替えても POST/MEASURE/REFLECT/affiliate はそのまま — AiToEarn からの学びは
   「publish 層を platform-adapter として抽象化しておく」こと（POST step を `post_<platform>.sh` に分離）。
3. **YouTube/TikTok 展開時（traction 後）**: self-hosted AiToEarn を投稿 hub として再評価。
   その時は (a) Relay key（最速・cloud 依存）→ 軌道に乗ったら (b) 自前 credentials へ移行が現実的。
   MIT なので publish provider コードだけの抜き出し移植も可。
4. **自己改善の強化**（Dais の問い「勝者リサーチ毎回は不要では」への答え）: AiToEarn に learnable な実装は
   無かった。bible 47 の方針が現状最善: cold-start = 勝者 imitate（hook 40-50%）、traction
   （自平均×3 outlier 出現）後 = 自 metrics 内部最適化へ切替。LEARN step は cold-start 期のみ毎回、
   traction 後は週1 に落とす（REFLECT が切替を判断）。

## 残置物

- clone: scratchpad/AiToEarn（読了、削除可）
- 起動中 stack: scratchpad/AiToEarn-run で `docker compose ps` 7サービス Up。
  見る → http://localhost:8080 ／ 止める → `docker compose -f <scratchpad>/AiToEarn-run/docker-compose.yml down`
- colima が `--mount /private/tmp:w` で再起動済み（システム状態変更、破壊的ではない）
