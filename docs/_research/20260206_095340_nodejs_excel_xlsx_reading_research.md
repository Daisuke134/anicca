# Node.js Excel (.xlsx) ファイル読み込み調査レポート

**調査日時**: 2026-02-06 09:53:40
**調査対象**: Node.jsおよびコマンドラインでのExcelファイル読み込みベストプラクティス
**制約**: pipインストール不可（npm/npxのみ使用）

---

## 📊 調査結果サマリー

```
調査完了: Node.js Excel 処理
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📦 推奨パッケージ: @e965/xlsx v0.20.3
📌 npx ワンライナー: convert-excel-to-json v1.7.0
⚠️  セキュリティ: 従来の xlsx パッケージは脆弱性あり（使用禁止）
🔧 MCP サーバー: @negokaz/excel-mcp-server が利用可能
🔒 セキュリティ: 入力検証・ファイルサイズ制限が必須
```

---

## 1. 最新バージョンと推奨パッケージ

| パッケージ | 最新バージョン | 推奨度 | 備考 |
|-----------|--------------|--------|------|
| **@e965/xlsx** | 0.20.3 | ⭐⭐⭐⭐⭐ | SheetJSの安全なfork、セキュリティ対応済み |
| **convert-excel-to-json** | 1.7.0 | ⭐⭐⭐⭐ | npxワンライナー対応、CLI使用に最適 |
| **xlsx2csv** | - | ⭐⭐⭐ | CSV変換専用、軽量 |
| **xlsx** (npm公開版) | 0.18.5 | ❌ | 脆弱性あり、使用禁止 |

---

## 2. セキュリティ上の重大な注意

### ⚠️ 従来の `xlsx` パッケージは使用禁止

```bash
# ❌ 禁止（脆弱性あり）
npm install xlsx
```

**理由**:
- npm公開版は0.18.5（4年前公開）で更新停止
- DoS（Denial of Service）の脆弱性
- Prototype Pollution の脆弱性
- SheetJS公式がnpm公開を停止済み

