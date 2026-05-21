【保存推奨】
NotebookLMのスライド生成、ボタン1発でも
スライドは作れますがプロンプト次第で
クオリティが10倍変わります。

5つのシーン別プロンプト例をまとめました👇

1. 研修・教育資料を作りたい
--
温かみのある配色で柔らかい印象にしてください。
背景はサンドベージュ(#F5E6D3)、
文字はチョコールグレー(#4A4A4A)、
アクセントにオリーブグリーン(#8B9556)を使用。
自然光のような柔らかいトーンで統一。
1スライド1メッセージのみ。
テキストは最小限に抑えてください。
--
```yaml
design_style:
  color_palette:
    background: "#F5E6D3"
    text: "#4A4A4A"
    accent: "#8B9556"
  tone: "ナチュラル・オーガニック"
  layout: "1スライド1メッセージ"
  typography:
    heading: "ゴシック体, Bold"
    body: "ゴシック体, Regular, 最小限"
```
2. IT・スタートアップの提案資料
--
先進的な印象を与えるデザインで
作成してください。
背景は濃紺(#1A2332)、
文字は白(#FFFFFF)、
アクセントにシアン(#00D4FF)を使用。
ダーク背景で「未来感」を演出。
図解・ピクトグラム中心の構成。
テクノロジー感のあるビジュアルで統一してください。
--
YAML/JSON形式：
```yaml
design_style:
  color_palette:
    background: "#1A2332"
    text: "#FFFFFF"
    accent: "#00D4FF"
  tone: "テック・モダン"
  visual_style: "図解・ピクトグラム中心"
  layout: "ダーク背景、未来感重視"
  typography:
    heading: "サンセリフ, Bold"
    body: "サンセリフ, Regular"
```
3. 会社ブランドに完全統一
--
コーポレートカラー(プライマリ:#2C3E50、
アクセント:#3498DB)をベースにスライド作成。
全スライドでブランドガイドライン準拠。
ロゴカラーをアクセントに使用し、
企業の統一感を重視してください。
フォントはゴシック体、見出しはBold指定。
--
YAML/JSON形式：
```yaml
design_style:
  color_palette:
    primary: "#2C3E50"
    secondary: "#ECF0F1"
    accent: "#3498DB"
  brand: "コーポレート準拠"
  layout: "ブランドガイドライン統一"
  typography:
    heading: "ゴシック体, Bold"
    body: "ゴシック体, Regular"
  visual_elements: "ロゴカラーをアクセントに使用"
```
4. Before/After比較資料
--
Before/Afterの対比レイアウトで作成してください。
左側に課題・現状、右側に解決策・理想を配置。
矢印やコントラストで変化を明確に表現。
数値データは大きく目立たせてください。
提案資料の説得力がアップする構成で。
--
YAML/JSON形式：
```yaml
design_style:
  layout: "Before/After対比"
  structure:
    left: "課題・現状"
    right: "解決策・理想"
  visual_elements:
    - "矢印で変化を表現"
    - "コントラスト強調"
    - "数値データを大きく表示"
  purpose: "提案資料・説得力重視"
```
5. SNS映え・イベント告知用
--
ビビッドな配色で目を引くデザインに。
背景は白(#FFFFFF)、
メインカラーはコーラルピンク(#FF6B9D)、
アクセントにティール(#1DD3B0)を使用。
ポップでデジタルな雰囲気。
大きな見出しと有機的なシェイプを活用し、
SNS映えするビジュアルで統一してください。
--
YAML/JSON形式：
```yaml
design_style:
  color_palette:
    background: "#FFFFFF"
    primary: "#FF6B9D"
    accent: "#1DD3B0"
  tone: "ポップ・デジタル"
  visual_style: "有機的シェイプ活用"
  typography:
    heading: "大きく目立つ見出し"
    body: "読みやすさ重視"
  purpose: "SNS映え・イベント告知"
```

＜重要点＞
✅ プロンプト例は「シンプル版」
→実務ではもっと詳細に書くと精度UP
✅ YAML/JSON形式使用
プロ級コントロール可能
✅ AI生成なのでガチャ要素あり
→数回試す前提
✅ 1日15回制限(Pro版)に注意