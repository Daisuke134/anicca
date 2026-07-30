# Outbound Apply Engine — 設計 SSOT (2026-07-30)

status: ACTIVE / 実装未着手 (P0 から番号順)
owner: Life Manager (canonical runtime = `/Users/anicca/Projects/life-manager-main`)
関連 spec: `2026-07-19-anicca-one-repo-consolidation-spec.md` (repo layout / OSS 不変条件),
`.worktrees/job-profile-targets/docs/superpowers/specs/2026-07-28-job-search-loop-design.md` (Job pack)

---

## 1. Goal

Life Manager が **人間をループに入れずに「外に応募し続ける」** 単一エンジンを持つ。
対象は3つ、しかし **エージェントは3つではない。config が3つ**。

| pack | 何に応募するか | 個人固有の config |
|---|---|---|
| `events` | Luma / connpass のイベント参加 + **LT(登壇)枠** | 興味タグ・地域・登壇テーマ |
| `funders` | アクセラレータ / VC プログラム / 投資家 cold outbound | プロダクト・トラクション・応募 Q&A |
| `jobs` | 求人応募 + 面接調整 | 年収下限700万 / 中心1000万 / 勤務地 / 就労権 |

done (このspec全体):
```
done = "3 pack すべてが、実 side-effect の証拠(E1/E2/E3)付きで週次に成果を出し、
        Telegram に届き、週次 reflection が template を実際に書き換えた履歴が残る"
```

---

## 2. 現状実測 (2026-07-30、tool 実行結果に基づく。推測ゼロ)

### 2.1 Events (連結ループ) — 2実装、片方は偽物

| 事実 | 証拠 (file:line / log) |
|---|---|
| Loop A = `profitable-claude/skills/connector/connector_fill_gaps.sh`、launchd `ai.anicca.connector-fill-gaps` 07:50、log `~/.openclaw/logs/connector-fill-gaps.log` | `connector_fill_gaps.sh:21` |
| Loop A は **12日間ゼロ成果**。直近3回すべて `rc=1`。原因はログイン切れ | log `--- done ... rc=1 ---`、attempt stdout に `ログイン・新規登録` / `検索結果 (0件)`。ledger `skills/connector/state/applications.jsonl` 最終行 2026-07-18 |
| Loop A は嘘はついていない (evidence_gate.py / PNG magic-number / post-insert calendar verify あり) が、**死亡が報告されていない** | `event_apply_wrapper.py:147-155`、`register_and_calendar.py:143` |
| Loop A の 404 原因 = カレンダーの summary/description に `/join/complete/` (一発 POST 結果 URL) を入れている | `gcal_write.py:135`, `:140` |
| Loop B = `.openclaw/skills/anicca-meetup-talk-applier/scripts/connpass-lt-discover.py`、cron `connpass-lt-apply-daily` 09:30 | cron id `connpass-lt-apply-daily-1779342348769` |
| **Loop B は偽物**: 成功判定が DOM テキストの regex で、`キャンセル` を含む → 「キャンセルポリシー」に必ず当たり常に True | `connpass-lt-discover.py:166` |
| その未検証 bool のまま無条件でカレンダー作成 | `connpass-lt-discover.py:283`, `:302-307` |
| Loop B は subdomain を捕捉して捨て、404 URL を生成する | `:227` で捕捉 → `:239` で `https://connpass.com/event/<id>/` に再構築 |
| Loop B は一度も出力ファイルを作っていない (`data/connpass` ディレクトリが存在しない) | `:22` の DATA パスが未作成 |
| **QR / チケット取得・Telegram 画像送信は両方に存在しない** (未実装であってバグではない) | `grep -i 'qr|ticket|チケット|sendPhoto'` → 0 hit。`telegram_payload.py:28-30` はテキスト専用 |
| 確認メール検証器は存在するが **本番から誰も呼んでいない** | `registration_confirmation_classify.py` の呼び出し元 = docstring と自テストのみ |

### 2.2 Funders

