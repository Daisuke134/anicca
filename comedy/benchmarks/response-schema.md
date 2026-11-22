# Comedy Agent Benchmark — JSONL schema v1

1行につき1モデルの1つのタスクの回答をJSONで保存する。

必須フィールド: `run_id` (同一実行で一意), `task_id`, `model`, `skill_version`, `skill_commit`, `response` (文字列、無言タスクのみ空文字を許容)。

推奨フィールド: `model_version`, `created_at` (ISO8601), `effort`, `temperature`, `modality` ("text" / "voice"), `source_sha`, `provider_receipt`, `latency_ms`, `evaluator_notes`。

```json
{"run_id":"2026-11-22-grok-01","task_id":"stage-open-01","model":"example-model","model_version":"explicit-model-id","skill_version":"0.1.0","skill_commit":"actual-git-sha","response":"はい、救急指令センターです。火事ですか、救急ですか？","modality":"text"}
```

`response`は**モデルが実際に出力した全文**。ダイスの台詞や期待解を混ぜない。正解欄を見てから書き換えない。提出していないタスクは未実施として記録。

自動採点は**台本遵守ハードゲート**だけ。面白さの生成能力は別途盲検の人間評価で測る。`status`は `NOT_RUN` / `PASS` / `FAIL` / `NOT_MEASURED` などで表す。外部のXや大喜利サイトの評価を仮の数字で作らない。
