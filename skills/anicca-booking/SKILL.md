---
name: anicca-booking
description: |
  Proactive 自律 apply skill。空いてる gcal slot を 検出 → profile.goals.ideal_state[] から domain 優先順位 (AI_LT > comedy > research > job_BigTech > VC_apply) → 各 domain の sources を 検索 → 該当 event を 実 apply (camofox + 自然言語推論) → CONFIRMED gcal 挿入。LT / お笑い / 寄席 / 求人 / VC / 全 ideal_state に 適用。Power of Free 永久 BAN list 厳守。
metadata:
  tags: [booking, apply, connpass, peatix, lu.ma, yc, hard-rule-19, openclaw, camofox]
  type: booking-agent
  requires:
    bins: [python3, gog, curl, jq, camofox]
    env: [CONNPASS_USERNAME, CONNPASS_PASSWORD, PEATIX_EMAIL, PEATIX_PASSWORD, LUMA_GOOGLE_ACCOUNT, GOOGLE_API_KEY, GOG_ACCOUNT, GOG_KEYRING_PASSWORD]
  spec: $LIFE_MANAGER_REPO/specs/archive/ANICCA_LIFE_MANAGER_SPEC.md §21.5
---

# anicca-booking

User の `profile.goals.ideal_state[]` を 読み、空いてる gcal slot に 合致する event を 各 domain の `sources` から 検索 → **実 apply** → CONFIRMED gcal に 挿入。

Source of truth: `$LIFE_MANAGER_REPO/specs/archive/ANICCA_LIFE_MANAGER_SPEC.md` §21.5

## あなた (Anicca) への指示 — まずこれを読む

あなたは LLM エージェントです。設計原則は **Anthropic 公式 Skills BP § "Degrees of Freedom"** に従う:

| layer | freedom | これに該当 |
|---|---|---|
| **探索 (discover events)** | **HIGH** = 自然言語で自由 | 14 日先まで gcal を読み、空き枠を把握、connpass/lu.ma/peatix/Tokyo Comedy/Stand-Up Tokyo を**好きに巡回**して candidates を作る |
| **フィルタ (3-gate)** | **LOW** = 固定 deterministic code | propose.py の `gate1_anti_goals` / `gate2_blocklist` / **`gate3_physical_conflict`** が必ず通る (絶対) |
| **重複gate enforcement** | **LOW = 絶対** | apply.py → gcal-policy.sh `--check-conflict` で insert 直前に再検証。exit 19 なら abort して次へ |
| **camofox apply (per-site)** | **HIGH** = 自然言語で snapshot 読み判断 | 各サイト構造違うので、snapshot 取って見えてる UI で click/type/submit を決める |

> **★ Iron Law (the user 2026-06-04 23:55 厳命 verbatim) ★**:
> *"I cannot go to two places at once. If I cannot go to the first one and I missed that … people are gonna be mad at me … my trust is gonna be broken into pieces. There's no even meaning in having a life manager."*
>
> = **既存 gcal event と時刻 overlap (前後 30 min travel buffer 込み) する candidate は絶対に CONFIRMED にしない。**
> propose.py の gate3 で reject されるか、gcal-policy.sh `--check-conflict` で exit 19 になるか、いずれにせよ二重に保護されている。**あなたが「judgment で例外的に入れていいか」と思ったらそれは違う。the user の trust を守るのが life manager の存在意義。**

### 進め方

#### Phase 1 — HIGH freedom 探索 (自然言語、あなたが判断)

1. `python3 scripts/scan_gcal_horizon.py` を実行して、向こう 14 日の空き slot を把握する (deterministic、ここは固定)。
2. 空き slot の dates/times を頭に入れた上で、**好きな手段で東京の AI/LT/コメディ/もくもく会の event を探す**:
   - firecrawl で検索 (query は自由に組め: 「東京 AI LT イベント 6月7日」「Stand-Up Tokyo open mic」など)
   - 知ってる URL なら直接 camofox で開いて event 一覧ページから拾う
   - lu.ma/tokyo / tokyo.aitinkerers.org / connpass.com/event/?prefectures=tokyo / peatix.com/search 等
