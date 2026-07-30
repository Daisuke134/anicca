# Write for DOnations — Proposal

**Status**: draft, not yet submitted
**Program**: DigitalOcean Write for DOnations (`do.co/w4do`) — $400 per new tutorial, CC BY-NC-SA 4.0, original first-run content only
**Byline policy**: submit under the AI persona (Anicca), never the operator's legal name or personal handles (spec 47 §28.1)

---

## 1. Topic

**How To Block Secrets and Personal Data From an Automated Publishing Pipeline on Ubuntu**

A fail-closed scanner that runs between "content is generated" and "content goes public", wired into a systemd-timer-driven pipeline. The reader ends with a gate that refuses to publish when a secret, an API key, or a personal identifier appears in the payload — and, critically, that also refuses when the gate itself cannot run.

## 2. Why this topic, and who it is for

Anyone running an automated pipeline that pushes content outward — a static site deploy, a scheduled social poster, a docs publisher, a report mailer — eventually leaks something: an API key pasted into a draft, a customer email in a log excerpt, an internal hostname in a screenshot. The usual advice is "review before publishing", which does not survive automation.

The audience is a beginning-to-intermediate developer or sysadmin who already has a scheduled job that publishes something, and who wants a mechanical stop rather than a human review step.

The load-bearing idea, and the reason this is worth a tutorial rather than a snippet: **most naive gates fail open**. If the scanner throws, or the blocklist file is missing, a `try/except` around it quietly lets the payload through — which is exactly the moment you most needed it. This tutorial makes failing closed the default and proves it with a test that sabotages the scanner.

## 3. Prerequisites

- One Ubuntu 24.04 server with a non-root sudo user and a firewall, set up per DigitalOcean's initial server setup guide
- Python 3.10 or newer (default on Ubuntu 24.04)
- Familiarity with running commands over SSH and editing files with `nano`
- An existing script that publishes something on a schedule (the tutorial supplies a small stand-in if the reader does not have one)

## 4. Goal

By the end, the reader has:

- A `pii-gate` command that exits `0` on clean input and a distinct non-zero code for each refusal reason
- That command wired in front of their publish step, so a refusal stops the publish before any network call
- A blocklist stored outside the repository, loaded from the environment
- Tests that prove the three failure modes all block: a match, a missing blocklist, and a scanner that raises

## 5. Outline

### Introduction

Open with the concrete failure: an automated job publishes a draft that contains an API key, and nobody notices until the key is in a search index. Explain that adding a scanner is the easy half; the hard half is guaranteeing it cannot be bypassed by its own failure. State what the reader will build and what they will end up with.

### Prerequisites

List the items from section 3, each linking to the relevant DigitalOcean setup tutorial.

### Step 1 — Setting Up the Project and a Publish Script to Protect

Create a working directory and a minimal `publish.sh` that stands in for the reader's real publisher (it will `curl` a request to a local listener so the reader can watch whether the call happens). This gives the tutorial an observable "did it publish or not" signal in every later step, instead of asking the reader to trust a log line.

### Step 2 — Writing the Detectors

Build the scanner in two halves and explain why they are different kinds of rule. First, patterns that are true regardless of who you are: email addresses, credit-card-shaped digit runs validated with the Luhn checksum to cut false positives, and API-key-shaped high-entropy strings. Second, a blocklist of literals that are specific to the reader — their own domain, their own handle, a customer name. Cover Unicode normalisation so that full-width or composed characters cannot slip a literal past a naive `in` check.

### Step 3 — Keeping the Blocklist Out of the Repository

Explain the trap: the blocklist is itself sensitive, so committing it to the repo leaks exactly what it protects. Load it from an environment variable or a file path given by one, store the real file with `chmod 600` outside the working tree, and make the loader raise a distinct error when neither is configured.

### Step 4 — Making the Gate Fail Closed

The core step. Show the naive version first — a `try/except` that logs and continues — and demonstrate it letting a payload through when the scanner raises. Then rewrite it so that a finding, a missing blocklist, and any unexpected exception all end in a refusal with a distinct exit code. Emphasise the rule: there must be no branch in which an exception reaches the publish call.

### Step 5 — Wiring the Gate Into the Publish Step

Call the gate from `publish.sh` before the network call, using the exit code to decide. Show the output for each case: clean payload publishes, dirty payload stops with the matched rule ids, and the matched values appear only in redacted form so the log itself does not become the leak.

### Step 6 — Running It on a Schedule With a systemd Timer

Write the service and timer units, enable them, and confirm with `systemctl list-timers` and `journalctl`. Explain why the environment that a timer-spawned unit sees is not the reader's login shell, which is the most common reason a gate that worked by hand refuses in production — and show `EnvironmentFile=` as the fix.

### Step 7 — Proving the Gate Cannot Be Bypassed

Three tests the reader runs themselves: a payload containing a blocklisted literal, a run with the blocklist unset, and a run with a deliberately broken scanner. All three must block. Explain that passing the first test alone is the mistake most people make.

### Conclusion

Recap what was built, name the residual gaps honestly — a gate on the payload does not cover text that a downstream tool generates after the gate runs — and point to where the reader would extend it next.

## 6. Writing sample

To attach: one previously published technical article demonstrating step-by-step explanation for readers unfamiliar with the topic. Must be selected from articles that pass the identity gate (no operator handle, no location).

## 7. Verification status of the material

Every mechanism in this outline exists in a system I run, not in a hypothetical. The fail-closed gate, the distinct exit codes, the environment-loaded blocklist, and the sabotage test were built and measured on 2026-07-30/31: 41 unit tests passing, the failure set identical to the pre-change baseline, and the gate observed blocking a real artifact that carried an identifier. The tutorial rewrites that work as a from-scratch Ubuntu walkthrough — it does not reuse the article text, so the submission remains first-run content.
