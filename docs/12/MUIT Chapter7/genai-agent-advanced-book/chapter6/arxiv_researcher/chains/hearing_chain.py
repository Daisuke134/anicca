from datetime import datetime
from pathlib import Path
from typing import Literal

from langchain_core.messages import BaseMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langgraph.types import Command
from pydantic import BaseModel, Field


def load_prompt(name: str) -> str:
    prompt_path = Path(__file__).parent / "prompts" / f"{name}.prompt"
    return prompt_path.read_text().strip()


class Hearing(BaseModel):
    is_need_human_feedback: bool = Field(
        default=False, description="追加の質問が必要かどうか"
    )
    additional_question: str = Field(default="", description="追加の質問")


class HearingChain:
    def __init__(self, llm: ChatOpenAI):
        self.llm = llm
        self.current_date = datetime.now().strftime("%Y-%m-%d")

    def __call__(
        self, state: dict
    ) -> Command[Literal["human_feedback", "goal_setting"]]:
        messages = state.get("messages", [])
        hearing = self.run(messages)
        message = []

        if hearing.is_need_human_feedback:
            message = [{"role": "assistant", "content": hearing.additional_question}]

        next_node = (
            "human_feedback" if hearing.is_need_human_feedback else "goal_setting"
        )

        return Command(
            goto=next_node,
            update={"hearing": hearing, "messages": message},
        )

    def run(self, messages: list[BaseMessage]) -> Hearing:
        try:
            prompt = ChatPromptTemplate.from_template(load_prompt("hearing"))
            chain = prompt | self.llm.with_structured_output(
                Hearing,
                method="function_calling",
            )
            hearing = chain.invoke(
                {
                    "current_date": self.current_date,
                    "conversation_history": self._format_history(messages),
                }
            )
        except Exception as e:
            raise RuntimeError(f"LLMの呼び出し中にエラーが発生しました: {str(e)}")

        return hearing

    def _format_history(self, messages: list[BaseMessage]) -> str:
        return "\n".join([f"{message.type}: {message.content}" for message in messages])
