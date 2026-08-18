#!/usr/bin/env python3
"""CDP driver for Coconala retainer application threads.

Every selector below was read off the live pages on 2026-07-30 through the
sanctioned browser lease, not guessed:

  list   https://coconala.com/mypage/job_matching/applied/outsource_applications
         rows are `a[href^='/mypage/job_matching/job_talkroom/<ULID>']`;
         filter chips render as buttons "すべて 9" / "未読 1" / "未返信 3".

  thread https://coconala.com/mypage/job_matching/job_talkroom/<ULID>/talkroom
         composer  textarea#jobtalkroom-message-input  (0/3000) + button 送信する
         banner    「三者面談の候補日時が届きました。…」 + button 面談日時を選択する

  modal  「面談日時の選択」 -- a calendar restricted to the offered days, radio
         inputs whose values are the platform's own 30-minute slots
         (18:00~18:30 / 18:30~19:00 / 19:00~19:30 / 19:30~20:00), a checkbox
         「都合が合う日時がないため、別の候補の提示をお願いする」, an optional
         0/800 message box, and キャンセル / 確認に進む.
         The radio group `name` is a React Aria generated id
         (react-aria6437392866-_r_1k_) and changes on every render, so options are
         matched by their value text and never by name.

The page is Tailwind-utility-classed with no data attributes and no stable ids
except the composer, so text is the only durable handle; each expression asserts on
that text and fails closed rather than clicking the wrong control.
"""

from __future__ import annotations

import asyncio
import hashlib
import importlib.util
import json
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import websockets


def _load_local(name: str):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(f"{name}.py"))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_retainer = None
_collector = None


def _thread_module():
    global _retainer
    if _retainer is None:
        _retainer = _load_local("retainer_thread")
    return _retainer


def _collector_module():
    """coconala_queue_snapshot owns tab opening and navigation waiting; reuse it."""
    global _collector
    if _collector is None:
        _collector = _load_local("coconala_queue_snapshot")
    return _collector


APPLICATIONS_URL = (
    "https://coconala.com/mypage/job_matching/applied/outsource_applications"
)
THREAD_MESSAGE_URL_TEMPLATE = (
    "https://coconala.com/mypage/job_matching/job_talkroom/{}/talkroom"
)

COMPOSER_SELECTOR = "#jobtalkroom-message-input"
SEND_BUTTON_TEXT = "送信する"
SELECT_INTERVIEW_BUTTON_TEXT = "面談日時を選択する"
CONFIRM_STEP_BUTTON_TEXT = "確認に進む"
CANCEL_BUTTON_TEXT = "キャンセル"
NO_SUITABLE_SLOT_CHECKBOX_TEXT = "都合が合う日時がないため、別の候補の提示をお願いする"
MODAL_TITLE_TEXT = "面談日時の選択"
COMPOSER_MAX_CHARS = 3000
MODAL_MESSAGE_MAX_CHARS = 800

_SLOT_LABEL = re.compile(r"^\d{1,2}:\d{2}[~〜]\d{1,2}:\d{2}$")


def thread_message_url(application_id: str) -> str:
    """Message view URL for a retainer application thread."""
    if not _thread_module().is_retainer_id(application_id):
        raise ValueError("not a retainer application id")
    return THREAD_MESSAGE_URL_TEMPLATE.format(str(application_id).strip())


def slot_label(start_local: str, end_local: str) -> str:
    """The radio value the modal renders for one slot, e.g. 18:00~18:30."""
    label = f"{start_local}~{end_local}"
    if not _SLOT_LABEL.fullmatch(label):
        raise ValueError("invalid slot label")
    return label


