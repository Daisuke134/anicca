"""LangChain chat-model bridge to the existing bounded CLI agent runner."""

from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path
from typing import Any, Sequence

from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.tools import BaseTool
from langchain_core.utils.function_calling import convert_to_openai_tool
from pydantic import Field


class ExistingRunnerChatModel(BaseChatModel):
    """Translate LangChain turns to the repository's existing runner contract."""

    runner_path: Path
    schema_path: Path
    evidence_root: Path
    workdir: Path
    python_executable: str = "python3"
    task_class: str = "diagnostic-agent"
    loop: str = "gig"
    task_label_prefix: str = "gig-FULFILLMENT-SHADOW"
    bound_tools: list[dict[str, Any]] = Field(default_factory=list, exclude=True)
    pending_content: str | None = Field(default=None, exclude=True)
    pending_tool_signature: str | None = Field(default=None, exclude=True)

    @property
    def _llm_type(self) -> str:
        return "anicca-existing-agent-runner"

    @property
    def _identifying_params(self) -> dict[str, Any]:
        return {"task_class": self.task_class, "loop": self.loop}

    def bind_tools(
        self,
        tools: Sequence[dict[str, Any] | type | BaseTool],
        *,
        tool_choice: str | None = None,
        **kwargs: Any,
    ) -> ExistingRunnerChatModel:
        del tool_choice, kwargs
        schemas = [convert_to_openai_tool(tool) for tool in tools]
        return self.model_copy(update={"bound_tools": schemas})

    @staticmethod
    def _message_payload(message: BaseMessage) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "role": message.type,
            "content": message.content,
        }
        tool_calls = getattr(message, "tool_calls", None)
        if tool_calls:
            payload["tool_calls"] = tool_calls
        tool_call_id = getattr(message, "tool_call_id", None)
        if tool_call_id:
            payload["tool_call_id"] = tool_call_id
        return payload

    def _prompt(self, messages: list[BaseMessage]) -> str:
        tool_result_present = any(message.type == "tool" for message in messages)
        contract = {
            "messages": [self._message_payload(message) for message in messages],
            # This decision graph's contract permits write_todos exactly once. Once its
            # result is in the transcript, withholding tools makes the next turn a
            # structurally final turn instead of trusting the provider not to repeat the
            # same valid tool call forever.
            "available_tools": [] if tool_result_present else self.bound_tools,
        }
        return (
            "You are one model turn inside the effect-free Coconala fulfillment shadow graph.\n"
            "Return only the JSON object required by the supplied output schema.\n"
            "Choose either a final content response or tool calls from available_tools.\n"
            "Encode each tool's argument object as JSON in args_json.\n"
            "Do not execute provider-native shell, browser, network, or filesystem tools; emit a requested tool call instead.\n"
            "Never invent a tool name. This shadow cannot perform marketplace effects.\n\n"
            + (
                "A tool result is already present. Tool calls are now forbidden; return the requested final content.\n\n"
                if tool_result_present
                else ""
            )
            + json.dumps(contract, ensure_ascii=False, separators=(",", ":"))
        )

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        del stop, run_manager, kwargs
        call_id = f"{int(time.time() * 1_000_000)}"
        evidence_dir = self.evidence_root / call_id
        evidence_dir.mkdir(parents=True, exist_ok=False)
        completed = subprocess.run(
            [
                self.python_executable,
                str(self.runner_path),
                "--task-class",
                self.task_class,
                "--prompt-stdin",
                "--schema",
                str(self.schema_path),
                "--evidence-dir",
                str(evidence_dir),
                "--task-label",
                f"{self.task_label_prefix}-{call_id}",
                "--loop",
                self.loop,
                "--workdir",
                str(self.workdir),
            ],
            input=self._prompt(messages),
            text=True,
            capture_output=True,
            check=False,
        )
        if completed.returncode != 0:
            raise RuntimeError(
                f"existing runner failed rc={completed.returncode}; "
                f"summary={completed.stdout.strip()[-1000:]}"
            )
        summary = json.loads(completed.stdout.strip().splitlines()[-1])
        result_path = Path(summary["result_path"])
        result = json.loads(result_path.read_text(encoding="utf-8"))
        tool_calls = [
            {
                "name": call["name"],
                "args": json.loads(call["args_json"]),
                "id": call["id"],
                "type": "tool_call",
            }
            for call in result["tool_calls"]
        ]
        content = result["content"]
        signature = json.dumps(tool_calls, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        if tool_calls and content:
            self.pending_content = content
            self.pending_tool_signature = signature
            content = ""
        elif tool_calls and self.pending_content and signature == self.pending_tool_signature:
            content = self.pending_content
            tool_calls = []
            self.pending_content = None
            self.pending_tool_signature = None
        message = AIMessage(content=content, tool_calls=tool_calls)
        return ChatResult(generations=[ChatGeneration(message=message)])
