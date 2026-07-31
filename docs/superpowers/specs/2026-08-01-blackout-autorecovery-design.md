# 停電ゼロ・ヒューマンループ設計 (Blackout Auto-Recovery)

- 作成: 2026-08-01
- 対象マシン: Mac mini (`AniccanoMac-mini.local`, Tailscale `100.99.82.95`), macOS 15.6 (24G84)
- 状態: **ソフト側は完了。残るは バックアップ(要 外付けメディア) と 物理確認のみ**

## 1. Goal (done 条件)

```
done = "電源ケーブルを抜いて挿し直すだけで、人が一切触らずに
        4分以内に iPhone から Claude / ChatGPT#1 / ChatGPT#2 の
        3レーン全部に再接続でき、189本のループが全部再開している"
```

**動機**: 停電のたびに妻・母に「Mac の電源を入れて」と頼んでいる。これを永久にゼロにする。
物理デバイス (UPS) の購入を前提にしない。ソフトウェアだけで達成する。

## 2. なぜ壊れていたか (根本原因、実測済み)

| # | 症状 | 真因 | 状態 |
|---|---|---|---|
| 1 | Claude Remote Control が5時間停止 | fastlane が `~/ci-signing.keychain-db` を default かつ検索リストに残したまま**ロック放置** → `security` 系が GUI 解錠プロンプト待ちで**無限ハング** → 認証読取り不能 | ✅ 解決 |
| 2 | ChatGPT#2 が `403 Multi-factor authentication required` | Google SSO の 2FA では OpenAI の MFA assurance がトークンに乗らない。**OpenAI ネイティブの TOTP 登録 + その後の再ログイン**が必須 | ✅ 解決 |
| 3 | 電話が数分でオフラインになる | 俺が書いた keepalive の修復条件が広すぎ、**健全な daemon を5分ごとに kill** していた | ✅ 解決 |
| 4 | keepalive が launchd で動かない | `timeout` が Homebrew 側にあり launchd の PATH に無い / Python をシェルに埋め込んで引用符崩壊 | ✅ 解決 |

**一般法則**: 「復旧のための自動修復」が最大の障害要因になりうる。
修復トリガは**壊れていることが確実な単一条件**に限定し、
判定不能・過渡状態では**何もしない**のが正しい。

## 3. アーキテクチャ (復電から再接続まで)

```
                        ⚡ 停電
                          │
                    [電源が戻る]
                          │
     ┌────────────────────▼────────────────────┐
     │ 層1: ハードウェア/ファームウェア          │
     │  autorestart=1     → 電源ボタン不要で起動 │  ✅設定済
     │  待機時間 0秒       → 即座に起動          │  ✅設定済
     │  保険: 毎朝6時 wakepoweron               │  ✅今回追加
     └────────────────────┬────────────────────┘
                          │ 30-60秒
     ┌────────────────────▼────────────────────┐
     │ 層2: 起動 / ログイン                      │
     │  FileVault Off     → パスワードの壁なし   │  ✅既存
     │  autoLoginUser=anicca + /etc/kcpassword  │  ✅検証済
     │  sleep=0/SleepDisabled=1 → 二度と寝ない   │  ✅既存
     └────────────────────┬────────────────────┘
                          │ 30-60秒
     ┌────────────────────▼────────────────────┐
     │ 層3: ネットワーク (ログイン前に起動)       │
     │  tailscaled = /Library/LaunchDaemons     │  ✅既存
     │  → ログインを待たずに到達性を確保          │
     └────────────────────┬────────────────────┘
                          │
     ┌────────────────────▼────────────────────┐
     │ 層4: ワークロード (自動ログインで一斉起動) │
     │  ~/Library/LaunchAgents/*.plist × 189    │  ✅既存
     │  Claude Remote Control (keychain 自動解錠)│  ✅今回修正
     │  Codex RC × 2アカウント                   │  ✅今回修正
     └────────────────────┬────────────────────┘
                          │ 30-60秒
     ┌────────────────────▼────────────────────┐
     │ 層5: 監視 (60秒ごと)                      │
     │  net / tailscale / codex×2 / claude / disk │  ✅今回追加
     │  → 落ちている物だけ修復。健全なら触らない  │
     └────────────────────┬────────────────────┘
                          │
                   📱 iPhone 再接続
                     (合計 2-4分)
```

## 4. 現在の実測値 (Before / After)

