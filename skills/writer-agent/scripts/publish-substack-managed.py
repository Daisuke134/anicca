#!/usr/bin/env python3
"""Publish one persisted paid Substack draft without a general model."""
import json, os, shlex, subprocess
from pathlib import Path
# --- fail-closed PII gate wiring ---------------------------------------------------
# gate_* raise SystemExit (non-zero) on a finding, a missing blocklist, an unreadable
# artifact, or ANY scanner error. There is no code path where a failure means publish.
import sys as _pii_sys  # noqa: E402
from pathlib import Path as _PiiPath  # noqa: E402
_pii_sys.path.insert(0, str(next(
    _p / "_shared"
    for _p in _PiiPath(__file__).resolve().parents
    if (_p / "_shared" / "pii_gate.py").is_file()
)))
from pii_gate import gate_files, gate_run_dir, gate_text  # noqa: E402,F401


def run(argv, env=None):
    r=subprocess.run(argv,env=env,text=True,capture_output=True,check=False)
    if r.returncode: raise SystemExit(r.stderr or r.stdout)
    return r.stdout

def main():
    pair=os.environ["ARTICLE_PUBLISH_PAIR"]
    if pair not in {"substack/ja","substack/en"}: raise SystemExit("invalid pair")
    lang=pair.split("/", 1)[1]
    publication_key=f"SUBSTACK_PUBLICATION_{lang.upper()}"
    publication=os.environ.get(publication_key, "").strip().lower()
    if not publication:
        raise SystemExit(f"{publication_key} is required; refusing implicit Substack identity")
    if lang == "en":
        japanese_publication=os.environ.get("SUBSTACK_PUBLICATION_JA", "").strip().lower()
        if not japanese_publication:
            raise SystemExit("SUBSTACK_PUBLICATION_JA is required before English publication")
        if publication == japanese_publication:
            raise SystemExit("English Substack publication must be distinct from Japanese publication")
    cookie_key=f"SUBSTACK_SESSION_COOKIE_{lang.upper()}"
    session_cookie=os.environ.get(cookie_key, "").strip()
    if not session_cookie and lang == "ja":
        session_cookie=os.environ.get("SUBSTACK_SESSION_COOKIE", "").strip()
    if not session_cookie:
        raise SystemExit(f"{cookie_key} is required for managed Substack publication")
    state_path=Path(os.environ["ARTICLE_PUBLICATION_STATE"]); state=json.loads(state_path.read_text())
    expected_identity=str(state.get("destination_identities", {}).get(pair, "")).strip().lower()
    if not expected_identity or expected_identity != publication:
        raise SystemExit(f"Substack identity does not match persisted state for {pair}")
    entry=state.get("pairs",{}).get(pair,{})
    if entry.get("status")!="intent" or not str(entry.get("target","")).isdigit(): raise SystemExit("durable Substack intent missing")
    rows=[json.loads(x) for x in (Path(os.environ["ARTICLE_RUN_DIR"])/"gates/platform-dispatch.jsonl").read_text().splitlines() if x]
    # The canonical dispatch ledger stores the platform as ``substack`` and
    # carries the locale in ``lang``.  Keep accepting the older channel-shaped
    # spelling so immutable runs created before the Mr.bot move remain
    # resumable without rewriting their receipts.
    rows=[x for x in rows if x.get("platform") in {"substack", f"substack-{lang}"} and x.get("lang")==lang]
    if len(rows)!=1: raise SystemExit("persisted Substack row missing")
    argv=rows[0]["argv"]
    def value(flag):
        return argv[argv.index(flag)+1]
    wrapper=shlex.split(os.environ.get("SUBSTACK_WRAPPER_COMMAND","")) or ["bash",str(Path(__file__).parent/"_shared/publish-substack-mermaid.sh")]
    refresh=shlex.split(os.environ.get("SUBSTACK_REFRESH_COMMAND","")) or ["python3",str(Path(__file__).parent/"substack-publish/substack_refresh_intent.py")]
    env={
        **os.environ,
        "SUBSTACK_MODE":"go",
        "SUBSTACK_PUBLICATION":publication,
        "SUBSTACK_SESSION_COOKIE":session_cookie,
        # The wrapper is also callable outside this managed entrypoint. Pass
        # the pair-specific identity explicitly so it cannot fall back to the
        # legacy generic host after the refresh gate has passed.
        publication_key: publication,
    }
    gate_files("publish-substack-managed", [value("--markdown-file")])
    run([*refresh,"--pair",pair],env)
    run([*wrapper,"enable-publish"],env)
    try:
        out=run([*wrapper,"publish",value("--markdown-file"),"--title",value("--title"),"--subtitle",value("--meta"),"--mode","go"],env)
    finally:
        run([*wrapper,"disable-publish"],env)
    if json.loads(state_path.read_text())["pairs"][pair].get("status")!="live": raise SystemExit("Substack live receipt missing")
    print(out,end="")
    return 0
if __name__=="__main__": raise SystemExit(main())