def fill_message_expression(body: str) -> str:
    """Type a reply into the thread composer. Does not send."""
    if not isinstance(body, str) or not body.strip():
        raise ValueError("empty message body")
    if len(body) > COMPOSER_MAX_CHARS:
        raise ValueError("message exceeds the composer limit")
    # Polls for the same reason the modal opener does: this page hydrates, and an
    # immediate query reports a composer that is merely not rendered yet as missing.
    return (
        "(async()=>{const wait=ms=>new Promise(r=>setTimeout(r,ms));"
        "let t=document.querySelector(%s);"
        "for(let i=0;i<60&&!t;i++){await wait(250);t=document.querySelector(%s);}"
        "if(!t)return JSON.stringify({ok:false,error:'composer_missing'});"
        "const set=Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype,'value').set;"
        "set.call(t,%s);t.dispatchEvent(new Event('input',{bubbles:true}));"
        "t.dispatchEvent(new Event('change',{bubbles:true}));"
        "return JSON.stringify({ok:t.value===%s,length:t.value.length});})()"
        % (_js(COMPOSER_SELECTOR), _js(COMPOSER_SELECTOR), _js(body), _js(body))
    )


def send_message_expression(expected_body: str) -> str:
    """Click 送信する only while the composer still holds exactly our text."""
    return (
        "(()=>{const t=document.querySelector(%s);"
        "if(!t||t.value!==%s)return JSON.stringify({ok:false,error:'composer_drifted'});"
        "const b=[...document.querySelectorAll('button')].filter(x=>(x.innerText||'').trim()===%s);"
        "if(b.length!==1)return JSON.stringify({ok:false,error:'send_button_ambiguous',count:b.length});"
        "if(b[0].disabled)return JSON.stringify({ok:false,error:'send_disabled'});"
        "b[0].click();return JSON.stringify({ok:true});})()"
        % (_js(COMPOSER_SELECTOR), _js(expected_body), _js(SEND_BUTTON_TEXT))
    )


def open_interview_modal_expression() -> str:
    """Open 面談日時の選択. Opening reveals options; it confirms nothing."""
    # The thread is a hydrating SPA: a tab that has finished navigating has not
    # necessarily rendered its controls yet. Measured live 2026-07-31 -- the very
    # same button that THREAD_EXPRESSION reports as present (it polls for body text
    # first) was absent to an expression that looked immediately. Polling here is
    # what makes "the button is gone" mean the booking happened rather than "we
    # asked too early", which is the signal the whole confirmation check rests on.
    return (
        "(async()=>{const wait=ms=>new Promise(r=>setTimeout(r,ms));"
        "const find=()=>[...document.querySelectorAll('button')]"
        ".find(x=>(x.innerText||'').trim()===%s);"
        "let b=find();for(let i=0;i<60&&!b;i++){await wait(250);b=find();}"
        "if(!b)return JSON.stringify({ok:false,error:'select_button_absent'});"
        "b.click();await wait(3000);"
        "const d=document.querySelector('[role=dialog]');"
        "if(!d||!(d.innerText||'').includes(%s))return JSON.stringify({ok:false,error:'modal_absent'});"
        "return JSON.stringify({ok:true,"
        "slots:[...document.querySelectorAll('input[type=radio]')].map(x=>String(x.value||'')),"
        "has_no_suitable_slot_checkbox:[...document.querySelectorAll('input[type=checkbox]')]"
        ".some(x=>((x.closest('label')||x.parentElement||{}).innerText||'').includes(%s)),"
        "confirm_enabled:![...document.querySelectorAll('button')]"
        ".filter(x=>(x.innerText||'').trim()===%s).every(x=>x.disabled)});})()"
        % (
            _js(SELECT_INTERVIEW_BUTTON_TEXT),
            _js(MODAL_TITLE_TEXT),
            _js(NO_SUITABLE_SLOT_CHECKBOX_TEXT),
            _js(CONFIRM_STEP_BUTTON_TEXT),
        )
    )


def close_interview_modal_expression() -> str:
    """Leave the modal without confirming anything."""
    return (
        "(()=>{const b=[...document.querySelectorAll('button')]"
        ".find(x=>(x.innerText||'').trim()===%s);if(b)b.click();"
        "return JSON.stringify({ok:!document.querySelector('[role=dialog]')});})()"
        % _js(CANCEL_BUTTON_TEXT)
    )


