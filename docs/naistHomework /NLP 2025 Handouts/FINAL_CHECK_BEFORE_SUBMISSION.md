# PDF提出前の最終確認チェックリスト

## ✅ 実行済みセルの確認

以下のセルが実行されていることを確認してください：

- [x] Cell 1: 個人情報（execution_count: 15）✓
- [x] Cell 4: データセットダウンロード（execution_count: 16）✓
- [x] Cell 6: ライブラリインポート（execution_count: 24）✓
- [x] Cell 8: ByteLMクラス定義（execution_count: 18）✓
- [x] Cell 10: テストコード実行（execution_count: 19）✓
- [x] Cell 13: 言語識別コード実行（execution_count: 20）✓
- [x] Cell 17: 追加実験（execution_count: 22）✓
- [ ] Cell 14: LANGUAGE入力セル（execution_count: null）⚠️ **実行が必要**

## 📋 PDF提出前の必須確認事項

### 1. すべての実行結果が表示されているか

#### Cell 10の出力（必須）
以下の4行がPDFに表示されているか確認：
```
English model: perplexity: 13.431301184867843 prob: 0.999999999997258
Japanese model: perplexity: 196.09094718142185 prob: 0.9999999999997222
Simplified Chiense model: perplexity: 155.13165142613286 prob: 0.9999999999964516
Traditional Chiense model: perplexity: 182.54658837935466 prob: 1.0000000000032374
```

#### Cell 13の出力（必須）
以下の内容がPDFに**完全に**表示されているか確認：
- "Found 102 language files" のメッセージ
- 全102言語のperplexity値（afrからzulまで）
- "Results Summary"セクション
- "Best match (lowest perplexity): oci"
- "Perplexity: 11.186163"
- "Top 5 languages"のリスト

**⚠️ 重要**: Cell 13の出力が長いため、PDFで途中で切れていないか必ず確認してください。

### 2. すべてのコードが表示されているか

以下のコードセルがPDFに含まれているか確認：
- [x] Cell 1: 個人情報入力コード
- [x] Cell 4: データセットダウンロードコード
- [x] Cell 6: ライブラリインポートコード
- [x] Cell 8: ByteLMクラス定義（**バグ修正のコメントを含む**）
- [x] Cell 10: テストコード
- [x] Cell 13: 言語識別コード
- [x] Cell 14: LANGUAGE入力コード

### 3. すべての説明が表示されているか

以下のMarkdownセルがPDFに含まれているか確認：
- [x] Cell 0: 課題説明
- [x] Cell 2: Instructions
- [x] Cell 3: データセット説明
- [x] Cell 5: ライブラリ説明
- [x] Cell 7: ByteLM説明
- [x] Cell 9: テストコード説明
- [x] Cell 11: "Why perplexities are different?"の説明
- [x] Cell 12: 言語識別の説明
- [x] Cell 15: "How you identify the language?"の説明
- [x] Cell 16: 追加実験の説明

### 4. 個人情報が正しく表示されているか

PDFの最初の方に以下が表示されているか確認：
- NAME: daisuke narita
- STUDENT_ID: 2411218
- EMAIL: narita.daisuke.nd4@naist.ac.jp

### 5. バグ修正のコメントが表示されているか

Cell 8のByteLMクラス内に以下のコメントが含まれているか確認：
```python
# BUG FIX: The original code assigned -inf for zero probabilities...
# Solution: Apply Laplace smoothing (add-one smoothing)...
```

### 6. 言語識別の回答が表示されているか

Cell 14に以下が表示されているか確認：
- LANGUAGE = 'Occitan'
- 説明文（ociコードとperplexity値の記載）

## 🖨️ PDF保存時の注意点

### ColabでのPDF保存手順

1. **すべてのセルを再実行**（念のため）
   - 「ランタイム」→「すべてのセルを再実行」
   - または、上から順にすべてのセルをShift+Enterで実行

2. **Cell 14を実行**
   - LANGUAGE入力セルも実行して値を確定させる

3. **PDFとして保存**
   - 「ファイル」→「印刷」（またはCtrl+P / Cmd+P）
   - 「送信先」で「PDFに保存」を選択
   - 「レイアウト」で「縦」を選択（推奨）
   - 「保存」をクリック

4. **PDFの内容を確認**
   - ダウンロードしたPDFを開く
   - 上記のチェックリストを確認
   - 特にCell 13の出力が完全に表示されているか確認

### PDFで確認すべき重要なポイント

1. **ページ数**: 全セルが含まれているか（おそらく10-15ページ程度）
2. **実行結果の完全性**: Cell 13の出力が途中で切れていないか
3. **コードの可読性**: コードが正しくフォーマットされているか
4. **個人情報**: 名前、学籍番号、メールが正しく表示されているか

## ⚠️ よくある問題と対処法

### 問題1: Cell 13の出力が途中で切れている
**対処法**: 
- Colabの出力設定を確認
- PDF保存時に「すべての出力を含める」オプションを選択
- 必要に応じて、Cell 13の出力をスクロールしてすべて表示してからPDF保存

### 問題2: コードが正しく表示されない
**対処法**:
- Colabの表示設定を確認
- PDF保存時に「コードセルを含める」オプションを確認

### 問題3: 実行結果が表示されていない
**対処法**:
- 該当セルを再実行
- エラーが出ていないか確認
- 実行結果がセル出力に保存されているか確認

## ✅ 最終確認

PDF提出前に以下を確認：

1. [ ] すべてのセルが実行されている（Cell 14も含む）
2. [ ] Cell 10の出力が表示されている
3. [ ] Cell 13の出力が**完全に**表示されている（102言語すべて）
4. [ ] 個人情報が正しく表示されている
5. [ ] バグ修正のコメントが表示されている
6. [ ] 言語識別の回答（Occitan）が表示されている
7. [ ] すべての説明セクションが表示されている
8. [ ] PDFのページが途中で切れていない

## 📤 提出

すべての確認が完了したら：
1. PDFファイルをダウンロード
2. https://edu-portal.naist.jp/ にログイン
3. 「NLP #3」の「2025 NAIST 4102 NLP」に提出
4. PDFファイルをアップロード

**提出期限**: December 19th, 2025 JST

