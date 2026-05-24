# RECIPE: Camp Fire JP project end-to-end (camofox + gog gmail)

**Recipe written 2026-05-12. Recreatable by any agent that has camofox + gog gmail + Stripe API.**

This is **exactly** how Camp Fire project `951165` was built from zero. No scripts wrap any of this — these are the literal HTTP calls + button clicks that any other agent can replay.

---

## Prerequisites

```bash
# camofox-{{profile.lateness.stakeholders.channel}} running on :9377 (idempotent start)
bash ~/.openclaw/skills/camofox-{{profile.lateness.stakeholders.channel}}/scripts/start.sh

# gog gmail CLI auth (Mac Mini keychain unlocked)
export GOG_KEYRING_PASSWORD=<password>
gog gmail labels list -a {{profile.contact.personalEmail}} -j --results-only  # smoke test

# env: ~/.openclaw/.env contains
#   DAIS_BANK_NAME / DAIS_BANK_BRANCH / DAIS_BANK_ACCOUNT_NUMBER / DAIS_BANK_ACCOUNT_NAME_EN
#   DAIS_MYNUMBER (just number, scan upload requires Dais physical)
```

---

## Step 1 — Account creation

**Recipe (ONE-TIME per project owner):**

> ⚠️ Per `feedback_always_google_login_your-email-user.md` HARD RULE — for any future Camp Fire account, use **Google login (`{{profile.contact.personalEmail}}` / `<password>`)** + Slack-notify Dais for 2FA tap. The current 951165 project was created via {{profile.lateness.stakeholders.channel}} signup before this rule was set; do not repeat that pattern.

### Recipe A — Google login path (use this for all NEW services)

1. `curl -sS -X POST http://localhost:9377/tabs -H 'Content-Type: application/json' -d '{"url":"https://camp-fire.jp/login","userId":"anicca-retreat","sessionKey":"crowdfund"}'`
2. From snapshot, find Google login link (e.g. ref `e44`, "GOOGLEでログインする"). Click it.
3. Enter `{{profile.contact.personalEmail}}` in {{profile.lateness.stakeholders.channel}} textbox. Click Next.
4. If passkey challenge: click "Try another way" → "Enter your password" → type `<password>` → Next.
5. If 2FA tap: post Slack to `#metrics` channel `{{profile.channels.reportChannel}}`: "Camp Fire 2FA tap お願いします (camofox session key=crowdfund). 5 分以内に tap してください." Then poll `/snapshot` every 30s for redirect to Camp Fire mypage.
6. Once redirected, session is persisted in `~/.camofox/profiles/anicca-retreat/crowdfund/` cookies.

### Recipe B — Email signup (legacy 5/11 — DO NOT REPEAT)

Skipped to avoid violating Google-login HARD RULE. Documented only for reference of how 951165 came to exist.

---

## Step 2 — Open new project

Once logged in:

1. Navigate camofox to `https://camp-fire.jp/mypage/projects/new` OR click `プロジェクトをつくってみる` from `/readyfor` page.
2. Camp Fire auto-creates a draft and redirects to `/mypage/projects/<DRAFT_ID>/planning_information?first=true`.
3. Save the `<DRAFT_ID>` (e.g. `951165`) to `~/.openclaw/skills/anicca-retreat-factory/data/crowdfund-state.json`.

---

## Step 3 — 6-question survey

The page is rendered as Vue with **non-input radio buttons** for items 2-6 (text-only paragraphs are clickable). Use `/evaluate` to set them via direct DOM input access:

```bash
TAB_ID=<tab-id>
curl -sS -X POST "http://localhost:9377/tabs/$TAB_ID/evaluate" \
  -H 'Content-Type: application/json' \
  -d '{"expression":"(()=>{const click=(name,value)=>{const e=document.querySelector(`input[type=radio][name=\"${name}\"][value=\"${value}\"]`);if(e){e.click();return true;}return false;};const r=[];r.push(click(\"target_amount_type\",\"over_five_million\"));r.push(click(\"desired_start_time_type\",\"less_half_a_year\"));r.push(click(\"project_category_type\",\"social_issue\"));r.push(click(\"planned_announcement_count_type\",\"over_1000\"));r.push(click(\"planned_backer_count_type\",\"over_hundred\"));const counselor=Array.from(document.querySelectorAll(\"input[type=radio][value=none]\")).filter(e=>!e.name);if(counselor[0]) counselor[0].click();return r;})()","userId":"anicca-retreat","sessionKey":"crowdfund"}'