| 事実 | 証拠 |
|---|---|
| `~/.openclaw/skills/apply-to-funder/` が唯一 cron 登録されている apply skill | `cron/jobs.json` job `accelerator-application-monthly-1777948324077`, `0 12 1 * *` JST, enabled |
| しかし **一度も走っていない** (`"state": {}`) | 同 job |
| 旧 `apply-to-yc/` は DEPRECATED 自己申告済 | `apply-to-yc/SKILL.md` 冒頭 |
| `opportunity-apply-vc` は cron 参照ゼロ = 死亡、`last_run: 2026-06-04` | `skills/opportunity-apply-vc/data/state.json` |
| 実績台帳 = `~/.openclaw/workspace/funders/funder-ledger.jsonl` 53行、最終 2026-06-10。Antler Japan / Techstars Tokyo / 500 Global / Plug and Play Japan / WiL / Samurai Incubate 等が SUBMITTED 済 | 同 file |
| **資産の中核** = `~/.openclaw/identity/application-kit/` (KIT.md, answers/q01..q10 × en/ja, deck, onepager, videos, submitted/INDEX.md)。最新提出 2026-07-22 | 同 dir |
| cold email cron 3本 enabled だが **state は 2026-06-09 で停止** = 静かな死 | `skills/anicca-corey-cold-email/state/sent-*.jsonl` |
| apply 系に **自己改善機構は1つも存在しない**。ledger を読んで prompt を書き換える経路ゼロ | grep 全域 |
| 拒否/返信を第一級 status として持つ state ファイルが無い (自由文の `reason`/`blocker` のみ) | `funder-ledger.jsonl` |

### 2.3 Jobs

worktree `anicca-project/.worktrees/job-profile-targets`。focused test 18/18 PASS、全203テストは中断。
未完: 全テスト再走 / 実環境 healthcheck / commit-push-PR-CI-merge / canonical runtime 反映 / 実 daily run での `700万未満 reject・1000万 target` 検証。
後続: 11D Guardian, 11E Lifecycle, 11F summary.v2, 実 Ashby/Workday 応募各1件, 面接メール→Calendar E2E。

### 2.4 既存の再利用可能資産

| 資産 | パス | 用途 |
|---|---|---|
| 雛形ループ (cloud まで通っている唯一の型) | `apps/life-manager/scripts/financial-report-boot.sh` → `lib/financial-report-runtime.js` → `lib/telegram.js` → `migrations/*.sql` → `*.test.js` → `scripts/install-financial-report-launchd.sh` | P0 はこれを丸ごと複製 |
| Telegram 送信 (cloud portable、chat_id は DB 由来) | `apps/life-manager/lib/telegram.js:19-20`、tenant 解決 `financial-report-runtime.js:49-50` (`lm_users.telegram_chat_id`) | 全 pack の報告 |
| Guardian / 死活監視 | `skills/self/healthcheck-runtime-loop.sh:50-54` (DEAD/STALE/OK)、`skills/self/self-fix.sh` | 「12日間死んでいた」の再発防止 |
| 自己改善の手本 | `~/.openclaw/skills/ai-entity-article-writer/scripts/self-improve.sh:352-416` (measure→learn→apply→keep/revert、`state/playbook.json`、7日未満は学習しない `:380`) | P4 の設計元 |
| eval harness | `apps/life-manager/eval/*.js` + `*.jsonl`、`npm run eval` | pack の qualify 判定を eval 化 |
| 証拠ゲート | `skills/connector/.../evidence_gate.py` (PNG magic-number + ≥5000 byte) | E2 に流用 |

---

## 3. アーキテクチャ

### 3.1 単一パイプライン (全 pack 共通、6段)

```
DISCOVER → QUALIFY → ACT → EVIDENCE GATE → TRACK → LEARN
```

| 段 | 責務 | 判断主体 |
|---|---|---|
| DISCOVER | source から候補を取る (Luma / connpass API / funder registry / job boards) | 決定的コード (provider adapter) |
| QUALIFY | 応募すべきか。denylist / 条件 / 重複 | **LLM 判断** (regex hardcode 禁止)、denylist のみ決定的 |
| ACT | 実際にフォーム送信 / RSVP / メール送信 | browser (CloakBrowser daily-driver) or API |
| EVIDENCE GATE | §4。証拠が揃わなければ **failed** | 決定的コード。**自己改善が書き換え不可** |
| TRACK | 返信・合否・面接日程を拾う (Gmail 実読) | LLM 分類 + 決定的 state 書き込み |
| LEARN | 週次 reflection、template 更新 | LLM (§6) |

