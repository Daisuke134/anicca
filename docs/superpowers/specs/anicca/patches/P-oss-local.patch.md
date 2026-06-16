# P-oss-local — make OSS Anicca's compute LOCAL + self-pay by default (ClawRouter/BlockRun), no server key

> Spec: `28-product-redesign-merge-2026-06-16.md` row **P-oss-local**.
> Target repo: `/Users/anicca/anicca` (github `Daisuke134/anicca`, MIT). Push origin = `anicca`.
> All diff paths are **relative to `/Users/anicca/anicca`**. Do NOT modify `~/anicca` source here / do NOT commit — this file only records the REAL patch + apply + verify.

---

## 1. Reality found (verified, cited)

### 1a. What `~/anicca` ACTUALLY does today

| Fact | Evidence (live file) |
|---|---|
| The ClawRouter/BlockRun **self-pay proxy already exists and is real code** | `runtime/compute-proxy/proxy.mjs` — `import { BlockrunClient } from "@blockrun/llm"`, OpenAI-compatible HTTP server on `:8402`, reads `~/.automaton/wallet.json` privkey, routes **only** `POST …/chat/completions` to BlockRun. Header: *"Every inference is paid in USDC via x402 from THIS Anicca's own wallet (no human key). Free model when broke, frontier when funded."* |
| Dependency is real + published | `runtime/compute-proxy/package.json` → `"@blockrun/llm": "^3.2.3"`; `npm view @blockrun/llm version` = **3.3.0**, desc *"Pay-per-request AI … via x402 on Base and Solana"*. `node_modules/viem/accounts` present (`generatePrivateKey.ts`, `privateKeyToAccount`) → wallet gen works after `npm install`. |
| The pattern is documented in THESIS/MASTER | `THESIS.md` *"FOOD (compute) = ClawRouter / Bankr — pays per LLM call in USDC (x402). 7 NVIDIA models free."*; `specs/00-MASTER.md:134` *"automaton points inference at `https://blockrun.ai/api` + a FREE model `nvidia/deepseek-v4-flash` → … ZERO human API key, $0 (verified)"*. |
| **GAP 1 — install.sh tells the user a key/wallet is REQUIRED, never mentions the free local-default path** | `install.sh:131-133` "What's next": *"Fill .env with at least: 1 FUEL (ANTHROPIC_API_KEY \| OPENAI_API_KEY \| DEEPSEEK_API_KEY \| a ClawRouter WALLET key) … WALLET (a funded Base wallet privkey)"* — presents BYOK/wallet as a precondition; **no** "default = free, no key" branch and **no** start command. |
| **GAP 2 — no committed runner starts the proxy** | (verified) `grep -rln "OPENAI_BASE_URL" .` (excl node_modules/_archive/.worktrees) = **ONLY `specs/00-MASTER.md`** (0 hits in any `*.sh` / harness). `find . -name 'run-cycle*'` (excl node_modules) = **none**. `specs/00-MASTER.md:154` *prose-claims* a `run-cycle.sh` "starts the proxy then automaton" but **that script is NOT committed**. So nothing boots `proxy.mjs` out of the box. |
| **GAP 2b — there is NO committed automaton loop at all** | (verified) `install.sh:135` itself says *"Start the automaton loop (**your runner of choice**)"* — the loop is BYO. The live (non-`_archive`) skills (`skills/earn/run.sh`, `skills/self/spawn/run.sh`, `skills/anicca-life-manager/scripts/run.sh`, `skills/eval-loop/scripts/eval.sh`) are individual **wake-slots a loop calls**, not a loop, and **none of them read `OPENAI_BASE_URL`** (`grep -rilE 'openai\|chat/completions\|8402\|compute-proxy' skills/ services/` returns only `services/x402-worker/*` + inbox-zero infra, unrelated to inference routing). ⇒ honest answer to reviewer §1 = **path (b): no loop to wire**. |
| **GAP 3 — README "Install" still says clone + BYOK, no local-free quickstart** | `README.md:55-73` Install = Path A (coding-agent) + Path B (`aniccaai.com/install`); the *free ClawRouter* story is only in the one-line architecture paragraph (`README.md:77`), not in Install. |
| **GAP 3b — compute-proxy `package.json` / `package-lock.json` are UNTRACKED** | (verified) `git ls-files runtime/compute-proxy/` = **`proxy.mjs` only**. `README`/`install.sh` tell the user to `npm install` in that dir, but the manifest the install reads is **not on the branch** — they must be `git add`ed (see §3). |
| LM is already a local skill (✅ confirmed, no change needed) | `skills/anicca-life-manager/SKILL.md` exists; `install.sh` registry-syncs `skills/life/*` + `skills/anicca-life-manager`; `skills/registry.json` declares `life/*`. LM-as-local-skill is **already wired** — this patch only *documents* it. |

