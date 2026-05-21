# Orchestrated by Anicca (VPS)

Created: 2026-02-11
Manager: Anicca (OpenClaw on VPS)
Player: Codex (on Mac via Tailscale SSH)

This file proves the Manager/Player pattern works across machines.

---

## 絶対ルール: 人間を介在させない

- **このプロジェクトで指示を出すのは Cursor（このチャット）と VPS Anicca だけ。人間は介在しない。**
- **Cursor → VPS Anicca への指示:** 必ず以下で送る。Slack メンションや「人間が Control UI で打つ」前提は書かない。
  ```bash
  ssh anicca@46.225.70.241 'openclaw agent --agent anicca --message "指示内容"'
  ```
- **Anicca → Cursor 側に返す必要があれば:** Anicca は Slack や cron など既存の経路を使う。人間に「コマンド叩いて」と言わせない。
- ドキュメント・説明では「人間がメンション」「人間が Control UI で」といった表現は使わない。**Cursor と Anicca がメッセージを取り合う**前提で書く。


オンボーディング最適化	A/B テスト、ファネル改善	Mixpanel + RevenueCat 連携
Paywall	価格テスト、表示タイミング	RevenueCat Paywall
TikTok Ads	広告運用自動化	クリエイティブ生成 + 配信
App Store Review	収集 + 自動返信	ASC API 連携
Newsletter	自動配信	コンテンツ生成 + 配信
iPad サポート	v1.6.2	spec 作成済み（未実装）
スキル化	全ロジックを SKILL.md に	再利用可能な形に