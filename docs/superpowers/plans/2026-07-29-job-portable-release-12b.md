# Job Search Portable Release 12B Implementation Plan

> **For agentic workers:** Use Superpowers executing-plans and
> test-driven-development. Keep this plan and the job-search design spec synchronized.

**Goal:** Let a new user author a verified private profile, download one reproducible
release artifact, verify its checksum, and install the loop from that artifact into a
clean HOME.

**Architecture:** Add a profile-authoring module/wrapper that feeds the existing
production validator and writes atomically. Add a Python release builder that reads
one Git tree, normalizes tar metadata, embeds redacted release metadata, and emits a
SHA-256 sidecar. Test the actual extracted artifact through the 12A installer.

**Tech Stack:** Python 3 standard library (`argparse`, `tarfile`, `gzip`, `hashlib`),
zsh, Git, `unittest`.

---

### Task 1: Guided profile authoring

**Files:**
- Create: `apps/job-search-loop/job_search_loop/profile_setup.py`
- Create: `apps/job-search-loop/scripts/setup-profile.sh`
- Create: `apps/job-search-loop/tests/test_profile_setup.py`
- Modify: `apps/job-search-loop/job_search_loop/local_setup.py`
- Modify: `apps/job-search-loop/tests/test_local_setup.py`

- [x] **Step 1: Add RED answers/interactive tests**

  Require production validation, exact input preservation, placeholder rejection,
  mode `0600`, parent mode `0700`, and overwrite refusal.

- [x] **Step 2: Implement the smallest GREEN authoring module**

  Support terminal prompts and `--answers`; never infer legal facts and never read
  another candidate profile.

- [x] **Step 3: Reuse an already-active profile safely**

  Permit the installer to validate and preserve a source profile that is already the
  destination, while retaining the different-source overwrite fence.

- [x] **Step 4: Run focused tests and push**

### Task 2: Reproducible release builder

**Files:**
- Create: `apps/job-search-loop/job_search_loop/release.py`
- Create: `apps/job-search-loop/scripts/build-release.sh`
- Create: `apps/job-search-loop/tests/test_release.py`

- [ ] **Step 1: Add RED archive tests**

  Require deterministic digest, normalized metadata, correct executable modes,
  bounded inventory, release metadata, and SHA-256 sidecar.

- [ ] **Step 2: Implement commit-tree packaging**

  Read tracked blobs and modes from a requested Git tree, sort every entry, normalize
  archive metadata, and refuse dirty/private paths by construction.

- [ ] **Step 3: Verify same-commit reproducibility**

  Build twice into different directories and require byte-identical archives.

### Task 3: Extracted-artifact clean-machine E2E

**Files:**
- Modify: `apps/job-search-loop/tests/test_release.py`
- Modify: `apps/job-search-loop/README.md`

- [ ] **Step 1: Verify checksum and extract**

- [ ] **Step 2: Author a synthetic profile inside a clean root**

- [ ] **Step 3: Run bundled `install-local.sh --scheduler none`**

  Use only the extracted artifact plus fake authenticated Codex and isolated absolute
  XDG roots. Assert private modes and provider receipt.

### Task 4: Full verification, GitHub, and canonical reflection

**Files:**
- Modify: `docs/superpowers/specs/2026-07-28-job-search-loop-design.md`
- Modify: this plan
- Create: `docs/evidence/job-search-loop/2026-07-29-portable-release-12b.json`

- [ ] **Step 1: Run all focused/full/syntax/JSON checks**

- [ ] **Step 2: Record redacted evidence and mark Order 12 locally verified**

- [ ] **Step 3: Push, pass every PR CI gate, and squash merge**

- [ ] **Step 4: Fast-forward canonical checkout and verify live health**