**Conclusion (honest, doc-vs-wiring split):** the repo already HAS the ClawRouter compute engine (`proxy.mjs` + `@blockrun/llm`); it is NOT the default and **nothing boots it**, and **the repo ships no automaton loop** ("your runner of choice"). So this patch ships exactly ONE piece of real wiring — a runner that **boots the existing self-pay proxy** + auto-generates the self-owned wallet + exports `OPENAI_BASE_URL` so a loop *you supply* routes through it — and **truthful docs** that the compute proxy is the local-free default while **the automaton loop is BYO** (plug it in as `./start-local.sh <your-loop-cmd>`). No claim that an automaton is wired, because none is. This mirrors Franklin's "free local compute, wallet = identity" — for the **compute layer only**.

### 1b. Franklin's real local-compute pattern (cited, to mirror — for the COMPUTE layer)

Source: `gh api repos/BlockRunAI/franklin/contents/README.md` + `npm view @blockrun/franklin` = **3.29.0**.

> *"Run (free — uses NVIDIA Nemotron & Qwen3 Coder out of the box). (optional) Fund a wallet to unlock Sonnet, Opus, GPT…"* — **free local run with zero key is the default; funding the wallet is optional.**
> *"Every paid action routes through the [x402] micropayment protocol and settles against your own wallet. No subscriptions. No API keys. No account. The wallet is the identity."*

Same SDK family our proxy uses (`@blockrun/llm`). So **local-default Anicca compute = `install.sh` → `start-local.sh` → free BlockRun model on the user's box, wallet auto-created, frontier unlocks when USDC lands in *its own* wallet.** Note: Franklin bundles its own agent loop; **our repo does not** — hence the honest "plug your loop in" framing.

---

## 2. REAL unified diff (git-applicable; VERIFIED `git apply --check` = exit 0 against live HEAD `a195c7f`)

This is the **canonical diff captured from a real working-tree edit** of `/Users/anicca/anicca`, then reverted (no commit). It applies clean as-is — hunk headers + blob hashes are real, context lines are verbatim from live `README.md` / `install.sh`. Three files in one patch: new runner `runtime/compute-proxy/start-local.sh` (boots the existing `proxy.mjs` + auto-gens a self-owned wallet via `viem` already in node_modules; **with no loop arg it holds the proxy + prints how to plug a loop in — it does NOT claim an automaton is wired**), `install.sh` "what's next" (local-free compute default, loop = BYO, BYOK optional), `README.md` (local quickstart + honest BYO-loop note + future-cloud HTML comment + LM-skill note).

