# #5 connector — offline対面 + Luma-main + crypto/AI 化 evidence（2026-07-12）

正本 spec: `docs/superpowers/specs/2026-07-10-connector-loop-design.md` §8/§10。
実行系: openclaw cron `ad89027d anicca-connector-daily`（07:35 JST）→ `connector-cli.sh --restart`
→ tmux `claude` worker が `$STARTUP` を1パス実行。payload はファイルに委譲 = ファイル編集がデプロイ実体（幽霊cron問題なし）。

## Dais 追加要件（2026-07-12 明示）
1. **OFFLINE/対面（東京の実会場）のみ** — 人と会って networking する為。online/オンライン/配信 は登録禁止。
2. **crypto + AI 優先**（web3/blockchain/on-chain が #1 テーマ）。登録前に event 内容を読んで crypto/AI か確認。
3. **Luma メイン + connpass サブ**（両方 offline+crypto/AI gate）。
4. 量より質: 非crypto で gap を padding しない。無ければ正直 `none:no_offline_crypto_ai_candidate`。

## 真因（RCA）
過去11件が全て `location:online` の connpass AI講演だった。真因はプロンプトが `"Tokyo + online"` かつ
テーマ `AI/agent/LLM/founder`（crypto無し）と指示していたこと。horizon ロジック（signals.py）は
online の短い夜イベントでも各日に90分空きが残る為 horizon を塞いでおらず、純粋にプロンプト問題。

## 打った fix（commit, profitable-claude repo）
- `0652d43` STEP1 に HARD RULE #1(offline-only)+#2(crypto+AI優先) を焼込。
- （runbook commit）OpenClaw の luma-register runbook をそのまま STEP1 にコピペ（identity=Daisuke Narita /
  keiodaisuke@gmail.com=Dais本人の Luma アカウント、CTA selector、OTP via gog、`?tk=` 成功トークン、
  参加確定/参加申請完了、register後の create_event）。
- （crypto-native commit）量より質: 登録前に event 説明を読んで crypto/AI 確認、非crypto padding 禁止。

## gcal クリーンアップ（Dais 明示指示、6件削除）
7/13-7/18 の online connpass イベント6件を MCP `delete_event`（notificationLevel=NONE）で削除、
全件 `status:cancelled` 確認。Dais の実予定（Meditation/MUIT出社/Day job/Team Sync/1on1/DS部/松竹芸能/
福澤先生/ALAEW Meeting）は無傷。削除id: gi1k09..., ehdbfa..., veo2mq..., qi7l1i..., 87utva..., c2fq6f...。

## 実登録 evidence（自己申告でなく実 side-effect、3点裏取り）
### ★本命: AI Growth Tokyo 2026 - AI & Web3 Track（Luma, crypto+AI, 対面）
- Luma URL: `https://luma.com/x92v6uvi`（公式タグ AI+Crypto、主催 LamWeb3）
- 日時: **2026-07-15(水) 18:00–21:00 JST**、末に networking session
- **1. ブラウザ**: `luma.com/x92v6uvi?tk=cHuMc0` + モーダル「参加確定！ありがとうございます。お会いできるのを楽しみにしています！」
- **2. 確認メール（keiodaisuke@gmail.com）**: 「AI Growth Tokyo 2026 - AI & Web3 Trackの参加登録が完了しました」
  from `AIGrowthAssociation@calendar.luma-mail.com`、msg id `19f528addd2db64a`、受信 2026-07-12 03:57
  → **Dais 本人アカウントで登録された証拠**
- **3. gcal get_event 読返し** id=`fu7anjp34o3mlu12vjee57a7rk`:
  - `location`: **"Tokyo Innovation Base, 東京都千代田区丸の内３丁目８−３, 〒100-0005"**（online でない実会場）
  - `status`: confirmed、creator/organizer: keiodaisuke@gmail.com
  - start 2026-07-15T18:00:00+09:00 / end 21:00

### AI-Driven Development Meetup（connpass, AI, 対面）
- `https://lycorptech-jp.connpass.com/event/396547/` 受付番号7020141, Daisuke Narita
- 日時: 2026-07-14、location: **"LINEヤフー株式会社 紀尾井町オフィス, 東京都千代田区紀尾井町１−２ 東京ガーデンテラス 17F"**（対面東京）

## Before / After
| | Before | After（この pass） |
|---|---|---|
| ソース | 全 connpass | Luma（本命）+ connpass |
| 場所 | 全 `location:online` | 全 実会場（千代田区）= 対面 |
| テーマ | generic AI | AI + Web3/crypto |
| アカウント | — | keiodaisuke@gmail.com（Dais本人、確認メール受信） |

## 残（7日 streak の done 条件、§10）
- cron `ad89027d` が7日連続 ok run、各日 Telegram delivered:true + FREE 実登録（サイト証跡+gcal 読返し）or 正直 none。
- 本 pass の STEP5 Telegram 8547730585 配信 delivered 確認（pass 完走待ち、last-pass touch で判定）。
- fresh adversary(Opus) PASS。