def select_slot_expression(
    *, year: int, month: int, day_of_month: int, slot_label_text: str
) -> str:
    """Pick one offered day and one 30-minute option. Still does not confirm.

    The month is part of the address, not decoration. Measured live 2026-07-31: the
    calendar opens on 2026年7月, whose grid renders June's tail and August's head, so
    "3" exists twice in one page and the offered 8/3 is not on it at all. Matching a
    bare day number would therefore have been a coin flip across a month boundary.
    So this walks 「次へ」 until the rendered header IS the target month, and only then
    matches the day -- and requires exactly one ENABLED match, because the platform
    disables every day it did not offer (only 31 was selectable on the July page).
    """
    for name, value in (("year", year), ("month", month), ("day", day_of_month)):
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError(f"invalid {name}")
    if not 1 <= month <= 12 or not 1 <= day_of_month <= 31 or not 2000 <= year <= 2100:
        raise ValueError("invalid calendar target")
    if not _SLOT_LABEL.fullmatch(str(slot_label_text)):
        raise ValueError("invalid slot label")
    return (
        "(async()=>{const wait=ms=>new Promise(r=>setTimeout(r,ms));"
        "const dlg=()=>document.querySelector('[role=dialog]');"
        "if(!dlg())return JSON.stringify({ok:false,error:'modal_absent'});"
        "const header=()=>{const n=[...dlg().querySelectorAll('*')]"
        ".filter(x=>x.children.length===0&&/^\\d{4}年\\d{1,2}月$/.test((x.innerText||'').trim()));"
        "return n.length?(n[0].innerText||'').trim():''};"
        "const want=%s;let seen=header();"
        "for(let i=0;i<12&&seen!==want;i++){"
        "const nx=[...dlg().querySelectorAll('button')]"
        ".filter(x=>x.getAttribute('aria-label')==='次へ'&&!x.disabled"
        "&&x.dataset.disabled!=='true');"
        "if(!nx.length)break;nx[0].click();await wait(700);seen=header();}"
        "if(seen!==want)return JSON.stringify({ok:false,error:'month_unreachable',header:seen});"
        # The <td> is scenery. React Aria puts usePress on an inner div[role=button]
        # carrying data-react-aria-pressable, and marks a day it did not offer with
        # data-unavailable / data-disabled, and a neighbouring month's day with
        # data-outside-month. Measured live 2026-07-31: clicking the <td> silently
        # did nothing, the pre-selected day stayed selected, and the confirmation
        # step then offered 07月31日 -- the exact slot the scheduler had REJECTED as
        # a calendar conflict. usePress also listens on pointer events, so a bare
        # .click() is not enough on its own.
        "const days=[...dlg().querySelectorAll('[role=button][data-react-aria-pressable]')]"
        ".filter(x=>(x.innerText||'').trim()===String(%d)"
        "&&x.dataset.disabled!=='true'&&x.dataset.unavailable!=='true'"
        "&&x.dataset.outsideMonth!=='true'&&x.getAttribute('aria-disabled')!=='true');"
        "if(days.length!==1)return JSON.stringify({ok:false,error:'day_ambiguous',count:days.length,header:seen});"
        "const cell=days[0];"
        "const press=t=>cell.dispatchEvent(new PointerEvent(t,{bubbles:true,cancelable:true,"
        "pointerId:1,pointerType:'mouse',isPrimary:true,button:0,buttons:t==='pointerdown'?1:0}));"
        "press('pointerdown');press('pointerup');cell.click();await wait(1500);"
        "const r=[...document.querySelectorAll('input[type=radio]')]"
        ".filter(x=>String(x.value||'')===%s);"
        "if(r.length!==1)return JSON.stringify({ok:false,error:'slot_absent',count:r.length});"
        "r[0].click();await wait(600);"
        "return JSON.stringify({ok:r[0].checked===true,header:seen,"
        "day_state:Object.assign({},cell.dataset),"
        "selected:String(r[0].value||'')});})()"
        % (
            _js(f"{year}年{month}月"),
            day_of_month,
            _js(slot_label_text),
        )
    )