### 3.2 配置 (consolidation spec §6.1 準拠)

★ 2026-07-31 実測で訂正 ★ — `packages/*` と `adapters/{providers,state}` は **実在しない**
(`adapters/` は README だけの空スタブ)。実在するのは `runtime/loop/` のみ。
新規ディレクトリを増やさず、既に動いている場所に置く。

| 層 | パス | 実在 |
|---|---|---|
| エンジン | `runtime/loop/outbound/` | 親 `runtime/loop/` は実在 (31 entries) |
| 冪等 / receipt | `runtime/loop/outbound/receipt.mjs` (将来 `packages/job-protocol` に切り出す) | 新規 |
| provider I/O | `apps/life-manager/lib/providers/{luma,connpass,gmail,cloakbrowser}.js` | 新規、既存 lib/ の下 |
| config pack | `skills/life-manager/outbound/{events,funders,jobs}/` | 新規、`skills/` は実在 |
| 製品 entrypoint + test + eval | `apps/life-manager/{scripts,lib,test,eval}/` | 実在 |
| durable state | Supabase (既存 `lm_users` に `telegram_chat_id` あり)。ローカル scratch は `~/.openclaw/state/outbound/` | 実在 |
| spec | 本ファイル。証跡は `docs/evidence/outbound/` | 実在 |

雛形の実体 (実測): `apps/life-manager/scripts/financial-report-boot.sh` (7行) は
`node ../lib/report-job-adapter.js enqueue` を呼ぶ薄い wrapper。
本体は `lib/financial-report-runtime.js` (495行)。`lib/telegram.js` (158行) に
**`sendPhoto` は既に実装済** (`telegram.js:29`、FormData + Blob image/png)。

**repo に state を置かない** (OSS-3)。local と cloud は **同一 commit / 同一エンジン** (OSS-2)。

---

## 4. Evidence Contract (嘘を物理的に不可能にする層)

成功は **E1 ∧ E2 ∧ E3** が揃った時のみ。1つでも欠ければ `status=failed` + 理由を Telegram。

| # | 必須証拠 | 実装 |
|---|---|---|
| E1 | 外部システムの応答: HTTP 2xx receipt / **Gmail で実読した確認メール** / ticket ID | `registration_confirmation_classify.py` を本番配線 (現在は死にコード) |
| E2 | artifact: 確認画面 PNG (magic-number + ≥5000 byte) | 既存 `evidence_gate.py` 流用 |
| E3 | canonical URL が HEAD で 200。`/join/complete/` 系の一発 URL 禁止、subdomain 保持 | `gcal_write.py:135` と `connpass-lt-discover.py:239` の修正 |

禁止事項 (違反 = 即 revert):
- DOM テキストの文字列/regex マッチで成功を宣言する行を **1つも残さない** (`connpass-lt-discover.py:166` は削除)
- 自分が生成したテキストを自分で読んで成功と判定しない
- 証拠なしでカレンダー / ledger / Telegram に「完了」を書かない

**自己改善の書き込み権限**: template / targeting / cadence の config のみ。
`runtime/loop/outbound/evidence/**` は self-improve から **read-only**。
(報酬を「verified evidence 件数」にしても、ゲートを緩める方向の学習だけは構造的に禁止する)

---

## 5. QR / チケット配送 (Dais 要求の中核)

★ 2026-07-31 実測で訂正 ★ — **確認メールに QR 画像は入っていない**。
実サンプル (thread `19fa9e1cc6f49e56`, Luma "Registration confirmed", 2026-07-29) を dump した結果、
part 構成は `multipart/mixed[ multipart/alternative[text/plain, text/html], text/calendar invite.ics ]`。
`<img>` は avatar/appstore/SNS アイコンのみ、`grep -i qr` = 0 hit。
**しかし guest key は本文に入っている**: `https://luma.com/8tdfs50y?pk=g-lAbPrfciSZzRRgy` と
`https://luma.com/join/g-lAbPrfciSZzRRgy`。同じ key は `invite.ics` の DESCRIPTION/LOCATION にも入る。

