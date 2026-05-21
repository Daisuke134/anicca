# Railway PostgreSQL Security Research

## 調査日時
2026年1月29日 10:17:49

## 調査対象
Railway.app上のPostgreSQLデータベースへのブルートフォース攻撃を防ぐセキュリティベストプラクティス

## 問題の背景
本番環境のログに以下のようなエラーが繰り返し記録されている：
```
FATAL: password authentication failed for user "postgres"
```

これはRailwayの公開プロキシURL（`proxy.rlwy.net`）に対する外部からのブルートフォース攻撃と思われる。

---

## 調査結果サマリー

### Railway固有のセキュリティ機能

| 機能 | 詳細 | セキュリティレベル |
|------|------|------------------|
| **プライベートネットワーキング** | デフォルトで全プロジェクトに有効。`railway.internal` ドメインで内部通信 | ⭐⭐⭐⭐⭐ |
| **SSL暗号化** | 公開・プライベート接続の両方で強制有効 | ⭐⭐⭐⭐ |
| **TCPプロキシ削除** | 公開プロキシを完全に無効化可能（内部接続のみ許可） | ⭐⭐⭐⭐⭐ |
| **IPホワイトリスト** | ❌ **サポートされていない** | - |

### 現在のバージョンと推奨バージョン

| 項目 | 現在 | 推奨 | 理由 |
|------|------|------|------|
| **アプリ→DB接続** | `DATABASE_URL` (公開プロキシ経由?) | `DATABASE_PRIVATE_URL` | プライベートネットワークで内部通信（高速・安全・無料） |
| **TCPプロキシ** | 有効 | **無効化** | 外部アクセスが不要ならブルートフォース攻撃を完全にブロック |
| **auth_delay拡張** | 未確認 | 有効化 | ブルートフォース攻撃を遅延させる（TCPプロキシ維持時） |

---

## 詳細な調査結果

### 1. Railwayプライベートネットワーキング

#### 仕組み
- 全プロジェクトでデフォルト有効
- 各サービスは `servicename.railway.internal` のDNS名を取得
- 2025年10月16日以降の環境：IPv4 + IPv6の両方に対応
- レガシー環境：IPv6のみ

#### 内部URL使用方法
```
# 例：APIサービス（ポート3000）への接続
http://api.railway.internal:3000/endpoint

# 参照変数を使った動的設定
${{servicename.RAILWAY_PRIVATE_DOMAIN}}:${{servicename.PORT}}
```

#### セキュリティ上の利点
- **インターネットから隔離**：プライベートネットワークは同一プロジェクト/環境内でのみ通信可能
- **高速通信**：内部ネットワークのため遅延が少ない
- **エグレス料金ゼロ**：サービス間通信はネットワーク使用料に含まれない
- **SSL不要**（内部通信）：既にセキュアなため平文HTTP可能

#### 制限事項
- **プロジェクト/環境間の通信は不可**：別プロジェクトのサービスとは通信できない
- **クライアントサイドからアクセス不可**：ブラウザからは接続できない
- **外部ホスティング（Vercel等）からアクセス不可**
- **ビルドフェーズでは利用不可**

#### ベストプラクティス
- アプリケーションを `::`（全インターフェース）でリッスンさせてIPv4/IPv6両対応
- 内部通信には `http`（HTTPS不要）
- ライブラリ固有の設定が必要な場合あり（例：ioredisは`family=0`）

