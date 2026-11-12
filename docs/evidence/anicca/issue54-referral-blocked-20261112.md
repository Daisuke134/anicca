# Issue #54 リファラル実装 — 制約による停止報告（2026-11-12）

状態: BLOCKED。MVP 未実装。製品コードは変更していない。実装完了として扱わない。

## 確認した正本

- [Issue #54](https://github.com/Daisuke134/anicca-ops/issues/54) 全文。
- VM の `goals/anicca-revenue-growth-as-life-manager/hidden_files/affirmation-referral-loop-spec-2026-11-05.md` 全文。
- anicca-ops `files/mobile-growth-playbook-2026-11-12.md` E1。
- Life Manager origin/main `e4e694298e78cadcb411de3ae048e776e18377c3` 起点。ブランチ `codex/issue54-referral`。

## 停止理由とコードの証拠

委任文の「既存の課金実験 exp529116692b の対象コードには触らない。触る必要が出たら、実装を止めてサマリに理由を書く」を適用した。

`apps/mobile/anicca-ios/aniccaios/Onboarding/OnboardingFlowView.swift` は最初のアファメーションと通知意思表示からペイウォールへ進むフローを所有する。冒頭コメントおよび `gateVariant`、`resolveOnboardingPaywallEntry`、`handlePaywallDismissedAsFree`、`handlePaywallDismissalBlocked` に hard/soft 群の分岐がある。hard 群は購入・復元の権利取得までオンボーディングを完了しない。仕様の紹介導線はこの初回価値体験直後であり、コード入力・活性化・権利付与を同フローへ接続する必要があると判断した。

`Onboarding/PaywallPackageSelection.swift` の `PaywallGateVariant` は `HARD-PAYWALL-20261108` と offering `anicca_variant_b_hard` を定義する。コード内の名前と委任文の RevenueCat provider ID の対応は管理画面で未検証。実験の本番状態は読み戻していない。

`Services/SubscriptionManager.swift` は CustomerInfo を権利の入力とし、サーバー同期では利用量のみを更新して plan/status を上書きしない。`Models/SubscriptionInfo.swift` が Premium 判定を持つ。ローカル日数だけで Premium を偽装する変更は行っていない。

最初のアファメーションは既にペイウォール前に存在する。紹介実装が技術的に不可能だとは主張しない。実験対象フローへの接続が今回の禁止範囲に含まれるという保守的な判断で停止した。子画面への独立追加や RevenueCat のサーバー側プロモーション付与でフロー変更を避けられるかは未検証。

## 仕様との対応

| 要件 | 状態・残件 |
|---|---|
| 自分のコード表示・共有・任意のコード入力 | 未実装 |
| コードによる帰属 | 未実装。App Store をまたぐ文脈消失を計測済み扱いにしない |
| 初回全文体験＋受取意思表示で両面7日 | 未実装。インストールだけでは付与しない |
| 紹介者累計30日、7日以内の活性化期限 | 未実装。永続台帳・重複付与防止・並行更新制御が必要 |
| 共有・保留・確定・獲得日数の表示、不正保留・問合せ | 未実装 |
| 共有率・クリック率・2定義の転換率・K・参加率・D1/D7・サイクル時間 | 全て未計測。イベント未実装。共有シート完了を実際の送信先数と同一視しない。クリック計測には実リンク側の観測も必要 |

## 検証と環境差分

確認済み: git fetch、正規 origin、Git root/common directory、指定ブランチ作成、仕様とコードの静的照合。製品コード差分なし。
未実施: Swift ビルド（VM に環境なし）、CI ビルド、実機、初回共有から両面付与までの実行、RevenueCat readback、イベント受信、初回10件コホートの D1/D7。ビルド成功・報酬付与成功は主張しない。

`bash scripts/verify-source-boundary.sh` は失敗。スクリプトは `$HOME/Projects/life-manager-main` またはその `.worktrees` を要求する一方、今回の明示指定は `/home/hatch/workspace/life-manager-wt`。origin は正規 URL、common dir は `/home/hatch/workspace/life-manager/.git`。チェックの書換えや他 checkout の変更は行っていない。

指定 `~/.agents/skills/superpowers/using-superpowers` は存在せず、インストール済み `/home/hatch/.codex/plugins/cache/openai-curated-remote/superpowers/7.0.1/skills/using-superpowers/SKILL.md` と brainstorming を実読。technical-writing も参照。Astra Advisor は公開ツールに見当たらず未使用。

## 再開に必要な判断

実験終了後に着手するか、初回価値体験画面と権利同期へのリファラル接続を実験対象の変更禁止から除外するかを担当者が決定する。その後、既存バックエンドと認証の所在を確認し、サーバーで帰属・活性化・累計上限・両面付与の再実行安全性を実装する。今回の調査はバックエンド設計完了を意味しない。

本 PR は停止理由のレビュー資料のみ。Issue は閉じない。実装 PR としての完了条件は未達。作業ツリーはレビュー対応のため保持する。