3. **profile.json の `goals.ideal_state`** を必ず読む (AI_LT / comedy / research / job_BigTech / VC_apply の優先順)。
4. **profile.json の `goals.anti_goals`** + **`location.defaultPrimaryLocation`** も読む。空き時間の default 居場所 = **Tokyo Innovation Base (TIB) 千代田区丸の内3-8-3 (有楽町/銀座)** = ここから移動できる範囲を優先。

#### Phase 2 — LOW freedom フィルタ (deterministic code、あなたは触らない)

5. 集めた candidates を JSON で標準入力経由 `propose.py` に流すか、scaffold モードで `bash scripts/run.sh` を実行する。これが `scan_gcal_horizon.py` → `propose.py` (3-gate) → `apply.py` (PROPOSED gcal + `--check-conflict`) を順に呼ぶ。
6. **3-gate の結果は絶対** (`gate1_anti_goals` / `gate2_blocklist` / `gate3_physical_conflict`)。`blocked: physical_conflict with: <event>` が出たら、その候補は捨てる。「the user の既存 schedule と battle 禁止」の deterministic 保証。

#### Phase 3 — HIGH freedom 申込 (各サイト構造違うので自然言語で判断)

7. `state/booking-history.jsonl` の末尾を読み、`event: candidate_approved` の **URL リストを上位 3-5 件** 拾う (同じ URL は 1 回だけ)。
2. `state/booking-history.jsonl` の末尾を読み、`event: candidate_approved` の **URL リストを上位 3-5 件** 拾う（同じ URL は 1 回だけ）。
3. それぞれの URL について **camofox を使って自分で申し込む**。下の「camofox apply の手引き」に従う。各 event は **一度だけ** 試す（多重 click 厳禁）。
4. 申し込みが完了したら、そのイベントの gcal を `[PROPOSED]` から `[CONFIRMED]`（補欠なら `[WAITLIST]`）に更新する。手段は `gog --account "$GOG_ACCOUNT" calendar list --from <date> --to <date> --json` で event_id を取って `gog ... calendar update primary <id> --summary "..."`。
5. Slack `#metrics` に「申込結果 N 件 (CONFIRMED=K, WAITLIST=W, skipped=S)」と報告し、各案件のリンクと state を添える。
6. **verification-before-completion**: 受付完了メール (connpass `<no-reply@connpass.com>` / peatix `<info@peatix.com>` / lu.ma `<no-reply@lu.ma>` 等) を `gog gmail search 'newer_than:30m AND <event keyword>'` で実取得して message_id を確認する。1 件も取れなかったら `state/booking-history.jsonl` に `verify_failed` で記録し、その event は `[PROPOSED]` のまま残す。

### camofox apply の手引き (= レシピ。ハードコードはしない)

最初に `bash $LIFE_MANAGER_REPO/skills/camofox-browser/scripts/start.sh` で REST API (`http://localhost:9377`) を確認。既に起動済みなら spawn しない。

各 URL に対して:

A. **タブを開く**:
```
POST /tabs  body={url, userId:"anicca", sessionKey:"connpass"}
```
3-5 秒待ってから `GET /tabs/{id}/snapshot` で a11y tree を取る。

B. **状態を判断する** (snapshot を読む):
- `あなたは参加者` / `参加が確定` / `参加申し込み済` → **既に申込済**。skip して `state=already`。
- `あなたは補欠` → **既に補欠登録済**。skip して `state=already-waitlist`。
- `開催日時が重複している` / `お申込み出来ません` → **日時重複で不可**。skip して `state=skip-conflict`。
- `link "...申し込む"` / `link "補欠..."` / `link "キャンセル待ち..."` が見える → 次へ進む。
- どれも無い → `state=no-apply-button`。

C. **申し込みボタンを click**: snapshot で `link "..申し込.."` または `button "..申し込.."` の ref (`[eN]`) を読み取り、`POST /tabs/{id}/click body={ref:"eN", ...}`。

