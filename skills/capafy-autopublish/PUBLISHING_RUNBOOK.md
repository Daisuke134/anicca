# Capafy Publishing Runbook (proven on C1 + C2, 2026-06-25) — so failures NEVER repeat

The ONE proven path to publish a run_online subscription listing with REAL Claude Sonnet 4.6.
Every step has a VERIFY gate. Never trust a "shipped"/toast alone — confirm with publish-remote-status.

## Canonical LLM config (copy the winners = Claude Sonnet 4.6)
- CP1 Primary Model (display) = **Claude Sonnet 4.6**
- CP2 LLM Config: Base URL **https://openrouter.ai/api/v1** · Model **anthropic/claude-sonnet-4.6** (dot 4.6) · API Format **openai-responses** (Capafy default) · Key **CAPAFY_HOST_OPENROUTER_KEY** ($LIFE_MANAGER_STATE_HOME/.env)
- Direct Anthropic FAILS (no /responses). OpenRouter speaks /responses + serves Claude. Verified.

## Flow (one listing)
1. **Research winner live**: `capafy-user` GET `/agent/agent/agents/<id>` with `X-Access-Token` header → copy billings (cycle/price/cap/trial) + categoryId + structure. Words = original (anti-plagiarism), facts = verbatim.
2. **Build skill**: pure-LLM, self-contained, NO local deps/secrets. Add `test/case1.md`. grep-verify clean.
3. **Write LISTING.md**: title ≤50 chars, shortDescription, **welcomeMessage**, detailedDescription (emoji sections + table).
4. **Copy skill to clean-WS** `$LIFE_MANAGER_STATE_HOME/work/capafy/skills/<skill>` (LEAK GUARD — never publish from live $LIFE_MANAGER_STATE_HOME/work).
5. **publish-init** `--runtime-dir $LIFE_MANAGER_STATE_HOME/work/capafy --skill-dir <...> --selections-file .temp/confirmed-selections.json`. Over 5-draft cap → put a junk draft's `agent_id` in selections to reuse it. ★ NOTE: re-init does NOT set the card from selections — the CARD MUST be filled in CP1 web form. ★
6. **CP1 (CloakBrowser)** — fill ALL of these or "提出を確認" silently fails:
   - 基本情報: title (real-type), shortDescription (textarea[0]), detailedDescription (textarea[1]), **welcomeMessage (the "初回実行前にユーザーへ表示" textarea — REQUIRED, easy to miss)**, tags, privacy URL, category dropdown.
   - 価格設定: "Capafy で実行" → "Subscription" → set Plan 1 cycle + Add Plan ×2 → fill price/cap per cycle (placeholders: day 0.07/50, week 0.5/200, month 2/500) → **Primary Model = Claude Sonnet 4.6** → **test input (the "例：『たくさん買って…』" textarea — REQUIRED)** → **AI service provider field** → **per-plan trial radio: select Enable OR No Free Trial on EVERY plan (an unselected trial radio silently blocks save).** If Enable: fill Free Days + Free Request Limit (>0). Reliable valid state when trial config fights you = **No Free Trial on all plans**.
   - Click **提出を確認**. ★ VERIFY GATE: page must reach `page=card-done` / "カードを保存しました". If still `page=edit`, a required field is empty/invalid — find the red error or empty input and fix; do NOT proceed. ★
7. **publish-configure --deep-scan** → leak check (`.temp/staging/agent.workspace_documents.json` must NOT exist) → submit `{"generic":[],"env_var":[]}` findings → status must be **configured** (not "ready" — "ready" w/ 0 keys = card never saved, go back to CP1).
8. **CP2 (drive_checkpoint2.py <CP2url>)** — auto: expand 検出されたキー → click Edit pencil if card in summary mode → set Base URL/Model/Key (OpenRouter recipe) → delete blockrun(127.0.0.1) card → "キーを確認して保存". ★ VERIFY: "キー確認済み" toast / page=credential-done. ★
9. **publish-ship** → CP3 url.
10. **CP3 (CloakBrowser)**: click "審査に提出" → modal "提出を確認".
11. ★★ FINAL VERIFY (truth source) ★★ `publish-remote-status --agent-id <id>` → MUST show: **status=1** (審査中) · **isConfirmedConfigKeys=1** · **agentType=run_online** · title=<our title> · model="Claude Sonnet 4.6". If status=0 or agentType=download or title=old → the chain operated on the wrong/old draft; DO NOT claim done — redo from the failed gate. Then append to `state/published.jsonl`.

