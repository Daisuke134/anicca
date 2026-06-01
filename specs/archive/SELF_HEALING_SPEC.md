# SELF_HEALING_SPEC — Anicca 自己修復 & 遅刻防止 仕様書

最終更新: 2026-05-25 / 作成理由: 2026-05-25 の「起こし電話が鳴らない＋全exec cron一日中死亡」インシデントを受け、自己修復を恒久化し記録する。

---

## 0. 原則
- cron の `status="ok"` は信用しない。**`summary` を読む**。"exec denied"/"実行できませんでした"/"Message failed" があれば偽ok=実失敗。
- 自己修復は **detector(データ収集) → LLM(文脈読んで実修復) → 未完了は再実行 → 「直した」報告** （Sutando friction-detector/regression-search 方式）。ハードコード修復禁止。
- exec=full は全自動化の生命線。allowlist に振れたら全 exec cron が死ぬ。

---

## 1. インシデント記録 (2026-05-25)
| 事象 | 真因 | 影響 |
|------|------|------|
| 朝の起こし電話 鳴らず | exec policy が `allowlist`(空) に振れ exec 全拒否 | wake-call/lateness-guard/naist/larry/x-marketing/watercolor… 全 exec cron が 07:00-19:53 死亡 |
| 全cron故障が気付かれない | self-improving-agent は受動ログのみ / health-check は cron個別失敗を見ない | Dais が手動で指摘するまで放置 |
| 偽ok | status=ok でも summary=denied | 監視が「正常」と誤認 |

検証: run.sh 直接実行 → Twilio sid=CA... completed 18s → Dais 応答確認（通話path自体は正常）。位置/OwnTracks は無関係。

---

## 2. 自己修復アーキテクチャ（実装済 + 計画）

```
全208 cron ──失敗/結果──▶ #metrics (208/208 配信設定済) + cron/runs/*.jsonl (ローカル真実)
                                   │
 HEARTBEAT.md §2 (claude-p毎時 / openclaw 6h・同じ脳が両方走る):
   [1] exec-policy-guard.sh   ← 最優先。exec≠full なら full 復元+報告 ✅実装済
   [2] health-check.py --fix  ← gateway/launchd/files/memory/stuck-loop ✅
   [3] disk-janitor/run.sh     ← 時刻不問の掃除を畳込 ✅
   [4] cron-doctor.sh          ← 全error cronの error+summary+sessionログ集約(検知専用) 🔜#22
 HEARTBEAT.md §3.5 (LLM実修復) 🔜#22:
   各故障: 偽ok判定→本物なら根本修正→社会投稿未投稿は `openclaw cron run`再実行→「直した」報告
```

### 2.1 実装済パッチ (#26)
**exec-policy 固定:**
```
openclaw exec-policy set --security full --ask off --ask-fallback full
```
**新規 `skills/anicca-core/scripts/exec-policy-guard.sh`**: `openclaw exec-policy show` で security 抽出→full でなければ `exec-policy set --security full` で復元+#metrics報告。
**HEARTBEAT.md §2 先頭に配線**（毎ビート両ハーネスが exec=full 保証）。

