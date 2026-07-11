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

## ループ再設計（2026-07-12 04:33、Dais「full 2週間埋めろ・プロンプトでなくループ改善」）
真因: 1つの LLM パスに14日任せると2-3件で早期停止（信頼性なし）。
fix = `connector_fill_gaps.sh`（決定論的 per-day driver）:
1. gcal から空き日を決定論的に列挙（KEYS=connpass/luma/参加登録/申し込み/参加確定/?tk= を含むイベントがある日=埋済）。
2. 各空き日ごとに「その日1件だけ登録する」短命 `claude -p` エージェントを **soonest-first で順に spawn**（1日1件=小タスク=確実）。
3. 全日終了後に `connector_daily_report.sh` で Telegram 日次報告。
- 検証: 空き日計算 OK（FILLED=7/12-15,21,23,25 / OPEN=7/16,17,18,19,20,22,24）。driver 起動後 7/16 agent が :9222 で luma.com/tokyo+discover?categories=crypto+connpass を実際に検索中（実タブ確認）。

## Telegram 配信（Dais「届いてない」→解決）
- 真因: 長い STEP1 で pass が STEP5(Telegram) 前に力尽きる日がある。
- 送信経路は正常: `openclaw message send --channel telegram --target 8547730585` テスト msgId 1941 + 本日ブリーフ 1942/1943 全て ok:true 実配信。
- 恒久 fix: `connector_daily_report.sh`（applications.jsonl を読み honest offline/none）を本パスと独立の launchd で毎日送る。

## launchd（毎日自動）
- `ai.anicca.connector-fill-gaps`（07:50 JST）= 全空き日を埋める driver。LOADED 確認。
- `ai.anicca.connector-daily-report`（09:10 JST）= Telegram 日次報告。LOADED 確認。

## 競合バグ（発見+修正）
- connector が2系統（旧 connector-cli.sh tmux パス + fill_gaps driver）が同時に :9222 を奪い合い→登録が進まなかった。旧 tmux パスを kill して driver に専有させ解消。
- bug 修正: プロンプト肥大で `command too long`→セッション DEAD→file-based prompt（`~/.openclaw/state/connector-startup-prompt.txt` に全文、短い bootstrap で読ませる）。

## commit（全 push 済、profitable-claude repo）
0652d43(offline+crypto) / runbookコピペ / crypto-quality / file-based-prompt / fill-every-day / connector_fill_gaps.sh driver / connector_daily_report.sh。

## (c) 競合 revival 根絶（2026-07-12、DONE・検証済み）
真の revival 経路は cron でなく **healthcheck launchd** だった（当初仮説の cron `ad89027d` は副経路）。
- **真犯人**: `ai.anicca.connector-core-healthcheck` launchd が **5分ごと**に tmux `anicca-connector-core` の生存を確認し、無ければ `connector-cli.sh --restart`（旧2-3件単発パス）を revive（`connector-healthcheck.sh:75-76→58`）。ログで 04:24/04:34 の実 restart を確認。
- **リアルタイム証拠**: driver の 7/16 `rc=124` / 7/17 `rc=124`（各600s timeout・未着地）= 旧パスと :9222 を奪い合い browser を掴めなかった為。
- **打った fix**:
  1. `openclaw cron disable ad89027d-c869-...`（full id 必須、短縮 id は "not found"）→ `enabled:false`。
  2. `launchctl bootout gui/<uid>/ai.anicca.connector-core-healthcheck` + plist を `.disabled` にリネーム（次ログインで再ロードさせない）→ `NOT loaded` 確認。
  3. 旧 tmux パス `tmux kill-session -t anicca-connector-core` → `DEAD` 確認。
  4. revive トリガー file 除去（`.connector-core-restart-log` / `.connector-core-selfheal-request.json` / `.connector-core-last-start`）。
- **結果**: connector のスケジューラは launchd 2本（fill-gaps 07:50 + daily-report 09:10）に collapse。旧持続 tmux パスは退役。driver(PID 44014) が :9222 を専有。他に connector-cli.sh を呼ぶ launchd/cron は無いことを確認。