| 経路 | 実際の取得方法 | 根拠 |
|---|---|---|
| Luma (主) | RSVP → 確認メール → `gog gmail` で実読 → 正規表現 `https://luma\.com/([a-z0-9]+)\?pk=(g-[A-Za-z0-9]+)` で slug + guest key 抽出 → **`qrcode` で自前 QR 生成** → Telegram `sendPhoto`。日時/場所は `invite.ics` の DTSTART/LOCATION から | 実メール dump (2026-07-31) |
| connpass (延期) | 受付票は `connpass.com/event/<id>/ticket/` で **要ログイン**、メールに key が一切出ない → セッション付きブラウザでスクショ以外に道なし | 実メール dump: 「受付票URL: ... (ログインした参加者のみ閲覧可)」 |

**Luma のアカウントは `contact@aniccaai.com` = Anicca 所有** (確認メールの To ヘッダ)。
daily-driver profile に `luma.com` cookie 10件 (`luma.evt-*.registered-with` ×5 = 登録実績) を確認。

未検証: `pk=g-` が Luma 公式スキャナの check-in ペイロードとして通るか。
チケットページ SSR に QR 文字列が無いため、**実イベント会場で1回試すまで確定しない**。
→ #8 の done は「Dais の手元に QR が届く」までとし、スキャン通過は次の実イベントで検証する。

**Dais 側の必要物 = Telegram のみ**。Luma アプリ / connpass アプリ / 認証情報の提供は不要。
カレンダーには canonical event URL (200 検証済) を入れる。

---

## 6. 自己改善層 (eval engineering)

報酬がスパースかつ遅延する (返信・合否が数週間後)。採用する機構:

| 出典 | 採用する仕組み |
|---|---|
| Anthropic「Writing effective tools for agents」 | 「Each evaluation prompt should be paired with a **verifiable response or outcome**」/「Simply **concatenate the transcripts** ... and paste them into Claude Code」/「We relied on **held-out test sets** to ensure we did not overfit」 |
| DSPy **GEPA** | 「uses LLMs to **reflect on structured execution traces** (inputs, outputs, failures, feedback) ... proposing a new instruction tailored to real observed failures」/「can leverage **any textual feedback**—not just scalar rewards」/「maintains a **Pareto frontier**」 |

実装:

```
trace 1行 = {ts, pack, segment, target, template_variant, sent_at,
             evidence{e1,e2,e3}, outcome, outcome_at, reply_text}

日次   : trace 追記のみ (jsonl → Supabase)
週次   : 勝ち trace + 負け trace + 返信本文の原文 を LLM に渡す
         → 出力 = 「次の1仮説 + template 差分」 (playbook.json と同型)
segment: YC系 / 日本VC / Luma LT / 海外remote求人 ... ごとに Pareto 保持
ガード : 7日分未満のデータでは学習しない / hold-out 20% は旧 template 維持
報酬   : verified evidence 件数 (返信率ではない)
```

Cold outbound の型 (実測 BP):
- TechCrunch (Kamps): 3段落・デッキ添付しない・「Good cold emailing is all about **targeting very carefully, not sending out hundreds**」
- OpenVC: 件名60字未満 / 本文1000字未満 /「the longer the email, the less reply you get」/ フォローアップは3〜7日空けて最大2回 / デッキ開封済で無返信なら「take the L and move on」

→ **量産しない。1日3〜5通の精密射撃 + 自動フォローアップ最大2回**。

---

## 7. 制約 (実測、隠さない)

