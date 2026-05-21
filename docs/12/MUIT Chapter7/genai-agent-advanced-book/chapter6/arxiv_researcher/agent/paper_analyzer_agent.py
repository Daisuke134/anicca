from typing import TypedDict

from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command

from arxiv_researcher.chains.reading_chains import (
    CheckSufficiency,
    SetSection,
    Sufficiency,
    Summarizer,
)
from arxiv_researcher.models import ArxivPaper, ReadingResult
from arxiv_researcher.settings import settings


class PaperAnalyzerAgentInputState(TypedDict):
    goal: str
    reading_result: ReadingResult


class PaperAnalyzerAgentProcessingState(TypedDict):
    selected_section_indices: list[int]
    sufficiency: Sufficiency
    check_count: int


class PaperAnalyzerAgentOutputState(TypedDict):
    reading_result: ReadingResult


class PaperAnalyzerAgentState(
    PaperAnalyzerAgentInputState,
    PaperAnalyzerAgentProcessingState,
    PaperAnalyzerAgentOutputState,
):
    pass


class PaperAnalyzerAgent:
    # 読み取りを行う最大セクション数
    MAX_SECTIONS = 5

    # 十分性をチェックする回数
    CHECK_COUNT = 3

    def __init__(
        self,
        llm: ChatOpenAI,
    ):
        self.set_section = SetSection(llm, max_sections=self.MAX_SECTIONS)
        self.check_sufficiency = CheckSufficiency(llm, check_count=self.CHECK_COUNT)
        self.summarizer = Summarizer(llm)
        self.graph = self._create_graph()

    def _create_graph(self) -> CompiledStateGraph:
        workflow = StateGraph(
            PaperAnalyzerAgentState,
            input=PaperAnalyzerAgentInputState,
            output=PaperAnalyzerAgentOutputState,
        )
        workflow.add_node("set_section", self.set_section)
        workflow.add_node("check_sufficiency", self.check_sufficiency)
        workflow.add_node("mark_as_not_related", self._mark_as_not_related)
        workflow.add_node("summarize", self.summarizer)

        workflow.set_entry_point("set_section")
        workflow.set_finish_point("mark_as_not_related")
        workflow.set_finish_point("summarize")

        return workflow.compile()

    def _mark_as_not_related(self, state: PaperAnalyzerAgentState) -> Command:
        reading_result = state.get("reading_result")
        if reading_result is None:
            raise ValueError("reading_result is not set")
        reading_result.is_related = False
        return Command(
            update={"reading_result": reading_result},
        )


graph = PaperAnalyzerAgent(llm=settings.fast_llm).graph

if __name__ == "__main__":
    # uv run python -m arxiv_researcher.agent.paper_analyzer_agent fixtures/2408.14317.md
    import sys
    from pathlib import Path

    # コマンドラインからテスト用のmarkdownファイルを読み込む
    markdown_file_path = Path(sys.argv[1])
    reading_result = ReadingResult(
        id=0,
        task="研究の意義についてまとめよ",
        paper=ArxivPaper(
            title="Claim Verification in the Age of Large Language Models: A Survey",
            authors=[
                "Alphaeus Dmonte",
                "Roland Oruche",
                "Marcos Zampieri",
                "Prasad Calyam",
                "Isabelle Augenstein",
            ],
            abstract="The large and ever-increasing amount of data available on the Internet coupled with the laborious task of manual claim and fact verification has sparked the interest in the development of automated claim verification systems. 1 Several deep learning and transformer-based models have been proposed for this task over the years. With the i ntroduction of Large Language Models (LLMs) and their superior performance in several NLP tasks, we have seen a surge of LLM-based approaches to claim verification along with the use of novel methods such as Retrieval Augmented Generation (RAG). In this survey, we present a comprehensive account of recent claim verification frameworks using LLMs. We describe the different components of the claim v erification pipeline used in these frameworks in detail including common approaches to retrieval, prompting, and fine-tuning. Finally, we describe publicly available English datasets created for this task.",
        ),
        markdown_path=str(markdown_file_path),
    )

    agent = PaperAnalyzerAgent(
        llm=ChatOpenAI(model="gpt-4o-mini", temperature=0.0),
    )
    for state in agent.graph.stream(
        PaperAnalyzerAgentState(
            goal="研究の意義についてまとめよ",
            reading_result=reading_result,
        )
    ):
        print(state)
