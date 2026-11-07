# Manager研究付録｜MG-01実ホストShadow（発表資料の1スライド追加原稿）

## Slide. 実行できることと、人間の助けになることは違う

**画面テキスト：** 2026-11-07 / MG-01 TECH S1 / 自社公開6ページ / Qwen3-4B real CPU / source SHA checked three times.

| 初期比較 | 既存ルール | Qwen3-4B |
|---|---:|---:|
| 同じ公開6ページの判断 | NO_ACTION | REVIEW_ONLY |
| 処理時間 | 4.287ms | 46,606ms |
| モデル品質の昇格 | ー | **保留：不一致・未説明** |

公式GitHub Actions run #42393800213 = success。公式billing APIの課金対象時間0ms、run全体135,000ms。モデル/原ページSHA一致。**外部書込0、通知0、利用者データ0、幸福・害の測定0。** 技術比較の受入だけ実施、MG-01完了・次MG-02。追加の専用UIは不要だが正規権限・取消手段は省略しない。

**発表者ノート：** モデルを接続しただけでは人間の行動を上手に予測できるとは限りません。今回は実際にQwenの重みをロードし、自社公開ページの同じSHAの情報からQwenと既存ルールへ判断を求めました。既存ルールは問題なし、Qwenは要検討と答えました。どちらが真に正しいか、Qwenの具体的指摘もないため、サイトは変更しません。推論は実行され、時刻・費用・一致しない結果は全て証拠に固定しました。これがリスクの小さいShadow導入です。次のMG-02では本番で他の情報を扱う場合の正当な権限・データ目的・撤回を確定させます。人間の便益の証拠と混同しません。

**出典:** https://github.com/Daisuke134/life-manager/actions/runs/42393800213 / 元のcompany SSOTのMG-01 / GitHub Actions Billing Docs / リポジトリ内 machine-readable receipts。