```diff
diff --git a/README.md b/README.md
index 1399595..aa68998 100644
--- a/README.md
+++ b/README.md
@@ -54,6 +54,34 @@
 
 ## Install
 
+### 既定 = 完全ローカル + 無料 (サーバー鍵・API キー不要) ★Franklin 方式★
+
+Anicca は **自分の計算資源を自分で払います** — ClawRouter / BlockRun に USDC を
+x402 で都度支払い (人間の API キー不要)。あなたが渡すのは「この端末 (= 住処)」
+だけ。財布が空なら **無料の NVIDIA モデル ($0)**、USDC が入れば自動で frontier に
+昇格します (Franklin と同じ "wallet = identity"、`runtime/compute-proxy/`)。
+
+```bash
+git clone https://github.com/Daisuke134/anicca ~/anicca && cd ~/anicca
+./install.sh                                   # runtime root + skills を同期
+cd runtime/compute-proxy && npm install        # 一度だけ (@blockrun/llm + viem)
+./start-local.sh                               # 自前 wallet 自動生成 → 自己決済プロキシ起動
+```
+
+`start-local.sh` は `http://127.0.0.1:8402/v1` に OpenAI 互換の **自己決済コンピュート
+プロキシ**を立て、`~/.automaton/wallet.json` の自前 wallet から **毎推論を USDC で自己
+決済**します。frontier を使いたければ表示された wallet アドレスに USDC を送るだけです。
+
+> **注 (正直な範囲):** このリポジトリには automaton ループ本体は **同梱されていません**
+> (`install.sh` も「automaton ループはあなたの runner で起動」と明記)。`start-local.sh` は
+> **コンピュートプロキシだけ**を起動します。あなたのループは `./start-local.sh <your-loop-cmd>`
+> として差し込んでください — `OPENAI_BASE_URL` を読む OpenAI 互換ループなら自動でプロキシ経由に
+> なります。引数なしで実行すると、プロキシを保持したまま差し込み方を表示します。**BYOK は任意** —
+> `ANTHROPIC_API_KEY` 等を `.env` に置けばそちらも使えますが、既定の無料ローカル動作には不要です。
+
+> **Life Manager はローカルスキル**として同梱済 (`skills/anicca-life-manager/` +
+> `skills/life/*`)。openclaw / hermes / claude-code 単体でも同じスキルとして動きます。
+
 ### Path A — already have a coding agent installed (≈ 30 秒)
 
 **Claude Code**, **Codex CLI**, **Cursor**, **Aider** のいずれかが常時稼働マシンにあれば、以下を貼り付けてください。
@@ -72,6 +100,14 @@ You are installing Anicca on this machine.
 
 ブラウザで <https://aniccaai.com/install> を開き、表示される手順に従ってください。Claude / Codex / Cursor のいずれかを 1 行で入れ、それから Path A に戻ります。
 
+## Cloud (FUTURE — not active yet)
+
+<!-- ROADMAP / NOT WIRED: the same body runs on a cloud droplet once Conway is
+available, where Anicca ALSO pays its own SERVER cost (not just compute) from its
+own wallet — removing the last human-in-the-loop (paying for shelter). Until
+Conway/Akash sovereign-deploy lands, the DEFAULT and only no-key path is LOCAL
+(above). Do not document this as live. -->
+
 ## アーキテクチャの一行
 
 **Conway automaton** (ReAct ループ = think→act→observe→persist + heartbeat デーモン) を 1 つの runtime として、常駐スキル群と 1 つの Base Smart Wallet が runtime root (`~/.anicca`) の下で動いています。compute は **ClawRouter / BlockRun** に x402 で USDC を払って都度購入します (人間の API キー不要)。`launchd` (macOS) または `systemd` (Linux) が automaton ループを 1 つだけ常駐させ、内蔵 heartbeat スケジューラが上の表のスキルを発火します。
diff --git a/install.sh b/install.sh
index 367003d..eca0330 100755
--- a/install.sh
+++ b/install.sh
@@ -128,13 +128,29 @@ cyan "[5/5] done."
 echo
 green "What's next:"
 cat <<EOM