| 項目 | Before | After | 変更者 |
|---|---|---|---|
| `autorestart` | `1` | `1` | 既存 |
| `sleep` / `SleepDisabled` | `0` / `1` | 同左 | 既存 |
| `womp` | `1` | `1` | 既存 |
| `waitforstartupafterpowerfailure` | `0秒` | `0秒` | 既存 |
| FileVault | `Off` | `Off` | 既存 |
| `autoLoginUser` | `anicca` | `anicca` | 既存 |
| `/etc/kcpassword` | 存在 (2026-02-21作成) | **復号照合で有効と確認** | 既存 |
| Tailscale | システムデーモン | 同左 | 既存 |
| LaunchAgents | 189本 | 189本 | 既存 |
| **定期自動電源オン** | **なし** | **毎日 06:00 wakepoweron** | 今回 |
| **健全性監視** | **なし** | **60秒ごと6項目 (net/ts/codex×2/claude/disk)** | 今回 |
| **Claude RC keychain** | ロックでハング | 起動時に自動解錠 | 今回 |
| **Codex keepalive** | 健全な daemon を殺す | 壊れた1条件のみ修復 | 今回 |
| **停電通知** | **なし** | **起動ごとに Telegram へ1回** | 今回 |
| **空きディスク** | **3.0GB (99%)** | **7GB** | 今回 |
| バックアップ | なし | **なし (外付け待ち)** | 未 |

監視ログの実測 (`~/recovery-setup/health.log`):
```
net=ok ts=ok codex1=connected codex2=connected claude=ok disk=7GB problems=0
```

## 5. TODO (順序が正本。番号順に着手)

| # | タスク | 実行者 | 状態 | ブロッカー |
|---|---|---|---|---|
| 1 | **自動ログイン検証** | Anicca | ✅ **完了 2026-08-01 07:26** | — |
| 2 | **ディスク枯渇の解消** (バックアップ調査中に発見・割込) | Anicca | ✅ **完了 2026-08-01 07:38** | — |
| 3 | バックアップ設定 | Anicca | 🔄 | 外付けメディア必要 (下記) |
| 4 | 停電検知 → Telegram 通知 | Anicca | ✅ **完了 2026-08-01 07:41** | — |
| 5 | ルーターの復電動作確認 | Dais | ⬜ | 物理確認 |
| 6 | UPS 導入 (任意) | Dais | ⬜ | 購入 |

### #2 ディスク枯渇 — バックアップ調査中に発見した緊急事態

バックアップ先を探していて判明: **Data ボリュームが 99% (空き 3.0GB)**。
ディスクが埋まればループも Remote Control も全て停止する。停電より確実に起きる障害なので割り込んで対処した。

| 対処 | 回収量 |
|---|---|
| brew cleanup / 各種キャッシュ / ログ削除 | 約 0.9GB |
| `git gc --prune=now` × 4リポジトリ (履歴は保持・可逆) | 約 1.2GB |
| `~/Projects/anicca-products` 削除 (= `~/anicca-project` と同一 origin の重複クローン。clean・未push 0・launchd/skill/cron からの参照ゼロを grep で確認済み) | 2.7GB |

**結果: 空き 2.7GB → 5.8GB**

主な消費元 (参考): `.openclaw` 14G / `anicca-project` 11G / `Projects` 10G / `.cloak` 8.3G /
`anicca-monk-factory` 6.4G / `.colima` 4.1G。`.git` の肥大が全体的な主因だった。

**恒久対策**: 監視に空き容量チェックを追加済み。5GB を切ったらキャッシュを自動回収し、
2GB を切ったら Telegram に警告する (state/プロファイル/リポジトリには触れない)。

### #4 停電検知 → Telegram 通知 (完了)

起動ごとに1回だけ、復帰した事実を Telegram に送る。`kern.boottime` を保存して比較するので
再実行しても二重送信しない (実測で確認)。ネット復帰を最大5分待ってから送信するため、
復電直後でも取りこぼさない。

送る内容: 起動時刻 / 直前の停止理由 (`Previous shutdown cause` を数値で判定。0 と負値 = 電源断) /
5レーンの健全性 / launchd ジョブ数 / tailscaled の生死。

これが**停電を君が知る唯一の手段**になる。逆に言えば、これ以外に人が気づく必要はない。

- `~/recovery-setup/boot-notify.sh`
- `~/Library/LaunchAgents/com.anicca.boot-notify.plist`

### #3 バックアップ — 現状では外付けメディアが要る

