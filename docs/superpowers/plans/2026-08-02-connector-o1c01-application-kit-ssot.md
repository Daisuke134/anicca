# O1C-01 application-kit SSOT 接続計画

**Goal:** funder applicationの会社facts・定型回答・添付素材を`application-kit`だけから解決し、consumer内の重複hardcodeやfallbackを禁止する。

## Contract

- KIT.md、MANIFEST.md、日英20回答を完全snapshotし、一つのdigestへ束縛する。
- form fieldは`kit:answer/<id>.<lang>`、素材はallowlistされた`kit:asset/<name>`だけを参照する。
- dashboard tokenは同runのlive snapshotで全解決し、missing keyや未解決tokenを拒否する。
- missing file、path traversal、unknown source、consumer literal fallbackを拒否する。
- outputへsource refとkit digestを付け、どの正本版から生成したか追跡可能にする。

## Steps

1. 20回答完全性、live token、素材allowlist、fallback禁止をRED testで固定する。
2. application-kit providerとfunder field resolverを実装する。
3. 実kit foundation gate、20回答snapshot、live dashboard解決readbackを行う。
4. 全回帰、evidence、spec、残数、commit/pushを完了する。