## (a) 真因＝「1件も埋まらない」landing bug（2026-07-12、自分で診断・修正・検証）
driver の per-day agent が 7/16-18 全て `rc=124`（timeout・ゼロ着地）だった真因は competition ではなく**コードバグ**だった:
- `connector_fill_gaps.sh` が gcal 登録枠を**丸1日**(`${D}T00:00:00`–`23:59`)で渡し、`gcal_write.py:71-86` がその枠に**何か1つでも予定が重なると必ず abort**。
- Dais は毎日ルーティン予定（Meditation/MUIT出社/Day job/Team Sync/DS部/ALAEW）がある → **全日 abort → register_and_calendar が status:failed → applications.jsonl 行なし・gcal event なし → その日は永久に "open" → 何度リトライしても埋まらない**。7/13-15 が残ったのは旧フロー（実時刻）で書けたから。
- **fix（自分で、commit 済）**:
  1. `gcal_write.py`: ルーティン重複では abort しない。**connector イベント同士の重複だけ** conflict 扱い（`_is_connector_event()` で summary/description/location に connpass/luma/参加確定/?tk=/connector_status を含むか判定）。dedup は OPEN_DAYS が担保済み。7/16 実データで conflict=0 を確認。
  2. `connector_fill_gaps.sh`: 丸1日枠→agent が読んだ**実イベント時刻**を渡す。
  3. タブ使い回し（"open a NEW tab" が 108 タブ蓄積→遅延の元。既存 daily-driver タブを navigate、重複19タブ掃除）。
  4. `timeout 600→900`。
- **`claude -p` は print mode で出力を完了までバッファ**→ per-day agent の中間監視は不可。監視は **gcal（ground truth）に event が現れるか**で行う。
- **7/16 実着地・自分の目で検証（gog calendar event 直読、id=8krltisdlhr9f2tsufp62kbf18）**:
  - 会場 **HASEKO - KUMA HALL, 東京都文京区本郷7丁目3−1**（東大本郷・実会場、online=False）
  - 13:30–18:30 JST（実時刻）、status confirmed
  - テーマ = 東大ブロックチェーンイノベーション寄付講座 研究交流会（crypto/blockchain）
  - Luma `luma.com/d0dvi7zl?tk=guRdzS`、参加確定！、確認メール keiodaisuke@gmail.com 受信
- driver は 7/16 landing 後 7/17→7/18→…と継続中。各日 gcal で offline+実会場を読返し確認する。
- **残注意**: 7/21/23/25/26 は online junk が gcal に残り "filled" 扱い→driver が触らない。whole-2-week offline 化には junk 削除→再 driver が必要（Dais は junk 削除を deprioritize だが goal は whole-2-week offline）。

## ★ダブルブッキング bug（Dais最重要指摘 2026-07-12）→ 特定・修正・実証★
最初の landing-fix（gcal_write を「connector同士の重複のみ abort」に緩和）が**緩すぎ**、7/16 に **13:30–18:30** の日中イベントを登録＝**Dais の「Day job 9-17 JST」とダブルブッキング**した。
- **正しい設計**: 元の any-overlap abort は正しく、唯一のバグは**丸1日枠**だった。実時刻に直した今、ガードはこうあるべき: **イベントの実時刻窓に重なる「時刻付き(all-dayでない)・非connector予定」があれば abort**。夜(18:00+)/週末は仕事(9-17)と重ならないので通り、日中の仕事重複は正しく拒否。
- **fix（自分で、commit 済）**:
  1. `gcal_write.py`: `_is_busy_conflict()` = 時刻付き非connector予定が窓に重なれば abort（all-day marker と connector event は除外）。**実gogで検証**: 夜19-21窓→Day job返らず=WRITE OK / 日中13:30-18:30窓→Day job返る=ABORT。
  2. `connector_fill_gaps.sh` prompt: HARD「平日は18:00以降のみ、9-17重複は拒否、土日自由」。
  3. ダブルブッキングした 7/16 イベント + 残骸 travel 2件を MCP delete_event で削除。
- **実証**: 再driver で 7/16 が **WeWork渋谷スクランブルスクエア39F 18:30–20:00**（夜・仕事の後・重複なし）に再登録。agent が「Day job 9-17 の後、重複なし」を自己確認。**loop が自分でダブルブッキングを回避する**ことを実データで確認。
- 現状 offline確定=5日(7/13-17、全て夜・重複ゼロ)。driver は 7/18→7/24 を継続中。online junk 4日(7/21/23/25/26)は未処理。

## 残 TODO（(c)(d) 済、(a) 進行中）
- 再driver が 7/18/19/20/22/24 を夜・offline・非重複で埋める（進行中）→各日 gcal 直読で検証。
- online junk 4日(7/21/23/25/26)を削除→再driver で offline 化＝whole-2-week offline。
- 全着地でダブルブッキング0の最終確認。
- (a) driver が 7 空き日(7/16,17,18,19,20,22,24)を実際に着地させる — 競合解消後の着地を gcal get_event で各日 location=実会場を読返し確認。
- (b) 高速化 = discover-once: luma.com/tokyo + /crypto + connpass を1回スクレイプ→次14日の in-person AI/crypto イベントを全抽出→各空き日にマッピング→登録。per-day 再探索を廃す。
- (d) fresh adversary(Opus) PASS。
- (e) 7日 streak（時間累積、Dais は不要と発言だが §10 done 条件には残る）。