**根拠**: [TheLinuxCode - NPM + SheetJS XLSX in 2026](https://thelinuxcode.com/npm-sheetjs-xlsx-in-2026-safe-installation-secure-parsing-and-real-world-nodejs-patterns/)

---

## 3. 推奨インストール方法

### A. @e965/xlsx（プログラム利用向け）

**推奨される安全なインストール**:

```bash
# 最新版インストール
npm install @e965/xlsx

# または公式CDNから直接
npm install --save https://cdn.sheetjs.com/xlsx-latest/xlsx-latest.tgz

# 特定バージョン指定（推奨）
npm install --save https://cdn.sheetjs.com/xlsx-0.20.3/xlsx-0.20.3.tgz
```

**package.jsonで厳密なバージョン固定**:

```json
{
  "dependencies": {
    "@e965/xlsx": "0.20.3"
  }
}
```

**CommonJS 使用例**:

```javascript
const xlsx = require("@e965/xlsx");
const workbook = xlsx.readFile("sample.xlsx", {
  cellDates: true,  // 日付をDateオブジェクトに変換
  dense: true       // メモリ使用量削減
});

// セーフティパース（ヘッダー検証付き）
const sheet = workbook.Sheets["Sheet1"];
const rows = xlsx.utils.sheet_to_json(sheet, { header: 1 }); // 配列形式で取得

// ヘッダー検証
const expectedHeaders = ["Name", "Email", "Age"];
const actualHeaders = rows[0];
if (JSON.stringify(actualHeaders) !== JSON.stringify(expectedHeaders)) {
  throw new Error("Invalid header format");
}

// データを安全にマッピング
const data = rows.slice(1).map(row => ({
  name: row[0],
  email: row[1],
  age: row[2]
}));
```

**ESM 使用例**:

```javascript
import * as xlsx from "@e965/xlsx";
const workbook = xlsx.readFile("sample.xlsx", { cellDates: true });
```

---

### B. convert-excel-to-json（npx ワンライナー向け）

**最新バージョン**: 1.7.0

**npx ワンライナー**:

```bash
# 基本形
npx convert-excel-to-json --sourceFile="data.xlsx"

# 設定オプション付き
npx convert-excel-to-json --config='{"sourceFile": "data.xlsx"}'
```

**出力形式**:

```json
{
  "Sheet1": [
    { "COLUMN_A": "value1", "COLUMN_B": "value2" },
    { "COLUMN_A": "value3", "COLUMN_B": "value4" }
  ],
  "Sheet2": [
    { "NAME": "John", "AGE": "30" }
  ]
}
```

**特徴**:
- 全シートを読み込み（シート名がキー）
- 各行がオブジェクト形式
- インストール不要でnpx経由で実行可能

**根拠**: [npm - convert-excel-to-json](https://www.npmjs.com/package/convert-excel-to-json)

---

### C. xlsx2csv（CSV変換専用）

**インストール**:

```bash
git clone https://github.com/papnkukn/xlsx2csv && cd xlsx2csv
npm install -g .
```

**CLI使用例**:

```bash
# 基本形
xlsx2csv sample.xlsx output.csv

# オプション付き
xlsx2csv --verbose --sheet "Sheet1" --separator ";" input.xlsx output.csv
```

**オプション**:

| オプション | 説明 |
|-----------|------|
| `--sheet [name]` | 特定シートを指定 |
| `--range [A1:C3]` | セル範囲を指定 |
| `--separator [char]` | 区切り文字（カンマ、セミコロン、タブ） |
| `--data [type]` | 出力タイプ（formula, value, display） |
| `--force` | 既存ファイル上書き |

**Node.jsライブラリとしても使用可能**:

```javascript
const xlsx2csv = require('node-xlsx2csv');
const options = { verbose: true, sheet: "Sample" };

xlsx2csv('sample.xlsx', options, function(error, result) {
  if (error) return console.error(error);
  console.log(result);
});
```

**根拠**: [GitHub - papnkukn/xlsx2csv](https://github.com/papnkukn/xlsx2csv)

---

## 4. MCP（Model Context Protocol）サーバー

### @negokaz/excel-mcp-server

**概要**: Claude等のAIアシスタントがExcelファイルを直接操作できるMCPサーバー

**インストール（Mac/Linux）**:

```json
{
  "mcpServers": {
    "excel": {
      "command": "npx",
      "args": ["--yes", "@negokaz/excel-mcp-server"],
      "env": {
        "EXCEL_MCP_PAGING_CELLS_LIMIT": "4000"
      }
    }
  }
}
```

**インストール（Windows）**:

```json
{
  "mcpServers": {
    "excel": {
      "command": "cmd",
      "args": ["/c", "npx", "--yes", "@negokaz/excel-mcp-server"],
      "env": {
        "EXCEL_MCP_PAGING_CELLS_LIMIT": "4000"
      }
    }
  }
}
```

**Smitheryによるインストール**:

```bash
npx -y @smithery/cli install @negokaz/excel-mcp-server --client claude
```

**主な機能**:

| ツール | 機能 |
|-------|------|
| `excel_describe_sheets` | シートのメタデータ取得 |
| `excel_read_sheet` | セルデータ読み込み（ページネーション、数式表示対応） |
| `excel_write_to_sheet` | セルへの値・数式書き込み、新規シート作成 |
| `excel_create_table` | 範囲をExcelテーブル形式に変換 |
| `excel_copy_sheet` | シートの複製 |
| `excel_format_range` | 罫線、フォント、塗りつぶし、数値書式設定 |
| `excel_screen_capture` | シートのスクリーンショット（Windows限定） |

**対応フォーマット**:
- .xlsx
- .xlsm
- .xltx
- .xltm

**システム要件**:
- Node.js 20.x 以降

**他のMCPサーバー**:

| サーバー | GitHub | 特徴 |
|---------|--------|------|
| **haris-musa/excel-mcp-server** | [GitHub](https://github.com/haris-musa/excel-mcp-server) | Triple transport対応（stdio, SSE, HTTP）、ピボットテーブル・チャート対応 |
| **Excel-MCP-Server-Master** | [GitHub](https://github.com/guillehr2/Excel-MCP-Server-Master) | ClaudeAI統合特化 |

**根拠**:
- [GitHub - negokaz/excel-mcp-server](https://github.com/negokaz/excel-mcp-server)
- [LobeHub - Excel MCP Server](https://lobehub.com/mcp/negokaz-excel-mcp-server)

---

## 5. セキュリティベストプラクティス（2026年版）

### 必須のセキュリティ対策

| # | 対策 | 理由 |
|---|------|------|
| 1 | **ファイルサイズ制限** | DoS攻撃防止（推奨: 10MB以下） |
| 2 | **シート数・行数制限** | メモリ枯渇防止 |
| 3 | **ヘッダー検証** | 不正なキー名による攻撃防止 |
| 4 | **`header: 1`でパース** | オブジェクトキー汚染防止 |
| 5 | **`Object.create(null)`使用** | プロトタイプ汚染防止 |
| 6 | **lockfile コミット** | 依存関係の固定 |
| 7 | **`npm audit`定期実行** | 脆弱性検出 |

### セーフティパースのパターン

```javascript
const xlsx = require("@e965/xlsx");
const fs = require("fs");

function safeParseExcel(filePath, maxSizeMB = 10) {
  // 1. ファイルサイズチェック
  const stats = fs.statSync(filePath);
  const fileSizeMB = stats.size / (1024 * 1024);
  if (fileSizeMB > maxSizeMB) {
    throw new Error(`File too large: ${fileSizeMB.toFixed(2)}MB (max: ${maxSizeMB}MB)`);
  }

  // 2. パース（配列形式）
  const workbook = xlsx.readFile(filePath, {
    header: 1,        // 配列形式（オブジェクト汚染防止）
    cellDates: true,
    dense: true,
    defval: null      // undefined防止
  });

  // 3. シート数制限
  const sheetNames = workbook.SheetNames;
  if (sheetNames.length > 10) {
    throw new Error(`Too many sheets: ${sheetNames.length} (max: 10)`);
  }

  const sheet = workbook.Sheets[sheetNames[0]];
  const rows = xlsx.utils.sheet_to_json(sheet, { header: 1, defval: null });

  // 4. 行数制限
  if (rows.length > 10000) {
    throw new Error(`Too many rows: ${rows.length} (max: 10000)`);
  }

  // 5. ヘッダー検証（ホワイトリスト）
  const expectedHeaders = ["name", "email", "age"];
  const actualHeaders = rows[0];

  // 危険なキー名をブロック
  const dangerousKeys = ["__proto__", "constructor", "prototype"];
  for (const header of actualHeaders) {
    if (dangerousKeys.includes(header)) {
      throw new Error(`Dangerous header detected: ${header}`);
    }
  }

  // 6. 安全なマッピング（Object.create(null)使用）
  const data = rows.slice(1).map(row => {
    const obj = Object.create(null); // プロトタイプ汚染防止
    expectedHeaders.forEach((key, index) => {
      obj[key] = row[index];
    });
    return obj;
  });

  return data;
}

// 使用例
try {
  const data = safeParseExcel("user-upload.xlsx");
  console.log(data);
} catch (error) {
  console.error("Parse failed:", error.message);
}
```

**重要なパースオプション**:

| オプション | 効果 |
|-----------|------|
| `cellDates: true` | 日付セルをDateオブジェクトに変換 |
| `dense: true` | メモリ使用量削減 |
| `header: 1` | 配列形式で取得（オブジェクト汚染防止） |
| `defval: null` | 空セルをnullで埋める（undefined防止） |

**根拠**: [TheLinuxCode - NPM + SheetJS XLSX in 2026](https://thelinuxcode.com/npm-sheetjs-xlsx-in-2026-safe-installation-secure-parsing-and-real-world-nodejs-patterns/)

---

## 6. コマンド比較一覧

### npx ワンライナー

| コマンド | 用途 | 出力形式 |
|---------|------|---------|
| `npx convert-excel-to-json --sourceFile="data.xlsx"` | Excel→JSON変換 | JSON（全シート） |
| `npx i18n-json-to-xlsx-converter --convert 'data.xlsx'` | Excel↔JSON双方向 | JSON |
| `xlsx2csv sample.xlsx output.csv` | Excel→CSV変換 | CSV（要グローバルインストール） |

### プログラムでの使用

```javascript
// @e965/xlsx でJSON出力
const xlsx = require("@e965/xlsx");
const workbook = xlsx.readFile("sample.xlsx");
const sheet = workbook.Sheets["Sheet1"];
const json = xlsx.utils.sheet_to_json(sheet);
console.log(JSON.stringify(json, null, 2));

// CSV出力
const csv = xlsx.utils.sheet_to_csv(sheet);
console.log(csv);
```

---

## 7. 破壊的変更とマイグレーション

### 従来の `xlsx` から `@e965/xlsx` への移行

**変更なし**: APIは完全互換

```javascript
// 変更前
const xlsx = require("xlsx");

// 変更後（パッケージ名のみ変更）
const xlsx = require("@e965/xlsx");
```

**package.json**:

```diff
{
  "dependencies": {
-   "xlsx": "^0.18.5"
+   "@e965/xlsx": "0.20.3"
  }
}
```

**移行手順**:

```bash
# 1. 古いパッケージ削除
npm uninstall xlsx

# 2. 新パッケージインストール
npm install @e965/xlsx

# 3. lockfile 更新を確認
git diff package-lock.json

# 4. セキュリティ監査
npm audit --audit-level=high
```

**ロールバック不要**: APIが同じため、コード変更なしで移行可能

---

## 8. パフォーマンス最適化のヒント

| 最適化 | 方法 | 効果 |
|-------|------|------|
| **メモリ削減** | `dense: true` オプション使用 | 大きなファイルでメモリ使用量50%削減 |
| **ストリーミング** | `XLSX.stream.to_csv()` 使用 | 大容量ファイルのメモリ枯渇防止 |
| **必要なシートのみ読み込み** | 特定シート名を指定 | 処理時間短縮 |
| **範囲指定** | `range: "A1:C100"` で範囲限定 | 不要データの読み込み回避 |
| **Worker Thread** | 大容量ファイルはWorkerで並列処理 | CPU効率向上 |

**ストリーミング例**:

```javascript
const xlsx = require("@e965/xlsx");
const fs = require("fs");

// 大容量ファイルをストリーミングでCSV変換
const workbook = xlsx.readFile("large.xlsx", { dense: true });
const sheet = workbook.Sheets["Sheet1"];
const stream = xlsx.stream.to_csv(sheet);
stream.pipe(fs.createWriteStream("output.csv"));
```

---

## 9. 公式ドキュメントへのリンク

### SheetJS公式

| リソース | URL |
|---------|-----|
| **公式ドキュメント** | [SheetJS Community Edition](https://docs.sheetjs.com/) |
| **CLI使用ガイド** | [Sheets on the Command Line](https://docs.sheetjs.com/docs/demos/cli/) |
| **Node.jsインストール** | [NodeJS Installation Guide](https://docs.sheetjs.com/docs/getting-started/installation/nodejs/) |
| **公式CDN** | [SheetJS CDN](https://cdn.sheetjs.com/xlsx/) |

### npm パッケージ

| パッケージ | npm URL |
|-----------|---------|
| **convert-excel-to-json** | [npmjs.com/package/convert-excel-to-json](https://www.npmjs.com/package/convert-excel-to-json) |
| **xlsx** | [npmjs.com/package/xlsx](https://www.npmjs.com/package/xlsx) |
| **node-xlsx** | [npmjs.com/package/node-xlsx](https://www.npmjs.com/package/node-xlsx) |

### GitHub リポジトリ

| ツール | GitHub URL |
|-------|-----------|
| **xlsx2csv** | [github.com/papnkukn/xlsx2csv](https://github.com/papnkukn/xlsx2csv) |
| **excel-mcp-server** | [github.com/negokaz/excel-mcp-server](https://github.com/negokaz/excel-mcp-server) |

### 参考記事

| タイトル | URL |
|---------|-----|
| **NPM + SheetJS XLSX in 2026** | [TheLinuxCode](https://thelinuxcode.com/npm-sheetjs-xlsx-in-2026-safe-installation-secure-parsing-and-real-world-nodejs-patterns/) |

---

## 10. 追加の推奨事項

### ✅ 今すぐ実行すべき手順

| # | アクション | コマンド/手順 |
|---|-----------|-------------|
| 1 | **古い`xlsx`を削除** | `npm uninstall xlsx` |
| 2 | **安全なパッケージをインストール** | `npm install @e965/xlsx` |
| 3 | **バージョン固定** | package.jsonで`"@e965/xlsx": "0.20.3"`と明記 |
| 4 | **lockfileコミット** | `git add package-lock.json && git commit` |
| 5 | **セキュリティ監査** | `npm audit --audit-level=high` |
| 6 | **入力検証コード追加** | 上記のセーフティパースパターンを実装 |

### 🔄 今後のアップデート計画

| タイミング | アクション |
|-----------|-----------|
| **月次** | `npm audit`でセキュリティチェック |
| **四半期** | `@e965/xlsx`の新バージョン確認 |
| **年次** | パフォーマンステスト、大容量ファイル対応の見直し |

### ⚡ パフォーマンスチューニングの提案

| 状況 | 提案 |
|------|------|
| **10MB以上のファイル** | ストリーミング処理に切り替え |
| **複数ファイル処理** | Worker Threadで並列化 |
| **頻繁な読み込み** | キャッシュ機構の導入 |

---

## Sources

- [npm - convert-excel-to-json](https://www.npmjs.com/package/convert-excel-to-json)
- [npm - xlsx](https://www.npmjs.com/package/xlsx)
- [GitHub - papnkukn/xlsx2csv](https://github.com/papnkukn/xlsx2csv)
- [npm - node-xlsx](https://www.npmjs.com/package/node-xlsx)
- [TheLinuxCode - NPM + SheetJS XLSX in 2026](https://thelinuxcode.com/npm-sheetjs-xlsx-in-2026-safe-installation-secure-parsing-and-real-world-nodejs-patterns/)
- [SheetJS Community Edition Docs](https://docs.sheetjs.com/)
- [Sheets on the Command Line - SheetJS](https://docs.sheetjs.com/docs/demos/cli/)
- [NodeJS Installation Guide - SheetJS](https://docs.sheetjs.com/docs/getting-started/installation/nodejs/)
- [GitHub - negokaz/excel-mcp-server](https://github.com/negokaz/excel-mcp-server)
- [GitHub - haris-musa/excel-mcp-server](https://github.com/haris-musa/excel-mcp-server)
- [LobeHub - Excel MCP Server](https://lobehub.com/mcp/negokaz-excel-mcp-server)
- [Zapier - Microsoft Excel MCP Server](https://zapier.com/mcp/excel)
