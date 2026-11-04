# Manager Masterclass｜P04-1〜P04-6 因果推論と行動介入

**更新：2026-11-04（Asia/Tokyo）。** このディレクトリは教育講義と架空実験の再現資料。**実人間への介入、実公開RCTの前向き効果予測、Manager Behavior Foundation Modelの科学的な優位性の実証ではない。**

**唯一の全ロードマップ・進捗正本：`ROADMAP_STATUS_JA.md`。** 本READMEやMANIFESTを講義の別SSOTとみなさない。P04-1〜6は講義・人工実験まで進み、次はP05-1。P04-5の実在公開RCTに対する未見研究効果予測、P00-3の権限・同意、実世界での方策検証は未完了。

## 2026年11月5日 13:00–14:00｜神経科学ジャーナルクラブ

**本番ではこちらの厳選33枚版を使う。** 来場者は神経科学・計算論的神経科学の研究者とM1/M2。人間行動シミュレーションの専門知識を前提とせず、歴史、モデルの種類、代表的な研究・企業、ベンチマーク、因果と限界を基礎から説明し、Managerは最後の3枚に留める。

| ファイル | 内容 |
| --- | --- |
| [60分発表 PowerPoint](journal_club/AI_BEHAVIOR_JOURNAL_CLUB_60MIN_JA.pptx) | **33枚**、編集可能・全ページに日本語発表者ノート |
| [60分発表 PDF](journal_club/AI_BEHAVIOR_JOURNAL_CLUB_60MIN_JA.pdf) | **33ページ**、発表画面用 |
| [全33枚日本語読み上げ原稿](journal_club/SPEAKER_SCRIPT_60MIN_JA.md) | 1ページごとの自然な読み上げ文と元スライド・時間 |
| [60分の進行表](journal_club/RUN_OF_SHOW_60MIN_JA.md) | **41.7分講演＋15分質疑＋約3分の余裕**、章別時間・重要スライド・短縮ルート |
| [発表版を再生成](journal_club/build_60min_journal_club.py) | 正本の85枚版＋85ページPDFから再構築。別々に管理し、元ファイルを破壊しない |

**優先順位：** ①基礎と研究史 ②どの対象にどの模型を使うか ③既存研究・企業は何を主張しているか ④何を検証して何をまだ検証していないか ⑤最後にManagerが目指すこと。数式の厳密な導出・企業の細かい数字・P04-6の全シミュレーションは本番で列挙しない。質疑用の長い資料に残す。

## 全85枚の詳細保存版（本番で一挙上映しない）

| ファイル | 内容 |
| --- | --- |
| [詳細85枚PowerPoint](journal_club/AI_BEHAVIOR_JOURNAL_CLUB_JA.pptx) | 既存82枚を保存し、P04-6研究付録3枚を追加 |
| [詳細85ページPDF](journal_club/AI_BEHAVIOR_JOURNAL_CLUB_JA.pdf) | 85ページ。元82ページ保持＋追加3ページを画像レンダリングで統合 |
| [全85枚の日本語発表ノート](journal_club/SPEAKER_NOTES_JA.md) | 1〜85の全ページ分。PowerPoint内部にも全85枚のノートを保存 |
| `journal_club/build_p04_6_appendix.py` | 82枚版→85枚版への追加作成に使用。すでに85枚なら二重追加しない |
| `journal_club/build_p04_45_appendix.py` | **歴史的な74枚→82枚作成スクリプト**。現在85枚版への再実行はしない |
| `journal_club/export_p04_45_pdf.py` | **歴史的な74ページ→82ページPDF結合スクリプト** |
| `journal_club/RUN_OF_SHOW_JA.md` | 元のフル講義の履歴上の進行表。**2026-11-05本番は60MIN版の進行表を優先** |

## 講義の本文

| 資料 | 内容 | 学習の検証 |
| --- | --- | --- |
| `P04-1_JA.md` | 観察vs介入・DAG・潜在的結果 | 完全架空データ、14テスト |
| `P04-2_JA.md` | RCT・ATE・ITT・信頼区間 | 架空RCT、17テスト |
| `P04-3_JA.md` | 交絡・g-formula・IPW・AIPW・DiD | 架空30,000人、26テスト |
| `P04-4_JA.md` | CATE・効果異質性・方策選択・媒介 | 架空24,000人＋媒介20,000人、12テスト |
| `P04-5_JA.md` | study holdout・予測凍結・介入効果予測 | 架空180研究、11テスト。**実公開RCTの未見予測は未実施** |
| `P04-6_JA.md` | 事前登録・方策対方策RCT・意思決定価値・無計画な途中解析 | 架空40,000人＋A/A 750試行、16テスト。**実研究の事前登録・実介入は未実施** |

単体テストは合計 **96/96件成功**（14 + 17 + 26 + 12 + 11 + 16）。`evidence/TEST_RESULTS_P04_1_TO_P04_6.txt` に最新のログを保存。教材のテスト合格を実世界への有効性の証明と混同しない。

## P04-6の新規実行結果（完全架空）

- 対象40,000人。政策群への無作為割当：Manager型約19,835人／比較型約20,165人。
- 同じ事前特徴、同じ候補行動、同じ観測期間を設定。比較方策は有用な固定ヒューリスティックであり「世界最強のbaseline」とは認定しない。
- 主成果（完了マイナス通知人工費用0.02/回）は、Manager型平均0.33616／比較方策0.32003、差 **+1.613pt**（95%近似CI **+0.688〜+2.539pt**、p≈0.000635）。
- 人工の期待効果真値は**+2.00pt**。設定した世界での証拠に過ぎない。
- 効果ゼロの架空A/Aを750回反復し、最終1回の未補正検定による偽陽性**4.27%**、途中6回のいずれかで有意なら成功とした偽陽性**15.20%**。
- 結果生成前に`P04-6_PREANALYSIS_PLAN_SYNTHETIC.json`を保存し`P04-6_PLAN_FREEZE_RECEIPT.json`でSHA256を固定。**外部公開研究登録はしていない**。
- 全人工40,000人のCSVは`evidence/P04-6_POLICY_RCT_SYNTHETIC.csv`。結果は`evidence/P04-6_POLICY_RCT_SYNTHETIC_RESULTS.json`。

## ローカル再現

Python 3.11+とNumPy、PowerPoint編集はpython-pptx、PDF/追加スライド生成にはpypdf・Pillowが必要。

```bash
cd docs/research/manager/masterclass/2026-11-04-p04-causal/experiments
python3 -m unittest discover -p 'test_p04_*.py' -v
python3 p04_6_preregistered_policy_value.py
```

本番発表版は`journal_club/build_60min_journal_club.py`で再生成。**詳細マスターを消す／発表で全85枚を使う運用はしない**。全33枚の構成・書式と85枚の正規教材を保持する。

## 監査

`evidence/P04-6_JOURNAL_CLUB_QA.json` に、33枚・33ページ、85枚・85ページ、発表版33枚の全ノート、詳細版85枚の全ノート、元82枚本文の保持、凍結予測ハッシュ、人工RCT計画ハッシュ、96テストの照合を記録。ファイルのSHA256とサイズは`MANIFEST.json`に保存する。**外部の研究ベンチマーク検証や実施権限の承認を行ったとは主張しない。**
