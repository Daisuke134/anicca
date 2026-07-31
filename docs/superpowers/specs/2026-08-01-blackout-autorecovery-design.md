# 停電ゼロ・ヒューマンループ設計 (Blackout Auto-Recovery)

- 作成: 2026-08-01
- 対象マシン: Mac mini (`AniccanoMac-mini.local`, Tailscale `100.99.82.95`), macOS 15.6 (24G84)
- 状態: **設計確定・実装90%完了・再起動検証待ち**

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
     │  autoLoginUser=anicca + /etc/kcpassword  │  ⚠️未検証
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
     │  net / tailscale / codex×2 / claude       │  ✅今回追加
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
| `/etc/kcpassword` | 存在 (2026-02-21作成) | 同左 | 既存 |
| Tailscale | システムデーモン | 同左 | 既存 |
| LaunchAgents | 189本 | 189本 | 既存 |
| **定期自動電源オン** | **なし** | **毎日 06:00 wakepoweron** | 今回 |
| **健全性監視** | **なし** | **60秒ごと5項目** | 今回 |
| **Claude RC keychain** | ロックでハング | 起動時に自動解錠 | 今回 |
| **Codex keepalive** | 健全な daemon を殺す | 壊れた1条件のみ修復 | 今回 |
| バックアップ | なし | **なし** | 未 |

監視ログの実測 (`~/recovery-setup/health.log`):
```
net=ok ts=ok codex1=connected codex2=connected claude=ok problems=0
```

## 5. TODO (順序が正本。番号順に着手)

| # | タスク | 実行者 | 状態 | ブロッカー |
|---|---|---|---|---|
| 1 | **再起動テスト** — 自動ログインが本当に効くか実証 | Anicca | ⬜ | Dais の承認 (接続が切れるため) |
| 2 | バックアップ設定 (Time Machine or rsync) | Anicca | ⬜ | 外付けディスク or 保存先の決定 |
| 3 | 停電検知 → Telegram 通知 | Anicca | ⬜ | なし |
| 4 | ルーターの復電動作確認 | Dais | ⬜ | 物理確認 |
| 5 | UPS 導入 (任意) | Dais | ⬜ | 購入 |

### #1 が最優先である理由

`/etc/kcpassword` は 2026-02-21 作成。**それ以降に Mac のパスワードを変更していれば
この鍵は無効**で、復電後にログイン画面で停止し、189本のループが全て沈黙する。
再起動しない限り検証不能。ここが**唯一の残存単一障害点**。

## 6. 残存リスク

| リスク | 影響 | 緩和策 |
|---|---|---|
| 自動ログイン失敗 (kcpassword 陳腐化) | **全停止・人手必須** | #1 で検証。失敗なら再生成 |
| バックアップ不在 | ディスク破損でデータ消失 | #2 |
| UPS 不在 | 毎回ハードな電源断 = 破損確率が蓄積 | #5 (任意) |
| ルーターが復電で戻らない | Mac は生きているが到達不能 | #4 |

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
| `~/.codex-acct2/` | ChatGPT#2 (daisukenarita53) の隔離 CODEX_HOME |

## 9. アカウント構成

| レーン | アカウント | プラン | 環境ID |
|---|---|---|---|
| Claude Remote Control | keiodaisuke@gmail.com | Max | `env_01GnjSLC5KA4jXhuw5eigP65` |
| ChatGPT #1 | keiodaisuke@gmail.com | pro | `env_e_6a5e30ef61948320a651f4c48ff8c53e` |
| ChatGPT #2 | daisukenarita53@gmail.com | plus | `env_e_6a6ca7b726f48320a2ba97899bced6d2` |

ChatGPT iOS アプリは同時1アカウントのみ (公式仕様)。#2 を使うときはアプリ側でログアウト→ログイン。
Mac 側は両方常時接続なので、切り替えは電話側だけで完結する。