## Hard lessons (why this runbook exists)
- "shipped" can be a lie: it shipped the OLD junk draft when CP1 never saved. ALWAYS verify remote-status fields (status/isConfirmedConfigKeys/agentType/title/model), not the local "shipped".
- CP1 silent-block causes: empty welcomeMessage, empty test input, an unselected per-plan trial radio, empty provider field. Fill all, then confirm `page=card-done`.
- CP2 card defaults to SUMMARY mode → must click Edit before fields exist. drive_checkpoint2.py now does this.
- Direct Anthropic never passes CP2 (openai-responses /responses 404) → OpenRouter only.
- Re-using a download-type junk draft for run_online is fine (C1 did it) BUT you must fully fill + save CP1; selections alone don't set the card.

## IMAGE-GEN skills (Amazon/poster/headshot) — the OTHER recipe (verified 2026-06-25)
Winner Listful (Amazon Listing Images, 74 sales): agentRuntime=claude, displayed model="GPT Image 2".
How it actually works: **OpenAI Responses API `image_generation` tool** (openai-responses native).
VERIFIED: `POST https://api.openai.com/v1/responses` with `{"model":"gpt-5","tools":[{"type":"image_generation",...}]}` + our funded CAPAFY_HOST_OPENAI_KEY → returns image_generation_call (base64 image). Works.
→ CP2 for an IMAGE skill = **OpenAI** (NOT OpenRouter-Claude): Base URL `https://api.openai.com/v1`, Model `gpt-5` (or gpt-4.1), format openai-responses, Key CAPAFY_HOST_OPENAI_KEY, display Primary Model "GPT Image 2". The skill plans in text then calls the image_generation tool per image. drive_checkpoint2.py is OpenRouter/Claude only → for image skills set CP2 manually to OpenAI.
Cost: ~$0.01–0.17/image; cap (e.g. month cap80) bounds it << revenue.

## UPGRADING a LISTED download agent → run_online (O1 deep findings 2026-06-25)
Mechanism (api-docs 00_overview §166-167, SKILL.md:127/278):
- agentType (download/run_online) is set on CP1 web "収益化モデル" card (Capafy で実行 = run_online, distribution_mode=cloud_hosted).
- run_online default billing = **Hourly**; must click the **Subscription** card under "Billing Method" to get day/week/month plans. (hourly billing mode IS real on Capafy.)
- ★ Toggling mode download↔run_online ROLLS the version back to draft AND CLEARS the confirmed skill selection → you MUST re-confirm the skill on the Skill/プラグイン tab, then re-run publish-configure under the new agentType (SKILL.md:127). ★
- download mode hosts NO keys (no CP2). run_online needs the LLM Config (CP2).
BLOCKER (unsolved): converting an ALREADY-LISTED (status=4) download agent (e.g. 3332784488 jp-humanizer) to run_online did NOT persist — UI showed run_online + advanced to page=credential, but remote-status stayed agentType=download / isConfirmedConfigKeys=0 / billings empty across ~25 attempts. The clk() helpers were also hitting inner spans not the radio CARD (fix: climb to the card container before clicking).
RELIABLE ALTERNATIVE: create the skill as a FRESH run_online agent (proven 5/5 on C1-C5) instead of in-place converting a listed download agent. Needs a free unlisted slot (max 5 unlisted; C1-C5 fill it until reviewed). So: wait for C1-C5 review → free slots → create O1/O2 fresh as run_online.

## LOGO/ICON upload (verified 2026-06-25) — the working recipe
1. Build edit URL: refresh-url --step init → extract token → `https://capafy.ai/developer/createAgent?source=temp-link&token=<TOK>&page=edit`
2. goto (wait_until networkidle + sleep). Click 基本情報 tab. ★ file inputs are mounted only after the tab+page fully load — query `input[type=file]` returns 2 (logo + detail-image). If 0, the page/tab wasn't fully loaded — re-goto.
3. set_input_files(icon) on BOTH file inputs (one is the logo) → a **"ロゴを切り抜く" (crop) MODAL opens** showing the icon.
4. Click the modal's **保存** button (width<200) → crop confirmed, logo set (left ロゴ box + right preview card both show the icon).
5. Click card **提出を確認** → ★SUCCESS = a TOAST "Agent カードを保存しました"/"保存しました" appears (NOT a url=card-done navigation; checking url false-reports NOT SAVED).★ Use drive_logo.py (scripts/) — verified, takes edit_url+icon, toast-based success.
6. ALL in ONE script (file inputs vanish across Bash calls — the page re-renders; do set→crop→save in one run).
Icons generated via OpenAI image_generation (gpt-5 + tools image_generation, medium, 1024→sips -Z 512).

