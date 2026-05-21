from typing import Optional

from pydantic import BaseModel, Field

from arxiv_researcher.models.arxiv import ArxivPaper


class ReadingResult(BaseModel):
    """
    論文の読み込み結果を表現するモデル
    """

    id: int = Field(default=0, description="ID")
    task: str = Field(default="", description="調査タスク")
    paper: ArxivPaper = Field(default=None, description="論文データ")
    markdown_path: str = Field(
        default="", description="論文のmarkdownファイルへの相対パス"
    )
    answer: str = Field(default="", description="タスクに対する回答")
    is_related: Optional[bool] = Field(
        default=None, description="タスクとの関係性があるかどうか"
    )

    def __hash__(self) -> int:
        return hash(self.id)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, ReadingResult):
            return self.id == other.id
        return False
