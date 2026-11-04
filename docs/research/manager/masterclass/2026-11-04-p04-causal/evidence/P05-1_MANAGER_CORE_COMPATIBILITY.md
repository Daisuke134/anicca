# Manager Core 既存単体テスト｜Python 3.12 / 3.14 の互換性

**対象**：`products/manager/tests/test_collaboration_authority.py`における、権限・効果・人間便益を受け取らない`AdvisoryResult`のテスト。

## 発見（2026-11-04）

4つの`subTest`で`dataclasses.replace(safe, proof_level=...)`等の操作を行い、`init=False`の非公開状態を改変できないことを確かめていた。Python3.12では`ValueError`、Python3.14では`TypeError`で拒否される。

元のテストは`assertRaises(ValueError)`だけを受け入れていたため、**3.14の4 subtestsが落ちた**。しかし、どちらのランタイムでも権限昇格や効果証拠の書き換えが成功したわけではない。

## 修復

```python
with self.subTest(name=name), self.assertRaises((ValueError, TypeError)):
    replace(safe, **{name: value})
```

実装コード`manager_core/authority.py`、`models/intervention.py`、`audit.py`等は変更していない。

| Python | 変更後の対象4ファイル | 状態 |
|---|---|---|
| 3.12 | 44 passed, 15 subtests passed | PASS |
| 3.14 | 44 passed, 15 subtests passed | PASS |

4ファイルは`test_evaluation.py`, `test_advice_protocol.py`, `test_collaboration_authority.py`, `test_governance.py`。他の数十個の`products/manager/tests`をすべて実行して製品全体の正常性を保証したわけではない。

**境界**：この修正はPython標準ライブラリでの例外型の扱いを両バージョンへ広げるだけ。実際の権限発行・実外部効果・ユーザー同意とは関係しない。

## 証拠

- `MANAGER_CORE_python312_AFTER_FIX.txt`
- `MANAGER_CORE_python314_AFTER_FIX.txt`
- 変更ファイル `products/manager/tests/test_collaboration_authority.py`。

一次情報：Python標準ライブラリ`dataclasses.replace`の動作を両ランタイムで再現した実行ログ。
