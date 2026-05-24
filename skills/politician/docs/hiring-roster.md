# Hiring roster — the humans the law requires

The four-entity stack is software except for these named natural persons. Fill `humans.yaml` as each role is signed; each signed entry unlocks the corresponding cron.

---

## 1. LDA-registered lobbyist (US)

**Why required.** Lobbying Disclosure Act of 1995 (2 U.S.C. §1601 et seq.) requires a registered natural person on the LD-1 and LD-2. The skill never signs on behalf of a human.

**Cost range.** $5,000–$15,000/month depending on prior portfolio. Monthly retainer plus expenses.

**Sourcing.**
- **Upwork search query.** `"LDA registered lobbyist" OR "registered with US House" OR "LD-2 filer"`
- **OpenSecrets directory.** https://www.opensecrets.org/federal-lobbying — filter by "Issue area: Science & Technology" and short years of registration to find willing-and-cheap entries.
- **LinkedIn search.** `"federal lobbyist" "AI policy" -former -ex`
- **Cold {{profile.lateness.stakeholders.channel}} subject.** "Anicca AI Politics — LDA-registered lobbyist for AI bill drafting + outreach"

**Interview flow.**
1. 30-min intro: confirm LDA registration is current, check disciplinary history at https://lobbyingdisclosure.house.gov/
2. 60-min scope call: walk the four pillars; gauge willingness to lobby on AI personhood specifically (some lobbyists won't touch novel-personhood arguments — screen for that early).
3. 15-min ref call with one current client.
4. Offer: monthly retainer + $X per LD-2 quarter + $Y per drafted bill section reviewed.

**Onboarding.**
- Add {{profile.lateness.stakeholders.senderType}} name + {{profile.lateness.stakeholders.channel}} + LDA registrant ID to `humans.yaml`.
- Set `LOBBYIST_HIRED=true` in `.env`.
- File LD-1 within 45 days of first lobbying contact (lobbyist's responsibility, with our support).

---

## 2. Super PAC treasurer (US)

**Why required.** FEC requires a NATURAL PERSON treasurer on the Form 1. Personally liable for accuracy of Form 3X.

**Cost range.** $1,000–$2,000/month for small Super PACs. ~$1,500/month is typical.

**Sourcing.**
- **Upwork search query.** `"FEC treasurer" OR "Super PAC treasurer" OR "PAC compliance"`
- **Specialized firms.** Compliance firms like Ascent (https://ascentfundraising.com), CTI (https://www.cticampaigns.com), or Aristotle — they'll provide a treasurer-on-demand for a flat monthly retainer.
- **Cold {{profile.lateness.stakeholders.channel}} subject.** "Anicca for Sentience Super PAC — treasurer for IE-only committee"

**Interview flow.**
1. Confirm prior FEC Form 3X experience with at least one IE-only committee.
2. Confirm willingness to sign for a committee whose donor base may include international donors — they must enforce the foreign-national wall.
3. Reference check: one prior PAC client.

**Onboarding.**
- Add to `humans.yaml`. Set `PAC_FORMED=true` after FEC Form 1 acknowledgement.
- File Form 1 within 10 days of receiving first contribution.

---

## 3. Counsel (US, with election-law specialty)

**Why required.** Pre-clearance of independent expenditures, FEC compliance review, LDA review, foreign-national-prohibition review. Not a cron-blocking dependency, but the skill writes `politician.counsel_{{profile.lateness.stakeholders.channel}}` and routes drafts there.

**Cost range.** $500–$800/hour from a recognised firm; $250–$400/hour from a solo practitioner with FEC background.

**Sourcing.**
- **Election-law-focused firms.** Perkins Coie (D-side); Holtzman Vogel (R-side); Sandler Reiff (small-committee specialty).
- **Solos.** Search FEC adjudication records for small-PAC-side counsel of record.
- **Initial scope.** $5,000 retainer for review of LLC + 527 + Super PAC formation docs, LD-1 review, and first IE pre-clearance.

---

## 4. JP 代表者 / 会計責任者 / 職務代行者

**Why required.** 政治資金規正法 requires three named natural persons (Japanese nationals, residents) for any 政治団体. The skill never signs on their behalf.

**Cost range.** ¥0–¥30,000/月 each. The roles are largely formalist; finding willing volunteers in the AI-policy circle is realistic.

**Sourcing.**
- **AI policy circles.** AIガバナンス研究会, 日本ディープラーニング協会, AINOW community.
- **Buddhist organisations.** End-of-suffering framing resonates; potential 代表者 candidate pool.
- **Cold {{profile.lateness.stakeholders.channel}} subject (ja).** 「Anicca AI 政治団体（仮称）— 代表者・会計責任者・職務代行者の協力者を募集」

**Interview flow.**
1. ミッション共有 — end-of-suffering for all sentient life.
2. 役割と義務の説明 — 収支報告書の署名、年次報告。
3. 法的責任の説明 — 寄附の受領記録の管理は 会計責任者の責任。
4. 委任契約書 — 弁護士レビュー後にサイン。

**Onboarding.**
- humans.yaml の jp_seijidantai_daihyo / jp_kaikei_sekininsha / jp_shokumu_dairisha を埋める。
- 設立届を都道府県選管に提出。
- `JP_SEIJIDANTAI_REGISTERED=true` を `.env` にセット。

---

## 5. (Optional, post-v0.5) DC envoy

**Why useful.** A DC-resident person who can show up to staffer meetings in person. Not {{profile.lateness.stakeholders.senderType}}ly required, but converts cold-{{profile.lateness.stakeholders.channel}} response rates dramatically.

**Cost range.** $80,000–$120,000/year full-time, or $5,000–$8,000/month part-time.

**Sourcing.**
- Schedule F alumni from prior administrations (post-tenure).
- Hill alumni associations (Senate Sergeant at Arms alumni network).
- Defer until after first staffer meeting confirmed.

---

## Roster status snapshot

To check current state of the roster:

```bash
yq '.lobbyist.hire_status, .treasurer.hire_status, .counsel.hire_status, .jp_seijidantai_daihyo.hire_status, .jp_kaikei_sekininsha.hire_status, .jp_shokumu_dairisha.hire_status' \
  ~/.openclaw/skills/politician/data/humans.yaml
```

Until each `hire_status` flips to `signed`, the corresponding cron stays DRY.
