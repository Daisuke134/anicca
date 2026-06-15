# 01 — Core / Body
Goal: one ReAct loop that drives a body. Body is swappable: **automaton** (spawn/survival/memory; runs on ClawRouter; PROVEN on Akash) OR **Franklin** (wallet-agent). Default body = automaton (has self-replication + survival; Conway optional).
Files: core/identity.mjs (1 key → Base+cosmos+AgentMail), core/loop.mjs (perceive→think via :8402→act(skills)→pay food/shelter→report), core/config.mjs (model=auto, OPENAI_BASE_URL=:8402).
Acceptance: `node core/loop.mjs` runs ≥1 turn using ClawRouter (deepseek free), logs perceive/think/act, no human.
