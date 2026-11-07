# 【新しい実験による受入更新】

**この文書は最初の公開GETだけを実施した時点の履歴。現在は、実モデルを使ったS1比較をGitHub Actions run #42393800213で実施、同サイトSHA三度一致、時間と公式課金対象時間0msを受入済み。**Qwen REVIEW_ONLY / 従来 NO_ACTION で不一致、モデル昇格なし。MG-01の限定技術S1を完了扱いとし、唯一の現在カーソルはMG-02。詳細は [最新のS1研究プロトコル](MG01_S1_QWEN_REAL_PUBLIC_HOST_PROTOCOL_20261107_JA.md)。以下はhistorical readback情報。

---

# Manager MG-01｜公式公開ホストの読み取り専用Shadow 実測（2026-11-07）

**唯一の現在の実装カーソル：MG-01（G3 / P00-3 / P05-5 S1 / P06-1）。** 正式な順番付きTODOと完了条件は [統合SSOT](../../../superpowers/specs/2026-09-25-life-manager-unified-ssot.md) のMANAGER MG表のみ。ここでは観測事実だけを記録し、第二のTODOは作らない。

## 実環境のreadback（実行済み）

- 対象：既存の会社公開サイト https://daisuke134.github.io/life-manager/manager-support/ 。**認証・個人情報・第三者の端末アクセスなしの公開ページ**。新しいManagerアプリ画面や利用登録を要求しない。
- 既存manager_core.owned_catalog_planner._read_served_bundle、products/manager/scripts/phase06_kernel_release.pyの固定公開GET、既存digital_environment.verify_readbackを再利用。User-supplied URLを受け取らず、リダイレクト拒否・サイズ上限・Manifest整合・ページSHA検証を維持。
- 観測時刻：2026-11-07T15:51:57.600275+00:00（原資料の時刻。JST 11/8 00:51）。
- 現在の公開source commit：f8e11d27b9f98b511d6fdc55e2781cacbe26f8a5。
- 公開Manifest SHA256：bd670bee1cdb6dda2cd90f35352ba1b820eb181650521759e578fa4b8ac83dff。
- 公開Manifest＋6ページ：HTTP GET・正しいSHA照合。technical_proof=P2_ARTIFACT_ONLY、beneficiary_outcome=NOT_MEASURED、causal_effect_verified=false。
- 同じManifestSHAのbaseline=NO_ACTION と、既存のカタログ/アクセシビリティルール候補=NO_ACTIONを評価。**実際の学習済み行動モデル推論はこのWeb対象に行っていない**（G2の禁煙研究アウトカムHeadはこのサイト向けの判断モデルではないため）。
- 実行world_action=NO_ACTION、external_writes=0、notifications_sent=0、personal_data_accessed=false、requires_ui_or_recurring_prompt=false。
- 機械可読な公式スナップショット・比較レシート： [MANAGER_G3_PUBLIC_HOST_SHADOW_20261107.json](MANAGER_G3_PUBLIC_HOST_SHADOW_20261107.json)。
- 実行コード：products/manager/manager_core/zero_ui_host_shadow_v1.py。TEST-only injectionは「実サイトから来た」と偽装できないよう、製品実装は固定の公開GET関数だけを使用。
- 主なテスト：製品管理のPhase6サイト検証、既存Shadow/Authと新G3を合わせた65ソフトテスト成功。既存sqlite.Connectionの解放時ResourceWarningは発生し、テストexit0と区別して記録。テスト数から人間への便益を推定しない。

## MG-01の未受入境界

公開サイトが正常に配信されていることだけでは、P05-5 S1に求める実業務のモデル対incumbentを満たさない。**本物のホスト業務・正当な操作/観測権限・固定入力/予算/時刻、実際のincumbent意思決定、別モデル候補の同条件予測、遅延・費用の独立Receiptが不足**している。したがってMG-01=進行中を維持し、勝手にMG-02、G4、S2へ進まない。

第三者に知られない個人プロファイリングや無同意の行動介入は実施しない。Zero-UIは追加Manager画面・毎回の操作不要というUX方針であり、適切な元サービスの許諾/開示/撤回を省略することではない。Apple公式のApp Review Guidelines 5.1.1(ii), 5.1.2(i,iii)を尊重する：https://developer.apple.com/app-store/review/guidelines/ 。

**既存の成功基準を変更せず、次の実装も同じMG-01だけを扱う。** モデル候補のない場合はNO_ACTIONが正しい受入であって、無理に変更や通知を作らない。