| 事実 | 引用 | 設計への影響 |
|---|---|---|
| YC は締切後も受け付ける | ycombinator.com/apply 「we are still accepting late applications」/ FAQ 「We fund many companies that apply late every batch」 | **Fall 2026 に今すぐ出す**。P2 の1発目 |
| YC は1分の創業者動画必須 | YC library 6t 「it should be a minute long, all the founders should be in the video, and people don't do that」 | application-kit の videos/ を使う |
| connpass は API 以外の自動アクセスを禁止 | connpass.com/about/api/ 「提供されているAPI以外の手段（自動化の有無にかかわらず）で ... アクセスを行う、または試みる行為は、利用規約により禁止」 | 発見 = 公式 API (要 key, 1 req/sec)。RSVP = **人間速度**のブラウザ、Anicca 自身のアカウント。バースト禁止。**Luma を主・connpass を従** |
| Luma API は主催者側のみ | docs.luma.com 「programmatically manage **your** events and guests」/「you need a **Luma Plus** subscription」 | 参加側 RSVP は daily-driver ブラウザ一択 |
| LT枠は構造化フィールドが存在しない | connpass API に発表枠フラグ無し / Sessionize は read-only JSON API / PaperCall は公開 API 無し | LT 判定は本文を **LLM に読ませる** (regex 禁止) |
| MUFG 系は応募禁止 (Dais の勤務先) | mucap.co.jp のヘッダに MUFG ロゴ、フッタに三菱UFJ銀行 | denylist: `三菱UFJ` `MUFG` `MUCAP` `MUIP` `Mitsubishi UFJ`。加えて **プログラムのコーポレートパートナー名簿を提出前に毎回チェック** (1stRound 等は名簿未検証のため機械ゲート化) |
| 英語圏優先 | Dais 指示 | qualify の重み付けで en > ja、ただし ja も除外しない |

---

## 8. TODO 表 (順序の正本。番号順に着手、飛ばさない)

| # | P | タスク | done 条件 (これ以外を done と呼ばない) |
|---:|---|---|---|
| 1 | P0 | `runtime/loop/outbound/` エンジン骨格を financial-report から複製 (boot.sh / runtime.js / migrations / test / launchd installer) | `npm test` 緑 + launchd 登録 + heartbeat `~/.local/state/life-manager/.outbound-last-pass` 更新 (★訂正: `~/.openclaw/state/` は禁止根。§8.1 参照★) |
| 2 | P0 | Evidence Contract E1/E2/E3 を独立モジュール化 (self-improve から read-only) | 単体テストで「証拠欠落 → failed」が3ケース PASS |
| 3 | P0 | ~~Telegram `sendPhoto` を追加~~ **CLOSED 2026-07-31: 既に実装済 (`lib/telegram.js:29`)** | — |
| 3b | P0 | `npm install` で baseline を緑にする (`tldts` 欠落で `npm test` が即死。pretest は 68/68 PASS) | `npm test` が最後まで走り、pass/fail 数が出る |
| 4 | P0 | Guardian 配線 (`healthcheck-runtime-loop.sh` 登録 + STALE で self-fix) | **配線 = 完了 (§8.1)**。★残 = live 検証: loop を launchd に入れ、意図的に止めて実 self-fix が起動すること★ (「Telegram 警告」は誤り。escalation 先は `self-fix.sh` = 分離 fixer agent であって Telegram ではない) |
| 5 | P1 | Loop B の偽物判定を削除 (`connpass-lt-discover.py:166` の regex を廃棄、`:302` の無条件カレンダー書き込みを撤去) | grep で成功宣言の文字列マッチが 0 hit |
| 6 | P1 | URL バグ2箇所修正 (`gcal_write.py:135/140` を canonical event URL に、`connpass-lt-discover.py:239` の subdomain 保持) | 生成された URL 10件が全部 HEAD 200 |
| 7 | P1 | Luma provider adapter (discover + RSVP via daily-driver) | 実イベント1件を RSVP、確認メールを Gmail で実読 |
| 8 | P1 | QR パイプライン。★訂正: メールに QR 画像は無い★ → 本文から `pk=g-` guest key を抽出 → **自前で QR 生成** → sendPhoto | **Dais の Telegram に実イベントの QR 画像が届く** |
| 9 | P2 | ★v1 から除外 (2026-07-31 決定)★ connpass はセッションが **Dais 個人アカウント `DaisNar`** で BAN リスクが本人に飛ぶ + API key 未取得 + ToS。残タスクは「connpass API key を申請する」のみ | API key 取得 (取れるまで connpass を触らない) |
| 10 | P1 | LT/CFP 優先ロジック (LLM が本文から登壇枠を判定、観客枠より優先) | LT 枠のあるイベント5件を正しく分類 (eval jsonl) |
| 11 | P1 | Loop A のログイン復旧 + events pack への統合、旧2実装の退役 | 12日ゼロだった状態が解消、1週間で ≥1 件の verified 登録 |
| 12 | P2 | funders pack: `application-kit` を SSOT に配線 + funder registry 再構築 | registry から1件を選んで下書きが生成される |
| 13 | P2 | MUFG denylist + パートナー名簿チェックゲート | denylist 対象に対して応募が機械的にブロックされるテスト PASS |
| 14 | P2 | **YC Fall 2026 に late application を実提出**。既存下書き (App UUID `0b61fe42-e383-490d-b60e-04f1ad7ec5df`、18項目記入済、未提出) の3ブロッカーを潰す: ①Description を50字未満 ②Founder video アップロード (≤60秒 / <100MB) ③founder profile を completed に | 確認画面 PNG + **YC からの提出確認メール** + ledger 1行 + Telegram 報告 |
| 14b | P2 | founder video の確定。`Anicca_intro_EN.mp4` (58秒 / 21MB) は YC 両制約をクリア。`2026-07-30-founder-video-IMG_5024.mov` (79秒 / 144MB) は両方アウト | アップロード可能なファイルが1つ確定 |
| 15 | P2 | cold outbound 蘇生 (1日3〜5通、件名60字/本文1000字、follow-up 最大2回) | 実送信 + 送信 receipt + 3日後 follow-up が自動発火 |
| 16 | P2 | 返信・拒否を第一級 status として TRACK (Gmail 実読 → outcome 更新) | rejection / reply / meeting が state に型付きで入る |
| 17 | P3 | Job loop: **206テスト** (203 は古い数、pytest で実測) 再走 → 実環境 healthcheck → PR → merge → canonical 反映。★worktree は commit ゼロ・全変更が未コミット・canonical/main から 5 behind★ → commit → rebase が先 | main に merge 済 + canonical runtime が新方針で1回実走 |
| 18 | P3 | Job loop: `700万未満 reject / 1000万 target` を実 daily run で検証 | 実ログで reject/accept の判定が仕様通り |
| 19 | P3 | Job loop 11D Guardian / 11E Lifecycle / 11F summary.v2 | 各機能のテスト + 実走証拠 |
| 20 | P3 | 実 Ashby / Workday 応募 各1件 + 面接メール→Calendar E2E | 応募 receipt + カレンダー実登録 |
| 21 | P4 | trace ledger + 週次 reflection + Pareto (segment別) + hold-out 20% | 2週分の trace で template が実際に1回書き換わり keep/revert が記録される |
| 22 | P5 | cloud 化: state を Supabase、chat_id を per-tenant、local/cloud 同一 commit SHA | Railway 上で同エンジンが別ユーザー分を回し、receipt に同一 SHA |