def request_other_candidates_expression(message: str) -> str:
    """Tick 「都合が合う日時がないため…」 and put our alternatives in the box."""
    if not isinstance(message, str) or not message.strip():
        raise ValueError("empty counter-proposal message")
    if len(message) > MODAL_MESSAGE_MAX_CHARS:
        raise ValueError("counter-proposal exceeds the modal limit")
    return (
        "(async()=>{const wait=ms=>new Promise(r=>setTimeout(r,ms));"
        "const d=document.querySelector('[role=dialog]');"
        "if(!d)return JSON.stringify({ok:false,error:'modal_absent'});"
        "const c=[...d.querySelectorAll('input[type=checkbox]')]"
        ".filter(x=>((x.closest('label')||x.parentElement||{}).innerText||'').includes(%s));"
        "if(c.length!==1)return JSON.stringify({ok:false,error:'checkbox_absent'});"
        "if(!c[0].checked){c[0].click();await wait(600);}"
        "const t=d.querySelector('textarea');"
        "if(!t)return JSON.stringify({ok:false,error:'modal_textarea_absent'});"
        "const set=Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype,'value').set;"
        "set.call(t,%s);t.dispatchEvent(new Event('input',{bubbles:true}));"
        "return JSON.stringify({ok:c[0].checked===true&&t.value===%s});})()"
        % (
            _js(NO_SUITABLE_SLOT_CHECKBOX_TEXT),
            _js(message),
            _js(message),
        )
    )


def advance_to_confirmation_expression() -> str:
    """Press 確認に進む. The caller must already hold a confirm authorization."""
    return (
        "(async()=>{const wait=ms=>new Promise(r=>setTimeout(r,ms));"
        "const d=document.querySelector('[role=dialog]');"
        "if(!d)return JSON.stringify({ok:false,error:'modal_absent'});"
        "const b=[...d.querySelectorAll('button')].filter(x=>(x.innerText||'').trim()===%s);"
        "if(b.length!==1)return JSON.stringify({ok:false,error:'confirm_button_ambiguous'});"
        "if(b[0].disabled)return JSON.stringify({ok:false,error:'nothing_selected'});"
        "b[0].click();await wait(2500);"
        "return JSON.stringify({ok:true,dialog_text:(document.querySelector('[role=dialog]')||{}).innerText||''});})()"
        % _js(CONFIRM_STEP_BUTTON_TEXT)
    )


FINAL_CONFIRM_BUTTON_TEXT = "日程を確定する"
AMEND_BUTTON_TEXT = "修正する"
CONFIRMATION_TITLE_TEXT = "面談日時の確認"


def confirmation_date_text(*, year: int, month: int, day: int) -> str:
    """How the confirmation step spells a date: 2026年07月31日 (zero padded)."""
    return f"{int(year)}年{int(month):02d}月{int(day):02d}日"