**出典：** [Railway Private Networking Docs](https://docs.railway.com/guides/private-networking)

---

### 2. DATABASE_URL vs DATABASE_PRIVATE_URL vs DATABASE_PUBLIC_URL

| 環境変数 | 用途 | 経路 | セキュリティ | エグレス料金 |
|---------|------|------|------------|-------------|
| **DATABASE_PRIVATE_URL** | **Railway内部接続（推奨）** | `railway.internal` | ⭐⭐⭐⭐⭐ | ✅ 無料 |
| **DATABASE_URL** | デフォルト（動作は環境依存） | 不明（要確認） | ⭐⭐⭐ | ⚠️ 要確認 |
| **DATABASE_PUBLIC_URL** | 外部接続・ローカル開発 | `proxy.rlwy.net` | ⭐⭐ | ❌ 課金対象 |

#### 使い分け

| 接続元 | 使用する環境変数 |
|--------|----------------|
| Railway内のサービス（本番/Staging） | **DATABASE_PRIVATE_URL** |
| ローカル開発環境 | DATABASE_PUBLIC_URL |
| 外部サービス（管理ツール等） | DATABASE_PUBLIC_URL（必要な場合のみ） |

**重要：** アプリケーションコードで `DATABASE_PRIVATE_URL` を優先的に使用し、存在しない場合のみ `DATABASE_URL` にフォールバックする実装を推奨。

**出典：** [Railway Public Networking Docs](https://docs.railway.com/reference/public-networking), [Railway Best Practices](https://docs.railway.com/overview/best-practices)

---

### 3. TCPプロキシの削除（最強のセキュリティ対策）

#### 現状の問題
- Railway PostgreSQLはデフォルトでTCPプロキシ（`proxy.rlwy.net`）を公開
- インターネット全体から接続可能
- ブルートフォース攻撃の標的になる

#### 解決策：TCPプロキシを完全無効化
**Railway管理画面の操作：**
1. PostgreSQLサービスの設定を開く
2. Networking → Public Networking セクション
3. TCP Proxyを **Remove / Disable**

**効果：**
- ✅ ブルートフォース攻撃を**完全にブロック**
- ✅ Railway内部ネットワークからのみアクセス可能
- ✅ エグレス料金の削減
- ❌ 外部ツール（TablePlus、pgAdmin等）から接続不可

#### 注意事項
- TCPプロキシを削除すると、内部ネットワークへのトンネリング方法は**存在しない**
- 外部からのDB接続が必要な場合（管理ツール、マイグレーション実行等）はプロキシを維持
- プロキシを維持する場合は後述の `auth_delay` で緩和策を実施

**出典：** [Railway PostgreSQL Docs](https://docs.railway.com/guides/postgresql), [Railway Private Networking Docs](https://docs.railway.com/guides/private-networking)

---

### 4. PostgreSQL auth_delay拡張（ブルートフォース緩和）

#### 仕組み
`auth_delay` 拡張は、認証失敗時にレスポンスを意図的に遅延させることで、ブルートフォース攻撃を困難にする。

#### 設定方法
PostgreSQLの設定ファイル（`postgresql.conf`）に追加：
```conf
shared_preload_libraries = 'auth_delay'
auth_delay.milliseconds = 5000  # 5秒の遅延
```

再起動後、拡張を有効化：
```sql
CREATE EXTENSION IF NOT EXISTS auth_delay;
```

#### 効果
- デフォルトのPostgreSQLには**ブルートフォース保護が一切ない**
- 5秒の遅延により、攻撃者は1時間あたり720回しか試行できない
- 正規ユーザーへの影響：初回接続時にパスワードを間違えた場合のみ5秒待つ

#### Railway での実装可能性
Railwayの提供するPostgreSQLテンプレートは [postgres-ssl](https://github.com/railwayapp-templates/postgres-ssl) ベース。
- ⚠️ カスタム `postgresql.conf` の設定が可能か要確認
- ⚠️ 拡張のインストール権限があるか要確認

**出典：** [DigitalOcean PostgreSQL Security Tutorial](https://www.digitalocean.com/community/tutorials/how-to-secure-postgresql-against-automated-attacks), [EnterpriseDB Security Guide](https://www.enterprisedb.com/blog/how-to-secure-postgresql-security-hardening-best-practices-checklist-tips-encryption-authentication-vulnerabilities)

---

### 5. PostgreSQL SCRAM-SHA-256（パスワードハッシュ強化）

#### 設定
`postgresql.conf`:
```conf
scram_sha_256_iterations = 8192  # デフォルト4096
```

#### 効果
- パスワードハッシュの計算コストを増やし、オフライン攻撃を遅延
- 値を大きくすると認証が遅くなるトレードオフあり
- 8192程度が推奨（デフォルト4096の2倍）

**出典：** [PostgreSQL Documentation - Connections and Authentication](https://www.postgresql.org/docs/current/runtime-config-connection.html)

---

### 6. pg_hba.conf（ホストベース認証）

#### Railwayでの制限
**Railwayは現在、PostgreSQLインスタンスへのインバウンド接続に対するIPベースのアクセス制御をサポートしていない。**

一般的なPostgreSQL環境では以下が可能：
```conf
# pg_hba.conf
host    all    all    trusted_ip/32    scram-sha-256
host    all    all    0.0.0.0/0        reject  # 他全拒否
```

しかし、RailwayのマネージドPostgreSQLではこれらの設定は**変更不可**。

**出典：** [Railway Help Station - PostgreSQL IP Restrictions](https://station.railway.com/questions/postgre-sql-configuration-ip-restriction-b43d9aad)

---

### 7. 監視とログ分析

#### 現在の問題
```
FATAL: password authentication failed for user "postgres"
```
が大量に記録されている。

#### 推奨される監視
- **ログボリューム監視**：フルパワーのブルートフォース攻撃は1時間あたり数GB以上のログを生成
- **FATAL エラーのアラート**：認証失敗が閾値（例：10回/分）を超えたら通知
- **接続元IPの記録**：攻撃元の地理的分布を確認

#### Railway での実装
- Railway Logs ダッシュボードで確認
- 外部ログ集約サービス（Datadog、Logflare等）にエクスポート可能
- Mixpanelやカスタムスクリプトで異常検知

**出典：** [CYBERTEC PostgreSQL Security](https://www.cybertec-postgresql.com/en/secure-postgresql-a-reminder-on-various-attack-surfaces/)

---

## 破壊的変更とリスク

### TCPプロキシ削除のリスク

| 影響を受けるもの | リスクレベル | 緩和策 |
|---------------|------------|--------|
| **外部DBツール（TablePlus等）** | ⚠️ 高 | Railway CLI経由でローカルフォワーディング、またはプロキシ維持 |
| **ローカル開発環境** | ⚠️ 高 | `railway link` + `railway run` でプロキシ経由接続 |
| **CI/CDパイプライン** | ⚠️ 中 | GitHub Actions等は Railway 内で実行可能（問題なし） |
| **マイグレーションスクリプト** | ⚠️ 中 | `railway run npx prisma migrate deploy` で内部接続可能 |

### DATABASE_PRIVATE_URL への切り替えリスク

| リスク | 確率 | 緩和策 |
|--------|------|--------|
| 既存コードが `DATABASE_URL` 依存 | 低 | 環境変数のフォールバック実装 |
| PrismaクライアントのURL検出失敗 | 極低 | `.env` と環境変数で両方定義 |
| 接続プール設定の不一致 | 低 | 接続パラメータを明示的に設定 |

---

## 推奨される実装手順

### Phase 1: 内部接続の切り替え（破壊的変更なし）

| # | タスク | 担当 | リスク |
|---|--------|------|--------|
| 1 | `DATABASE_PRIVATE_URL` 環境変数が存在するか確認 | Ops | 低 |
| 2 | アプリケーションコードで `DATABASE_PRIVATE_URL` を優先使用する実装 | Dev | 低 |
| 3 | Staging環境でテスト | QA | 低 |
| 4 | Production環境にデプロイ | Ops | 低 |
| 5 | ログでブルートフォース攻撃が継続していることを確認 | Ops | - |

**実装例（Node.js）：**
```javascript
const databaseUrl = process.env.DATABASE_PRIVATE_URL || process.env.DATABASE_URL;

if (!databaseUrl) {
  throw new Error('DATABASE_PRIVATE_URL or DATABASE_URL must be set');
}

// Prisma等のORMに渡す
```

**効果：**
- ✅ 内部接続が高速化・無料化
- ✅ エグレス料金の削減
- ⚠️ TCPプロキシはまだ公開されているため、ブルートフォース攻撃は継続

---

### Phase 2: TCPプロキシの削除（最強のセキュリティ対策）

#### 前提条件
- [ ] Phase 1完了（内部接続が `DATABASE_PRIVATE_URL` 使用）
- [ ] 外部からのDB接続が不要であることを確認
- [ ] ローカル開発環境が Railway CLI 経由で接続可能であることを確認

#### 実行手順

| # | 操作 | 詳細 | ロールバック |
|---|------|------|-------------|
| 1 | **Staging環境でテスト** | Staging DBのTCPプロキシを削除 → アプリ動作確認 | プロキシ再有効化 |
| 2 | **Production DBのバックアップ** | Railwayダッシュボードで手動バックアップ | - |
| 3 | **TCPプロキシを削除** | PostgreSQL設定 → Networking → TCP Proxy → Remove | プロキシ再有効化 |
| 4 | **アプリ動作確認** | 本番アプリが正常に接続できるか確認 | 即座にプロキシ再有効化 |
| 5 | **ログ監視（24時間）** | FATALエラーが消失することを確認 | - |

#### ロールバック手順
1. Railway管理画面 → PostgreSQL設定 → Networking
2. TCP Proxyを再有効化
3. 新しい公開URLが生成される（URLは変わる可能性あり）
4. 外部ツールで新URLを使用

**効果：**
- ✅ ブルートフォース攻撃を**完全にブロック**
- ✅ ログのノイズが消える
- ✅ セキュリティ最大化

---

### Phase 3（オプション）: auth_delay の有効化（プロキシ維持時のみ）

**このPhaseは、外部接続が必要でTCPプロキシを削除できない場合のみ実施。**

#### 前提条件
- [ ] TCPプロキシを維持する必要がある（外部ツール、CI/CD等）
- [ ] Railway PostgreSQLでカスタム設定が可能であることを確認

#### 実装方法（要検証）

Railwayの [postgres-ssl テンプレート](https://github.com/railwayapp-templates/postgres-ssl) をフォークし、カスタム `postgresql.conf` を追加：

```dockerfile
# Dockerfile
FROM postgres:16

COPY postgresql.conf /etc/postgresql/postgresql.conf
CMD ["postgres", "-c", "config_file=/etc/postgresql/postgresql.conf"]
```

```conf
# postgresql.conf
shared_preload_libraries = 'auth_delay'
auth_delay.milliseconds = 5000
```

Railway設定でカスタムDockerイメージを使用。

⚠️ **注意：** Railwayのマネージド PostgreSQL では設定変更が制限されている可能性が高い。実現可能性は要確認。

**効果：**
- ✅ ブルートフォース攻撃を遅延（完全ブロックではない）
- ⚠️ 攻撃は継続するがログ量が減る
- ⚠️ 正規ユーザーもパスワード間違い時に5秒待つ

---

## セキュリティ考慮事項

### 公開プロキシを維持する場合の残存リスク

| リスク | 深刻度 | 緩和策 |
|--------|--------|--------|
| **ブルートフォース攻撃** | 中 | auth_delay、強力なパスワード、監視 |
| **DDoS攻撃** | 低 | Railwayのインフラレベルで保護 |
| **ログの肥大化** | 中 | ログローテーション、外部集約 |
| **パスワード漏洩時の即座の侵害** | 高 | パスワードローテーション、最小権限の原則 |

### TCPプロキシ削除後の残存リスク

| リスク | 深刻度 | 緩和策 |
|--------|--------|--------|
| **内部ネットワーク侵害時のDB露出** | 低 | Railway内の他サービスのセキュリティ強化 |
| **設定ミスによる意図しない公開** | 極低 | 定期的なセキュリティ監査 |

---

## パフォーマンス最適化のヒント

### プライベートネットワーク使用時の利点

| 指標 | 公開プロキシ | プライベートネットワーク |
|------|------------|---------------------|
| **レイテンシ** | 10-50ms | 1-5ms |
| **スループット** | 中 | 高 |
| **エグレス料金** | $0.10/GB | **$0.00/GB** |

### 接続プール設定

```javascript
// Prismaの推奨設定
datasource db {
  provider = "postgresql"
  url      = env("DATABASE_PRIVATE_URL")
}

// 接続プール（サーバーレス環境）
const prisma = new PrismaClient({
  datasources: {
    db: {
      url: process.env.DATABASE_PRIVATE_URL,
    },
  },
  connection_limit: 10,  // Railway内部接続は高速なため小さめでOK
});
```

**出典：** [Railway Best Practices](https://docs.railway.com/overview/best-practices)

---

## 今後のアップデート計画

### 短期（1-2週間）
- [ ] Phase 1実装（DATABASE_PRIVATE_URL切り替え）
- [ ] Staging環境でTCPプロキシ削除テスト
- [ ] Production環境でTCPプロキシ削除（外部接続不要を確認後）

### 中期（1ヶ月）
- [ ] ログ監視ダッシュボードの構築（認証失敗の可視化）
- [ ] 自動アラートの設定（異常な認証失敗パターン検出）

### 長期（3ヶ月）
- [ ] Railway PostgreSQLのカスタム設定可能性を調査（auth_delay等）
- [ ] データベース監査ログの外部エクスポート（Datadog等）
- [ ] セキュリティ監査の定期実施（四半期ごと）

---

## 参考リンク

### Railway公式ドキュメント
- [Private Networking](https://docs.railway.com/guides/private-networking)
- [PostgreSQL Guide](https://docs.railway.com/guides/postgresql)
- [Best Practices](https://docs.railway.com/overview/best-practices)
- [Public Networking](https://docs.railway.com/reference/public-networking)

### PostgreSQLセキュリティ
- [DigitalOcean - How To Secure PostgreSQL Against Automated Attacks](https://www.digitalocean.com/community/tutorials/how-to-secure-postgresql-against-automated-attacks)
- [EnterpriseDB - PostgreSQL Security Hardening Best Practices](https://www.enterprisedb.com/blog/how-to-secure-postgresql-security-hardening-best-practices-checklist-tips-encryption-authentication-vulnerabilities)
- [CYBERTEC - PostgreSQL Attack Surfaces](https://www.cybertec-postgresql.com/en/secure-postgresql-a-reminder-on-various-attack-surfaces/)
- [PostgreSQL Documentation - Connections and Authentication](https://www.postgresql.org/docs/current/runtime-config-connection.html)

### Railway Community
- [Railway Help Station - PostgreSQL IP Restrictions](https://station.railway.com/questions/postgre-sql-configuration-ip-restriction-b43d9aad)
- [Railway Help Station - DATABASE_URL vs DATABASE_PUBLIC_URL](https://station.railway.com/questions/database-url-vs-database-public-url-cf8e4425)

---

## 最終更新
2026年1月29日 10:17:49