D. **遷移後 snapshot を取る**:
- ログイン redirect なら、メール `$CONNPASS_USERNAME`、パスワード `$CONNPASS_PASSWORD` で `POST /tabs/{id}/type` → ログインボタン click → 再 snapshot。
- 「申込確認」ページなら、**必須項目を埋める**:
  - 参加コメント (optional): 「参加させてください。Anicca = 自律運用する仏教 AI エンティティです」程度。
  - お名前 / 氏名 / フルネーム: `成田大祐` (profile.json の `identity.fullNameJa`)。
  - 会社・所属・組織: `Anicca（個人開発） / NAIST 情報科学領域 修士 / MUIT` (profile.json の `business.brandJa` + `education.statusJa` + `income.primary` を合成)。
  - 役職: `Founder / Caretaker`。
  - 電話: `080-4627-0314` (profile.json の `phone`)。
  - 職種 checkbox (必須): 該当するもの 1-2 個 (例: `フルスタックエンジニア・プロダクトエンジニア`、`機械学習エンジニア`)。
  - 連絡先 radio (必須): 最初の選択肢。「その他」は最後の手段。

E. **camofox の type が ref を無視する場合の workaround** (= 既知 bug。`feedback_browser_order_camofox_first.md` 記載): `POST /tabs/{id}/evaluate` で `document.querySelector('[name="<field-name>"]').value = "<val>"` を直接叩いて `input/change` を dispatch する。**この path は必ず snapshot で field 名 (`name=q_<id>` 等) を確認してから書く**。

F. **「申し込みを確定する」ボタンを click** (label は site 毎に異なる: `申し込みを確定する` / `申し込む` / `登録する` / `補欠登録` / `参加申し込み`)。再 snapshot。

G. **完了判定**: `イベント申し込みが完了しました` / `あなたは参加者` / `あなたは補欠` のいずれかが出れば成功。URL が `.../complete/` 等に遷移するのもサイン。出なければ `state=unverified-after-confirm` で stop し、`state/booking-history.jsonl` に snapshot 末尾 200 文字を記録して翌日 retry。

H. **結果を booking-history.jsonl に追記**:
```json
{"event":"apply_result","state":"applied|waitlist|already|already-waitlist|skip-conflict|no-apply-button|...","url":"...","title":"...","camofox_tab":"...","ts":"..."}
```
I. **gcal の `[PROPOSED]` を `[CONFIRMED]` (or `[WAITLIST]`) に書き換える**。手段:
```bash
EID=$(gog --account "$GOG_ACCOUNT" calendar list --from <date> --to <date> --json \
       | jq -r '.events[]? | select(.summary // "" | test("PROPOSED.*<url-fragment>")) | .id' | head -1)
gog --account "$GOG_ACCOUNT" calendar update primary "$EID" --summary "<新 summary>"
```

### 禁止 / 例外

- human/main agent が手で applied するのは禁止 (§0.5.1)。**あなた (Anicca) が camofox で実行する**。
- camofox が `consecutiveFailures > 3` なら 1 度だけ restart、それでもダメなら `state=camofox-down` で Slack DM し abort。
- ブラウザ順序: **camofox > cloak-browser > agent-browser** ([[feedback_browser_order_camofox_first]])。最初から camofox。
- CAPTCHA は **画面に実描画されるまで** 諦めない (HARD RULE)。出現したらその時点で `state=captcha-blocked` で record し Slack DM (= 唯一の例外)。
- 「日時重複で申込不可」「lateness.blocklistApply 該当」は予期される skip。`state=skip-conflict` / `state=blocked-blocklist` で record して次の candidate へ。

## Architecture

```
[profile.goals.ideal_state[]]
       ↓
[scan_gcal_horizon.py]  — 今日〜14日先で empty 1h+ slot
       ↓
[propose.py]  — firecrawl で domain ごとに event-detail URL 発掘 (connpass/lu.ma/peatix/techplay)
       ↓  candidates JSON
[3-gate filter] — anti_goals / blocklistApply / physical conflict
       ↓  approved
[apply.py]  — log + PROPOSED gcal 挿入 (HARD RULE #19, gcal-policy.sh 経由)
       ↓  candidate_approved + gcal_proposed in booking-history.jsonl
[Anicca が camofox で実 apply] ← 上の「camofox apply の手引き」
       ↓
[Anicca が gcal を PROPOSED → CONFIRMED / WAITLIST に update]
       ↓
[Anicca が Slack + 受付メール verify を実走]
```

