# O1C-04 YC description 修正計画

**Goal:** Fall 2026 draftのdescriptionをapplication-kit正本へ同期し、50文字未満を保存後readbackで証明する。

## Contract

- descriptionは`application-kit://KIT.md#english-one-liner`からだけ取得する。
- Unicode文字数は1〜49。前後空白、改行、placeholder、別sourceを拒否する。
- draft値が違う場合だけ一度保存し、Submit applicationは押さない。
- 保存後のexact value、文字数、source digest、draft UUIDをprivacy-safe evidenceへ残す。

## Steps

1. 制約、source binding、no-op、over-limitをRED testで固定する。
2. description patch builderを実装する。
3. 現行`:9222`でFall 2026 draftへ一度だけ保存し、fresh pageでreadbackする。
4. 全回帰、evidence、spec、残数、commit/pushを完了する。
