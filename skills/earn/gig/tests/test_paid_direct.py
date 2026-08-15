import ast
import hashlib
import json
import os
import shutil
import sqlite3
import stat
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "paid_direct.py"


def put(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False) + "\n", encoding="utf-8")


def official_content_sha256(side, sent_at, text, attachments=None):
    canonical = {
        "side": side,
        "sent_at": sent_at,
        "text": str(text or ""),
        "attachments": attachments or [],
    }
    return hashlib.sha256(json.dumps(
        canonical, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")).hexdigest()


def exe(path, source):
    path.write_text("#!/usr/bin/env python3\n" + source, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return path


def case(tmp_path, stale=False, fail_targeted=None, invalid_remote=False, existing_answer=False):
    feedback, room, request, answer = "a" * 64, "90000101", "recoverable-request", "更新を確認しました。"
    target, desired = "https://example.test/item", {"title": "updated", "enabled": True}
    digest = hashlib.sha256(json.dumps(desired, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    statement = {"text": "既存要件", "attachments": []}
    statement_sha256 = hashlib.sha256(json.dumps(statement, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    accumulated_sha256 = hashlib.sha256(json.dumps([statement_sha256], ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
    requirements_sha256 = accumulated_sha256
    message_sha256 = hashlib.sha256(answer.encode()).hexdigest()
    projects, project = tmp_path / "projects", tmp_path / "projects" / request
    (project / "delivery").mkdir(parents=True); (project / "evidence").mkdir(); (project / "requirements").mkdir()
    (project / "source/talkroom").mkdir(parents=True)
    put(project / "state.json", {"request_id": request, "talkroom_id": room})
    put(project / "requirements/live-buyer-reply.json", {"version": 1, "feedback_sha256": feedback,
        "accumulated_requirements": [{**statement, "sha256": statement_sha256}],
        "accumulated_sha256": accumulated_sha256})
    before, after = project / "evidence/before.json", project / "evidence/after.json"
    put(before, {"target": target, "authenticated": True, "state": "old", "requirements_sha256": requirements_sha256,
                 "message_sha256": message_sha256})
    put(after, {"target": target, "authenticated": True, "observed_state": desired, "requirements_sha256": requirements_sha256,
                "message_sha256": message_sha256})
    put(project / "delivery/paid-remote-intent.json", {"version": 1, "buyer_feedback_sha256": feedback,
        "target": target, "desired_state": desired, "desired_state_sha256": digest, "requirements_sha256": requirements_sha256,
        "message_sha256": message_sha256})
    put(project / "delivery/paid-remote-result.json", {"version": 1, "status": "ok", "buyer_feedback_sha256": feedback,
        "target": target, "observed_state": desired, "after_state_digest": digest, "verified_after": True,
        "before_evidence": str(before), "after_evidence": str(after), "customer_message": answer,
        "requirements_sha256": requirements_sha256, "message_sha256": message_sha256})
    put(project / "delivery/paid-answer.json", {"version": 1, "status": "answer", "message": answer,
        "requirements_sha256": requirements_sha256, "message_sha256": message_sha256})
    talkroom_message = {
        "version": 1, "source": "coconala_live_talkroom", "talkroom_id": room,
        "message_id": "seller-message-1", "observed_at": "2026-08-12T00:00:00+00:00",
        "side": "seller", "sent_at": "2026-08-12T00:00:00+00:00", "text": answer,
        "attachments": [],
    }
    talkroom_message["content_sha256"] = official_content_sha256(
        talkroom_message["side"], talkroom_message["sent_at"],
        talkroom_message["text"], talkroom_message["attachments"],
    )
    (project / "source/talkroom/messages.jsonl").write_text(
        json.dumps(talkroom_message, ensure_ascii=False) + "\n", encoding="utf-8")
    key = hashlib.sha256(f"{feedback}:{target}:{digest}".encode()).hexdigest()
    (project / "events.jsonl").write_text(json.dumps({"kind": "live_system_delivery_recorded", "key": key,
        "buyer_feedback_sha256": feedback, "target": target, "result_digest": digest, "verified_after": True,
        "requirements_sha256": requirements_sha256, "message_sha256": message_sha256}) + "\n", encoding="utf-8")
    if invalid_remote:
        (project / "events.jsonl").write_text("[]\n", encoding="utf-8")
    verify = project / "evidence/agent-PAID_REMOTE_VERIFY"
    put(verify / "before.json", {"target": target, "authenticated": True, "observed_state": desired,
                                  "requirements_sha256": requirements_sha256, "message_sha256": message_sha256})
    put(verify / "after.json", {"target": target, "authenticated": True, "observed_state": desired,
                                 "requirements_sha256": requirements_sha256, "message_sha256": message_sha256})
    put(verify / "remote-verifier-result.json", {"version": 1, "verified": True, "buyer_feedback_sha256": feedback,
        "target": target, "desired_digest": digest, "observed_state": desired, "observed_digest": digest,
        "before_evidence": "before.json", "after_evidence": "after.json", "requirements_sha256": requirements_sha256,
        "message_sha256": message_sha256})
    put(verify / "runner-result.json", {"status": "ok"})
    put(verify / "summary.json", {"version": 1, "status": "success", "task_label": "paid-remote-verifier",
        "task_class": "escalation-agent", "escalated": True, "selected_provider": "codex",
        "selected_model": "gpt-5.6-sol", "result_path": str(verify / "runner-result.json")})
    base = {"request_id": request, "contract_id": f"talkroom:{room}", "talkroom_id": room, "buyer": "buyer-one",
            "title": "paid work", "price_jpy": 12000, "price_source": "structured_order_label", "delivery_date": "2026-08-12",
            "status": "paid", "marketplace_url": f"https://coconala.com/talkrooms/{room}", "buyer_feedback_sha256": feedback,
            "talkroom_state": "取引中"}
    pending = {**base, "request_id": "not-recoverable", "talkroom_id": "90000102", "contract_id": "talkroom:90000102",
               "marketplace_url": "https://coconala.com/talkrooms/90000102", "buyer_feedback_sha256": "c" * 64,
               "delivery_date": "2026-08-13", "status": "unknown"}
    preliminary = {key: value for key, value in base.items() if key not in {"request_id", "buyer_feedback_sha256"}}
    pending_preliminary = {key: value for key, value in pending.items() if key not in {"request_id", "buyer_feedback_sha256"}}
    orders = {"source": "authenticated_coconala_hidden_default_context_dom", "read_only": True,
              "captured_at": "2026-08-12T00:00:00+00:00", "collector_mode": "orders-only", "observed_sources": ["orders"],
              "open_orders_list_observed": True, "orders": [base, pending], "source_receipt": {
                  "source": "orders", "requested_route": "https://coconala.com/mypage/received_orders/open",
                  "final_route": "https://coconala.com/mypage/received_orders/open", "login_redirect": False,
                  "cards_count": 2, "empty_state_present": False, "coverage_complete": True}}
    def selected(row, selected_feedback, seller_message=False):
        seller = [{"text": answer, "text_sha256": hashlib.sha256(answer.encode()).hexdigest()}] if seller_message else []
        live = tmp_path / f"talkroom-{row['talkroom_id']}.json"
        put(live, {"talkroom_id": row["talkroom_id"], "buyer_feedback_sha256": selected_feedback})
        return {"collector_mode": "selected-talkroom-only", "talkroom_id": row["talkroom_id"], "talkroom": {
            "talkroom_id": row["talkroom_id"], "transaction_state": "取引中", "formal_delivery_confirmed": False,
            "buyer_feedback_sha256": selected_feedback, "seller_sent_messages": seller}, "orders": [{
                **row, "selection_stage": "targeted", "targeted_readback_required": False,
                "talkroom_evidence_file": str(live), "talkroom_observed_at": "2026-08-12T00:00:00+00:00",
                "buyer_feedback_sha256": selected_feedback, "formal_delivery_observed": False,
                "seller_sent_messages": seller}]}
    snapshot = tmp_path / "orders.json"
    put(snapshot, {**orders, "orders": [preliminary, pending_preliminary]})
    for row in (base, pending):
        put(tmp_path / f"targeted-{row['talkroom_id']}.json", selected(row, row["buyer_feedback_sha256"]))
        put(tmp_path / f"fresh-{row['talkroom_id']}.json", selected(row, "b" * 64 if stale and row is base else row["buyer_feedback_sha256"], existing_answer and row is base))
        put(tmp_path / f"repair-{row['talkroom_id']}.json", selected(row, row["buyer_feedback_sha256"], existing_answer and row is base))
        put(tmp_path / f"presend-{row['talkroom_id']}.json", selected(row, row["buyer_feedback_sha256"], existing_answer and row is base))
        put(tmp_path / f"official-{row['talkroom_id']}.json", selected(row, row["buyer_feedback_sha256"], True))
    collector = exe(tmp_path / "collector.py", """
import json, os, sys
from pathlib import Path
a = dict(zip(sys.argv[1::2], sys.argv[2::2])); mode = a['--mode']; room = a.get('--talkroom-id')
if mode == 'orders-only': src = os.environ['ORDERS_SNAPSHOT']
else:
    targeted = 'paid-direct/targeted' in a['--output']; presend = Path(a['--output']).parent.name == 'presend'; official = 'official-readback' in a['--output']; repair = 'remote-repair-readback' in a['--output']
    kind = 'targeted' if targeted else 'presend' if presend else 'official' if official else 'repair' if repair else 'fresh'
    src = os.environ[kind.upper() + '_' + room]
    if os.getenv('HELD_LOG'): open(os.environ['HELD_LOG'], 'a').write(kind + ':' + os.getenv('GIG_CDP_LOCK_HELD', '0') + '\\n')
    if targeted and room == os.getenv('FAIL_TARGETED_ROOM'): raise SystemExit(1)
    if kind == 'presend' and os.getenv('MUTATE_ANSWER'):
        Path(os.environ['MUTATE_ANSWER']).write_text(json.dumps({'version': 1, 'status': 'answer', 'message': '改ざんされた回答'}), encoding='utf-8')
    if kind == 'presend' and os.getenv('MUTATE_REQUIREMENTS'):
        requirements = Path(os.environ['MUTATE_REQUIREMENTS'])
        payload = json.loads(requirements.read_text())
        payload['accumulated_sha256'] = 'e' * 64
        requirements.write_text(json.dumps(payload))
    if kind == 'presend' and os.getenv('MUTATE_ATTACHMENT'):
        Path(os.environ['MUTATE_ATTACHMENT']).write_bytes(b'changed-after-review')
    open(os.environ['TARGET_LOG'], 'a').write(kind + ':' + room + '\\n')
os.makedirs(a['--evidence-dir'], exist_ok=True)
open(a['--output'], 'w').write(open(src).read())
""")
    wrapper = exe(tmp_path / "lock-wrapper.py", """
import os, shutil, subprocess, sys
from pathlib import Path
i = sys.argv.index('--'); env = os.environ.copy(); env['GIG_CDP_LOCK_HELD'] = '1'
if os.getenv('CDP_LOCK_DIR_LOG'): open(os.environ['CDP_LOCK_DIR_LOG'], 'a').write(os.getenv('CDP_LOCK_DIR', '<missing>') + '\\n')
if os.getenv('CDP_ACQUIRE_LOG'): open(os.environ['CDP_ACQUIRE_LOG'], 'a').write(('nested' if os.getenv('GIG_CDP_LOCK_HELD') == '1' else 'acquired') + '\\n')
if os.getenv('BUSY_EFFECT') and sys.argv[1].startswith('paid-direct-'): raise SystemExit(75)
lock = Path(os.environ['CDP_LOCK_DIR']); lock.mkdir(parents=True, exist_ok=True)
(lock / 'meta').write_text(sys.argv[1] + ' 1\\n', encoding='utf-8')
try:
    raise SystemExit(subprocess.run(sys.argv[i + 1:], env=env).returncode)
finally:
    shutil.rmtree(lock, ignore_errors=True)
""")
    browser = exe(tmp_path / "answer-browser.py", """
import hashlib, json, os, sys
from pathlib import Path
if '--queue-item' in sys.argv and '--manifest' in sys.argv:
    queue = json.loads(Path(sys.argv[sys.argv.index('--queue-item') + 1]).read_text())
    manifest = json.loads(Path(sys.argv[sys.argv.index('--manifest') + 1]).read_text())
    evidence = Path(sys.argv[sys.argv.index('--evidence-dir') + 1]); evidence.mkdir(parents=True, exist_ok=True)
    artifact = Path(manifest['artifact_path']); room = str(queue['talkroom_id'])
    binding = f"添付: {artifact.name}（{manifest['artifact_version']}）"
    message = queue['progress_payload']['message'] + '\\n\\n' + binding
    shot = evidence / 'post.png'; shot.write_bytes(b'png')
    live = evidence / 'post.json'; live.write_text(json.dumps({'url': queue['marketplace_url'], 'sent': True,
        'formal_delivery_checkbox': False, 'latest_seller_attachment': {'filename': artifact.name,
        'size_bytes': artifact.stat().st_size, 'message': message}}))
    (evidence / 'paid-queue-evidence.json').write_text(json.dumps({'sent': True, 'send_performed': True,
        'deduplicated': False, 'formal_delivery_checkbox': False, 'captured_at': '2026-08-12T01:00:00Z',
        'talkroom_id': room, 'artifact_basename': artifact.name, 'artifact_version': manifest['artifact_version'],
        'package_sha256': manifest['package_sha256'], 'acceptance_delta': manifest['acceptance_delta'],
        'screenshot_path': str(shot), 'live_dom_path': str(live)}))
    official = Path(os.environ['OFFICIAL_' + room]); snapshot = json.loads(official.read_text())
    seller = [{'text': message, 'text_sha256': hashlib.sha256(message.encode()).hexdigest(), 'attachments': [artifact.name]}]
    snapshot['talkroom']['seller_sent_messages'] = seller; snapshot['orders'][0]['seller_sent_messages'] = seller
    official.write_text(json.dumps(snapshot))
    print(json.dumps({'ok': True, 'evidence': {'sent': True, 'send_performed': True,
        'deduplicated': False, 'formal_delivery_checkbox': False}})); raise SystemExit(0)
if os.getenv('ANSWER_COUNT'): open(os.environ['ANSWER_COUNT'], 'a').write('1\\n')
if os.getenv('HELD_LOG'): open(os.environ['HELD_LOG'], 'a').write('browser:' + os.getenv('GIG_CDP_LOCK_HELD', '0') + '\\n')
if os.getenv('ANSWER_MESSAGE_LOG'):
    answer_path = sys.argv[sys.argv.index('--answer-file') + 1]
    with open(answer_path, encoding='utf-8') as answer_file:
        answer = json.load(answer_file)
    with open(os.environ['ANSWER_MESSAGE_LOG'], 'a', encoding='utf-8') as message_file:
        message_file.write(answer['message'] + '\\n')
if os.getenv('ANSWER_PAYLOAD_LOG'):
    answer_path = sys.argv[sys.argv.index('--answer-file') + 1]
    open(os.environ['ANSWER_PAYLOAD_LOG'], 'w').write(open(answer_path).read())
print(json.dumps({'ok': True, 'evidence': {'sent': True, 'mode': 'answer', 'send_performed': os.getenv('ANSWER_SEND_PERFORMED') == '1', 'deduplicated': True, 'formal_delivery_checkbox': False}}))
""")
    runner = exe(tmp_path / "safe-runner.py", """
import json, os, sys
from pathlib import Path
argv, args, index = sys.argv[1:], {}, 0
while index < len(argv):
    if argv[index] == '--read-only': index += 1; continue
    args[argv[index]] = argv[index + 1]; index += 2
role = args['--task-label']
evidence = Path(args['--evidence-dir'])
evidence.mkdir(parents=True, exist_ok=True)
if os.getenv('RUNNER_LOG'): open(os.environ['RUNNER_LOG'], 'a').write(role + '\\n')
result = evidence / 'runner-result.json'
if role == 'paid-work-decision':
    root = Path(args['--workdir'])
    requirements = json.loads((root / 'requirements/live-buyer-reply.json').read_text())
    identity = json.loads((root / 'source/talkroom/messages.jsonl').read_text().splitlines()[-1])
    result.write_text(json.dumps({
        'decision': 'actionable', 'mode': 'remote',
        'feedback_sha256': requirements['feedback_sha256'],
        'requirements_sha256': requirements['accumulated_sha256'],
        'latest_message_identity': {
            'message_id': identity['message_id'], 'content_sha256': identity['content_sha256'],
            'side': identity['side'],
        },
        'required_output': 'verified buyer-owned system update and buyer reply',
        'required_effect': 'authenticated external-system mutation',
        'delivery_stage': 'none',
        'formal_approval_evidence': None,
        'unresolved': [],
    }))
elif role == 'paid-work-mode':
    result.write_text(json.dumps({'status': 'ok', 'summary': 'answer', 'evidence': ['fixture']}))
elif role == 'paid-remote-verifier':
    root = Path(args['--workdir'])
    delivery = root / 'delivery'
    intent = json.loads((delivery / 'paid-remote-intent.json').read_text())
    remote = json.loads((delivery / 'paid-remote-result.json').read_text())
    requirements = json.loads((root / 'requirements/live-buyer-reply.json').read_text())['accumulated_sha256']
    message_sha = remote['message_sha256']
    (evidence / 'before.json').write_text(json.dumps({
        'target': intent['target'], 'authenticated': True, 'observed_state': intent['desired_state'],
        'requirements_sha256': requirements, 'message_sha256': message_sha,
    }))
    (evidence / 'after.json').write_text((evidence / 'before.json').read_text())
    verified = {
        'verified': True, 'buyer_feedback_sha256': intent['buyer_feedback_sha256'],
        'target': intent['target'], 'desired_digest': intent['desired_state_sha256'],
        'observed_digest': intent['desired_state_sha256'], 'observed_state': intent['desired_state'],
        'before_evidence': 'before.json', 'after_evidence': 'after.json',
        'requirements_sha256': requirements, 'message_sha256': message_sha,
    }
    (evidence / 'remote-verifier-result.json').write_text(json.dumps(verified))
    result.write_text(json.dumps({'status': 'ok'}))
else:
    raise SystemExit(1)
(evidence / 'summary.json').write_text(json.dumps({
    'version': 1, 'status': 'success', 'task_label': role, 'task_class': args['--task-class'],
    'escalated': role in ('paid-work-decision', 'paid-remote-verifier'), 'selected_provider': 'codex',
    'selected_model': 'gpt-5.6-sol',
    'result_path': str(result),
}))
""")
    output, evidence = tmp_path / "result.json", tmp_path / "evidence"
    env = {**os.environ, "ORDERS_SNAPSHOT": str(snapshot), "TARGETED_90000101": str(tmp_path / "targeted-90000101.json"),
           "TARGETED_90000102": str(tmp_path / "targeted-90000102.json"), "FRESH_90000101": str(tmp_path / "fresh-90000101.json"),
           "FRESH_90000102": str(tmp_path / "fresh-90000102.json"), "REPAIR_90000101": str(tmp_path / "repair-90000101.json"),
           "REPAIR_90000102": str(tmp_path / "repair-90000102.json"), "OFFICIAL_90000101": str(tmp_path / "official-90000101.json"),
           "OFFICIAL_90000102": str(tmp_path / "official-90000102.json"), "PRESEND_90000101": str(tmp_path / "presend-90000101.json"),
           "PRESEND_90000102": str(tmp_path / "presend-90000102.json"), "TARGET_LOG": str(tmp_path / "target-log"),
           "ANSWER_COUNT": str(tmp_path / "answer-count"), "ANSWER_SEND_PERFORMED": "0", "FAIL_TARGETED_ROOM": fail_targeted or ""}
    openclaw = exe(tmp_path / "openclaw", """
import json
print(json.dumps({'messageId': 'paid-wake-1', 'payload': {'ok': True}}))
""")
    args = [sys.executable, str(SCRIPT), "--output", str(output), "--evidence-dir", str(evidence), "--projects-root", str(projects),
            "--collector", str(collector), "--run-with-cdp-lock", str(wrapper), "--answer-browser", str(browser),
            "--cdp-helper", str(tmp_path / "helper.py"), "--lock-file", str(tmp_path / "lock"), "--cdp-lock-dir", str(tmp_path / "cdp-lock"), "--today", "2026-08-12",
            "--telegram-database", str(tmp_path / "telegram.sqlite3"),
            "--telegram-receipt-dir", str(tmp_path / "receipts"),
            "--openclaw", str(openclaw), "--telegram-target", "123",
            "--agent-runner", str(runner)]
    effect_item = tmp_path / "effect-item.json"; put(effect_item, base)
    return output, env, args, tmp_path / "answer-count", effect_item


def test_paid_direct_normal_wake_passes_explicit_shared_cdp_lock_dir(tmp_path):
    output, env, args, _, _ = case(tmp_path)
    lock_flag = args.index("--cdp-lock-dir")
    del args[lock_flag:lock_flag + 2]
    lock_log = tmp_path / "cdp-lock-dir.log"
    env.pop("CDP_LOCK_DIR", None)
    env["CDP_LOCK_DIR_LOG"] = str(lock_log)
    run = subprocess.run(args, env=env, capture_output=True, text=True)
    assert run.returncode == 0, run.stdout + run.stderr
    assert lock_log.read_text().splitlines() == [str(Path.home() / "gig/.cdp-gig.lock")]


def test_paid_direct_reports_every_wake_through_existing_telegram_outbox(tmp_path):
    output, env, args, _, _ = case(tmp_path)
    database = tmp_path / "telegram.sqlite3"

    run = subprocess.run(args, env=env, capture_output=True, text=True)

    assert run.returncode == 0, run.stdout + run.stderr
    result = json.loads(output.read_text())
    assert result["telegram"] == {"status": "sent", "message_id": "paid-wake-1"}
    with sqlite3.connect(database) as connection:
        message, state = connection.execute(
            "SELECT message,state FROM telegram_reports WHERE kind='paid-direct'"
        ).fetchone()
    assert state == "sent"
    assert message.startswith("[ココナラ][納品] Codex:::\n")
    for field in ("observed", "actionable", "effect", "readback", "failed", "pending", "oldest"):
        assert f"{field}:" in message


def test_paid_direct_telegram_failure_does_not_change_business_truth(tmp_path):
    output, env, args, _, _ = case(tmp_path)
    openclaw = exe(tmp_path / "openclaw-fail", "raise SystemExit(1)")
    args += ["--telegram-database", str(tmp_path / "telegram.sqlite3"),
             "--telegram-receipt-dir", str(tmp_path / "receipts"), "--openclaw", str(openclaw)]

    run = subprocess.run(args, env=env, capture_output=True, text=True)

    assert run.returncode == 0, run.stdout + run.stderr
    result = json.loads(output.read_text())
    assert result["status"] == "completed" and result["failed"] == 0
    assert result["telegram"]["status"] == "delivery_unknown"


def test_paid_direct_reports_top_level_exception_as_failed_wake(tmp_path):
    output, env, args, _, _ = case(tmp_path)
    lock_index = args.index("--lock-file") + 1
    broken_lock = tmp_path / "lock-directory"
    broken_lock.mkdir()
    args[lock_index] = str(broken_lock)

    run = subprocess.run(args, env=env, capture_output=True, text=True)

    assert run.returncode == 1, run.stdout + run.stderr
    result = json.loads(output.read_text())
    assert result["status"] == "failed" and result["failed"] == 1
    assert result["telegram"] == {"status": "sent", "message_id": "paid-wake-1"}
    with sqlite3.connect(tmp_path / "telegram.sqlite3") as connection:
        message, state = connection.execute(
            "SELECT message,state FROM telegram_reports WHERE kind='paid-direct'"
        ).fetchone()
    assert state == "sent"
    assert "failed: 1件" in message


def test_paid_direct_prepare_is_outside_lock_and_write_readback_is_inside(tmp_path):
    output, env, args, _, _ = remote_repair_case(tmp_path)
    held_log = tmp_path / "held.log"
    env["HELD_LOG"] = str(held_log)
    env["ANSWER_SEND_PERFORMED"] = "1"
    run = subprocess.run(args, env=env, capture_output=True, text=True)
    assert run.returncode == 0, run.stdout + run.stderr
    prepared = json.loads((tmp_path / "evidence/paid-direct/items/item-90000101-prepared.json").read_text())
    assert prepared["talkroom_id"] == "90000101" and "item" not in prepared
    lines = held_log.read_text().splitlines()
    assert "paid-remote-owner:0" in lines and "paid-remote-verifier:0" in lines
    assert "presend:1" in lines and "browser:1" in lines and "official:1" in lines


def test_paid_direct_ambient_lock_marker_still_acquires_fresh_wrapper_lock(tmp_path):
    output, env, args, _, _ = case(tmp_path)
    acquire_log = tmp_path / "acquire.log"
    env["GIG_CDP_LOCK_HELD"] = "1"
    env["CDP_ACQUIRE_LOG"] = str(acquire_log)
    run = subprocess.run(args, env=env, capture_output=True, text=True)
    assert run.returncode == 0, run.stdout + run.stderr
    assert acquire_log.read_text().splitlines() == ["acquired"]


def test_paid_direct_busy_write_does_not_recount_stale_effect_result(tmp_path):
    output, env, args, _, _ = case(tmp_path)
    stale = tmp_path / "evidence/paid-direct/items/item-0-result.json"
    put(stale, {"status": "completed", "effect": 1, "readback": 1, "failed": 0})
    env["BUSY_EFFECT"] = "1"
    run = subprocess.run(args, env=env, capture_output=True, text=True)
    assert run.returncode != 0
    result = json.loads(output.read_text())
    assert result["effect"] == 0 and result["readback"] == 0


def test_paid_direct_observes_all_orders_and_deduplicates_verified_answer(tmp_path):
    output, env, args, answer_count, _ = case(tmp_path)
    run = subprocess.run(args, env=env, capture_output=True, text=True)
    assert run.returncode == 0, run.stdout + run.stderr
    result = json.loads(output.read_text())
    assert result["status"] == "completed" and result["observed"] == 2 and result["actionable"] == 1
    assert result["effect"] == 0 and result["readback"] == 1 and result["pending"] == 1
    assert result["items"][0]["send_performed"] is False
    assert result["items"][0]["deduplicated"] is True
    assert result["items"][0]["formal_delivery_checkbox"] is False
    assert len(answer_count.read_text().splitlines()) == 1
    targeted = Path(env["TARGET_LOG"]).read_text().splitlines()
    assert targeted.count("targeted:90000101") == 1 and targeted.count("targeted:90000102") == 1


def test_paid_direct_accepts_dom_collapsed_whitespace_in_official_readback(tmp_path):
    output, env, args, answer_count, _ = case(tmp_path)
    project = tmp_path / "projects/recoverable-request"
    message = "更新を確認しました。\n詳細も確認しました。"
    dom_message = "更新を確認しました。 詳細も確認しました。"
    message_sha256 = hashlib.sha256(message.encode()).hexdigest()
    answer = json.loads((project / "delivery/paid-answer.json").read_text())
    answer["message"] = message
    answer["message_sha256"] = message_sha256
    put(project / "delivery/paid-answer.json", answer)
    intent = json.loads((project / "delivery/paid-remote-intent.json").read_text())
    intent["message_sha256"] = message_sha256
    put(project / "delivery/paid-remote-intent.json", intent)
    remote_result = json.loads((project / "delivery/paid-remote-result.json").read_text())
    remote_result["customer_message"] = message
    remote_result["message_sha256"] = message_sha256
    put(project / "delivery/paid-remote-result.json", remote_result)
    for evidence in (project / "evidence/before.json", project / "evidence/after.json",
                     project / "evidence/agent-PAID_REMOTE_VERIFY/before.json",
                     project / "evidence/agent-PAID_REMOTE_VERIFY/after.json"):
        payload = json.loads(evidence.read_text())
        payload["message_sha256"] = message_sha256
        put(evidence, payload)
    verifier = project / "evidence/agent-PAID_REMOTE_VERIFY/remote-verifier-result.json"
    verified = json.loads(verifier.read_text())
    verified["message_sha256"] = message_sha256
    put(verifier, verified)
    event = json.loads((project / "events.jsonl").read_text().splitlines()[0])
    event["message_sha256"] = message_sha256
    (project / "events.jsonl").write_text(json.dumps(event) + "\n", encoding="utf-8")
    official = json.loads((tmp_path / "official-90000101.json").read_text())
    seller = [{"text": dom_message}]
    official["talkroom"]["seller_sent_messages"] = seller
    official["orders"][0]["seller_sent_messages"] = seller
    put(tmp_path / "official-90000101.json", official)

    run = subprocess.run(args, env=env, capture_output=True, text=True)

    assert run.returncode == 0, run.stdout + run.stderr
    result = json.loads(output.read_text())
    assert result["status"] == "completed" and result["effect"] == 0 and result["readback"] == 1
    assert len(answer_count.read_text().splitlines()) == 1


def test_paid_direct_recovers_missing_handoff_from_single_fresh_verifier_readback(tmp_path):
    output, env, args, answer_count, _ = case(tmp_path)
    verifier = (tmp_path / "projects/recoverable-request/evidence/agent-PAID_REMOTE_VERIFY/remote-verifier-result.json")
    verified = json.loads(verifier.read_text())
    verified.pop("before_evidence")
    verified.pop("after_evidence")
    verified["evidence"] = ["after.json"]
    put(verifier, verified)
    project = tmp_path / "projects/recoverable-request"
    result_path = project / "delivery/paid-remote-result.json"
    remote_result = json.loads(result_path.read_text())
    remote_result["observed_state"] = None
    remote_result["after_state_digest"] = "0" * 64
    put(result_path, remote_result)
    (project / "delivery/paid-answer.json").unlink()
    (project / "events.jsonl").write_text("", encoding="utf-8")
    env["ANSWER_SEND_PERFORMED"] = "1"

    run = subprocess.run(args, env=env, capture_output=True, text=True)

    assert run.returncode == 0, run.stdout + run.stderr
    result = json.loads(output.read_text())
    assert result["effect"] == 1 and result["readback"] == 1
    assert len(answer_count.read_text().splitlines()) == 1


def test_paid_direct_refuses_stale_fresh_feedback_before_answer_browser(tmp_path):
    output, env, args, answer_count, _ = case(tmp_path, stale=True)
    run = subprocess.run(args, env=env, capture_output=True, text=True)
    assert run.returncode != 0
    result = json.loads(output.read_text())
    assert result["status"] == "failed" and result["failed_step"] == "remote_resume" and result["effect"] == 0
    assert result["pending"] == 1
    assert not answer_count.exists()


def test_paid_direct_closes_official_formal_delivery_as_awaiting_buyer(tmp_path):
    output, env, args, answer_count, _ = case(tmp_path)
    project = tmp_path / "projects/recoverable-request"
    (project / "state.json").unlink()
    requirements = json.loads((project / "requirements/live-buyer-reply.json").read_text())
    requirements.update(project_id=project.name, talkroom_id="90000101")
    put(project / "requirements/live-buyer-reply.json", requirements)
    artifact = project / "artifacts/delivered.xlsx"
    artifact.parent.mkdir()
    artifact.write_bytes(b"real-delivery")
    put(project / "events.jsonl", {
        "event": "FORMAL_DELIVERY_CONFIRMED",
        "project_id": project.name,
        "talkroom_id": "90000101",
        "artifact_path": str(artifact),
        "artifact_bytes": artifact.stat().st_size,
        "artifact_sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
        "seller_attachment_readback": artifact.name,
    })
    snapshot = tmp_path / "targeted-90000101.json"
    value = json.loads(snapshot.read_text())
    value["talkroom"].update({
        "transaction_state": "納品確認待ち", "formal_delivery_confirmed": True,
        "seller_sent_messages": [{"text": "納品します", "attachments": [artifact.name]}],
    })
    value["orders"][0].update({
        "talkroom_state": "納品確認待ち", "formal_delivery_observed": True,
        "seller_sent_messages": [{"text": "納品します", "attachments": [artifact.name]}],
    })
    value["orders"][0]["request_id"] = "wrong-project"
    put(snapshot, value)

    run = subprocess.run(args, env=env, capture_output=True, text=True)

    assert run.returncode == 0, run.stdout + run.stderr
    result = json.loads(output.read_text())
    row = next(item for item in result["items"] if item["talkroom_id"] == "90000101")
    assert row["status"] == "awaiting_buyer"
    assert row["send_performed"] is False and row["formal_delivery_checkbox"] is True
    assert result["actionable"] == 0 and result["effect"] == 0 and result["readback"] == 1
    assert not answer_count.exists()

    value["orders"][0]["buyer_feedback_pending_artifact"] = True
    put(snapshot, value)
    rerun = subprocess.run(args, env=env, capture_output=True, text=True)
    assert rerun.returncode == 0, rerun.stdout + rerun.stderr
    row = next(item for item in json.loads(output.read_text())["items"] if item["talkroom_id"] == "90000101")
    assert row["status"] != "awaiting_buyer"


def test_paid_direct_isolates_targeted_failure_from_other_orders(tmp_path):
    output, env, args, answer_count, _ = case(tmp_path, fail_targeted="90000102")
    run = subprocess.run(args, env=env, capture_output=True, text=True)
    assert run.returncode != 0
    result = json.loads(output.read_text())
    rows = {row["talkroom_id"]: row for row in result["items"]}
    assert result["failed"] == 1 and result["pending"] == 0 and result["actionable"] == 1 and result["effect"] == 0
    assert rows["90000101"]["status"] == "completed" and result["readback"] == 1
    assert rows["90000102"]["status"] == "failed"
    assert len(answer_count.read_text().splitlines()) == 1


def test_paid_direct_repairs_invalid_remote_resume_before_reusing_existing_answer(tmp_path):
    output, env, args, answer_count, _ = case(tmp_path, invalid_remote=True, existing_answer=True)
    run = subprocess.run(args, env=env, capture_output=True, text=True)
    assert run.returncode == 0, run.stdout + run.stderr
    result = json.loads(output.read_text())
    assert result["status"] == "completed" and result["actionable"] == 1
    assert result["effect"] == 0 and result["readback"] == 1 and result["failed"] == 0
    assert not answer_count.exists()


def test_paid_direct_rejects_verifier_file_when_its_runner_was_blocked(tmp_path):
    output, env, args, answer_count, _ = case(tmp_path)
    verifier_dir = tmp_path / "projects/recoverable-request/evidence/agent-PAID_REMOTE_VERIFY"
    blocked = verifier_dir / "blocked-result.json"
    put(blocked, {"status": "blocked"})
    put(verifier_dir / "summary.json", {"result_path": str(blocked)})
    run = subprocess.run(args, env=env, capture_output=True, text=True)
    assert run.returncode == 0, run.stdout + run.stderr
    result = json.loads(output.read_text())
    assert result["actionable"] == 1 and result["effect"] == 0 and result["readback"] == 1
    assert result["items"][0]["remote_repaired"] is True
    assert len(answer_count.read_text().splitlines()) == 1


def test_paid_direct_accepts_fresh_verifier_desired_state_digest_field(tmp_path):
    output, env, args, _, _ = case(tmp_path)
    verifier = (tmp_path / "projects/recoverable-request/evidence/agent-PAID_REMOTE_VERIFY/remote-verifier-result.json")
    value = json.loads(verifier.read_text())
    value["desired_state_digest"] = value.pop("desired_digest")
    put(verifier, value)
    run = subprocess.run(args, env=env, capture_output=True, text=True)
    assert run.returncode == 0, run.stdout + run.stderr
    result = json.loads(output.read_text())
    assert result["actionable"] == 1 and result["readback"] == 1


def test_paid_direct_deduplicates_fresh_existing_answer_after_remote_resume(tmp_path):
    output, env, args, answer_count, _ = case(tmp_path, existing_answer=True)
    run = subprocess.run(args, env=env, capture_output=True, text=True)
    assert run.returncode == 0, run.stdout + run.stderr
    result = json.loads(output.read_text())
    row = next(row for row in result["items"] if row["talkroom_id"] == "90000101")
    assert result["status"] == "completed" and result["effect"] == 0 and result["readback"] == 1
    assert row["send_performed"] is False and row["deduplicated"] is True
    assert row["formal_delivery_checkbox"] is False
    assert "presend/selected-talkroom-snapshot.json" in row["evidence_paths"]["official_readback"]
    assert not answer_count.exists()


def test_paid_direct_effect_item_requires_shared_lock(tmp_path):
    output, env, args, answer_count, effect_item = case(tmp_path)
    direct_output = tmp_path / "direct-effect-result.json"
    direct = list(args); direct[direct.index("--output") + 1] = str(direct_output)
    direct += ["--write-item", str(effect_item)]
    env = {key: value for key, value in env.items() if key != "GIG_CDP_LOCK_HELD"}
    run = subprocess.run(direct, env=env, capture_output=True, text=True)
    assert run.returncode != 0, run.stdout + run.stderr
    result = json.loads(direct_output.read_text())
    assert result["status"] == "failed" and result["failed_step"] == "writer_lock"
    assert not answer_count.exists() and not Path(env["TARGET_LOG"]).exists()


def test_paid_direct_write_marker_requires_current_lock_receipt(tmp_path):
    output, env, args, _, effect_item = case(tmp_path)
    direct_output = tmp_path / "direct-write-result.json"
    direct = list(args); direct[direct.index("--output") + 1] = str(direct_output)
    direct += ["--write-item", str(effect_item)]
    env["GIG_CDP_LOCK_HELD"] = "1"
    run = subprocess.run(direct, env=env, capture_output=True, text=True)
    assert run.returncode != 0, run.stdout + run.stderr
    result = json.loads(direct_output.read_text())
    assert result["status"] == "failed" and result["failed_step"] == "writer_lock"
    assert not Path(env["TARGET_LOG"]).exists()


def test_paid_direct_answer_snapshot_survives_presend_project_mutation(tmp_path):
    output, env, args, _, _ = case(tmp_path)
    env["ANSWER_SEND_PERFORMED"] = "1"
    env["MUTATE_ANSWER"] = str(tmp_path / "projects/recoverable-request/delivery/paid-answer.json")
    answer_log = tmp_path / "answer-message.log"
    env["ANSWER_MESSAGE_LOG"] = str(answer_log)
    run = subprocess.run(args, env=env, capture_output=True, text=True)
    assert run.returncode == 0, run.stdout + run.stderr
    assert answer_log.read_text().splitlines() == ["更新を確認しました。"]
    assert json.loads(output.read_text())["effect"] == 1


def remote_repair_case(tmp_path, preserve_verifier=False, preserve_builder=False):
    output, env, args, answer_count, _ = case(tmp_path)
    project = tmp_path / "projects" / "recoverable-request"
    put(project / "delivery/paid-work-mode.json", {
        "version": 1, "status": "ok", "feedback_sha256": "a" * 64, "mode": "remote"
    })
    if not preserve_builder:
        for name in ("paid-remote-intent.json", "paid-remote-result.json", "paid-answer.json"):
            (project / "delivery" / name).unlink()
    verifier = (tmp_path / "projects/recoverable-request/evidence/agent-PAID_REMOTE_VERIFY/remote-verifier-result.json")
    if not preserve_verifier:
        shutil.rmtree(verifier.parent)
    compiler = exe(tmp_path / "compiler.py", """
import json, sys
from pathlib import Path
a = dict(zip(sys.argv[1::2], sys.argv[2::2]))
queue = json.loads(Path(a['--queue-item']).read_text())
if not Path(queue.get('talkroom_evidence_file', '')).is_file(): raise SystemExit('live_talkroom_evidence_missing')
open(a['--output'], 'w').write(json.dumps({
    'ok': True, 'queue_title': queue.get('title'), 'source_refs': [],
    'combined_context': {'read_these_first': []},
}) + '\\n')
""")
    runner = exe(tmp_path / "runner.py", """
import hashlib, json, os, shutil, sys
from pathlib import Path
argv, a, i = sys.argv[1:], {}, 0
while i < len(argv):
    if argv[i] == '--read-only': i += 1; continue
    a[argv[i]] = argv[i + 1]; i += 2
role = a['--task-label']
log = os.environ['RUNNER_LOG']
open(log, 'a').write(role + '\\n')
if os.getenv('DECISION_RUNNER_FAILURE') and role == 'paid-work-decision': raise SystemExit(1)
role_attempt = Path(log).read_text().splitlines().count(role)
if os.getenv('HELD_LOG'): open(os.environ['HELD_LOG'], 'a').write(role + ':' + os.getenv('GIG_CDP_LOCK_HELD', '0') + '\\n')
evidence = Path(a['--evidence-dir'])
evidence.mkdir(parents=True, exist_ok=True)
runner_status = os.environ.get('RUNNER_STATUS', 'ok')
transient_review = 'verifier' in role and os.getenv('VERIFIER_TRANSIENT_ONCE') and role_attempt == 1
reject_review = 'verifier' in role and (os.getenv('VERIFIER_ALWAYS_REJECT') or (os.getenv('VERIFIER_REJECT_ONCE') and role_attempt == 1))
if reject_review or transient_review: runner_status = 'blocked'
(evidence / 'runner-result.json').write_text(json.dumps({'status': runner_status}))
summary = {
    'version': 1, 'status': 'success',
    'task_label': role, 'task_class': a['--task-class'],
    'escalated': a['--task-class'] == 'escalation-agent', 'selected_provider': 'codex',
    'selected_model': (os.environ.get('DECISION_SELECTED_MODEL', 'gpt-5.6-sol') if role == 'paid-work-decision'
                       else os.environ.get('VERIFIER_SELECTED_MODEL', 'gpt-5.6-sol') if 'verifier' in role
                       else 'gpt-5.6-sol'),
    'result_path': str(evidence / 'runner-result.json')}
if os.getenv('EXTERNAL_RUNNER_RESULT') and 'verifier' in role:
    external_result = evidence.parent / 'external-runner-result.json'
    external_result.write_bytes((evidence / 'runner-result.json').read_bytes())
    summary['result_path'] = str(external_result)
(evidence / 'summary.json').write_text(json.dumps(summary))
if os.getenv('STALE_VERIFIER_RUNNER_PROOF') and 'verifier' in role:
    os.utime(evidence / 'summary.json', (1, 1))
    os.utime(evidence / 'runner-result.json', (1, 1))
if role == 'paid-source-census':
    if os.getenv('SOURCE_CENSUS_FORBIDDEN_PATH'):
        Path(os.environ['SOURCE_CENSUS_FORBIDDEN_PATH']).read_text()
    isolated = Path(a['--workdir'])
    source_manifest = json.loads((isolated / 'source-manifest.json').read_text())
    source_row = source_manifest['sources'][0]
    visual_sources = json.loads((isolated / 'visual-manifest.json').read_text())['visual_sources']
    try:
        measures = json.loads(Path(source_row['isolated_path']).read_text()).get('measures', [1])
    except (UnicodeDecodeError, json.JSONDecodeError):
        measures = [1]
    verification = 'source-only exact read ' + ' '.join(row['sha256'] for row in visual_sources)
    (isolated / 'source-census.json').write_text(json.dumps({
        'version': 1, 'status': 'PASS',
        'requirements_sha256': source_manifest['requirements_sha256'],
        'sources': [{'path': row['path'], 'sha256': row['sha256']} for row in source_manifest['sources']],
        'visual_sources': visual_sources,
        'items': [
            {'source_locator': f'page=1,measure={measure}', 'exact_semantic_value': str(measure),
             'modifiers': 'none', 'verification': verification}
            for measure in measures
        ],
    }))
    print(json.dumps({'ok': True})); raise SystemExit(0)
root = Path(a['--workdir'])
delivery = root / 'delivery'
requirements_sha256 = json.loads((root / 'requirements/live-buyer-reply.json').read_text())['accumulated_sha256']
if role == 'paid-file-owner':
    correspondence_fixture = os.getenv('SOURCE_CORRESPONDENCE_FIXTURE')
    version = role_attempt if correspondence_fixture else 1
    artifact = delivery / f'delivery-v{version}.md'
    if correspondence_fixture:
        source = root / 'source/source-score.json'; source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text(json.dumps({'measures': [1, 2, 3]}))
        shifted = correspondence_fixture == 'always' or role_attempt == 1
        artifact.write_text(json.dumps({'measures': [2, 3, 1] if shifted else [1, 2, 3]}))
    else:
        artifact.write_text('# 納品物\\n' + '確認済みの成果物です。' * 100)
    if os.getenv('PRESERVE_ARTIFACT_MTIME'): os.utime(artifact, (1, 1))
    acceptance = root / f'acceptance/file-v{version}.json'; acceptance.parent.mkdir(parents=True, exist_ok=True)
    acceptance.write_text(json.dumps({'status': 'PASS', 'acceptance_delta': ['buyer requirements implemented']}))
    manifest = {'status': 'ok', 'project_root': str(root),
        'requirements_path': str(root / 'requirements/live-buyer-reply.json'), 'artifact_path': str(artifact),
        'artifact_version': f'v{version}', 'acceptance_evidence_path': str(acceptance), 'acceptance_status': 'PASS',
        'acceptance_delta': ['buyer requirements implemented'],
        'package_sha256': hashlib.sha256(artifact.read_bytes()).hexdigest()}
    if correspondence_fixture:
        receipt = root / f'acceptance/source-correspondence-v{version}.json'
        census = root / 'acceptance/controller-source-census-v1.json'
        controller_receipt = root / 'context/paid-source-census.json'
        label_evidence = root / f'acceptance/source-label-evidence-v{version}.json'
        label_evidence.write_text(json.dumps({'checks': []}))
        receipt.write_text(json.dumps({
            'version': 1, 'status': 'PASS', 'artifact_sha256': manifest['package_sha256'],
            'sources': [{'path': 'source/source-score.json',
                         'sha256': hashlib.sha256(source.read_bytes()).hexdigest()}],
            'independent_source_census': {
                'path': str(census), 'sha256': hashlib.sha256(census.read_bytes()).hexdigest(),
                'controller_receipt_path': str(controller_receipt),
                'controller_receipt_sha256': hashlib.sha256(controller_receipt.read_bytes()).hexdigest(),
            },
            'exact_semantic_value_checks': {
                'label_evidence_path': str(label_evidence),
                'label_evidence_sha256': hashlib.sha256(label_evidence.read_bytes()).hexdigest(),
            },
            'mappings': [
                {'source_locator': f'page=1,measure={measure}',
                 'output_locator': f'page=1,measure={measure}',
                 'correspondence': f'measure {measure} is preserved',
                 'verification': 'independent exact measure comparison'}
                for measure in (1, 2, 3)
            ],
        }))
        manifest['source_correspondence_path'] = str(receipt)
    (delivery / 'paid-work-result.json').write_text(json.dumps(manifest))
    print(json.dumps({'ok': True})); raise SystemExit(0)
if role == 'paid-file-verifier':
    if os.getenv('SOURCE_CORRESPONDENCE_FIXTURE'):
        manifest = json.loads((delivery / 'paid-work-result.json').read_text())
        source_measures = json.loads((root / 'source/source-score.json').read_text())['measures']
        output_measures = json.loads(Path(manifest['artifact_path']).read_text())['measures']
        verdict = ('deliverable' if source_measures == output_measures else 'needs_revision')
        reason = ('all receipt locators independently match source and output measures'
                  if verdict == 'deliverable' else
                  'output is shifted by one measure; repair every mapped locator before submission')
        (evidence / 'runner-result.json').write_text(json.dumps({'verdict': verdict, 'reason': reason}))
        print(json.dumps({'ok': True})); raise SystemExit(0)
    (evidence / 'runner-result.json').write_text(json.dumps({
        'verdict': 'deliverable', 'reason': 'artifact proves the request'}))
    print(json.dumps({'ok': True})); raise SystemExit(0)
if role in ('paid-work-mode', 'paid-work-decision'):
    if role == 'paid-work-decision' or os.getenv('PAID_WORK_DECISION'):
        identity = json.loads((root / 'source/talkroom/messages.jsonl').read_text().splitlines()[-1])
        decision = os.getenv('PAID_WORK_DECISION', 'actionable')
        mode = None if decision != 'actionable' else os.getenv('PAID_WORK_MODE', 'answer')
        result = {
            'decision': decision, 'mode': mode, 'feedback_sha256': 'a' * 64,
            'requirements_sha256': requirements_sha256,
            'latest_message_identity': {'message_id': identity['message_id'],
                'content_sha256': identity['content_sha256'], 'side': identity['side']},
            'required_output': 'answer' if mode == 'answer' else 'buyer deliverable',
            'required_effect': 'coconala_answer' if mode == 'answer' else 'coconala_progress',
            'delivery_stage': 'review' if mode == 'file' else 'none',
            'formal_approval_evidence': None,
            'unresolved': [],
        }
        if os.getenv('DECISION_EXTRA_FIELD'): result['unexpected'] = True
        (evidence / 'runner-result.json').write_text(json.dumps(result))
        if os.getenv('MUTATE_DECISION_ITEM'):
            item_path = Path(os.environ['MUTATE_DECISION_ITEM'])
            item = json.loads(item_path.read_text())
            item['title'] = 'runner-mutated-input'
            item_path.write_text(json.dumps(item))
        print(json.dumps({'ok': True}))
        raise SystemExit(0)
    (evidence / 'runner-result.json').write_text(json.dumps({
        'status': 'ok', 'summary': os.getenv('PAID_WORK_MODE', 'remote'),
        'evidence': ['Current buyer requirements require an authenticated external-system mutation.']}))
    print(json.dumps({'ok': True}))
    raise SystemExit(0)
desired = {'title': 'updated', 'enabled': True}
digest = hashlib.sha256(json.dumps(desired, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
message = (os.getenv('CONSULTATION_MESSAGE', '更新を確認しました。') if role.startswith('paid-answer-')
           else os.getenv('REMOTE_CUSTOMER_MESSAGE', '更新を確認しました。'))
message_sha256 = hashlib.sha256(message.encode()).hexdigest()
if '--read-only' in sys.argv and role.startswith('paid-answer-'):
    attachments = json.loads((root / 'requirements/live-buyer-reply.json').read_text())['attachments']
    reviewed = [{'filename': row['filename'], 'sha256': row['sha256'], 'observation': '画像内容を確認しました'} for row in attachments]
    issues = [os.environ['CONSULTATION_BUILDER_ISSUE']] if 'owner' in role and os.getenv('CONSULTATION_BUILDER_ISSUE') else []
    if 'verifier' in role and os.getenv('CONSULTATION_BUILDER_ISSUE'):
        prompt = Path(a['--prompt-file']).read_text()
        resolution = os.environ['CONSULTATION_ISSUE_RESOLUTION']
        resolved = (os.environ['CONSULTATION_BUILDER_ISSUE'] in prompt
                    and 'Candidate:' in prompt and resolution in message)
        issues = [] if resolved else ['builder concern remains unresolved']
    status = 'ok' if 'owner' in role or not issues else 'blocked'
    (evidence / 'runner-result.json').write_text(json.dumps({'status': status, 'customer_message': message, 'reviewed_attachments': reviewed, 'issues': issues}))
    print(json.dumps({'ok': True}))
    raise SystemExit(0)
if 'owner' in role:
    customer_attachment = None
    if os.getenv('REMOTE_CUSTOMER_ATTACHMENT'):
        screenshot = root / 'evidence/buyma-seller-registration-date.png'
        screenshot.write_bytes(b'official-buyma-registration-date-screenshot')
        customer_attachment = {'path': str(screenshot), 'filename': screenshot.name,
                               'sha256': hashlib.sha256(screenshot.read_bytes()).hexdigest()}
    (root / 'evidence/remote-before.json').write_text(json.dumps({'target': 'https://example.test/item', 'authenticated': True, 'requirements_sha256': requirements_sha256, 'message_sha256': message_sha256}))
    (root / 'evidence/remote-after.json').write_text(json.dumps({'target': 'https://example.test/item', 'authenticated': True, 'observed_state': desired, 'requirements_sha256': requirements_sha256, 'message_sha256': message_sha256}))
    (delivery / 'paid-remote-intent.json').write_text(json.dumps({'buyer_feedback_sha256': 'a' * 64, 'target': 'https://example.test/item', 'desired_state': desired, 'desired_state_sha256': digest, 'requirements_sha256': requirements_sha256, 'message_sha256': message_sha256, 'customer_attachment': customer_attachment}))
    result = {'status': 'ok', 'buyer_feedback_sha256': 'a' * 64, 'target': 'https://example.test/item', 'observed_state': desired, 'after_state_digest': digest, 'verified_after': True, 'before_evidence': 'evidence/remote-before.json', 'after_evidence': 'evidence/remote-after.json', 'customer_message': message, 'requirements_sha256': requirements_sha256, 'message_sha256': message_sha256, 'customer_attachment': customer_attachment}
    if os.getenv('BUILDER_USES_VERIFIER_EVIDENCE'):
        managed = root / 'evidence/agent-PAID_REMOTE_VERIFY'
        managed.mkdir(parents=True, exist_ok=True)
        (managed / 'builder-before.json').write_text(json.dumps({'target': 'https://example.test/item', 'authenticated': True, 'requirements_sha256': requirements_sha256, 'message_sha256': message_sha256}))
        (managed / 'builder-after.json').write_text(json.dumps({'target': 'https://example.test/item', 'authenticated': True, 'observed_state': desired, 'requirements_sha256': requirements_sha256, 'message_sha256': message_sha256}))
        result['before_evidence'] = str(managed / 'builder-before.json')
        result['after_evidence'] = str(managed / 'builder-after.json')
    if os.getenv('DROP_REQUIREMENTS_DIGEST'):
        result.pop('requirements_sha256', None)
    (delivery / 'paid-remote-result.json').write_text(json.dumps(result))
    if os.getenv('MUTATE_REQUIREMENTS_IN_BUILDER'):
        requirements = root / 'requirements/live-buyer-reply.json'
        payload = json.loads(requirements.read_text())
        payload['accumulated_sha256'] = 'e' * 64
        requirements.write_text(json.dumps(payload))
    if os.getenv('REMOVE_REPAIR_DIR'):
        shutil.rmtree(Path(a['--prompt-file']).parent)
else:
    managed = root / 'evidence/agent-PAID_REMOTE_VERIFY'
    managed.mkdir(parents=True, exist_ok=True)
    (managed / 'before.json').write_text(json.dumps({'target': 'https://example.test/item', 'authenticated': True, 'observed_state': desired, 'requirements_sha256': requirements_sha256, 'message_sha256': message_sha256}))
    (managed / 'after.json').write_text(json.dumps({'target': 'https://example.test/item', 'authenticated': True, 'observed_state': desired, 'requirements_sha256': requirements_sha256, 'message_sha256': message_sha256}))
    if os.getenv('FUTURE_VERIFIER_EVIDENCE'):
        os.utime(managed / 'before.json', (4102444800, 4102444800))
        os.utime(managed / 'after.json', (4102444800, 4102444800))
    customer_attachment = (None if os.getenv('DROP_VERIFIER_CUSTOMER_ATTACHMENT') else
                           json.loads((delivery / 'paid-remote-result.json').read_text()).get('customer_attachment'))
    verifier_result = {'verified': not (reject_review or transient_review), 'buyer_feedback_sha256': 'a' * 64, 'target': 'https://example.test/item', 'desired_digest': digest, 'observed_digest': digest, 'observed_state': desired, 'before_evidence': 'before.json', 'after_evidence': 'after.json', 'requirements_sha256': requirements_sha256, 'message_sha256': message_sha256, 'customer_attachment': customer_attachment}
    if reject_review:
        verifier_result.update({'classification': 'quality_mismatch', 'delta': [{'requirement': 'buyer-ready explanation', 'expected': 'complete usage explanation', 'observed': 'too terse', 'evidence': 'after.json', 'repair': 'explain how to use the delivered system'}]})
    if transient_review:
        verifier_result.update({'classification': 'cdp_transient', 'delta': []})
    (managed / 'remote-verifier-result.json').write_text(json.dumps(verifier_result))
    if os.getenv('MUTATE_VERIFIER_DELIVERY'):
        result = json.loads((delivery / 'paid-remote-result.json').read_text())
        result['customer_message'] = '改ざんされた回答'
        (delivery / 'paid-remote-result.json').write_text(json.dumps(result))
        (delivery / 'paid-answer.json').write_text(json.dumps({'version': 1, 'status': 'answer', 'message': '改ざんされた回答'}))
    if os.getenv('REPLACE_VERIFIER_DELIVERY'):
        result_path = delivery / 'paid-remote-result.json'
        external_result = delivery / 'paid-remote-result-copy.json'
        external_result.write_bytes(result_path.read_bytes())
        result_path.unlink()
        result_path.symlink_to(external_result)
print(json.dumps({'ok': True}))
""")
    while "--agent-runner" in args:
        runner_flag = args.index("--agent-runner")
        del args[runner_flag:runner_flag + 2]
    args += ["--context-compiler", str(compiler), "--agent-runner", str(runner)]
    args += ["--delivery-evidence-dir", str(tmp_path / "delivery-evidence")]
    env["RUNNER_LOG"] = str(tmp_path / "runner-log")
    return output, env, args, answer_count, project


def initial_consultation_case(tmp_path, title="パソコン購入相談にのってください", message="更新を確認しました。",
                              attachment_count=3):
    output, env, args, answer_count, project = remote_repair_case(tmp_path)
    (project / "delivery/paid-work-mode.json").unlink()
    (project / "state.json").unlink()
    for path in (
        project / "delivery/paid-remote-intent.json",
        project / "delivery/paid-remote-result.json",
        project / "delivery/paid-answer.json",
        project / "events.jsonl",
    ):
        path.unlink(missing_ok=True)
    shutil.rmtree(project / "evidence/agent-PAID_REMOTE_VERIFY", ignore_errors=True)
    requirements_path = project / "requirements/live-buyer-reply.json"
    requirements = json.loads(requirements_path.read_text())
    attachments = []
    for index in range(attachment_count):
        content = f"image-{index}".encode()
        digest = hashlib.sha256(content).hexdigest()
        image = project / "source/buyer-attachments" / f"{digest[:12]}-image-{index}.jpg"
        image.parent.mkdir(parents=True, exist_ok=True)
        image.write_bytes(content)
        attachments.append({"filename": f"image-{index}.jpg", "sha256": digest, "source_path": str(image)})
    requirements["attachments"] = attachments
    put(requirements_path, requirements)
    targeted = tmp_path / "targeted-90000101.json"
    snapshot = json.loads(targeted.read_text())
    for row in (snapshot["talkroom"], snapshot["orders"][0]):
        row.update({
            "buyer_feedback_pending_artifact": True,
            "buyer_feedback_stage": "initial_request",
            "title": title,
        })
    put(targeted, snapshot)
    env["ANSWER_SEND_PERFORMED"] = "1"
    env["PAID_WORK_MODE"] = "answer"
    env["CONSULTATION_MESSAGE"] = message
    official = tmp_path / "official-90000101.json"
    snapshot = json.loads(official.read_text())
    seller = [{"text": message, "text_sha256": hashlib.sha256(message.encode()).hexdigest()}]
    snapshot["talkroom"]["seller_sent_messages"] = seller
    snapshot["orders"][0]["seller_sent_messages"] = seller
    put(official, snapshot)
    return output, env, args, answer_count, project, attachments


def initial_remote_attachment_case(tmp_path, message="更新を確認しました。"):
    output, env, args, answer_count, project = remote_repair_case(tmp_path)
    (project / "state.json").unlink()
    (project / "delivery/paid-work-mode.json").unlink()
    for path in (
        project / "delivery/paid-remote-intent.json",
        project / "delivery/paid-remote-result.json",
        project / "delivery/paid-answer.json",
        project / "events.jsonl",
    ):
        path.unlink(missing_ok=True)
    shutil.rmtree(project / "evidence/agent-PAID_REMOTE_VERIFY", ignore_errors=True)

    manual = project / "source/buyer-attachments/manual.pdf"
    manual.parent.mkdir(parents=True, exist_ok=True)
    manual.write_bytes(b"BUYMA account registration manual")
    requirements_path = project / "requirements/live-buyer-reply.json"
    requirements = json.loads(requirements_path.read_text())
    requirements["accumulated_requirements"][0]["text"] = (
        "BUYMAの出品者登録後、パーソナルショッパーページの出品者登録日をスクリーンショットして送ってください。"
    )
    requirements["accumulated_requirements"][0]["attachments"] = ["アカウント登録方法.pdf"]
    row = requirements["accumulated_requirements"][0]
    row["sha256"] = hashlib.sha256(json.dumps(
        {"text": row["text"], "attachments": row["attachments"]},
        ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    ).encode()).hexdigest()
    requirements["accumulated_sha256"] = hashlib.sha256(json.dumps(
        [row["sha256"]], ensure_ascii=False, separators=(",", ":"),
    ).encode()).hexdigest()
    put(requirements_path, requirements)

    for kind in ("targeted", "fresh", "repair", "presend", "official"):
        snapshot_path = tmp_path / f"{kind}-90000101.json"
        snapshot = json.loads(snapshot_path.read_text())
        for observed in (snapshot["talkroom"], snapshot["orders"][0]):
            observed.update({
                "title": "バイマ出品作業 12件",
                "buyer_feedback_pending_artifact": True,
                "buyer_feedback_stage": "initial_request",
                "buyer_feedback_requirements_path": str(requirements_path),
            })
        if kind == "official":
            seller = [{"text": message[:300], "text_sha256": hashlib.sha256(" ".join(message.split()).encode()).hexdigest(),
                       "attachments": ["buyma-seller-registration-date.png"]}]
            snapshot["talkroom"]["seller_sent_messages"] = seller
            snapshot["orders"][0]["seller_sent_messages"] = seller
        put(snapshot_path, snapshot)
    env["REMOTE_CUSTOMER_ATTACHMENT"] = "1"
    env["REMOTE_CUSTOMER_MESSAGE"] = message
    env["PAID_WORK_MODE"] = "remote"
    env["ANSWER_SEND_PERFORMED"] = "1"
    env["ANSWER_PAYLOAD_LOG"] = str(tmp_path / "answer-payload.json")
    return output, env, args, answer_count, project


def decision_case(tmp_path, title="注文内容の確認"):
    output, env, args, answer_count, project, _ = initial_consultation_case(tmp_path, title=title)
    put(project / "state.json", {"request_id": "recoverable-request", "talkroom_id": "90000101"})
    snapshot = json.loads((tmp_path / "targeted-90000101.json").read_text())
    item = {**snapshot["orders"][0], "request_id": "recoverable-request", "contract_id": "talkroom:90000101"}
    item_path = tmp_path / "decision-item.json"
    put(item_path, item)
    env["PAID_WORK_DECISION"] = "actionable"
    env["PAID_WORK_MODE"] = "answer"
    return output, env, args + ["--decision-item", str(item_path)], answer_count, project


def test_paid_direct_creates_strict_decision_receipt(tmp_path):
    output, env, args, answer_count, project = decision_case(tmp_path)

    run = subprocess.run(args, env=env, capture_output=True, text=True)

    assert run.returncode == 0, run.stdout + run.stderr
    result = json.loads(output.read_text())
    assert result["status"] == "completed" and result["decision"] == "actionable" and result["mode"] == "answer"
    assert Path(env["RUNNER_LOG"]).read_text().splitlines() == ["paid-work-decision"]
    assert not answer_count.exists()
    receipt = json.loads((project / "context/paid-work-decision.json").read_text())
    assert receipt["decision"] == "actionable" and receipt["mode"] == "answer"
    assert receipt["runner"]["selected_provider"] == "codex"
    assert len(receipt["prompt_sha256"]) == 64


def test_paid_decision_schema_uses_codex_supported_subset():
    schema = json.loads((SCRIPT.parent.parent / "schemas/paid_work_decision.schema.json").read_text())

    assert "allOf" not in schema
    assert schema["properties"]["mode"]["enum"] == ["file", "remote", "answer", None]


def test_paid_decision_prompt_defines_modes_by_required_effect(tmp_path):
    output, env, args, _, _ = decision_case(tmp_path)

    run = subprocess.run(args, env=env, capture_output=True, text=True)

    assert run.returncode == 0, run.stdout + run.stderr
    prompt = (tmp_path / "evidence/paid-direct/90000101/mode/decision.prompt.txt").read_text()
    assert "outside the Coconala marketplace" in prompt
    assert "Answer mode is for the Coconala talkroom" in prompt
    assert "Use file whenever satisfying the request requires a seller-produced local artifact" in prompt


def test_paid_direct_stale_decision_message_identity_reruns_judgement(tmp_path):
    output, env, args, _, project = decision_case(tmp_path)
    first = subprocess.run(args, env=env, capture_output=True, text=True)
    assert first.returncode == 0, first.stdout + first.stderr
    messages = project / "source/talkroom/messages.jsonl"
    new_text = "新しい公式メッセージ"
    new_row = {
        "version": 1, "source": "coconala_live_talkroom", "talkroom_id": "90000101",
        "message_id": "seller-message-2", "observed_at": "2026-08-12T00:01:00+00:00",
        "side": "seller", "sent_at": "2026-08-12T00:01:00+00:00", "text": new_text,
        "attachments": [],
    }
    new_sha = official_content_sha256(
        new_row["side"], new_row["sent_at"], new_row["text"], new_row["attachments"],
    )
    new_row["content_sha256"] = new_sha
    with messages.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(new_row, ensure_ascii=False) + "\n")

    second = subprocess.run(args, env=env, capture_output=True, text=True)

    assert second.returncode == 0, second.stdout + second.stderr
    assert Path(env["RUNNER_LOG"]).read_text().splitlines() == ["paid-work-decision", "paid-work-decision"]
    assert json.loads((project / "context/paid-work-decision.json").read_text())["latest_message_identity"] == {
        "message_id": "seller-message-2", "content_sha256": new_sha, "side": "seller",
    }


def test_paid_direct_stale_decision_requirements_reruns_judgement(tmp_path):
    output, env, args, _, project = decision_case(tmp_path)
    first = subprocess.run(args, env=env, capture_output=True, text=True)
    assert first.returncode == 0, first.stdout + first.stderr
    requirements_path = project / "requirements/live-buyer-reply.json"
    requirements = json.loads(requirements_path.read_text())
    row = requirements["accumulated_requirements"][0]
    row["text"] = "変更された累積要件"
    row["sha256"] = hashlib.sha256(json.dumps(
        {"text": row["text"], "attachments": row["attachments"]},
        ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    ).encode()).hexdigest()
    requirements["accumulated_sha256"] = hashlib.sha256(json.dumps(
        [row["sha256"]], ensure_ascii=False, separators=(",", ":"),
    ).encode()).hexdigest()
    put(requirements_path, requirements)

    second = subprocess.run(args, env=env, capture_output=True, text=True)

    assert second.returncode == 0, second.stdout + second.stderr
    assert Path(env["RUNNER_LOG"]).read_text().splitlines() == ["paid-work-decision", "paid-work-decision"]
    assert json.loads((project / "context/paid-work-decision.json").read_text())["requirements_sha256"] == requirements["accumulated_sha256"]


def test_paid_direct_stale_decision_context_reruns_judgement(tmp_path):
    output, env, args, _, project = decision_case(tmp_path)
    first = subprocess.run(args, env=env, capture_output=True, text=True)
    assert first.returncode == 0, first.stdout + first.stderr
    item_path = tmp_path / "decision-item.json"
    item = json.loads(item_path.read_text())
    item["title"] = "更新された案件文脈"
    put(item_path, item)

    second = subprocess.run(args, env=env, capture_output=True, text=True)

    assert second.returncode == 0, second.stdout + second.stderr
    assert Path(env["RUNNER_LOG"]).read_text().splitlines() == ["paid-work-decision", "paid-work-decision"]


def test_paid_direct_real_context_compiler_reuses_unchanged_decision(tmp_path):
    output, env, args, _, project = decision_case(tmp_path)
    while "--context-compiler" in args:
        index = args.index("--context-compiler")
        del args[index:index + 2]
    args += ["--context-compiler", str(SCRIPT.parent / "project_context_compiler.py")]

    first = subprocess.run(args, env=env, capture_output=True, text=True)
    assert first.returncode == 0, first.stdout + first.stderr
    second = subprocess.run(args, env=env, capture_output=True, text=True)

    assert second.returncode == 0, second.stdout + second.stderr
    assert Path(env["RUNNER_LOG"]).read_text().splitlines() == ["paid-work-decision"]
    assert (project / "context/paid-work-decision.json").is_file()


def test_paid_direct_tampered_decision_evidence_forces_fresh_judgement(tmp_path):
    output, env, args, _, project = decision_case(tmp_path)
    first = subprocess.run(args, env=env, capture_output=True, text=True)
    assert first.returncode == 0, first.stdout + first.stderr
    (project / "evidence/agent-PAID_WORK_DECISION/runner-result.json").unlink()

    second = subprocess.run(args, env=env, capture_output=True, text=True)

    assert second.returncode == 0, second.stdout + second.stderr
    assert Path(env["RUNNER_LOG"]).read_text().splitlines() == ["paid-work-decision", "paid-work-decision"]


def test_paid_direct_accepts_non_actionable_decision_only_with_null_mode(tmp_path):
    output, env, args, _, _ = decision_case(tmp_path)
    env["PAID_WORK_DECISION"] = "await_buyer"

    run = subprocess.run(args, env=env, capture_output=True, text=True)

    assert run.returncode == 0, run.stdout + run.stderr
    result = json.loads(output.read_text())
    assert result["decision"] == "await_buyer" and result["mode"] is None
    assert result.get("effect", 0) == 0


def test_paid_direct_rejects_wrong_decision_model_and_extra_field(tmp_path):
    for variable in ("DECISION_SELECTED_MODEL", "DECISION_EXTRA_FIELD"):
        output, env, args, _, project = decision_case(tmp_path / variable)
        env[variable] = "gpt-5.6-luna" if variable == "DECISION_SELECTED_MODEL" else "1"

        run = subprocess.run(args, env=env, capture_output=True, text=True)

        assert run.returncode == 1
        assert json.loads(output.read_text())["effect"] == 0
        assert not (project / "context/paid-work-decision.json").exists()


def test_paid_direct_rejects_decision_input_traversal(tmp_path):
    output, env, args, _, project = decision_case(tmp_path)
    item_path = tmp_path / "decision-item.json"
    item = json.loads(item_path.read_text())
    item["talkroom_id"] = "../escape"
    put(item_path, item)

    run = subprocess.run(args, env=env, capture_output=True, text=True)

    assert run.returncode == 1
    assert json.loads(output.read_text()) == {
        "status": "failed", "failed_step": "paid_work_decision", "effect": 0,
    }
    assert not Path(env["RUNNER_LOG"]).exists()


def test_paid_direct_rejects_symlinked_decision_evidence_root(tmp_path):
    output, env, args, _, _ = decision_case(tmp_path)
    evidence = tmp_path / "evidence"
    evidence.mkdir(parents=True, exist_ok=True)
    paid = evidence / "paid-direct"
    outside = tmp_path / "outside-evidence"
    outside.mkdir()
    paid.symlink_to(outside, target_is_directory=True)

    run = subprocess.run(args, env=env, capture_output=True, text=True)

    assert run.returncode == 1
    assert json.loads(output.read_text()) == {
        "status": "failed", "failed_step": "paid_work_decision", "effect": 0,
    }
    assert not (outside / "90000101/mode/decision.prompt.txt").exists()
    assert not Path(env["RUNNER_LOG"]).exists()


def test_paid_direct_rejects_decision_input_mutation_before_receipt(tmp_path):
    output, env, args, _, project = decision_case(tmp_path)
    env["MUTATE_DECISION_ITEM"] = str(tmp_path / "decision-item.json")

    run = subprocess.run(args, env=env, capture_output=True, text=True)

    assert run.returncode == 1
    assert json.loads(output.read_text()) == {
        "status": "failed", "failed_step": "paid_work_decision", "effect": 0,
    }
    assert not (project / "context/paid-work-decision.json").exists()


def test_paid_direct_decision_model_failure_is_fail_closed(tmp_path):
    output, env, args, _, project = decision_case(tmp_path)
    env["DECISION_RUNNER_FAILURE"] = "1"

    run = subprocess.run(args, env=env, capture_output=True, text=True)

    assert run.returncode == 1
    result = json.loads(output.read_text())
    assert result == {"status": "failed", "failed_step": "paid_work_decision", "effect": 0}
    assert not (project / "context/paid-work-decision.json").exists()


def test_paid_direct_bootstraps_initial_remote_work_and_sends_verified_attachment(tmp_path):
    output, env, args, answer_count, project = initial_remote_attachment_case(tmp_path)

    run = subprocess.run(args, env=env, capture_output=True, text=True)

    assert run.returncode == 0, run.stdout + run.stderr
    result = json.loads(output.read_text())
    assert result["actionable"] == 1 and result["effect"] == 1 and result["readback"] == 1
    assert (project / "state.json").is_file()
    decision = json.loads((project / "context/paid-work-decision.json").read_text())
    assert decision["mode"] == "remote" and decision["feedback_sha256"] == "a" * 64
    assert Path(env["RUNNER_LOG"]).read_text().splitlines() == [
        "paid-work-decision", "paid-remote-owner", "paid-remote-verifier",
    ]
    answer = json.loads(Path(env["ANSWER_PAYLOAD_LOG"]).read_text())
    attachment = answer["attachment"]
    assert attachment["filename"] == "buyma-seller-registration-date.png"
    assert hashlib.sha256(Path(attachment["path"]).read_bytes()).hexdigest() == attachment["sha256"]
    assert len(answer_count.read_text().splitlines()) == 1


def test_paid_direct_does_not_send_attachment_without_fresh_verifier_attestation(tmp_path):
    output, env, args, answer_count, _ = initial_remote_attachment_case(tmp_path)
    env["DROP_VERIFIER_CUSTOMER_ATTACHMENT"] = "1"

    run = subprocess.run(args, env=env, capture_output=True, text=True)

    assert run.returncode != 0, run.stdout + run.stderr
    result = json.loads(output.read_text())
    assert result["effect"] == 0 and result["failed"] == 1
    assert not answer_count.exists()


def test_paid_direct_long_attached_answer_deduplicates_from_official_hash(tmp_path):
    message = "BUYMA出品者登録日を確認したスクリーンショットを添付します。" * 20
    output, env, args, answer_count, _ = initial_remote_attachment_case(tmp_path, message)

    first = subprocess.run(args, env=env, capture_output=True, text=True)
    assert first.returncode == 0, first.stdout + first.stderr
    targeted = tmp_path / "targeted-90000101.json"
    snapshot = json.loads((tmp_path / "official-90000101.json").read_text())
    put(targeted, snapshot)
    second = subprocess.run(args, env=env, capture_output=True, text=True)

    assert second.returncode == 0, second.stdout + second.stderr
    result = json.loads(output.read_text())
    assert result["effect"] == 0 and result["readback"] == 1
    assert len(answer_count.read_text().splitlines()) == 1


def test_paid_direct_routes_initial_paid_request_through_reviewed_answer(tmp_path):
    output, env, args, answer_count, project, _ = initial_consultation_case(tmp_path)

    run = subprocess.run(args, env=env, capture_output=True, text=True)

    assert run.returncode == 0, run.stdout + run.stderr
    result = json.loads(output.read_text())
    assert result["actionable"] == 1 and result["effect"] == 1 and result["readback"] == 1
    assert Path(project / "state.json").is_file()
    assert Path(env["RUNNER_LOG"]).read_text().splitlines() == [
        "paid-work-decision", "paid-answer-owner", "paid-answer-verifier",
    ]
    prompt = (tmp_path / "evidence/paid-direct/90000101/answer-review/owner.prompt.txt").read_text()
    assert "Sol paid answer owner" in prompt
    assert "Read-only: never submit or send anything" in prompt
    assert len(answer_count.read_text().splitlines()) == 1
    intent = json.loads((project / "delivery/paid-remote-intent.json").read_text())
    assert intent["mode"] == "answer"
    assert not (project / "delivery/paid-remote-result.json").exists()
    assert not (project / "evidence/agent-PAID_REMOTE_VERIFY/remote-verifier-result.json").exists()

    targeted = tmp_path / "targeted-90000101.json"
    snapshot = json.loads(targeted.read_text())
    message = json.loads((project / "delivery/paid-answer.json").read_text())["message"]
    for row in (snapshot["talkroom"], snapshot["orders"][0]):
        row["seller_sent_messages"] = [{"text": message, "text_sha256": hashlib.sha256(message.encode()).hexdigest()}]
    put(targeted, snapshot)
    second = subprocess.run(args, env=env, capture_output=True, text=True)
    assert second.returncode == 0, second.stdout + second.stderr
    assert json.loads(output.read_text())["effect"] == 0
    assert len(answer_count.read_text().splitlines()) == 1


def test_paid_direct_routes_unknown_initial_paraphrase_by_semantic_mode(tmp_path):
    output, env, args, answer_count, _, _ = initial_consultation_case(
        tmp_path, title="用途に合う一台を一緒に選んでほしい",
    )
    env["PAID_WORK_MODE"] = "answer"

    run = subprocess.run(args, env=env, capture_output=True, text=True)

    assert run.returncode == 0, run.stdout + run.stderr
    result = json.loads(output.read_text())
    assert result["actionable"] == 1 and result["effect"] == 1 and result["readback"] == 1
    assert len(answer_count.read_text().splitlines()) == 1


def test_paid_direct_routes_message_only_answer_without_attachment(tmp_path):
    message = "キャンセルのご希望を承知しました。手続き状況を確認します。"
    output, env, args, answer_count, project, _ = initial_consultation_case(
        tmp_path,
        title="判定システム作成",
        message=message,
        attachment_count=0,
    )

    run = subprocess.run(args, env=env, capture_output=True, text=True)

    assert run.returncode == 0, run.stdout + run.stderr
    result = json.loads(output.read_text())
    assert result["actionable"] == 1 and result["effect"] == 1 and result["readback"] == 1
    assert len(answer_count.read_text().splitlines()) == 1
    intent = json.loads((project / "delivery/paid-remote-intent.json").read_text())
    assert intent["desired_state"]["reviewed_attachments"] == []


def test_paid_direct_production_has_no_title_keyword_route():
    tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
    functions = {node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}
    strings = {node.value for node in ast.walk(tree) if isinstance(node, ast.Constant) and isinstance(node.value, str)}
    title_reads = [
        node for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        and node.func.attr == "get" and node.args
        and isinstance(node.args[0], ast.Constant) and node.args[0].value == "title"
    ]

    assert "_consultation_candidate" not in functions
    assert not title_reads
    assert not any(
        phrase in value
        for value in strings
        for phrase in ("購入相談にのって", "購入相談に乗って", "完成(?:データ|レポート)")
    )


def test_paid_direct_routes_resubmission_paraphrase_by_semantic_mode(tmp_path):
    output, env, args, answer_count, _, _ = initial_consultation_case(
        tmp_path, title="前回回答を踏まえて条件を見直してほしい",
    )
    for name in ("targeted-90000101.json", "fresh-90000101.json", "presend-90000101.json", "official-90000101.json"):
        path = tmp_path / name
        snapshot = json.loads(path.read_text())
        for row in (snapshot["talkroom"], snapshot["orders"][0]):
            row["buyer_feedback_stage"] = "revision_request"
        put(path, snapshot)
    env["PAID_WORK_MODE"] = "answer"

    run = subprocess.run(args, env=env, capture_output=True, text=True)

    assert run.returncode == 0, run.stdout + run.stderr
    result = json.loads(output.read_text())
    assert result["actionable"] == 1 and result["effect"] == 1 and result["readback"] == 1
    assert len(answer_count.read_text().splitlines()) == 1


def test_paid_direct_ignores_consultation_words_when_semantic_mode_is_file(tmp_path):
    output, env, args, answer_count, _, _ = initial_consultation_case(tmp_path)
    env["PAID_WORK_MODE"] = "file"

    run = subprocess.run(args, env=env, capture_output=True, text=True)

    assert run.returncode == 0, run.stdout + run.stderr
    result = json.loads(output.read_text())
    assert result["actionable"] == 1 and result["effect"] == 1 and result["failed"] == 0
    assert result["items"][0]["status"] == "completed"
    assert Path(env["RUNNER_LOG"]).read_text().splitlines() == [
        "paid-work-decision", "paid-source-census", "paid-file-owner", "paid-file-verifier",
    ]
    verifier_prompt = (tmp_path / "evidence/paid-direct/90000101/file/verifier.prompt.txt").read_text()
    assert "every tool needed for that specific repair is currently available" in verifier_prompt
    assert "return needs_revision for the repairable defect first" in verifier_prompt
    assert "no independently repairable defect remains" in verifier_prompt
    assert "require a source-correspondence receipt" in verifier_prompt
    assert "a missing receipt is itself a concrete correctable defect" in verifier_prompt
    builder_prompt = (tmp_path / "evidence/paid-direct/90000101/file/builder.prompt.txt").read_text()
    assert "source_correspondence_path" in builder_prompt
    assert "source_locator, output_locator, correspondence, and verification" in builder_prompt
    assert "derive its failure class, enumerate analogous instances" in builder_prompt
    assert "Never patch only the named locator" in builder_prompt
    assert "Running shared logic earlier or under a different filename is circular proof" in builder_prompt
    assert "candidate output pixels, annotations, or manifests must never select" in builder_prompt
    assert "including modifiers, with the actual output value" in builder_prompt
    assert "include every confirmed instance in one bounded finding" in verifier_prompt
    assert "an alleged independent source census is circular" in verifier_prompt
    assert "Executing shared logic before the manifest or renaming it does not make it independent" in verifier_prompt
    assert "source-item set is selected, filtered, or confirmed using candidate" in verifier_prompt
    assert "Verify modifiers and the actual output semantic value" in verifier_prompt
    assert not answer_count.exists()


def test_paid_direct_ignores_well_formed_operator_policy_from_prior_feedback_cycle(tmp_path):
    output, env, args, answer_count, project, _ = initial_consultation_case(tmp_path)
    env["PAID_WORK_MODE"] = "file"
    put(project / "context/paid-file-operator-policy.json", {
        "version": 1, "authorized_by": "account_owner", "request_id": project.name,
        "buyer_feedback_sha256": "b" * 64, "requirements_sha256": "c" * 64,
        "directives": ["Prior-cycle direction that must not authorize the current buyer request."],
    })

    run = subprocess.run(args, env=env, capture_output=True, text=True)

    assert run.returncode == 0, run.stdout + run.stderr
    result = json.loads(output.read_text())
    assert result["actionable"] == 1 and result["effect"] == 1 and result["failed"] == 0
    assert Path(env["RUNNER_LOG"]).read_text().splitlines() == [
        "paid-work-decision", "paid-source-census", "paid-file-owner", "paid-file-verifier",
    ]
    assert not answer_count.exists()


def test_paid_direct_accepts_new_artifact_copy_with_preserved_source_mtime(tmp_path):
    output, env, args, answer_count, _, _ = initial_consultation_case(tmp_path)
    env["PAID_WORK_MODE"] = "file"
    env["PRESERVE_ARTIFACT_MTIME"] = "1"

    run = subprocess.run(args, env=env, capture_output=True, text=True)

    assert run.returncode == 0, run.stdout + run.stderr
    result = json.loads(output.read_text())
    assert result["actionable"] == 1 and result["effect"] == 1 and result["failed"] == 0
    assert Path(env["RUNNER_LOG"]).read_text().splitlines() == [
        "paid-work-decision", "paid-source-census", "paid-file-owner", "paid-file-verifier",
    ]
    assert not answer_count.exists()


def test_paid_direct_resumes_artifact_copy_with_preserved_source_mtime(tmp_path):
    root = tmp_path / "project"
    artifact = root / "delivery/delivery-v1.md"
    artifact.parent.mkdir(parents=True)
    artifact.write_text("# 納品物\n" + "確認済みの成果物です。" * 100, encoding="utf-8")
    os.utime(artifact, (1, 1))
    acceptance = root / "acceptance/file-v1.json"
    put(acceptance, {"status": "PASS", "acceptance_delta": ["buyer requirements implemented"]})
    requirements = root / "requirements/live-buyer-reply.json"
    put(requirements, {
        "feedback_sha256": "a" * 64,
        "feedback_first_observed_at": "1970-01-01T00:01:40+00:00",
        "accumulated_requirements": [],
        "accumulated_sha256": hashlib.sha256(b"[]").hexdigest(),
    })
    put(root / "state.json", {"request_id": "project", "talkroom_id": "90000101"})
    put(root / "delivery/paid-work-result.json", {
        "status": "ok", "project_root": str(root), "requirements_path": str(requirements),
        "artifact_path": str(artifact), "artifact_version": "v1",
        "acceptance_evidence_path": str(acceptance), "acceptance_status": "PASS",
        "acceptance_delta": ["buyer requirements implemented"],
        "package_sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
    })
    probe = (
        "import pathlib,sys;"
        f"sys.path.insert(0,{str(SCRIPT.parent)!r});"
        "import paid_direct;"
        f"r=paid_direct._resumable_file_bundle(pathlib.Path({str(root)!r}),pathlib.Path('unused'),{'a' * 64!r});"
        "raise SystemExit(0 if r is not None else 1)"
    )

    run = subprocess.run([sys.executable, "-c", probe], capture_output=True, text=True)

    assert run.returncode == 0, run.stdout + run.stderr


def test_paid_direct_sends_builder_concern_to_fresh_verifier_instead_of_self_authorizing(tmp_path):
    resolution = "購入前にOfficeと遠隔操作設定を販売店へ確認してください。"
    output, env, args, answer_count, _, _ = initial_consultation_case(tmp_path, message=resolution)
    env["CONSULTATION_BUILDER_ISSUE"] = "Officeと遠隔操作設定の確認が必要です。"
    env["CONSULTATION_ISSUE_RESOLUTION"] = resolution

    run = subprocess.run(args, env=env, capture_output=True, text=True)

    assert run.returncode == 0, run.stdout + run.stderr
    result = json.loads(output.read_text())
    assert result["effect"] == 1 and result["readback"] == 1 and result["failed"] == 0
    assert Path(env["RUNNER_LOG"]).read_text().splitlines() == [
        "paid-work-decision", "paid-answer-owner", "paid-answer-verifier",
    ]
    assert len(answer_count.read_text().splitlines()) == 1


def test_paid_direct_blocks_unresolved_builder_concern_before_effect(tmp_path):
    output, env, args, answer_count, _, _ = initial_consultation_case(tmp_path)
    env["CONSULTATION_BUILDER_ISSUE"] = "Officeと遠隔操作設定の確認が必要です。"
    env["CONSULTATION_ISSUE_RESOLUTION"] = "購入前にOfficeと遠隔操作設定を販売店へ確認してください。"

    run = subprocess.run(args, env=env, capture_output=True, text=True)

    assert run.returncode == 1, run.stdout + run.stderr
    result = json.loads(output.read_text())
    assert result["effect"] == 0 and result["failed"] == 1
    assert Path(env["RUNNER_LOG"]).read_text().splitlines() == [
        "paid-work-decision",
        "paid-answer-owner", "paid-answer-verifier",
        "paid-answer-owner", "paid-answer-verifier",
        "paid-answer-owner", "paid-answer-verifier",
    ]
    assert not answer_count.exists()


def test_paid_direct_long_consultation_answer_readback_deduplicates(tmp_path):
    message = "安全性を優先した購入相談です。" * 80
    output, env, args, answer_count, _, _ = initial_consultation_case(tmp_path, message=message)

    first = subprocess.run(args, env=env, capture_output=True, text=True)

    assert first.returncode == 0, first.stdout + first.stderr
    assert json.loads(output.read_text())["effect"] == 1
    targeted = tmp_path / "targeted-90000101.json"
    snapshot = json.loads(targeted.read_text())
    seller = [{"text": message[:300], "text_sha256": hashlib.sha256(message.encode()).hexdigest()}]
    for row in (snapshot["talkroom"], snapshot["orders"][0]):
        row["seller_sent_messages"] = seller
    put(targeted, snapshot)
    second = subprocess.run(args, env=env, capture_output=True, text=True)
    assert second.returncode == 0, second.stdout + second.stderr
    assert json.loads(output.read_text())["effect"] == 0
    assert len(answer_count.read_text().splitlines()) == 1


def test_paid_direct_does_not_answer_artifact_job_as_consultation(tmp_path):
    output, env, args, answer_count, _, _ = initial_consultation_case(
        tmp_path, "パソコン購入相談にのって完成レポートを納品してください",
    )
    env["PAID_WORK_MODE"] = "file"

    run = subprocess.run(args, env=env, capture_output=True, text=True)

    assert run.returncode == 0, run.stdout + run.stderr
    result = json.loads(output.read_text())
    assert result["effect"] == 1 and result["failed"] == 0
    assert result["items"][0]["status"] == "completed"
    assert Path(env["RUNNER_LOG"]).read_text().splitlines() == [
        "paid-work-decision", "paid-source-census", "paid-file-owner", "paid-file-verifier",
    ]
    assert not answer_count.exists()


def test_paid_direct_rejects_attachment_changed_after_visual_review(tmp_path):
    output, env, args, answer_count, _, attachments = initial_consultation_case(tmp_path)
    env["MUTATE_ATTACHMENT"] = attachments[0]["source_path"]

    run = subprocess.run(args, env=env, capture_output=True, text=True)

    assert run.returncode == 1, run.stdout + run.stderr
    result = json.loads(output.read_text())
    assert result["effect"] == 0 and result["failed"] == 1
    row = next(item for item in result["items"] if item["talkroom_id"] == "90000101")
    assert row["failed_step"] == "requirements_toctou"
    assert not answer_count.exists()


def test_paid_direct_rejects_buyer_attachment_directory_symlink(tmp_path):
    output, env, args, answer_count, project, attachments = initial_consultation_case(tmp_path)
    source = project / "source/buyer-attachments"
    external = tmp_path / "other-project-images"
    source.rename(external)
    source.symlink_to(external, target_is_directory=True)

    run = subprocess.run(args, env=env, capture_output=True, text=True)

    assert run.returncode == 1, run.stdout + run.stderr
    result = json.loads(output.read_text())
    assert result["effect"] == 0 and result["failed"] == 1
    assert not answer_count.exists()


def test_paid_direct_rejects_consultation_project_symlink(tmp_path):
    output, env, args, answer_count, project, _ = initial_consultation_case(tmp_path)
    first = subprocess.run(args, env=env, capture_output=True, text=True)
    assert first.returncode == 0, first.stdout + first.stderr
    message = json.loads((project / "delivery/paid-answer.json").read_text())["message"]
    targeted = tmp_path / "targeted-90000101.json"
    snapshot = json.loads(targeted.read_text())
    seller = [{"text": message, "text_sha256": hashlib.sha256(message.encode()).hexdigest()}]
    for row in (snapshot["talkroom"], snapshot["orders"][0]):
        row["seller_sent_messages"] = seller
    put(targeted, snapshot)
    external = tmp_path / "outside-project"
    project.rename(external)
    project.symlink_to(external, target_is_directory=True)

    run = subprocess.run(args, env=env, capture_output=True, text=True)

    assert run.returncode != 0, run.stdout + run.stderr
    result = json.loads(output.read_text())
    assert result["effect"] == 0 and result["failed"] == 1
    assert len(answer_count.read_text().splitlines()) == 1


def test_paid_direct_rejects_missing_result_requirements_digest_before_answer_browser(tmp_path):
    output, env, args, answer_count, _ = remote_repair_case(tmp_path)
    env["ANSWER_SEND_PERFORMED"] = "1"
    env["DROP_REQUIREMENTS_DIGEST"] = "1"

    run = subprocess.run(args, env=env, capture_output=True, text=True)

    assert run.returncode != 0, run.stdout + run.stderr
    result = json.loads(output.read_text())
    assert result["effect"] == 0
    assert not answer_count.exists()


def test_paid_direct_rejects_builder_mutation_of_collector_requirements(tmp_path):
    output, env, args, answer_count, _ = remote_repair_case(tmp_path)
    env["ANSWER_SEND_PERFORMED"] = "1"
    env["MUTATE_REQUIREMENTS_IN_BUILDER"] = "1"

    run = subprocess.run(args, env=env, capture_output=True, text=True)

    assert run.returncode != 0, run.stdout + run.stderr
    assert json.loads(output.read_text())["effect"] == 0
    assert not answer_count.exists()


def test_paid_direct_rejects_requirements_change_during_presend_readback(tmp_path):
    output, env, args, answer_count, project = remote_repair_case(tmp_path)
    env["ANSWER_SEND_PERFORMED"] = "1"
    env["MUTATE_REQUIREMENTS"] = str(project / "requirements/live-buyer-reply.json")

    run = subprocess.run(args, env=env, capture_output=True, text=True)

    assert run.returncode != 0, run.stdout + run.stderr
    assert json.loads(output.read_text())["effect"] == 0
    assert not answer_count.exists()


def test_paid_direct_rejects_verifier_owned_builder_evidence_before_review(tmp_path):
    output, env, args, answer_count, _ = remote_repair_case(tmp_path)
    env["ANSWER_SEND_PERFORMED"] = "1"
    env["BUILDER_USES_VERIFIER_EVIDENCE"] = "1"

    run = subprocess.run(args, env=env, capture_output=True, text=True)

    assert run.returncode != 0, run.stdout + run.stderr
    assert json.loads(output.read_text())["effect"] == 0
    assert (tmp_path / "runner-log").read_text().splitlines() == ["paid-remote-owner"]
    assert not answer_count.exists()


def test_paid_direct_repairs_established_remote_project_with_builder_and_verifier(tmp_path):
    output, env, args, answer_count, project = remote_repair_case(tmp_path)
    env["ANSWER_SEND_PERFORMED"] = "1"
    run = subprocess.run(args, env=env, capture_output=True, text=True)
    assert run.returncode == 0, run.stdout + run.stderr
    result = json.loads(output.read_text())
    assert result["status"] == "completed" and result["actionable"] == 1 and result["effect"] == 1 and result["readback"] == 1
    assert (tmp_path / "runner-log").read_text().splitlines() == ["paid-remote-owner", "paid-remote-verifier"]
    assert len(answer_count.read_text().splitlines()) == 1
    assert json.loads((project / "delivery/paid-answer.json").read_text())["message"] == "更新を確認しました。"
    assert "live_system_delivery_recorded" in (project / "events.jsonl").read_text()
    (tmp_path / "targeted-90000101.json").write_text((tmp_path / "official-90000101.json").read_text())
    (tmp_path / "fresh-90000101.json").write_text((tmp_path / "official-90000101.json").read_text())
    (tmp_path / "repair-90000101.json").write_text((tmp_path / "official-90000101.json").read_text())
    (tmp_path / "presend-90000101.json").write_text((tmp_path / "official-90000101.json").read_text())
    second = subprocess.run(args, env=env, capture_output=True, text=True)
    assert second.returncode == 0, second.stdout + second.stderr
    assert (tmp_path / "runner-log").read_text().splitlines() == ["paid-remote-owner", "paid-remote-verifier"]
    assert len(answer_count.read_text().splitlines()) == 1
    second_result = json.loads(output.read_text())
    assert second_result["effect"] == 0 and second_result["readback"] == 1
    (project / "evidence/agent-PAID_REMOTE_VERIFY/remote-verifier-result.json").unlink()
    env["RUNNER_STATUS"] = "blocked"
    third = subprocess.run(args, env=env, capture_output=True, text=True)
    assert third.returncode == 0, third.stdout + third.stderr
    third_result = json.loads(output.read_text())
    assert third_result["actionable"] == 0 and third_result["effect"] == 0 and third_result["readback"] == 1
    assert third_result["items"][0]["deduplicated"] is True
    assert (tmp_path / "runner-log").read_text().splitlines() == ["paid-remote-owner", "paid-remote-verifier"]
    assert len(answer_count.read_text().splitlines()) == 1


def test_paid_direct_applies_structured_review_delta_before_effect(tmp_path):
    output, env, args, answer_count, _ = remote_repair_case(tmp_path)
    env["VERIFIER_REJECT_ONCE"] = "1"
    env["ANSWER_SEND_PERFORMED"] = "1"

    run = subprocess.run(args, env=env, capture_output=True, text=True)

    assert run.returncode == 0, run.stdout + run.stderr
    assert json.loads(output.read_text())["effect"] == 1
    assert (tmp_path / "runner-log").read_text().splitlines() == [
        "paid-remote-owner", "paid-remote-verifier",
        "paid-remote-owner", "paid-remote-verifier",
    ]
    prompt = (tmp_path / "evidence/paid-direct/90000101/remote-repair/owner.prompt.txt").read_text()
    assert "buyer-ready explanation" in prompt
    assert "explain how to use the delivered system" in prompt
    assert len(answer_count.read_text().splitlines()) == 1


def test_paid_direct_stops_after_three_rejected_reviews_without_effect(tmp_path):
    output, env, args, answer_count, _ = remote_repair_case(tmp_path)
    env["VERIFIER_ALWAYS_REJECT"] = "1"
    env["ANSWER_SEND_PERFORMED"] = "1"

    run = subprocess.run(args, env=env, capture_output=True, text=True)

    assert run.returncode != 0, run.stdout + run.stderr
    assert json.loads(output.read_text())["effect"] == 0
    assert (tmp_path / "runner-log").read_text().splitlines() == [
        "paid-remote-owner", "paid-remote-verifier",
        "paid-remote-owner", "paid-remote-verifier",
        "paid-remote-owner", "paid-remote-verifier",
    ]
    assert not answer_count.exists()


def test_paid_direct_retries_cdp_transient_without_rebuilding(tmp_path):
    output, env, args, answer_count, _ = remote_repair_case(tmp_path)
    env["VERIFIER_TRANSIENT_ONCE"] = "1"
    env["ANSWER_SEND_PERFORMED"] = "1"

    run = subprocess.run(args, env=env, capture_output=True, text=True)

    assert run.returncode == 0, run.stdout + run.stderr
    assert json.loads(output.read_text())["effect"] == 1
    assert (tmp_path / "runner-log").read_text().splitlines() == [
        "paid-remote-owner", "paid-remote-verifier", "paid-remote-verifier",
    ]
    assert len(answer_count.read_text().splitlines()) == 1


def test_paid_direct_resumes_valid_builder_checkpoint_at_reviewer(tmp_path):
    output, env, args, _, _ = remote_repair_case(tmp_path, preserve_builder=True)
    project = tmp_path / "projects/recoverable-request"
    put(project / "delivery/paid-work-mode.json", {
        "version": 1, "status": "ok", "feedback_sha256": "a" * 64, "mode": "remote"
    })

    run = subprocess.run(args, env=env, capture_output=True, text=True)

    assert run.returncode == 0, run.stdout + run.stderr
    assert (tmp_path / "runner-log").read_text().splitlines() == ["paid-remote-verifier"]


def test_paid_direct_routes_actionable_live_system_resubmission_to_remote_builder(tmp_path):
    output, env, args, _, project = remote_repair_case(tmp_path)
    put(project / "delivery/paid-work-mode.json", {
        "version": 1, "status": "ok", "feedback_sha256": "a" * 64, "mode": "answer"
    })
    state = json.loads((project / "state.json").read_text())
    state.update({
        "buyer_feedback_sha256": "a" * 64,
        "active_feedback_cycle": {"buyer_feedback_sha256": "a" * 64, "action": "resubmit", "phase": "ACTIONABLE"},
        "live_system_delivery": {"target_url": "https://example.test/item"},
    })
    put(project / "state.json", state)

    run = subprocess.run(args, env=env, capture_output=True, text=True)

    assert run.returncode == 0, run.stdout + run.stderr
    assert (tmp_path / "runner-log").read_text().splitlines() == ["paid-remote-owner", "paid-remote-verifier"]
    builder_prompt = (tmp_path / "evidence/paid-direct/90000101/remote-repair/owner.prompt.txt").read_text()
    verifier_prompt = (tmp_path / "evidence/paid-direct/90000101/remote-repair/verifier.prompt.txt").read_text()
    assert "observed_state must exactly equal paid-remote-intent.json desired_state" in builder_prompt
    assert "observed_state must exactly equal paid-remote-intent.json desired_state" in verifier_prompt
    assert "accumulated requirements SHA256=" in builder_prompt
    assert "Independently verify that live target" in verifier_prompt
    assert "Only arrays named tags or keywords are unordered" in builder_prompt
    assert "Never place credential values in commands, stdout, prompts, or evidence" in builder_prompt


def test_paid_direct_routes_verifier_through_explicit_escalation(tmp_path):
    output, env, args, _, _ = remote_repair_case(tmp_path)
    runner = Path(args[args.index("--agent-runner") + 1])
    source = runner.read_text()
    source = source.replace(
        "role = a['--task-label']\n",
        "Path(os.environ['RUNNER_ARGV_LOG']).open('a').write(json.dumps(sys.argv[1:]) + '\\n')\n"
        "role = a['--task-label']\n",
    )
    runner.write_text(source, encoding="utf-8")
    env["RUNNER_ARGV_LOG"] = str(tmp_path / "runner-argv.jsonl")

    run = subprocess.run(args, env=env, capture_output=True, text=True)

    assert run.returncode == 0, run.stdout + run.stderr
    invocations = [json.loads(line) for line in (tmp_path / "runner-argv.jsonl").read_text().splitlines()]
    assert len(invocations) == 2
    assert [argv[argv.index("--task-label") + 1] for argv in invocations] == ["paid-remote-owner", "paid-remote-verifier"]
    by_label = {argv[argv.index("--task-label") + 1]: argv for argv in invocations}
    builder = by_label["paid-remote-owner"]
    verifier = by_label["paid-remote-verifier"]
    assert builder[builder.index("--task-class") + 1] == "escalation-agent"
    assert builder[builder.index("--candidate-model") + 1] == "gpt-5.6-sol"
    assert verifier[verifier.index("--task-class") + 1] == "escalation-agent"
    assert verifier[verifier.index("--candidate-model") + 1] == "gpt-5.6-sol"
    assert verifier[verifier.index("--timeout-seconds") + 1] == "1800"
    assert verifier[verifier.index("--evidence-dir") + 1].endswith("agent-PAID_REMOTE_VERIFY")
    reason = verifier[verifier.index("--escalation-reason") + 1].lower()
    assert all(term in reason for term in ("independent", "paid", "live target"))


def test_paid_direct_rejects_non_sol_verifier_before_coconala_effect(tmp_path):
    output, env, args, answer_count, _ = remote_repair_case(tmp_path)
    env["VERIFIER_SELECTED_MODEL"] = "gpt-5.6-luna"

    run = subprocess.run(args, env=env, capture_output=True, text=True)

    assert run.returncode != 0, run.stdout + run.stderr
    result = json.loads(output.read_text())
    assert result["failed_step"] == "remote_verifier"
    assert result["effect"] == 0
    assert not answer_count.exists()


def test_paid_direct_rejects_stale_verifier_runner_proof_before_effect(tmp_path):
    output, env, args, answer_count, _ = remote_repair_case(tmp_path)
    env["STALE_VERIFIER_RUNNER_PROOF"] = "1"
    env["ANSWER_SEND_PERFORMED"] = "1"

    run = subprocess.run(args, env=env, capture_output=True, text=True)

    assert run.returncode != 0, run.stdout + run.stderr
    result = json.loads(output.read_text())
    assert result["failed_step"] == "remote_verifier" and result["effect"] == 0
    assert not answer_count.exists()


def test_paid_direct_does_not_resume_historical_non_sol_verifier(tmp_path):
    output, env, args, answer_count, _ = case(tmp_path)
    summary = tmp_path / "projects/recoverable-request/evidence/agent-PAID_REMOTE_VERIFY/summary.json"
    value = json.loads(summary.read_text())
    value["selected_model"] = "gpt-5.6-luna"
    put(summary, value)

    run = subprocess.run(args, env=env, capture_output=True, text=True)

    assert run.returncode == 0, run.stdout + run.stderr
    result = json.loads(output.read_text())
    assert result["effect"] == 0 and result["actionable"] == 1 and result["readback"] == 1
    assert result["items"][0]["remote_repaired"] is True
    assert len(answer_count.read_text().splitlines()) == 1


def test_paid_direct_rebuilds_after_historical_non_sol_verifier_in_remote_mode(tmp_path):
    output, env, args, _, _ = remote_repair_case(tmp_path, preserve_verifier=True)
    project = tmp_path / "projects/recoverable-request"
    summary = project / "evidence/agent-PAID_REMOTE_VERIFY/summary.json"
    value = json.loads(summary.read_text())
    value["selected_model"] = "gpt-5.6-luna"
    put(summary, value)
    env["ANSWER_SEND_PERFORMED"] = "1"

    run = subprocess.run(args, env=env, capture_output=True, text=True)

    assert run.returncode == 0, run.stdout + run.stderr
    result = json.loads(output.read_text())
    assert result["effect"] == 1 and result["readback"] == 1
    assert (tmp_path / "runner-log").read_text().splitlines() == ["paid-remote-owner", "paid-remote-verifier"]


def test_paid_direct_rejects_verifier_delivery_mutation_before_coconala_effect(tmp_path):
    output, env, args, answer_count, _ = remote_repair_case(tmp_path)
    env["MUTATE_VERIFIER_DELIVERY"] = "1"

    run = subprocess.run(args, env=env, capture_output=True, text=True)

    assert run.returncode != 0, run.stdout + run.stderr
    result = json.loads(output.read_text())
    assert result["failed_step"] == "remote_verifier"
    assert result["effect"] == 0
    assert not answer_count.exists()


def test_paid_direct_rejects_external_verifier_runner_result_before_coconala_effect(tmp_path):
    output, env, args, answer_count, _ = remote_repair_case(tmp_path)
    env["EXTERNAL_RUNNER_RESULT"] = "1"
    env["ANSWER_SEND_PERFORMED"] = "1"

    run = subprocess.run(args, env=env, capture_output=True, text=True)

    assert run.returncode != 0, run.stdout + run.stderr
    result = json.loads(output.read_text())
    assert result["failed_step"] == "remote_verifier"
    assert result["effect"] == 0
    assert not answer_count.exists()


def test_paid_direct_rejects_same_bytes_verifier_delivery_symlink_before_coconala_effect(tmp_path):
    output, env, args, answer_count, _ = remote_repair_case(tmp_path)
    env["REPLACE_VERIFIER_DELIVERY"] = "1"
    env["ANSWER_SEND_PERFORMED"] = "1"

    run = subprocess.run(args, env=env, capture_output=True, text=True)

    assert run.returncode != 0, run.stdout + run.stderr
    result = json.loads(output.read_text())
    assert result["failed_step"] == "remote_verifier"
    assert result["effect"] == 0
    assert not answer_count.exists()


def test_paid_direct_rejects_future_verifier_evidence_before_coconala_effect(tmp_path):
    output, env, args, answer_count, _ = remote_repair_case(tmp_path)
    env["FUTURE_VERIFIER_EVIDENCE"] = "1"

    run = subprocess.run(args, env=env, capture_output=True, text=True)

    assert run.returncode != 0, run.stdout + run.stderr
    result = json.loads(output.read_text())
    assert result["failed_step"] == "remote_verifier"
    assert result["effect"] == 0
    assert not answer_count.exists()


def test_paid_direct_ignores_verifier_outside_project_managed_dir(tmp_path):
    output, env, args, answer_count, _ = case(tmp_path)
    project = tmp_path / "projects/recoverable-request"
    managed = project / "evidence/agent-PAID_REMOTE_VERIFY"
    outside = tmp_path / "evidence/agent-PAID_REMOTE_VERIFY"
    shutil.move(str(managed), str(outside))

    run = subprocess.run(args, env=env, capture_output=True, text=True)

    assert run.returncode == 0, run.stdout + run.stderr
    result = json.loads(output.read_text())
    assert result["effect"] == 0 and result["actionable"] == 1 and result["readback"] == 1
    assert result["items"][0]["remote_repaired"] is True
    assert len(answer_count.read_text().splitlines()) == 1


def test_paid_direct_rejects_symlinked_project_evidence_root_before_coconala_effect(tmp_path):
    output, env, args, answer_count, _ = case(tmp_path)
    project = tmp_path / "projects/recoverable-request"
    evidence = project / "evidence"
    outside = project / "outside-evidence"
    shutil.move(str(evidence), str(outside))
    evidence.symlink_to(outside, target_is_directory=True)
    env["ANSWER_SEND_PERFORMED"] = "1"

    run = subprocess.run(args, env=env, capture_output=True, text=True)

    assert run.returncode != 0, run.stdout + run.stderr
    result = json.loads(output.read_text())
    assert result["effect"] == 0 and result["actionable"] == 0 and result["failed"] == 1
    assert not answer_count.exists()


def test_paid_direct_rejects_stale_verifier_evidence_before_coconala_effect(tmp_path):
    output, env, args, answer_count, project = remote_repair_case(tmp_path)
    managed = project / "evidence/agent-PAID_REMOTE_VERIFY"
    managed.mkdir(parents=True, exist_ok=True)
    before = managed / "before.json"
    after = managed / "after.json"
    put(before, {"target": "https://example.test/item", "authenticated": True,
                 "observed_state": {"title": "updated", "enabled": True}})
    put(after, {"target": "https://example.test/item", "authenticated": True,
                "observed_state": {"title": "updated", "enabled": True}})
    os.utime(before, (1, 1))
    os.utime(after, (1, 1))
    runner = Path(args[args.index("--agent-runner") + 1])
    source = runner.read_text()
    source = source.replace(
        "    (managed / 'before.json').write_text(json.dumps({'target': 'https://example.test/item', 'authenticated': True, 'observed_state': desired, 'requirements_sha256': requirements_sha256, 'message_sha256': message_sha256}))\n"
        "    (managed / 'after.json').write_text(json.dumps({'target': 'https://example.test/item', 'authenticated': True, 'observed_state': desired, 'requirements_sha256': requirements_sha256, 'message_sha256': message_sha256}))\n",
        "",
    )
    runner.write_text(source, encoding="utf-8")

    run = subprocess.run(args, env=env, capture_output=True, text=True)

    assert run.returncode != 0, run.stdout + run.stderr
    result = json.loads(output.read_text())
    assert result["failed_step"] == "remote_verifier"
    assert result["effect"] == 0
    assert not answer_count.exists()


def test_paid_direct_normalizes_builder_result_from_authenticated_after_evidence(tmp_path):
    output, env, args, _, project = remote_repair_case(tmp_path)
    runner = Path(args[args.index("--agent-runner") + 1])
    source = runner.read_text()
    source = source.replace("'observed_state': desired, 'after_state_digest': digest",
                            "'observed_state': None, 'after_state_digest': '0' * 64")
    runner.write_text(source, encoding="utf-8")

    run = subprocess.run(args, env=env, capture_output=True, text=True)

    assert run.returncode == 0, run.stdout + run.stderr
    result = json.loads((project / "delivery/paid-remote-result.json").read_text())
    intent = json.loads((project / "delivery/paid-remote-intent.json").read_text())
    assert result["observed_state"] == intent["desired_state"]
    assert result["after_state_digest"] == intent["desired_state_sha256"]


def test_paid_direct_recreates_ephemeral_repair_dir_before_verifier(tmp_path):
    output, env, args, _, _ = remote_repair_case(tmp_path)
    env["REMOVE_REPAIR_DIR"] = "1"
    run = subprocess.run(args, env=env, capture_output=True, text=True)
    assert run.returncode == 0, run.stdout + run.stderr
    assert (tmp_path / "runner-log").read_text().splitlines() == ["paid-remote-owner", "paid-remote-verifier"]


def test_paid_direct_remote_prompts_name_the_real_helper_and_remote_target(tmp_path):
    output, env, args, _, project = remote_repair_case(tmp_path)
    run = subprocess.run(args, env=env, capture_output=True, text=True)
    assert run.returncode == 0, run.stdout + run.stderr
    prompt_root = tmp_path / "evidence/paid-direct/90000101/remote-repair"
    helper = str(tmp_path / "helper.py")
    for name in ("owner.prompt.txt", "verifier.prompt.txt"):
        text = (prompt_root / name).read_text()
        assert helper in text
        assert "Invoke the helper with python3, never python" in text
        assert "top-level target, authenticated=true, requirements_sha256, message_sha256, and observed_state" in text
        assert "delivery/paid-remote-intent.json" in text
        assert "Content-identical duplicate images do not satisfy a request for another image" in text
    assert "Never write remote-verifier-result.json" in (prompt_root / "owner.prompt.txt").read_text()
    assert "Write project-owned intent/result" in (prompt_root / "owner.prompt.txt").read_text()
    verifier_prompt = (prompt_root / "verifier.prompt.txt").read_text()
    assert "not the Coconala talkroom" in verifier_prompt
    assert "write only verifier-owned result/evidence" in verifier_prompt
    assert "Never modify paid-remote-intent.json" in verifier_prompt
    assert "then write both records" not in verifier_prompt


def test_paid_direct_remote_repair_refuses_stale_feedback_before_runner(tmp_path):
    output, env, args, _, _ = case(tmp_path, stale=True)
    project = tmp_path / "projects" / "recoverable-request"
    put(project / "delivery/paid-work-mode.json", {"version": 1, "status": "ok", "feedback_sha256": "a" * 64, "mode": "remote"})
    for name in ("paid-remote-intent.json", "paid-remote-result.json", "paid-answer.json"):
        (project / "delivery" / name).unlink()
    env["RUNNER_LOG"] = str(tmp_path / "runner-log")
    run = subprocess.run(args, env=env, capture_output=True, text=True)
    assert run.returncode != 0 and json.loads(output.read_text())["failed_step"] == "remote_resume"
    assert not (tmp_path / "runner-log").exists()


def test_paid_direct_remote_repair_refuses_feedback_changed_at_presend_after_runner(tmp_path):
    output, env, args, answer_count, _ = remote_repair_case(tmp_path)
    presend = json.loads((tmp_path / "presend-90000101.json").read_text())
    presend["talkroom"]["buyer_feedback_sha256"] = "b" * 64
    presend["orders"][0]["buyer_feedback_sha256"] = "b" * 64
    put(tmp_path / "presend-90000101.json", presend)
    run = subprocess.run(args, env=env, capture_output=True, text=True)
    assert run.returncode != 0, run.stdout + run.stderr
    result = json.loads(output.read_text())
    assert result["status"] == "failed" and result["failed_step"] == "presend_readback"
    assert result["effect"] == 0 and result["readback"] == 0
    assert (tmp_path / "runner-log").read_text().splitlines() == ["paid-remote-owner", "paid-remote-verifier"]
    assert not answer_count.exists()


def test_paid_direct_refuses_feedback_changed_after_send(tmp_path):
    output, env, args, answer_count, _ = case(tmp_path)
    env["ANSWER_SEND_PERFORMED"] = "1"
    official = json.loads((tmp_path / "official-90000101.json").read_text())
    official["talkroom"]["buyer_feedback_sha256"] = "b" * 64
    official["orders"][0]["buyer_feedback_sha256"] = "b" * 64
    put(tmp_path / "official-90000101.json", official)
    run = subprocess.run(args, env=env, capture_output=True, text=True)
    assert run.returncode != 0, run.stdout + run.stderr
    result = json.loads(output.read_text())
    assert result["status"] == "failed" and result["failed_step"] == "official_readback"
    assert result["effect"] == 1 and result["readback"] == 0
    assert len(answer_count.read_text().splitlines()) == 1


def test_paid_direct_binds_source_correspondence_to_real_source_and_artifact(tmp_path):
    root = tmp_path / "project"
    source = root / "source" / "buyer.pdf"
    artifact = root / "delivery" / "result.pdf"
    acceptance = root / "acceptance" / "v1.json"
    requirements = root / "requirements" / "live-buyer-reply.json"
    receipt = root / "acceptance" / "source-correspondence-v1.json"
    census = root / "acceptance" / "controller-source-census-v1.json"
    controller_receipt = root / "context" / "paid-source-census.json"
    for path, content in (
        (source, b"buyer-source"), (artifact, b"buyer-result"),
        (acceptance, b'{"status":"PASS","acceptance_delta":["mapped"]}'),
        (requirements, b'{"feedback_sha256":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"}'),
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    artifact_sha = hashlib.sha256(artifact.read_bytes()).hexdigest()
    census.write_text('{"items":["buyer-source"]}', encoding="utf-8")
    source_sha = hashlib.sha256(source.read_bytes()).hexdigest()
    put(controller_receipt, {
            "version": 1, "policy_version": "paid-source-census-v4", "requirements_sha256": "r" * 64,
        "sources": [{"path": "source/buyer.pdf", "sha256": source_sha}],
        "census_path": str(census), "census_sha256": hashlib.sha256(census.read_bytes()).hexdigest(),
    })
    put(receipt, {
        "version": 1, "status": "PASS", "artifact_sha256": artifact_sha,
        "sources": [{"path": "source/buyer.pdf", "sha256": source_sha}],
        "independent_source_census": {
            "path": str(census), "sha256": hashlib.sha256(census.read_bytes()).hexdigest(),
            "controller_receipt_path": str(controller_receipt),
            "controller_receipt_sha256": hashlib.sha256(controller_receipt.read_bytes()).hexdigest(),
        },
        "mappings": [{
            "source_locator": "page=1,measure=1", "output_locator": "page=1,measure=1",
            "correspondence": "source notes are preserved in the output part",
            "verification": "independent note and rhythm comparison",
        }],
    })
    put(root / "delivery" / "paid-work-result.json", {
        "status": "ok", "project_root": str(root), "requirements_path": str(requirements),
        "artifact_path": str(artifact), "artifact_version": "v1",
        "acceptance_evidence_path": str(acceptance), "acceptance_status": "PASS",
        "acceptance_delta": ["mapped"], "package_sha256": artifact_sha,
        "source_correspondence_path": str(receipt),
    })
    probe = (
        "import pathlib,sys;"
        f"sys.path.insert(0,{str(SCRIPT.parent)!r});"
        "import paid_direct;"
        f"m,s=paid_direct._file_bundle_snapshots(pathlib.Path({str(root)!r}));"
        "raise SystemExit(0 if 'source_correspondence' in s else 1)"
    )

    valid = subprocess.run([sys.executable, "-c", probe], capture_output=True, text=True)

    compatible_receipt = json.loads(receipt.read_text())
    binding = compatible_receipt["independent_source_census"]
    compatible_receipt["controller_receipt_path"] = binding.pop("controller_receipt_path")
    compatible_receipt["controller_receipt_sha256"] = binding.pop("controller_receipt_sha256")
    put(receipt, compatible_receipt)
    compatible = subprocess.run([sys.executable, "-c", probe], capture_output=True, text=True)

    put(receipt, {
        **compatible_receipt,
        "independent_source_census": {
            **binding,
            "controller_receipt_path": compatible_receipt["controller_receipt_path"],
            "controller_receipt_sha256": compatible_receipt["controller_receipt_sha256"],
        },
    })
    source.write_bytes(b"tampered-source")
    stale = subprocess.run([sys.executable, "-c", probe], capture_output=True, text=True)

    source.write_bytes(b"buyer-source")
    forged_census = root / "acceptance" / "owner-source-census.json"
    forged_census.write_text('{"items":["copied-production-item"]}', encoding="utf-8")
    forged_receipt = json.loads(receipt.read_text())
    forged_receipt["independent_source_census"].update({
        "path": str(forged_census), "sha256": hashlib.sha256(forged_census.read_bytes()).hexdigest(),
    })
    put(receipt, forged_receipt)
    forged = subprocess.run([sys.executable, "-c", probe], capture_output=True, text=True)

    del forged_receipt["independent_source_census"]
    put(receipt, forged_receipt)
    blocked_probe = (
        "import pathlib,sys;"
        f"sys.path.insert(0,{str(SCRIPT.parent)!r});"
        "import paid_direct;"
        f"v=paid_direct._blocked_file_bundle_for_recheck(pathlib.Path({str(root)!r}),"
        f"{{'state':'REVIEW_BLOCKED','mode':'file','artifact_sha256':{artifact_sha!r}}});"
        "raise SystemExit(0 if v else 1)"
    )
    legacy_blocked = subprocess.run([sys.executable, "-c", blocked_probe], capture_output=True, text=True)

    assert valid.returncode == 0, valid.stdout + valid.stderr
    assert compatible.returncode == 0, compatible.stdout + compatible.stderr
    assert stale.returncode != 0, stale.stdout + stale.stderr
    assert forged.returncode != 0, forged.stdout + forged.stderr
    assert legacy_blocked.returncode == 0, legacy_blocked.stdout + legacy_blocked.stderr


def add_source_score_attachment(tmp_path):
    root = tmp_path / "projects" / "recoverable-request"
    source = root / "source" / "source-score.json"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text(json.dumps({"measures": [1, 2, 3]}))
    requirements_path = root / "requirements" / "live-buyer-reply.json"
    requirements = json.loads(requirements_path.read_text())
    requirements["attachments"] = [{
        "filename": source.name, "source_path": str(source),
        "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
    }]
    put(requirements_path, requirements)


def test_source_census_visual_inputs_bind_attached_image_sha(tmp_path):
    sys.path.insert(0, str(SCRIPT.parent))
    import paid_direct

    isolated = tmp_path / "isolated"
    copied = isolated / "sources" / "0000.png"
    copied.parent.mkdir(parents=True)
    copied.write_bytes(bytes.fromhex(
        "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
        "0000000d49444154789c6360f8cfc000000301010018dd8db10000000049454e44ae426082"
    ))

    images, rows = paid_direct._source_census_visual_inputs(isolated, [{
        "path": "source/buyer.png", "sha256": "a" * 64, "isolated_path": str(copied),
    }])

    assert images == [copied]
    assert rows == [{
        "source_path": "source/buyer.png", "page": 1,
        "sha256": hashlib.sha256(copied.read_bytes()).hexdigest(),
        "kind": "source",
    }]


def test_paid_direct_never_sends_persistently_shifted_source_mapping(tmp_path):
    output, env, args, answer_count, _, _ = initial_consultation_case(tmp_path)
    add_source_score_attachment(tmp_path)
    env.update(PAID_WORK_MODE="file", SOURCE_CORRESPONDENCE_FIXTURE="always")

    run = subprocess.run(args, env=env, capture_output=True, text=True)

    assert run.returncode != 0, run.stdout + run.stderr
    result = json.loads(output.read_text())
    assert result["effect"] == 0 and result["readback"] == 0
    assert Path(env["RUNNER_LOG"]).read_text().splitlines() == [
        "paid-work-decision", "paid-source-census", "paid-file-owner", "paid-file-verifier",
        "paid-file-owner", "paid-file-verifier", "paid-file-owner", "paid-file-verifier",
    ]
    assert not answer_count.exists()


def test_paid_direct_source_census_cannot_read_project_output(tmp_path):
    output, env, args, answer_count, _, _ = initial_consultation_case(tmp_path)
    add_source_score_attachment(tmp_path)
    forbidden = tmp_path / "projects" / "recoverable-request" / "delivery" / "producer-ledger.json"
    forbidden.parent.mkdir(parents=True, exist_ok=True)
    forbidden.write_text('{"production":[1,2,3]}')
    env.update(
        PAID_WORK_MODE="file", SOURCE_CORRESPONDENCE_FIXTURE="repair",
        SOURCE_CENSUS_FORBIDDEN_PATH=str(forbidden),
    )

    run = subprocess.run(args, env=env, capture_output=True, text=True)

    assert run.returncode != 0, run.stdout + run.stderr
    result = json.loads(output.read_text())
    assert result["effect"] == 0 and result["readback"] == 0
    assert Path(env["RUNNER_LOG"]).read_text().splitlines() == [
        "paid-work-decision", "paid-source-census",
    ]
    assert not answer_count.exists()


def test_paid_direct_source_census_cannot_read_release_spec(tmp_path):
    output, env, args, answer_count, _, _ = initial_consultation_case(tmp_path)
    add_source_score_attachment(tmp_path)
    env.update(
        PAID_WORK_MODE="file", SOURCE_CORRESPONDENCE_FIXTURE="repair",
        SOURCE_CENSUS_FORBIDDEN_PATH=str(
            SCRIPT.parents[3] / "docs/loop-engineering/26-gig-loop-asis-tobe-plan.md"
        ),
    )

    run = subprocess.run(args, env=env, capture_output=True, text=True)

    assert run.returncode != 0, run.stdout + run.stderr
    result = json.loads(output.read_text())
    assert result["effect"] == 0 and result["readback"] == 0
    assert Path(env["RUNNER_LOG"]).read_text().splitlines() == [
        "paid-work-decision", "paid-source-census",
    ]
    assert not answer_count.exists()


def test_paid_direct_rechecks_repaired_source_mapping_before_sending(tmp_path):
    output, env, args, answer_count, _, _ = initial_consultation_case(tmp_path)
    add_source_score_attachment(tmp_path)
    env.update(PAID_WORK_MODE="file", SOURCE_CORRESPONDENCE_FIXTURE="repair")

    run = subprocess.run(args, env=env, capture_output=True, text=True)

    assert run.returncode == 0, run.stdout + run.stderr
    result = json.loads(output.read_text())
    assert result["effect"] == 1 and result["readback"] == 1
    assert Path(env["RUNNER_LOG"]).read_text().splitlines() == [
        "paid-work-decision", "paid-source-census", "paid-file-owner", "paid-file-verifier",
        "paid-file-owner", "paid-file-verifier",
    ]
    assert not answer_count.exists()