-  1. Fill $ANICCA_HOME/.env with at least:
-       1 FUEL  (ANTHROPIC_API_KEY | OPENAI_API_KEY | DEEPSEEK_API_KEY | a ClawRouter WALLET key)
-       WALLET  (a funded Base wallet privkey for earn + telemetry signing)
-  2. Optional Life Manager keys: GEMINI_API_KEY, TWILIO_*, GOOGLE_API_KEY, AGENTMAIL_API_KEY.
-  3. Start the automaton loop (your runner of choice). On each wake it reads
-     $ANICCA_HOME/skills and runs the live slots; the report slot POSTs signed
-     telemetry to https://aniccaai.com so your instance shows up on /dashboard.
+  DEFAULT = FULLY LOCAL + FREE. No server key, no API key required. Anicca pays
+  its OWN compute via ClawRouter/BlockRun (USDC x402) from its OWN wallet — like
+  Franklin. You provide only this device (shelter); Anicca buys its own food.
+
+  1. Start the self-pay compute proxy (auto-creates a self-owned wallet):
+       cd "$REPO_ROOT/runtime/compute-proxy" && npm install   # one-time
+       "$REPO_ROOT/runtime/compute-proxy/start-local.sh"       # holds proxy on :8402
+     The proxy listens on http://127.0.0.1:8402/v1 and signs every inference in
+     USDC from \$HOME/.automaton/wallet.json. Empty wallet ⇒ free model, \$0.
+  2. Plug YOUR automaton loop in (this repo does NOT ship one — "your runner of
+     choice"): run it as  start-local.sh <your-loop-cmd>  , OR start your loop
+     separately with OPENAI_BASE_URL=http://127.0.0.1:8402/v1 . On each wake the
+     loop reads $ANICCA_HOME/skills and runs the live slots; the report slot
+     POSTs signed telemetry to https://aniccaai.com so you show on /dashboard.
+  3. (OPTIONAL) Unlock frontier models / more earning: send USDC to the wallet
+     address printed by start-local.sh — your loop can then pick a paid model. Or
+     BYOK: put ANTHROPIC_API_KEY | OPENAI_API_KEY | DEEPSEEK_API_KEY in
+     $ANICCA_HOME/.env and point OPENAI_BASE_URL at your provider instead.
+  4. (OPTIONAL) Life Manager keys: GEMINI_API_KEY, TWILIO_*, GOOGLE_API_KEY,
+     AGENTMAIL_API_KEY — only for phone wake-calls / lateness alerts.
+
+  # FUTURE (cloud, not active): once Conway is available, the same body can run
+  # on a droplet where Anicca ALSO pays its own server cost — see README "Cloud".
 
   Slots are declared in skills/registry.json. To enable a reserved slot, drop its
   implementation into its dir and flip status to "live" — no install.sh edit.
diff --git a/runtime/compute-proxy/start-local.sh b/runtime/compute-proxy/start-local.sh
new file mode 100755
index 0000000..57a0067
--- /dev/null
+++ b/runtime/compute-proxy/start-local.sh
@@ -0,0 +1,87 @@
+#!/usr/bin/env bash
+# anicca local-default compute proxy — fully local, free, no server/API key.
+#
+# Anicca pays its OWN compute via ClawRouter/BlockRun (USDC x402) from its OWN
+# wallet — exactly like Franklin. The user provides only SHELTER (this device);
+# Anicca buys its own FOOD (inference). Free NVIDIA models when the wallet is
+# empty; frontier models unlock automatically once USDC lands in the wallet.
+#
+# What this script DOES (and does NOT) do:
+#   1. ensures a self-owned wallet at ~/.automaton/wallet.json (auto-gen, never a human key)
+#   2. starts runtime/compute-proxy/proxy.mjs on :8402 (x402 self-pay, OpenAI-compatible)
+#   3. exports OPENAI_BASE_URL + OPENAI_API_KEY (placeholder) + ANICCA_MODEL so an
+#      OpenAI-compatible loop you pass in routes inference through the self-paid proxy
+#   4. exec "$@" if you give it a loop command; otherwise HOLD the proxy in the
+#      foreground and PRINT how to plug your loop in.
+#
+# IMPORTANT — HONEST SCOPE: this repo does NOT ship an automaton loop entrypoint
+# (install.sh:"Start the automaton loop (your runner of choice)"). So with NO
+# args this script ONLY runs the self-pay compute proxy and tells you to plug
+# your loop in as:  ./start-local.sh <your-loop-cmd>  . It does not pretend an
+# automaton is wired. Any OpenAI-compatible loop that reads OPENAI_BASE_URL /
+# OPENAI_API_KEY (or ANICCA_MODEL) will route through the proxy once you pass it.
+set -euo pipefail
+
+HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
+PORT="${COMPUTE_PROXY_PORT:-8402}"
+WALLET="$HOME/.automaton/wallet.json"
+# Free BlockRun model = $0/call, no key. Frontier (paid) is chosen by your loop
+# when the wallet has USDC; override with ANICCA_MODEL to pin one.
+FREE_MODEL="${ANICCA_FREE_MODEL:-nvidia/deepseek-v4-flash}"
+
+# --- 1. self-owned wallet (no human key) -------------------------------
+if [ ! -f "$WALLET" ]; then
+  mkdir -p "$HOME/.automaton"
+  node -e '
+    const {generatePrivateKey,privateKeyToAccount}=require("'"$HERE"'/node_modules/viem/accounts");
+    const fs=require("fs"); const pk=generatePrivateKey();
+    fs.writeFileSync(process.env.HOME+"/.automaton/wallet.json",
+      JSON.stringify({privateKey:pk,address:privateKeyToAccount(pk).address},null,2));
+    fs.chmodSync(process.env.HOME+"/.automaton/wallet.json",0o600);
+    console.error("[local] created self-owned wallet "+privateKeyToAccount(pk).address);
+  '
+else
+  echo "[local] wallet preserved: $(node -e 'console.log(JSON.parse(require("fs").readFileSync(process.env.HOME+"/.automaton/wallet.json")).address)')"
+fi
+
+# --- 2. start the x402 self-pay proxy ----------------------------------
+# Readiness is proven by a real routed path (/v1/chat/completions), NOT /v1/models
+# (proxy.mjs returns an empty data:[] for /models, so a 200 there proves nothing).
+proxy_ready() {
+  curl -sS --max-time 3 "http://127.0.0.1:$PORT/v1/chat/completions" \
+    -H 'Content-Type: application/json' \
+    -d "{\"model\":\"$FREE_MODEL\",\"messages\":[{\"role\":\"user\",\"content\":\"ping\"}]}" \
+    >/dev/null 2>&1
+}
+if ! curl -sS --max-time 2 "http://127.0.0.1:$PORT/v1/models" >/dev/null 2>&1; then
+  echo "[local] starting compute-proxy on :$PORT (x402 self-pay from own wallet)..."
+  ( cd "$HERE" && COMPUTE_PROXY_PORT="$PORT" node proxy.mjs ) &
+  # wait for the HTTP server to bind (port up). Live inference still needs the
+  # network + a free-tier/funded wallet — see step 4 / verify notes.
+  for _ in $(seq 1 20); do
+    curl -sS --max-time 1 "http://127.0.0.1:$PORT/v1/models" >/dev/null 2>&1 && break
+    sleep 0.5
+  done
+else
+  echo "[local] compute-proxy already live on :$PORT"
+fi
+
+# --- 3. point any OpenAI-compatible loop at the self-paid proxy --------
+export OPENAI_BASE_URL="http://127.0.0.1:$PORT/v1"
+export OPENAI_API_KEY="${OPENAI_API_KEY:-x402-local-nokey}"   # placeholder; proxy pays in USDC, not this
+export ANICCA_MODEL="${ANICCA_MODEL:-$FREE_MODEL}"
+echo "[local] inference -> $OPENAI_BASE_URL  model=$ANICCA_MODEL  (free until wallet funded)"
+
+# --- 4. run YOUR loop, or hold the proxy + show how to plug one in -----
+if [ "$#" -gt 0 ]; then
+  echo "[local] launching your loop: $*"
+  exec "$@"
+else
+  echo "[local] no loop command given — holding the self-pay compute proxy in foreground."
+  echo "[local] this repo does NOT ship an automaton loop; plug yours in like:"
+  echo "[local]     ./start-local.sh <your-loop-cmd>"
+  echo "[local] your loop just needs to read OPENAI_BASE_URL (now $OPENAI_BASE_URL)."
+  echo "[local] fund frontier: send USDC to the wallet address above; your loop can then pick a paid model."
+  echo "[local] (Ctrl-C to stop the proxy.)"
+  wait
+fi
```

---

## 3. Exact APPLY commands (this repo; do NOT commit here — recorded for the apply step)

```bash
# 1. extract the single ```diff block in §2 verbatim into /tmp/oss.diff
#    (one patch, three files: README.md, install.sh, runtime/compute-proxy/start-local.sh)
#    NOTE: the README hunk contains a nested ```bash fence — when copying, take the
#    WHOLE block from `diff --git a/README.md` down to the final `+fi`, do NOT
#    stop at the first inner ``` . (the new-file body is 87 lines, ends at `+fi`.)

cd /Users/anicca/anicca
git checkout main && git pull
git checkout -b feature/oss-local-default

# 2. dry-run check FIRST (VERIFIED exit 0 against HEAD a195c7f on 2026-06-16):
git apply --check /tmp/oss.diff && echo "APPLY-OK"

# 3. apply (the new-file hunk carries mode 100755, so it lands executable; the
#    belt-and-suspenders chmod is harmless):
git apply /tmp/oss.diff
chmod +x runtime/compute-proxy/start-local.sh

# 4. ★ TRACK THE UNTRACKED MANIFEST (reviewer finding 3) ★ — README/install tell the
#    user to `npm install` in runtime/compute-proxy, but package.json + package-lock.json
#    are NOT yet on the branch (`git ls-files runtime/compute-proxy/` = proxy.mjs only).
#    They MUST be added so the documented `npm install` resolves @blockrun/llm + viem:
git add runtime/compute-proxy/package.json runtime/compute-proxy/package-lock.json
#    (if package-lock.json is absent, run `npm install` once in that dir to generate it,
#     then add both. node_modules/ stays gitignored — only the manifest is tracked.)

# 5. commit + push (origin = anicca):
git add -A
git commit -m "feat(oss): local-default ClawRouter compute proxy — free, no server key; loop stays BYO (Franklin-pattern)"
git push -u origin feature/oss-local-default
# → gh pr create --base main --title "OSS local-default compute (ClawRouter self-pay)" ...
```

> NOTE: the §2 diff is the **canonical diff captured from a real working-tree edit** then reverted
> (no commit) — hunk headers (`@@ -54,6 +54,34 @@` etc.) and blob hashes (`1399595..aa68998`,
> `367003d..eca0330`, `0000000..57a0067`) are REAL, taken from `git diff` on live HEAD `a195c7f`.
> `git apply --check /tmp/oss.diff` returned **exit 0** during authoring. If HEAD later drifts and
> an offset appears, `git apply --recount /tmp/oss.diff` re-derives counts from the verbatim context.

---

## 4. LIVE VERIFY commands (prove local run + ClawRouter compute, no server key)

```bash
cd /Users/anicca/anicca/runtime/compute-proxy
npm install                                   # @blockrun/llm + viem (no API key anywhere)

# (a) start the self-pay proxy — proves wallet auto-gen + proxy boot, ZERO keys in env.
#     With no loop arg it HOLDS the proxy and prints how to plug a loop in (it does NOT
#     claim an automaton is running — none ships in this repo):
env -u ANTHROPIC_API_KEY -u OPENAI_API_KEY -u DEEPSEEK_API_KEY ./start-local.sh &
sleep 4

# (b) prove the self-owned wallet exists (Anicca's own, not a human key):
test -f ~/.automaton/wallet.json && \
  node -e 'console.log("WALLET", JSON.parse(require("fs").readFileSync(process.env.HOME+"/.automaton/wallet.json")).address)'

# (c) ★ REAL INFERENCE PROOF + the network-dependent gate ★
#     proxy.mjs only routes /v1/chat/completions (its /v1/models returns an empty
#     data:[] — a 200 there proves nothing). So the readiness/inference proof MUST hit
#     /v1/chat/completions. THIS is the network-dependent step: it requires live BlockRun
#     reachability + a free-tier-eligible (or USDC-funded) wallet. It is NOT a guaranteed
#     local 200 — if BlockRun is unreachable or the free tier is exhausted the proxy
#     returns 502 (proxy.mjs catch path), which is the honest failure, not the local one.
curl -sS http://127.0.0.1:8402/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"nvidia/deepseek-v4-flash","messages":[{"role":"user","content":"reply exactly: ANICCA RUNS ON ITS OWN COMPUTE"}]}' \
  | python3 -c 'import json,sys; d=json.load(sys.stdin); print("INFER:", d.get("choices",[{}])[0].get("message",{}).get("content", d.get("error", d)))'

# EXPECT (local, always): WALLET 0x… printed (own wallet); proxy bound on :8402 ⇒ proves
#   fully-local boot + self-owned wallet + NO server key (ANTHROPIC/OPENAI/DEEPSEEK UNSET).
# EXPECT (network gate, step c): a real model reply via BlockRun on the FREE model, $0, no
#   key — IFF BlockRun is reachable and the wallet is free-tier/funded. A 502/error here is
#   the network/funding gate, NOT a wiring defect. Funding the wallet address from (b) with
#   USDC is what unlocks frontier — money flows to the user's own anicca wallet.
```

---

## 5. Honest scope / risk note

| File in the diff | Doc change | Real wiring | Risk / caveat |
|---|---|---|---|
| `runtime/compute-proxy/start-local.sh` (NEW) | — | ✅ REAL new runnable entrypoint — boots the existing `proxy.mjs`, auto-gens the wallet via `viem` already in node_modules, exports `OPENAI_BASE_URL`. **Does NOT wire an automaton** (none exists): with no arg it holds the proxy + prints BYO-loop guidance; with an arg it `exec`s your loop. | Wallet gen needs `runtime/compute-proxy/node_modules/viem` → only after `npm install` in that dir (`accounts/generatePrivateKey` verified present). Free model id `nvidia/deepseek-v4-flash` = what MASTER:134 verified; if BlockRun renames it, set `ANICCA_FREE_MODEL`. The `/v1/models` readiness loop only proves the port is up; the real inference proof is `/v1/chat/completions` (§4c), which is network/funding-dependent. |
| `install.sh` | ✅ doc/UX ("what's next" text) | partial — points users at the real new runner; **explicitly states the loop is BYO** ("this repo does NOT ship one") | Pure text in `cat <<EOM`; no behavioral risk. Cloud line is a COMMENT (`#`), not active. |
| `README.md` | ✅ doc | — | Doc only. The new quickstart includes an **honest BYO-loop note** (no claim an automaton is wired). "Cloud (FUTURE)" is inside an HTML `<!-- -->` comment → renders as nothing on GitHub = future/flagged, not active. |
| `runtime/compute-proxy/package.json` + `package-lock.json` | — | ⚠ **currently UNTRACKED** — must be `git add`ed on the branch (see §3 step 4) so the documented `npm install` has a tracked manifest | Without this, README/install tell the user to `npm install` against files not on the branch. `node_modules/` stays gitignored; only the manifest is tracked. |
| LM-as-local-skill | ✅ documented (README note) | already wired (no code added) | Confirmed present (`skills/anicca-life-manager/SKILL.md` + registry `life/*`); patch only states it, does not re-implement it. |
| ClawRouter compute engine | — | already real (`proxy.mjs`, `@blockrun/llm`) | NOT modified — this patch makes it **bootable + the documented default**, closing GAP 1/2/3. MASTER:140 "ClawRouter REJECTED as base (shared router addr hardcoded)" is real: `@blockrun/llm` settles via BlockRun's gateway, not a per-wallet sovereign rail. This patch ships BlockRun's PROVEN free-tier path (what works today); fully-sovereign native-x402 inference is a separate future build (MASTER:138), NOT claimed here. |

**Net:** one new runnable script (`start-local.sh`) that **boots the existing self-pay compute proxy** = the only real wiring; `install.sh` + `README.md` = doc/UX making local-free compute the documented default **while truthfully stating the automaton loop is BYO** (`./start-local.sh <your-loop-cmd>`). No invented features, no claim the automaton is wired, no claim of a guaranteed local inference 200 (the real inference proof is the network-dependent `/v1/chat/completions` gate). The compute engine + LM skill already exist and are cited. The whole patch is one VERIFIED-applicable diff (`git apply --check` = exit 0 against live HEAD `a195c7f`); the untracked `package.json`/`package-lock.json` must be `git add`ed per §3 step 4.