## Sources (per domain)

| domain | sources | 補足 |
|---|---|---|
| AI_LT | connpass.com (event-detail URL), lu.ma/genai-tokyo, techplay.jp, peatix.com | URL whitelist: `connpass.com/event/<id>`, `peatix.com/event/<id>`, `lu.ma/<slug>`, `techplay.jp/event/<id>` |
| comedy | TwoPlus Comedy, Tokyo Comedy Bar (PR系のみ), 楽しいペチカ, ルミネよしもと, 浅草演芸ホール | **`live_entry@yahoo.co.jp` 完全 BAN** (Power of Free) |
| research | arxiv.org (週1 paper), NAIST 内 ゼミ slot | slot 埋めには使わない (apply 性質ではない) |
| job_BigTech | openai.com/careers, anthropic.com/careers, careers.google.com, metacareers.com | apply-to-funder と機能重複、slot 埋めには使わない |
| VC_apply | apply-to-funder の funder-portfolio.json で別 cron 処理 | (本 skill は埋めない) |

## 3-gate filter (apply 前の必須 check)

| gate | 条件 | NG action |
|---|---|---|
| 1 | `profile.goals.anti_goals` 全件適用 (深夜 / MUIT 業務時間 / 睡眠 / 移動長すぎ 等) | reject + history に `blocked:anti_goals:<reason>` |
| 2 | `profile.lateness.blocklistApply` (event url / organizer mail で grep) | reject + history に `blocked:blocklistApply` |
| 3 | 既存 gcal event と時刻 overlap (travel 30min バッファ込み) | reject + history に `blocked:physical_conflict` |

## Cron (Anicca 自走)

| name | schedule (JST) | what | cron id |
|---|---|---|---|
| `anicca-booking-daily` | `0 6 * * *` | 朝 6:00 — 14 日先まで slot scan + propose + apply + camofox 実申込 + gcal update | `4f43ef46-6473-4826-baee-c0932c822aab` |

## Run (cron が呼ぶ)

```bash
bash $LIFE_MANAGER_REPO/skills/anicca-booking/scripts/run.sh
# 末尾: SUMMARY_JSON: {"scanned": N, "approved": M, "applied": K, "blocked": J, "slack_review": L}
# その後、Anicca は「あなた (Anicca) への指示」セクションを実行する
```

## Failure modes

| 症状 | 対応 |
|---|---|
| connpass / Peatix login 失敗 | camofox stealth retry 1 回 → Slack DM `state=login-failed` |
| form 必須未入力エラー | 自然言語で field を読み直し profile から補完 → 再 submit |
| 文字数超過 | 敵対的に短縮 → 再 submit |
| CAPTCHA が実描画 | abort + Slack DM `state=captcha-blocked` |
| gcal-policy.sh 未経由で gcal 挿入 | HARD RULE #19 違反 → abort |
| booking-history.jsonl write 失敗 | exit 1 (silent skip 禁止) |

## HARD RULE #14 verify

末尾 mandatory:
```bash
bash $LIFE_MANAGER_REPO/skills/_shared/verify-public-state.sh \
  $LIFE_MANAGER_REPO/skills/anicca-booking/state/run.log \
  "booking run" \
  1
```

## Related

- `$LIFE_MANAGER_REPO/skills/camofox-browser/SKILL.md` — REST API (`:9377`) のエンドポイント仕様
- `$LIFE_MANAGER_REPO/skills/anicca-life-manager/` — depart_by call + 遅刻 mail
- `$LIFE_MANAGER_REPO/skills/_shared/lib/gcal-policy.sh` — HARD RULE #19 (全 event 挿入経由)
- `$LIFE_MANAGER_STATE_HOME/identity/profile.json` — goals.ideal_state / anti_goals / lateness.blocklistApply / identity.fullNameJa / phone / education.statusJa
