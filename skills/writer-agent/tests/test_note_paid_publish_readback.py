"""The irreversible Note click must always reach authoritative readback."""

import importlib.util
import io
import json
import subprocess
import sys
import types
import urllib.error
from pathlib import Path


def test_post_click_screenshot_failure_does_not_skip_note_api_readback() -> None:
    source = (
        Path(__file__).parents[1] / "scripts" / "note-publish" / "publish-paid.py"
    ).read_text(encoding="utf-8")

    assert "try:\n            pg.screenshot(" in source


def test_note_paid_publisher_uses_its_own_cloak_context(monkeypatch) -> None:
    """A shared CDP driver crash cannot take down the Note publication tab."""
    script = Path(__file__).parents[1] / "scripts" / "note-publish" / "publish-paid.py"
    sys.path.insert(0, str(script.parent))
    monkeypatch.setitem(
        sys.modules,
        "cloakbrowser",
        types.SimpleNamespace(launch_context=lambda **kwargs: None),
    )
    spec = importlib.util.spec_from_file_location("note_publish_paid", script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    page = object()

    class Context:
        def __init__(self) -> None:
            self.cookies = None

        def add_cookies(self, cookies) -> None:
            self.cookies = cookies

        def new_page(self):
            return page

    context = Context()
    monkeypatch.setattr(module, "launch_context", lambda **kwargs: context, raising=False)

    opened_context, opened_page = module.open_authenticated_note_page(
        {"session": "secret"}
    )

    assert opened_context is context
    assert opened_page is page
    assert context.cookies == [
        {
            "name": "session",
            "value": "secret",
            "domain": ".note.com",
            "path": "/",
            "secure": True,
        }
    ]


def test_publish_click_uses_playwright_user_action(monkeypatch) -> None:
    """A synthetic DOM click must not be accepted as an irreversible publish."""
    script = Path(__file__).parents[1] / "scripts" / "note-publish" / "publish-paid.py"
    sys.path.insert(0, str(script.parent))
    monkeypatch.setitem(
        sys.modules,
        "cloakbrowser",
        types.SimpleNamespace(launch_context=lambda **kwargs: None),
    )
    spec = importlib.util.spec_from_file_location("note_publish_paid_click", script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    calls = []

    class Locator:
        def click(self, timeout) -> None:
            calls.append(timeout)

    class Page:
        def get_by_role(self, role, name, exact):
            assert role == "button"
            assert name == "投稿する"
            assert exact is True
            return Locator()

    assert module.click_publish_button(Page(), "投稿する") == "投稿する"
    assert calls == [6000]


def test_note_mutation_trace_records_api_boundary_without_secret_headers(
    monkeypatch, tmp_path
) -> None:
    """A failed publish must leave the exact Note mutation boundary to diagnose."""
    script = Path(__file__).parents[1] / "scripts" / "note-publish" / "publish-paid.py"
    sys.path.insert(0, str(script.parent))
    monkeypatch.setitem(
        sys.modules,
        "cloakbrowser",
        types.SimpleNamespace(launch_context=lambda **kwargs: None),
    )
    spec = importlib.util.spec_from_file_location("note_publish_paid_trace", script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    handlers = {}

    class Page:
        def on(self, event, handler):
            handlers[event] = handler

    class Request:
        method = "PUT"
        url = "https://note.com/api/v1/text_notes/173574051"
        post_data = '{"status":"published","price":500}'
        headers = {"cookie": "secret", "authorization": "secret"}

    class Response:
        request = Request()
        status = 422

    trace_path = tmp_path / "note-publish-mutations.json"
    trace = module.NoteMutationTrace(Page(), trace_path)
    handlers["response"](Response())
    trace.write()

    assert json.loads(trace_path.read_text()) == {
        "schema": "writer.note-publish-mutations",
        "version": 1,
        "mutations": [
            {
                "method": "PUT",
                "url": "https://note.com/api/v1/text_notes/173574051",
                "status": 422,
                "post_data": '{"status":"published","price":500}',
            }
        ],
    }


def test_paid_payload_matches_note_frontend_separator_semantics(monkeypatch) -> None:
    module = _load_module(monkeypatch, "note_publish_paid_payload")
    body = (
        '<p id="free-1">12345</p>'
        '<p id="free-2">67890</p>'
        '<p id="paid-1">paid text</p>'
    )

    payload = module.build_paid_publish_payload(
        {
            "id": 173574051,
            "name": "Title",
            "note_draft": {"body": body},
            "index": [],
            "send_notifications_flag": True,
            "slug": "slug-n-test",
        },
        price=500,
        after_chars=7,
        tags=["AI活用"],
    )

    # Note's current frontend includes the separator block in freeBody and
    # starts payBody at the following sibling.
    assert payload["free_body"] == (
        '<p id="free-1">12345</p><p id="free-2">67890</p>'
    )
    assert payload["pay_body"] == '<p id="paid-1">paid text</p>'
    assert payload["separator"] == "free-2"
    assert payload["price"] == 500
    assert payload["status"] == "published"
    assert payload["hashtags"] == ["#AI活用"]


def test_paid_publisher_imports_in_installed_cloak_runtime() -> None:
    cloak_python = (
        Path.home() / ".openclaw/skills/_shared/venv-cloak/bin/python3"
    )
    script = Path(__file__).parents[1] / "scripts" / "note-publish" / "publish-paid.py"
    result = subprocess.run(
        [
            str(cloak_python),
            "-c",
            (
                "import importlib.util;"
                f"import sys;sys.path.insert(0,{str(script.parent)!r});"
                f"s=importlib.util.spec_from_file_location('paid',{str(script)!r});"
                "m=importlib.util.module_from_spec(s);s.loader.exec_module(m)"
            ),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr


def test_native_paid_publish_uses_authenticated_numeric_note_put(monkeypatch) -> None:
    module = _load_module(monkeypatch, "note_publish_paid_native")
    seen = {}

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return b'{"data":{"result":true}}'

    def opener(request, timeout):
        seen["request"] = request
        seen["timeout"] = timeout
        return Response()

    result = module.put_paid_note(
        173574051,
        {"status": "published", "price": 500},
        {"XSRF-TOKEN": "xsrf-value", "session": "cookie-value"},
        opener=opener,
    )

    request = seen["request"]
    assert request.full_url == "https://note.com/api/v1/text_notes/173574051"
    assert request.method == "PUT"
    assert json.loads(request.data) == {"status": "published", "price": 500}
    assert request.get_header("X-xsrf-token") == "xsrf-value"
    assert request.get_header("Cookie") == "XSRF-TOKEN=xsrf-value; session=cookie-value"
    assert seen["timeout"] == 30
    assert result == {"data": {"result": True}}


def test_native_paid_publish_preserves_provider_rejection_body(monkeypatch) -> None:
    module = _load_module(monkeypatch, "note_publish_paid_rejection")

    def opener(request, timeout):
        raise urllib.error.HTTPError(
            request.full_url,
            422,
            "Unprocessable Entity",
            {},
            io.BytesIO(b'{"error":{"message":"pay_body is required"}}'),
        )

    try:
        module.put_paid_note(
            173574051,
            {"status": "published"},
            {"session": "cookie-value"},
            opener=opener,
        )
    except module.NoteNativePublishError as error:
        assert error.status == 422
        assert error.body == '{"error":{"message":"pay_body is required"}}'
    else:
        raise AssertionError("provider rejection was not preserved")


def _load_module(monkeypatch, name):
    script = Path(__file__).parents[1] / "scripts" / "note-publish" / "publish-paid.py"
    sys.path.insert(0, str(script.parent))
    monkeypatch.setitem(
        sys.modules,
        "cloakbrowser",
        types.SimpleNamespace(launch_context=lambda **kwargs: None),
    )
    spec = importlib.util.spec_from_file_location(name, script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module




# ---------------------------------------------------------------------------
# The only Note paid publish that has ever been accepted.
#
# https://note.com/anicca123/n/n190c1d92bf10 went live at 2026-08-07T00:32:19+09:00
# (`publish_at` on https://note.com/api/v3/notes/n190c1d92bf10), ¥500, owner
# anicca123, one paid `<figure>` behind the paywall.  It was produced by this
# script's own native PUT: the run receipt
# `state/runs/20260806-084924/gates/note-native-effect.json` records
# `numeric_id: 173574051`, `state: "response"` and was last written at
# 2026-08-07 00:32:20 JST -- one second after note's own `publish_at`.  The
# browser path cannot be the author: its mutation trace
# (`gates/note-publish-mutations.json`) was last written at 00:21:50 JST and
# contains a `draft_save` and no publish request at all.
#
# That payload carried exactly nineteen keys.  `image_keys` was added twenty
# hours later (1dbbc59c/86df50eb), after the only success, and every publish
# since has been rejected 422.
# ---------------------------------------------------------------------------

ACCEPTED_PAID_PUBLISH_KEYS = {
    "author_ids",
    "body_length",
    "disable_comment",
    "exclude_ai_learning_reward",
    "exclude_from_creator_top",
    "free_body",
    "hashtags",
    "index",
    "is_refund",
    "limited",
    "magazine_ids",
    "magazine_keys",
    "name",
    "pay_body",
    "price",
    "send_notifications_flag",
    "separator",
    "slug",
    "status",
}


def test_paid_payload_key_set_matches_the_only_publish_note_ever_accepted(
    monkeypatch,
) -> None:
    """Send the field set note accepted, not one field more.

    A body carrying a real note-hosted `<img>` published fine without declaring
    it: n190c1d92bf10's paid half is a single `<figure>` whose image
    (`assets.st-note.com/img/1786024684-Kjn2tLDbsW19gadfoxevPT6X.png`) is live
    and hash-verified in the run receipt.  Declaring image keys is therefore not
    a precondition of acceptance, and adding the field did not lift the 422.
    """
    module = _load_module(monkeypatch, "note_publish_paid_accepted_key_set")
    body = (
        '<p id="free-1">12345</p>'
        '<p id="free-2">67890</p>'
        '<figure id="paid-1">'
        '<img src="https://assets.st-note.com/img/1786024684-Kjn2tLDbsW19gadfoxevPT6X.png">'
        "</figure>"
    )

    payload = module.build_paid_publish_payload(
        {"id": 173574051, "name": "Title", "note_draft": {"body": body}},
        price=500,
        after_chars=7,
        tags=[],
    )

    assert set(payload) == ACCEPTED_PAID_PUBLISH_KEYS


def test_accepted_publish_response_is_not_rejected_for_a_missing_result_flag(
    monkeypatch, tmp_path
) -> None:
    """A 200 that publishes must not be reported as a logical failure.

    On 2026-08-07 note answered this exact PUT with HTTP 200 and no truthy
    `data.result`, and published the article anyway -- the receipt says
    `result: false` while note says `status: published`, `price: 500`.  Only the
    authoritative readback may decide whether the article is live.
    """
    module = _load_module(monkeypatch, "note_publish_paid_missing_result_flag")

    cookies = tmp_path / "note-cookies.json"
    cookies.write_text(json.dumps({"session": "test-only"}), encoding="utf-8")
    monkeypatch.setattr(module, "WORK", str(tmp_path))
    monkeypatch.setenv("ARTICLE_RUN_DIR", str(tmp_path))
    monkeypatch.setattr(module, "gate_run_dir", lambda *a, **k: None)
    monkeypatch.setattr(module, "assert_publish_allowed", lambda: None)
    monkeypatch.setattr(
        module.sys, "argv", ["publish-paid.py", "--key", "n190c1d92bf10", "--price", "500", "--arm"]
    )
    monkeypatch.setattr(
        module.subprocess,
        "run",
        lambda *a, **k: types.SimpleNamespace(
            returncode=0, stdout=json.dumps({"action": "publish"}), stderr=""
        ),
    )
    monkeypatch.setattr(
        module,
        "get_authenticated_note",
        lambda key, ck: {
            "id": 173574051,
            "name": "Title",
            "note_draft": {
                "body": (
                    '<p id="free-1">12345</p>'
                    '<p id="free-2">67890</p>'
                    '<figure id="paid-1"><img src="https://x/y.png"></figure>'
                )
            },
        },
    )
    monkeypatch.setattr(module, "save_paid_split_draft", lambda *a, **k: {"data": {}})
    monkeypatch.setattr(module, "put_paid_note", lambda *a, **k: {"data": {}})
    readback = []
    monkeypatch.setattr(
        module,
        "verify_note_publication",
        lambda args, managed: readback.append(args.key) or 0,
    )

    assert module.main() == 0
    assert readback == ["n190c1d92bf10"]

    effect = json.loads((tmp_path / "gates" / "note-native-effect.json").read_text())
    assert effect["state"] == "response"
    assert effect["result"] is False


# ---------------------------------------------------------------------------
# The paid split must exist on note's own draft before it is published.
#
# Measured 2026-08-07 with an authenticated read-only GET of the rejected
# article: `GET /api/v3/notes/n47735d9811e8` returns a `note_draft` whose keys
# include `separator`, and its value is null -- while the PUT that note answered
# `422 {"error":{"code":"invalid","message":"本文に利用できない内容が含まれています。"}}`
# asserted separator `d44c0a65-1a70-415e-b959-27294926cdc7`.  That id is not
# stale and not misplaced: it is top-level block 37 of 62, a `<p>`, and the
# boundary falls between `</p>` and the next top-level `<figure>`.  Rebuilding
# the payload from the body note still holds reproduces the recorded
# `payload_sha256 4e06c659...` exactly.
#
# The shape below is i0switch/ThreadsOS `NoteApiPlaywrightClient.saveDraft`
# (`src/adapters/note-api/playwright-client.ts`), which sends `free_body`,
# `pay_body`, `separator`, `limited: true` and `price` on the draft surface
# before its publish PUT.  Nothing here is invented.
# ---------------------------------------------------------------------------

THREADSOS_DRAFT_SAVE_KEYS = {
    "body",
    "body_length",
    "free_body",
    "index",
    "is_lead_form",
    "limited",
    "name",
    "pay_body",
    "price",
    "separator",
}


def test_paid_draft_save_payload_copies_the_threadsos_split_shape(monkeypatch) -> None:
    module = _load_module(monkeypatch, "note_publish_paid_draft_shape")
    body = (
        '<p id="free-1">12345</p>'
        '<p id="free-2">67890</p>'
        '<figure id="paid-1"><img src="https://x/y.png"></figure>'
    )
    publish_payload = module.build_paid_publish_payload(
        {"id": 173630036, "name": "Title", "note_draft": {"body": body}},
        price=500,
        after_chars=7,
        tags=[],
    )

    draft_payload = module.build_paid_draft_save_payload(publish_payload)

    assert set(draft_payload) == THREADSOS_DRAFT_SAVE_KEYS
    # A draft_save is not a publish. `status` is what makes a PUT irreversible.
    assert "status" not in draft_payload
    # ThreadsOS declares the split as limited on the draft surface.
    assert draft_payload["limited"] is True
    assert draft_payload["price"] == 500
    # The separator note is told about must be the one the publish asserts.
    assert draft_payload["separator"] == publish_payload["separator"] == "free-2"
    assert draft_payload["free_body"] == publish_payload["free_body"]
    assert draft_payload["pay_body"] == publish_payload["pay_body"]
    # The body is not regenerated, so the id cannot go stale between requests.
    assert draft_payload["body"] == body
    assert draft_payload["body_length"] == publish_payload["body_length"]
    assert draft_payload["name"] == publish_payload["name"]


def test_paid_draft_save_refuses_to_carry_a_status_field(monkeypatch) -> None:
    """The draft write must be structurally incapable of publishing."""
    module = _load_module(monkeypatch, "note_publish_paid_draft_status_guard")

    def opener(request, timeout):  # pragma: no cover - must never be reached
        raise AssertionError("a draft_save carrying status was sent to note")

    try:
        module.save_paid_split_draft(
            173630036,
            {"body": "<p></p>", "status": "published"},
            {"session": "cookie-value"},
            opener=opener,
        )
    except SystemExit as error:
        assert "status" in str(error)
    else:
        raise AssertionError("a draft_save carrying status was accepted")


def test_paid_draft_save_targets_the_temp_saved_draft_surface(monkeypatch) -> None:
    module = _load_module(monkeypatch, "note_publish_paid_draft_request")
    seen = {}

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return b'{"data":{"result":true}}'

    def opener(request, timeout):
        seen["request"] = request
        return Response()

    result = module.save_paid_split_draft(
        173630036,
        {"body": "<p></p>", "separator": "free-2"},
        {"XSRF-TOKEN": "xsrf-value", "session": "cookie-value"},
        opener=opener,
    )

    request = seen["request"]
    assert request.full_url == (
        "https://note.com/api/v1/text_notes/draft_save"
        "?id=173630036&is_temp_saved=true"
    )
    assert request.method == "POST"
    assert json.loads(request.data) == {"body": "<p></p>", "separator": "free-2"}
    # Same editor-origin header set as the PUT: a note 422 is not always about
    # content -- DELETE answers 422 without these headers and 200 with them.
    assert request.get_header("Origin") == "https://editor.note.com"
    assert request.get_header("Referer") == "https://editor.note.com/"
    assert request.get_header("X-requested-with") == "XMLHttpRequest"
    assert request.get_header("X-xsrf-token") == "xsrf-value"
    assert request.get_header("Cookie") == "XSRF-TOKEN=xsrf-value; session=cookie-value"
    assert result == {"data": {"result": True}}


def test_split_is_persisted_on_note_before_the_irreversible_publish(
    monkeypatch, tmp_path
) -> None:
    """note must be told the boundary on its draft before it is asked to publish it."""
    module = _load_module(monkeypatch, "note_publish_paid_draft_then_put")

    cookies = tmp_path / "note-cookies.json"
    cookies.write_text(json.dumps({"session": "test-only"}), encoding="utf-8")
    monkeypatch.setattr(module, "WORK", str(tmp_path))
    monkeypatch.setenv("ARTICLE_RUN_DIR", str(tmp_path))
    monkeypatch.setattr(module, "gate_run_dir", lambda *a, **k: None)
    monkeypatch.setattr(module, "assert_publish_allowed", lambda: None)
    monkeypatch.setattr(
        module.sys,
        "argv",
        ["publish-paid.py", "--key", "n47735d9811e8", "--price", "500", "--arm"],
    )
    monkeypatch.setattr(
        module.subprocess,
        "run",
        lambda *a, **k: types.SimpleNamespace(
            returncode=0, stdout=json.dumps({"action": "publish"}), stderr=""
        ),
    )
    body = (
        '<p id="free-1">12345</p>'
        '<p id="free-2">67890</p>'
        '<figure id="paid-1"><img src="https://x/y.png"></figure>'
    )
    monkeypatch.setattr(
        module,
        "get_authenticated_note",
        lambda key, ck: {
            "id": 173630036,
            "name": "Title",
            "note_draft": {"body": body, "separator": None},
        },
    )

    calls = []

    def record_draft(numeric_id, payload, ck, **kwargs):
        calls.append(("draft_save", numeric_id, payload))
        return {"data": {"result": True}}

    def record_put(numeric_id, payload, ck, **kwargs):
        calls.append(("put", numeric_id, payload))
        return {"data": {"result": True}}

    monkeypatch.setattr(module, "save_paid_split_draft", record_draft)
    monkeypatch.setattr(module, "put_paid_note", record_put)
    monkeypatch.setattr(module, "verify_note_publication", lambda args, managed: 0)

    assert module.main() == 0

    assert [call[0] for call in calls] == ["draft_save", "put"], (
        "the paid split must reach note's draft before the irreversible publish"
    )
    draft_payload, put_payload = calls[0][2], calls[1][2]
    assert calls[0][1] == calls[1][1] == 173630036
    # Server state and publish payload must assert the same boundary.
    assert draft_payload["separator"] == put_payload["separator"]
    assert draft_payload["free_body"] == put_payload["free_body"]
    assert draft_payload["pay_body"] == put_payload["pay_body"]
    assert "status" not in draft_payload

    effect = json.loads((tmp_path / "gates" / "note-native-effect.json").read_text())
    assert effect["draft_split_saved"] is True
    assert effect["draft_save_separator"] == put_payload["separator"]


def test_publish_is_refused_when_note_will_not_hold_the_split(
    monkeypatch, tmp_path
) -> None:
    """A draft_save that note rejects must stop the run before the PUT."""
    module = _load_module(monkeypatch, "note_publish_paid_draft_fail_closed")

    cookies = tmp_path / "note-cookies.json"
    cookies.write_text(json.dumps({"session": "test-only"}), encoding="utf-8")
    monkeypatch.setattr(module, "WORK", str(tmp_path))
    monkeypatch.setenv("ARTICLE_RUN_DIR", str(tmp_path))
    monkeypatch.setattr(module, "gate_run_dir", lambda *a, **k: None)
    monkeypatch.setattr(module, "assert_publish_allowed", lambda: None)
    monkeypatch.setattr(
        module.sys,
        "argv",
        ["publish-paid.py", "--key", "n47735d9811e8", "--price", "500", "--arm"],
    )
    monkeypatch.setattr(
        module.subprocess,
        "run",
        lambda *a, **k: types.SimpleNamespace(
            returncode=0, stdout=json.dumps({"action": "publish"}), stderr=""
        ),
    )
    monkeypatch.setattr(
        module,
        "get_authenticated_note",
        lambda key, ck: {
            "id": 173630036,
            "name": "Title",
            "note_draft": {
                "body": (
                    '<p id="free-1">12345</p>'
                    '<p id="free-2">67890</p>'
                    '<figure id="paid-1"><img src="https://x/y.png"></figure>'
                )
            },
        },
    )

    def refuse(*args, **kwargs):
        raise module.NoteNativePublishError(422, '{"error":{"code":"invalid"}}')

    monkeypatch.setattr(module, "save_paid_split_draft", refuse)

    def must_not_publish(*args, **kwargs):  # pragma: no cover - must never run
        raise AssertionError("published without the split on note's draft")

    monkeypatch.setattr(module, "put_paid_note", must_not_publish)
    monkeypatch.setattr(module, "verify_note_publication", must_not_publish)

    try:
        module.main()
    except module.NoteNativePublishError as error:
        assert error.status == 422
    else:
        raise AssertionError("a refused draft_save did not stop the publish")