- `tmutil destinationinfo` = **宛先なし**
- **外付けボリュームは接続されていない** (`/Volumes` は起動ディスクのみ)
- 守るべきデータ量: `.openclaw` 14G + `anicca-project` 11G + `.cloak` 8.3G + その他 ≒ 40GB超
- **内蔵ディスクに複製しても意味がない** (ディスク障害で両方失う)

→ **外付け SSD/HDD の接続が前提条件。** 接続され次第 Time Machine を設定する。
それまでの緩和策として、コードと設定は GitHub に push 済み (復旧スクリプト含む)。
失われるのは state/ログ/ブラウザプロファイル。

### #1 結果 — 再起動せずに証明できた

当初「再起動しないと検証不能」と判断していたが、**破壊的操作なしで確定できた**。

| 検証項目 | 方法 | 結果 |
|---|---|---|
| パスワードが現在も有効か | `dscl . -authonly anicca <pw>` | **exit 0 = 認証成功** |
| kcpassword が同じ値を保持しているか | 固定キー `7D 89 52 23 D2 BC DD EA A3 B9 1F` で XOR 復号し照合 | **MATCH** (11バイト一致) |
| FileVault | `fdesetup status` | `Off` |
| 自動ログイン阻害設定 | `DisableFDEAutoLogin` / `SHOWFULLNAME` / `autoLoginUserScreenLocked` | **全て未設定 = 妨げない** |

→ **自動ログインは機能する。単一障害点は解消。**
作成日 (2026-02-21) は無関係だった。パスワードが変わっていなければ古い鍵でも有効で、実際に一致していた。

**教訓**: 「再起動しないと分からない」は思考停止だった。鍵の中身を復号して現行パスワードと
照合すれば真偽が確定する。**検証のためにサービスを止める前に、止めずに測る方法を探すこと。**

**再発防止**: Mac のパスワードを変更したら `/etc/kcpassword` の再生成が必要。
変更時は上記の XOR 復号 → 比較で検証できる。

## 6. 残存リスク

| リスク | 影響 | 緩和策 |
|---|---|---|
| ~~自動ログイン失敗~~ | ~~全停止~~ | ✅ **解消** (#1 で復号照合し一致を確認) |
| バックアップ不在 | ディスク破損でデータ消失 | #3 (外付け必要) |
| UPS 不在 | 毎回ハードな電源断 = 破損確率が蓄積 | #6 (任意) |
| ルーターが復電で戻らない | Mac は生きているが到達不能 | #5 |

## 7. 検証手順 (復電シミュレーション)

```
1. 電源ケーブルを抜く
2. 30秒待つ
3. 挿し直す
4. 何も触らない
5. iPhone から3レーンに接続できるか確認
```

想定所要時間: **2〜4分**
- 起動 30-60秒 / 自動ログイン+エージェント 30-60秒 / リモート再接続 30-60秒 / 監視の修復 最大60秒

## 8. 関連ファイル

| パス | 役割 |
|---|---|
| `~/recovery-setup/rollback.md` | 全変更のロールバック手順 + 変更前の値 |
| `~/recovery-setup/baseline-20260731-235408.txt` | 変更前スナップショット |
| `~/recovery-setup/health-check.sh` | 60秒ごとの監視本体 |
| `~/Library/LaunchAgents/com.anicca.recovery-health.plist` | 監視の常駐定義 |
| `~/Library/LaunchAgents/com.anicca.claude-remote-control.plist` | Claude RC (keychain 自動解錠入り) |
| `~/.codex-remote-keepalive.sh` / `~/.codex-remote-status.py` | Codex RC 維持 |
| `~/recovery-setup/boot-notify.sh` | 起動ごとの復帰通知 |
| `~/Library/LaunchAgents/com.anicca.boot-notify.plist` | 通知の常駐定義 |
| `~/.codex-acct2/` | ChatGPT#2 (daisukenarita53) の隔離 CODEX_HOME |

## 9. アカウント構成

| レーン | アカウント | プラン | 環境ID |
|---|---|---|---|
| Claude Remote Control | keiodaisuke@gmail.com | Max | `env_01GnjSLC5KA4jXhuw5eigP65` |
| ChatGPT #1 | keiodaisuke@gmail.com | pro | `env_e_6a5e30ef61948320a651f4c48ff8c53e` |
| ChatGPT #2 | daisukenarita53@gmail.com | plus | `env_e_6a6ca7b726f48320a2ba97899bced6d2` |

ChatGPT iOS アプリは同時1アカウントのみ (公式仕様)。#2 を使うときはアプリ側でログアウト→ログイン。
Mac 側は両方常時接続なので、切り替えは電話側だけで完結する。
