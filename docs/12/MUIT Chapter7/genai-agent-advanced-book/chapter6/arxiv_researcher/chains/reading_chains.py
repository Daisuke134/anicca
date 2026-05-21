from pathlib import Path
from typing import Literal

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import ConfigurableField, RunnableLambda
from langchain_openai import ChatOpenAI
from langgraph.types import Command
from pydantic import BaseModel, Field

from arxiv_researcher.models import ArxivPaper, ReadingResult
from arxiv_researcher.service.markdown_parser import MarkdownParser
from arxiv_researcher.service.markdown_storage import MarkdownStorage


def load_prompt(name: str) -> str:
    prompt_path = Path(__file__).parent / "prompts" / f"{name}.prompt"
    return prompt_path.read_text().strip()


class Sufficiency(BaseModel):
    is_sufficient: bool = Field(description="十分かどうか")
    reason: str = Field(description="十分性の判断理由")


class SetSection:
    PROMPT = load_prompt("set_section")

    def __init__(self, llm: ChatOpenAI, max_sections: int):
        self.llm = llm.configurable_fields(
            max_tokens=ConfigurableField(id="max_tokens")
        )
        self.max_sections = max_sections
        self.storage = MarkdownStorage()
        self.parser = MarkdownParser()

    def __call__(self, state: dict) -> Command[Literal["check_sufficiency"]]:
        goal = state.get("goal", "")
        reading_result = state.get("reading_result")
        paper = reading_result.paper
        selected_section_indices = state.get("selected_section_indices", [])
        sufficiency = state.get("sufficiency", None)

        chain = (
            ChatPromptTemplate.from_template(self.PROMPT)
            | self.llm.with_config(max_tokens=10)
            | StrOutputParser()
            | RunnableLambda(lambda x: [int(i) for i in x.split(",")])
        )

        sufficiency_check_str = (
            (
                f"十分性の判断結果: {sufficiency.is_sufficient}\n"
                f"十分性の判断理由: {sufficiency.reason}\n"
            )
            if sufficiency
            else ""
        )

        markdown_text = self.storage.read(reading_result.markdown_path)
        section_indices: list[int] = chain.invoke(
            {
                "title": paper.title,
                "authors": paper.authors,
                "abstract": paper.abstract,
                "context": self.parser.get_sections_overview(markdown_text),
                "goal": goal,
                "selected_section_indices": ",".join(
                    map(str, selected_section_indices)
                ),
                "sufficiency_check": sufficiency_check_str,
                "task": reading_result.task,
                "max_sections": self.max_sections,
            }
        )

        return Command(
            goto="check_sufficiency",
            update={"selected_section_indices": section_indices},
        )


class CheckSufficiency:
    PROMPT = load_prompt("check_sufficiency")

    def __init__(self, llm: ChatOpenAI, check_count: int):
        self.llm = llm
        self.check_count = check_count
        self.storage = MarkdownStorage()
        self.parser = MarkdownParser()

    def __call__(
        self, state: dict
    ) -> Command[Literal["set_section", "summarize", "mark_as_not_related"]]:
        goal = state.get("goal", "")
        reading_result = state.get("reading_result")
        paper = reading_result.paper
        selected_section_indices = state.get("selected_section_indices", [])
        check_count = state.get("check_count", 0) + 1

        markdown_text = self.storage.read(reading_result.markdown_path)
        sufficiency: Sufficiency = (
            ChatPromptTemplate.from_template(self.PROMPT)
            | self.llm.with_structured_output(
                Sufficiency,
                method="function_calling",
            )
        ).invoke(
            {
                "title": paper.title,
                "authors": paper.authors,
                "abstract": paper.abstract,
                "sections": self.parser.get_selected_sections(
                    markdown_text, selected_section_indices
                ),
                "goal": goal,
                "task": reading_result.task,
            }
        )

        next_node = (
            "summarize"
            if sufficiency.is_sufficient
            else (
                "mark_as_not_related"
                if check_count >= self.check_count
                else "set_section"
            )
        )

        return Command(
            goto=next_node,
            update={"sufficiency": sufficiency, "check_count": check_count},
        )


class Summarizer:
    PROMPT = load_prompt("summarize")

    def __init__(self, llm: ChatOpenAI):
        self.llm = llm
        self.storage = MarkdownStorage()
        self.parser = MarkdownParser()

    def __call__(self, state: dict) -> Command:
        goal: str = state.get("goal", "")
        selected_section_indices: list[int] = state.get("selected_section_indices", [])
        reading_result: ReadingResult = state["reading_result"]
        paper: ArxivPaper = reading_result.paper
        task: str = reading_result.task

        prompt = ChatPromptTemplate.from_template(self.PROMPT)
        chain = prompt | self.llm | StrOutputParser()
        markdown_text = self.storage.read(reading_result.markdown_path)
        answer = chain.invoke(
            {
                "title": paper.title,
                "authors": paper.authors,
                "abstract": paper.abstract,
                "context": self.parser.get_selected_sections(
                    markdown_text,
                    selected_section_indices,
                ),
                "goal": goal,
                "task": task,
            }
        )
        reading_result.answer = answer
        reading_result.is_related = True

        return Command(
            update={"reading_result": reading_result},
        )