def confirm_interview_expression(*, expected_date: str, expected_slot: str) -> str:
    """Press 日程を確定する ONLY if the dialog names the slot we decided on.

    This is the last gate before an irreversible, client-visible commitment, and it
    is the one that has to assume every earlier step lied. It earned its place on
    2026-07-31: the day click was a silent no-op, and this screen was offering
    07月31日 -- a slot the scheduler had rejected as a conflict -- while every prior
    step had returned ok. Reading the summary the platform itself renders, and
    refusing to press when it disagrees, is the only check that catches that whole
    class of failure at once.
    """
    if not str(expected_date).strip() or not _SLOT_LABEL.fullmatch(str(expected_slot)):
        raise ValueError("invalid confirmation expectation")
    return (
        "(async()=>{const wait=ms=>new Promise(r=>setTimeout(r,ms));"
        "const d=document.querySelector('[role=dialog]');"
        "if(!d)return JSON.stringify({ok:false,error:'confirmation_absent'});"
        "const text=(d.innerText||'');"
        "if(!text.includes(%s))return JSON.stringify({ok:false,error:'not_confirmation_step',text:text.slice(0,400)});"
        "if(!text.includes(%s)||!text.includes(%s))"
        "return JSON.stringify({ok:false,error:'confirmation_shows_another_slot',text:text.slice(0,400)});"
        "const b=[...d.querySelectorAll('button')].filter(x=>(x.innerText||'').trim()===%s);"
        "if(b.length!==1)return JSON.stringify({ok:false,error:'confirm_button_ambiguous',count:b.length});"
        "if(b[0].disabled)return JSON.stringify({ok:false,error:'confirm_button_disabled'});"
        "b[0].click();await wait(4000);"
        "const after=document.querySelector('[role=dialog]');"
        "return JSON.stringify({ok:true,dialog_open:!!after,"
        "confirmed_text:text.slice(0,300)});})()"
        % (
            _js(CONFIRMATION_TITLE_TEXT),
            _js(str(expected_date)),
            _js(str(expected_slot)),
            _js(FINAL_CONFIRM_BUTTON_TEXT),
        )
    )


def dialog_state_expression() -> str:
    """Read the open dialog without touching it: its text and its enabled buttons.

    確認に進む leads to a second step whose wording was not captured on 2026-07-30, so
    the driver reads what is actually rendered instead of assuming a button name.
    """
    return (
        "(()=>{const d=document.querySelector('[role=dialog]');"
        "if(!d)return JSON.stringify({ok:true,open:false,text:'',buttons:[]});"
        "return JSON.stringify({ok:true,open:true,text:(d.innerText||'').slice(0,1200),"
        "buttons:[...d.querySelectorAll('button')]"
        ".map(b=>({label:(b.innerText||'').trim(),disabled:!!b.disabled}))});})()"
    )


def click_dialog_button_expression(label: str) -> str:
    """Click exactly one enabled dialog button, by its exact rendered label."""
    if not isinstance(label, str) or not label.strip():
        raise ValueError("empty dialog button label")
    return (
        "(async()=>{const wait=ms=>new Promise(r=>setTimeout(r,ms));"
        "const d=document.querySelector('[role=dialog]');"
        "if(!d)return JSON.stringify({ok:false,error:'modal_absent'});"
        "const b=[...d.querySelectorAll('button')].filter(x=>(x.innerText||'').trim()===%s);"
        "if(b.length!==1)return JSON.stringify({ok:false,error:'button_ambiguous',count:b.length});"
        "if(b[0].disabled)return JSON.stringify({ok:false,error:'button_disabled'});"
        "b[0].click();await wait(3000);"
        "const after=document.querySelector('[role=dialog]');"
        "return JSON.stringify({ok:true,dialog_open:!!after,"
        "dialog_text:after?(after.innerText||'').slice(0,1200):''});})()"
        % _js(label)
    )


def _js(value: str) -> str:
    """Embed a Python string as a JavaScript string literal."""
    import json as _json

    return _json.dumps(str(value), ensure_ascii=False)


JST = timezone(timedelta(hours=9))
_THREAD_STAMP = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$")


class RetainerThreadUnhealthy(RuntimeError):
    """A thread reading that must not be mistaken for a thread with nothing on it."""


def _thread_timestamp(value: Any) -> datetime:
    """Thread rows render local minutes: 2026-07-30 00:32, Asia/Tokyo."""
    text = str(value or "").strip()
    if not _THREAD_STAMP.fullmatch(text):
        raise RetainerThreadUnhealthy("missing_message_timestamp")
    return datetime.fromisoformat(text).replace(tzinfo=JST).astimezone(timezone.utc)


def _inbound_timestamp(value: Any) -> datetime:
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("inbound timestamp must include a timezone")
    return parsed.astimezone(timezone.utc)