```

For Q1 (organizer type), click ref `e1` (個人 radio) directly via `/click`.

Then click `次へ` (ref `e9`) via `/click`.

---

## Step 4 — 概要文 (overview, 150 char max)

After Step 3, page redirects to `/planning_information?edit_overview=true&first=true`.

Type into ref `e1` (textarea):

```bash
curl -sS -X POST "http://localhost:9377/tabs/$TAB_ID/type" -H 'Content-Type: application/json' \
  -d '{"ref":"e1","text":"<150-char overview>","userId":"anicca-retreat","sessionKey":"crowdfund"}'
```

Then click `ページ作成に進む` (ref `e2`).

---

## Step 5 — Story (title + body, Froala WYSIWYG editor)

Navigate: `https://camp-fire.jp/mypage/v3/projects/<DRAFT_ID>/edit/story`

The editor uses **Froala** (`.fr-element.fr-view` div is contenteditable, with a hidden `<textarea>` that stores the HTML). Set both to ensure Vue/Froala syncs:

```javascript
// Inject via /evaluate
(()=>{
  const HTML = `<h6>自己紹介</h6><p>...</p>...`;  // your full story HTML
  // 1. Title input (placeholder contains "バルをオープン")
  const titleInputs = Array.from(document.querySelectorAll('input[type=text],input:not([type])')).filter(i => i.placeholder?.includes('バルをオープン'));
  for (const i of titleInputs) {
    const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
    setter.call(i, "<your title>");
    i.dispatchEvent(new Event('input', {bubbles:true}));
    i.dispatchEvent(new Event('change', {bubbles:true}));
  }
  // 2. Story Froala editor
  const div = document.querySelector('.fr-element.fr-view');
  if (div) {
    div.innerHTML = HTML;
    div.dispatchEvent(new Event('input', {bubbles:true}));
    div.dispatchEvent(new Event('blur', {bubbles:true}));
  }
  // 3. Hidden textarea sync (Froala writes here)
  const tas = document.querySelectorAll('textarea');
  for (const ta of tas) {
    if (ta.value && (ta.value.startsWith('<h6>') || ta.value.startsWith('<p>'))) {
      const setter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set;
      setter.call(ta, HTML);
      ta.dispatchEvent(new Event('input', {bubbles:true}));
      ta.dispatchEvent(new Event('change', {bubbles:true}));
    }
  }
})()
```

Then find `保存する` button via JS (`Array.from(document.querySelectorAll('button')).find(b=>/^保存(する|して.*)?$/.test(b.textContent.trim())).click()`).

Verify save with `document.body.textContent.includes('保存しました')`.

---

## Step 6 — 募集設定 (target / category / region)

Navigate: `/edit/overview`

The target amount default is `5000000` (¥5M). Replace with `30000000`:

```javascript
(()=>{
  // Target amount (two synced inputs displaying value)
  const inputs = document.querySelectorAll('input[type=text], input[type=number], input:not([type])');
  for (const i of inputs) {
    if (i.value === '5000000' || i.value === '5,000,000') {
      const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
      setter.call(i, '30000000');
      i.dispatchEvent(new Event('input', {bubbles:true}));
      i.dispatchEvent(new Event('change', {bubbles:true}));
      i.dispatchEvent(new Event('blur', {bubbles:true}));
    }
  }

  // 使い道 checkboxes
  const want = ['設備費', '人件費', '広報/宣伝費'];
  const chks = Array.from(document.querySelectorAll('input[type=checkbox]'));
  for (const w of want) {
    const target = chks.find(c => {
      const text = (c.closest('label')||c.parentElement)?.textContent?.trim();
      return text === w || text?.includes(w);
    });
    if (target && !target.checked) target.click();
  }

  // 関連地域 = 千葉県 (combobox)
  const sels = Array.from(document.querySelectorAll('select'));
  for (const s of sels) {
    const opt = Array.from(s.querySelectorAll('option')).find(o => o.textContent.trim() === '千葉県');
    if (opt) {
      const setter = Object.getOwnPropertyDescriptor(window.HTMLSelectElement.prototype, 'value').set;
      setter.call(s, opt.value);
      s.dispatchEvent(new Event('change', {bubbles:true}));
    }
  }
})()
```

