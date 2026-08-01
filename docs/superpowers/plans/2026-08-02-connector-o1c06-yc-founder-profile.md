# O1C-06 YC founder profile 完了計画

**Goal:** profile.json/application-kitの事実だけでYC founder bioを補完し、Profile completeをfresh readbackする。

## Contract

- DOB、連絡先、学歴はprofile.jsonとapplication-kit digestへ束縛する。
- roleはFounder、未法人で期待持分100%、technical founder=true、currently in school=trueを事実どおり保存する。
- YC採択時の1年間専念=trueは、Fall 2026実提出とSF参加の明示目標から導出したintentとして別sourceを持つ。
- 学歴はNAIST MSc Information Science (2024-04〜2027-03)とKeio BA Politics (2020-04〜2024-03)のexact 2行。旧2026年終了と重複4行を残さない。
- `Save & return to application`は一度だけ。`Submit application`は押さない。

## Steps

1. canonical fields、2学歴、source binding、旧誤記拒否をRED testで固定する。
2. founder profile patch builderを実装する。
3. 実bioへ補完・重複整理・保存し、application pageでProfile completeをreadbackする。
4. 全回帰、evidence、spec、残数、commit/pushを完了する。