## CP1 field limits (learned 2026-06-26): shortDescription MAX 500 chars (over=red border, silent save-block, no toast). title ≤50. Trim before set.

## ★★★ NEW-AGENT CP1 — the complete gotcha list (cracked 2026-06-26 on O1, ~80 attempts) ★★★
A brand-new run_online agent (NOT a junk-draft reuse) has CP1 traps the reused-draft path hides. ALL must be right or 提出を確認 silently NO-OPS (button enabled, no red text, but nothing saves, skills stays 0):

1. ★ RHF (React-Hook-Form) STALENESS ★: NEVER set field values via `page.evaluate` native value-setters (Object.getOwnPropertyDescriptor(...).value.set) — RHF's internal state stays empty → the form thinks the field is blank → 提出を確認 no-ops. USE Playwright element methods: `el.fill(v)` / `el.type(v)`. (This was THE root cause of ~50 failed saves.)
2. ★ React SYNTHETIC-CLICK ignored ★: for tabs / monetization cards / billing cards, `evaluate(e=>e.click())` is a synthetic event React often ignores. USE real pointer events: get coords via evaluate, then `page.mouse.click(x,y)`.
3. ★ DUPLICATE TITLE = silent no-op ★: if the title equals another of your agents' titles (Capafy auto-detects the title from the skill, so two skills with the same name collide), 提出を確認 no-ops with NO visible error. Use a UNIQUE title (e.g. add "Pro").
4. ★ 下書きを保存 (Save Draft) PERSISTS fields without full validation ★ — use it to bank progress incrementally and verify via publish-remote-status (title/short/detail/billings/logoUrl/model all reflect immediately).
5. 収益化モデル: click the heading TEXT "Capafy で実行" at (left+20,top+8), not the card center.
6. Billing Method "Subscription" is BELOW "Hourly" → scrollIntoView before clicking.
7. Plans: "Add Plan" button label is "Add Plan (1/3)" etc. — match loosely.
8. ★ AI service provider field (placeholder "例: OpenAI、Anthropic、MiniMax") is REQUIRED ★ → `.type("openrouter.ai")`.
9. Container mode (On-Demand US$0.07/day vs Cron+On-Demand) — select On-Demand.
10. ★★ THE FINAL BLOCKER: EVERY plan must have a TRIAL CHOICE selected (Enable Free Trial OR No Free Trial). An unselected trial radio on ANY plan = price-tab red ✗ = 提出を確認 no-ops, with NO red text (only a tab-icon goes red). ★★
11. ★ Validate via the TAB ICON COLOR: find the 価格設定 tab <button>, read its <svg> color — green rgb(61,220,132)=✓ valid, red rgb(229,83,75)=✗ invalid. This is the ONLY reliable "is the tab complete" signal. ★
12. Success = toast "カードを保存しました" OR url=card-done/credential — never trust the absence of red text.

### TRIAL config = COPY THE WINNER (Unscore 4097802482 for Humanizer): day=No Free Trial, week=Enable 24h, month=Enable 72h. (Do NOT set all-No — that's original; follow the winner.)

## drive_cp1.py — 2 MORE gotchas found on O2 (2026-06-27), now baked in:
13. ★ The React form fields LAZY-MOUNT only after a Playwright LOCATOR click on the 基本情報 tab (`pg.get_by_text("基本情報",exact=True).first.click()`). On a fresh new_page goto, inputs count = 0 until that locator click fires the render. evaluate/coords clicks do NOT mount it. (drive_cp1 uses tab_click()).
14. ★ DPA checkbox REQUIRED: at the bottom of 価格設定 there is a "*私は Capafy のデータ処理契約を読み…準拠していることを確認します" checkbox. Unchecked = price-tab red ✗ = 提出を確認 no-ops. Must check it. ★
15. Add Plan button text is "Add Plan (1/3)" — match ANCHORED `^Add Plan` (a loose /Add Plan/ regex matches a huge page container and returns wrong coords → plans stay at 1).