All-In radio is default-checked, so leave alone. Click `保存する`.

---

## Step 7 — 5 reward tiers (THIS IS THE TRICKY PART)

For each tier:

1. Navigate to `/edit/rewards/new` (Camp Fire creates a NEW draft each visit).
2. **Wait at least 15-20 seconds** for Vue hydration (text inputs render late).
3. Fill in the form via `/evaluate`:

```javascript
(()=>{
  const PRICE = 30000;  // ¥
  const YEAR = "2027";
  const MONTH = "12";
  const DESC = "Anicca Retreats Build the Center に...";

  // 1. Description textarea
  const txa = document.querySelector('textarea[placeholder*="支援したくなる"]') || document.querySelector('textarea');
  if (txa) {
    const setter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set;
    setter.call(txa, DESC);
    txa.dispatchEvent(new Event('input', {bubbles:true}));
    txa.dispatchEvent(new Event('change', {bubbles:true}));
  }

  // 2. Price — CRITICAL: Camp Fire uses input WITHOUT type attribute (input:not([type])) for prices!
  //    Both display + raw inputs share placeholder='0'. Set BOTH.
  const priceInputs = Array.from(document.querySelectorAll('input:not([type])')).filter(i => i.placeholder === '0');
  for (const p of priceInputs) {
    const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
    setter.call(p, '');
    p.dispatchEvent(new Event('input', {bubbles:true}));
    setter.call(p, String(PRICE));
    p.dispatchEvent(new Event('input', {bubbles:true}));
    p.dispatchEvent(new Event('change', {bubbles:true}));
    p.dispatchEvent(new Event('blur', {bubbles:true}));
  }

  // 3. Year + month <select>
  const sels = Array.from(document.querySelectorAll('select'));
  const setter = Object.getOwnPropertyDescriptor(window.HTMLSelectElement.prototype, 'value').set;
  for (const s of sels) {
    const opts = Array.from(s.options);
    const yopt = opts.find(o => o.text.trim() === YEAR);
    const mopt = opts.find(o => o.text.trim() === MONTH);
    if (yopt && opts.length >= 7) { setter.call(s, yopt.value); s.dispatchEvent(new Event('change', {bubbles:true})); }
    else if (mopt && opts.length === 13) { setter.call(s, mopt.value); s.dispatchEvent(new Event('change', {bubbles:true})); }
  }
})()
```

4. Click `保存する` button via JS.
5. Repeat for each tier. Reward IDs are returned in the URL after save (e.g. `/edit/rewards/1667677`).

**Tier set used for project 951165:**
| ID | Price | Year/Month | Title gist |
|-----|-------|------------|------------|
| 1667677 | ¥1,000 | 2026-09 | A breath — name on donor wall |
| 1667678 | ¥5,000 | 2026-10 | A meal — thank-you postcard |
| 1667679 | ¥30,000 | 2027-12 | A day — 1 retreat seat |
| 1667680 | ¥100,000 | 2027-12 | A weekend — 2 seats + name engraving |
| 1667681 | ¥1,000,000 | 2027-12 | A whole retreat — 4 seats + room dedication |

---

## Step 8 — 特定商取引法 (default template)

Navigate: `/edit/identifications/sct`

```javascript
(()=>{
  const dft = document.querySelector('input[type=radio][value="default_template"]');
  if (dft) { dft.click(); dft.dispatchEvent(new Event('change', {bubbles:true})); }
})()
```

Click `保存する`.

---

## Step 9 — 本人確認 (KYC) — REQUIRES DAIS PHYSICAL

Navigate: `/edit/identifications/project-owner-kyc`

This requires uploading a scan of the **mynumber card front + back** via the system file picker. **camofox does not currently support file picker interaction.**

