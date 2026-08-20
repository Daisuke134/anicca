# Resume refinement provenance

This reference records the external open-source patterns adopted by the local
Job Hunter skill. It is a design input, not a runtime dependency. Third-party code
is not copied into the production executor without a license and security review.

## Adopted patterns

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
