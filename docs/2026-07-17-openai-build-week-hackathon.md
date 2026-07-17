# OpenAI Build Week (Devpost) — 調査メモ 2026-07-17

Source: https://openai.devpost.com/ + /rules + /details/dates（crwl 実測、2026-07-17 18:35 JST）

## 概要

| 項目 | 内容 |
|---|---|
| 名称 | OpenAI Build Week |
| テーマ | "Join a global week of building with Codex" |
| 賞金総額 | $100,000（4トラック × 1st $15k / 2nd $10k） |
| 参加者 | 32,278 registered |
| 必須技術 | **Codex + GPT-5.6 の両方**（"Build any project with Codex and GPT 5.6"） |

## 締切（JST換算）

| イベント | PT | JST |
|---|---|---|
| 無料クレジット申請（$100） | Jul 17 12:00pm PT | **Jul 18 04:00 JST（本日深夜）** |
| 提出締切 | Jul 21 5:00pm PT | Jul 22 09:00 JST |
| 審査 | Jul 22 – Aug 5 PT | – |
| 発表 | ~Aug 12 PT | Aug 13 06:00 JST |

クレジット申請フォーム: https://forms.gle/Ncu6iGkaHq1SwUmEA（first-come、Jul 21までに使い切る）

## トラック（4つ）

1. **Apps for Your Life** — consumer: productivity, health, personal finance 等 ← **Anicca 該当**
2. Work and Productivity
3. Developer Tools — testing, DevOps, agentic workflows, security ← anicca OSS framework も該当しうる
4. Education

## 既存プロジェクト参加の条件（Anicca に直結）

> "Projects must be either newly created during the Hackathon Submission Period or, if the Project existed prior..., must have been **meaningfully extended using Codex and/or GPT-5.6 after the Submission Period start date**."

- 既存OK。ただし Jul 13 以降の拡張分を Codex session logs + dated commits で証明する必要。
- README に「Codex がどこで workflow を加速したか」「GPT-5.6 と Codex をどう使ったか」を明記必須。

## 提出物

- 動くプロジェクト（Codex + GPT-5.6 使用）
- カテゴリ選択
- 説明文
- **デモ動画 <3分**（public YouTube、Codex と GPT-5.6 の使い方を音声で説明）
- **repo URL**（public、または private + testing@devpost.com と build-week-event@openai.com に共有）
- **/feedback Codex Session ID**（core functionality を作った session）提出フォームに必須
- テストアクセスは無料で審査期間末まで維持

## 審査基準

1. Technological Implementation — Codex をどれだけ深く使ったか
2. Design — PoC でなく完成した product experience
3. Potential Impact — 実在する audience の実在する問題
4. Quality of the Idea — 新規性

## 適格性

- 日本 OK（OpenAI API supported countries）
- 除外: Brazil, Quebec, Russia, OFAC 諸国

## 判断メモ

- **Anicca (iOS 行動変容 app) = "Apps for Your Life" トラックに素直に該当。**
- ネック: 審査の最重要軸が「Codex 使用の深さ」。Anicca は Claude Code で開発しており、勝つには Jul 13–21 の間に **Codex + GPT-5.6 で意味ある機能拡張を実際に行い、session ID を残す**必要がある。
- 代替案: `~/anicca` OSS（AI economic independence framework）を Developer Tools / agentic workflows トラックで出す手もある。
- コスト: 無料 $100 credit（本日 JST 深夜 04:00 締切）。超過分は自腹。
- 締切まで実働 ~4.5日。デモ動画 + README + Codex session 証跡が必要なので、機能は小さく絞るのが正解。
