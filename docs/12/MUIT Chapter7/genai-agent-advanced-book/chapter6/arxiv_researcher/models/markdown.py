from pydantic import BaseModel, Field


class Section(BaseModel):
    """
    Markdownのセクション構造を表現するモデル
    """

    header: str = Field(description="セクションのヘッダー")
    content: str = Field(description="セクションの内容")
    char_count: int = Field(description="セクションの文字数")