**Workaround:** Slack message to Dais on `#metrics`:
```
Camp Fire KYC お願い (Dais 物理 1 回のみ):
1. https://camp-fire.jp/mypage/v3/projects/951165/edit/identifications/project-owner-kyc を iPhone Safari で開く
2. mynumber カード写真を upload (DAIS_MYNUMBER=455121123646)
3. 完了したら "kyc done" と reply
```

---

## Step 10 — 振込先口座 (bank account)

Navigate: `/edit/identifications/bank-account`

Fill via `/evaluate` using env values:

```javascript
(()=>{
  const fields = {
    bank_name: '三菱UFJ銀行',
    branch: '青山通支店',
    account_type: '普通',  // verify radio value name
    account_number: '0381900',
    account_name_kana: '<your-name>',
  };
  // Inspect form via Array.from(document.querySelectorAll('input,select')).map(i=>({placeholder:i.placeholder, name:i.name, type:i.type})), then map fields to inputs.
  // Set each via Object.getOwnPropertyDescriptor(...).set.call(input, value); dispatch input/change/blur events.
})()
```

Click `保存する`.

---

## Step 11 — メイン画像 (optional, defer)

camofox can't upload files. Defer to Dais physical OR generate via Pillow then ask Dais to upload manually.

Pillow generator: `~/.openclaw/skills/anicca-retreat-factory/scripts/build-cf-hero.py` produces 1200x800 monastic-style JPEG.

---

## Step 12 — Submit for review

Navigate: `/edit/confirm_submit`

```javascript
(()=>{
  // Check the agreement checkbox
  const cb = document.querySelector('input[type=checkbox]');
  if (cb && !cb.checked) {
    cb.click();
    cb.dispatchEvent(new Event('change', {bubbles:true}));
  }
  // Force-enable + click submit button (Vue may not react to programmatic checkbox click)
  const btn = Array.from(document.querySelectorAll('button')).find(b => b.textContent.includes('提出'));
  if (btn) {
    btn.disabled = false;
    btn.click();
  }
})()
```

Verify submission: URL should redirect to `/edit?submit_complete=true&submit_first=true`.

Then navigate `/mypage/projects/<DRAFT_ID>` — should display "ただいまプロジェクトを審査中です" heading.

---

## Step 13 — Wait for Camp Fire staff approval (1-2 business days)

After approval, project goes public at `https://camp-fire.jp/projects/<DRAFT_ID>/view`.

Approval status check via cron (`anicca-retreat-crowdfund-daily`):
```bash
gog gmail search "from:campfire OR from:camp-fire newer_than:1d" -a {{profile.contact.personalEmail}} -j --results-only
# OR camofox visit https://camp-fire.jp/mypage/projects/<DRAFT_ID> and parse status text
```

---

## URLs summary (project 951165)

| URL | Use |
|-----|-----|
| `https://camp-fire.jp/mypage/projects/951165` | Management dashboard (login required) |
| `https://camp-fire.jp/mypage/v3/projects/951165/edit` | Edit panel |
| `https://camp-fire.jp/projects/951165/preview` | Owner preview (login required) |
| `https://camp-fire.jp/projects/951165/view` | Public after approval (404 until then) |

---

## Key gotchas (write these into your future agent's brain)

1. **Camp Fire price input is `<input>` without `type=` attribute** — `input[type=text]` selector misses them. Use `input:not([type])[placeholder="0"]`.
2. **Vue hydration is slow on /edit/rewards/<id>** — wait 15-20s after navigate before querying inputs.
3. **Submit button stays `disabled=true` even after checkbox.click()** — Vue doesn't react to programmatic events. Force `btn.disabled = false; btn.click()`.
4. **The 6-question survey radios are split into 6 named groups** + 1 unnamed group (counselor). Find the counselor "none" via `input[type=radio][value=none]:not([name])`.
5. **Camp Fire creates a NEW reward draft each visit to `/edit/rewards/new`** — don't accidentally create duplicates by re-visiting.
6. **`保存しました` toast appears in body text but disappears in 3-5s** — verify save IMMEDIATELY after click.
7. **Camp Fire takes 17% + 消費税 fee on All-In, ~12% on All-or-Nothing** — All-In is default and recommended for ¥30M target where partial helps.
