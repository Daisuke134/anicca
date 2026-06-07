---
title: "naist OSS 化 v2 — Deferred (out of scope for v1)"
date: 2026-06-04
status: deferred
parent_spec: 2026-06-04-skill-trio-oss-design.md (§ 4.3, D6)
parent_plan: 2026-06-04-skill-trio-oss-and-monk-fix.md (Task C2)
---

# naist OSS 化 v2 — Deferred Decision Record

## TL;DR

`naist` skill は **v1 で OSS 化しない**。 v2 で「naist-specific を外して generic university-automation template に refactor」 してから OSS 化を再評価する。 現在: 内部 skill のまま `~/.openclaw/skills/naist/` で運用、 Slack 日本語 digest のみ、 X 投稿しない、 GitHub 公開しない。

## なぜ defer (= parent spec D6 引用)

| risk | 内容 |
|---|---|
| Academic-integrity の他人事 | 課題の自動提出 + 履修自動登録 を public 化 = 大学 + Dais 個人の評判 risk |
| NAIST 固有性 | `idp.naist.jp` / `edu-portal.naist.jp` SSO / 履修期間 / 11 cron schedule |
| ハードコード日本語 visible-text | 「ログインはこちら」「9 提出」 など find-by-text procedure が naist 固有 |
| Generic 化のスコープ大 | SAML provider 抽象化 + UI element discovery generic 化 + 大学固有 procedure を YAML 駆動化が必要 |

## v2 の前提条件

| condition | 必要 work |
|---|---|
| Academic integrity 配慮 | README 頭に大型 disclaimer + 既定 `--dry-run` flag + `--really-submit` 明示要求 |
| SAML provider 抽象化 | `naist-cli auth login --provider shibboleth --idp <url>` 等の generic interface |
| 大学固有 procedure を data 化 | `procedures/<university>.yaml` に find-by-text 手順 / DOM selectors / 各 mode の URL を抽出 |
| 例: 他大学テスト | 慶應 SFC / 東大 UTAS / 京大 KULASIS / 等 1-2 校で fork → adapt → 動作確認 |

## いつ v2 を着手すべきか (trigger)

- naist v1 が **30 日連続で実害ゼロ** (academic integrity 苦情 / 大学からの注意ゼロ) で安定
- Dais の修了 (NAIST 卒業) もしくは Anicca の他大学 user からの強い要望
- v2 spec を `docs/superpowers/specs/YYYY-MM-DD-naist-oss-v2-design.md` として brainstorm + writing-plans

## 関連 artifact

- 現行 spec: `~/.openclaw/skills/naist/SKILL.md` (canonical で in-place)
- 現行 cron: `~/.openclaw/cron/jobs.json` 内 `naist-*` (11 cron)
- 現行 state: `~/.openclaw/state/naist/<slug>/` (= Dais の `dais` slug)

## Out of scope (= ここで明示的に「やらない」)

- naist v1 skill の rewrite / refactor (動いてる、 触らない)
- naist の anicca-products / anicca-products への merge
- naist の X 投稿 (= academic integrity public risk)

## このファイルの役割

v1 spec の D6 deferral を独立 file として記録 → 将来 `grep naist OSS v2 docs/superpowers/` で発見可能 → 着手時の前提条件 + 関連 artifact を 1 箇所参照。