**進め方**: 1つずつ閉じる。P1 の #8 (QR が Telegram に届く) が真になるまで P2 に入らない。

### 8.1 Guardian 配線 (TODO #4 の実装記録、2026-07-31)

**閉じた失敗クラス**: 前身の connector loop は 2026-07-18 を最後に 12 日間死んでいた (全 run `rc=1`) が、**誰も見ていなかったので誰も気づかなかった**。原因は「cron がある」だけで **artifact を見張る entry が無かった**こと。以下でその穴を塞ぐ。

| 項目 | 値 (実測・ハードコード) |
|---|---|
| guardian | `skills/self/healthcheck-runtime-loop.sh` (既存。`hrl_classify` を再利用、並行機構は作らない) |
| entry 1 | `outbound-pass` → label `ai.anicca.life-manager-outbound`、kind `interval`、stale **1410 min** |
| entry 2 | `outbound-verify` → label `ai.anicca.life-manager-outbound-verify`、kind `interval`、stale **1470 min** |
| ★heartbeat path★ | **`$HOME/.local/state/life-manager/.outbound-last-pass`** (両 entry 共通) |
| writer | `runtime/loop/outbound/streak.mjs::heartbeatPath()` — `lib/outbound-runtime.js`(pass) と `scripts/outbound-verify.js`(verify) の**両方**が `touchHeartbeat` する |
| なぜ `.openclaw` ではないか | `apps/life-manager/scripts/scan-legacy-paths.js` が `apps/` `runtime/` 内の `.openclaw` 参照 (コメント含む) で build を落とす + `lib/runtime-paths.js` が同根を reject する。canonical portable root は `resolveDataRoot()` |
| escalation | `STALE` / `DEAD_UNLOADED` → `skills/self/self-fix.sh <name> "<blocker>"` (= 分離 fixer agent。★Telegram 通知ではない★) |
| guardian 自身の cadence | `ai.anicca.runtime-loop-healthcheck` = `StartInterval 300` (5分毎) → 30分の検出マージンは約6評価分 |

