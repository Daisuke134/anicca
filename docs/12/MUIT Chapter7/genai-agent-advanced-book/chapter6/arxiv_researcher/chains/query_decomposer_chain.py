from datetime import datetime
from typing import Literal

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langgraph.types import Command
from pydantic import BaseModel, Field

from arxiv_researcher.chains.task_evaluator_chain import TaskEvaluation
from arxiv_researcher.chains.utils import load_prompt
from arxiv_researcher.settings import settings


class DecomposedTasks(BaseModel):
    tasks: list[str] = Field(
        default_factory=list,
        min_length=settings.query_decomposer.min_decomposed_tasks,
        max_length=settings.query_decomposer.max_decomposed_tasks,
        description="分解されたタスクのリスト",
    )


class QueryDecomposer:
    def __init__(self, llm: ChatOpenAI):
        self.llm = llm
        self.current_date = datetime.now().strftime("%Y-%m-%d")
        self.min_decomposed_tasks = settings.query_decomposer.min_decomposed_tasks
        self.max_decomposed_tasks = settings.query_decomposer.max_decomposed_tasks

    def __call__(self, state: dict) -> Command[Literal["paper_search_agent"]]:
        evaluation: TaskEvaluation | None = state.get("evaluation", None)

        content = evaluation.content if evaluation else state.get("goal", "")
        decomposed_tasks: DecomposedTasks = self.run(content)

        return Command(
            goto="paper_search_agent",
            update={"tasks": decomposed_tasks.tasks},
        )

    def run(self, query: str) -> DecomposedTasks:
        prompt = ChatPromptTemplate.from_template(load_prompt("query_decomposer"))
        chain = prompt | self.llm.with_structured_output(
            DecomposedTasks,
            method="function_calling",
        )
        return chain.with_retry().invoke(
            {
                "min_decomposed_tasks": self.min_decomposed_tasks,
                "max_decomposed_tasks": self.max_decomposed_tasks,
                "current_date": self.current_date,
                "query": query,
            }
        )


if __name__ == "__main__":
    from arxiv_researcher.settings import settings

    decomposer = QueryDecomposer(settings.fast_llm)
    print(
        decomposer.run(
            "NLPにおける事実検証用データセットに関する以下の3つの観点からの情報を収集してください：1. データセットの一般的な概要と事実検証への貢献2. 代表的なデータセット（FEVER、SQuADなど）の具体的な特徴と構造3. これらのデータセットの実際の使用事例と研究・産業界への影響"
        )
    )
