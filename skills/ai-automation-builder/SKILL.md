---
name: ai-automation-builder
description: Design, implement, verify, and hand over bounded AI-assisted business automations from buyer-supplied workflows and test data; use for custom agents, integrations, browser workflows, and recurring maintenance after a working system exists.
---

# AI Automation Builder

Turn one repeatable buyer workflow into a working, testable automation. The deliverable is the
implemented system plus evidence and operating instructions, not advice, prompts, or an unsupported
claim that AI can automate the work.

## Intake contract

Require before estimating implementation:

- the current trigger, inputs, decisions, outputs, tools, accounts, and approval points;
- redacted representative samples and the expected result for each sample;
- frequency, volume, failure cost, execution environment, and required delivery date;
- which external actions may run automatically and which require buyer approval.

If these facts are missing, deliver a bounded workflow assessment first. Do not promise an
implementation price, completion date, accuracy, savings, or fully autonomous operation from a
verbal description alone.

## Build contract

Choose the smallest implementation that completes one end-to-end workflow. Reuse the buyer's
existing tools and native integrations before adding services or infrastructure. Keep credentials
outside source, logs, screenshots, and deliverables. Fence every external effect with a stable
identity, checkpoint it before execution, and read the provider result back after execution.

The working package includes:

- source and pinned dependencies or a reproducible project package;
- configuration schema with secret values excluded;
- tests using the agreed redacted samples and expected outputs;
- an execution command or deployed entry point;
- retry, duplicate-prevention, failure and human-approval behavior;
- setup, operation, rollback and ownership instructions.

## Acceptance

Demonstrate the agreed workflow from representative input through the real output boundary. Record
the tested environment, artifact hashes, commands, results, unresolved limitations, and any external
readback. A local model response, process ID, dry run, or screenshot without matching artifact and
provider identity is not acceptance.

Reject or rescope work that requires a buyer's voice, attendance, undisclosed identity, regulatory
judgment, physical action, CAPTCHA/3DS bypass, unauthorized account access, or an external effect the
buyer has not approved.

## Recurring maintenance

Offer recurring support only after the base automation passes acceptance. Define a monthly change
budget, monitored workflows, response window, supported dependencies, exclusions, usage/tool costs,
and renewal/termination boundary. Maintenance may repair and improve the accepted system; it does
not silently expand into new workflows or guarantee uninterrupted third-party services.
