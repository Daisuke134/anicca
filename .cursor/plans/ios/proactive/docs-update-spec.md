# Docs Update Spec — Proactive iOS Focus

## 概要
Aniccaのドキュメント（README / AGENTS / CLAUDE）を、現行の「iOSプロアクティブエージェント」中心に更新する。  
デスクトップ/音声系の記述は削除し、iOS + Backendの現状に合わせる。  
App Store 次回提出は 1.4.0、直近承認は 1.3.0（Phase 6）を反映する。  
READMEには公式LP（https://aniccaai.com）を記載する。

## 受け入れ条件
| # | 条件 | 判定 |
|---|------|------|
| 1 | README.mdが英語になっている | ✅ |
| 2 | AGENTS.md / CLAUDE.md が日本語になっている | ✅ |
| 3 | desktop/voiceに関する記述が削除されている | ✅ |
| 4 | iOSの現行機能（ProblemType/Nudge/Onboarding等）と整合 | ✅ |
| 5 | API記述が apps/api の現状と整合 | ✅ |
| 6 | 既存のブランチ運用/テスト戦略/憲法ルールは削除しない | ✅ |
| 7 | App Store: 1.3.0 承認済み（Phase 6）/ 1.4.0 次回提出 を明記 | ✅ |
| 8 | READMEに公式LP URL（https://aniccaai.com）を記載 | ✅ |

## As-Is（現状）
| 対象 | 問題 |
|---|---|
| README.md | desktop/voice中心。iOSのプロアクティブ路線と不整合 |
| AGENTS.md | Voice/WebRTC/旧APIフローの記述が残存 |
| CLAUDE.md | 一部最新化済みだが、説明の粒度・用語に混在あり |
| roadmap | 方針は明確だがREADME/AGENTS/CLAUDEに反映されていない |

## To-Be（変更後）
| 対象 | 変更内容 |
|---|---|
| README.md | iOSプロアクティブ中心に再構成。API/レポ構造をiOS+backendへ整理。Roadmap参照と公式LPを明記。 |
| AGENTS.md | iOS/Backendの実態を反映し、Voice/desktop記述を削除。主要コンポーネント/エンドポイントを最新化。 |
| CLAUDE.md | 既存の憲法ルールは保持。iOS現状/主要ファイル/API/用語を最新化。最終更新日を更新。 |

## To-Be チェックリスト
| # | To-Be | 対応 |
|---|---|---|
| 1 | READMEを英語に再構成 | ☐ |
| 2 | AGENTSのプロアクティブ記述へ更新 | ☐ |
| 3 | CLAUDEの最新実装状況/用語整合 | ☐ |
| 4 | 1.3.0/1.4.0情報の記載 | ☐ |
| 5 | desktop/voice記述の完全削除 | ☐ |
| 6 | roadmap.md への参照追加 | ☐ |
| 7 | READMEに公式LP URLを明記 | ☐ |

## テストマトリックス
| # | To-Be | テスト名 | カバー |
|---|---|---|---|
| 1 | 言語整合 | Doc Language Check | ☐ |
| 2 | Desktop/Voice排除 | Doc Content Scan | ☐ |
| 3 | iOS/API整合 | Manual Cross Review | ☐ |
| 4 | LP URL記載 | Doc Link Check | ☐ |

## E2E シナリオ
| # | シナリオ | 対象 |
|---|---|---|
| 1 | N/A | ドキュメント更新のため対象外 |

## Skills / Sub-agents
| ステージ | 使用するもの | 用途 |
|---|---|---|
| Spec作成 | `/plan` | 更新方針の設計 |
| Specレビュー | `/codex-review` | 仕様レビューゲート |
| 実装レビュー | `/codex-review` | コミット前のレビュー |

## 境界（Boundaries）
### 触るファイル
| 種別 | パス |
|---|---|
| Spec | `.cursor/plans/ios/proactive/docs-update-spec.md` |
| Docs | `README.md`, `AGENTS.md`, `CLAUDE.md` |

### 触らないファイル
| 種別 | パス |
|---|---|
| コード | `aniccaios/`, `apps/api/`（参照のみ） |
| その他 | デスクトップ関連ディレクトリ（編集しない） |

## ローカライズ
| 対象 | 言語 |
|---|---|
| README.md | 英語 |
| AGENTS.md | 日本語 |
| CLAUDE.md | 日本語 |

## 実行手順
| # | 手順 | 詳細 |
|---|---|---|
| 1 | 現行機能の確認 | `aniccaios/` と `apps/api/` の主要構造・ルーティングを参照 |
| 2 | README更新 | iOS+backend中心の英語READMEに刷新（LP URL含む） |
| 3 | AGENTS更新 | Voice/desktop削除、iOS+API実態へ |
| 4 | CLAUDE更新 | 実装状況/用語/更新日を最新化 |
| 5 | 整合性レビュー | roadmapとの整合/ルール保持を確認 |

## レビューチェックリスト
| # | チェック項目 | 確認 |
|---|---|---|
| 1 | 憲法ルール（ブランチ/テスト戦略）を削除していない | ☐ |
| 2 | desktop/voice記述が残っていない | ☐ |
| 3 | READMEが英語、他2つが日本語 | ☐ |
| 4 | 1.3.0/1.4.0情報が明記 | ☐ |
| 5 | roadmapと矛盾がない | ☐ |
| 6 | LP URLが https://aniccaai.com になっている | ☐ |

## ユーザー作業（実装前）
| # | タスク | 手順 | 取得するもの |
|---|---|---|---|
| 1 | なし | - | - |

## ユーザー作業（実装中）
| # | タイミング | タスク | 理由 |
|---|---|---|---|
| 1 | なし | - | - |

## ユーザー作業（実装後）
| # | タスク | 確認項目 |
|---|---|---|
| 1 | なし | - |