**stale limit の導出** (感覚ではなく schedule から計算):

```
pass 07:30 / verify 09:00 が同じ heartbeat を触る
  両方生存      → 合法な最大 age = 09:00 → 翌 07:30 = 1350 min
  片方だけ死亡  → 生存側が1日1回触る       → age は 1440 min に達する
  両方死亡      → age は無限に伸びる
∴ 1350 < limit < 1440 だけが「健全」と「半死」を区別できる窓
   pass   = 1410 (23h30) … drift slack 60min、1440 の手前で鳴る
   verify = 1470 (24h30) … 「丸1日誰も触っていない」= 全滅アラーム。
                            pass より 60min ずらすことで、1回の障害で
                            self-fix が同時に2発起動するのを防ぐ
```

**正直な限界**: artifact を2 entry で共有しているため、**freshness だけでは「どちらの loop が死んだか」は判別できない**。判別するのは per-label の `DEAD_UNLOADED` 検査 (label 完全一致) の方。

**副次的に直したバグ**: `loop_pid` は `grep "$label"` の**部分一致**だった。`ai.anicca.life-manager-outbound` は `...-outbound-verify` の**厳密な接頭辞**なので、pass が unload されていても verify の行が PID を返し「生きている」と誤判定しうる = まさに本タスクが潰す失敗クラス。`hrl_pick_pid` (`launchctl list` の第3列を完全一致) に置換し、テストで固定した。

**テスト**: `apps/life-manager/scripts/outbound-guardian-wiring.test.js` (13 tests、`npm run test:outbound` に登録済)。scratch `HOME` + 実ファイルの mtime を操作して**実 bash script を subprocess で駆動**する (guardian を JS に書き直さない)。`NEGATIVE CONTROL` で「常に OK を返す classifier」を同じ表に通し、4件以上落ちることを assert = 表が空虚でないことの証明。escalation は stub `self-fix.sh` を隣に置いた sandbox copy で検証 (実 fixer を起動しない)。

### ★★ 8.2 `~/anicca` への再同期 (merge 時に必須) ★★

live guardian は **この repo ではなく `~/anicca` の copy** を実行している:

| 事実 | 実測値 (2026-07-31) |
|---|---|
| 実行される実体 | `~/Library/LaunchAgents/ai.anicca.runtime-loop-healthcheck.plist` → `/Users/anicca/anicca/skills/self/healthcheck-runtime-loop.sh` |
| 本 branch 側 | `skills/self/healthcheck-runtime-loop.sh` |
| 差分 (本タスク着手前) | ★byte-identical ではない★ — **1行だけ差異**: `LOG=` が repo 側 `$HOME/.local/state/life-manager/logs/...` に対し `~/anicca` 側は旧 `$HOME/.openclaw/logs/...` |
| plist の load 状態 | ★`launchctl list` に `ai.anicca.runtime-loop-healthcheck` が**居ない** = guardian 自体が現在 unload されている★ |

**したがって、この branch を merge しただけでは live guardian は新 entry を一切見ない。** merge 時に必ず:

1. `skills/self/healthcheck-runtime-loop.sh` を `~/anicca/skills/self/` へ再同期する (LOG 行の扱いを決めた上で。`~/anicca` は LIVE runtime store なので本 branch の executor は触っていない)
2. `~/anicca` 側で `bash skills/self/test-healthcheck-runtime-loop.sh` と outbound の classify を実走させる
3. `ai.anicca.runtime-loop-healthcheck` を load し直す (これをやらない限り guardian はゼロ回実行される)

同期を怠ると **「entry を書いたのに live では見張られていない」= 本タスクが塞いだはずの穴がそのまま残る**。

---

## 9. 一般化 (製品としての意味)

| pack | 製品になった時の一文 |
|---|---|
| events | 「知らないイベントに勝手に登録され、QR だけが届く」 |
| funders | 「YC を知らない人の代わりに YC に出す」 |
| jobs | 「50代でも学生でも、応募と面接調整が終わっている」 |

