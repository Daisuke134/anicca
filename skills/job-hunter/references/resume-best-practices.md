# Resume refinement provenance

This reference records the external open-source patterns adopted by the local
Job Hunter skill. It is a design input, not a runtime dependency. Third-party code
is not copied into the production executor without a license and security review.

## Adopted patterns

### `dabydat/resume-builder-skill` — resume-specific writing contract

Repository: <https://github.com/dabydat/resume-builder-skill>

This is the strongest directly resume-specific skill found in the current search.
Its contract requires a full information pass before writing, domain context for
each role, explicit education institutions/degrees/dates, action → technical
context → impact bullets, standard section names, consistent date formatting, and
text-extractable PDF verification. Its bullet-writing reference uses the XYZ/STAR
shape rather than responsibility-only prose.

Local adaptation: keep the private evidence ledger as the only source of claims and
do not copy the repository's sample content or assume its US-only ordering applies
to Japanese documents. Read this reference before changing either the renderer or
the resume-refinement contract.

### `OpenResume` — local-first builder/parser

Project: <https://github.com/yrgajjar/open-resume> · <https://resume.yags.in/>.

OpenResume is useful as an independent ATS readability check because it keeps data
in the browser, supports PDF import/export, and exposes a resume parser. Its built-in
US layout is a reference, not the source of truth for Japanese 履歴書.

### Regional source rules

- **English resume:** MIT Career Advising & Professional Development says to include
  institution, location, degree/major, and completed or expected graduation date;
  study start dates are optional for a normal US resume. Experience entries use
  month/year ranges. Source: <https://capd.mit.edu/resources/career-toolkit-crafting-an-effective-resume/>.
- **Japanese 履歴書 / 職務経歴書:** the Japanese government guide separates 学歴 and
  職歴, avoids abbreviated organization names, uses formal qualification names, and
  describes 職務経歴書 as a concrete A4 1–2 page document. Source:
  <https://www.jinji.go.jp/content/000012264.pdf>.
- **This candidate's concurrent research:** because NAIST study and ATR research
  overlap, the English technical-business variant explicitly shows the attendance
  ranges even though a generic US resume may omit education start dates. This is a
  chronology clarification, not a universal US rule.

### Canonical institution names for this profile

Use the full visible names below; an acronym may appear only after the full name if a
target or parser genuinely needs it. The current application variants use the full
names without acronym-only headings.

- Keio University, Faculty of Law, Department of Political Science
  (<https://www.keio.ac.jp/en/law/>).
- Nara Institute of Science and Technology
  (<https://www.naist.jp/en/academics/>).
- Advanced Telecommunications Research Institute International
  (<https://www.atr.jp/about/ir/CompanyHistory_e.html>).

### `amit-t/skills` — `resume-tailoring`

Repository: <https://github.com/amit-t/skills/tree/main/resume-tailoring>

- Build a reusable resume library/fact bank before matching a job.
- Parse the JD into must-haves, terminology, role archetype, and red flags.
- Score direct, transferable, adjacent, weak, and gap matches.
- Show before/after reframings with a truthfulness note.
- Use approval checkpoints before generating or saving a tailored artifact.

Local adaptation: the private profile and deterministic renderer are the source of
truth; no external resume library is uploaded, and approval is persisted in the
job-search state machine.

### `earino/resumasher`

Repository: <https://github.com/earino/resumasher>

- Mine evidence from the candidate's actual project folder and public work when the
  candidate authorizes that source.
- Produce ATS-safe, single-column PDFs plus a fit/research/prep report.
- Keep scratch data in a run-scoped private directory and fail clearly when setup or
  dependencies are incomplete.

Local adaptation: public repositories are optional evidence, private files stay
local, and the current WeasyPrint/pdftotext verification path remains authoritative.

### `santifer/career-ops`

Repository: <https://github.com/santifer/career-ops>

- Treat the job search as a structured pipeline with a single source of truth.
- Evaluate fit before spending application effort and generate a tailored PDF per
  role.
- Keep the runtime CLI-agnostic while preserving an explicit user approval boundary
  where the product requires it.

Local adaptation: Life Manager owns the durable read projection and Telegram prose;
`apps/job-search-loop` owns browser side effects until skill/loop parity is proven.

## Rejected shortcuts

- Keyword-only rewriting: it hides gaps and encourages unsupported claims.
- One generic resume for every role: it loses role terminology and evidence order.
- Auto-promotion on file generation: a draft is not an approved baseline.
- Visual-only success: a beautiful PDF without selectable ATS text is not accepted.
