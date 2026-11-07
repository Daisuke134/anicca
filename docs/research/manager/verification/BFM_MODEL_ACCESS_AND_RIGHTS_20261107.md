# BFM-01／BFM-02：Be.FM・Centaur利用権と計算資源の監査

2026-11-07現在。公式Hugging Face APIのメタデータと著者モデルカード、正本Managerロードマップを検証した。**未許諾の重みダウンロードと課金GPUは行っていない。**

| モデル | モデル実体の状況 | アクセス・利用権の確認 | まだ行っていないこと |
|---|---|---|---|
| Qwen3-4B-Instruct-2507 GGUF | 2,497,280,736 bytes、SHA256 2fde00ce69dd4899c70d020845e2638353015bba0fdf161b3eb965f2bca4464e、GitHub無料CPUで2026-11-07実forward | 公開量子化重み、基盤Qwenのモデルカードとライセンスを前提に出力を厳密検証 | 人間個人予測精度や実介入効果の証明 |
| Be.FM1.5-4B | Qwen3-4BベースへのLoRAアダプター、公開メタデータで66,126,768 bytes、HF revision 85b1fd83... | gated=auto。モデルカードのApache-2.0表記に対し、リンク先のBe.FM利用規約には非商用・派生/再配布制限が残る。MacのHF_TOKEN、Modal正規Secretは未接続 | アクセス承諾と利用権の書面確認、正規LoRA実forward、同条件比較、商用実装 |
| Centaur Llama3.1-70B | 公開モデルメタデータの30 safetensors重みファイル、合計141,107,497,872 bytes（約141.1GB）。HF revision 7e42dbd2... | gated=false、Meta Llama 3.1の独自条件。対応する権利の遵守が必要。Macの空き領域・無料CPUは本格bf16推論に不足 | Centaur70B実forward、Psych-101同条件評価、ライセンス・費用上限と資源確認 |

一次出典： https://huggingface.co/befm/BeFM1.5-4B 、 https://huggingface.co/marcelbinz/Llama-3.1-Centaur-70B 、 https://www.nature.com/articles/s41586-025-09215-4 。

**科学的注意：** Centaurの学習元Psych-101は160実験/約1,000万選択で、外部holdoutが論文で報告されているが、それをAniccaのモデル実行済み成果と取り違えない。

**実行しなかった理由：** モデルがAPIで検索可能なことは、使用権利・料金承諾・実体取得の認可を意味しない。非商用が疑われるBe.FMを勝手に商用製品へ配備しない。141GBのCentaur重みを小容量Macへ取得しない。

**残るゲート：** Be.FMの原権利者の正式な規約の適用範囲と研究/商用許諾、HFアカウントによる規約承諾、Modal利用認証と費用条件。CentaurはMeta Llama条件、評価データの用途・参加者権利・GPU費用上限を確定してから実行する。今回得たQwenの限られた実結果でBe.FM/Centaurの成績を代用しない。