def answer_observation(
    state: dict[str, Any], *, thread_id: str, inbound_sent_at: str
) -> dict[str, Any]:
    """Has anything from US landed at or after the client message we owe an answer to?

    Deliberately biased toward "yes". Thread rows carry minutes, not seconds, so an
    equal timestamp is ambiguous -- and the two ways to be wrong are not symmetric:
    a false "yes" costs one late reply, a false "no" sends a stranger the same thing
    twice. `>=` is the direction that cannot double-send.
    """
    origin = _inbound_timestamp(inbound_sent_at)
    matches = [
        message for message in state.get("messages", [])
        if message.get("side") == "seller"
        and _thread_timestamp(message.get("sent_at")) >= origin
    ]
    return {
        "thread_id": str(thread_id),
        "answered": bool(matches),
        "answer_count": len(matches),
        "seller_sent_at": (
            _thread_timestamp(matches[-1]["sent_at"]).isoformat() if matches else None
        ),
        "seller_body_sha256": (
            hashlib.sha256(str(matches[-1].get("body") or "").encode("utf-8")).hexdigest()
            if matches else None
        ),
        "seller_body_snippet": (
            str(matches[-1].get("body") or "")[:30] if matches else None
        ),
    }


async def _evaluate(ws_url: str, expression: str) -> dict[str, Any]:
    """Run one of this module's expressions and fail closed on its own `ok` flag."""
    collector = _collector_module()
    async with websockets.connect(ws_url, ping_interval=None, open_timeout=10) as ws:
        result = await collector.call(
            ws,
            1,
            "Runtime.evaluate",
            {"expression": expression, "returnByValue": True, "awaitPromise": True},
        )
    raw = result.get("result", {}).get("value")
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError as error:
            raise RuntimeError("browser expression returned invalid JSON") from error
    if not isinstance(raw, dict):
        raise RuntimeError("browser expression returned no structured result")
    if raw.get("ok") is not True:
        raise RuntimeError(str(raw.get("error") or "browser expression failed"))
    return raw


def validate_thread_dom(dom: dict[str, Any], expected_url: str) -> None:
    """An unreadable thread is not an empty thread."""
    if not isinstance(dom, dict):
        raise RetainerThreadUnhealthy("invalid_dom")
    title = str(dom.get("title") or "")
    path = urlsplit(str(dom.get("url") or "")).path.rstrip("/")
    if path.startswith("/login") or "ログイン" in title:
        raise RetainerThreadUnhealthy("login")
    if dom.get("not_found_present") is True:
        raise RetainerThreadUnhealthy("not_found")
    if dom.get("error_present") is True:
        raise RetainerThreadUnhealthy("error_page")
    if path != urlsplit(expected_url).path.rstrip("/"):
        raise RetainerThreadUnhealthy("unexpected_url")
    if dom.get("container_present") is not True:
        raise RetainerThreadUnhealthy("missing_container")