### 2.2 計画パッチ #22 — cron-doctor を detector化
**FILE `skills/anicca-core/scripts/cron-doctor.sh`**: `case "$err"` の自動編集ブロックを削除→各 error cron の `openclaw cron runs --id` (error+summary+sessionKey) + `cron/runs/<name>.jsonl` 末尾 を「故障ブリーフ」として stdout 出力するだけ。
**FILE `workspace/HEARTBEAT.md` §3.5 追加**: ブリーフ各件を ①summaryで偽ok/本物判定 ②偽okは配信設定のみ修正 ③本物はsessionログ+skillコード読んで根本修正 ④社会投稿未投稿は `openclaw cron run <id>` 再実行しURL確認(#8) ⑤「X→原因Y→Zで直した→再投稿成功」報告。不明なら雑に直さず原因報告。

---

## 3. 遅刻防止システム (P0.7 / #25) — 仕様 & パッチ

### 3.1 現状アーキ（既存・ほぼ完成）
| 部品 | 役割 |
|------|------|
| `gcal_departures.py` | departBy = 予定開始 − 移動時間(origin→dest 実トランジット) − 準備バッファ。origin=新鮮位置(≤45分)or HOME |
| `lateness_check.py decide()` | home_latlon と haversine で at_home 判定 / vel>0.8=moving / action: call/nudge/ok/stale-location |
| `guide_me_now.py` | live位置→逆ジオ→ETA→電話誘導(Googleマップ的催促) |
| `renraku.py` | 遅刻確定→ prof.stakeholder_for(文脈)→ gog gmail自動送信 / 無ければSlack下書き |

### 3.2 P0.7 パッチ（直す3+1点）

**PATCH 1 — stale時に「家と仮定して鳴らす」(今日鳴らなかった直接バグ)**
FILE: `skills/lateness-guard/scripts/lateness_check.py` decide() L87-89
```diff
     if age_min > STALE_MIN:
-        return {"action": "stale-location",
-                "reason": f"location {int(age_min)}m old — won't guess (need fresh fix; OwnTracks=Move)",
-                "event": nxt}
+        # stale でも「最後の位置=家 & 動いてない」なら家にいる前提で出発判断する
+        # (朝: 一晩静止で fix は古いが 実際 家に居る = 出勤を逃さない)。
+        # 家から離れた位置で stale の時だけ「分からない」として鳴らさない。
+        if not (at_home and not moving):
+            return {"action": "stale-location",
+                    "reason": f"location {int(age_min)}m old & 家から{int(dist)}m — 居場所不明で保留",
+                    "event": nxt}
+        # else: 家で静止 → そのまま下の departBy 判定へ（assume_home）
```

**PATCH 2 — 移動中 late の連続催促を自動化**
FILE: `lateness_check.py` decide() moving 分岐 L105-106
```diff
     if moving:
-        return {"action": "ok", "reason": f"en route, moving (vel={vel}) — reassess next tick", "event": nxt}
+        # 移動中でも departBy を過ぎてる/間に合わない ETA なら guide(催促)を出す。
+        if mins <= 0 or (travel is not None and mins < travel):
+            return {"action": "guide", "reason": f"移動中だが間に合わない (残{int(mins)}m < 移動{travel}m) — 急かす", "event": nxt}
+        return {"action": "ok", "reason": f"en route, moving (vel={vel}) — 間に合う見込み", "event": nxt}
```
+ run.sh 側で action=='guide' → `guide_me_now.py` 発火、action=='call' → lateness call、を分岐（現状 RENRAKU_NEEDED のみ解釈→ guide/call/nudge も解釈するよう拡張）。

**PATCH 3 — renraku を動的・文脈化（静的lookup卒業）**
FILE: `skills/lateness-guard/scripts/renraku.py` send_renraku()
- 現状: `prof.stakeholder_for(ctx)` で profile登録の相手のみ。
- 追加: 未登録時に Slack下書きで終わらず、**heartbeat の LLM に「この予定の連絡先を記憶/カレンダー/メール文脈から特定し、メール or connpass等のサイトを browser操作して連絡せよ」とタスクを渡す**（RENRAKU_DYNAMIC イベントを出力→§3 が拾う）。歯医者→歯医者 / connpass→主催者 を文脈で解決。

**PATCH 4 — 位置鮮度（transportは変えない）**
FILE: `workspace/loco/server.js` — HTTP応答に reportLocation cmd を返す
```diff
-    res.json([]);                       // 現状: 空配列
+    res.json(staleNudge ? [{ "_type":"cmd", "action":"reportLocation" }] : []);
```
（端末が起きてる隙に追加 fix を引く。MQTTは iOS suspend で無効=不採用。端末は OwnTracks 常時許可+Move 済）。

### 3.3 検証
- PATCH 1: `LATE_STALE_MIN` 超の古い位置 + 家座標 で decide() が action=call を返すか単体テスト。
- 実機: 明朝 7:50 morning-leave で 古い位置でも出発電話が鳴るか確認。

---

## 4. 関連メモリ
- exec_policy_lockout_incident / cron_autofix_heartbeat_loop / anicca_core_sutando_infra
- lateness_guard_and_location / realtime_voice_wakeup_bridge / feedback_post_manually_not_api_zero_views
