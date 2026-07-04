// ci-failure-triage runx runner (deterministic cli-tool).
//
// Reads a CI failure (logs + commit + repo_state) and an escalation policy,
// classifies the failure as one of: flake | infra | real-break | dep, and emits
// a typed runx.ci.triage.v1 packet on stdout. The packet carries exactly one of:
//   - real-break | dep  -> routing decision { recommended_lane, rationale }
//   - flake             -> read-only rerun verdict
//   - infra             -> read-only operator page note
// When the logs cannot support a confident verdict (truncated / empty / no
// decisive signal under the policy threshold) the run REFUSES: it blocks for a
// human lane (needs_agent), emits no routing, and exits non-zero so the runtime
// seals a refusal rather than a closed process.
//
// This skill opens no tracking item, reruns nothing, and pages no one. It only
// produces the classification + the routing decision for a separate downstream
// governed step (issue-intake / issue-to-pr / pr-review-note).
//
// Inputs arrive as RUNX_INPUT_<NAME> environment variables.

const logs = (process.env.RUNX_INPUT_LOGS ?? "").toString();
const commit = (process.env.RUNX_INPUT_COMMIT ?? "").toString().trim();
const repoState = (process.env.RUNX_INPUT_REPO_STATE ?? "").toString().trim();
const minConfidenceRaw = (process.env.RUNX_INPUT_MIN_CONFIDENCE ?? "0.6").toString().trim();
const minConfidence = Number.isFinite(parseFloat(minConfidenceRaw)) ? parseFloat(minConfidenceRaw) : 0.6;

function refuse(reason) {
  process.stderr.write(`needs_agent: ${reason}\n`);
  process.exit(64); // non-zero -> runtime seals a refusal (process_failed)
}

// --- Guardrails: never assert on evidence we do not have. --------------------
const trimmed = logs.trim();
if (trimmed.length === 0) {
  refuse("no logs supplied; cannot classify a CI failure without the failure output");
}
const truncated = /\.\.\.\s*\[?truncated\]?|log truncated|output truncated|\[\.\.\. truncated/i.test(logs)
  || trimmed.length < 40;

// --- Evidence-cited signal extraction (deterministic). -----------------------
const lines = logs.split(/\r?\n/);
const cite = (re) => {
  const hits = [];
  for (let i = 0; i < lines.length; i++) {
    if (re.test(lines[i])) hits.push({ line: i + 1, text: lines[i].trim().slice(0, 200) });
    if (hits.length >= 3) break;
  }
  return hits;
};

const signals = {
  dep: cite(/npm ERR!|yarn error|ECONNREFUSED .*registry|could not resolve dependency|cannot find module|unmet peer dependency|version (conflict|solving failed)|pip (could not find|install failed)|go: .*: unknown revision|lockfile|incompatible versions/i),
  infra: cite(/no space left on device|runner (lost|disconnected|was lost)|the runner has received a shutdown|503 Service|502 Bad Gateway|connection reset by peer|i\/o timeout|docker: .*daemon|could not connect to the docker daemon|oomkilled|killed process|network is unreachable|429 too many requests/i),
  realBreak: cite(/assertion(error)?|expect(ed)?\b.*(but|to (be|equal))|test(s)? failed|✕ |FAIL \b|compilation (error|failed)|cannot find name|type '.*' is not assignable|panic:|segmentation fault|nullpointerexception|syntaxerror|referenceerror|build failed/i),
  flake: cite(/flaky|flake|intermittent|timed out after .* retrying|passed on retry|known.?flaky|nondeterministic|race condition detected|test retry succeeded/i),
};

// --- Classification (precedence + confidence). -------------------------------
// Precedence: infra/dep (environmental) are weighed before real-break so an
// environmental cause is not misread as a code defect; flake only when it is the
// dominant and explicit signal.
let verdict = null;
let evidence = [];
let confidence = 0;

if (signals.flake.length && !signals.realBreak.length && !signals.infra.length && !signals.dep.length) {
  verdict = "flake"; evidence = signals.flake; confidence = 0.7;
} else if (signals.dep.length) {
  verdict = "dep"; evidence = signals.dep; confidence = signals.dep.length >= 2 ? 0.85 : 0.7;
} else if (signals.infra.length && signals.realBreak.length <= signals.infra.length) {
  verdict = "infra"; evidence = signals.infra; confidence = 0.8;
} else if (signals.realBreak.length) {
  verdict = "real-break"; evidence = signals.realBreak; confidence = signals.realBreak.length >= 2 ? 0.9 : 0.72;
}

// Refuse when the evidence is too weak or the logs are truncated.
if (!verdict) {
  refuse("no decisive flake/infra/real-break/dep signal found in the supplied logs");
}
if (truncated && confidence < 0.9) {
  refuse("logs are truncated; remaining evidence cannot support a confident verdict");
}
if (confidence < minConfidence) {
  refuse(`computed confidence ${confidence.toFixed(2)} is below escalation_policy.min_confidence ${minConfidence}`);
}

const evidence_refs = evidence.map((e) => `log:L${e.line}`);

// --- Build exactly one consequence for the verdict. --------------------------
let decision;
if (verdict === "real-break" || verdict === "dep") {
  decision = {
    routing_decision: {
      recommended_lane: "issue-to-pr",
      rationale:
        verdict === "real-break"
          ? `Clear real-break in the supplied logs (${evidence_refs.join(", ")}); route to a downstream issue-intake / issue-to-pr run. This skill opens no item itself.`
          : `Dependency break detected (${evidence_refs.join(", ")}); route to issue-to-pr for a governed dependency fix.`,
    },
  };
} else if (verdict === "flake") {
  decision = {
    rerun_verdict: {
      action: "rerun-readonly",
      rationale: `Flake signal dominant (${evidence_refs.join(", ")}); recommend a read-only rerun. No code change implied.`,
    },
  };
} else {
  decision = {
    page_note: {
      severity: "operator",
      note: `Infrastructure failure (${evidence_refs.join(", ")}); read-only operator page note. Not a code defect.`,
    },
  };
}

const packet = {
  schema: "runx.ci.triage.v1",
  classification: { verdict, confidence: Number(confidence.toFixed(2)), evidence_refs },
  ...decision,
  handoff: {
    seam: "dispatch-by-naming",
    downstream: ["issue-intake", "issue-to-pr", "pr-review-note"],
    note: "Triage only. The downstream run is the separate governed commencement gate.",
  },
  context: { commit: commit || null, repo_state: repoState || null },
};

process.stdout.write(JSON.stringify(packet) + "\n");