class CoconalaCdpRetainerBrowser:
    """One authenticated tab on one retainer thread, for reading and for acting.

    Only pages this class opens are ever closed; the shared persistent browser and
    its context are never touched.  Every readback opens a FRESH tab rather than
    re-evaluating in the tab that just clicked, because a single-page app can keep
    showing an optimistic local update -- the whole point of the readback is to make
    the platform, not our own process, the witness.
    """

    def __init__(
        self,
        helper: Path,
        application_id: str,
        *,
        hidden: bool = False,
        background: bool = True,
        settle_seconds: float = 2.5,
    ):
        self.helper = Path(helper)
        self.application_id = str(application_id)
        self.url = thread_message_url(self.application_id)
        self.hidden = hidden
        self.background = background and not hidden
        self.settle_seconds = settle_seconds
        self.tab: Any = None

    def __enter__(self) -> "CoconalaCdpRetainerBrowser":
        self.tab = self._open_tab()
        return self

    def __exit__(self, *args: object) -> None:
        if self.tab is not None:
            self.tab.__exit__(*args)
            self.tab = None

    def _open_tab(self) -> Any:
        collector = _collector_module()
        tab = collector.DefaultTab(
            self.helper, self.url, hidden=self.hidden, background=self.background,
        )
        tab.__enter__()
        return tab

    def _read(self, ws_url: str) -> dict[str, Any]:
        collector = _collector_module()
        retainer = _thread_module()
        dom = asyncio.run(collector.inspect_message_page(
            ws_url, retainer.THREAD_EXPRESSION, self.url,
        ))
        validate_thread_dom(dom, self.url)
        dom["application_id"] = self.application_id
        state = retainer.thread_state(dom)
        state["url"] = str(dom.get("url") or "")
        state["banner_text"] = str(dom.get("banner_text") or "")
        return state

    def read_state(self) -> dict[str, Any]:
        if self.tab is None:
            raise RuntimeError("browser tab is not open")
        return self._read(self.tab.ws)

    def read_fresh(self) -> dict[str, Any]:
        """Authoritative readback: a brand-new tab, a brand-new render."""
        time.sleep(self.settle_seconds)
        tab = self._open_tab()
        try:
            return self._read(tab.ws)
        finally:
            tab.__exit__(None, None, None)

    def _settle(self) -> dict[str, Any]:
        """Let the SPA finish arriving before an expression is allowed to act.

        Measured live 2026-07-31: acting on a tab that had merely finished
        NAVIGATING raised `Execution context was destroyed` -- the thread route
        re-renders after load, and a long-lived evaluate is killed with the old
        context. read_state() polls until the DOM is really there, so running it
        first turns that race into a wait.
        """
        return self.read_state()

    # --- message composer -------------------------------------------------------
    def send_reply(self, body: str) -> None:
        if self.tab is None:
            raise RuntimeError("browser tab is not open")
        self._settle()
        asyncio.run(_evaluate(self.tab.ws, fill_message_expression(body)))
        time.sleep(1.0)
        asyncio.run(_evaluate(self.tab.ws, send_message_expression(body)))

    # --- interview modal --------------------------------------------------------
    def open_interview_modal(self) -> dict[str, Any]:
        if self.tab is None:
            raise RuntimeError("browser tab is not open")
        self._settle()
        return asyncio.run(_evaluate(self.tab.ws, open_interview_modal_expression()))

    def select_slot(
        self, *, year: int, month: int, day_of_month: int, slot_label_text: str
    ) -> dict[str, Any]:
        if self.tab is None:
            raise RuntimeError("browser tab is not open")
        return asyncio.run(_evaluate(
            self.tab.ws,
            select_slot_expression(
                year=year, month=month, day_of_month=day_of_month,
                slot_label_text=slot_label_text,
            ),
        ))

    def request_other_candidates(self, message: str) -> dict[str, Any]:
        if self.tab is None:
            raise RuntimeError("browser tab is not open")
        return asyncio.run(_evaluate(
            self.tab.ws, request_other_candidates_expression(message)
        ))

    def advance_to_confirmation(self) -> dict[str, Any]:
        if self.tab is None:
            raise RuntimeError("browser tab is not open")
        return asyncio.run(_evaluate(self.tab.ws, advance_to_confirmation_expression()))

    def confirm_interview(self, *, expected_date: str, expected_slot: str) -> dict[str, Any]:
        if self.tab is None:
            raise RuntimeError("browser tab is not open")
        return asyncio.run(_evaluate(
            self.tab.ws,
            confirm_interview_expression(
                expected_date=expected_date, expected_slot=expected_slot,
            ),
        ))

    def dialog_state(self) -> dict[str, Any]:
        if self.tab is None:
            raise RuntimeError("browser tab is not open")
        return asyncio.run(_evaluate(self.tab.ws, dialog_state_expression()))

    def click_dialog_button(self, label: str) -> dict[str, Any]:
        if self.tab is None:
            raise RuntimeError("browser tab is not open")
        return asyncio.run(_evaluate(self.tab.ws, click_dialog_button_expression(label)))

    def close_interview_modal(self) -> None:
        if self.tab is None:
            return
        try:
            asyncio.run(_evaluate(self.tab.ws, close_interview_modal_expression()))
        except RuntimeError:
            pass