エンジンが1つなので、CFO / 投資エージェントも同じ6段に載る
(DISCOVER=銘柄, ACT=発注, EVIDENCE=約定 receipt)。作り直しは発生しない。

---

## 10. 未検証 (見える穴として残す)

| 項目 | 状態 (2026-07-31 更新) |
|---|---|
| `pk=g-` が Luma 公式スキャナの check-in ペイロードとして通るか | **未検証**。ticket ページ SSR に QR 文字列が無い。実イベント会場で1回試すまで確定しない |
| ANRI の応募フォーム項目 | **未検証**。GSAP プリローダーで headless が全滅 (crwl / r.jina.ai とも 0%)。過去に submit 実績あり (`/en/thanks`) → daily-driver で開けば取れる |
| Plug and Play Japan | 解決: HubSpot form。**ただし三菱UFJ銀行がアンカーLP** (bk.mufg.jp 公式PDF) かつ既に応募済 (#88) |
| a16z speedrun | 解決: **rolling で今も受付中**。SR008 = 2027年1-4月 SF、審査4-6週、採択率<0.4%、ソロ創業者可 |
| YC の AI 生成応募に関する公式見解 | **存在を確認できなかった**。「YC が AI 応募を禁止」は未検証として扱う |
| Incubate Fund / Genesia 4号の LP に MUFG がいるか | 非公開で判定不能。**§7.1 の線引きにより無関係になった** |
| `apps/life-manager` の真のテスト数 | `npm install` (#3b) 後に判明。現状は `tldts` 欠落で即死 |
| VC 連絡先のオープンデータセット | 見つからず (OpenVC 等はゲート付き商用)。プログラム的一括取得は未検証 |
| Guardian: 「STALE → 実 self-fix agent が起動する」 | **未検証**。outbound の2 plist は launchd に未 install (provider が `NOT_IMPLEMENTED` を投げる段階) なので、実 heartbeat が STALE になる状況を作れない。検証済なのは ①classify が実ファイル mtime から STALE/OK/MISSING/DEAD を正しく返すこと ②DEAD 時に escalation が **stub** self-fix に到達すること。**実 fixer agent の起動は一度も観測していない** |
| Guardian: 「Telegram 警告が届く」 | **そもそも配線が存在しない**。`self-fix.sh` に Telegram 送信は無い (grep 0 hit)。TODO #4 の旧 done 条件は誤り。§8.1 で訂正済 |
| Guardian が live で回っているか | **回っていない**。`ai.anicca.runtime-loop-healthcheck` は plist が `~/Library/LaunchAgents/` に在るのに `launchctl list` に居ない (unload 状態)。§8.2 の再同期 + load をやるまで entry 追加は live には効かない |

## 11. 決定ログ (2026-07-31 の不確実性掃討)

| # | 決定 | 理由 |
|---|---|---|
| D1 | **v1 は Luma のみ。connpass は延期** | ①ToS が API 以外の自動アクセスを禁止 ②API key 未取得 ③セッションが **Dais 個人アカウント `DaisNar`** = BAN リスクが本人に飛ぶ。Luma は `contact@aniccaai.com` で Anicca 所有 |
| D2 | **QR はメールから抜くのではなく自前生成** | 実メール dump で QR 画像が存在しないことを確認。guest key は本文にある |
| D3 | **MUFG 除外は「運営/CVC」のみ。LP に過ぎない先は応募可** | 除外対象 = MUCAP / MUIP / MUFG 冠プログラム。LP は応募者情報への可視性が無い。この線で 1stRound (partner list grep 0 hit) と HAX Tokyo (SOSV/住友商事/SCSK) はクリーン |
| D4 | **YC は Fall 2026 に late で今すぐ出す** | 18項目記入済 + 面接8-9月 + 「we are still accepting late applications」。待つ理由がゼロ |
| D5 | **エンジンは feature branch → PR で main へ** | `Daisuke134/life-manager` は branch protection ゼロ・test CI ゼロ (`sec-scan.yml` のみ)。直 push は危険 |
| D6 | **新ディレクトリを増やさない** | `packages/*` と `adapters/{providers,state}` は実在しない。実在する `runtime/loop/` と `apps/life-manager/lib/` の下に置く |
