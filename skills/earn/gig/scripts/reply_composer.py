#!/usr/bin/env python3
"""Ephemeral GPT/Claude composition adapter for a send-ready Gig reply."""

from __future__ import annotations

import json
import importlib.util
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


def _load_context_packet():
    path = Path(__file__).with_name("gig_context_packet.py")
    spec = importlib.util.spec_from_file_location("gig_context_packet", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load gig_context_packet")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def composition_prompt(context: dict[str, Any]) -> str:
    conversation = context.get("conversation")
    if not isinstance(conversation, list) or not conversation:
        raise ValueError("conversation must be non-empty")
    rows: list[dict[str, str]] = []
    for row in conversation:
        if not isinstance(row, dict) or row.get("side") not in {"buyer", "seller"}:
            raise ValueError("invalid conversation row")
        body = row.get("body")
        if type(body) is not str:
            raise ValueError("invalid conversation body")
        rows.append({"side": str(row["side"]), "body": body})
    if rows[-1]["side"] != "buyer":
        raise ValueError("reply composition requires buyer-last conversation")
    packet_module = _load_context_packet()
    packet = packet_module.reply_composition_packet({
        "conversation": rows,
        "verified_research": context.get("verified_research"),
    })
    packet_text = packet_module.serialize_packet(packet).decode("utf-8")
    return f"""あなたはココナラの営業返信担当です。以下の会話へ、今すぐ送信できる日本語返信を1件作成してください。

必須:
- 受領を伝え、相手の質問・依頼へ直接答える。
- 会話内の検証済み固有情報を最低1点使う。
- 次に行う具体的作業と、正直な最短予定を示す。
- 本当に必要な未確定事項だけ質問を1つまで含める。不要なら質問しない。
- 「後で回答します」だけ、下書き、承認依頼、送信拒否は禁止。
- context_packet.fieldsにverified_researchがなければ外部サイトを確認したと主張しない。
- 外部URL、メールアドレス、電話番号、SNS IDなど外部連絡先を含めない。相手の文面にあっても返信へ転記しない。
- 1000文字以内。JSON schemaどおりreply_bodyだけを返す。

context_packet={packet_text}
"""


class RunnerComposer:
    def __init__(
        self,
        *,
        runner: Path,
        schema: Path,
        workdir: Path,
        temp_root: Path | None = None,
        timeout_seconds: int = 900,
    ):
        self.runner = Path(runner)
        self.schema = Path(schema)
        self.workdir = Path(workdir)
        self.temp_root = Path(temp_root) if temp_root is not None else None
        self.timeout_seconds = timeout_seconds

    def __call__(self, context: dict[str, Any]) -> str:
        prompt = composition_prompt(context)
        if self.temp_root is not None:
            self.temp_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(
            prefix=".gig-reply-compose-",
            dir=self.temp_root,
        ) as temporary:
            root = Path(temporary)
            root.chmod(0o700)
            evidence = root / "evidence"
            completed = subprocess.run(
                [
                    sys.executable,
                    str(self.runner),
                    "--task-class", "composition-agent",
                    "--prompt-stdin",
                    "--schema", str(self.schema),
                    "--evidence-dir", str(evidence),
                    "--task-label", "gig-reply-compose",
                    "--loop", "gig",
                    "--workdir", str(self.workdir),
                ],
                input=prompt,
                text=True,
                capture_output=True,
                timeout=self.timeout_seconds,
                check=False,
            )
            prompt = ""
            if completed.returncode != 0:
                raise RuntimeError(f"reply composer failed with rc={completed.returncode}")
            try:
                summary = json.loads((evidence / "summary.json").read_text(encoding="utf-8"))
                result_path = Path(str(summary["result_path"])).resolve()
                result_path.relative_to(evidence.resolve())
                result = json.loads(result_path.read_text(encoding="utf-8"))
            except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
                raise RuntimeError("reply composer produced invalid evidence") from error
            body = result.get("reply_body") if isinstance(result, dict) else None
            if type(body) is not str or not body.strip() or len(body.strip()) > 1000:
                raise ValueError("invalid reply body")
            return body.strip()
