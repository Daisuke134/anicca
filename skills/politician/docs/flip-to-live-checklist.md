# Flip-to-LIVE checklist

The bridge between agent-builds and user-bootstraps. Each step unlocks one cron from DRY to LIVE. Order matters — earlier steps gate later ones.

---

### ✅ Step 0 — verify the four LIVE intel crons fire

Already shipped LIVE in v0.1.0:

- `politician-policy-monitor` (every 15 min)
- `politician-bill-tracker` (daily 14:00 JST, weekdays)
- `politician-news-pulse` (daily 07:00 JST)
- `politician-opensecrets-scan` (Mon 08:00 JST)

**Bootstrap (one-time, by user):**

```bash
# 1. Add API keys to ~/.openclaw/.env
echo "REGULATIONS_GOV_API_KEY=<sign-up-at-api.data.gov>" >> ~/.openclaw/.env
echo "CONGRESS_GOV_API_KEY=<sign-up-at-api.congress.gov>" >> ~/.openclaw/.env
echo "OPENSECRETS_API_KEY=<sign-up-at-opensecrets.org>" >> ~/.openclaw/.env
echo "OPENFEC_API_KEY=<sign-up-at-api.open.fec.gov>" >> ~/.openclaw/.env  # optional but recommended

# 2. (Optional) Manually fire one to confirm
MODE=monitor bash ~/.openclaw/skills/politician/scripts/run.sh
MODE=news bash ~/.openclaw/skills/politician/scripts/run.sh   # works without keys (RSS)
```

Slack channel `{{profile.channels.reportChannel}}` should now receive scheduled posts.

---

### ☐ Step 1 — Delaware LLC + Stripe revenue path

**Action.** See `docs/incorporation-checklist.md` §1.

**No env flip — yet.** This step is a precondition for the Super PAC bank account and for the Stripe→PAC sweep.

---

### ☐ Step 2 — Hire Super PAC treasurer + register PAC at FEC

**Action.** See `docs/hiring-roster.md` §2 + `docs/incorporation-checklist.md` §3.

**On completion:**
1. Update `humans.yaml: treasurer.{{profile.lateness.stakeholders.senderType}}_name + {{profile.lateness.stakeholders.channel}} + hire_status: signed`.
2. Verify FEC Form 1 acknowledgement received.
3. Open Amalgamated Bank account in committee name; record routing/account in 1Password (NOT in `.env`).
4. **Flip the env flag:**
   ```bash
   sed -i '' 's/^PAC_FORMED=.*/PAC_FORMED=true/' ~/.openclaw/.env
   ```
5. **Unlocks:** `politician-fec-year-end` (DRY → LIVE-prep, still needs treasurer sign on Form 3X) and the math half of `politician-stripe-to-pac`.

---

### ☐ Step 3 — Flip stripe-to-pac to LIVE money movement

**Action.** Confirm step 2 is fully clean (treasurer signed, bank live). Then:

1. Add `STRIPE_API_KEY_PAC` to `.env` (Stripe Connect or external-bank wire).
2. Set monthly sweep percentage:
   ```bash
   echo "POL_PAC_SWEEP_PCT=10" >> ~/.openclaw/.env
   ```
3. **Flip global DRY off:**
   ```bash
   sed -i '' 's/^POLITICIAN_DRY_RUN=.*/POLITICIAN_DRY_RUN=false/' ~/.openclaw/.env
   ```
4. **First LIVE run.** Manually trigger once and verify the wire arrives:
   ```bash
   MODE=stripe_pac bash ~/.openclaw/skills/politician/scripts/run.sh
   ```
5. Counsel reviews the first wire confirmation.

---

### ☐ Step 4 — Hire LDA lobbyist + register LD-1

**Action.** See `docs/hiring-roster.md` §1 + `docs/incorporation-checklist.md` §5.

**On completion:**
1. Update `humans.yaml: lobbyist.{{profile.lateness.stakeholders.senderType}}_name + {{profile.lateness.stakeholders.channel}} + lda_registrant_id + hire_status: signed`.
2. Verify LD-1 filed at https://lda.congress.gov/.
3. Add `RESEND_API_KEY` to `.env` for outbound {{profile.lateness.stakeholders.channel}}.
4. **Flip the env flag:**
   ```bash
   sed -i '' 's/^LOBBYIST_HIRED=.*/LOBBYIST_HIRED=true/' ~/.openclaw/.env
   ```
5. **Unlocks:**
   - `politician-staffer-weekly-brief` — actual {{profile.lateness.stakeholders.channel}}s go out (one per due office, capped at 30 unique recipients per week).
   - `politician-staffer-reply-watch` — Gmail polling LIVE.
   - `politician-lda-quarterly` — LD-2 prep for lobbyist signature.

---

### ☐ Step 5 — Register JP 政治団体

**Action.** See `docs/incorporation-checklist.md` §6 + `docs/hiring-roster.md` §4.

**On completion:**
1. Fill `humans.yaml: jp_seijidantai_daihyo / jp_kaikei_sekininsha / jp_shokumu_dairisha`.
2. Verify 受理通知 from 都道府県選管.
3. Open JP bank account in 政治団体 name.
4. Add `politician.jp_seijidantai_name` to `~/.openclaw/state/anicca.json`.
5. **Flip the env flag:**
   ```bash
   sed -i '' 's/^JP_SEIJIDANTAI_REGISTERED=.*/JP_SEIJIDANTAI_REGISTERED=true/' ~/.openclaw/.env
   ```
6. **Unlocks:** `politician-jp-shushihokoku` LIVE-prep for 会計責任者 signature.

---

### ☐ Step 6 — First bill drafted end-to-end

**Action.** Allow `politician-staffer-weekly-brief` to queue 4 K-Dense `scientific-writing` bill drafts (one per pillar, rotating weekly). After 4 weeks the corpus has `data/drafts/bills/<ts>.full.md` for each pillar.

1. Counsel reviews each draft.
2. Best-of-4 chosen as first introducible bill.
3. Tag git commit `v0.5-first-bill-counsel-cleared`.

**Unlocks:** v1.0 open-source release at `github.com/Daisuke134/anicca-politician`.

---

### Quick reference: env flag matrix

| flag | default | flip when |
|---|---|---|
| `REGULATIONS_GOV_API_KEY` | unset | step 0 |
| `CONGRESS_GOV_API_KEY` | unset | step 0 |
| `OPENSECRETS_API_KEY` | unset | step 0 |
| `OPENFEC_API_KEY` | unset | step 0 |
| `PAC_FORMED` | `false` | step 2 |
| `STRIPE_API_KEY_PAC` | unset | step 3 |
| `POLITICIAN_DRY_RUN` | `true` | step 3 (global LIVE) |
| `LOBBYIST_HIRED` | `false` | step 4 |
| `RESEND_API_KEY` | unset | step 4 |
| `JP_SEIJIDANTAI_REGISTERED` | `false` | step 5 |
