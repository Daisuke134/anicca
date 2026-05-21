from datetime import datetime
from typing import Literal

from langchain_core.messages import BaseMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langgraph.types import Command

from arxiv_researcher.chains.utils import load_prompt


class GoalOptimizer:
    def __init__(self, llm: ChatOpenAI):
        self.llm = llm
        self.current_date = datetime.now().strftime("%Y-%m-%d")

    def __call__(self, state: dict) -> Command[Literal["decompose_query"]]:
        messages = state.get("messages", [])
        goal: str = self.run(messages=messages)
        return Command(
            goto="decompose_query",
            update={"goal": goal},
        )

    def run(
        self,
        messages: list[BaseMessage],
        mode: Literal["conversation", "search"] = "conversation",
        search_results: list | None = None,
        improvement_hint: str | None = None,
    ) -> str:
        template = (
            load_prompt("goal_optimizer_search")
            if mode == "search"
            else load_prompt("goal_optimizer_conversation")
        )
        prompt = ChatPromptTemplate.from_template(template)
        chain = prompt | self.llm | StrOutputParser()

        inputs = {
            "current_date": self.current_date,
            "conversation_history": self._format_history(messages),
        }

        if mode == "search" and search_results:
            inputs["search_results"] = self._format_search_results(search_results)
        if improvement_hint:
            inputs["improvement_hint"] = improvement_hint

        return chain.invoke(inputs)

    def _format_history(self, messages: list[BaseMessage]) -> str:
        return "\n".join([f"{message.type}: {message.content}" for message in messages])

    def _format_search_results(self, results: list) -> str:
        return "\n\n".join(
            [
                f"Title: {result.get('title', '')}\n"
                f"Abstract: {result.get('abstract', '')}"
                for result in results
            ]
        )
