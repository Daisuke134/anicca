import concurrent.futures
from typing import Literal, TypedDict

from langgraph.types import Command, Send

from arxiv_researcher.agent.paper_analyzer_agent import PaperAnalyzerAgentInputState
from arxiv_researcher.models import ArxivPaper, ReadingResult
from arxiv_researcher.searcher.arxiv_searcher import ArxivSearcher
from arxiv_researcher.service.markdown_storage import MarkdownStorage
from arxiv_researcher.service.pdf_to_markdown import PdfToMarkdown
from arxiv_researcher.settings import settings


class PaperProcessorInput(TypedDict):
    goal: str
    tasks: list[str]


class PaperProcessor:
    def __init__(
        self,
        searcher: ArxivSearcher,
        max_workers: int = settings.arxiv_search_agent.max_workers,
    ):
        self.searcher = searcher
        self.max_workers = max_workers
        self.markdown_storage = MarkdownStorage()

    def __call__(self, state: PaperProcessorInput) -> Command[Literal["analyze_paper"]]:
        gotos = []
        reading_results = self.run(state)
        for reading_result in reading_results:
            gotos.append(
                Send(
                    "analyze_paper",
                    PaperAnalyzerAgentInputState(
                        goal=state.get("goal", ""),
                        reading_result=reading_result,
                    ),
                )
            )
        return Command(
            goto=gotos,
            update={"reading_results": reading_results},
        )

    def convert_pdfs(self, papers: list[ArxivPaper]) -> list[str]:
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=self.max_workers
        ) as executor:
            markdown_paths = []
            for paper in papers:
                markdown_text = PdfToMarkdown(paper.pdf_link).convert()
                filename = f"{paper.id}.md"
                markdown_path = self.markdown_storage.write(filename, markdown_text)
                markdown_paths.append(markdown_path)
        return markdown_paths

    def run(self, state: PaperProcessorInput) -> list[ReadingResult]:
        result_index = 0
        reading_results: list[ReadingResult] = []
        unique_papers: dict[str, ArxivPaper] = {}
        task_papers: dict[str, list[str]] = {}

        def process_task(task: str) -> None:
            searched_papers: list[ArxivPaper] = self.searcher.run(
                state.get("goal", ""), task
            )
            task_papers[task] = [paper.pdf_link for paper in searched_papers]
            for paper in searched_papers:
                unique_papers[paper.pdf_link] = paper

        # タスクの処理
        for task in state.get("tasks", []):
            process_task(task)

        # 重複排除後の論文リストに対してPDF変換を実行
        markdown_paths = self.convert_pdfs(list(unique_papers.values()))

        # 各タスクに対して関連する論文を割り当て
        for task in state.get("tasks", []):
            for pdf_link in task_papers[task]:
                paper = unique_papers[pdf_link]
                paper_index = list(unique_papers.keys()).index(pdf_link)
                reading_results.append(
                    ReadingResult(
                        id=result_index,
                        task=task,
                        paper=paper,
                        markdown_path=markdown_paths[paper_index],
                    )
                )
                result_index += 1

        return reading_results
