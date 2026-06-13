# 02 — Compute (food)
Goal: ClawRouter on :8402, model=auto → free NVIDIA when broke, frontier when funded; x402 USDC from the agent's own wallet (BLOCKRUN_WALLET_KEY). Started by core; health-checked.
Files: runtime/compute-proxy/start.mjs (launch clawrouter, ensure :8402/health), config.
Acceptance: a chat call via :8402 succeeds on deepseek at $0; after funding USDC, picks a paid model. `clawrouter status` shows the agent wallet.
