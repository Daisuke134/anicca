import json
import os
import subprocess
from pathlib import Path


MODULE = Path(__file__).resolve().parent / "semantic-reply.ts"


def test_semantic_reply_uses_canonical_runner_and_reads_result(tmp_path):
    runner = tmp_path / "runner.py"
    calls = tmp_path / "calls.json"
    runner.write_text(
        "import json,pathlib,sys\n"
        f"pathlib.Path({str(calls)!r}).write_text(json.dumps(sys.argv[1:]))\n"
        "a=sys.argv; e=pathlib.Path(a[a.index('--evidence-dir')+1]); e.mkdir(parents=True)\n"
        "r=e/'result.json'; r.write_text(json.dumps({'action':'reply','reply':'hello'}))\n"
        "(e/'summary.json').write_text(json.dumps({'result_path':str(r)}))\n"
    )
    script = (
        f"import {{ semanticDecision }} from {json.dumps(MODULE.as_uri())};"
        "console.log(JSON.stringify(semanticDecision('agentmail-replier','reply safely')));"
    )
    result = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        env={
            **os.environ,
            "AGENT_RUNNER_BIN": str(runner),
            "AGENTMAIL_SEMANTIC_STATE_DIR": str(tmp_path / "evidence"),
        },
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {"action": "reply", "reply": "hello"}
    argv = json.loads(calls.read_text())
    assert argv[argv.index("--task-class") + 1] == "reply-semantic-agent"
    assert "--read-only" in argv


def test_replier_ignores_automated_mail_without_direct_provider_key(tmp_path):
    database = tmp_path / "agentmail.db"
    schema = Path(__file__).resolve().parent / "state-schema.sql"
    subprocess.run(["sqlite3", str(database)], input=schema.read_text(), text=True, check=True)
    subprocess.run(
        ["sqlite3", str(database)], input=(
            "INSERT INTO inbox_threads(id,address,subject,last_message_at) VALUES"
            "('t1','agent@example.com','code','2026-08-28T00:00:00Z');"
            "INSERT INTO inbox_messages(id,thread_id,direction,sent_at,from_addr,subject,body) VALUES"
            "('m1','t1','inbound','2026-08-28T00:00:00Z','no-reply@example.com','code','123456');"
        ), text=True, check=True)
    runner = tmp_path / "runner.py"
    runner.write_text(
        "import json,pathlib,sys\n"
        "a=sys.argv; e=pathlib.Path(a[a.index('--evidence-dir')+1]); e.mkdir(parents=True)\n"
        "r=e/'result.json'; r.write_text(json.dumps({'action':'ignore','reply':None}))\n"
        "(e/'summary.json').write_text(json.dumps({'result_path':str(r)}))\n"
    )
    adapter = tmp_path / "send.sh"
    adapter.write_text("#!/bin/sh\nexit 99\n")
    adapter.chmod(0o755)

    result = subprocess.run(
        ["node", str(Path(__file__).resolve().parent / "replier.ts")],
        env={
            **os.environ,
            "HOME": str(tmp_path),
            "AGENTMAIL_DB_PATH": str(database),
            "AGENTMAIL_API_KEY": "test-only",
            "AGENTMAIL_ADAPTER_SEND_SH": str(adapter),
            "AGENT_RUNNER_BIN": str(runner),
            "AGENTMAIL_SEMANTIC_STATE_DIR": str(tmp_path / "evidence"),
        },
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "pending: 1" in result.stdout
    assert "ignored" in result.stdout
    evidence_count = len(list((tmp_path / "evidence").iterdir()))
    replay = subprocess.run(
        ["node", str(Path(__file__).resolve().parent / "replier.ts")],
        env={
            **os.environ,
            "HOME": str(tmp_path), "AGENTMAIL_DB_PATH": str(database),
            "AGENTMAIL_API_KEY": "test-only", "AGENTMAIL_ADAPTER_SEND_SH": str(adapter),
            "AGENT_RUNNER_BIN": str(runner),
            "AGENTMAIL_SEMANTIC_STATE_DIR": str(tmp_path / "evidence"),
        }, capture_output=True, text=True, check=False)
    assert replay.returncode == 0, replay.stderr
    assert "pending: 0" in replay.stdout
    assert len(list((tmp_path / "evidence").iterdir())) == evidence_count


def test_nudge_uses_semantic_runner_without_direct_provider_key(tmp_path):
    database = tmp_path / "agentmail.db"
    schema = Path(__file__).resolve().parent / "state-schema.sql"
    subprocess.run(["sqlite3", str(database)], input=schema.read_text(), text=True, check=True)
    subprocess.run(
        ["sqlite3", str(database)], input=(
            "INSERT INTO inbox_threads(id,address,subject,last_message_at) VALUES"
            "('t1','agent@example.com','hello','2026-01-01T00:00:00Z');"
            "INSERT INTO inbox_messages(id,thread_id,direction,sent_at,to_addr,subject,body) VALUES"
            "('m1','t1','outbound','2026-01-01T00:00:00Z','human@example.com','hello','hi');"
            "INSERT INTO awaiting_reply(thread_id,sent_at) VALUES('t1','2026-01-01T00:00:00Z');"
        ), text=True, check=True)
    runner = tmp_path / "runner.py"
    runner.write_text(
        "import json,pathlib,sys\n"
        "a=sys.argv; e=pathlib.Path(a[a.index('--evidence-dir')+1]); e.mkdir(parents=True)\n"
        "r=e/'result.json'; r.write_text(json.dumps({'action':'ignore','reply':None}))\n"
        "(e/'summary.json').write_text(json.dumps({'result_path':str(r)}))\n"
    )
    adapter = tmp_path / "send.sh"
    adapter.write_text("#!/bin/sh\nexit 99\n")
    adapter.chmod(0o755)
    result = subprocess.run(
        ["node", str(Path(__file__).resolve().parent / "nudge.ts")],
        env={
            **os.environ,
            "HOME": str(tmp_path),
            "AGENTMAIL_DB_PATH": str(database),
            "AGENTMAIL_API_KEY": "test-only",
            "AGENTMAIL_ADAPTER_SEND_SH": str(adapter),
            "AGENT_RUNNER_BIN": str(runner),
            "AGENTMAIL_SEMANTIC_STATE_DIR": str(tmp_path / "evidence"),
        },
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "eligible nudges: 1" in result.stdout
    assert "ignored" in result.stdout
