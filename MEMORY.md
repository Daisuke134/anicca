# Operating memory

## Browser-agent architecture

- Before changing an autonomous browser workflow, search in English and Japanese,
  clone multiple active OSS implementations into an isolated temporary directory,
  pin each commit, and read the real entrypoint, call graph, state loop, recovery,
  side-effect boundary, and completion readback. Article summaries and README-only
  research are not sufficient.
- Record what is adopted and rejected against the current production call graph.
  Browser Use contributes the repeated observe/model/action loop and CDP recovery;
  Stagehand contributes accessibility-tree observation and post-action self-heal;
  Skyvern contributes action/screenshot persistence and independent completion
  verification as patterns only because of its AGPL license; fixed ATS scripts and
  guessed defaults are rejected.
- Do not apply Ponytail/minimal-diff pressure when the current architecture assigns
  ownership to the wrong layer. For Job Hunter, repeated fast-path patches are the
  failure class: deterministic code must not own variable forms. Build the complete
  shared browser-agent framework, while reusing the existing CDP owner, runner,
  credential helper, Ledger, Gmail, and Telegram transports as components.
- A framework is complete only after its real hourly owner produces authoritative
  external outcomes. A click, HTTP response, model statement, test, or Ledger state
  alone is never submission proof.
