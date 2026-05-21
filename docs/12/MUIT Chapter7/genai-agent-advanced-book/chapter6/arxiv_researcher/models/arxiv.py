import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ArxivPaper(BaseModel):
    """
    arXivの論文情報を表現するモデル
    """

    id: str = Field(default="", description="arXiv ID")
    title: str = Field(default="", description="論文タイトル")
    link: str = Field(default="", description="論文リンク")
    pdf_link: str = Field(default="", description="PDFリンク")
    abstract: str = Field(default="", description="論文アブストラクト")
    published: datetime.datetime = Field(default=None, description="公開日")
    updated: datetime.datetime = Field(default=None, description="更新日")
    version: int = Field(default=0, description="バージョン")
    authors: list[str] = Field(default=[], description="著者")
    categories: list[str] = Field(default=[], description="カテゴリ")
    relevance_score: Optional[float] = Field(default=None, description="関連度スコア")

    @property
    def text(self) -> str:
        return f"""\
<paper>
  <id>{self.id}</id>
  <title>{self.title}</title>
  <link>{self.link}</link>
  <pdf_link>{self.pdf_link}</pdf_link>
  <abstract>{self.abstract}</abstract>
  <published>{self.published}</published>
  <updated>{self.updated}</updated>
  <version>{self.version}</version>
  <authors>{', '.join(self.authors)}</authors>
  <categories>{', '.join(self.categories)}</categories>
  {f"<relevance_score>{self.relevance_score}</relevance_score>" if self.relevance_score else ""}
</paper>"""
