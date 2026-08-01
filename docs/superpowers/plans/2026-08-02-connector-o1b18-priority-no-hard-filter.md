# O1B-18 category priority / no hard filter 実装計画

**Goal:** AI、crypto、英語等の好みを順位にだけ反映し、東京・対面・期間内候補をcategoryで一件も落とせないrank contractを実装する。

## Contract

- inventory candidateとassessmentはevent_refで完全な1:1対応を要求する。
- scoreは0〜100で、0も有効候補として保持する。
- signal/reasonは順位説明用でありeligible/excluded/filter fieldを持てない。
- output countとevent_ref setはinputと完全一致する。
- score同点はevent_refで決定的に並べる。

## Steps

1. preferred/non-preferred/unknownを全保持するRED testを書く。
2. exact-schema assessment validatorとlossless rankerを実装する。
3. mixed-category inventoryでinput/output cardinalityとset一致を実測する。
4. 全回帰、evidence、spec、残数、commit/pushを完了する。
